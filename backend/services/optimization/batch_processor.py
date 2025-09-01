"""
Batch processing for image optimization with progress tracking.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Callable, Optional, Any
from dataclasses import dataclass
from PIL import Image
import logging
import time

from .optimizer import ImageOptimizer, OptimizationResult
from ..presets import PresetType

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch optimization."""
    preset_type: PresetType
    image_bytes: bytes
    optimization_result: OptimizationResult
    processing_time: float


class BatchOptimizer:
    """
    Batch processor for optimizing multiple images with progress tracking.
    """
    
    def __init__(
        self,
        optimizer: Optional[ImageOptimizer] = None,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize batch optimizer.
        
        Args:
            optimizer: ImageOptimizer instance (creates default if None)
            max_workers: Maximum number of parallel workers
            progress_callback: Callback for progress updates (current, total)
        """
        self.optimizer = optimizer or ImageOptimizer()
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def optimize_batch(
        self,
        images: Dict[PresetType, Image.Image],
        optimization_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[PresetType, BatchResult]:
        """
        Optimize a batch of images for different presets.
        
        Args:
            images: Dictionary mapping preset types to PIL Images
            optimization_settings: Optional optimization settings per preset
            
        Returns:
            Dictionary mapping preset types to BatchResults
        """
        results = {}
        total = len(images)
        completed = 0
        
        # Default settings
        default_settings = {
            'quality_range': (70, 95),
            'optimization_level': 3,
            'format': 'PNG'
        }
        
        if optimization_settings:
            default_settings.update(optimization_settings)
        
        # Submit all tasks
        futures = {}
        for preset_type, image in images.items():
            future = self._executor.submit(
                self._optimize_single,
                preset_type,
                image,
                default_settings
            )
            futures[future] = preset_type
        
        # Process completed tasks
        for future in as_completed(futures):
            preset_type = futures[future]
            try:
                result = future.result()
                results[preset_type] = result
                completed += 1
                
                # Call progress callback
                if self.progress_callback:
                    self.progress_callback(completed, total)
                
                logger.info(
                    f"Optimized {preset_type.value}: "
                    f"{result.optimization_result.reduction_percentage:.1f}% reduction"
                )
            
            except Exception as e:
                logger.error(f"Failed to optimize {preset_type.value}: {e}")
                # Add failed result
                results[preset_type] = BatchResult(
                    preset_type=preset_type,
                    image_bytes=b'',
                    optimization_result=OptimizationResult(
                        original_size=0,
                        optimized_size=0,
                        reduction_percentage=0.0,
                        optimization_method="none",
                        success=False,
                        error_message=str(e)
                    ),
                    processing_time=0.0
                )
                completed += 1
                
                if self.progress_callback:
                    self.progress_callback(completed, total)
        
        return results
    
    async def optimize_batch_async(
        self,
        images: Dict[PresetType, Image.Image],
        optimization_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[PresetType, BatchResult]:
        """
        Asynchronously optimize a batch of images.
        
        Args:
            images: Dictionary mapping preset types to PIL Images
            optimization_settings: Optional optimization settings
            
        Returns:
            Dictionary mapping preset types to BatchResults
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.optimize_batch,
            images,
            optimization_settings
        )
    
    def _optimize_single(
        self,
        preset_type: PresetType,
        image: Image.Image,
        settings: Dict[str, Any]
    ) -> BatchResult:
        """
        Optimize a single image.
        
        Args:
            preset_type: Preset type being processed
            image: PIL Image to optimize
            settings: Optimization settings
            
        Returns:
            BatchResult with optimization details
        """
        start_time = time.time()
        
        # Determine format and optimize accordingly
        if settings.get('format', 'PNG').upper() == 'JPEG':
            optimized_bytes, result = self.optimizer.optimize_jpeg(
                image,
                quality=settings.get('jpeg_quality', 85),
                optimize=True,
                progressive=True
            )
        else:
            optimized_bytes, result = self.optimizer.optimize_image(
                image,
                quality_range=settings.get('quality_range', (70, 95)),
                optimization_level=settings.get('optimization_level', 3)
            )
        
        processing_time = time.time() - start_time
        
        return BatchResult(
            preset_type=preset_type,
            image_bytes=optimized_bytes,
            optimization_result=result,
            processing_time=processing_time
        )
    
    def compare_optimization_methods(
        self,
        image: Image.Image
    ) -> Dict[str, OptimizationResult]:
        """
        Compare different optimization methods on the same image.
        
        Args:
            image: PIL Image to test
            
        Returns:
            Dictionary of method names to results
        """
        results = {}
        
        # Test PNG with different settings
        test_configs = [
            ('png_lossless', {
                'format': 'PNG',
                'enable_lossy': False,
                'optimization_level': 3
            }),
            ('png_lossy_high', {
                'format': 'PNG',
                'enable_lossy': True,
                'quality_range': (85, 95),
                'optimization_level': 3
            }),
            ('png_lossy_medium', {
                'format': 'PNG',
                'enable_lossy': True,
                'quality_range': (70, 85),
                'optimization_level': 3
            }),
            ('jpeg_high', {
                'format': 'JPEG',
                'jpeg_quality': 95
            }),
            ('jpeg_medium', {
                'format': 'JPEG',
                'jpeg_quality': 85
            }),
            ('jpeg_low', {
                'format': 'JPEG',
                'jpeg_quality': 75
            })
        ]
        
        for method_name, config in test_configs:
            # Create optimizer with specific settings
            optimizer = ImageOptimizer(
                enable_lossy=config.get('enable_lossy', True)
            )
            
            if config.get('format') == 'JPEG':
                _, result = optimizer.optimize_jpeg(
                    image,
                    quality=config.get('jpeg_quality', 85)
                )
            else:
                _, result = optimizer.optimize_image(
                    image,
                    quality_range=config.get('quality_range', (70, 95)),
                    optimization_level=config.get('optimization_level', 3)
                )
            
            results[method_name] = result
        
        return results
    
    def get_best_optimization(
        self,
        image: Image.Image,
        max_size_kb: Optional[int] = None,
        min_quality: int = 70
    ) -> Tuple[bytes, OptimizationResult]:
        """
        Find the best optimization that meets size constraints.
        
        Args:
            image: PIL Image to optimize
            max_size_kb: Maximum file size in KB (optional)
            min_quality: Minimum acceptable quality
            
        Returns:
            Tuple of (optimized_bytes, OptimizationResult)
        """
        best_bytes = None
        best_result = None
        best_size = float('inf')
        
        # Try different quality levels
        for quality_max in range(95, min_quality - 1, -5):
            quality_range = (max(min_quality, quality_max - 10), quality_max)
            
            optimized_bytes, result = self.optimizer.optimize_image(
                image,
                quality_range=quality_range,
                optimization_level=3
            )
            
            # Check if this is better
            if result.success:
                size_kb = result.optimized_size / 1024
                
                if max_size_kb is None or size_kb <= max_size_kb:
                    if result.optimized_size < best_size:
                        best_bytes = optimized_bytes
                        best_result = result
                        best_size = result.optimized_size
                        
                        # If we're under the target size, we can stop
                        if max_size_kb and size_kb <= max_size_kb * 0.9:
                            break
        
        if best_bytes is None:
            # Fallback to JPEG if PNG doesn't meet requirements
            for quality in range(85, min_quality - 1, -5):
                optimized_bytes, result = self.optimizer.optimize_jpeg(
                    image,
                    quality=quality
                )
                
                if result.success:
                    size_kb = result.optimized_size / 1024
                    
                    if max_size_kb is None or size_kb <= max_size_kb:
                        return optimized_bytes, result
            
            # Last resort - return with minimum quality
            return self.optimizer.optimize_jpeg(image, quality=min_quality)
        
        return best_bytes, best_result
    
    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)