"""
Feature extraction for heuristics learning system.
"""

import hashlib
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from PIL import Image

class FeatureExtractor:
    """Extracts relevant features from images for heuristic learning."""
    
    def __init__(self):
        """Initialize feature extractor."""
        self.aspect_classes = {
            'square': 1.0,
            'portrait': 0.75,
            'landscape': 1.33,
            'wide': 1.77,
            'ultrawide': 2.35
        }
        
        self.zoom_levels = {
            'tight': 0.8,    # Very close crop
            'close': 0.9,    # Close crop
            'medium': 1.0,   # Standard crop
            'wide': 1.1,     # Wide crop
            'full': 1.2      # Full body or very wide
        }
    
    def extract_features(
        self,
        image: Image.Image,
        face_boxes: Optional[List[Dict[str, int]]] = None,
        pose_keypoints: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Extract features from an image.
        
        Args:
            image: PIL Image object
            face_boxes: List of detected face bounding boxes
            pose_keypoints: List of detected pose keypoints
            
        Returns:
            Dictionary of extracted features
        """
        width, height = image.size
        
        features = {
            'image_width': width,
            'image_height': height,
            'aspect_ratio': width / height,
            'total_pixels': width * height,
            'face_count': len(face_boxes) if face_boxes else 0,
            'has_face': bool(face_boxes),
            'has_pose': bool(pose_keypoints),
        }
        
        # Face-related features
        if face_boxes:
            features.update(self._extract_face_features(face_boxes, (width, height)))
        
        # Pose-related features
        if pose_keypoints:
            features.update(self._extract_pose_features(pose_keypoints, (width, height)))
        
        # Image statistics
        features.update(self._extract_image_statistics(image))
        
        # Classification features
        features['aspect_class'] = self.classify_aspect_ratio(width / height)
        features['size_class'] = self.classify_image_size(width * height)
        
        return features
    
    def _extract_face_features(
        self, 
        face_boxes: List[Dict[str, int]], 
        image_dims: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Extract features from face detections."""
        width, height = image_dims
        
        # Calculate face areas and positions
        face_areas = []
        face_centers_x = []
        face_centers_y = []
        
        for face in face_boxes:
            face_area = face['width'] * face['height']
            face_areas.append(face_area / (width * height))  # Normalized
            
            center_x = (face['x'] + face['width'] / 2) / width
            center_y = (face['y'] + face['height'] / 2) / height
            face_centers_x.append(center_x)
            face_centers_y.append(center_y)
        
        # Find dominant face (largest)
        dominant_idx = np.argmax(face_areas)
        dominant_face = face_boxes[dominant_idx]
        
        return {
            'dominant_face_area': face_areas[dominant_idx],
            'dominant_face_x': face_centers_x[dominant_idx],
            'dominant_face_y': face_centers_y[dominant_idx],
            'dominant_face_width': dominant_face['width'] / width,
            'dominant_face_height': dominant_face['height'] / height,
            'face_spread_x': max(face_centers_x) - min(face_centers_x) if len(face_centers_x) > 1 else 0,
            'face_spread_y': max(face_centers_y) - min(face_centers_y) if len(face_centers_y) > 1 else 0,
            'average_face_area': np.mean(face_areas),
            'face_area_variance': np.var(face_areas) if len(face_areas) > 1 else 0
        }
    
    def _extract_pose_features(
        self,
        pose_keypoints: List[Dict[str, Any]],
        image_dims: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Extract features from pose detections."""
        width, height = image_dims
        
        # Simplified pose feature extraction
        # In production, this would analyze keypoint positions
        
        features = {
            'pose_count': len(pose_keypoints),
            'has_full_body': False,  # Would check if all keypoints visible
            'pose_vertical_span': 0.0,  # Would calculate from keypoints
            'pose_horizontal_span': 0.0,  # Would calculate from keypoints
            'pose_center_x': 0.5,  # Would calculate from keypoints
            'pose_center_y': 0.5   # Would calculate from keypoints
        }
        
        if pose_keypoints:
            # This would normally process actual keypoints
            # For now, return placeholder values
            features['has_full_body'] = len(pose_keypoints) > 0
            features['pose_vertical_span'] = 0.7  # Placeholder
            features['pose_horizontal_span'] = 0.4  # Placeholder
        
        return features
    
    def _extract_image_statistics(self, image: Image.Image) -> Dict[str, Any]:
        """Extract statistical features from image."""
        # Convert to grayscale for statistics
        gray = image.convert('L')
        pixels = np.array(gray)
        
        # Calculate image statistics
        return {
            'brightness_mean': np.mean(pixels) / 255.0,
            'brightness_std': np.std(pixels) / 255.0,
            'brightness_min': np.min(pixels) / 255.0,
            'brightness_max': np.max(pixels) / 255.0,
            'contrast': (np.max(pixels) - np.min(pixels)) / 255.0,
            'edge_density': self._calculate_edge_density(pixels)
        }
    
    def _calculate_edge_density(self, pixels: np.ndarray) -> float:
        """Calculate edge density using simple gradient."""
        # Simple edge detection using gradients
        dy = np.diff(pixels, axis=0)
        dx = np.diff(pixels, axis=1)
        
        # Calculate magnitude of gradients
        edge_y = np.mean(np.abs(dy)) / 255.0
        edge_x = np.mean(np.abs(dx)) / 255.0
        
        return (edge_x + edge_y) / 2
    
    def classify_aspect_ratio(self, ratio: float) -> str:
        """
        Classify aspect ratio into predefined classes.
        
        Args:
            ratio: Width / height ratio
            
        Returns:
            Aspect class name
        """
        # Find closest aspect class
        min_diff = float('inf')
        best_class = 'square'
        
        for class_name, class_ratio in self.aspect_classes.items():
            diff = abs(ratio - class_ratio)
            if diff < min_diff:
                min_diff = diff
                best_class = class_name
        
        return best_class
    
    def classify_zoom_level(
        self,
        face_area: Optional[float] = None,
        face_height: Optional[float] = None
    ) -> str:
        """
        Classify zoom level based on face size.
        
        Args:
            face_area: Normalized face area (0-1)
            face_height: Normalized face height (0-1)
            
        Returns:
            Zoom level class
        """
        if face_area is None and face_height is None:
            return 'medium'  # Default
        
        # Use face height as primary indicator
        if face_height is not None:
            if face_height > 0.4:
                return 'tight'
            elif face_height > 0.3:
                return 'close'
            elif face_height > 0.2:
                return 'medium'
            elif face_height > 0.1:
                return 'wide'
            else:
                return 'full'
        
        # Fall back to area if height not available
        if face_area > 0.15:
            return 'tight'
        elif face_area > 0.08:
            return 'close'
        elif face_area > 0.04:
            return 'medium'
        elif face_area > 0.02:
            return 'wide'
        else:
            return 'full'
    
    def classify_image_size(self, total_pixels: int) -> str:
        """
        Classify image by total pixel count.
        
        Args:
            total_pixels: Total number of pixels
            
        Returns:
            Size classification
        """
        if total_pixels < 500_000:
            return 'small'
        elif total_pixels < 2_000_000:
            return 'medium'
        elif total_pixels < 8_000_000:
            return 'large'
        else:
            return 'xlarge'
    
    def calculate_image_hash(self, image: Image.Image) -> str:
        """
        Calculate a hash for image identification.
        
        Args:
            image: PIL Image object
            
        Returns:
            SHA256 hash string
        """
        # Convert image to bytes
        img_bytes = image.tobytes()
        
        # Calculate hash
        return hashlib.sha256(img_bytes).hexdigest()
    
    def normalize_crop_coordinates(
        self,
        crop: Dict[str, int],
        image_dims: Tuple[int, int]
    ) -> Dict[str, float]:
        """
        Normalize crop coordinates relative to image dimensions.
        
        Args:
            crop: Crop coordinates (x, y, width, height)
            image_dims: Image (width, height)
            
        Returns:
            Normalized crop coordinates (0-1 range)
        """
        width, height = image_dims
        
        return {
            'x': crop['x'] / width,
            'y': crop['y'] / height,
            'width': crop['width'] / width,
            'height': crop['height'] / height,
            'center_x': (crop['x'] + crop['width'] / 2) / width,
            'center_y': (crop['y'] + crop['height'] / 2) / height
        }
    
    def denormalize_crop_coordinates(
        self,
        normalized_crop: Dict[str, float],
        image_dims: Tuple[int, int]
    ) -> Dict[str, int]:
        """
        Convert normalized crop coordinates back to pixel values.
        
        Args:
            normalized_crop: Normalized crop coordinates (0-1)
            image_dims: Image (width, height)
            
        Returns:
            Pixel crop coordinates
        """
        width, height = image_dims
        
        # Handle both center-based and corner-based coordinates
        if 'center_x' in normalized_crop:
            # Convert from center to corner
            x = int((normalized_crop['center_x'] - normalized_crop['width'] / 2) * width)
            y = int((normalized_crop['center_y'] - normalized_crop['height'] / 2) * height)
        else:
            x = int(normalized_crop['x'] * width)
            y = int(normalized_crop['y'] * height)
        
        return {
            'x': max(0, x),
            'y': max(0, y),
            'width': int(normalized_crop['width'] * width),
            'height': int(normalized_crop['height'] * height)
        }
    
    def calculate_feature_distance(
        self,
        features1: Dict[str, Any],
        features2: Dict[str, Any]
    ) -> float:
        """
        Calculate distance between two feature sets.
        
        Args:
            features1: First feature set
            features2: Second feature set
            
        Returns:
            Distance score (lower is more similar)
        """
        # Simple Euclidean distance for numeric features
        distance = 0.0
        count = 0
        
        numeric_features = [
            'aspect_ratio', 'face_count', 'dominant_face_area',
            'dominant_face_x', 'dominant_face_y', 'brightness_mean',
            'contrast', 'edge_density'
        ]
        
        for feature in numeric_features:
            if feature in features1 and feature in features2:
                diff = features1[feature] - features2[feature]
                distance += diff ** 2
                count += 1
        
        if count > 0:
            return np.sqrt(distance / count)
        
        return float('inf')