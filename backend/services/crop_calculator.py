"""
Crop calculation algorithms for different preset types.
Handles face-centered framing and intelligent crop calculations.
"""

from typing import Tuple, Dict, Optional
from dataclasses import dataclass
import math

from services.presets import PresetType, PresetConfig, get_preset


@dataclass
class FaceBox:
    """Represents a detected face bounding box."""
    x: int  # Left edge
    y: int  # Top edge
    width: int
    height: int
    
    @property
    def center_x(self) -> int:
        """Get horizontal center of face."""
        return self.x + self.width // 2
    
    @property
    def center_y(self) -> int:
        """Get vertical center of face."""
        return self.y + self.height // 2
    
    @property
    def bottom(self) -> int:
        """Get bottom edge of face."""
        return self.y + self.height


@dataclass
class CropBox:
    """Represents a calculated crop region."""
    x: int  # Left edge
    y: int  # Top edge
    width: int
    height: int
    preset_type: PresetType
    
    def validate_bounds(self, image_width: int, image_height: int) -> bool:
        """Check if crop box is within image bounds."""
        return (
            self.x >= 0 and
            self.y >= 0 and
            self.x + self.width <= image_width and
            self.y + self.height <= image_height
        )
    
    def adjust_to_bounds(self, image_width: int, image_height: int) -> 'CropBox':
        """Adjust crop box to fit within image bounds."""
        # Adjust position to fit within bounds
        x = max(0, min(self.x, image_width - self.width))
        y = max(0, min(self.y, image_height - self.height))
        
        # Adjust size if necessary
        width = min(self.width, image_width - x)
        height = min(self.height, image_height - y)
        
        return CropBox(x, y, width, height, self.preset_type)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'preset_type': self.preset_type.value
        }


class CropCalculator:
    """Base class for crop calculations."""
    
    def __init__(self, preset: PresetConfig):
        self.preset = preset
    
    def calculate(
        self,
        face: FaceBox,
        image_width: int,
        image_height: int
    ) -> CropBox:
        """
        Calculate crop box for given face and image dimensions.
        
        Args:
            face: Detected face bounding box
            image_width: Original image width
            image_height: Original image height
            
        Returns:
            CropBox with calculated crop region
        """
        raise NotImplementedError


class HeadshotCropCalculator(CropCalculator):
    """Calculator for headshot and avatar crops (square)."""
    
    def calculate(
        self,
        face: FaceBox,
        image_width: int,
        image_height: int
    ) -> CropBox:
        """Calculate square crop centered on face with 14.5% head clearance."""
        # Calculate desired crop size based on face
        # Based on samples: face should be ~31% of the crop
        # Using 3.2x to match sample proportions
        crop_size = int(max(face.width, face.height) * 3.2)
        
        # Ensure minimum size for quality
        min_size = min(1000, min(image_width, image_height))
        crop_size = max(crop_size, min_size)
        
        # Don't exceed image dimensions
        crop_size = min(crop_size, min(image_width, image_height))
        
        # Estimate head top position
        # Face bbox top minus ~15% of face height for forehead/hair
        # This has been verified to match our sample images perfectly
        estimated_head_top = face.y - int(face.height * 0.15)
        
        # Calculate crop_y to achieve 14.5% head clearance (from samples)
        # We want the head to be at 14.5% FROM THE TOP of the crop
        # So if head is at pixel 1978, and we want it at 14.5% of crop:
        # crop_y = head_top - (0.145 * crop_size)
        # This positions the crop so the head appears at 14.5% down from crop top
        target_head_position = int(crop_size * 0.145)
        crop_y = estimated_head_top - target_head_position
        
        # Debug logging (removed as it was causing issues)
        
        # Only fall back if crop would go out of bounds
        if crop_y < 0:
            # If head clearance pushes crop above image, reduce clearance
            crop_y = 0
        elif crop_y + crop_size > image_height:
            # If crop extends below image, adjust up
            crop_y = image_height - crop_size
        
        # Center horizontally on face
        crop_x = face.center_x - crop_size // 2
        
        # Create crop box
        crop = CropBox(
            x=crop_x,
            y=crop_y,
            width=crop_size,
            height=crop_size,
            preset_type=self.preset.type
        )
        
        # Adjust to image bounds
        return crop.adjust_to_bounds(image_width, image_height)


class WebsiteCropCalculator(CropCalculator):
    """Calculator for website photo crops (4:5 portrait)."""
    
    def calculate(
        self,
        face: FaceBox,
        image_width: int,
        image_height: int
    ) -> CropBox:
        """Calculate 4:5 portrait crop with 13.8% head clearance."""
        # Calculate crop dimensions based on aspect ratio
        aspect_ratio = 4 / 5  # Width / Height
        
        # Base crop height on face size - include upper torso
        # Based on samples: face should be ~25% of crop height
        crop_height = int(face.height * 4.0)
        crop_width = int(crop_height * aspect_ratio)
        
        # Ensure minimum size
        min_height = min(1200, image_height)
        if crop_height < min_height:
            crop_height = min_height
            crop_width = int(crop_height * aspect_ratio)
        
        # Don't exceed image dimensions
        if crop_width > image_width:
            crop_width = image_width
            crop_height = int(crop_width / aspect_ratio)
        if crop_height > image_height:
            crop_height = image_height
            crop_width = int(crop_height * aspect_ratio)
        
        # Estimate head top position
        # Face bbox top minus ~15% of face height for forehead/hair
        # This has been verified to match our sample images perfectly
        estimated_head_top = face.y - int(face.height * 0.15)
        
        # Calculate crop_y to achieve 13.8% head clearance (from samples)
        # Target: head_clearance / crop_height = 0.138
        target_head_clearance = int(crop_height * 0.138)
        crop_y = estimated_head_top - target_head_clearance
        
        # Only fall back if crop would go out of bounds
        if crop_y < 0:
            # If head clearance pushes crop above image, reduce clearance
            crop_y = 0
        elif crop_y + crop_height > image_height:
            # If crop extends below image, adjust up
            crop_y = image_height - crop_height
        
        # Center horizontally
        crop_x = face.center_x - crop_width // 2
        
        # Create crop box
        crop = CropBox(
            x=crop_x,
            y=crop_y,
            width=crop_width,
            height=crop_height,
            preset_type=self.preset.type
        )
        
        return crop.adjust_to_bounds(image_width, image_height)


