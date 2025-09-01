"""
Main API router
"""

from fastapi import APIRouter

from api.endpoints import upload, process, health, heuristics, storage, suggestions

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

api_router.include_router(
    upload.router,
    prefix="/upload",
    tags=["upload"]
)

api_router.include_router(
    process.router,
    prefix="/process",
    tags=["process"]
)

api_router.include_router(
    heuristics.router,
    prefix="/heuristics",
    tags=["heuristics"]
)

api_router.include_router(
    storage.router,
    prefix="/storage",
    tags=["storage"]
)

api_router.include_router(
    suggestions.router,
    prefix="/suggestions",
    tags=["suggestions"]
)