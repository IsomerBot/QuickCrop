"""
Tests for enhanced storage manager.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from services.storage_manager import (
    EnhancedStorageManager,
    DuplicateHandling,
    StorageStats
)


class TestEnhancedStorageManager:
    """Test enhanced storage management functionality."""
    
    @pytest.fixture
    async def storage_manager(self):
        """Create a storage manager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = EnhancedStorageManager(base_path=tmpdir)
            yield manager
    
    @pytest.mark.asyncio
    async def test_directory_structure_creation(self, storage_manager):
        """Test that all required directories are created."""
        assert storage_manager.dirs['originals'].exists()
        assert storage_manager.dirs['output'].exists()
        assert storage_manager.dirs['model'].exists()
        assert storage_manager.dirs['temp'].exists()
        assert storage_manager.dirs['archive'].exists()
    
    def test_unicode_filename_sanitization(self, storage_manager):
        """Test Unicode filename handling."""
        # Test various Unicode cases
        test_cases = [
            ("普通话文件.png", "普通话文件.png"),  # Chinese
            ("файл.jpg", "файл.jpg"),  # Cyrillic
            ("αρχείο.pdf", "αρχείο.pdf"),  # Greek
            ("ملف.doc", "ملف.doc"),  # Arabic
            ("emoji😀file.txt", "emoji😀file.txt"),  # Emoji
            ("bad<>:file.txt", "bad___file.txt"),  # Invalid chars
            ("   spaces   .txt", "spaces.txt"),  # Leading/trailing spaces
            ("." * 100 + ".txt", "_" * 235 + ".txt"),  # Too long
        ]
        
        for input_name, expected_pattern in test_cases:
            result = storage_manager.sanitize_unicode_filename(input_name)
            assert len(result) <= 255
            assert '..' not in result
            assert result != ""
    
    def test_ascii_fallback(self, storage_manager):
        """Test ASCII fallback for problematic filenames."""
        # Test ASCII fallback
        result = storage_manager._ascii_fallback("完全不是ASCII")
        assert result != ""
        assert all(ord(c) < 128 for c in result)
        
        # Test empty fallback
        result = storage_manager._ascii_fallback("")
        assert result.startswith("file_")
    
    @pytest.mark.asyncio
    async def test_save_original(self, storage_manager):
        """Test saving original files."""
        content = b"test file content"
        filename = "test_image.png"
        employee = "John Doe"
        
        file_id, file_path = await storage_manager.save_original(
            content, filename, employee, {"extra": "metadata"}
        )
        
        assert file_id != ""
        assert file_path.exists()
        assert "John_Doe" in str(file_path)
        
        # Check metadata was saved
        meta_path = file_path.with_suffix('.meta.json')
        assert meta_path.exists()
        
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
            assert metadata['original_filename'] == filename
            assert metadata['employee_name'] == employee
            assert metadata['extra'] == "metadata"
    
    @pytest.mark.asyncio
    async def test_save_output(self, storage_manager):
        """Test saving output files."""
        content = b"processed image data"
        
        # Test with suffix handling
        path1 = await storage_manager.save_output(
            content, "张三", "headshot", "file123",
            DuplicateHandling.SUFFIX
        )
        
        assert path1.exists()
        assert "张三" in str(path1)
        
        # Test duplicate handling with suffix
        path2 = await storage_manager.save_output(
            content, "张三", "headshot", "file123",
            DuplicateHandling.SUFFIX
        )
        
        assert path2.exists()
        assert path2 != path1
        assert "_1" in str(path2) or "_2" in str(path2)
        
        # Test overwrite
        path3 = await storage_manager.save_output(
            content, "张三", "headshot", "file123",
            DuplicateHandling.OVERWRITE
        )
        
        assert path3 == path1  # Should overwrite first file
    
    @pytest.mark.asyncio
    async def test_save_model(self, storage_manager):
        """Test saving model files."""
        model_data = b"model binary data"
        
        # Save with version
        path1 = await storage_manager.save_model(
            model_data, "heuristics", "1.0"
        )
        
        assert path1.exists()
        assert "heuristics_v1.0.model" in path1.name
        
        # Check latest symlink
        latest_path = storage_manager.dirs['model'] / "heuristics_latest.model"
        assert latest_path.is_symlink() or latest_path.exists()
    
    @pytest.mark.asyncio
    async def test_list_files(self, storage_manager):
        """Test file listing functionality."""
        # Create some test files
        test_files = [
            ("test1.png", b"content1", "Employee A"),
            ("test2.jpg", b"content2", "Employee B"),
            ("test3.pdf", b"content3", "Employee A"),
        ]
        
        for filename, content, employee in test_files:
            await storage_manager.save_original(content, filename, employee)
        
        # List all originals
        all_files = await storage_manager.list_files('originals')
        assert len(all_files) >= 3
        
        # List with employee filter
        employee_files = await storage_manager.list_files(
            'originals', employee_name="Employee A"
        )
        assert len(employee_files) == 2
        
        # List with pattern
        png_files = await storage_manager.list_files(
            'originals', pattern="**/*.png"
        )
        assert any('test1.png' in f['name'] for f in png_files)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, storage_manager):
        """Test cleaning up old files."""
        # Create old file
        old_file = storage_manager.dirs['temp'] / "old_file.txt"
        old_file.write_text("old content")
        
        # Modify its timestamp to be old
        old_time = (datetime.now() - timedelta(days=40)).timestamp()
        os.utime(old_file, (old_time, old_time))
        
        # Create recent file
        new_file = storage_manager.dirs['temp'] / "new_file.txt"
        new_file.write_text("new content")
        
        # Cleanup files older than 30 days
        deleted, freed = await storage_manager.cleanup_old_files(
            'temp', days_old=30, dry_run=False
        )
        
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()
        
        # Test dry run
        another_old = storage_manager.dirs['temp'] / "another_old.txt"
        another_old.write_text("content")
        os.utime(another_old, (old_time, old_time))
        
        deleted_dry, freed_dry = await storage_manager.cleanup_old_files(
            'temp', days_old=30, dry_run=True
        )
        
        assert deleted_dry == 1
        assert another_old.exists()  # Should still exist after dry run
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, storage_manager):
        """Test getting storage statistics."""
        # Create some files
        await storage_manager.save_original(b"orig1", "file1.png", "Employee")
        await storage_manager.save_original(b"orig2", "file2.png")
        await storage_manager.save_output(b"out1", "Employee", "preset", "id1")
        await storage_manager.save_model(b"model", "test_model")
        
        stats = await storage_manager.get_storage_stats()
        
        assert isinstance(stats, StorageStats)
        assert stats.total_files >= 4
        assert stats.originals_count >= 2
        assert stats.outputs_count >= 1
        assert stats.model_count >= 1
        assert stats.total_size_bytes > 0
        assert stats.oldest_file is not None
        assert stats.newest_file is not None
    
    @pytest.mark.asyncio
    async def test_verify_integrity(self, storage_manager):
        """Test storage integrity verification."""
        # Create file without metadata
        no_meta = storage_manager.dirs['originals'] / "no_meta.png"
        no_meta.write_bytes(b"content")
        
        # Create orphaned metadata
        orphan = storage_manager.dirs['originals'] / "orphan.meta.json"
        orphan.write_text('{"test": "data"}')
        
        issues = await storage_manager.verify_integrity()
        
        assert str(no_meta) in issues['missing_metadata']
        assert str(orphan) in issues['orphaned_metadata']
    
    def test_get_temp_path(self, storage_manager):
        """Test getting temporary file paths."""
        path1 = storage_manager.get_temp_path("test")
        path2 = storage_manager.get_temp_path("test")
        
        assert path1 != path2  # Should be unique
        assert path1.parent == storage_manager.dirs['temp']
        assert str(path1).startswith(str(storage_manager.dirs['temp'] / "test_"))
    
    @pytest.mark.asyncio
    async def test_unicode_employee_names(self, storage_manager):
        """Test handling of Unicode employee names."""
        test_names = [
            "李明",  # Chinese
            "Müller",  # German
            "José García",  # Spanish
            "Владимир",  # Russian
            "محمد",  # Arabic
        ]
        
        for name in test_names:
            content = f"Test for {name}".encode()
            file_id, path = await storage_manager.save_original(
                content, "test.png", name
            )
            
            assert path.exists()
            
            # Should be able to list files for this employee
            files = await storage_manager.list_files(
                'originals', employee_name=name
            )
            assert len(files) > 0


import os  # Add this import for os.utime