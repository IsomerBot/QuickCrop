"""
File upload endpoints
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import os
import uuid
import aiofiles
from PIL import Image
import io
import numpy as np
import cv2

from core.config import settings
from models.upload import UploadResponse, BatchUploadResponse
from services.storage import StorageService
from services.detection import DetectionService
from services.processing_queue import ProcessingQueueService

router = APIRouter()

# Initialize services
storage = StorageService()
detector = DetectionService()
processing_queue = ProcessingQueueService()


@router.post("/single", response_model=UploadResponse)
async def upload_single_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a single image file with validation and initial processing.
    
    - Validates file type and size
    - Saves file to storage
    - Detects faces in the image
    - Returns upload metadata with detection results
    """
    
    # Validate file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Validate file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
        )
    
    # Validate image can be opened
    try:
        img = Image.open(io.BytesIO(contents))
        width, height = img.size
        
        # Check minimum dimensions
        if width < 500 or height < 500:
            raise HTTPException(
                status_code=400,
                detail="Image dimensions must be at least 500x500 pixels"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file: {str(e)}"
        )
    
    # Generate unique filename and save
    temp_id = str(uuid.uuid4())
    filename = f"{temp_id}{file_extension}"
    
    # Save to storage
    file_id, file_path = await storage.save_upload(contents, filename)
    
    # Detect faces - convert bytes to numpy array first
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    detection_result = detector.detect(image)
    
    # Add to processing queue if faces detected
    if detection_result and detection_result.face:
        if background_tasks:
            # Format face detection for queue
            bbox = detection_result.face.bbox
            face_dict = {
                "x": bbox[0],
                "y": bbox[1],
                "width": bbox[2],
                "height": bbox[3]
            }
            background_tasks.add_task(
                processing_queue.add_job,
                file_id,
                face_dict
            )
    
    # Format detection result for response
    faces_detected = 1 if (detection_result and detection_result.face) else 0
    
    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        size=len(contents),
        content_type=file.content_type or "image/jpeg",
        dimensions={"width": width, "height": height},
        faces_detected=faces_detected,
        status="ready" if faces_detected > 0 else "no_faces"
    )


@router.post("/batch", response_model=BatchUploadResponse)
async def upload_batch_images(files: List[UploadFile] = File(...)):
    """Upload multiple image files"""
    
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files can be uploaded at once"
        )
    
    uploaded_files = []
    errors = []
    
    for idx, file in enumerate(files):
        try:
            # Validate file extension
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension not in settings.ALLOWED_EXTENSIONS:
                errors.append({
                    "filename": file.filename,
                    "error": f"File type {file_extension} not allowed"
                })
                continue
            
            # Read and validate file size
            contents = await file.read()
            if len(contents) > settings.MAX_UPLOAD_SIZE:
                errors.append({
                    "filename": file.filename,
                    "error": f"File size exceeds maximum allowed size"
                })
                continue
            
            # Generate unique filename
            file_id = str(uuid.uuid4())
            filename = f"{file_id}{file_extension}"
            
            # TODO: Save file to storage
            
            uploaded_files.append(
                UploadResponse(
                    file_id=file_id,
                    filename=file.filename,
                    size=len(contents),
                    content_type=file.content_type or "image/jpeg"
                )
            )
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return BatchUploadResponse(
        uploaded_files=uploaded_files,
        errors=errors,
        total=len(files),
        successful=len(uploaded_files)
    )