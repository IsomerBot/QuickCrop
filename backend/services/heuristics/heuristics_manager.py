"""
Main heuristics manager that coordinates the learning system.
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
import logging

from .database import HeuristicsDB
from .ema_calculator import EMACalculator
from .feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

class HeuristicsManager:
    """
    Manages the complete heuristics learning pipeline.
    Coordinates between database, EMA calculations, and feature extraction.
    """
    
    def __init__(
        self,
        db_path: str = "data/model/heuristics.db",
        alpha: float = 0.1,
        min_samples_for_confidence: int = 10
    ):
        """
        Initialize heuristics manager.
        
        Args:
            db_path: Path to SQLite database
            alpha: EMA smoothing factor
            min_samples_for_confidence: Minimum samples needed for confident predictions
        """
        self.db = HeuristicsDB(db_path)
        self.ema_calculator = EMACalculator(alpha)
        self.feature_extractor = FeatureExtractor()
        self.min_samples_for_confidence = min_samples_for_confidence
        
        # Load existing parameters from database
        self._load_parameters_from_db()
    
    def _load_parameters_from_db(self):
        """Load existing EMA parameters from database into calculator."""
        try:
            # Get all unique aspect class and zoom level combinations
            stats = self.db.get_statistics()
            
            # For each combination, load parameters
            for aspect_class in stats.get('aspect_distribution', {}).keys():
                for zoom_level in stats.get('zoom_distribution', {}).keys():
                    params = self.db.get_ema_parameters(aspect_class, zoom_level)
                    
                    if params:
                        bucket_key = self.ema_calculator.create_bucket_key(
                            aspect_class, zoom_level
                        )
                        for param_name, value in params.items():
                            self.ema_calculator.update_bucket(
                                bucket_key, param_name, value
                            )
            
            logger.info(f"Loaded {len(self.ema_calculator.buckets)} parameter buckets from database")
        
        except Exception as e:
            logger.warning(f"Could not load parameters from database: {e}")
    
    def learn_from_adjustment(
        self,
        image: Image.Image,
        initial_crop: Dict[str, int],
        final_crop: Dict[str, int],
        face_boxes: Optional[List[Dict[str, int]]] = None,
        pose_keypoints: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Learn from user's crop adjustment.
        
        Args:
            image: Original image
            initial_crop: AI-suggested crop
            final_crop: User-adjusted crop
            face_boxes: Detected face bounding boxes
            pose_keypoints: Detected pose keypoints
        """
        try:
            # Extract features
            features = self.feature_extractor.extract_features(
                image, face_boxes, pose_keypoints
            )
            
            # Determine classification
            aspect_class = features['aspect_class']
            
            # Determine zoom level from face detection
            zoom_level = 'medium'  # Default
            if features.get('has_face') and features.get('dominant_face_height'):
                zoom_level = self.feature_extractor.classify_zoom_level(
                    face_area=features.get('dominant_face_area'),
                    face_height=features.get('dominant_face_height')
                )
            
            # Calculate adjustment deltas
            deltas = self.ema_calculator.calculate_adjustment_deltas(
                initial_crop, final_crop, (image.width, image.height)
            )
            
            # Create bucket key
            bucket_key = self.ema_calculator.create_bucket_key(aspect_class, zoom_level)
            
            # Update EMA parameters
            for param_name, delta_value in deltas.items():
                # Update in memory
                new_value = self.ema_calculator.update_bucket(
                    bucket_key, param_name, delta_value
                )
                
                # Update in database
                self.db.update_ema_parameter(
                    aspect_class, zoom_level, param_name, delta_value,
                    alpha=self.ema_calculator.alpha
                )
            
            # Add sample to audit trail
            image_hash = self.feature_extractor.calculate_image_hash(image)
            self.db.add_sample(
                image_hash=image_hash,
                original_dimensions=(image.width, image.height),
                face_detected=features.get('has_face', False),
                pose_detected=features.get('has_pose', False),
                aspect_class=aspect_class,
                zoom_level=zoom_level,
                initial_crop=initial_crop,
                final_crop=final_crop,
                features=features
            )
            
            logger.info(f"Learned from adjustment for {aspect_class}/{zoom_level}")
        
        except Exception as e:
            logger.error(f"Error learning from adjustment: {e}")
    
    def apply_heuristics(
        self,
        image: Image.Image,
        base_crop: Dict[str, int],
        face_boxes: Optional[List[Dict[str, int]]] = None,
        pose_keypoints: Optional[List[Dict[str, Any]]] = None,
        confidence_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Apply learned heuristics to improve crop suggestion.
        
        Args:
            image: Original image
            base_crop: Initial crop suggestion
            face_boxes: Detected face bounding boxes
            pose_keypoints: Detected pose keypoints
            confidence_threshold: Minimum confidence to apply adjustments
            
        Returns:
            Dictionary with adjusted crop and metadata
        """
        try:
            # Extract features
            features = self.feature_extractor.extract_features(
                image, face_boxes, pose_keypoints
            )
            
            # Determine classification
            aspect_class = features['aspect_class']
            
            # Determine zoom level
            zoom_level = 'medium'
            if features.get('has_face') and features.get('dominant_face_height'):
                zoom_level = self.feature_extractor.classify_zoom_level(
                    face_area=features.get('dominant_face_area'),
                    face_height=features.get('dominant_face_height')
                )
            
            # Create bucket key
            bucket_key = self.ema_calculator.create_bucket_key(aspect_class, zoom_level)
            
            # Get confidence score
            params = self.db.get_ema_parameters(aspect_class, zoom_level)
            sample_count = 0
            
            # Get sample count from database stats
            samples = self.db.get_samples(aspect_class, zoom_level, limit=1)
            if samples:
                # Estimate sample count from database
                # In production, this would be tracked more precisely
                sample_count = len(self.db.get_samples(aspect_class, zoom_level, limit=1000))
            
            confidence = min(1.0, sample_count / self.min_samples_for_confidence)
            
            # Apply heuristics if confidence is sufficient
            if confidence >= confidence_threshold and params:
                adjusted_crop = self.ema_calculator.apply_heuristics(
                    base_crop, bucket_key, (image.width, image.height), confidence
                )
                
                logger.info(f"Applied heuristics with confidence {confidence:.2f}")
                
                return {
                    'crop': adjusted_crop,
                    'confidence': confidence,
                    'aspect_class': aspect_class,
                    'zoom_level': zoom_level,
                    'adjustments_applied': True,
                    'sample_count': sample_count
                }
            else:
                logger.info(f"Confidence {confidence:.2f} below threshold, using base crop")
                
                return {
                    'crop': base_crop,
                    'confidence': confidence,
                    'aspect_class': aspect_class,
                    'zoom_level': zoom_level,
                    'adjustments_applied': False,
                    'sample_count': sample_count
                }
        
        except Exception as e:
            logger.error(f"Error applying heuristics: {e}")
            return {
                'crop': base_crop,
                'confidence': 0.0,
                'aspect_class': 'unknown',
                'zoom_level': 'medium',
                'adjustments_applied': False,
                'sample_count': 0,
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the heuristics system."""
        db_stats = self.db.get_statistics()
        
        # Add EMA calculator statistics
        db_stats['loaded_buckets'] = len(self.ema_calculator.buckets)
        db_stats['bucket_keys'] = list(self.ema_calculator.buckets.keys())
        
        # Calculate confidence scores for each bucket
        confidences = {}
        for bucket_key in self.ema_calculator.buckets.keys():
            aspect_class, zoom_level = bucket_key.split('_', 1)
            samples = self.db.get_samples(aspect_class, zoom_level, limit=1000)
            sample_count = len(samples)
            confidence = min(1.0, sample_count / self.min_samples_for_confidence)
            confidences[bucket_key] = {
                'sample_count': sample_count,
                'confidence': confidence
            }
        
        db_stats['bucket_confidences'] = confidences
        
        return db_stats
    
    def export_model(self, export_path: str) -> None:
        """
        Export the complete heuristics model.
        
        Args:
            export_path: Path to save the model
        """
        model_data = {
            'version': '1.0',
            'alpha': self.ema_calculator.alpha,
            'min_samples_for_confidence': self.min_samples_for_confidence,
            'parameters': self.db.export_params(),
            'ema_state': self.ema_calculator.export_state(),
            'statistics': self.get_statistics()
        }
        
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        
        with open(export_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        logger.info(f"Exported heuristics model to {export_path}")
    
    def import_model(self, import_path: str) -> None:
        """
        Import a heuristics model.
        
        Args:
            import_path: Path to the model file
        """
        with open(import_path, 'r') as f:
            model_data = json.load(f)
        
        # Import database parameters
        if 'parameters' in model_data:
            self.db.import_params(model_data['parameters'])
        
        # Import EMA state
        if 'ema_state' in model_data:
            self.ema_calculator.import_state(model_data['ema_state'])
        
        # Update configuration
        if 'alpha' in model_data:
            self.ema_calculator.alpha = model_data['alpha']
        
        if 'min_samples_for_confidence' in model_data:
            self.min_samples_for_confidence = model_data['min_samples_for_confidence']
        
        logger.info(f"Imported heuristics model from {import_path}")
    
    def cleanup_old_samples(self, days_to_keep: int = 30) -> int:
        """
        Clean up old samples from the database.
        
        Args:
            days_to_keep: Number of days of samples to keep
            
        Returns:
            Number of samples deleted
        """
        deleted = self.db.cleanup_old_samples(days_to_keep)
        logger.info(f"Cleaned up {deleted} old samples")
        return deleted
    
    def reset_learning(self, aspect_class: Optional[str] = None, zoom_level: Optional[str] = None):
        """
        Reset learning for specific or all buckets.
        
        Args:
            aspect_class: Optional specific aspect class
            zoom_level: Optional specific zoom level
        """
        if aspect_class and zoom_level:
            # Reset specific bucket
            bucket_key = self.ema_calculator.create_bucket_key(aspect_class, zoom_level)
            self.ema_calculator.reset_bucket(bucket_key)
            logger.info(f"Reset learning for {bucket_key}")
        else:
            # Reset all
            self.ema_calculator.reset_all()
            logger.info("Reset all learning")
    
    def close(self):
        """Clean up resources."""
        self.db.close()