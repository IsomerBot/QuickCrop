"""
AI-powered crop suggestions endpoint
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import numpy as np
import cv2

from services.storage import StorageService
from services.detection import DetectionService
from services.crop_calculator import calculate_all_crops, FaceBox
from services.presets import PresetType

router = APIRouter()

# Initialize services
storage = StorageService()
detector = DetectionService()


@router.get("/{upload_id}/suggestions")
async def get_crop_suggestions(upload_id: str):
    """
    Get AI-calculated crop suggestions for all presets based on face detection.
    
    Returns crop boxes optimized using our tuned MediaPipe rules.
    """
    
    # Load image from storage
    image_data = await storage.get_upload(upload_id)
    if not image_data:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {upload_id} not found"
        )
    
    # Detect face
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    detection_result = detector.detect(image)
    
    if not detection_result or not detection_result.face:
        raise HTTPException(
            status_code=400,
            detail="No faces detected in image"
        )
    
    # Convert detection to FaceBox
    bbox = detection_result.face.bbox
    height, width = image.shape[:2]
    face = FaceBox(
        x=int(bbox[0] * width),
        y=int(bbox[1] * height),
        width=int(bbox[2] * width),
        height=int(bbox[3] * height)
    )
    
    # Calculate crops for all presets using our tuned rules
    crops = calculate_all_crops(face, width, height)
    
    # Format response with crop suggestions
    suggestions = {}
    for preset_type, crop in crops.items():
        preset_name = preset_type.value
        suggestions[preset_name] = {
            "x": crop.x,
            "y": crop.y,
            "width": crop.width,
            "height": crop.height,
            "confidence": detection_result.face.confidence
        }
    
    # Add face detection info for debugging
    face_info = {
        "x": face.x,
        "y": face.y,
        "width": face.width,
        "height": face.height,
        "center_x": face.center_x,
        "center_y": face.center_y
    }
    
    # Log the suggestions for debugging
    import json
    for preset_name, suggestion in suggestions.items():
        face_position_in_crop = (face.center_y - suggestion['y']) / suggestion['height'] * 100
    
    return {
        "upload_id": upload_id,
        "image_dimensions": {
            "width": width,
            "height": height
        },
        "face_detection": face_info,
        "crop_suggestions": suggestions,
        "confidence": detection_result.face.confidence,
        "message": "Crop suggestions calculated using optimized MediaPipe rules"
    }