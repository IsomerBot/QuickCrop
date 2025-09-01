"""
Crop processing engine with manual adjustment support.
Handles crop execution, image resizing, and export functionality.
"""

from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image
import io
import logging

from services.presets import PresetType, get_preset
from services.crop_calculator import CropBox, FaceBox, calculate_crop
from services.heuristics import HeuristicsManager
from services.image_processor import image_processor_service


logger = logging.getLogger(__name__)


@dataclass
class ManualAdjustment:
    """Represents manual adjustments to a crop."""
    offset_x: int = 0  # Horizontal offset from calculated position
    offset_y: int = 0  # Vertical offset from calculated position
    scale: float = 1.0  # Scale factor for crop size
    
    def apply_to_crop(self, crop: CropBox, image_width: int, image_height: int) -> CropBox:
        """
        Apply manual adjustments to a crop box.
        
        Args:
            crop: Original crop box
            image_width: Image width for bounds checking
            image_height: Image height for bounds checking
            
        Returns:
            Adjusted crop box
        """
        # Apply scale to dimensions
        new_width = int(crop.width * self.scale)
        new_height = int(crop.height * self.scale)
        
        # Calculate new position to keep crop centered after scaling
        scale_offset_x = (crop.width - new_width) // 2
        scale_offset_y = (crop.height - new_height) // 2
        
        # Apply manual offsets
        new_x = crop.x + scale_offset_x + self.offset_x
        new_y = crop.y + scale_offset_y + self.offset_y
        
        # Create adjusted crop
        adjusted = CropBox(
            x=new_x,
            y=new_y,
            width=new_width,
            height=new_height,
            preset_type=crop.preset_type
        )
        
        # Ensure it fits within image bounds
        return adjusted.adjust_to_bounds(image_width, image_height)


class CropExecutor:
    """Executes crop operations on images."""
    
    def __init__(self, image: Image.Image):
        """
        Initialize crop executor with an image.
        
        Args:
            image: PIL Image to crop
        """
        self.image = image
        self.width, self.height = image.size
    
    def execute_crop(
        self,
        crop: CropBox,
        adjustment: Optional[ManualAdjustment] = None
    ) -> Image.Image:
        """
        Execute a crop operation on the image.
        
        Args:
            crop: Crop box defining the region
            adjustment: Optional manual adjustments
            
        Returns:
            Cropped PIL Image
        """
        # Apply manual adjustments if provided
        if adjustment:
            crop = adjustment.apply_to_crop(crop, self.width, self.height)
        
        # Validate bounds
        if not crop.validate_bounds(self.width, self.height):
            logger.warning(f"Crop extends beyond image bounds, adjusting...")
            crop = crop.adjust_to_bounds(self.width, self.height)
        
        # Extract crop region
        crop_box = (crop.x, crop.y, crop.x + crop.width, crop.y + crop.height)
        cropped = self.image.crop(crop_box)
        
        return cropped
    
    def execute_and_resize(
        self,
        crop: CropBox,
        target_size: Tuple[int, int],
        adjustment: Optional[ManualAdjustment] = None
    ) -> Image.Image:
        """
        Execute crop and resize to target dimensions.
        
        Args:
            crop: Crop box defining the region
            target_size: Target (width, height) for resize
            adjustment: Optional manual adjustments
            
        Returns:
            Cropped and resized PIL Image
        """
        # Execute crop
        cropped = self.execute_crop(crop, adjustment)
        
        # Resize to target dimensions
        resized = cropped.resize(target_size, Image.Resampling.LANCZOS)
        
        return resized


