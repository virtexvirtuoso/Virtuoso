"""
Unified Cache Manager System
Consolidates all caching mechanisms into a single, efficient system
with connection pooling, automatic fallback, and performance monitoring
"""

import asyncio
import json
import time
import logging
from typing import Any, Dict, Optional, Union, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiomcache
from contextlib import asynccontextmanager
import threading
from collections import defaultdict
import pickle
import hashlib
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_requests: int = 0
    average_response_time: float = 0.0
    memory_usage_kb: float = 0.0
    last_reset: datetime = None
    
    def __post_init__(self):
        if self.last_reset is None:
            self.last_reset = datetime.now()
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100


class ConnectionPool:
    """Manages a pool of cache connections with automatic recycling"""
    
    def __init__(self, host: str = 'localhost', port: int = 11211, 
                 min_size: int = 5, max_size: int = 20):
        self.host = host
        self.port = port
        self.min_size = min_size
        self.max_size = max_size
        self._pool: List[aiomcache.Client] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._size = 0
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the connection pool with minimum connections"""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            for _ in range(self.min_size):
                conn = await self._create_connection()
                if conn:
                    self._pool.append(conn)
                    await self._available.put(conn)
                    self._size += 1
                    
            self._initialized = True
            logger.info(f"Connection pool initialized with {self._size} connections")
    
    async def _create_connection(self) -> Optional[aiomcache.Client]:
        """Create a new connection to cache server"""
        try:
            conn = aiomcache.Client(self.host, self.port)
            # Test the connection
            await conn.set(b'test_conn', b'1', exptime=1)
            await conn.delete(b'test_conn')
            return conn
        except Exception as e:
            logger.error(f"Failed to create cache connection: {e}")
            return None
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        if not self._initialized:
            await self.initialize()
            
        conn = None
        try:
            # Try to get an available connection
            try:
                conn = await asyncio.wait_for(self._available.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # Create a new connection if pool not at max
                async with self._lock:
                    if self._size < self.max_size:
                        conn = await self._create_connection()
                        if conn:
                            self._pool.append(conn)
                            self._size += 1
                        else:
                            # Fallback to any connection
                            if self._pool:
                                conn = self._pool[0]
            
            if conn:
                yield conn
            else:
                raise ConnectionError("No available connections in pool")
                
        finally:
            # Return connection to pool
            if conn and conn in self._pool:
                try:
                    await self._available.put(conn)
                except:
                    pass
    
    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            for conn in self._pool:
                try:
                    await conn.close()
                except:
                    pass
            self._pool.clear()
            self._size = 0
            self._initialized = False


class InMemoryCache:
    """Fallback in-memory cache implementation"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = threading.Lock()
        self.stats = CacheStats()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from in-memory cache"""
        with self._lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    self.stats.hits += 1
                    self.stats.total_requests += 1
                    return value
                else:
                    del self.cache[key]
            
            self.stats.misses += 1
            self.stats.total_requests += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in in-memory cache"""
        with self._lock:
            # Check size limit
            if len(self.cache) >= self.max_size:
                # Remove oldest entries (simple FIFO)
                to_remove = len(self.cache) - self.max_size + 1
                for k in list(self.cache.keys())[:to_remove]:
                    del self.cache[k]
            
            expiry = time.time() + (ttl or self.default_ttl)
            self.cache[key] = (value, expiry)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
    
    def get_memory_usage(self) -> float:
        """Estimate memory usage in KB"""
        try:
            # Rough estimation
            total_size = 0
            for key, (value, _) in self.cache.items():
                total_size += len(key.encode()) + len(pickle.dumps(value))
            return total_size / 1024
        except:
            return 0.0


