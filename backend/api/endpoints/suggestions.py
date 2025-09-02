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
    
    # If no face, try object detection for project-oriented crops
    is_employee = detection_result and detection_result.face is not None
    
    height, width = image.shape[:2]
    suggestions: Dict[str, Any] = {}
    face_info = None
    object_info = None

    if is_employee:
        # Convert detection to FaceBox
        bbox = detection_result.face.bbox
        face = FaceBox(
            x=int(bbox[0] * width),
            y=int(bbox[1] * height),
            width=int(bbox[2] * width),
            height=int(bbox[3] * height)
        )
        # Calculate employee crops
        crops = calculate_all_crops(face, width, height)
        for preset_type, crop in crops.items():
            preset_name = preset_type.value
            suggestions[preset_name] = {
                "x": crop.x,
                "y": crop.y,
                "width": crop.width,
                "height": crop.height,
                "confidence": detection_result.face.confidence
            }
        face_info = {
            "x": face.x,
            "y": face.y,
            "width": face.width,
            "height": face.height,
            "center_x": face.center_x,
            "center_y": face.center_y
        }
    else:
        # Project crops using object detection; fallback to centered crops if none found
        roi = detector.best_object_roi(image)
        def crop_from_center(cx, cy, aspect_w, aspect_h, pad=1.2):
            ar = aspect_w / aspect_h
            # Start from roi size if available
            base_w = width * 0.4
            base_h = height * 0.4
            if roi:
                base_w = roi['width'] * pad
                base_h = roi['height'] * pad
            # Enforce aspect by expanding the smaller dimension
            cand_w = max(base_w, base_h * ar)
            cand_h = max(base_h, cand_w / ar)
            cand_w = min(cand_w, width)
            cand_h = min(cand_h, height)
            x = int(max(0, min(cx - cand_w / 2, width - cand_w)))
            y = int(max(0, min(cy - cand_h / 2, height - cand_h)))
            return {
                "x": x,
                "y": y,
                "width": int(cand_w),
                "height": int(cand_h),
                "confidence": float(roi['score']) if roi else 0.0
            }
        if roi:
            cx = roi['x'] + roi['width'] // 2
            cy = roi['y'] + roi['height'] // 2
            object_info = {
                "x": roi['x'],
                "y": roi['y'],
                "width": roi['width'],
                "height": roi['height'],
                "score": roi['score'],
                "category": roi.get('category', 'object')
            }
        else:
            # Fallback to image center
            cx, cy = width // 2, height // 2
        # Generate project preset crops
        suggestions['proj_header'] = crop_from_center(cx, cy, 16, 9, pad=1.25)
        suggestions['proj_thumbnail'] = crop_from_center(cx, cy, 1, 1, pad=1.15)
        suggestions['proj_description'] = crop_from_center(cx, cy, 3, 2, pad=1.20)
    
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
        "object_detection": object_info,
        "crop_suggestions": suggestions,
        "confidence": (detection_result.face.confidence if is_employee else (object_info or {}).get('score', 0.0)),
        "message": "Crop suggestions calculated using MediaPipe detection"
    }
