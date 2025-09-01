"""
Exponential Moving Average (EMA) calculator for heuristics learning.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np

class EMACalculator:
    """
    Implements Exponential Moving Average calculations for learning
    crop adjustment patterns over time.
    """
    
    def __init__(self, alpha: float = 0.1):
        """
        Initialize EMA calculator.
        
        Args:
            alpha: Smoothing factor (0 < alpha < 1).
                   Higher values give more weight to recent observations.
        """
        if not 0 < alpha < 1:
            raise ValueError("Alpha must be between 0 and 1")
        
        self.alpha = alpha
        self.buckets: Dict[str, Dict[str, float]] = {}
    
    def calculate_ema(
        self, 
        old_value: float, 
        new_value: float, 
        alpha: Optional[float] = None
    ) -> float:
        """
        Calculate exponential moving average.
        
        Args:
            old_value: Previous EMA value
            new_value: New observation
            alpha: Optional override for smoothing factor
            
        Returns:
            Updated EMA value
        """
        if alpha is None:
            alpha = self.alpha
        
        return (1 - alpha) * old_value + alpha * new_value
    
    def update_bucket(
        self,
        bucket_key: str,
        parameter_name: str,
        new_value: float
    ) -> float:
        """
        Update EMA for a specific bucket and parameter.
        
        Args:
            bucket_key: Key identifying the bucket (e.g., "portrait_high")
            parameter_name: Name of the parameter (e.g., "center_x_offset")
            new_value: New observation value
            
        Returns:
            Updated EMA value
        """
        if bucket_key not in self.buckets:
            self.buckets[bucket_key] = {}
        
        if parameter_name in self.buckets[bucket_key]:
            old_value = self.buckets[bucket_key][parameter_name]
            new_ema = self.calculate_ema(old_value, new_value)
        else:
            # First observation - use as initial value
            new_ema = new_value
        
        self.buckets[bucket_key][parameter_name] = new_ema
        return new_ema
    
    def get_bucket_value(
        self, 
        bucket_key: str, 
        parameter_name: str,
        default: float = 0.0
    ) -> float:
        """
        Get current EMA value for a bucket parameter.
        
        Args:
            bucket_key: Key identifying the bucket
            parameter_name: Name of the parameter
            default: Default value if not found
            
        Returns:
            Current EMA value or default
        """
        if bucket_key in self.buckets:
            return self.buckets[bucket_key].get(parameter_name, default)
        return default
    
    def create_bucket_key(
        self, 
        aspect_class: str, 
        zoom_level: str
    ) -> str:
        """
        Create a standardized bucket key.
        
        Args:
            aspect_class: Aspect ratio class (e.g., "portrait", "landscape")
            zoom_level: Zoom level (e.g., "high", "medium", "low")
            
        Returns:
            Bucket key string
        """
        return f"{aspect_class}_{zoom_level}"
    
    def calculate_adjustment_deltas(
        self,
        initial_crop: Dict[str, int],
        final_crop: Dict[str, int],
        image_dimensions: Tuple[int, int]
    ) -> Dict[str, float]:
        """
        Calculate normalized adjustment deltas between initial and final crops.
        
        Args:
            initial_crop: Initial crop coordinates
            final_crop: Final (user-adjusted) crop coordinates
            image_dimensions: Original image (width, height)
            
        Returns:
            Dictionary of normalized adjustment deltas
        """
        width, height = image_dimensions
        
        # Calculate center points
        initial_center_x = initial_crop['x'] + initial_crop['width'] / 2
        initial_center_y = initial_crop['y'] + initial_crop['height'] / 2
        final_center_x = final_crop['x'] + final_crop['width'] / 2
        final_center_y = final_crop['y'] + final_crop['height'] / 2
        
        # Normalize deltas by image dimensions
        deltas = {
            'center_x_offset': (final_center_x - initial_center_x) / width,
            'center_y_offset': (final_center_y - initial_center_y) / height,
            'width_scale': final_crop['width'] / initial_crop['width'],
            'height_scale': final_crop['height'] / initial_crop['height'],
            'x_shift': (final_crop['x'] - initial_crop['x']) / width,
            'y_shift': (final_crop['y'] - initial_crop['y']) / height
        }
        
        return deltas
    
    def apply_heuristics(
        self,
        base_crop: Dict[str, int],
        bucket_key: str,
        image_dimensions: Tuple[int, int],
        confidence_threshold: float = 0.5
    ) -> Dict[str, int]:
        """
        Apply learned heuristics to adjust base crop suggestion.
        
        Args:
            base_crop: Initial crop suggestion
            bucket_key: Bucket key for parameter lookup
            image_dimensions: Original image dimensions
            confidence_threshold: Minimum confidence to apply adjustments
            
        Returns:
            Adjusted crop coordinates
        """
        if bucket_key not in self.buckets:
            # No learned parameters - return base crop
            return base_crop
        
        width, height = image_dimensions
        params = self.buckets[bucket_key]
        
        # Calculate adjusted center position
        center_x_offset = params.get('center_x_offset', 0) * width
        center_y_offset = params.get('center_y_offset', 0) * height
        
        # Calculate adjusted dimensions
        width_scale = params.get('width_scale', 1.0)
        height_scale = params.get('height_scale', 1.0)
        
        # Apply adjustments
        adjusted_width = int(base_crop['width'] * width_scale)
        adjusted_height = int(base_crop['height'] * height_scale)
        
        # Calculate new position maintaining center adjustment
        base_center_x = base_crop['x'] + base_crop['width'] / 2
        base_center_y = base_crop['y'] + base_crop['height'] / 2
        
        new_center_x = base_center_x + center_x_offset
        new_center_y = base_center_y + center_y_offset
        
        adjusted_x = int(new_center_x - adjusted_width / 2)
        adjusted_y = int(new_center_y - adjusted_height / 2)
        
        # Ensure crop stays within image bounds
        adjusted_x = max(0, min(adjusted_x, width - adjusted_width))
        adjusted_y = max(0, min(adjusted_y, height - adjusted_height))
        adjusted_width = min(adjusted_width, width - adjusted_x)
        adjusted_height = min(adjusted_height, height - adjusted_y)
        
        return {
            'x': adjusted_x,
            'y': adjusted_y,
            'width': adjusted_width,
            'height': adjusted_height
        }
    
    def get_confidence_score(
        self, 
        bucket_key: str,
        min_samples: int = 10
    ) -> float:
        """
        Calculate confidence score for a bucket based on sample count.
        
        Args:
            bucket_key: Bucket key to check
            min_samples: Minimum samples needed for full confidence
            
        Returns:
            Confidence score between 0 and 1
        """
        if bucket_key not in self.buckets:
            return 0.0
        
        # This would normally check sample count from database
        # For now, return a default confidence
        # In production, this would query the database for sample_count
        return 0.5  # Placeholder - would be calculated from actual sample count
    
    def merge_buckets(
        self,
        source_key: str,
        target_key: str,
        weight: float = 0.5
    ) -> None:
        """
        Merge parameters from source bucket into target bucket.
        
        Args:
            source_key: Source bucket key
            target_key: Target bucket key
            weight: Weight for source values (0-1)
        """
        if source_key not in self.buckets:
            return
        
        if target_key not in self.buckets:
            self.buckets[target_key] = {}
        
        source_params = self.buckets[source_key]
        target_params = self.buckets[target_key]
        
        for param_name, source_value in source_params.items():
            if param_name in target_params:
                # Weighted average
                target_value = target_params[param_name]
                merged_value = weight * source_value + (1 - weight) * target_value
                target_params[param_name] = merged_value
            else:
                # Direct copy with weight adjustment
                target_params[param_name] = source_value * weight
    
    def export_state(self) -> Dict[str, Dict[str, float]]:
        """Export current EMA state."""
        return self.buckets.copy()
    
    def import_state(self, state: Dict[str, Dict[str, float]]) -> None:
        """Import EMA state."""
        self.buckets = state.copy()
    
    def reset_bucket(self, bucket_key: str) -> None:
        """Reset a specific bucket."""
        if bucket_key in self.buckets:
            del self.buckets[bucket_key]
    
    def reset_all(self) -> None:
        """Reset all buckets."""
        self.buckets = {}