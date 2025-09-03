"""
Image processing endpoints for crop preview and export.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import io
import json

from models.process import ProcessRequest, ProcessResponse, CropPreset, PreviewRequest, ExportRequest
from services.storage import StorageService
from services.detection import DetectionService
from services.crop_processor import ImageProcessor, ManualAdjustment, create_adjustment_from_ui
from services.crop_calculator import FaceBox
from services.presets import PresetType

router = APIRouter()

# Initialize services
storage = StorageService()
detector = DetectionService()


@router.post("/{upload_id}/preview")
async def generate_preview(
    upload_id: str,
    request: PreviewRequest = Body(...)
):
    """
    Generate preview for a specific preset with optional manual adjustments.
    
    - Loads the uploaded image
    - Applies crop with adjustments
    - Returns preview image and metadata
    """
    
    # Load image from storage
    image_data = await storage.get_upload(upload_id)
    if not image_data:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {upload_id} not found"
        )
    
    # Get stored face detection or detect again
    import numpy as np
    import cv2
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
    # Note: bbox is normalized (0-1), need to convert to pixels
    height, width = image.shape[:2]
    face = FaceBox(
        x=int(bbox[0] * width),
        y=int(bbox[1] * height),
        width=int(bbox[2] * width),
        height=int(bbox[3] * height)
    )
    
    # Create adjustment if provided
    adjustment = None
    if request.adjustments:
        adjustment = create_adjustment_from_ui(request.adjustments)
    
    # Process image
    processor = ImageProcessor(image_data)
    
    # Map preset string to PresetType
    preset_map = {
        'headshot': PresetType.HEADSHOT,
        'avatar': PresetType.AVATAR,
        'website': PresetType.WEBSITE,
        'full_body': PresetType.FULL_BODY
    }
    
    preset_type = preset_map.get(request.preset)
    if not preset_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset: {request.preset}"
        )
    
    # Generate preview
    preview_data = processor.get_crop_preview(
        preset_type,
        face,
        adjustment,
        preview_width=request.preview_width or 400
    )
    
    # Return preview image with metadata headers
    return StreamingResponse(
        io.BytesIO(preview_data['preview']),
        media_type="image/jpeg",
        headers={
            "X-Crop-Box": json.dumps(preview_data['crop_box']),
            "X-Preset-Info": json.dumps(preview_data['preset']),
            "X-Adjustments": json.dumps(preview_data['adjustments'])
        }
    )


@router.post("/{upload_id}/export")
async def export_image(
    upload_id: str,
    request: ExportRequest = Body(...)
):
    """
    Export processed image with specified preset and format.
    
    - Loads the uploaded image
    - Applies final crop processing
    - Returns processed image in requested format
    """
    
    # Load image from storage
    image_data = await storage.get_upload(upload_id)
    if not image_data:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {upload_id} not found"
        )
    
    # Attempt face detection (required for employee-only presets)
    import numpy as np
    import cv2
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    detection_result = detector.detect(image)
    height, width = image.shape[:2]
    face = None
    if detection_result and detection_result.face:
        bbox = detection_result.face.bbox
        face = FaceBox(
            x=int(bbox[0] * width),
            y=int(bbox[1] * height),
            width=int(bbox[2] * width),
            height=int(bbox[3] * height)
        )
    
    # Create adjustment if provided
    adjustment = None
    if request.adjustments:
        adjustment = create_adjustment_from_ui(request.adjustments)
    
    # Process image
    processor = ImageProcessor(image_data)
    
    # Handle single or multiple preset export
    if request.preset:
        # Single preset export
        preset_map = {
            'headshot': PresetType.HEADSHOT,
            'avatar': PresetType.AVATAR,
            'website': PresetType.WEBSITE,
            'full_body': PresetType.FULL_BODY
        }
        preset_type = preset_map.get(request.preset)
        # Handle employee presets via existing flow
        if preset_type:
            if face is None:
                raise HTTPException(status_code=400, detail="No faces detected in image")
            if request.crop_box:
                processed = processor.process_with_crop_box(
                    request.crop_box,
                    preset_type,
                    format=request.format.upper(),
                    quality=request.quality if not request.auto_optimize else None,
                    auto_optimize=request.auto_optimize
                )
            else:
                processed = processor.process_preset(
                    preset_type,
                    face,
                    adjustment,
                    format=request.format.upper(),
                    quality=request.quality if not request.auto_optimize else None,
                    auto_optimize=request.auto_optimize
                )
        else:
            # Project presets: custom sizes + crop_box required
            project_sizes = {
                'proj_header': (2560, 1440),
                'proj_thumbnail': (500, 500),
                'proj_description': (3000, 2000),
            }
            if request.preset not in project_sizes:
                raise HTTPException(status_code=400, detail=f"Invalid preset: {request.preset}")
            if not request.crop_box:
                raise HTTPException(status_code=400, detail="crop_box is required for project presets")
            processed = processor.process_with_custom_output(
                request.crop_box,
                project_sizes[request.preset],
                format=request.format.upper(),
                quality=request.quality if not request.auto_optimize else None,
                auto_optimize=request.auto_optimize
            )

        # Determine content type
        fmt = request.format.lower()
        if fmt == 'png':
            content_type = 'image/png'
        elif fmt == 'webp':
            content_type = 'image/webp'
        else:
            content_type = 'image/jpeg'
        output_id = f"{upload_id}_{request.preset}_{request.format}"
        return StreamingResponse(
            io.BytesIO(processed),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={upload_id}_{request.preset}.{request.format}",
                "X-Output-Id": output_id
            }
        )
    
    elif request.presets:
        # Multiple preset export (batch)
        results = {}
        preset_map = {
            'headshot': PresetType.HEADSHOT,
            'avatar': PresetType.AVATAR,
            'website': PresetType.WEBSITE,
            'full_body': PresetType.FULL_BODY
        }
        
        for preset_name in request.presets:
            preset_type = preset_map.get(preset_name)
            if not preset_type:
                continue
            
            # Use specific adjustment for this preset if provided
            preset_adjustment = None
            if request.preset_adjustments and preset_name in request.preset_adjustments:
                preset_adjustment = create_adjustment_from_ui(
                    request.preset_adjustments[preset_name]
                )
            elif adjustment:
                preset_adjustment = adjustment
            
            processed = processor.process_preset(
                preset_type,
                face,
                preset_adjustment,
                format=request.format.upper(),
                quality=request.quality if not request.auto_optimize else None,
                auto_optimize=request.auto_optimize
            )
            
            # Generate output ID for tracking
            output_id = f"{upload_id}_{preset_name}_{request.format}"
            
            results[preset_name] = {
                "output_id": output_id,
                "size": len(processed),
                "format": request.format
            }
        
        # For batch export, return JSON with download URLs
        return {
            "upload_id": upload_id,
            "results": results,
            "total": len(results)
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'preset' or 'presets' must be specified"
        )


@router.get("/{upload_id}/status")
async def get_processing_status(upload_id: str):
    """
    Get processing status and available exports for an upload.
    """
    
    # Check if upload exists
    exists = await storage.upload_exists(upload_id)
    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {upload_id} not found"
        )
    
    # Get all processed outputs for this upload
    outputs = await storage.get_processed_outputs(upload_id)
    
    return {
        "upload_id": upload_id,
        "status": "ready",
        "available_exports": outputs,
        "total_exports": len(outputs)
    }


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str):
    """
    Delete an upload and all its processed outputs.
    """
    
    # Check if upload exists
    exists = await storage.upload_exists(upload_id)
    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {upload_id} not found"
        )
    
    # Delete upload and outputs
    deleted = await storage.delete_upload(upload_id)
    
    return {
        "upload_id": upload_id,
        "deleted": deleted,
        "message": "Upload and all outputs deleted successfully"
    }


@router.post("/validate")
async def validate_adjustments(
    preset: str = Body(...),
    adjustments: Dict[str, Any] = Body(...),
    image_dimensions: Dict[str, int] = Body(...)
):
    """
    Validate manual adjustments for a preset.
    
    - Checks if adjustments are within valid bounds
    - Returns validation result and adjusted values
    """
    
    from services.crop_processor import validate_manual_adjustment
    from services.crop_calculator import CropBox
    
    # Map preset to type
    preset_map = {
        'headshot': PresetType.HEADSHOT,
        'avatar': PresetType.AVATAR,
        'website': PresetType.WEBSITE,
        'full_body': PresetType.FULL_BODY
    }
    
    preset_type = preset_map.get(preset)
    if not preset_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset: {preset}"
        )
    
    # Create adjustment object
    adjustment = create_adjustment_from_ui(adjustments)
    
    # Create a dummy crop box for validation
    # In real usage, this would be the calculated crop
    crop = CropBox(
        x=100,
        y=100,
        width=min(500, image_dimensions.get('width', 500)),
        height=min(500, image_dimensions.get('height', 500)),
        preset_type=preset_type
    )
    
    # Validate
    is_valid, error = validate_manual_adjustment(
        adjustment,
        crop,
        image_dimensions.get('width', 1000),
        image_dimensions.get('height', 1000)
    )
    
    return {
        "valid": is_valid,
        "error": error,
        "adjustments": {
            "offset_x": adjustment.offset_x,
            "offset_y": adjustment.offset_y,
            "scale": adjustment.scale
        }
    }
