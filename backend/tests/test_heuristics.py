"""
Tests for the heuristics learning system.
"""

import pytest
import tempfile
import os
from PIL import Image
import numpy as np

from services.heuristics import (
    HeuristicsDB,
    EMACalculator,
    FeatureExtractor,
    HeuristicsManager
)


class TestHeuristicsDB:
    """Test database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = HeuristicsDB(db_path)
        yield db
        db.close()
        os.unlink(db_path)
    
    def test_database_initialization(self, temp_db):
        """Test database tables are created correctly."""
        stats = temp_db.get_statistics()
        assert stats['parameter_count'] == 0
        assert stats['sample_count'] == 0
    
    def test_ema_parameter_update(self, temp_db):
        """Test EMA parameter updates."""
        # First update
        temp_db.update_ema_parameter(
            'portrait', 'medium', 'center_x_offset', 0.1, alpha=0.2
        )
        
        params = temp_db.get_ema_parameters('portrait', 'medium')
        assert 'center_x_offset' in params
        assert params['center_x_offset'] == 0.1
        
        # Second update - should apply EMA
        temp_db.update_ema_parameter(
            'portrait', 'medium', 'center_x_offset', 0.2, alpha=0.2
        )
        
        params = temp_db.get_ema_parameters('portrait', 'medium')
        expected = 0.1 * 0.8 + 0.2 * 0.2  # EMA calculation
        assert abs(params['center_x_offset'] - expected) < 0.001
    
    def test_sample_storage(self, temp_db):
        """Test storing and retrieving samples."""
        temp_db.add_sample(
            image_hash='test_hash',
            original_dimensions=(1000, 1500),
            face_detected=True,
            pose_detected=False,
            aspect_class='portrait',
            zoom_level='medium',
            initial_crop={'x': 100, 'y': 200, 'width': 800, 'height': 1000},
            final_crop={'x': 110, 'y': 210, 'width': 790, 'height': 990},
            features={'brightness_mean': 0.5}
        )
        
        samples = temp_db.get_samples('portrait', 'medium')
        assert len(samples) == 1
        assert samples[0]['image_hash'] == 'test_hash'
        assert samples[0]['face_detected'] == True
        assert samples[0]['features']['brightness_mean'] == 0.5
    
    def test_cleanup_old_samples(self, temp_db):
        """Test cleanup of old samples."""
        # Add a sample
        temp_db.add_sample(
            image_hash='old_sample',
            original_dimensions=(1000, 1000),
            face_detected=False,
            pose_detected=False,
            aspect_class='square',
            zoom_level='wide',
            initial_crop={'x': 0, 'y': 0, 'width': 1000, 'height': 1000},
            final_crop={'x': 0, 'y': 0, 'width': 1000, 'height': 1000},
            features={}
        )
        
        # Cleanup with 0 days to keep (should delete all)
        deleted = temp_db.cleanup_old_samples(days_to_keep=0)
        assert deleted == 1
        
        samples = temp_db.get_samples()
        assert len(samples) == 0


class TestEMACalculator:
    """Test EMA calculation logic."""
    
    def test_ema_calculation(self):
        """Test basic EMA calculation."""
        calc = EMACalculator(alpha=0.1)
        
        # Single update
        result = calc.calculate_ema(10.0, 20.0, alpha=0.1)
        expected = 10.0 * 0.9 + 20.0 * 0.1
        assert abs(result - expected) < 0.001
    
    def test_bucket_updates(self):
        """Test bucket-based parameter updates."""
        calc = EMACalculator(alpha=0.2)
        
        # First update
        value1 = calc.update_bucket('portrait_medium', 'center_x', 0.1)
        assert value1 == 0.1  # First value is used directly
        
        # Second update
        value2 = calc.update_bucket('portrait_medium', 'center_x', 0.2)
        expected = 0.1 * 0.8 + 0.2 * 0.2
        assert abs(value2 - expected) < 0.001
    
    def test_adjustment_deltas(self):
        """Test calculation of adjustment deltas."""
        calc = EMACalculator()
        
        initial = {'x': 100, 'y': 100, 'width': 200, 'height': 300}
        final = {'x': 110, 'y': 90, 'width': 180, 'height': 320}
        dims = (1000, 1000)
        
        deltas = calc.calculate_adjustment_deltas(initial, final, dims)
        
        # Check center offset calculations
        assert 'center_x_offset' in deltas
        assert 'center_y_offset' in deltas
        assert 'width_scale' in deltas
        assert abs(deltas['width_scale'] - 0.9) < 0.001  # 180/200
    
    def test_apply_heuristics(self):
        """Test applying learned heuristics to a crop."""
        calc = EMACalculator()
        
        # Set up learned parameters
        calc.update_bucket('portrait_medium', 'center_x_offset', 0.05)
        calc.update_bucket('portrait_medium', 'center_y_offset', -0.02)
        calc.update_bucket('portrait_medium', 'width_scale', 1.1)
        calc.update_bucket('portrait_medium', 'height_scale', 1.05)
        
        base_crop = {'x': 100, 'y': 200, 'width': 400, 'height': 600}
        adjusted = calc.apply_heuristics(
            base_crop, 'portrait_medium', (1000, 1500)
        )
        
        # Check adjustments were applied
        assert adjusted['width'] == int(400 * 1.1)
        assert adjusted['height'] == int(600 * 1.05)


class TestFeatureExtractor:
    """Test feature extraction."""
    
    def test_aspect_ratio_classification(self):
        """Test aspect ratio classification."""
        extractor = FeatureExtractor()
        
        assert extractor.classify_aspect_ratio(1.0) == 'square'
        assert extractor.classify_aspect_ratio(0.75) == 'portrait'
        assert extractor.classify_aspect_ratio(1.33) == 'landscape'
        assert extractor.classify_aspect_ratio(1.77) == 'wide'
    
    def test_zoom_level_classification(self):
        """Test zoom level classification."""
        extractor = FeatureExtractor()
        
        assert extractor.classify_zoom_level(face_height=0.5) == 'tight'
        assert extractor.classify_zoom_level(face_height=0.25) == 'medium'
        assert extractor.classify_zoom_level(face_height=0.05) == 'full'
    
    def test_feature_extraction(self):
        """Test feature extraction from image."""
        extractor = FeatureExtractor()
        
        # Create a test image
        image = Image.new('RGB', (800, 600), color='white')
        
        features = extractor.extract_features(image)
        
        assert features['image_width'] == 800
        assert features['image_height'] == 600
        assert features['aspect_ratio'] == 800 / 600
        assert features['face_count'] == 0
        assert features['has_face'] == False
        assert 'aspect_class' in features
        assert 'brightness_mean' in features
    
    def test_crop_normalization(self):
        """Test crop coordinate normalization."""
        extractor = FeatureExtractor()
        
        crop = {'x': 100, 'y': 200, 'width': 300, 'height': 400}
        dims = (1000, 1000)
        
        normalized = extractor.normalize_crop_coordinates(crop, dims)
        
        assert normalized['x'] == 0.1
        assert normalized['y'] == 0.2
        assert normalized['width'] == 0.3
        assert normalized['height'] == 0.4
        assert normalized['center_x'] == 0.25  # (100 + 150) / 1000
        assert normalized['center_y'] == 0.4   # (200 + 200) / 1000


class TestHeuristicsManager:
    """Test the main heuristics manager."""
    
    @pytest.fixture
    def manager(self):
        """Create a heuristics manager with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        manager = HeuristicsManager(db_path=db_path, alpha=0.2)
        yield manager
        manager.close()
        os.unlink(db_path)
    
    def test_learn_from_adjustment(self, manager):
        """Test learning from user adjustments."""
        # Create test image
        image = Image.new('RGB', (1000, 1500), color='white')
        
        initial_crop = {'x': 100, 'y': 200, 'width': 800, 'height': 1200}
        final_crop = {'x': 110, 'y': 190, 'width': 780, 'height': 1220}
        
        face_boxes = [{'x': 400, 'y': 300, 'width': 200, 'height': 250}]
        
        # Learn from adjustment
        manager.learn_from_adjustment(
            image, initial_crop, final_crop, face_boxes
        )
        
        # Check that parameters were updated
        stats = manager.get_statistics()
        assert stats['sample_count'] == 1
        assert stats['parameter_count'] > 0
    
    def test_apply_heuristics(self, manager):
        """Test applying heuristics to improve crops."""
        # Create test image
        image = Image.new('RGB', (1000, 1500), color='white')
        
        # First, learn from some adjustments
        for i in range(5):
            initial = {'x': 100, 'y': 200, 'width': 800, 'height': 1200}
            # Simulate consistent user preference for slightly offset crops
            final = {'x': 120, 'y': 180, 'width': 780, 'height': 1220}
            
            manager.learn_from_adjustment(image, initial, final)
        
        # Now apply heuristics to a new crop
        base_crop = {'x': 100, 'y': 200, 'width': 800, 'height': 1200}
        result = manager.apply_heuristics(
            image, base_crop, confidence_threshold=0.0
        )
        
        # Check that heuristics were applied
        assert 'crop' in result
        assert 'confidence' in result
        assert result['sample_count'] >= 5
    
    def test_export_import_model(self, manager):
        """Test model export and import."""
        # Add some data
        manager.db.update_ema_parameter(
            'portrait', 'medium', 'test_param', 0.5
        )
        
        # Export model
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            export_path = f.name
        
        manager.export_model(export_path)
        assert os.path.exists(export_path)
        
        # Create new manager and import
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            new_db_path = f.name
        
        new_manager = HeuristicsManager(db_path=new_db_path)
        new_manager.import_model(export_path)
        
        # Check data was imported
        params = new_manager.db.get_ema_parameters('portrait', 'medium')
        assert 'test_param' in params
        assert params['test_param'] == 0.5
        
        # Cleanup
        new_manager.close()
        os.unlink(export_path)
        os.unlink(new_db_path)