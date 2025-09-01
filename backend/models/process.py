"""
Image processing-related Pydantic models
"""

from pydantic import BaseModel
from typing import Optional, Literal, Dict, List, Any
from enum import Enum


class CropPreset(str, Enum):
    """Available crop presets"""
    HEADSHOT = "headshot"  # 2000x2000 square
    AVATAR = "avatar"  # 300x300 square
    WEBSITE = "website"  # 1600x2000 portrait (4:5)
    FULL_BODY = "full_body"  # 3400x4000 portrait (17:20)


class ProcessRequest(BaseModel):
    """Request model for image processing"""
    file_id: str
    preset: str
    output_format: Optional[Literal["jpeg", "png", "webp"]] = "jpeg"
    quality: Optional[int] = 85  # 1-100 for JPEG/WebP, ignored when auto_optimize=True
    optimize: Optional[bool] = True
    auto_optimize: Optional[bool] = True  # Use Tinify for smart compression


class ProcessResponse(BaseModel):
    """Response model for image processing"""
    file_id: str
    preset: str
    status: Literal["queued", "processing", "completed", "failed"]
    output_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PreviewRequest(BaseModel):
    """Request model for crop preview"""
    preset: str
    adjustments: Optional[Dict[str, Any]] = None  # offset_x, offset_y, scale
    preview_width: Optional[int] = 400


class ExportRequest(BaseModel):
    """Request model for image export"""
    preset: Optional[str] = None  # Single preset
    presets: Optional[List[str]] = None  # Multiple presets
    adjustments: Optional[Dict[str, Any]] = None  # Global adjustments
    preset_adjustments: Optional[Dict[str, Dict[str, Any]]] = None  # Per-preset adjustments
    crop_box: Optional[Dict[str, Any]] = None  # Absolute crop box from frontend (x, y, width, height)
    format: Literal["jpeg", "png", "webp"] = "jpeg"
    quality: Optional[int] = 85  # 1-100 for JPEG/WebP, ignored when auto_optimize=True
    optimize: Optional[bool] = True
    auto_optimize: Optional[bool] = True  # Use Tinify for smart compression


class CropSettings(BaseModel):
    """Settings for crop operation"""
    aspect_ratio: tuple[int, int]
    padding_percent: float = 0.2
    focus_area: Literal["face", "torso", "center"] = "face"
    
    class Config:
        frozen = True


# Preset configurations
PRESET_CONFIGS = {
    CropPreset.HEADSHOT: CropSettings(
        aspect_ratio=(1, 1),
        padding_percent=0.2,
        focus_area="face"
    ),
    CropPreset.AVATAR: CropSettings(
        aspect_ratio=(1, 1),
        padding_percent=0.15,
        focus_area="face"
    ),
    CropPreset.WEBSITE: CropSettings(
        aspect_ratio=(4, 5),
        padding_percent=0.2,
        focus_area="torso"
    ),
    CropPreset.FULL_BODY: CropSettings(
        aspect_ratio=(17, 20),
        padding_percent=0.15,
        focus_area="torso"
    )
}