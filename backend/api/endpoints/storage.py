"""
Storage management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.storage_manager import EnhancedStorageManager, DuplicateHandling

router = APIRouter()
logger = logging.getLogger(__name__)

# Global storage manager instance
storage_manager = EnhancedStorageManager()


class StorageStatsResponse(BaseModel):
    """Response model for storage statistics."""
    total_files: int
    total_size_mb: float
    total_size_gb: float
    originals_count: int
    outputs_count: int
    model_count: int
    oldest_file: Optional[datetime]
    newest_file: Optional[datetime]


class FileInfo(BaseModel):
    """File information model."""
    path: str
    name: str
    size: int
    created: datetime
    modified: datetime
    metadata: Dict[str, Any]


class CleanupResult(BaseModel):
    """Result of cleanup operation."""
    files_deleted: int
    bytes_freed: int
    mb_freed: float


class IntegrityReport(BaseModel):
    """Storage integrity report."""
    missing_metadata: List[str]
    orphaned_metadata: List[str]
    corrupted_files: List[str]
    permission_errors: List[str]
    total_issues: int


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_statistics():
    """Get comprehensive storage statistics."""
    try:
        stats = await storage_manager.get_storage_stats()
        return StorageStatsResponse(
            total_files=stats.total_files,
            total_size_mb=stats.total_size_mb,
            total_size_gb=stats.total_size_gb,
            originals_count=stats.originals_count,
            outputs_count=stats.outputs_count,
            model_count=stats.model_count,
            oldest_file=stats.oldest_file,
            newest_file=stats.newest_file
        )
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{directory}", response_model=List[FileInfo])
async def list_files(
    directory: str,
    pattern: Optional[str] = Query(None, description="Glob pattern for filtering"),
    employee_name: Optional[str] = Query(None, description="Filter by employee name")
):
    """
    List files in a specific directory.
    
    Args:
        directory: Directory name ('originals', 'output', 'model', 'temp', 'archive')
        pattern: Optional glob pattern for filtering
        employee_name: Optional employee name filter
    """
    try:
        files = await storage_manager.list_files(directory, pattern, employee_name)
        return [FileInfo(**f) for f in files]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/{directory}", response_model=CleanupResult)
async def cleanup_old_files(
    directory: str,
    days_old: int = Body(..., ge=1, le=365),
    dry_run: bool = Body(True, description="If true, only simulate deletion")
):
    """
    Clean up old files from a directory.
    
    Args:
        directory: Directory to clean
        days_old: Delete files older than this many days
        dry_run: If true, only simulate deletion
    """
    try:
        files_deleted, bytes_freed = await storage_manager.cleanup_old_files(
            directory, days_old, dry_run
        )
        
        return CleanupResult(
            files_deleted=files_deleted,
            bytes_freed=bytes_freed,
            mb_freed=bytes_freed / (1024 * 1024)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cleaning up files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archive/{directory}")
async def archive_old_files(
    directory: str,
    days_old: int = Body(..., ge=1, le=365),
    compress: bool = Body(True, description="Compress the archive")
):
    """
    Archive old files to a tar archive.
    
    Args:
        directory: Directory to archive from
        days_old: Archive files older than this many days
        compress: Whether to compress the archive
    """
    try:
        archive_path = await storage_manager.archive_files(
            directory, days_old, compress
        )
        
        return {
            "success": True,
            "archive_path": str(archive_path),
            "message": f"Files archived to {archive_path.name}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error archiving files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify", response_model=IntegrityReport)
async def verify_storage_integrity():
    """Verify storage integrity and find issues."""
    try:
        issues = await storage_manager.verify_integrity()
        
        total_issues = sum(len(v) for v in issues.values())
        
        return IntegrityReport(
            missing_metadata=issues['missing_metadata'],
            orphaned_metadata=issues['orphaned_metadata'],
            corrupted_files=issues['corrupted_files'],
            permission_errors=issues['permission_errors'],
            total_issues=total_issues
        )
    except Exception as e:
        logger.error(f"Error verifying integrity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sanitize")
async def sanitize_filename(
    filename: str = Body(..., embed=True)
):
    """
    Sanitize a filename for safe filesystem storage.
    
    Args:
        filename: Original filename to sanitize
    """
    try:
        sanitized = storage_manager.sanitize_unicode_filename(filename)
        ascii_fallback = storage_manager._ascii_fallback(filename)
        
        return {
            "original": filename,
            "sanitized": sanitized,
            "ascii_fallback": ascii_fallback,
            "length": len(sanitized),
            "is_safe": sanitized == filename
        }
    except Exception as e:
        logger.error(f"Error sanitizing filename: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/temp")
async def cleanup_temp_directory():
    """Clean up all files in the temp directory."""
    try:
        # Clean up files older than 0 days (all files)
        files_deleted, bytes_freed = await storage_manager.cleanup_old_files(
            'temp', days_old=0, dry_run=False
        )
        
        return {
            "success": True,
            "files_deleted": files_deleted,
            "mb_freed": bytes_freed / (1024 * 1024),
            "message": f"Cleaned up {files_deleted} temporary files"
        }
    except Exception as e:
        logger.error(f"Error cleaning temp directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))