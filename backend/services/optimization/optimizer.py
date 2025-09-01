"""
Core image optimization functionality using oxipng and pngquant.
"""

import subprocess
import tempfile
import os
import shutil
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image
import io
import logging
from pathlib import Path

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


class ImageOptimizer:
    """
    Image optimizer using oxipng and pngquant for PNG optimization.
    """
    
    def __init__(
        self,
        oxipng_path: str = "oxipng",
        pngquant_path: str = "pngquant",
        enable_lossy: bool = True,
        strip_metadata: bool = True
    ):
        """
        Initialize image optimizer.
        
        Args:
            oxipng_path: Path to oxipng binary
            pngquant_path: Path to pngquant binary
            enable_lossy: Whether to use lossy compression with pngquant
            strip_metadata: Whether to strip EXIF metadata
        """
        self.oxipng_path = oxipng_path
        self.pngquant_path = pngquant_path
        self.enable_lossy = enable_lossy
        self.strip_metadata = strip_metadata
        
        # Check if tools are available
        self._check_tools()
    
    def _check_tools(self):
        """Check if optimization tools are available."""
        self.oxipng_available = self._check_command(self.oxipng_path)
        self.pngquant_available = self._check_command(self.pngquant_path)
        
        if not self.oxipng_available:
            logger.warning(f"oxipng not found at {self.oxipng_path}")
        if not self.pngquant_available:
            logger.warning(f"pngquant not found at {self.pngquant_path}")
    
    def _check_command(self, command: str) -> bool:
        """Check if a command is available."""
        try:
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def optimize_image(
        self,
        image: Image.Image,
        quality_range: Tuple[int, int] = (70, 95),
        optimization_level: int = 3
    ) -> Tuple[bytes, OptimizationResult]:
        """
        Optimize an image using available tools.
        
        Args:
            image: PIL Image to optimize
            quality_range: Quality range for lossy compression (min, max)
            optimization_level: Optimization level for oxipng (1-6)
            
        Returns:
            Tuple of (optimized_bytes, OptimizationResult)
        """
        # Convert image to PNG bytes
        original_bytes = self._image_to_png_bytes(image)
        original_size = len(original_bytes)
        
        # Strip metadata if requested
        if self.strip_metadata:
            image = self._strip_metadata(image)
            original_bytes = self._image_to_png_bytes(image)
        
        # Try optimization chain
        optimized_bytes = original_bytes
        optimization_method = "none"
        
        try:
            # First try lossless optimization with oxipng
            if self.oxipng_available:
                oxipng_result = self._optimize_with_oxipng(
                    original_bytes, optimization_level
                )
                if oxipng_result and len(oxipng_result) < len(optimized_bytes):
                    optimized_bytes = oxipng_result
                    optimization_method = "oxipng"
            
            # Then try lossy optimization with pngquant
            if self.enable_lossy and self.pngquant_available:
                pngquant_result = self._optimize_with_pngquant(
                    optimized_bytes, quality_range
                )
                if pngquant_result and len(pngquant_result) < len(optimized_bytes):
                    optimized_bytes = pngquant_result
                    optimization_method = "pngquant" if optimization_method == "none" else "oxipng+pngquant"
            
            # Calculate reduction
            optimized_size = len(optimized_bytes)
            reduction = ((original_size - optimized_size) / original_size) * 100
            
            return optimized_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=optimized_size,
                reduction_percentage=reduction,
                optimization_method=optimization_method,
                success=True,
                metadata={
                    'quality_range': quality_range,
                    'optimization_level': optimization_level,
                    'metadata_stripped': self.strip_metadata
                }
            )
        
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return original_bytes, OptimizationResult(
                original_size=original_size,
                optimized_size=original_size,
                reduction_percentage=0.0,
                optimization_method="none",
                success=False,
                error_message=str(e)
            )
    
    def _image_to_png_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to PNG bytes."""
        buffer = io.BytesIO()
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            # Check if alpha channel has any transparency
            alpha = image.split()[3]
            if alpha.getextrema() == (255, 255):
                # No transparency, convert to RGB
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=alpha)
                image = rgb_image
        
        image.save(buffer, format='PNG', optimize=False)
        return buffer.getvalue()
    
    def _strip_metadata(self, image: Image.Image) -> Image.Image:
        """Strip EXIF and other metadata from image."""
        # Create a new image without metadata
        data = list(image.getdata())
        image_no_exif = Image.new(image.mode, image.size)
        image_no_exif.putdata(data)
        return image_no_exif
    
    def _optimize_with_oxipng(
        self,
        png_bytes: bytes,
        optimization_level: int = 3
    ) -> Optional[bytes]:
        """
        Optimize PNG using oxipng.
        
        Args:
            png_bytes: PNG image bytes
            optimization_level: Optimization level (1-6)
            
        Returns:
            Optimized bytes or None if failed
        """
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_in:
            tmp_in.write(png_bytes)
            tmp_in_path = tmp_in.name
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_out:
            tmp_out_path = tmp_out.name
        
        try:
            # Copy input to output (oxipng modifies in place)
            shutil.copy2(tmp_in_path, tmp_out_path)
            
            # Run oxipng
            cmd = [
                self.oxipng_path,
                f'-o{optimization_level}',
                '--strip', 'safe',  # Strip metadata safely
                '--quiet',
                tmp_out_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                with open(tmp_out_path, 'rb') as f:
                    return f.read()
            else:
                logger.warning(f"oxipng failed: {result.stderr}")
                return None
        
        except Exception as e:
            logger.error(f"Error running oxipng: {e}")
            return None
        
        finally:
            # Cleanup temp files
            for path in [tmp_in_path, tmp_out_path]:
                try:
                    os.unlink(path)
                except:
                    pass
    
    def _optimize_with_pngquant(
        self,
        png_bytes: bytes,
        quality_range: Tuple[int, int] = (70, 95)
    ) -> Optional[bytes]:
        """
        Optimize PNG using pngquant.
        
        Args:
            png_bytes: PNG image bytes
            quality_range: Quality range (min, max) 0-100
            
        Returns:
            Optimized bytes or None if failed
        """
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_in:
            tmp_in.write(png_bytes)
            tmp_in_path = tmp_in.name
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_out:
            tmp_out_path = tmp_out.name
        
        try:
            # Run pngquant
            cmd = [
                self.pngquant_path,
                '--quality', f'{quality_range[0]}-{quality_range[1]}',
                '--speed', '1',  # Slowest/best compression
                '--output', tmp_out_path,
                '--force',
                tmp_in_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                with open(tmp_out_path, 'rb') as f:
                    return f.read()
            else:
                logger.warning(f"pngquant failed: {result.stderr}")
                return None
        
        except Exception as e:
            logger.error(f"Error running pngquant: {e}")
            return None
        
        finally:
            # Cleanup temp files
            for path in [tmp_in_path, tmp_out_path]:
                try:
                    os.unlink(path)
                except:
                    pass
    
    def optimize_jpeg(
        self,
        image: Image.Image,
        quality: int = 85,
        optimize: bool = True,
        progressive: bool = True
    ) -> Tuple[bytes, OptimizationResult]:
        """
        Optimize JPEG image using Pillow's built-in optimization.
        
        Args:
            image: PIL Image to optimize
            quality: JPEG quality (1-100)
            optimize: Enable Pillow optimization
            progressive: Enable progressive JPEG
            
        Returns:
            Tuple of (optimized_bytes, OptimizationResult)
        """
        # Original size
        buffer_orig = io.BytesIO()
        image.save(buffer_orig, format='JPEG', quality=95)
        original_size = buffer_orig.tell()
        
        # Strip metadata if requested
        if self.strip_metadata:
            image = self._strip_metadata(image)
        
        # Optimize
        buffer_opt = io.BytesIO()
        
        # Convert RGBA to RGB for JPEG
        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        
        image.save(
            buffer_opt,
            format='JPEG',
            quality=quality,
            optimize=optimize,
            progressive=progressive
        )
        
        optimized_bytes = buffer_opt.getvalue()
        optimized_size = len(optimized_bytes)
        reduction = ((original_size - optimized_size) / original_size) * 100
        
        return optimized_bytes, OptimizationResult(
            original_size=original_size,
            optimized_size=optimized_size,
            reduction_percentage=reduction,
            optimization_method="pillow_jpeg",
            success=True,
            metadata={
                'quality': quality,
                'optimize': optimize,
                'progressive': progressive,
                'metadata_stripped': self.strip_metadata
            }
        )
    
    def resize_with_lanczos(
        self,
        image: Image.Image,
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """
        Resize image using high-quality Lanczos resampling.
        
        Args:
            image: PIL Image to resize
            target_size: Target (width, height)
            
        Returns:
            Resized image
        """
        return image.resize(target_size, Image.Resampling.LANCZOS)