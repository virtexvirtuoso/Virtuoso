"""
Decorator utilities for the monitoring system.

This module provides decorators for error handling, performance tracking,
retry logic, and other cross-cutting concerns.
"""

import functools
import logging
import time
import asyncio
import traceback
from typing import Any, Callable, Optional, TypeVar, Union


# Type variable for preserving function signatures
F = TypeVar('F', bound=Callable[..., Any])


def handle_monitoring_error(
    logger: Optional[logging.Logger] = None,
    default_return: Any = None,
    reraise: bool = False
) -> Callable[[F], F]:
    """Decorator to handle monitoring errors gracefully.
    
    This decorator catches exceptions in monitoring functions and logs them
    appropriately, optionally returning a default value or re-raising the error.
    
    Args:
        logger: Logger to use for error logging. If None, uses function's module logger.
        default_return: Default value to return on error.
        reraise: If True, re-raises the exception after logging.
    
    Returns:
        Decorated function with error handling.
        
    Examples:
        >>> @handle_monitoring_error(default_return={})
        ... async def fetch_data():
        ...     # This function will return {} on error
        ...     pass
        >>> 
        >>> @handle_monitoring_error(reraise=True)
        ... async def critical_operation():
        ...     # This function will log and re-raise errors
        ...     pass
    """
    def decorator(func: F) -> F:
        """Inner decorator function."""
        
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """Async wrapper with error handling."""
                nonlocal logger
                
                # Get logger if not provided
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    logger.debug(f"Stack trace:\n{traceback.format_exc()}")
                    
                    if reraise:
                        raise
                    
                    return default_return
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                """Sync wrapper with error handling."""
                nonlocal logger
                
                # Get logger if not provided
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    logger.debug(f"Stack trace:\n{traceback.format_exc()}")
                    
                    if reraise:
                        raise
                    
                    return default_return
            
            return sync_wrapper
    
    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable[[F], F]:
    """Decorator to retry a function on error with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries in seconds.
        backoff_factor: Factor to multiply delay by after each failure.
        exceptions: Tuple of exceptions to catch and retry on.
        logger: Logger for retry messages.
    
    Returns:
        Decorated function with retry logic.
        
    Examples:
        >>> @retry_on_error(max_attempts=3, delay=1.0)
        ... async def unreliable_api_call():
        ...     # Will retry up to 3 times with exponential backoff
        ...     pass
    """
    def decorator(func: F) -> F:
        """Inner decorator function."""
        
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """Async wrapper with retry logic."""
                nonlocal logger
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                current_delay = delay
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): "
                                f"{str(e)}. Retrying in {current_delay:.1f}s..."
                            )
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff_factor
                        else:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                            )
                
                raise last_exception
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                """Sync wrapper with retry logic."""
                nonlocal logger
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                current_delay = delay
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): "
                                f"{str(e)}. Retrying in {current_delay:.1f}s..."
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff_factor
                        else:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                            )
                
                raise last_exception
            
            return sync_wrapper
    
    return decorator


