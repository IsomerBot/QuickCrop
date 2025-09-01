"""
Image processing service for cropping and optimization
"""

import cv2
import numpy as np
from PIL import Image, ImageOps
from typing import Tuple, Optional, Dict, Any
import io
import subprocess
import os
import tempfile
from pathlib import Path

from core.config import settings
from models.process import CropPreset, PRESET_CONFIGS
from services.detection import detection_service, DetectionResult
from services.optimization import ImageOptimizer, BatchOptimizer, TinifyOptimizer


class ImageProcessorService:
    """Service for image processing operations"""
    
    def __init__(self):
        self.detection_service = detection_service
        # Use Tinify if API key is available, otherwise fall back to local optimizer
        tinify_api_key = settings.TINIFY_API_KEY or os.environ.get('TINIFY_API_KEY')
        try:
            self.optimizer = TinifyOptimizer(api_key=tinify_api_key)
            self.use_tinify = True
        except Exception as e:
            self.optimizer = ImageOptimizer()
            self.use_tinify = False
        self.batch_optimizer = BatchOptimizer(self.optimizer)
        
    def load_image(self, file_path: str) -> np.ndarray:
        """Load image from file path"""
        image = cv2.imread(file_path)
        if image is None:
            raise ValueError(f"Failed to load image from {file_path}")
        return image
    
    def load_image_from_bytes(self, content: bytes) -> np.ndarray:
        """Load image from bytes"""
        nparr = np.frombuffer(content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode image from bytes")
        return image
    
    def process_image_crop(self, 
                          image: np.ndarray, 
                          preset: CropPreset) -> np.ndarray:
        """
        Process image with specified crop preset
        Returns cropped image
        """
        # Get preset configuration
        preset_config = PRESET_CONFIGS.get(preset)
        if not preset_config:
            raise ValueError(f"Invalid preset: {preset}")
        
        # Perform detection
        detection_result = self.detection_service.detect(image)
        
        # Calculate crop region
        crop_region = self.detection_service.get_crop_region(
            detection_result,
            aspect_ratio=preset_config.aspect_ratio,
            padding_percent=preset_config.padding_percent,
            focus_area=preset_config.focus_area
        )
        
        # Apply crop
        x, y, width, height = crop_region
        cropped = image[y:y+height, x:x+width]
        
        return cropped
    
    def apply_manual_crop(self,
                         image: np.ndarray,
                         crop_area: Tuple[int, int, int, int]) -> np.ndarray:
        """Apply manual crop to image"""
        x, y, width, height = crop_area
        
        # Validate crop area
        img_height, img_width = image.shape[:2]
        x = max(0, min(x, img_width - 1))
        y = max(0, min(y, img_height - 1))
        width = max(1, min(width, img_width - x))
        height = max(1, min(height, img_height - y))
        
        return image[y:y+height, x:x+width]
    
    def resize_image(self, 
                    image: np.ndarray, 
                    target_size: Optional[Tuple[int, int]] = None,
                    max_dimension: Optional[int] = None) -> np.ndarray:
        """Resize image to target size or max dimension"""
        height, width = image.shape[:2]
        
        if target_size:
            return cv2.resize(image, target_size, interpolation=cv2.INTER_LANCZOS4)
        
        if max_dimension:
            if width > height:
                if width > max_dimension:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    return image
            else:
                if height > max_dimension:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                else:
                    return image
            
            return cv2.resize(image, (new_width, new_height), 
                            interpolation=cv2.INTER_LANCZOS4)
        
        return image
    
    def encode_image(self, 
                    image: np.ndarray, 
                    format: str = 'jpeg',
                    quality: int = 85,
                    auto_optimize: bool = True) -> bytes:
        """Encode image to specified format
        
        Args:
            image: OpenCV image array
            format: Output format (jpeg, png, webp)
            quality: Quality for JPEG/WebP (ignored if auto_optimize=True for PNG)
            auto_optimize: Use Tinify for smart compression
        """
        if format == 'jpeg' or format == 'jpg':
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, quality]
            _, encoded = cv2.imencode('.jpg', image, encode_param)
        elif format == 'png':
            encode_param = [cv2.IMWRITE_PNG_COMPRESSION, settings.PNG_COMPRESSION_LEVEL]
            _, encoded = cv2.imencode('.png', image, encode_param)
        elif format == 'webp':
            encode_param = [cv2.IMWRITE_WEBP_QUALITY, quality]
            _, encoded = cv2.imencode('.webp', image, encode_param)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return encoded.tobytes()
    
    def optimize_image_bytes(self, image_bytes: bytes, format: str = 'png', auto_optimize: bool = True) -> bytes:
        """Optimize image bytes using Tinify or local optimization
        
        Args:
            image_bytes: Image bytes
            format: Image format (jpeg, png, webp)
            auto_optimize: Use Tinify for smart compression
        """
        
        if not settings.USE_PNG_OPTIMIZATION and format == 'png':
            return image_bytes
        
        try:
            if self.use_tinify and auto_optimize:
                # Use Tinify for all formats when auto_optimize is enabled
                optimized_bytes, result = self.optimizer.optimize_bytes(
                    image_bytes,
                    preserve_metadata=False
                )
                
                
                # Log optimization result
                if result.success and result.reduction_percentage > 0:
                    pass  # Optimization successful
                
                return optimized_bytes
            else:
                # For manual mode or fallback, only optimize PNG
                if format == 'png':
                    return self.optimize_png(image_bytes, auto_optimize=False)
                else:
                    # Return as-is for JPEG/WebP in manual mode (quality already applied during encoding)
                    return image_bytes
                    
        except Exception as e:
            return image_bytes
    
    def optimize_png(self, png_bytes: bytes, auto_optimize: bool = True) -> bytes:
        """Optimize PNG using Tinify or local optimization pipeline
        
        Args:
            png_bytes: PNG image bytes
            auto_optimize: Use Tinify for smart compression (ignores quality setting)
        """
        if not settings.USE_PNG_OPTIMIZATION:
            return png_bytes
        
        try:
            if self.use_tinify and auto_optimize:
                # Use Tinify optimizer when auto_optimize is enabled
                optimized_bytes, result = self.optimizer.optimize_bytes(
                    png_bytes,
                    preserve_metadata=False
                )
            else:
                # Use local optimizer when manual quality control is needed
                image = Image.open(io.BytesIO(png_bytes))
                # For local optimizer, check if it's the Tinify fallback
                if hasattr(self.optimizer, 'optimize_bytes'):
                    # This is TinifyOptimizer but with manual mode
                    optimized_bytes, result = self.optimizer.optimize_bytes(
                        png_bytes,
                        preserve_metadata=False
                    )
                else:
                    # This is the local ImageOptimizer
                    optimized_bytes, result = self.optimizer.optimize_image(
                        image,
                        quality_range=(85, 95),
                        optimization_level=3
                    )
            
            # Log optimization result
            if result.success and result.reduction_percentage > 0:
                pass  # Optimization successful
            
            return optimized_bytes
            
        except Exception as e:
            # Return original if optimization fails
            return png_bytes
    
    def optimize_batch_presets(
        self, 
        images: Dict[str, Image.Image],
        progress_callback=None
    ) -> Dict[str, bytes]:
        """
        Optimize multiple preset images in batch.
        
        Args:
            images: Dictionary of preset name to PIL Image
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary of preset name to optimized bytes
        """
        # Convert to PresetType keys if needed
        preset_images = {}
        for key, image in images.items():
            if isinstance(key, str):
                # Convert string to PresetType
                for preset_type in CropPreset:
                    if preset_type.value == key:
                        preset_images[preset_type] = image
                        break
            else:
                preset_images[key] = image
        
        # Process batch
        results = self.batch_optimizer.optimize_batch(
            preset_images,
            optimization_settings={
                'quality_range': (85, 95),
                'optimization_level': 3,
                'format': 'PNG'
            }
        )
        
        # Extract optimized bytes
        optimized = {}
        for preset_type, batch_result in results.items():
            if batch_result.optimization_result.success:
                optimized[preset_type.value] = batch_result.image_bytes
            else:
                # Fallback to unoptimized if failed
                buffer = io.BytesIO()
                preset_images[preset_type].save(buffer, format='PNG')
                optimized[preset_type.value] = buffer.getvalue()
        
        return optimized
    
    def get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Get image information"""
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1
        
        return {
            'width': width,
            'height': height,
            'channels': channels,
            'aspect_ratio': width / height,
            'size_kb': image.nbytes / 1024
        }
    
    def process_batch(self, 
                     images: list[np.ndarray], 
                     preset: CropPreset) -> list[np.ndarray]:
        """Process multiple images with the same preset"""
        processed = []
        for image in images:
            try:
                cropped = self.process_image_crop(image, preset)
                processed.append(cropped)
            except Exception as e:
                # Log error and continue with next image
                processed.append(None)
        
        return processed


# Singleton instance
image_processor_service = ImageProcessorService()