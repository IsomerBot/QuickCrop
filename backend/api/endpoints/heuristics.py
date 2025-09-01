"""
Heuristics API endpoints for machine learning system.
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from services.heuristics import HeuristicsManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global heuristics manager instance
heuristics_manager = HeuristicsManager()


class LearnRequest(BaseModel):
    """Request model for learning from user adjustments."""
    image_width: int
    image_height: int
    initial_crop: Dict[str, int]
    final_crop: Dict[str, int]
    face_box: Optional[Dict[str, int]] = None
    features: Optional[Dict[str, Any]] = None


class HeuristicsStatsResponse(BaseModel):
    """Response model for heuristics statistics."""
    parameter_count: int
    sample_count: int
    loaded_buckets: int
    bucket_keys: list
    aspect_distribution: Dict[str, int]
    zoom_distribution: Dict[str, int]
    bucket_confidences: Dict[str, Dict[str, Any]]


@router.post("/learn")
async def learn_from_adjustment(request: LearnRequest):
    """
    Learn from user's manual crop adjustment.
    
    This endpoint records user adjustments to improve future crop suggestions.
    """
    try:
        # Note: In production, we would reconstruct the image from stored data
        # For now, we'll store the adjustment metrics only
        
        # Extract features for learning
        features = request.features or {}
        features.update({
            'image_width': request.image_width,
            'image_height': request.image_height,
            'aspect_ratio': request.image_width / request.image_height
        })
        
        # Determine classifications
        aspect_class = heuristics_manager.feature_extractor.classify_aspect_ratio(
            features['aspect_ratio']
        )
        
        # Determine zoom level from face box if available
        zoom_level = 'medium'
        if request.face_box:
            face_height = request.face_box['height'] / request.image_height
            zoom_level = heuristics_manager.feature_extractor.classify_zoom_level(
                face_height=face_height
            )
        
        # Calculate adjustment deltas
        deltas = heuristics_manager.ema_calculator.calculate_adjustment_deltas(
            request.initial_crop,
            request.final_crop,
            (request.image_width, request.image_height)
        )
        
        # Update EMA parameters
        bucket_key = heuristics_manager.ema_calculator.create_bucket_key(
            aspect_class, zoom_level
        )
        
        for param_name, delta_value in deltas.items():
            # Update in memory and database
            heuristics_manager.ema_calculator.update_bucket(
                bucket_key, param_name, delta_value
            )
            heuristics_manager.db.update_ema_parameter(
                aspect_class, zoom_level, param_name, delta_value,
                alpha=heuristics_manager.ema_calculator.alpha
            )
        
        # Add to audit trail (simplified without actual image)
        heuristics_manager.db.add_sample(
            image_hash="placeholder",  # Would be actual image hash
            original_dimensions=(request.image_width, request.image_height),
            face_detected=bool(request.face_box),
            pose_detected=False,
            aspect_class=aspect_class,
            zoom_level=zoom_level,
            initial_crop=request.initial_crop,
            final_crop=request.final_crop,
            features=features
        )
        
        return {
            "success": True,
            "message": "Learned from adjustment",
            "aspect_class": aspect_class,
            "zoom_level": zoom_level,
            "deltas": deltas
        }
    
    except Exception as e:
        logger.error(f"Error learning from adjustment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=HeuristicsStatsResponse)
async def get_heuristics_statistics():
    """Get comprehensive statistics about the heuristics system."""
    try:
        stats = heuristics_manager.get_statistics()
        return HeuristicsStatsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Error getting heuristics statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_heuristics_model(path: str = Body(..., embed=True)):
    """Export the heuristics model to a file."""
    try:
        heuristics_manager.export_model(path)
        return {"success": True, "message": f"Model exported to {path}"}
    
    except Exception as e:
        logger.error(f"Error exporting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_heuristics_model(path: str = Body(..., embed=True)):
    """Import a heuristics model from a file."""
    try:
        heuristics_manager.import_model(path)
        return {"success": True, "message": f"Model imported from {path}"}
    
    except Exception as e:
        logger.error(f"Error importing model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_heuristics(
    aspect_class: Optional[str] = Body(None, embed=True),
    zoom_level: Optional[str] = Body(None, embed=True)
):
    """Reset heuristics learning for specific or all buckets."""
    try:
        heuristics_manager.reset_learning(aspect_class, zoom_level)
        
        if aspect_class and zoom_level:
            message = f"Reset learning for {aspect_class}/{zoom_level}"
        else:
            message = "Reset all learning"
        
        return {"success": True, "message": message}
    
    except Exception as e:
        logger.error(f"Error resetting heuristics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_samples(days_to_keep: int = Body(30, embed=True)):
    """Clean up old samples from the audit trail."""
    try:
        deleted = heuristics_manager.cleanup_old_samples(days_to_keep)
        return {
            "success": True,
            "message": f"Deleted {deleted} old samples",
            "samples_deleted": deleted
        }
    
    except Exception as e:
        logger.error(f"Error cleaning up samples: {e}")
        raise HTTPException(status_code=500, detail=str(e))