def measure_performance(
    logger: Optional[logging.Logger] = None,
    metric_name: Optional[str] = None,
    log_args: bool = False
) -> Callable[[F], F]:
    """Decorator to measure function execution time.
    
    Args:
        logger: Logger for performance metrics.
        metric_name: Custom metric name (defaults to function name).
        log_args: If True, logs function arguments.
    
    Returns:
        Decorated function with performance measurement.
        
    Examples:
        >>> @measure_performance(metric_name="data_fetch")
        ... async def fetch_market_data(symbol):
        ...     # Execution time will be logged
        ...     pass
    """
    def decorator(func: F) -> F:
        """Inner decorator function."""
        
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """Async wrapper with performance measurement."""
                nonlocal logger
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                name = metric_name or func.__name__
                
                if log_args:
                    logger.debug(f"Starting {name} with args={args}, kwargs={kwargs}")
                
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.debug(f"{name} completed in {elapsed:.3f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.debug(f"{name} failed after {elapsed:.3f}s: {str(e)}")
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                """Sync wrapper with performance measurement."""
                nonlocal logger
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                name = metric_name or func.__name__
                
                if log_args:
                    logger.debug(f"Starting {name} with args={args}, kwargs={kwargs}")
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.debug(f"{name} completed in {elapsed:.3f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.debug(f"{name} failed after {elapsed:.3f}s: {str(e)}")
                    raise
            
            return sync_wrapper
    
    return decorator


def rate_limit(
    calls: int,
    period: float,
    logger: Optional[logging.Logger] = None
) -> Callable[[F], F]:
    """Decorator to rate limit function calls.
    
    Args:
        calls: Maximum number of calls allowed.
        period: Time period in seconds.
        logger: Logger for rate limit messages.
    
    Returns:
        Decorated function with rate limiting.
        
    Examples:
        >>> @rate_limit(calls=10, period=60.0)
        ... async def api_call():
        ...     # Limited to 10 calls per minute
        ...     pass
    """
    def decorator(func: F) -> F:
        """Inner decorator function."""
        
        # Track call times
        call_times = []
        lock = asyncio.Lock() if asyncio.iscoroutinefunction(func) else None
        
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """Async wrapper with rate limiting."""
                nonlocal logger
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                async with lock:
                    now = time.time()
                    
                    # Remove old calls outside the period
                    call_times[:] = [t for t in call_times if now - t < period]
                    
                    # Check if we've exceeded the limit
                    if len(call_times) >= calls:
                        wait_time = period - (now - call_times[0])
                        logger.warning(
                            f"{func.__name__} rate limited. Waiting {wait_time:.1f}s"
                        )
                        await asyncio.sleep(wait_time)
                        
                        # After waiting, clean up old calls again
                        now = time.time()
                        call_times[:] = [t for t in call_times if now - t < period]
                    
                    # Record this call
                    call_times.append(now)
                
                return await func(*args, **kwargs)
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                """Sync wrapper with rate limiting."""
                nonlocal logger
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                now = time.time()
                
                # Remove old calls outside the period
                call_times[:] = [t for t in call_times if now - t < period]
                
                # Check if we've exceeded the limit
                if len(call_times) >= calls:
                    wait_time = period - (now - call_times[0])
                    logger.warning(
                        f"{func.__name__} rate limited. Waiting {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    
                    # After waiting, clean up old calls again
                    now = time.time()
                    call_times[:] = [t for t in call_times if now - t < period]
                
                # Record this call
                call_times.append(now)
                
                return func(*args, **kwargs)
            
            return sync_wrapper
    
    return decorator


def validate_arguments(**validators) -> Callable[[F], F]:
    """Decorator to validate function arguments.
    
    Args:
        **validators: Keyword arguments mapping parameter names to validation functions.
    
    Returns:
        Decorated function with argument validation.
        
    Examples:
        >>> @validate_arguments(
        ...     symbol=lambda s: isinstance(s, str) and len(s) > 0,
        ...     limit=lambda l: isinstance(l, int) and l > 0
        ... )
        ... async def fetch_data(symbol: str, limit: int):
        ...     pass
    """
    def decorator(func: F) -> F:
        """Inner decorator function."""
        
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """Async wrapper with argument validation."""
                # Get function signature
                import inspect
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                
                # Validate arguments
                for param_name, validator in validators.items():
                    if param_name in bound.arguments:
                        value = bound.arguments[param_name]
                        if not validator(value):
                            raise ValueError(
                                f"Invalid argument {param_name}={value} for {func.__name__}"
                            )
                
                return await func(*args, **kwargs)
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                """Sync wrapper with argument validation."""
                # Get function signature
                import inspect
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                
                # Validate arguments
                for param_name, validator in validators.items():
                    if param_name in bound.arguments:
                        value = bound.arguments[param_name]
                        if not validator(value):
                            raise ValueError(
                                f"Invalid argument {param_name}={value} for {func.__name__}"
                            )
                
                return func(*args, **kwargs)
            
            return sync_wrapper
    
    return decorator