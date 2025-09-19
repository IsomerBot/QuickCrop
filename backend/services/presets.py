"""
Crop preset configuration system for QuickCrop.
Defines the four main preset types with their dimensions and rules.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from enum import Enum


class PresetType(Enum):
    """Enumeration of available crop preset types."""
    HEADSHOT = "headshot"
    AVATAR = "avatar"
    THUMBNAIL = "thumbnail"
    WEBSITE = "website"
    FULL_BODY = "full_body"


@dataclass
class PresetConfig:
    """Configuration for a single crop preset."""
    name: str
    type: PresetType
    output_width: int
    output_height: int
    aspect_ratio: float
    crop_ratio: Tuple[int, int]  # (width_ratio, height_ratio)
    face_position: str  # 'center', 'upper', 'full'
    margin_top: float  # Percentage of height for top margin
    margin_sides: float  # Percentage of width for side margins
    description: str
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return output dimensions as a tuple."""
        return (self.output_width, self.output_height)
    
    def validate(self) -> bool:
        """Validate preset configuration."""
        if self.output_width <= 0 or self.output_height <= 0:
            return False
        if self.margin_top < 0 or self.margin_top > 0.5:
            return False
        if self.margin_sides < 0 or self.margin_sides > 0.5:
            return False
        calculated_ratio = self.output_width / self.output_height
        if abs(calculated_ratio - self.aspect_ratio) > 0.01:
            return False
        return True


# Define all crop presets
PRESETS: Dict[PresetType, PresetConfig] = {
    PresetType.HEADSHOT: PresetConfig(
        name="Headshot",
        type=PresetType.HEADSHOT,
        output_width=2000,
        output_height=2000,
        aspect_ratio=1.0,
        crop_ratio=(1, 1),
        face_position="center",
        margin_top=0.08,  # 8% top margin
        margin_sides=0.1,  # 10% side margins
        description="Square crop with face-centered framing for professional headshots"
    ),
    
    PresetType.AVATAR: PresetConfig(
        name="Avatar",
        type=PresetType.AVATAR,
        output_width=300,
        output_height=300,
        aspect_ratio=1.0,
        crop_ratio=(1, 1),
        face_position="center",
        margin_top=0.08,  # Same as headshot
        margin_sides=0.1,  # Same as headshot
        description="Small square crop for profile pictures and avatars"
    ),

    PresetType.THUMBNAIL: PresetConfig(
        name="Thumbnail",
        type=PresetType.THUMBNAIL,
        output_width=500,
        output_height=500,
        aspect_ratio=1.0,
        crop_ratio=(1, 1),
        face_position="center",
        margin_top=0.08,  # Same tuning as headshot/avatar for consistency
        margin_sides=0.1,
        description="Medium square crop for internal directories and thumbnails"
    ),
    
    PresetType.WEBSITE: PresetConfig(
        name="Website Photo",
        type=PresetType.WEBSITE,
        output_width=1600,
        output_height=2000,
        aspect_ratio=0.8,  # 4:5 ratio
        crop_ratio=(4, 5),
        face_position="upper",
        margin_top=0.05,  # 5% top margin
        margin_sides=0.08,  # 8% side margins
        description="Portrait crop with upper-body framing for website headers"
    ),
    
    PresetType.FULL_BODY: PresetConfig(
        name="Full Body",
        type=PresetType.FULL_BODY,
        output_width=3400,
        output_height=4000,
        aspect_ratio=0.85,  # 17:20 ratio
        crop_ratio=(17, 20),
        face_position="full",
        margin_top=0.05,  # 5% top margin
        margin_sides=0.05,  # 5% side margins
        description="Portrait crop with full-figure framing for professional photos"
    )
}


def get_preset(preset_type: PresetType) -> PresetConfig:
    """
    Get preset configuration by type.
    
    Args:
        preset_type: The type of preset to retrieve
        
    Returns:
        PresetConfig object for the requested preset
        
    Raises:
        KeyError: If preset type is not found
    """
    if preset_type not in PRESETS:
        raise KeyError(f"Preset type {preset_type} not found")
    return PRESETS[preset_type]


def get_all_presets() -> Dict[PresetType, PresetConfig]:
    """Get all available presets."""
    return PRESETS.copy()


def validate_all_presets() -> bool:
    """
    Validate all preset configurations.
    
    Returns:
        True if all presets are valid, False otherwise
    """
    for preset_type, preset in PRESETS.items():
        if not preset.validate():
            return False
    return True


def calculate_aspect_ratio(width: int, height: int) -> float:
    """
    Calculate aspect ratio from dimensions.
    
    Args:
        width: Width in pixels
        height: Height in pixels
        
    Returns:
        Aspect ratio as width/height
    """
    if height == 0:
        raise ValueError("Height cannot be zero")
    return width / height


def get_preset_by_dimensions(width: int, height: int) -> Optional[PresetType]:
    """
    Find a preset that matches the given dimensions.
    
    Args:
        width: Target width
        height: Target height
        
    Returns:
        PresetType if found, None otherwise
    """
    for preset_type, preset in PRESETS.items():
        if preset.output_width == width and preset.output_height == height:
            return preset_type
    return None


# Validate presets on module load
if not validate_all_presets():
    raise ValueError("Invalid preset configuration detected")
