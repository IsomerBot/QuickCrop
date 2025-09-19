"""
Unit tests for crop calculation algorithms.
"""

import unittest
from services.crop_calculator import (
    FaceBox, CropBox, HeadshotCropCalculator, WebsiteCropCalculator,
    FullBodyCropCalculator, CropCalculatorFactory, calculate_crop,
    calculate_all_crops, validate_crop_bounds
)
from services.presets import PresetType, get_preset


class TestFaceBox(unittest.TestCase):
    """Test FaceBox dataclass."""
    
    def test_face_box_properties(self):
        """Test face box center and edge calculations."""
        face = FaceBox(x=100, y=50, width=80, height=100)
        
        self.assertEqual(face.center_x, 140)  # 100 + 80/2
        self.assertEqual(face.center_y, 100)  # 50 + 100/2
        self.assertEqual(face.bottom, 150)    # 50 + 100


class TestCropBox(unittest.TestCase):
    """Test CropBox dataclass and methods."""
    
    def test_validate_bounds(self):
        """Test crop box bounds validation."""
        crop = CropBox(x=10, y=10, width=100, height=100, preset_type=PresetType.HEADSHOT)
        
        # Valid within bounds
        self.assertTrue(crop.validate_bounds(200, 200))
        
        # Invalid - extends beyond image
        self.assertFalse(crop.validate_bounds(50, 200))
        self.assertFalse(crop.validate_bounds(200, 50))
    
    def test_adjust_to_bounds(self):
        """Test crop box adjustment to fit image bounds."""
        # Crop that extends beyond image
        crop = CropBox(x=150, y=150, width=100, height=100, preset_type=PresetType.HEADSHOT)
        
        # Adjust to fit within 200x200 image
        adjusted = crop.adjust_to_bounds(200, 200)
        
        self.assertEqual(adjusted.x, 100)  # Moved left to fit
        self.assertEqual(adjusted.y, 100)  # Moved up to fit
        self.assertEqual(adjusted.width, 100)
        self.assertEqual(adjusted.height, 100)
        self.assertTrue(adjusted.validate_bounds(200, 200))
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        crop = CropBox(x=10, y=20, width=100, height=150, preset_type=PresetType.WEBSITE)
        result = crop.to_dict()
        
        self.assertEqual(result['x'], 10)
        self.assertEqual(result['y'], 20)
        self.assertEqual(result['width'], 100)
        self.assertEqual(result['height'], 150)
        self.assertEqual(result['preset_type'], 'website')


