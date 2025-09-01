"""
Health check endpoints
"""

from fastapi import APIRouter
from datetime import datetime

from core.config import settings

router = APIRouter()


@router.get("/status")
async def health_status():
    """Get detailed health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "version": "0.1.0"
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    # Add any dependency checks here
    return {"ready": True}