"""
Unit tests for crop processing and execution engine.
"""

import unittest
from PIL import Image
import io

from services.crop_processor import (
    ManualAdjustment, CropExecutor, ImageProcessor,
    validate_manual_adjustment, create_adjustment_from_ui
)
from services.crop_calculator import CropBox, FaceBox
from services.presets import PresetType


def create_test_image(width: int = 1000, height: int = 1000, color: str = 'white') -> Image.Image:
    """Create a test image."""
    return Image.new('RGB', (width, height), color)


def image_to_bytes(image: Image.Image, format: str = 'JPEG') -> bytes:
    """Convert PIL Image to bytes."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()


class TestManualAdjustment(unittest.TestCase):
    """Test manual adjustment functionality."""
    
    def test_apply_offset(self):
        """Test applying position offsets."""
        crop = CropBox(x=100, y=100, width=200, height=200, preset_type=PresetType.HEADSHOT)
        adjustment = ManualAdjustment(offset_x=50, offset_y=-20)
        
        adjusted = adjustment.apply_to_crop(crop, 1000, 1000)
        
        self.assertEqual(adjusted.x, 150)  # 100 + 50
        self.assertEqual(adjusted.y, 80)   # 100 - 20
        self.assertEqual(adjusted.width, 200)
        self.assertEqual(adjusted.height, 200)
    
    def test_apply_scale(self):
        """Test applying scale adjustment."""
        crop = CropBox(x=100, y=100, width=200, height=200, preset_type=PresetType.HEADSHOT)
        adjustment = ManualAdjustment(scale=1.5)
        
        adjusted = adjustment.apply_to_crop(crop, 1000, 1000)
        
        # Scaled dimensions
        self.assertEqual(adjusted.width, 300)  # 200 * 1.5
        self.assertEqual(adjusted.height, 300)  # 200 * 1.5
        
        # Position adjusted to keep centered
        self.assertEqual(adjusted.x, 50)   # 100 - (300-200)/2
        self.assertEqual(adjusted.y, 50)   # 100 - (300-200)/2
    
    def test_combined_adjustments(self):
        """Test combining scale and offset adjustments."""
        crop = CropBox(x=200, y=200, width=100, height=100, preset_type=PresetType.HEADSHOT)
        adjustment = ManualAdjustment(offset_x=20, offset_y=10, scale=2.0)
        
        adjusted = adjustment.apply_to_crop(crop, 1000, 1000)
        
        # Scale doubles size to 200x200
        self.assertEqual(adjusted.width, 200)
        self.assertEqual(adjusted.height, 200)
        
        # Position: original - scale_offset + manual_offset
        # scale_offset = (200-100)/2 = 50
        self.assertEqual(adjusted.x, 170)  # 200 - 50 + 20
        self.assertEqual(adjusted.y, 160)  # 200 - 50 + 10
    
    def test_bounds_adjustment(self):
        """Test that adjustments respect image bounds."""
        crop = CropBox(x=50, y=50, width=100, height=100, preset_type=PresetType.HEADSHOT)
        # Large offset that would push crop out of bounds
        adjustment = ManualAdjustment(offset_x=-100, offset_y=-100)
        
        adjusted = adjustment.apply_to_crop(crop, 500, 500)
        
        # Should be adjusted to fit within bounds
        self.assertGreaterEqual(adjusted.x, 0)
        self.assertGreaterEqual(adjusted.y, 0)


class TestCropExecutor(unittest.TestCase):
    """Test crop execution functionality."""
    
    def setUp(self):
        self.image = create_test_image(800, 600)
        self.executor = CropExecutor(self.image)
    
    def test_execute_crop(self):
        """Test basic crop execution."""
        crop = CropBox(x=100, y=50, width=200, height=150, preset_type=PresetType.HEADSHOT)
        
        result = self.executor.execute_crop(crop)
        
        self.assertEqual(result.size, (200, 150))
    
    def test_execute_crop_with_adjustment(self):
        """Test crop execution with manual adjustment."""
        crop = CropBox(x=100, y=100, width=200, height=200, preset_type=PresetType.HEADSHOT)
        adjustment = ManualAdjustment(offset_x=50, offset_y=0, scale=0.5)
        
        result = self.executor.execute_crop(crop, adjustment)
        
        # Scale 0.5 reduces size to 100x100
        self.assertEqual(result.size, (100, 100))
    
    def test_execute_and_resize(self):
        """Test crop and resize operation."""
        crop = CropBox(x=100, y=100, width=400, height=300, preset_type=PresetType.WEBSITE)
        target_size = (200, 250)
        
        result = self.executor.execute_and_resize(crop, target_size)
        
        self.assertEqual(result.size, target_size)
    
    def test_bounds_validation(self):
        """Test that out-of-bounds crops are adjusted."""
        # Crop that extends beyond image (image is 800x600)
        crop = CropBox(x=700, y=500, width=200, height=200, preset_type=PresetType.HEADSHOT)
        
        result = self.executor.execute_crop(crop)
        
        # Crop should be adjusted to fit within bounds
        # From x=700, max width is 100 (800-700)
        # From y=500, max height is 100 (600-500)
        # But adjust_to_bounds moves the crop to fit the requested size if possible
        # The crop will be moved to fit 200x200 if there's space
        self.assertLessEqual(result.size[0], 200)  # Should maintain width if adjusted
        self.assertLessEqual(result.size[1], 200)  # Should maintain height if adjusted


class TestImageProcessor(unittest.TestCase):
    """Test image processing functionality."""
    
    def setUp(self):
        self.test_image = create_test_image(1600, 1200, 'blue')
        self.image_bytes = image_to_bytes(self.test_image)
        self.processor = ImageProcessor(self.image_bytes)
        self.face = FaceBox(x=700, y=400, width=200, height=250)
    
    def test_process_preset_jpeg(self):
        """Test processing for a specific preset in JPEG format."""
        result = self.processor.process_preset(
            PresetType.HEADSHOT,
            self.face,
            format='JPEG'
        )
        
        # Check it's valid JPEG data
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)
        
        # Verify it's a valid image
        img = Image.open(io.BytesIO(result))
        self.assertEqual(img.format, 'JPEG')
        self.assertEqual(img.size, (2000, 2000))  # Headshot dimensions
    
    def test_process_preset_png(self):
        """Test processing for a specific preset in PNG format."""
        result = self.processor.process_preset(
            PresetType.AVATAR,
            self.face,
            format='PNG'
        )
        
        # Verify it's a valid PNG
        img = Image.open(io.BytesIO(result))
        self.assertEqual(img.format, 'PNG')
        self.assertEqual(img.size, (300, 300))  # Avatar dimensions
    
    def test_process_with_adjustment(self):
        """Test processing with manual adjustment."""
        adjustment = ManualAdjustment(offset_x=50, scale=1.2)
        
        result = self.processor.process_preset(
            PresetType.WEBSITE,
            self.face,
            adjustment=adjustment
        )
        
        # Verify result is valid
        img = Image.open(io.BytesIO(result))
        self.assertEqual(img.size, (1600, 2000))  # Website dimensions
    
    def test_process_all_presets(self):
        """Test processing all presets at once."""
        results = self.processor.process_all_presets(self.face)
        
        # Should have results for all preset types
        self.assertEqual(len(results), len(PresetType))
        
        # Verify each result
        for preset_type, image_bytes in results.items():
            self.assertIsInstance(image_bytes, bytes)
            img = Image.open(io.BytesIO(image_bytes))
            self.assertIsNotNone(img)
    
    def test_get_crop_preview(self):
        """Test preview generation."""
        preview_data = self.processor.get_crop_preview(
            PresetType.HEADSHOT,
            self.face,
            preview_width=200
        )
        
        # Check preview structure
        self.assertIn('preview', preview_data)
        self.assertIn('crop_box', preview_data)
        self.assertIn('preset', preview_data)
        self.assertIn('adjustments', preview_data)
        
        # Verify preview image
        preview_img = Image.open(io.BytesIO(preview_data['preview']))
        self.assertEqual(preview_img.width, 200)
        self.assertEqual(preview_img.height, 200)  # Square for headshot
        
        # Check metadata
        self.assertEqual(preview_data['preset']['type'], 'headshot')
        self.assertEqual(preview_data['adjustments']['scale'], 1.0)


class TestValidation(unittest.TestCase):
    """Test validation functions."""
    
    def test_validate_manual_adjustment(self):
        """Test manual adjustment validation."""
        crop = CropBox(x=100, y=100, width=200, height=200, preset_type=PresetType.HEADSHOT)
        
        # Valid adjustment
        valid_adj = ManualAdjustment(offset_x=10, scale=1.5)
        is_valid, error = validate_manual_adjustment(valid_adj, crop, 1000, 1000)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Scale too small
        small_scale = ManualAdjustment(scale=0.3)
        is_valid, error = validate_manual_adjustment(small_scale, crop, 1000, 1000)
        self.assertFalse(is_valid)
        self.assertIn("0.5", error)
        
        # Scale too large
        large_scale = ManualAdjustment(scale=3.0)
        is_valid, error = validate_manual_adjustment(large_scale, crop, 1000, 1000)
        self.assertFalse(is_valid)
        self.assertIn("2.0", error)
        
        # Would make crop too small
        tiny_crop = CropBox(x=100, y=100, width=150, height=150, preset_type=PresetType.HEADSHOT)
        shrink = ManualAdjustment(scale=0.6)
        is_valid, error = validate_manual_adjustment(shrink, tiny_crop, 1000, 1000)
        self.assertFalse(is_valid)
        self.assertIn("too small", error)
    
    def test_create_adjustment_from_ui(self):
        """Test creating adjustment from UI data."""
        ui_data = {
            'offset_x': 25,
            'offset_y': -15,
            'scale': 1.25
        }
        
        adjustment = create_adjustment_from_ui(ui_data)
        
        self.assertEqual(adjustment.offset_x, 25)
        self.assertEqual(adjustment.offset_y, -15)
        self.assertEqual(adjustment.scale, 1.25)
        
        # Test with missing values (should use defaults)
        partial_data = {'offset_x': 10}
        adjustment = create_adjustment_from_ui(partial_data)
        
        self.assertEqual(adjustment.offset_x, 10)
        self.assertEqual(adjustment.offset_y, 0)
        self.assertEqual(adjustment.scale, 1.0)


class TestRGBAHandling(unittest.TestCase):
    """Test handling of RGBA images."""
    
    def test_rgba_to_jpeg(self):
        """Test converting RGBA image to JPEG."""
        # Create RGBA image with transparency
        rgba_image = Image.new('RGBA', (500, 500), (255, 0, 0, 128))
        image_bytes = image_to_bytes(rgba_image, 'PNG')
        
        processor = ImageProcessor(image_bytes)
        face = FaceBox(x=200, y=150, width=100, height=120)
        
        # Process as JPEG (which doesn't support transparency)
        result = processor.process_preset(
            PresetType.HEADSHOT,
            face,
            format='JPEG'
        )
        
        # Should successfully convert to JPEG
        img = Image.open(io.BytesIO(result))
        self.assertEqual(img.format, 'JPEG')
        self.assertEqual(img.mode, 'RGB')  # No alpha channel


if __name__ == '__main__':
    unittest.main()