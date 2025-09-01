"""
File storage service
"""

import os
import aiofiles
from pathlib import Path
from typing import Optional

from core.config import settings
from utils.file_utils import ensure_directory, generate_file_hash, sanitize_filename


class StorageService:
    """Service for handling file storage operations"""
    
    def __init__(self):
        self.upload_dir = ensure_directory(settings.UPLOAD_DIR)
        self.output_dir = ensure_directory(settings.OUTPUT_DIR)
        self.temp_dir = ensure_directory(settings.TEMP_DIR)
    
    async def save_upload(self, content: bytes, filename: str) -> tuple[str, str]:
        """
        Save uploaded file to storage
        Returns: (file_id, file_path)
        """
        # Generate file hash as ID
        file_id = generate_file_hash(content)
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Create file path
        file_path = self.upload_dir / f"{file_id}_{safe_filename}"
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return file_id, str(file_path)
    
    async def get_upload(self, file_id: str) -> Optional[bytes]:
        """Get uploaded file content by ID"""
        # Find file with matching ID
        for file_path in self.upload_dir.glob(f"{file_id}_*"):
            async with aiofiles.open(file_path, 'rb') as f:
                return await f.read()
        return None
    
    async def save_output(self, content: bytes, file_id: str, suffix: str = "") -> str:
        """
        Save processed output file
        Returns: file_path
        """
        filename = f"{file_id}{suffix}.jpg"
        file_path = self.output_dir / filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return str(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            Path(file_path).unlink()
            return True
        except Exception:
            return False
    
    def get_temp_path(self, filename: str) -> str:
        """Get temporary file path"""
        return str(self.temp_dir / filename)


# Singleton instance
storage_service = StorageService()