class ImageProcessor:
    """Main image processing coordinator."""
    
    def __init__(self, image_bytes: bytes, enable_heuristics: bool = True):
        """
        Initialize processor with image data.
        
        Args:
            image_bytes: Raw image bytes
            enable_heuristics: Whether to use heuristics learning system
        """
        self.image = Image.open(io.BytesIO(image_bytes))
        self.executor = CropExecutor(self.image)
        self.width, self.height = self.image.size
        self.enable_heuristics = enable_heuristics
        self.heuristics_manager = HeuristicsManager() if enable_heuristics else None
    
    def process_with_crop_box(
        self,
        crop_box_dict: Dict[str, Any],
        preset_type: PresetType,
        format: str = 'JPEG',
        quality: Optional[int] = 95,
        auto_optimize: bool = True
    ) -> bytes:
        """
        Process image with a user-provided crop box.
        
        Args:
            crop_box_dict: Dictionary with x, y, width, height
            preset_type: Type of preset (for output dimensions)
            format: Output format (JPEG, PNG, etc.)
            quality: Output quality (1-100) - ignored when auto_optimize=True
            auto_optimize: Use Tinify for smart compression
            
        Returns:
            Processed image bytes
        """
        from services.crop_calculator import CropBox
        
        # Create CropBox from user's crop area
        user_crop = CropBox(
            x=int(crop_box_dict.get('x', 0)),
            y=int(crop_box_dict.get('y', 0)),
            width=int(crop_box_dict.get('width', 100)),
            height=int(crop_box_dict.get('height', 100)),
            preset_type=preset_type
        )
        
        # Get preset configuration for output dimensions
        preset = get_preset(preset_type)
        
        # Execute crop and resize to preset dimensions
        processed = self.executor.execute_and_resize(
            user_crop,
            (preset.output_width, preset.output_height),
            None  # No adjustments needed - using exact crop
        )
        
        # Convert to bytes
        output = io.BytesIO()
        
        # Handle different formats
        if format.upper() == 'PNG':
            processed.save(output, format='PNG', optimize=False)
        elif format.upper() == 'WEBP':
            if processed.mode == 'RGBA':
                processed.save(output, format='WEBP', quality=quality or 85, optimize=True)
            else:
                processed.save(output, format='WEBP', quality=quality or 85, optimize=True)
        else:
            # Convert RGBA to RGB for JPEG
            if processed.mode == 'RGBA':
                background = Image.new('RGB', processed.size, (255, 255, 255))
                background.paste(processed, mask=processed.split()[3])
                processed = background
            
            if auto_optimize:
                processed.save(output, format='JPEG', quality=95, optimize=False)
            else:
                processed.save(output, format='JPEG', quality=quality or 85, optimize=True)
        
        image_bytes = output.getvalue()
        
        # Apply Tinify optimization if enabled
        if auto_optimize:
            optimized_bytes = image_processor_service.optimize_image_bytes(
                image_bytes, 
                format=format.lower(), 
                auto_optimize=True
            )
            return optimized_bytes
        else:
            return image_bytes
    
    def process_preset(
        self,
        preset_type: PresetType,
        face: FaceBox,
        adjustment: Optional[ManualAdjustment] = None,
        format: str = 'JPEG',
        quality: Optional[int] = 95,
        auto_optimize: bool = True
    ) -> bytes:
        """
        Process image for a specific preset.
        
        Args:
            preset_type: Type of preset to apply
            face: Detected face bounding box
            adjustment: Optional manual adjustments
            format: Output format (JPEG, PNG, etc.)
            quality: Output quality (1-100) - ignored when auto_optimize=True
            auto_optimize: Use Tinify for smart compression
            
        Returns:
            Processed image bytes
        """
        # Get preset configuration
        preset = get_preset(preset_type)
        
        # Calculate crop
        crop = calculate_crop(preset_type, face, self.width, self.height)
        
        # Execute crop and resize
        processed = self.executor.execute_and_resize(
            crop,
            (preset.output_width, preset.output_height),
            adjustment
        )
        
        # Convert to bytes
        output = io.BytesIO()
        
        # Handle different formats
        if format.upper() == 'PNG':
            processed.save(output, format='PNG', optimize=False)  # Don't pre-optimize, let Tinify handle it
        elif format.upper() == 'WEBP':
            # For WebP format
            if processed.mode == 'RGBA':
                processed.save(output, format='WEBP', quality=quality or 85, optimize=True)
            else:
                processed.save(output, format='WEBP', quality=quality or 85, optimize=True)
        else:
            # Convert RGBA to RGB for JPEG
            if processed.mode == 'RGBA':
                # Create white background
                background = Image.new('RGB', processed.size, (255, 255, 255))
                background.paste(processed, mask=processed.split()[3])
                processed = background
            
            # For JPEG, apply quality if not using auto-optimize
            if auto_optimize:
                processed.save(output, format='JPEG', quality=95, optimize=False)  # High quality for Tinify
            else:
                processed.save(output, format='JPEG', quality=quality or 85, optimize=True)
        
        image_bytes = output.getvalue()
        
        # Apply Tinify optimization if enabled
        if auto_optimize:
            optimized_bytes = image_processor_service.optimize_image_bytes(
                image_bytes, 
                format=format.lower(), 
                auto_optimize=True
            )
            return optimized_bytes
        else:
            return image_bytes
    
    def process_all_presets(
        self,
        face: FaceBox,
        adjustments: Optional[Dict[PresetType, ManualAdjustment]] = None,
        format: str = 'JPEG',
        quality: int = 95
    ) -> Dict[PresetType, bytes]:
        """
        Process image for all preset types.
        
        Args:
            face: Detected face bounding box
            adjustments: Optional manual adjustments per preset
            format: Output format
            quality: Output quality
            
        Returns:
            Dictionary mapping preset types to processed image bytes
        """
        results = {}
        
        for preset_type in PresetType:
            adjustment = adjustments.get(preset_type) if adjustments else None
            results[preset_type] = self.process_preset(
                preset_type, face, adjustment, format, quality
            )
        
        return results
    
    def apply_heuristics_to_crop(
        self,
        crop: CropBox,
        face: Optional[FaceBox] = None
    ) -> Tuple[CropBox, Dict[str, Any]]:
        """
        Apply learned heuristics to improve crop suggestion.
        
        Args:
            crop: Initial crop suggestion
            face: Optional face detection for context
            
        Returns:
            Tuple of (adjusted_crop, heuristics_metadata)
        """
        if not self.enable_heuristics or not self.heuristics_manager:
            return crop, {'heuristics_applied': False}
        
        # Convert face box to dict format for heuristics
        face_boxes = []
        if face:
            face_boxes.append({
                'x': face.x,
                'y': face.y,
                'width': face.width,
                'height': face.height
            })
        
        # Apply heuristics
        result = self.heuristics_manager.apply_heuristics(
            self.image,
            crop.to_dict(),
            face_boxes=face_boxes,
            confidence_threshold=0.3
        )
        
        # Convert result back to CropBox
        adjusted_crop = CropBox(
            x=result['crop']['x'],
            y=result['crop']['y'],
            width=result['crop']['width'],
            height=result['crop']['height'],
            preset_type=crop.preset_type
        )
        
        return adjusted_crop, result
    
    def learn_from_adjustment(
        self,
        initial_crop: CropBox,
        final_crop: CropBox,
        face: Optional[FaceBox] = None
    ) -> None:
        """
        Learn from user's manual crop adjustment.
        
        Args:
            initial_crop: AI-suggested crop
            final_crop: User-adjusted final crop
            face: Optional face detection for context
        """
        if not self.enable_heuristics or not self.heuristics_manager:
            return
        
        # Convert face box to dict format
        face_boxes = []
        if face:
            face_boxes.append({
                'x': face.x,
                'y': face.y,
                'width': face.width,
                'height': face.height
            })
        
        # Learn from adjustment
        self.heuristics_manager.learn_from_adjustment(
            self.image,
            initial_crop.to_dict(),
            final_crop.to_dict(),
            face_boxes=face_boxes
        )
        
        logger.info("Learned from user crop adjustment")
    
    def get_crop_preview(
        self,
        preset_type: PresetType,
        face: FaceBox,
        adjustment: Optional[ManualAdjustment] = None,
        preview_width: int = 400,
        apply_heuristics: bool = True
    ) -> Dict[str, Any]:
        """
        Get a preview of the crop with metadata.
        
        Args:
            preset_type: Type of preset
            face: Detected face bounding box
            adjustment: Optional manual adjustments
            preview_width: Width of preview image
            apply_heuristics: Whether to apply learned heuristics
            
        Returns:
            Dictionary with preview image and metadata
        """
        # Calculate crop
        crop = calculate_crop(preset_type, face, self.width, self.height)
        
        # Apply heuristics if enabled
        heuristics_metadata = {'heuristics_applied': False}
        if apply_heuristics and self.enable_heuristics:
            crop, heuristics_metadata = self.apply_heuristics_to_crop(crop, face)
        
        # Apply adjustments if provided
        if adjustment:
            crop = adjustment.apply_to_crop(crop, self.width, self.height)
        
        # Get preset info
        preset = get_preset(preset_type)
        
        # Calculate preview size maintaining aspect ratio
        aspect_ratio = preset.output_width / preset.output_height
        preview_height = int(preview_width / aspect_ratio)
        
        # Generate preview
        preview = self.executor.execute_and_resize(
            crop,
            (preview_width, preview_height),
            None  # Adjustments already applied
        )
        
        # Convert to bytes
        preview_bytes = io.BytesIO()
        preview.save(preview_bytes, format='JPEG', quality=85)
        
        return {
            'preview': preview_bytes.getvalue(),
            'crop_box': crop.to_dict(),
            'preset': {
                'type': preset_type.value,
                'name': preset.name,
                'dimensions': f"{preset.output_width}×{preset.output_height}",
                'aspect_ratio': preset.aspect_ratio
            },
            'adjustments': {
                'offset_x': adjustment.offset_x if adjustment else 0,
                'offset_y': adjustment.offset_y if adjustment else 0,
                'scale': adjustment.scale if adjustment else 1.0
            },
            'heuristics': heuristics_metadata
        }


