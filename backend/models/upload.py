"""
Upload-related Pydantic models
"""

from pydantic import BaseModel
from typing import List, Optional, Any


class UploadResponse(BaseModel):
    """Response model for single file upload"""
    file_id: str
    filename: str
    size: int
    content_type: str
    dimensions: Optional[dict[str, int]] = None
    faces_detected: Optional[int] = None
    status: Optional[str] = None  # 'ready', 'no_faces', 'error'


class BatchUploadResponse(BaseModel):
    """Response model for batch file upload"""
    uploaded_files: List[UploadResponse]
    errors: List[dict[str, Any]]
    total: int
    successful: int