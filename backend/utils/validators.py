"""
Comprehensive validation utilities for QuickCrop application.
"""

import re
import magic
import hashlib
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image
import unicodedata

# File validation constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MIN_FILE_SIZE = 1024  # 1KB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
    'image/bmp',
    'image/x-bmp',
}

# Image dimension constraints
MIN_IMAGE_DIMENSION = 100  # pixels
MAX_IMAGE_DIMENSION = 10000  # pixels
MIN_ASPECT_RATIO = 0.1
MAX_ASPECT_RATIO = 10

# Name validation
MAX_NAME_LENGTH = 100
SAFE_FILENAME_PATTERN = re.compile(r'^[\w\-\s]+$')
RESERVED_NAMES = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1'}  # Windows reserved


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, code: str = 'VALIDATION_ERROR', details: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def validate_file_size(file_size: int) -> bool:
    """
    Validate file size is within acceptable limits.
    
    Args:
        file_size: Size of file in bytes
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If file size is invalid
    """
    if file_size < MIN_FILE_SIZE:
        raise ValidationError(
            f"File too small. Minimum size is {MIN_FILE_SIZE/1024:.1f}KB",
            code="FILE_TOO_SMALL",
            details={"size": file_size, "min_size": MIN_FILE_SIZE}
        )
    
    if file_size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File too large. Maximum size is {MAX_FILE_SIZE/(1024*1024):.1f}MB",
            code="FILE_TOO_LARGE",
            details={"size": file_size, "max_size": MAX_FILE_SIZE}
        )
    
    return True


def validate_file_extension(filename: str) -> str:
    """
    Validate and return file extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Lowercase extension with dot
        
    Raises:
        ValidationError: If extension is not allowed
    """
    path = Path(filename)
    extension = path.suffix.lower()
    
    if not extension:
        raise ValidationError(
            "File has no extension",
            code="NO_EXTENSION",
            details={"filename": filename}
        )
    
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type '{extension}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            code="INVALID_EXTENSION",
            details={"extension": extension, "allowed": list(ALLOWED_EXTENSIONS)}
        )
    
    return extension


def validate_mime_type(file_path: str) -> str:
    """
    Validate MIME type using python-magic.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected MIME type
        
    Raises:
        ValidationError: If MIME type is not allowed
    """
    try:
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(file_path)
        
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Invalid file type detected: {detected_mime}",
                code="INVALID_MIME_TYPE",
                details={"detected": detected_mime, "allowed": list(ALLOWED_MIME_TYPES)}
            )
        
        return detected_mime
        
    except Exception as e:
        raise ValidationError(
            f"Could not determine file type: {str(e)}",
            code="MIME_CHECK_FAILED",
            details={"error": str(e)}
        )


def validate_image_dimensions(image_path: str) -> Tuple[int, int]:
    """
    Validate image dimensions are within acceptable limits.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (width, height)
        
    Raises:
        ValidationError: If dimensions are invalid
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Check minimum dimensions
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                raise ValidationError(
                    f"Image too small. Minimum dimension is {MIN_IMAGE_DIMENSION}px",
                    code="IMAGE_TOO_SMALL",
                    details={"width": width, "height": height, "min": MIN_IMAGE_DIMENSION}
                )
            
            # Check maximum dimensions
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise ValidationError(
                    f"Image too large. Maximum dimension is {MAX_IMAGE_DIMENSION}px",
                    code="IMAGE_TOO_LARGE",
                    details={"width": width, "height": height, "max": MAX_IMAGE_DIMENSION}
                )
            
            # Check aspect ratio
            aspect_ratio = width / height
            if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
                raise ValidationError(
                    f"Invalid aspect ratio: {aspect_ratio:.2f}",
                    code="INVALID_ASPECT_RATIO",
                    details={
                        "aspect_ratio": aspect_ratio,
                        "min": MIN_ASPECT_RATIO,
                        "max": MAX_ASPECT_RATIO
                    }
                )
            
            return width, height
            
    except Image.UnidentifiedImageError:
        raise ValidationError(
            "File is not a valid image or is corrupted",
            code="INVALID_IMAGE",
            details={"path": image_path}
        )
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            f"Error processing image: {str(e)}",
            code="IMAGE_PROCESSING_ERROR",
            details={"error": str(e)}
        )


def sanitize_filename(filename: str, fallback: str = "unnamed") -> str:
    """
    Sanitize filename for safe filesystem storage.
    
    Args:
        filename: Original filename
        fallback: Fallback name if sanitization fails
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove path components
    name = Path(filename).name
    
    # Split name and extension
    stem = Path(name).stem
    extension = Path(name).suffix
    
    # Handle Unicode - normalize and convert to ASCII
    stem = unicodedata.normalize('NFKD', stem)
    stem = stem.encode('ascii', 'ignore').decode('ascii')
    
    # Remove unsafe characters
    stem = re.sub(r'[^\w\s\-.]', '', stem)
    stem = re.sub(r'\s+', '_', stem)  # Replace spaces with underscores
    stem = stem.strip('._-')  # Remove leading/trailing special chars
    
    # Limit length
    if len(stem) > MAX_NAME_LENGTH:
        stem = stem[:MAX_NAME_LENGTH]
    
    # Use fallback if empty
    if not stem:
        stem = fallback
    
    # Check for reserved names (Windows)
    if stem.upper() in RESERVED_NAMES:
        stem = f"{stem}_file"
    
    return f"{stem}{extension}"


