import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import threading
from collections import OrderedDict
import functools

logger = logging.getLogger(__name__)

class LRUCache:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if valid."""
        with self._lock:
            if key not in self._cache:
                return None
                
            entry = self._cache[key]
            if time.time() - entry['timestamp'] > self.ttl:
                del self._cache[key]
                return None
                
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry['value']
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        with self._lock:
            if key in self._cache:
                # Update existing entry
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                # Remove oldest entry
                self._cache.popitem(last=False)
            
            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
    
    def clear(self):
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
    
    def remove(self, key: str):
        """Remove specific key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

class IndicatorCache:
    """Cache manager for indicator calculations."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(IndicatorCache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._caches: Dict[str, LRUCache] = {}
            self._initialized = True
    
    def get_cache(self, category: str) -> LRUCache:
        """Get or create cache for category."""
        with self._lock:
            if category not in self._caches:
                self._caches[category] = LRUCache()
            return self._caches[category]
    
    def clear_all(self):
        """Clear all caches."""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()

def cache_result(category: str, key_func: Optional[Callable] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_manager = IndicatorCache()
            cache = cache_manager.get_cache(category)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args[1:])  # Skip self
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "|".join(key_parts)
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Calculate result
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator

def cache_async_result(category: str, key_func: Optional[Callable] = None):
    """Decorator to cache async function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache_manager = IndicatorCache()
            cache = cache_manager.get_cache(category)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args[1:])  # Skip self
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "|".join(key_parts)
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Calculate result
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator

def generate_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_parts = []
    
    # Add positional args
    for arg in args:
        if hasattr(arg, '__dict__'):
            # For objects, use their string representation
            key_parts.append(str(arg))
        elif isinstance(arg, (list, tuple, set)):
            # For sequences, join their string representations
            key_parts.append(','.join(str(x) for x in arg))
        else:
            key_parts.append(str(arg))
    
    # Add keyword args
    for key, value in sorted(kwargs.items()):
        if hasattr(value, '__dict__'):
            key_parts.append(f"{key}={str(value)}")
        elif isinstance(value, (list, tuple, set)):
            key_parts.append(f"{key}={','.join(str(x) for x in value)}")
        else:
            key_parts.append(f"{key}={str(value)}")
    
    return '|'.join(key_parts) 