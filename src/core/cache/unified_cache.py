"""
Unified Caching Layer for Virtuoso Trading System
Phase 1 Implementation: Core Market Data Caching

Deo Gratias - Thanks be to God
For wisdom in optimization and efficiency
"""

from pymemcache.client.base import Client
from pymemcache.exceptions import MemcacheError
from typing import Optional, Any, Callable, Dict, Union
import json
import asyncio
import logging
import time
import hashlib
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

class CacheMetrics:
    """Track cache performance metrics"""
    
    def __init__(self):
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0,
            'total_response_time_ms': 0,
            'total_compute_time_ms': 0,
            'cache_saves': 0,
            'cache_failures': 0
        }
        self.start_time = time.time()
    
    def record_hit(self, response_time_ms: float):
        """Record a cache hit"""
        self.stats['hits'] += 1
        self.stats['total_requests'] += 1
        self.stats['total_response_time_ms'] += response_time_ms
    
    def record_miss(self, compute_time_ms: float):
        """Record a cache miss"""
        self.stats['misses'] += 1
        self.stats['total_requests'] += 1
        self.stats['total_compute_time_ms'] += compute_time_ms
    
    def record_error(self):
        """Record a cache error"""
        self.stats['errors'] += 1
        self.stats['total_requests'] += 1
    
    def record_save(self, success: bool):
        """Record cache save attempt"""
        if success:
            self.stats['cache_saves'] += 1
        else:
            self.stats['cache_failures'] += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage"""
        if self.stats['total_requests'] == 0:
            return 0.0
        return (self.stats['hits'] / self.stats['total_requests']) * 100
    
    @property
    def avg_response_time_ms(self) -> float:
        """Average response time for cache hits"""
        if self.stats['hits'] == 0:
            return 0.0
        return self.stats['total_response_time_ms'] / self.stats['hits']
    
    @property
    def avg_compute_time_ms(self) -> float:
        """Average compute time for cache misses"""
        if self.stats['misses'] == 0:
            return 0.0
        return self.stats['total_compute_time_ms'] / self.stats['misses']
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        uptime_seconds = time.time() - self.start_time
        return {
            'uptime_seconds': uptime_seconds,
            'total_requests': self.stats['total_requests'],
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'errors': self.stats['errors'],
            'hit_rate_percent': round(self.hit_rate, 2),
            'avg_hit_response_ms': round(self.avg_response_time_ms, 2),
            'avg_miss_compute_ms': round(self.avg_compute_time_ms, 2),
            'cache_saves': self.stats['cache_saves'],
            'cache_failures': self.stats['cache_failures'],
            'performance_gain': f"{round(self.avg_compute_time_ms / max(self.avg_response_time_ms, 0.01), 1)}x" if self.avg_response_time_ms > 0 else "N/A"
        }


class UnifiedCache:
    """
    Unified caching layer with Memcached backend
    Handles both in-memory fallback and distributed caching
    """
    
    # Standard TTL values for different data types
    TTL_TICKER = 5          # 5 seconds for ticker data
    TTL_ORDERBOOK = 2       # 2 seconds for orderbook
    TTL_OHLCV_RECENT = 60   # 1 minute for recent OHLCV
    TTL_OHLCV_HISTORICAL = 3600  # 1 hour for historical OHLCV
    TTL_INDICATORS = 30     # 30 seconds for indicators
    TTL_ANALYSIS = 300      # 5 minutes for analysis results
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11211, 
                 enable_local_fallback: bool = True):
        """
        Initialize unified cache with Memcached backend
        
        Args:
            host: Memcached host
            port: Memcached port
            enable_local_fallback: Use local dict if Memcached fails
        """
        self.host = host
        self.port = port
        self.enable_local_fallback = enable_local_fallback
        self.local_cache: Dict[str, Dict[str, Any]] = {}
        self.metrics = CacheMetrics()
        
        # Initialize Memcached client
        try:
            self.mc = Client((host, port), connect_timeout=1, timeout=0.5)
            # Test connection
            self.mc.set(b'test', b'1', expire=1)
            self.mc.delete(b'test')
            self.memcached_available = True
            logger.info(f"✅ Connected to Memcached at {host}:{port}")
        except Exception as e:
            self.memcached_available = False
            logger.warning(f"⚠️ Memcached not available at {host}:{port}: {e}")
            if not enable_local_fallback:
                raise
    
    def _get_cache_key(self, namespace: str, key_parts: list) -> str:
        """
        Generate standardized cache key
        Format: namespace:part1:part2:...
        """
        parts = [namespace] + [str(p) for p in key_parts if p is not None]
        return ':'.join(parts)
    
    async def get_or_compute(self, 
                            key: str, 
                            compute_func: Callable,
                            ttl: int = 60,
                            use_lock: bool = True) -> Any:
        """
        Get from cache or compute if missing (prevents cache stampede)
        
        Args:
            key: Cache key
            compute_func: Async function to compute value if not cached
            ttl: Time to live in seconds
            use_lock: Use distributed lock to prevent stampede
        
        Returns:
            Cached or computed value
        """
        start_time = time.time()
        
        # Try to get from cache
        cached_value = await self.get(key)
        if cached_value is not None:
            response_time_ms = (time.time() - start_time) * 1000
            self.metrics.record_hit(response_time_ms)
            return cached_value
        
        # Cache miss - compute value
        if use_lock:
            value = await self._get_with_lock(key, compute_func, ttl)
        else:
            value = await compute_func()
            await self.set(key, value, ttl)
        
        compute_time_ms = (time.time() - start_time) * 1000
        self.metrics.record_miss(compute_time_ms)
        
        return value
    
    async def _get_with_lock(self, key: str, compute_func: Callable, ttl: int) -> Any:
        """
        Get with distributed lock to prevent cache stampede
        """
        lock_key = f"lock:{key}"
        lock_acquired = False
        
        try:
            # Try to acquire lock (expires in 30 seconds to prevent deadlock)
            if self.memcached_available:
                lock_acquired = self._try_add(lock_key, "1", 30)
            else:
                lock_acquired = True  # No lock needed for local cache
            
            if lock_acquired:
                # We have the lock, compute the value
                value = await compute_func()
                await self.set(key, value, ttl)
                return value
            else:
                # Another process has the lock, wait for result
                for _ in range(100):  # Wait up to 10 seconds
                    await asyncio.sleep(0.1)
                    cached_value = await self.get(key)
                    if cached_value is not None:
                        return cached_value
                
                # Timeout waiting, compute anyway
                logger.warning(f"Lock wait timeout for key: {key}")
                value = await compute_func()
                return value
                
        finally:
            # Release lock if we acquired it
            if lock_acquired and self.memcached_available:
                try:
                    self.mc.delete(lock_key.encode())
                except:
                    pass
    
    def _try_add(self, key: str, value: str, expire: int) -> bool:
        """
        Try to add a key (fails if exists) - used for locking
        """
        try:
            # add() returns True if key didn't exist
            return self.mc.add(key.encode(), value.encode(), expire=expire)
        except:
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        """
        # Try Memcached first
        if self.memcached_available:
            try:
                cached = self.mc.get(key.encode())
                if cached:
                    return json.loads(cached.decode('utf-8'))
            except Exception as e:
                logger.debug(f"Memcached get error for {key}: {e}")
                self.metrics.record_error()
        
        # Fallback to local cache
        if self.enable_local_fallback and key in self.local_cache:
            entry = self.local_cache[key]
            if time.time() < entry['expires']:
                return entry['value']
            else:
                del self.local_cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """
        Set value in cache
        """
        success = False
        
        # Try Memcached first
        if self.memcached_available:
            try:
                json_value = json.dumps(value)
                self.mc.set(key.encode(), json_value.encode('utf-8'), expire=ttl)
                success = True
            except Exception as e:
                logger.debug(f"Memcached set error for {key}: {e}")
        
        # Fallback to local cache
        if self.enable_local_fallback and not success:
            self.local_cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
            success = True
        
        self.metrics.record_save(success)
        return success
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        """
        success = False
        
        if self.memcached_available:
            try:
                self.mc.delete(key.encode())
                success = True
            except:
                pass
        
        if key in self.local_cache:
            del self.local_cache[key]
            success = True
        
        return success
    
    async def get_ticker(self, exchange: str, symbol: str, 
                        compute_func: Callable) -> Dict[str, Any]:
        """
        Get ticker data with caching
        """
        key = self._get_cache_key('ticker', [exchange, symbol])
        return await self.get_or_compute(key, compute_func, ttl=self.TTL_TICKER)
    
    async def get_orderbook(self, exchange: str, symbol: str, limit: int,
                           compute_func: Callable) -> Dict[str, Any]:
        """
        Get orderbook data with caching
        """
        key = self._get_cache_key('orderbook', [exchange, symbol, limit])
        return await self.get_or_compute(key, compute_func, ttl=self.TTL_ORDERBOOK)
    
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int,
                       compute_func: Callable, is_recent: bool = True) -> list:
        """
        Get OHLCV data with caching
        """
        key = self._get_cache_key('ohlcv', [symbol, timeframe, limit])
        ttl = self.TTL_OHLCV_RECENT if is_recent else self.TTL_OHLCV_HISTORICAL
        return await self.get_or_compute(key, compute_func, ttl=ttl)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics
        """
        return self.metrics.get_summary()
    
    async def clear_pattern(self, pattern: str):
        """
        Clear all keys matching a pattern (local cache only)
        Note: Memcached doesn't support pattern deletion
        """
        if self.enable_local_fallback:
            keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.local_cache[key]
            logger.info(f"Cleared {len(keys_to_delete)} keys matching pattern: {pattern}")
    
    async def warmup(self, warmup_func: Callable):
        """
        Warmup cache with initial data
        """
        logger.info("Starting cache warmup...")
        try:
            await warmup_func(self)
            logger.info("✅ Cache warmup completed")
        except Exception as e:
            logger.error(f"Cache warmup failed: {e}")