def sanitize_employee_name(name: str) -> str:
    """
    Sanitize employee name for use in filenames and folders.
    
    Args:
        name: Employee name
        
    Returns:
        Sanitized name
        
    Raises:
        ValidationError: If name is invalid
    """
    if not name or not name.strip():
        raise ValidationError(
            "Employee name cannot be empty",
            code="EMPTY_NAME"
        )
    
    # Normalize Unicode
    normalized = unicodedata.normalize('NFKD', name)
    
    # Convert to ASCII with fallback
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
    
    # If nothing left after ASCII conversion, transliterate
    if not ascii_name.strip():
        # Keep alphanumeric and spaces from original
        ascii_name = ''.join(c if c.isalnum() or c.isspace() else '' for c in name)
    
    # Clean up
    cleaned = re.sub(r'[^\w\s\-]', '', ascii_name)
    cleaned = re.sub(r'\s+', '_', cleaned)
    cleaned = cleaned.strip('._-')
    
    if not cleaned:
        raise ValidationError(
            "Employee name contains no valid characters",
            code="INVALID_NAME",
            details={"original": name}
        )
    
    # Limit length
    if len(cleaned) > MAX_NAME_LENGTH:
        cleaned = cleaned[:MAX_NAME_LENGTH]
    
    return cleaned.lower()


def validate_crop_area(crop_area: Dict[str, float], image_width: int, image_height: int) -> bool:
    """
    Validate crop area is within image bounds.
    
    Args:
        crop_area: Dictionary with x, y, width, height
        image_width: Original image width
        image_height: Original image height
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If crop area is invalid
    """
    x = crop_area.get('x', 0)
    y = crop_area.get('y', 0)
    width = crop_area.get('width', 0)
    height = crop_area.get('height', 0)
    
    # Check all values are present and non-negative
    if any(v < 0 for v in [x, y, width, height]):
        raise ValidationError(
            "Crop area values cannot be negative",
            code="NEGATIVE_CROP_VALUES",
            details=crop_area
        )
    
    # Check crop area is within bounds
    if x + width > image_width or y + height > image_height:
        raise ValidationError(
            "Crop area extends beyond image boundaries",
            code="CROP_OUT_OF_BOUNDS",
            details={
                "crop": crop_area,
                "image": {"width": image_width, "height": image_height}
            }
        )
    
    # Check minimum crop size
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise ValidationError(
            f"Crop area too small. Minimum dimension is {MIN_IMAGE_DIMENSION}px",
            code="CROP_TOO_SMALL",
            details={"width": width, "height": height}
        )
    
    return True


def validate_export_settings(settings: Dict[str, Any]) -> bool:
    """
    Validate export settings.
    
    Args:
        settings: Export settings dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If settings are invalid
    """
    format = settings.get('format', '').lower()
    quality = settings.get('quality', 85)
    
    # Validate format
    if format not in ['jpeg', 'jpg', 'png', 'webp']:
        raise ValidationError(
            f"Invalid export format: {format}",
            code="INVALID_FORMAT",
            details={"format": format, "allowed": ['jpeg', 'png', 'webp']}
        )
    
    # Validate quality for lossy formats
    if format in ['jpeg', 'jpg', 'webp']:
        if not isinstance(quality, (int, float)) or quality < 1 or quality > 100:
            raise ValidationError(
                "Quality must be between 1 and 100",
                code="INVALID_QUALITY",
                details={"quality": quality}
            )
    
    # Validate employee name if present
    if 'employeeName' in settings:
        try:
            sanitize_employee_name(settings['employeeName'])
        except ValidationError:
            raise
    
    return True


def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file for integrity checking.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        
    Returns:
        Hex digest of the file hash
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def validate_request_rate(client_id: str, max_requests: int = 10, window: int = 60) -> bool:
    """
    Validate request rate for rate limiting.
    This is a placeholder - actual implementation would use Redis or similar.
    
    Args:
        client_id: Client identifier (IP or user ID)
        max_requests: Maximum requests allowed
        window: Time window in seconds
        
    Returns:
        True if within rate limit
    """
    # TODO: Implement actual rate limiting with Redis
    return True