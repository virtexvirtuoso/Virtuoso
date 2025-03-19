"""Error handling utilities."""

import logging
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from datetime import datetime

logger = logging.getLogger(__name__)

# Type variable for generic function type
F = TypeVar('F', bound=Callable[..., Any])

class TradingError(Exception):
    """Base class for trading system errors."""
    pass

class ValidationError(TradingError):
    """Error raised when data validation fails."""
    pass

class MarketDataError(TradingError):
    """Error raised when there are issues with market data."""
    pass

class CalculationError(TradingError):
    """Error raised when calculations fail."""
    pass

class ConfigurationError(TradingError):
    """Error raised when there are configuration issues."""
    pass

def handle_calculation_error(default_value: Any = None) -> Callable[[F], F]:
    """Decorator to handle calculation errors.
    
    Args:
        default_value: Value to return if calculation fails
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Calculation error in {func.__name__}: {str(e)}")
                return default_value
        return cast(F, wrapper)
    return decorator

def handle_indicator_error(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to handle errors in indicator calculations.
    Returns a default value if an error occurs.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function that handles errors
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(self.__class__.__name__)
            logger.error(f"Error in {func.__name__}: {str(e)}")
            
            # If the class has a _get_default_scores method, use it
            if hasattr(self, '_get_default_scores'):
                return self._get_default_scores(f"Error in {func.__name__}: {str(e)}")
            
            # Otherwise return a neutral score with error info
            return {
                'score': 50.0,
                'status': 'error',
                'message': f"Error in {func.__name__}: {str(e)}",
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
    return wrapper

def validate_input(validation_func: Callable[..., bool]) -> Callable[[F], F]:
    """Decorator to validate input parameters.
    
    Args:
        validation_func: Function that validates input parameters
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not validation_func(*args, **kwargs):
                raise ValidationError(f"Input validation failed for {func.__name__}")
            return func(*args, **kwargs)
        return cast(F, wrapper)
    return decorator

def log_exceptions(logger: logging.Logger) -> Callable[[F], F]:
    """Decorator to log exceptions.
    
    Args:
        logger: Logger instance to use for logging
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {str(e)}", exc_info=True)
                raise
        return cast(F, wrapper)
    return decorator

def retry_on_error(max_attempts: int = 3, delay: float = 1.0) -> Callable[[F], F]:
    """Decorator to retry function on error.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import time
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        logger.error(f"Max retry attempts ({max_attempts}) reached for {func.__name__}")
                        raise
                    logger.warning(f"Attempt {attempts} failed for {func.__name__}: {str(e)}")
                    time.sleep(delay)
            return None
        return cast(F, wrapper)
    return decorator

def measure_execution_time(logger: logging.Logger) -> Callable[[F], F]:
    """Decorator to measure function execution time.
    
    Args:
        logger: Logger instance to use for logging
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = datetime.now()
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"{func.__name__} executed in {execution_time:.3f} seconds")
            return result
        return cast(F, wrapper)
    return decorator 