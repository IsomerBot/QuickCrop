"""
Application configuration management
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "QuickCrop"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    
    # Image Processing Settings
    TEMP_DIR: str = "/tmp/quickcrop"
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    
    # MediaPipe Settings
    MIN_DETECTION_CONFIDENCE: float = 0.75
    MIN_TRACKING_CONFIDENCE: float = 0.5
    
    # Optimization Settings
    USE_PNG_OPTIMIZATION: bool = True
    PNG_COMPRESSION_LEVEL: int = 6  # 1-9, higher = better compression
    TINIFY_API_KEY: str = "GtKysk1RDvRZ7WLsb5h3cY8zfLv6Hx8l"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v


# Create settings instance
settings = Settings()