def validate_manual_adjustment(
    adjustment: ManualAdjustment,
    crop: CropBox,
    image_width: int,
    image_height: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate that manual adjustments are within acceptable bounds.
    
    Args:
        adjustment: Manual adjustment to validate
        crop: Original crop box
        image_width: Image width
        image_height: Image height
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check scale limits
    if adjustment.scale < 0.5:
        return False, "Scale cannot be less than 0.5"
    if adjustment.scale > 2.0:
        return False, "Scale cannot be greater than 2.0"
    
    # Apply adjustment and check if result fits
    adjusted = adjustment.apply_to_crop(crop, image_width, image_height)
    
    # Check if adjusted crop is too small
    if adjusted.width < 100 or adjusted.height < 100:
        return False, "Adjusted crop is too small"
    
    # The adjust_to_bounds method will handle boundary violations,
    # but we can warn if significant adjustment is needed
    if adjusted.x < 0 or adjusted.y < 0:
        logger.warning("Adjustment moves crop outside image bounds")
    
    if adjusted.x + adjusted.width > image_width:
        logger.warning("Adjustment extends crop beyond image width")
    
    if adjusted.y + adjusted.height > image_height:
        logger.warning("Adjustment extends crop beyond image height")
    
    return True, None


def create_adjustment_from_ui(
    ui_data: Dict[str, Any]
) -> ManualAdjustment:
    """
    Create ManualAdjustment from UI data.
    
    Args:
        ui_data: Dictionary with offset_x, offset_y, scale from UI
        
    Returns:
        ManualAdjustment instance
    """
    return ManualAdjustment(
        offset_x=ui_data.get('offset_x', 0),
        offset_y=ui_data.get('offset_y', 0),
        scale=ui_data.get('scale', 1.0)
    )