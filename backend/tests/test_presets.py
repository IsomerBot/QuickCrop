"""
Unit tests for crop preset configuration system.
"""

import unittest
from services.presets import (
    PresetType, PresetConfig, get_preset, get_all_presets,
    validate_all_presets, calculate_aspect_ratio, 
    get_preset_by_dimensions, PRESETS
)


class TestPresetConfiguration(unittest.TestCase):
    """Test preset configuration system."""
    
    def test_preset_types_exist(self):
        """Test that all preset types are defined."""
        self.assertEqual(len(PresetType), 5)
        self.assertIn(PresetType.HEADSHOT, PresetType)
        self.assertIn(PresetType.AVATAR, PresetType)
        self.assertIn(PresetType.THUMBNAIL, PresetType)
        self.assertIn(PresetType.WEBSITE, PresetType)
        self.assertIn(PresetType.FULL_BODY, PresetType)
    
    def test_preset_dimensions(self):
        """Test that preset dimensions are correct."""
        headshot = get_preset(PresetType.HEADSHOT)
        self.assertEqual(headshot.dimensions, (2000, 2000))
        
        avatar = get_preset(PresetType.AVATAR)
        self.assertEqual(avatar.dimensions, (300, 300))

        thumbnail = get_preset(PresetType.THUMBNAIL)
        self.assertEqual(thumbnail.dimensions, (500, 500))

        website = get_preset(PresetType.WEBSITE)
        self.assertEqual(website.dimensions, (1600, 2000))
        
        full_body = get_preset(PresetType.FULL_BODY)
        self.assertEqual(full_body.dimensions, (3400, 4000))
    
    def test_aspect_ratios(self):
        """Test that aspect ratios are calculated correctly."""
        headshot = get_preset(PresetType.HEADSHOT)
        self.assertAlmostEqual(headshot.aspect_ratio, 1.0, places=2)
        
        avatar = get_preset(PresetType.AVATAR)
        self.assertAlmostEqual(avatar.aspect_ratio, 1.0, places=2)

        thumbnail = get_preset(PresetType.THUMBNAIL)
        self.assertAlmostEqual(thumbnail.aspect_ratio, 1.0, places=2)

        website = get_preset(PresetType.WEBSITE)
        self.assertAlmostEqual(website.aspect_ratio, 0.8, places=2)
        
        full_body = get_preset(PresetType.FULL_BODY)
        self.assertAlmostEqual(full_body.aspect_ratio, 0.85, places=2)
    
    def test_margin_configurations(self):
        """Test margin settings for each preset."""
        headshot = get_preset(PresetType.HEADSHOT)
        self.assertEqual(headshot.margin_top, 0.08)
        self.assertEqual(headshot.margin_sides, 0.1)

        thumbnail = get_preset(PresetType.THUMBNAIL)
        self.assertEqual(thumbnail.margin_top, 0.08)
        self.assertEqual(thumbnail.margin_sides, 0.1)

        website = get_preset(PresetType.WEBSITE)
        self.assertEqual(website.margin_top, 0.05)
        self.assertEqual(website.margin_sides, 0.08)
        
        full_body = get_preset(PresetType.FULL_BODY)
        self.assertEqual(full_body.margin_top, 0.05)
        self.assertEqual(full_body.margin_sides, 0.05)
    
    def test_face_positions(self):
        """Test face position settings."""
        headshot = get_preset(PresetType.HEADSHOT)
        self.assertEqual(headshot.face_position, "center")

        thumbnail = get_preset(PresetType.THUMBNAIL)
        self.assertEqual(thumbnail.face_position, "center")

        website = get_preset(PresetType.WEBSITE)
        self.assertEqual(website.face_position, "upper")
        
        full_body = get_preset(PresetType.FULL_BODY)
        self.assertEqual(full_body.face_position, "full")
    
    def test_preset_validation(self):
        """Test preset validation logic."""
        self.assertTrue(validate_all_presets())
        
        # Test individual preset validation
        for preset in PRESETS.values():
            self.assertTrue(preset.validate())
        
        # Test invalid preset
        invalid_preset = PresetConfig(
            name="Invalid",
            type=PresetType.HEADSHOT,
            output_width=-100,  # Invalid negative width
            output_height=100,
            aspect_ratio=1.0,
            crop_ratio=(1, 1),
            face_position="center",
            margin_top=0.1,
            margin_sides=0.1,
            description="Invalid preset"
        )
        self.assertFalse(invalid_preset.validate())
    
    def test_get_all_presets(self):
        """Test getting all presets."""
        all_presets = get_all_presets()
        self.assertEqual(len(all_presets), 5)
        self.assertIn(PresetType.HEADSHOT, all_presets)
        self.assertIn(PresetType.AVATAR, all_presets)
        self.assertIn(PresetType.THUMBNAIL, all_presets)
        self.assertIn(PresetType.WEBSITE, all_presets)
        self.assertIn(PresetType.FULL_BODY, all_presets)
    
    def test_calculate_aspect_ratio(self):
        """Test aspect ratio calculation."""
        self.assertAlmostEqual(calculate_aspect_ratio(100, 100), 1.0)
        self.assertAlmostEqual(calculate_aspect_ratio(400, 500), 0.8)
        self.assertAlmostEqual(calculate_aspect_ratio(1700, 2000), 0.85)
        
        with self.assertRaises(ValueError):
            calculate_aspect_ratio(100, 0)
    
    def test_get_preset_by_dimensions(self):
        """Test finding presets by dimensions."""
        self.assertEqual(
            get_preset_by_dimensions(2000, 2000),
            PresetType.HEADSHOT
        )
        self.assertEqual(
            get_preset_by_dimensions(300, 300),
            PresetType.AVATAR
        )
        self.assertEqual(
            get_preset_by_dimensions(500, 500),
            PresetType.THUMBNAIL
        )
        self.assertEqual(
            get_preset_by_dimensions(1600, 2000),
            PresetType.WEBSITE
        )
        self.assertEqual(
            get_preset_by_dimensions(3400, 4000),
            PresetType.FULL_BODY
        )
        self.assertIsNone(get_preset_by_dimensions(999, 999))
    
    def test_preset_descriptions(self):
        """Test that all presets have descriptions."""
        for preset in PRESETS.values():
            self.assertIsNotNone(preset.description)
            self.assertGreater(len(preset.description), 0)


if __name__ == '__main__':
    unittest.main()