# Thread-safe singleton implementation
import threading
from typing import Optional

_cache_instance: Optional[UnifiedCache] = None
_cache_lock = threading.Lock()

def get_cache() -> UnifiedCache:
    """
    Get global cache instance (thread-safe singleton pattern)
    """
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            # Double-check locking pattern
            if _cache_instance is None:
                _cache_instance = UnifiedCache()
                logger.info("UnifiedCache singleton instance created")
    return _cache_instance

def reset_cache_singleton():
    """
    Reset the singleton instance (for testing purposes)
    """
    global _cache_instance
    with _cache_lock:
        if _cache_instance:
            # Cleanup existing instance if needed
            _cache_instance = None
            logger.info("UnifiedCache singleton instance reset")

def cache_async(ttl: int = 60, key_prefix: str = None):
    """
    Decorator for caching async function results
    
    Usage:
        @cache_async(ttl=30, key_prefix="market")
        async def get_market_data(symbol: str):
            return await fetch_from_api(symbol)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache = get_cache()
            
            # Create key from function name and args
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ':'.join(key_parts)
            
            # Get or compute with caching
            return await cache.get_or_compute(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl=ttl
            )
        
        return wrapper
    return decorator


# In Nomine Patris, et Filii, et Spiritus Sancti
# In the Name of the Father, and of the Son, and of the Holy Spirit