class FullBodyCropCalculator(CropCalculator):
    """Calculator for full body crops (17:20 portrait)."""
    
    def calculate(
        self,
        face: FaceBox,
        image_width: int,
        image_height: int
    ) -> CropBox:
        """Calculate 17:20 portrait crop with 16.1% head clearance."""
        # Calculate crop dimensions based on aspect ratio
        aspect_ratio = 17 / 20  # Width / Height
        
        # For full body, based on samples: face should be ~20% of height
        crop_height = int(face.height * 5.0)
        crop_width = int(crop_height * aspect_ratio)
        
        # Ensure minimum size
        min_height = min(2000, image_height)
        if crop_height < min_height:
            crop_height = min_height
            crop_width = int(crop_height * aspect_ratio)
        
        # Don't exceed image dimensions
        if crop_width > image_width:
            crop_width = image_width
            crop_height = int(crop_width / aspect_ratio)
        if crop_height > image_height:
            crop_height = image_height
            crop_width = int(crop_height * aspect_ratio)
        
        # Estimate head top position
        # Face bbox top minus ~15% of face height for forehead/hair
        # This has been verified to match our sample images perfectly
        estimated_head_top = face.y - int(face.height * 0.15)
        
        # Calculate crop_y to achieve 16.1% head clearance (from samples)
        # Target: head_clearance / crop_height = 0.161
        target_head_clearance = int(crop_height * 0.161)
        crop_y = estimated_head_top - target_head_clearance
        
        # Only fall back if crop would go out of bounds
        if crop_y < 0:
            # If head clearance pushes crop above image, reduce clearance
            crop_y = 0
        elif crop_y + crop_height > image_height:
            # If crop extends below image, adjust up
            crop_y = image_height - crop_height
        
        # Center horizontally
        crop_x = face.center_x - crop_width // 2
        
        # Create crop box
        crop = CropBox(
            x=crop_x,
            y=crop_y,
            width=crop_width,
            height=crop_height,
            preset_type=self.preset.type
        )
        
        return crop.adjust_to_bounds(image_width, image_height)


class CropCalculatorFactory:
    """Factory for creating appropriate crop calculators."""
    
    _calculators = {
        PresetType.HEADSHOT: HeadshotCropCalculator,
        PresetType.AVATAR: HeadshotCropCalculator,  # Same as headshot
        PresetType.THUMBNAIL: HeadshotCropCalculator,  # Same framing as headshot
        PresetType.WEBSITE: WebsiteCropCalculator,
        PresetType.FULL_BODY: FullBodyCropCalculator
    }
    
    @classmethod
    def create(cls, preset_type: PresetType) -> CropCalculator:
        """
        Create calculator for given preset type.
        
        Args:
            preset_type: Type of preset to create calculator for
            
        Returns:
            Appropriate CropCalculator instance
            
        Raises:
            ValueError: If preset type is not supported
        """
        if preset_type not in cls._calculators:
            raise ValueError(f"No calculator available for preset type: {preset_type}")
        
        preset = get_preset(preset_type)
        calculator_class = cls._calculators[preset_type]
        return calculator_class(preset)


def calculate_crop(
    preset_type: PresetType,
    face: FaceBox,
    image_width: int,
    image_height: int
) -> CropBox:
    """
    Calculate crop for given preset type and face detection.
    
    Args:
        preset_type: Type of crop preset
        face: Detected face bounding box
        image_width: Original image width
        image_height: Original image height
        
    Returns:
        CropBox with calculated crop region
    """
    calculator = CropCalculatorFactory.create(preset_type)
    return calculator.calculate(face, image_width, image_height)


def calculate_all_crops(
    face: FaceBox,
    image_width: int,
    image_height: int
) -> Dict[PresetType, CropBox]:
    """
    Calculate crops for all preset types.
    
    Args:
        face: Detected face bounding box
        image_width: Original image width
        image_height: Original image height
        
    Returns:
        Dictionary mapping preset types to crop boxes
    """
    crops = {}
    for preset_type in PresetType:
        crops[preset_type] = calculate_crop(
            preset_type, face, image_width, image_height
        )
    return crops


def validate_crop_bounds(
    crop: CropBox,
    image_width: int,
    image_height: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a crop box is within image bounds.
    
    Args:
        crop: Crop box to validate
        image_width: Image width
        image_height: Image height
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if crop.x < 0:
        return False, "Crop x position is negative"
    if crop.y < 0:
        return False, "Crop y position is negative"
    if crop.x + crop.width > image_width:
        return False, "Crop extends beyond image width"
    if crop.y + crop.height > image_height:
        return False, "Crop extends beyond image height"
    if crop.width <= 0:
        return False, "Crop width must be positive"
    if crop.height <= 0:
        return False, "Crop height must be positive"
    
    return True, None
