"""
Error handling utilities and recovery mechanisms.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union, Callable
from functools import wraps
from pathlib import Path
import asyncio
from datetime import datetime

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error class."""
    
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.utcnow().isoformat()


class ProcessingError(AppError):
    """Error during image processing."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="PROCESSING_ERROR",
            status_code=422,
            **kwargs
        )


class StorageError(AppError):
    """Error with file storage operations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="STORAGE_ERROR",
            status_code=507,
            **kwargs
        )


class ValidationError(AppError):
    """Input validation error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=400,
            **kwargs
        )


class RateLimitError(AppError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(
            message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            **kwargs
        )


def error_response(error: Union[AppError, Exception]) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error: The error to convert to response
        
    Returns:
        JSONResponse with error details
    """
    if isinstance(error, AppError):
        content = {
            "error": {
                "code": error.code,
                "message": error.user_message,
                "details": error.details,
                "timestamp": error.timestamp
            }
        }
        status_code = error.status_code
    else:
        # Generic error handling
        content = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        status_code = 500
        
        # Log the actual error
        logger.error(f"Unhandled error: {str(error)}", exc_info=True)
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


def handle_errors(
    fallback_message: str = "Operation failed",
    log_errors: bool = True
):
    """
    Decorator for handling errors in route handlers.
    
    Args:
        fallback_message: Message to use if error has no message
        log_errors: Whether to log errors
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppError as e:
                if log_errors:
                    logger.warning(f"{e.code}: {e.message}", extra={"details": e.details})
                return error_response(e)
            except HTTPException:
                raise  # Let FastAPI handle HTTP exceptions
            except Exception as e:
                if log_errors:
                    logger.error(f"Unhandled error in {func.__name__}: {str(e)}", exc_info=True)
                return error_response(
                    AppError(
                        message=str(e) or fallback_message,
                        user_message=fallback_message
                    )
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError as e:
                if log_errors:
                    logger.warning(f"{e.code}: {e.message}", extra={"details": e.details})
                raise HTTPException(
                    status_code=e.status_code,
                    detail={
                        "code": e.code,
                        "message": e.user_message,
                        "details": e.details
                    }
                )
            except HTTPException:
                raise
            except Exception as e:
                if log_errors:
                    logger.error(f"Unhandled error in {func.__name__}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "INTERNAL_ERROR",
                        "message": fallback_message
                    }
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class ErrorRecovery:
    """Utilities for error recovery and fallback mechanisms."""
    
    @staticmethod
    async def retry_async(
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """
        Retry an async function with exponential backoff.
        
        Args:
            func: Async function to retry
            max_attempts: Maximum number of attempts
            delay: Initial delay between attempts
            backoff: Backoff multiplier
            exceptions: Tuple of exceptions to catch
            
        Returns:
            Result of the function
            
        Raises:
            Last exception if all attempts fail
        """
        last_exception = None
        current_delay = delay
        
        for attempt in range(max_attempts):
            try:
                return await func()
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                else:
                    logger.error(f"All {max_attempts} attempts failed")
        
        raise last_exception
    
    @staticmethod
    def with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """
        Execute primary function with fallback on failure.
        
        Args:
            primary_func: Primary function to execute
            fallback_func: Fallback function if primary fails
            exceptions: Exceptions to trigger fallback
            
        Returns:
            Result from primary or fallback function
        """
        try:
            return primary_func()
        except exceptions as e:
            logger.warning(f"Primary function failed: {str(e)}. Using fallback.")
            return fallback_func()
    
    @staticmethod
    async def with_timeout(
        func: Callable,
        timeout: float,
        timeout_message: str = "Operation timed out"
    ) -> Any:
        """
        Execute async function with timeout.
        
        Args:
            func: Async function to execute
            timeout: Timeout in seconds
            timeout_message: Error message on timeout
            
        Returns:
            Result of the function
            
        Raises:
            ProcessingError: If timeout occurs
        """
        try:
            return await asyncio.wait_for(func(), timeout=timeout)
        except asyncio.TimeoutError:
            raise ProcessingError(
                timeout_message,
                details={"timeout": timeout}
            )
    
    @staticmethod
    def cleanup_on_error(cleanup_func: Callable):
        """
        Decorator to ensure cleanup is performed on error.
        
        Args:
            cleanup_func: Function to call for cleanup
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.info("Performing cleanup after error")
                    try:
                        if asyncio.iscoroutinefunction(cleanup_func):
                            await cleanup_func()
                        else:
                            cleanup_func()
                    except Exception as cleanup_error:
                        logger.error(f"Cleanup failed: {str(cleanup_error)}")
                    raise e
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.info("Performing cleanup after error")
                    try:
                        cleanup_func()
                    except Exception as cleanup_error:
                        logger.error(f"Cleanup failed: {str(cleanup_error)}")
                    raise e
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for handling failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            ProcessingError: If circuit is open
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise ProcessingError(
                    "Service temporarily unavailable",
                    details={"circuit_state": "open"}
                )
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) \
                     else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        
        from datetime import datetime, timedelta
        return datetime.now() >= self.last_failure_time + timedelta(seconds=self.recovery_timeout)
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call."""
        from datetime import datetime
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")


def log_error(error: Exception, context: Optional[Dict] = None):
    """
    Log error with context and traceback.
    
    Args:
        error: The error to log
        context: Additional context information
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if context:
        error_info["context"] = context
    
    if isinstance(error, AppError):
        error_info["error_code"] = error.code
        error_info["error_details"] = error.details
    
    logger.error("Error occurred", extra=error_info)