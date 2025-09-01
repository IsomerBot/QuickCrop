"""
Enhanced storage and file system management with advanced features.
"""

import os
import shutil
import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import unicodedata
import re
import hashlib
import json
import logging
from dataclasses import dataclass
from enum import Enum

from core.config import settings
from utils.file_utils import ensure_directory, generate_file_hash, sanitize_filename

logger = logging.getLogger(__name__)


class DuplicateHandling(Enum):
    """Options for handling duplicate files."""
    OVERWRITE = "overwrite"
    SUFFIX = "suffix"
    SKIP = "skip"


@dataclass
class StorageStats:
    """Storage statistics."""
    total_files: int
    total_size_bytes: int
    originals_count: int
    outputs_count: int
    model_count: int
    oldest_file: Optional[datetime]
    newest_file: Optional[datetime]
    
    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)
    
    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 * 1024 * 1024)


class EnhancedStorageManager:
    """
    Enhanced storage manager with organized directory structure,
    Unicode handling, and maintenance routines.
    """
    
    def __init__(self, base_path: str = "data"):
        """
        Initialize storage manager.
        
        Args:
            base_path: Base directory for all storage
        """
        self.base_path = Path(base_path)
        
        # Define directory structure
        self.dirs = {
            'originals': self.base_path / 'originals',
            'output': self.base_path / 'output',
            'model': self.base_path / 'model',
            'temp': self.base_path / 'temp',
            'archive': self.base_path / 'archive'
        }
        
        # Create all directories
        for dir_path in self.dirs.values():
            ensure_directory(dir_path)
        
        # Configuration
        self.max_filename_length = 255
        self.timestamp_format = "%Y%m%d_%H%M%S"
    
    def sanitize_unicode_filename(self, filename: str) -> str:
        """
        Sanitize filename with proper Unicode handling and ASCII fallback.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        # Separate name and extension
        name, ext = os.path.splitext(filename)
        
        # Try to preserve Unicode characters if possible
        try:
            # Normalize Unicode
            name = unicodedata.normalize('NFKD', name)
            
            # Remove control characters and non-printable
            name = ''.join(c for c in name if unicodedata.category(c)[0] != 'C')
            
            # Replace problematic characters
            name = re.sub(r'[<>:"/\\|?*]', '_', name)
            
            # Remove leading/trailing spaces and dots
            name = name.strip(' .')
            
            # Ensure name is not empty
            if not name:
                name = 'unnamed'
            
            # Truncate if too long
            max_name_length = self.max_filename_length - len(ext) - 20  # Reserve space
            if len(name) > max_name_length:
                name = name[:max_name_length]
            
        except Exception:
            # ASCII fallback
            name = self._ascii_fallback(name)
        
        return name + ext
    
    def _ascii_fallback(self, text: str) -> str:
        """
        Convert text to ASCII-safe string.
        
        Args:
            text: Original text
            
        Returns:
            ASCII-safe string
        """
        # Try to transliterate to ASCII
        try:
            ascii_text = unicodedata.normalize('NFKD', text)
            ascii_text = ascii_text.encode('ascii', 'ignore').decode('ascii')
        except:
            ascii_text = ""
        
        # Clean up
        ascii_text = re.sub(r'[^a-zA-Z0-9._-]', '_', ascii_text)
        ascii_text = re.sub(r'_+', '_', ascii_text)
        ascii_text = ascii_text.strip('_')
        
        # Ensure not empty
        if not ascii_text:
            ascii_text = f"file_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        
        return ascii_text
    
    async def save_original(
        self,
        content: bytes,
        filename: str,
        employee_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Path]:
        """
        Save original uploaded file with timestamp prefix.
        
        Args:
            content: File content
            filename: Original filename
            employee_name: Optional employee name for categorization
            metadata: Optional metadata to save alongside
            
        Returns:
            Tuple of (file_id, file_path)
        """
        # Generate file ID
        file_id = generate_file_hash(content)
        
        # Create timestamp prefix
        timestamp = datetime.now().strftime(self.timestamp_format)
        
        # Sanitize filename
        safe_filename = self.sanitize_unicode_filename(filename)
        
        # Build path
        if employee_name:
            employee_dir = self.sanitize_unicode_filename(employee_name)
            dir_path = self.dirs['originals'] / employee_dir
            ensure_directory(dir_path)
        else:
            dir_path = self.dirs['originals']
        
        file_path = dir_path / f"{timestamp}_{file_id[:8]}_{safe_filename}"
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Save metadata if provided
        if metadata:
            meta_path = file_path.with_suffix('.meta.json')
            async with aiofiles.open(meta_path, 'w') as f:
                await f.write(json.dumps({
                    'file_id': file_id,
                    'original_filename': filename,
                    'timestamp': timestamp,
                    'employee_name': employee_name,
                    **metadata
                }, indent=2))
        
        logger.info(f"Saved original file: {file_path}")
        return file_id, file_path
    
    async def save_output(
        self,
        content: bytes,
        employee_name: str,
        preset_name: str,
        original_file_id: str,
        duplicate_handling: DuplicateHandling = DuplicateHandling.SUFFIX
    ) -> Path:
        """
        Save processed output file in organized structure.
        
        Args:
            content: Processed file content
            employee_name: Employee name for directory
            preset_name: Preset used for processing
            original_file_id: ID of original file
            duplicate_handling: How to handle duplicates
            
        Returns:
            Path to saved file
        """
        # Create employee directory
        employee_dir = self.sanitize_unicode_filename(employee_name)
        output_dir = self.dirs['output'] / employee_dir
        ensure_directory(output_dir)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d")
        base_filename = f"{employee_dir}_{preset_name}_{timestamp}"
        extension = ".png"
        
        file_path = output_dir / f"{base_filename}{extension}"
        
        # Handle duplicates
        if file_path.exists():
            if duplicate_handling == DuplicateHandling.OVERWRITE:
                # Overwrite existing
                pass
            elif duplicate_handling == DuplicateHandling.SUFFIX:
                # Add suffix
                counter = 1
                while file_path.exists():
                    file_path = output_dir / f"{base_filename}_{counter}{extension}"
                    counter += 1
            elif duplicate_handling == DuplicateHandling.SKIP:
                # Skip saving
                logger.info(f"Skipping duplicate file: {file_path}")
                return file_path
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Save processing metadata
        meta_path = file_path.with_suffix('.meta.json')
        async with aiofiles.open(meta_path, 'w') as f:
            await f.write(json.dumps({
                'original_file_id': original_file_id,
                'employee_name': employee_name,
                'preset_name': preset_name,
                'processed_at': datetime.now().isoformat(),
                'file_size': len(content)
            }, indent=2))
        
        logger.info(f"Saved output file: {file_path}")
        return file_path
    
    async def save_model(
        self,
        content: bytes,
        model_name: str,
        version: Optional[str] = None
    ) -> Path:
        """
        Save model or heuristics data.
        
        Args:
            content: Model data
            model_name: Name of the model
            version: Optional version string
            
        Returns:
            Path to saved model
        """
        # Create versioned filename
        if version:
            filename = f"{model_name}_v{version}.model"
        else:
            timestamp = datetime.now().strftime(self.timestamp_format)
            filename = f"{model_name}_{timestamp}.model"
        
        file_path = self.dirs['model'] / filename
        
        # Save model
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Create symlink to latest
        latest_path = self.dirs['model'] / f"{model_name}_latest.model"
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(file_path.name)
        
        logger.info(f"Saved model: {file_path}")
        return file_path
    
    async def list_files(
        self,
        directory: str,
        pattern: Optional[str] = None,
        employee_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List files in a directory with optional filtering.
        
        Args:
            directory: Directory name ('originals', 'output', etc.)
            pattern: Optional glob pattern
            employee_name: Optional employee name filter
            
        Returns:
            List of file information dictionaries
        """
        if directory not in self.dirs:
            raise ValueError(f"Unknown directory: {directory}")
        
        dir_path = self.dirs[directory]
        
        # Add employee subdirectory if specified
        if employee_name:
            dir_path = dir_path / self.sanitize_unicode_filename(employee_name)
            if not dir_path.exists():
                return []
        
        # Get files
        if pattern:
            files = list(dir_path.glob(pattern))
        else:
            files = [f for f in dir_path.iterdir() if f.is_file() and not f.name.endswith('.meta.json')]
        
        # Build file info
        file_info = []
        for file_path in files:
            stat = file_path.stat()
            
            # Load metadata if available
            meta_path = file_path.with_suffix('.meta.json')
            metadata = {}
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                except:
                    pass
            
            file_info.append({
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'metadata': metadata
            })
        
        # Sort by modified time (newest first)
        file_info.sort(key=lambda x: x['modified'], reverse=True)
        
        return file_info
    
    async def cleanup_old_files(
        self,
        directory: str,
        days_old: int,
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """
        Clean up old files from a directory.
        
        Args:
            directory: Directory to clean
            days_old: Delete files older than this many days
            dry_run: If True, only simulate deletion
            
        Returns:
            Tuple of (files_deleted, bytes_freed)
        """
        if directory not in self.dirs:
            raise ValueError(f"Unknown directory: {directory}")
        
        dir_path = self.dirs[directory]
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        files_deleted = 0
        bytes_freed = 0
        
        # Find old files
        for file_path in dir_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            stat = file_path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            if modified < cutoff_date:
                bytes_freed += stat.st_size
                files_deleted += 1
                
                if not dry_run:
                    try:
                        file_path.unlink()
                        logger.info(f"Deleted old file: {file_path}")
                        
                        # Also delete metadata if exists
                        meta_path = file_path.with_suffix('.meta.json')
                        if meta_path.exists():
                            meta_path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
                        files_deleted -= 1
                        bytes_freed -= stat.st_size
        
        logger.info(f"Cleanup: {'Would delete' if dry_run else 'Deleted'} {files_deleted} files, "
                   f"freeing {bytes_freed / (1024*1024):.2f} MB")
        
        return files_deleted, bytes_freed
    
    async def archive_files(
        self,
        directory: str,
        days_old: int,
        compress: bool = True
    ) -> Path:
        """
        Archive old files to a tar archive.
        
        Args:
            directory: Directory to archive from
            days_old: Archive files older than this many days
            compress: Whether to compress the archive
            
        Returns:
            Path to created archive
        """
        if directory not in self.dirs:
            raise ValueError(f"Unknown directory: {directory}")
        
        import tarfile
        
        dir_path = self.dirs[directory]
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Create archive name
        timestamp = datetime.now().strftime(self.timestamp_format)
        extension = '.tar.gz' if compress else '.tar'
        archive_path = self.dirs['archive'] / f"{directory}_{timestamp}{extension}"
        
        # Create archive
        mode = 'w:gz' if compress else 'w'
        with tarfile.open(archive_path, mode) as tar:
            files_archived = 0
            
            for file_path in dir_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                stat = file_path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                if modified < cutoff_date:
                    # Add to archive
                    arcname = str(file_path.relative_to(self.base_path))
                    tar.add(file_path, arcname=arcname)
                    files_archived += 1
                    
                    # Delete original
                    file_path.unlink()
                    
                    # Delete metadata if exists
                    meta_path = file_path.with_suffix('.meta.json')
                    if meta_path.exists():
                        tar.add(meta_path, arcname=str(meta_path.relative_to(self.base_path)))
                        meta_path.unlink()
        
        logger.info(f"Archived {files_archived} files to {archive_path}")
        return archive_path
    
    async def get_storage_stats(self) -> StorageStats:
        """
        Get storage statistics.
        
        Returns:
            StorageStats object
        """
        total_files = 0
        total_size = 0
        originals_count = 0
        outputs_count = 0
        model_count = 0
        oldest_file = None
        newest_file = None
        
        for dir_name, dir_path in self.dirs.items():
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                if file_path.name.endswith('.meta.json'):
                    continue
                
                stat = file_path.stat()
                total_files += 1
                total_size += stat.st_size
                
                # Count by type
                if dir_name == 'originals':
                    originals_count += 1
                elif dir_name == 'output':
                    outputs_count += 1
                elif dir_name == 'model':
                    model_count += 1
                
                # Track oldest/newest
                modified = datetime.fromtimestamp(stat.st_mtime)
                if oldest_file is None or modified < oldest_file:
                    oldest_file = modified
                if newest_file is None or modified > newest_file:
                    newest_file = modified
        
        return StorageStats(
            total_files=total_files,
            total_size_bytes=total_size,
            originals_count=originals_count,
            outputs_count=outputs_count,
            model_count=model_count,
            oldest_file=oldest_file,
            newest_file=newest_file
        )
    
    async def verify_integrity(self) -> Dict[str, List[str]]:
        """
        Verify storage integrity and find issues.
        
        Returns:
            Dictionary of issues found
        """
        issues = {
            'missing_metadata': [],
            'orphaned_metadata': [],
            'corrupted_files': [],
            'permission_errors': []
        }
        
        for dir_name, dir_path in self.dirs.items():
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Check for metadata files without data files
                if file_path.name.endswith('.meta.json'):
                    data_path = file_path.with_suffix('')
                    if not data_path.exists():
                        issues['orphaned_metadata'].append(str(file_path))
                    continue
                
                # Check for data files without metadata (optional)
                meta_path = file_path.with_suffix('.meta.json')
                if dir_name in ['originals', 'output'] and not meta_path.exists():
                    issues['missing_metadata'].append(str(file_path))
                
                # Check file readability
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1)  # Try to read first byte
                except PermissionError:
                    issues['permission_errors'].append(str(file_path))
                except Exception:
                    issues['corrupted_files'].append(str(file_path))
        
        return issues
    
    def get_temp_path(self, prefix: str = "tmp") -> Path:
        """
        Get a unique temporary file path.
        
        Args:
            prefix: Prefix for temp file
            
        Returns:
            Path to temporary file
        """
        import uuid
        filename = f"{prefix}_{uuid.uuid4().hex}"
        return self.dirs['temp'] / filename