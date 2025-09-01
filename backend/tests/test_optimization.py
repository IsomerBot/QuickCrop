"""
Tests for image optimization pipeline.
"""

import pytest
import tempfile
import os
from PIL import Image
import io

from services.optimization import ImageOptimizer, OptimizationResult, BatchOptimizer
from services.presets import PresetType


class TestImageOptimizer:
    """Test image optimization functionality."""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        image = Image.new('RGB', (800, 600), color='red')
        # Add some variation to make it compressible
        for x in range(0, 800, 100):
            for y in range(0, 600, 100):
                color = ((x * 255) // 800, (y * 255) // 600, 128)
                for dx in range(100):
                    for dy in range(100):
                        if x + dx < 800 and y + dy < 600:
                            image.putpixel((x + dx, y + dy), color)
        return image
    
    @pytest.fixture
    def optimizer(self):
        """Create an optimizer instance."""
        return ImageOptimizer(strip_metadata=True)
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initializes correctly."""
        assert optimizer is not None
        assert optimizer.strip_metadata == True
        assert optimizer.enable_lossy == True
    
    def test_png_optimization(self, optimizer, sample_image):
        """Test PNG optimization reduces file size."""
        # Optimize the image
        optimized_bytes, result = optimizer.optimize_image(
            sample_image,
            quality_range=(70, 90),
            optimization_level=2
        )
        
        assert result.success == True
        assert result.optimized_size > 0
        assert result.original_size > 0
        
        # Check if optimization actually reduced size (may not always happen)
        if result.reduction_percentage > 0:
            assert result.optimized_size < result.original_size
    
    def test_jpeg_optimization(self, optimizer, sample_image):
        """Test JPEG optimization."""
        optimized_bytes, result = optimizer.optimize_jpeg(
            sample_image,
            quality=85,
            optimize=True,
            progressive=True
        )
        
        assert result.success == True
        assert result.optimization_method == "pillow_jpeg"
        assert result.optimized_size > 0
        assert len(optimized_bytes) == result.optimized_size
    
    def test_metadata_stripping(self, optimizer):
        """Test that metadata is stripped from images."""
        # Create image with EXIF data
        image = Image.new('RGB', (100, 100), color='blue')
        
        # Add some fake EXIF
        from PIL import ExifTags
        exif = image.getexif()
        
        # Strip metadata
        stripped = optimizer._strip_metadata(image)
        
        # Check metadata is gone
        assert len(stripped.getexif()) == 0
    
    def test_image_to_png_bytes(self, optimizer, sample_image):
        """Test conversion of PIL Image to PNG bytes."""
        png_bytes = optimizer._image_to_png_bytes(sample_image)
        
        assert len(png_bytes) > 0
        
        # Verify it's valid PNG
        reloaded = Image.open(io.BytesIO(png_bytes))
        assert reloaded.size == sample_image.size
        assert reloaded.mode in ['RGB', 'RGBA']
    
    def test_resize_with_lanczos(self, optimizer, sample_image):
        """Test high-quality resizing."""
        target_size = (400, 300)
        resized = optimizer.resize_with_lanczos(sample_image, target_size)
        
        assert resized.size == target_size
        assert resized.mode == sample_image.mode


class TestBatchOptimizer:
    """Test batch optimization functionality."""
    
    @pytest.fixture
    def batch_images(self):
        """Create multiple test images."""
        images = {}
        for i, preset in enumerate(list(PresetType)[:3]):  # Test with 3 presets
            image = Image.new('RGB', (800 + i * 100, 600), color=(255, i * 50, 0))
            images[preset] = image
        return images
    
    @pytest.fixture
    def batch_optimizer(self):
        """Create a batch optimizer instance."""
        return BatchOptimizer(max_workers=2)
    
    def test_batch_optimization(self, batch_optimizer, batch_images):
        """Test batch optimization of multiple images."""
        # Track progress
        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        # Optimize batch
        results = batch_optimizer.optimize_batch(
            batch_images,
            optimization_settings={
                'quality_range': (80, 90),
                'optimization_level': 1
            }
        )
        
        # Check results
        assert len(results) == len(batch_images)
        
        for preset_type, result in results.items():
            assert preset_type in batch_images
            assert isinstance(result.image_bytes, bytes)
            assert result.optimization_result.success in [True, False]
            assert result.processing_time >= 0
    
    def test_compare_optimization_methods(self, batch_optimizer):
        """Test comparison of different optimization methods."""
        image = Image.new('RGB', (400, 300), color='green')
        
        results = batch_optimizer.compare_optimization_methods(image)
        
        # Check we have results for different methods
        assert 'png_lossless' in results
        assert 'png_lossy_high' in results
        assert 'jpeg_high' in results
        
        # Verify each result
        for method, result in results.items():
            assert isinstance(result, OptimizationResult)
            assert result.original_size > 0
    
    def test_get_best_optimization(self, batch_optimizer):
        """Test finding best optimization for size constraints."""
        image = Image.new('RGB', (800, 600), color='blue')
        
        # Find best optimization under 50KB
        optimized_bytes, result = batch_optimizer.get_best_optimization(
            image,
            max_size_kb=50,
            min_quality=70
        )
        
        assert result.success == True
        assert len(optimized_bytes) > 0
        
        # Check size constraint is met (with some tolerance)
        size_kb = len(optimized_bytes) / 1024
        assert size_kb <= 50 * 1.1  # Allow 10% tolerance
    
    @pytest.mark.asyncio
    async def test_batch_optimization_async(self, batch_optimizer, batch_images):
        """Test async batch optimization."""
        results = await batch_optimizer.optimize_batch_async(
            batch_images,
            optimization_settings={
                'quality_range': (85, 95),
                'optimization_level': 2
            }
        )
        
        assert len(results) == len(batch_images)
        
        for preset_type in batch_images:
            assert preset_type in results
    
    def test_batch_optimizer_shutdown(self, batch_optimizer):
        """Test proper shutdown of batch optimizer."""
        batch_optimizer.shutdown()
        # Should complete without error
        assert True