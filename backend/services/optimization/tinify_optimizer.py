"""
Image optimization using Tinify API (TinyPNG/TinyJPEG).
"""

import tinify
import io
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image
import os

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of image optimization."""
    original_size: int
    optimized_size: int
    reduction_percentage: float
    optimization_method: str
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    compression_count: Optional[int] = None


class TinifyOptimizer:
    """
    Image optimizer using Tinify API for both PNG and JPEG optimization.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Tinify optimizer.
        
        Args:
            api_key: Tinify API key. If not provided, will look for TINIFY_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('TINIFY_API_KEY')
        if not self.api_key:
            raise ValueError("Tinify API key not provided. Set TINIFY_API_KEY environment variable or pass api_key parameter.")
        
        # Configure Tinify
        tinify.key = self.api_key
        
        # Validate API key on initialization
        try:
            tinify.validate()
            self.compression_count = tinify.compression_count
            logger.info(f"Tinify initialized. Compressions used this month: {self.compression_count}")
        except tinify.Error as e:
            logger.error(f"Tinify validation failed: {e}")
            raise
    
    def optimize_image(
        self,
        image: Image.Image,
        preserve_metadata: bool = False,
        resize_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, OptimizationResult]:
        """
        Optimize an image using Tinify API.
        
        Args:
            image: PIL Image to optimize
            preserve_metadata: Whether to preserve image metadata (copyright, geolocation, etc.)
            resize_options: Optional resize options dict with keys:
                - method: "scale", "fit", "cover", "thumb" 
                - width: target width
                - height: target height
                
        Returns:
            Tuple of (optimized_bytes, OptimizationResult)
        """
        # Convert image to bytes
        original_bytes = self._image_to_bytes(image)
        original_size = len(original_bytes)
        
        try:
            # Upload to Tinify
            source = tinify.from_buffer(original_bytes)
            
            # Apply transformations if requested
            if resize_options:
                source = source.resize(**resize_options)
            
            # Configure metadata preservation
            if preserve_metadata:
                # Preserve all metadata
                result = source.to_buffer()
            else:
                # Strip metadata (default Tinify behavior)
                result = source.to_buffer()
            
            optimized_bytes = result
            optimized_size = len(optimized_bytes)
            reduction = ((original_size - optimized_size) / original_size) * 100
            
            # Get updated compression count
            compression_count = tinify.compression_count
            
            return optimized_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=optimized_size,
                reduction_percentage=reduction,
                optimization_method="tinify",
                success=True,
                metadata={
                    'preserve_metadata': preserve_metadata,
                    'resize_options': resize_options,
                    'format': self._detect_format(image)
                },
                compression_count=compression_count
            )
        
        except tinify.AccountError as e:
            # API key invalid or account limit reached
            logger.error(f"Tinify account error: {e}")
            return original_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=f"Tinify account error: {e}"
            )
        
        except tinify.ClientError as e:
            # Input file not supported or other client error
            logger.error(f"Tinify client error: {e}")
            return original_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=f"Tinify client error: {e}"
            )
        
        except tinify.ServerError as e:
            # Temporary server error
            logger.error(f"Tinify server error: {e}")
            return original_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=f"Tinify server error: {e}"
            )
        
        except tinify.ConnectionError as e:
            # Network connection error
            logger.error(f"Tinify connection error: {e}")
            return original_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=f"Tinify connection error: {e}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error during optimization: {e}")
            return original_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=str(e)
            )
    
    def optimize_bytes(
        self,
        image_bytes: bytes,
        preserve_metadata: bool = False,
        resize_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, OptimizationResult]:
        """
        Optimize image bytes directly using Tinify API.
        
        Args:
            image_bytes: Raw image bytes
            preserve_metadata: Whether to preserve image metadata
            resize_options: Optional resize options
                
        Returns:
            Tuple of (optimized_bytes, OptimizationResult)
        """
        original_size = len(image_bytes)
        
        try:
            # Upload to Tinify
            source = tinify.from_buffer(image_bytes)
            
            # Apply transformations if requested
            if resize_options:
                source = source.resize(**resize_options)
            
            # Get optimized result
            optimized_bytes = source.to_buffer()
            optimized_size = len(optimized_bytes)
            reduction = ((original_size - optimized_size) / original_size) * 100
            
            # Get updated compression count
            compression_count = tinify.compression_count
            
            return optimized_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=optimized_size,
                reduction_percentage=reduction,
                optimization_method="tinify",
                success=True,
                metadata={
                    'preserve_metadata': preserve_metadata,
                    'resize_options': resize_options
                },
                compression_count=compression_count
            )
        
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
            return image_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=str(e)
            )
    
    def get_compression_count(self) -> int:
        """
        Get the current number of compressions used this month.
        
        Returns:
            Number of compressions used
        """
        try:
            tinify.validate()
            return tinify.compression_count
        except:
            return -1
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to bytes."""
        buffer = io.BytesIO()
        
        # Detect format
        format = self._detect_format(image)
        
        # Convert RGBA to RGB for JPEG
        if format == 'JPEG' and image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        
        # Save to buffer
        image.save(buffer, format=format)
        return buffer.getvalue()
    
    def _detect_format(self, image: Image.Image) -> str:
        """Detect image format from PIL Image."""
        if hasattr(image, 'format') and image.format:
            return image.format
        
        # Default based on mode
        if image.mode == 'RGBA':
            return 'PNG'
        else:
            return 'JPEG'
    
    def resize_with_tinify(
        self,
        image_bytes: bytes,
        method: str = "fit",
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Tuple[bytes, OptimizationResult]:
        """
        Resize and optimize image using Tinify.
        
        Args:
            image_bytes: Input image bytes
            method: Resize method - "scale", "fit", "cover", "thumb"
            width: Target width
            height: Target height
            
        Returns:
            Tuple of (resized_optimized_bytes, OptimizationResult)
        """
        resize_options = {"method": method}
        if width:
            resize_options["width"] = width
        if height:
            resize_options["height"] = height
        
        return self.optimize_bytes(image_bytes, resize_options=resize_options)