"""
File handling utilities
"""

import os
import hashlib
from pathlib import Path
from typing import Optional


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if not"""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def generate_file_hash(content: bytes) -> str:
    """Generate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()


def is_valid_image_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """Check if file has valid image extension"""
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove path components
    filename = os.path.basename(filename)
    # Replace spaces and special characters
    filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
    return filename


def get_mime_type(extension: str) -> str:
    """Get MIME type from file extension"""
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    return mime_types.get(extension, "application/octet-stream")