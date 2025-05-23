"""Time utility functions for market monitoring."""

import functools
import logging
import traceback
from typing import Callable, Any


def ccxt_time_to_minutes(timeframe: str) -> int:
    """Convert CCXT timeframe string to minutes.
    
    Args:
        timeframe: Timeframe string (e.g., '1m', '5m', '1h', '1d')
        
    Returns:
        Number of minutes in the timeframe
    """
    if not timeframe:
        return 0
    
    unit = timeframe[-1]
    value = int(timeframe[:-1]) if timeframe[:-1].isdigit() else 0
    
    if unit == 'm':
        return value
    elif unit == 'h':
        return value * 60
    elif unit == 'd':
        return value * 1440  # 24 * 60
    elif unit == 'w':
        return value * 10080  # 7 * 24 * 60
    else:
        return int(timeframe) if timeframe.isdigit() else 0


def handle_monitoring_error(func: Callable) -> Callable:
    """Decorator to handle monitoring errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    logger = logging.getLogger(__name__)
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    return wrapper 