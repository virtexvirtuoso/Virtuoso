from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheManager:
    """Manages cached results with configurable TTL."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache if not expired."""
        if key in self._cache:
            item = self._cache[key]
            if item['expiry'] > datetime.now():
                logger.debug(f"Cache hit for {key}")
                return item['value']
            else:
                logger.debug(f"Cache expired for {key}")
                del self._cache[key]
        return None
        
    def set(self, key: str, value: Any, ttl: timedelta) -> None:
        """Store item in cache with expiration."""
        self._cache[key] = {
            'value': value,
            'expiry': datetime.now() + ttl
        }
        logger.debug(f"Cached value for {key} with TTL {ttl}")
        
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        logger.debug("Cache cleared")

# Global cache instance
cache_manager = CacheManager()

def cached(ttl: Union[int, timedelta] = 300):
    """Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds or timedelta
    """
    if isinstance(ttl, int):
        ttl = timedelta(seconds=ttl)
        
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = cache_manager.get(key)
            if result is not None:
                return result
                
            # Calculate and cache result
            result = func(*args, **kwargs)
            cache_manager.set(key, result, ttl)
            return result
            
        return wrapper
    return decorator 