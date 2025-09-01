"""
QuickCrop Backend API
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.middleware import RequestIDMiddleware, LoggingMiddleware
from api.router import api_router
from services.processing_queue import processing_queue_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting QuickCrop API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Start processing workers
    await processing_queue_service.start_workers(num_workers=2)
    logger.info("Processing workers started")

    yield

    # Shutdown
    logger.info("Shutting down QuickCrop API...")
    await processing_queue_service.stop_workers()
    logger.info("Processing workers stopped")


# Create FastAPI application
app = FastAPI(
    title="QuickCrop API",
    description="Photo crop/resize API for e-commerce product photography",
    version="0.1.0",
    lifespan=lifespan,
    # Keep docs on /api/* so they don't collide with static site at "/"
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Include API routes under /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint (kept outside /api so it's easy to probe)"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# ---- Serve the exported Next.js site as static files at "/" ----
# Place this AFTER API routes so /api/* keeps working.
# Put the exported Next.js build (from `next export`) into /app/static in the image.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
