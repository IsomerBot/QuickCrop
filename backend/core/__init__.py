"""
Core module for QuickCrop backend
"""

from .config import settings
from .middleware import RequestIDMiddleware, LoggingMiddleware

__all__ = ["settings", "RequestIDMiddleware", "LoggingMiddleware"]