class TestHeadshotCropCalculator(unittest.TestCase):
    """Test headshot/avatar crop calculator."""
    
    def setUp(self):
        preset = get_preset(PresetType.HEADSHOT)
        self.calculator = HeadshotCropCalculator(preset)
    
    def test_square_crop(self):
        """Test that headshot crop is square."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crop = self.calculator.calculate(face, 1600, 1200)
        
        # Should be square
        self.assertEqual(crop.width, crop.height)
    
    def test_face_centering(self):
        """Test that face is properly centered in crop."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crop = self.calculator.calculate(face, 2000, 2000)
        
        # Face should be in upper portion of crop
        face_center_y = face.center_y
        crop_center_y = crop.y + crop.height // 2
        
        # Face should be above center of crop
        self.assertLess(face_center_y - crop.y, crop.height // 2)
    
    def test_bounds_adjustment(self):
        """Test crop adjustment when near image edges."""
        # Face near top-left corner
        face = FaceBox(x=50, y=50, width=100, height=120)
        crop = self.calculator.calculate(face, 800, 600)
        
        # Should be adjusted to fit within image
        self.assertGreaterEqual(crop.x, 0)
        self.assertGreaterEqual(crop.y, 0)
        self.assertLessEqual(crop.x + crop.width, 800)
        self.assertLessEqual(crop.y + crop.height, 600)


class TestWebsiteCropCalculator(unittest.TestCase):
    """Test website photo crop calculator."""
    
    def setUp(self):
        preset = get_preset(PresetType.WEBSITE)
        self.calculator = WebsiteCropCalculator(preset)
    
    def test_aspect_ratio(self):
        """Test that website crop has 4:5 aspect ratio."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crop = self.calculator.calculate(face, 2000, 2500)
        
        # Check aspect ratio (allowing small rounding error)
        aspect_ratio = crop.width / crop.height
        expected_ratio = 4 / 5
        self.assertAlmostEqual(aspect_ratio, expected_ratio, places=2)
    
    def test_portrait_orientation(self):
        """Test that crop is portrait oriented."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crop = self.calculator.calculate(face, 2000, 3000)
        
        # Height should be greater than width
        self.assertGreater(crop.height, crop.width)
    
    def test_upper_body_framing(self):
        """Test that crop includes upper body area."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crop = self.calculator.calculate(face, 2000, 3000)
        
        # Crop should extend well below face
        self.assertGreater(crop.height, face.height * 3)


class TestFullBodyCropCalculator(unittest.TestCase):
    """Test full body crop calculator."""
    
    def setUp(self):
        preset = get_preset(PresetType.FULL_BODY)
        self.calculator = FullBodyCropCalculator(preset)
    
    def test_aspect_ratio(self):
        """Test that full body crop has 17:20 aspect ratio."""
        face = FaceBox(x=400, y=200, width=150, height=180)
        crop = self.calculator.calculate(face, 3000, 4000)
        
        # Check aspect ratio
        aspect_ratio = crop.width / crop.height
        expected_ratio = 17 / 20
        self.assertAlmostEqual(aspect_ratio, expected_ratio, places=2)
    
    def test_full_figure_framing(self):
        """Test that crop is sized for full figure."""
        face = FaceBox(x=400, y=200, width=150, height=180)
        crop = self.calculator.calculate(face, 3000, 4000)
        
        # Crop should be much larger than face (for full body)
        self.assertGreater(crop.height, face.height * 6)
    
    def test_face_positioning(self):
        """Test that face is positioned in upper portion."""
        face = FaceBox(x=400, y=200, width=150, height=180)
        crop = self.calculator.calculate(face, 3000, 4000)
        
        # Face should be in upper 20% of crop
        face_position_ratio = (face.center_y - crop.y) / crop.height
        self.assertLess(face_position_ratio, 0.2)


class TestCropCalculatorFactory(unittest.TestCase):
    """Test crop calculator factory."""
    
    def test_create_calculators(self):
        """Test factory creates correct calculator types."""
        headshot_calc = CropCalculatorFactory.create(PresetType.HEADSHOT)
        self.assertIsInstance(headshot_calc, HeadshotCropCalculator)
        
        avatar_calc = CropCalculatorFactory.create(PresetType.AVATAR)
        self.assertIsInstance(avatar_calc, HeadshotCropCalculator)

        thumbnail_calc = CropCalculatorFactory.create(PresetType.THUMBNAIL)
        self.assertIsInstance(thumbnail_calc, HeadshotCropCalculator)
        
        website_calc = CropCalculatorFactory.create(PresetType.WEBSITE)
        self.assertIsInstance(website_calc, WebsiteCropCalculator)
        
        fullbody_calc = CropCalculatorFactory.create(PresetType.FULL_BODY)
        self.assertIsInstance(fullbody_calc, FullBodyCropCalculator)
    
    def test_invalid_preset_type(self):
        """Test factory raises error for invalid preset type."""
        with self.assertRaises(ValueError):
            CropCalculatorFactory.create("invalid_type")


class TestCropCalculationFunctions(unittest.TestCase):
    """Test module-level calculation functions."""
    
    def test_calculate_crop(self):
        """Test single crop calculation."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crop = calculate_crop(PresetType.HEADSHOT, face, 2000, 2000)

        self.assertIsInstance(crop, CropBox)
        self.assertEqual(crop.preset_type, PresetType.HEADSHOT)
        self.assertEqual(crop.width, crop.height)  # Square for headshot

        thumb_crop = calculate_crop(PresetType.THUMBNAIL, face, 2000, 2000)
        self.assertIsInstance(thumb_crop, CropBox)
        self.assertEqual(thumb_crop.preset_type, PresetType.THUMBNAIL)
        self.assertEqual(thumb_crop.width, thumb_crop.height)
    
    def test_calculate_all_crops(self):
        """Test calculating all crop types at once."""
        face = FaceBox(x=400, y=300, width=200, height=250)
        crops = calculate_all_crops(face, 3000, 4000)

        # Should have all preset types
        self.assertEqual(len(crops), len(PresetType))
        self.assertIn(PresetType.HEADSHOT, crops)
        self.assertIn(PresetType.AVATAR, crops)
        self.assertIn(PresetType.THUMBNAIL, crops)
        self.assertIn(PresetType.WEBSITE, crops)
        self.assertIn(PresetType.FULL_BODY, crops)
        
        # Each should be a CropBox
        for preset_type, crop in crops.items():
            self.assertIsInstance(crop, CropBox)
            self.assertEqual(crop.preset_type, preset_type)
    
    def test_validate_crop_bounds(self):
        """Test crop bounds validation."""
        # Valid crop
        valid_crop = CropBox(x=10, y=10, width=100, height=100, preset_type=PresetType.HEADSHOT)
        is_valid, error = validate_crop_bounds(valid_crop, 200, 200)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Negative position
        invalid_crop = CropBox(x=-10, y=10, width=100, height=100, preset_type=PresetType.HEADSHOT)
        is_valid, error = validate_crop_bounds(invalid_crop, 200, 200)
        self.assertFalse(is_valid)
        self.assertIn("negative", error.lower())
        
        # Extends beyond image
        invalid_crop = CropBox(x=150, y=10, width=100, height=100, preset_type=PresetType.HEADSHOT)
        is_valid, error = validate_crop_bounds(invalid_crop, 200, 200)
        self.assertFalse(is_valid)
        self.assertIn("beyond", error.lower())
        
        # Zero size
        invalid_crop = CropBox(x=10, y=10, width=0, height=100, preset_type=PresetType.HEADSHOT)
        is_valid, error = validate_crop_bounds(invalid_crop, 200, 200)
        self.assertFalse(is_valid)
        self.assertIn("positive", error.lower())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_tiny_image(self):
        """Test handling of very small images."""
        face = FaceBox(x=20, y=20, width=30, height=40)
        
        # Calculate crops for tiny 100x100 image
        crops = calculate_all_crops(face, 100, 100)
        
        # All crops should fit within image
        for crop in crops.values():
            self.assertTrue(crop.validate_bounds(100, 100))
    
    def test_large_face_small_image(self):
        """Test when face is large relative to image."""
        face = FaceBox(x=100, y=100, width=300, height=400)
        
        # Calculate crops for image barely larger than face
        crops = calculate_all_crops(face, 500, 600)
        
        # All crops should still be valid
        for crop in crops.values():
            self.assertTrue(crop.validate_bounds(500, 600))
    
    def test_face_at_edge(self):
        """Test face detection at image edges."""
        # Face at top-left corner
        face = FaceBox(x=0, y=0, width=100, height=120)
        crops = calculate_all_crops(face, 1000, 1000)
        
        for crop in crops.values():
            self.assertGreaterEqual(crop.x, 0)
            self.assertGreaterEqual(crop.y, 0)
            self.assertTrue(crop.validate_bounds(1000, 1000))
        
        # Face at bottom-right corner
        face = FaceBox(x=900, y=880, width=100, height=120)
        crops = calculate_all_crops(face, 1000, 1000)
        
        for crop in crops.values():
            self.assertTrue(crop.validate_bounds(1000, 1000))


if __name__ == '__main__':
    unittest.main()
