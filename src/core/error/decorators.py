from src.utils.task_tracker import create_tracked_task
"""Error handling decorators."""

import logging
import functools
import asyncio
from typing import Any, Callable, Optional, Type, Union, TypeVar
from datetime import datetime

from .models import ErrorSeverity
from .exceptions import (
    SystemError, ComponentError, OperationError,
    TimeoutError, ValidationError
)

F = TypeVar('F', bound=Callable[..., Any])

def handle_errors(
    error_handler: Any,
    component: str,
    severity: str = "error",
    retries: int = 0,
    retry_delay: float = 1.0,
    timeout: Optional[float] = None,
    handled_exceptions: Optional[tuple[Type[Exception], ...]] = None
) -> Callable[[F], F]:
    """Decorator for standardized error handling.
    
    Args:
        error_handler: Error handler instance
        component: Component name
        severity: Error severity level
        retries: Number of retry attempts
        retry_delay: Delay between retries in seconds
        timeout: Optional timeout in seconds
        handled_exceptions: Tuple of exception types to handle
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            operation = func.__name__
            
            while True:
                try:
                    if timeout is not None:
                        return await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=timeout
                        )
                    return await func(*args, **kwargs)
                    
                except asyncio.TimeoutError as e:
                    await error_handler.handle_error(
                        TimeoutError(f"Operation timed out after {timeout}s"),
                        f"{component}_{operation}",
                        severity
                    )
                    raise
                    
                except Exception as e:
                    if handled_exceptions and not isinstance(e, handled_exceptions):
                        raise
                    
                    attempt += 1
                    await error_handler.handle_error(
                        e, f"{component}_{operation}", severity
                    )
                    
                    if attempt > retries:
                        raise
                    
                    await asyncio.sleep(retry_delay)
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            operation = func.__name__
            
            while True:
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    if handled_exceptions and not isinstance(e, handled_exceptions):
                        raise
                    
                    attempt += 1
                    create_tracked_task(
                        error_handler.handle_error(
                            e, f"{component}_{operation}", severity
                        , name="auto_tracked_task")
                    )
                    
                    if attempt > retries:
                        raise
                    
                    if retry_delay > 0:
                        asyncio.sleep(retry_delay)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def validate_input(validation_func: Callable[..., bool]) -> Callable[[F], F]:
    """Decorator to validate function input.
    
    Args:
        validation_func: Function that validates input parameters
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not validation_func(*args, **kwargs):
                raise ValidationError(
                    f"Input validation failed for {func.__name__}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

def measure_execution(logger: logging.Logger) -> Callable[[F], F]:
    """Decorator to measure function execution time.
    
    Args:
        logger: Logger instance
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = datetime.utcnow()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(
                    f"{func.__name__} executed in {execution_time:.3f} seconds"
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = datetime.utcnow()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(
                    f"{func.__name__} executed in {execution_time:.3f} seconds"
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 