class CacheManager:
    """
    Unified cache manager with singleton pattern, connection pooling,
    automatic fallback, and performance monitoring
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            # Connection pool for memcached
            self.connection_pool = ConnectionPool()
            
            # In-memory fallback cache
            self.memory_cache = InMemoryCache()
            
            # Performance statistics
            self.stats = CacheStats()
            
            # Circuit breaker for memcached
            self.memcached_failures = 0
            self.memcached_disabled_until = 0
            self.max_failures = 5
            self.circuit_breaker_timeout = 60  # seconds
            
            # Cache configuration
            self.default_ttl = 300  # 5 minutes
            self.use_compression = True
            
            self.initialized = True
            logger.info("Unified CacheManager initialized")
    
    def _is_memcached_available(self) -> bool:
        """Check if memcached is available (circuit breaker)"""
        if self.memcached_failures >= self.max_failures:
            if time.time() < self.memcached_disabled_until:
                return False
            else:
                # Reset circuit breaker
                self.memcached_failures = 0
                logger.info("Memcached circuit breaker reset")
        return True
    
    def _record_memcached_failure(self):
        """Record a memcached failure for circuit breaker"""
        self.memcached_failures += 1
        if self.memcached_failures >= self.max_failures:
            self.memcached_disabled_until = time.time() + self.circuit_breaker_timeout
            logger.warning(f"Memcached circuit breaker triggered, disabled for {self.circuit_breaker_timeout}s")
    
    def _generate_key(self, namespace: str, key: str) -> str:
        """Generate a namespaced cache key"""
        return f"{namespace}:{key}"
    
    async def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """
        Get value from cache with automatic fallback
        
        Args:
            namespace: Cache namespace (e.g., 'dashboard', 'market', 'signals')
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        start_time = time.time()
        cache_key = self._generate_key(namespace, key)
        
        try:
            # Try memcached first if available
            if self._is_memcached_available():
                try:
                    async with self.connection_pool.get_connection() as conn:
                        data = await conn.get(cache_key.encode())
                        if data:
                            value = json.loads(data.decode()) if data else None
                            self.stats.hits += 1
                            self.stats.total_requests += 1
                            self.memcached_failures = 0  # Reset on success
                            return value if value is not None else default
                except Exception as e:
                    logger.debug(f"Memcached get failed: {e}")
                    self._record_memcached_failure()
            
            # Fallback to in-memory cache
            value = self.memory_cache.get(cache_key)
            if value is not None:
                return value
            
            self.stats.misses += 1
            self.stats.total_requests += 1
            return default
            
        finally:
            # Update response time
            response_time = time.time() - start_time
            if self.stats.average_response_time == 0:
                self.stats.average_response_time = response_time
            else:
                self.stats.average_response_time = (
                    self.stats.average_response_time * 0.9 + response_time * 0.1
                )
    
    async def set(self, namespace: str, key: str, value: Any, 
                  ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 300)
            
        Returns:
            True if successful
        """
        cache_key = self._generate_key(namespace, key)
        ttl = ttl or self.default_ttl
        
        try:
            # Serialize value
            serialized = json.dumps(value) if value is not None else None
            
            # Try memcached first if available
            if self._is_memcached_available() and serialized:
                try:
                    async with self.connection_pool.get_connection() as conn:
                        await conn.set(
                            cache_key.encode(),
                            serialized.encode(),
                            exptime=ttl
                        )
                        self.memcached_failures = 0  # Reset on success
                except Exception as e:
                    logger.debug(f"Memcached set failed: {e}")
                    self._record_memcached_failure()
            
            # Always set in memory cache as well
            self.memory_cache.set(cache_key, value, ttl)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats.errors += 1
            return False
    
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete key from cache"""
        cache_key = self._generate_key(namespace, key)
        
        success = False
        
        # Try memcached
        if self._is_memcached_available():
            try:
                async with self.connection_pool.get_connection() as conn:
                    await conn.delete(cache_key.encode())
                    success = True
            except Exception as e:
                logger.debug(f"Memcached delete failed: {e}")
                self._record_memcached_failure()
        
        # Always delete from memory cache
        if self.memory_cache.delete(cache_key):
            success = True
        
        return success
    
    async def clear_namespace(self, namespace: str) -> bool:
        """Clear all keys in a namespace (memory cache only)"""
        try:
            keys_to_delete = [
                k for k in self.memory_cache.cache.keys() 
                if k.startswith(f"{namespace}:")
            ]
            for key in keys_to_delete:
                self.memory_cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"Clear namespace error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        memory_usage = self.memory_cache.get_memory_usage()
        self.stats.memory_usage_kb = memory_usage
        
        return {
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'errors': self.stats.errors,
            'total_requests': self.stats.total_requests,
            'hit_rate': self.stats.hit_rate,
            'average_response_time_ms': self.stats.average_response_time * 1000,
            'memory_usage_kb': memory_usage,
            'memory_cache_size': len(self.memory_cache.cache),
            'memcached_available': self._is_memcached_available(),
            'memcached_failures': self.memcached_failures,
            'connection_pool_size': self.connection_pool._size,
            'last_reset': self.stats.last_reset.isoformat() if self.stats.last_reset else None
        }
    
    async def reset_stats(self):
        """Reset performance statistics"""
        self.stats = CacheStats()
        self.memory_cache.stats = CacheStats()
        logger.info("Cache statistics reset")
    
    async def warmup(self, data: Dict[str, Dict[str, Any]]):
        """
        Warm up cache with initial data
        
        Args:
            data: Dictionary of {namespace: {key: value}}
        """
        tasks = []
        for namespace, items in data.items():
            for key, value in items.items():
                tasks.append(self.set(namespace, key, value))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Cache warmed up with {len(tasks)} entries")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache system"""
        health = {
            'status': 'healthy',
            'memory_cache': 'active',
            'memcached': 'unknown',
            'issues': []
        }
        
        # Check memcached
        if self._is_memcached_available():
            try:
                async with self.connection_pool.get_connection() as conn:
                    await conn.set(b'health_check', b'1', exptime=1)
                    result = await conn.get(b'health_check')
                    if result:
                        health['memcached'] = 'active'
                    else:
                        health['memcached'] = 'degraded'
                        health['issues'].append('Memcached write/read test failed')
            except Exception as e:
                health['memcached'] = 'failed'
                health['issues'].append(f'Memcached connection failed: {str(e)}')
                health['status'] = 'degraded'
        else:
            health['memcached'] = 'circuit_breaker_open'
            health['status'] = 'degraded'
        
        # Check memory usage
        memory_usage = self.memory_cache.get_memory_usage()
        if memory_usage > 100 * 1024:  # 100MB warning threshold
            health['issues'].append(f'High memory usage: {memory_usage/1024:.2f}MB')
            health['status'] = 'degraded'
        
        return health
    
    async def close(self):
        """Close all connections and cleanup"""
        await self.connection_pool.close_all()
        self.memory_cache.clear()
        logger.info("CacheManager closed")


# Global instance getter
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get the global CacheManager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Decorator for automatic caching
def cached(namespace: str, ttl: int = 300):
    """
    Decorator for automatic function result caching
    
    Args:
        namespace: Cache namespace
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = hashlib.md5("_".join(key_parts).encode()).hexdigest()
            
            # Get cache manager
            cache = get_cache_manager()
            
            # Try to get from cache
            result = await cache.get(namespace, key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(namespace, key, result, ttl)
            
            return result
        return wrapper
    return decorator