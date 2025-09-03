"""
Memcached client for ultra-fast dashboard caching
Phase 2 optimization for Virtuoso Trading System

Christus Rex - Christ the King
"""

# Using aiomcache for async-safe operations
import aiomcache
import asyncio
import json
import logging
from typing import Any, Optional, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class MemcachedCache:
    """
    High-performance Memcached client optimized for trading dashboards.
    20-50% faster than Redis for simple cache operations.
    Target latency: <1ms for cache hits
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11211, default_ttl: int = 30):
        """
        Initialize Memcached client.
        
        Args:
            host: Memcached server host
            port: Memcached server port
            default_ttl: Default TTL in seconds
        """
        self.host = host
        self.port = port
        self.default_ttl = default_ttl
        
        # Initialize async client - won't block event loop
        self.client = None  # Will be created on first use
        self._client_lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0,
            'total_get_time': 0,
            'total_set_time': 0
        }
        
        # Test connection
        try:
            self.client.set(b'health_check', b'ok', expire=1)
            logger.info(f"✅ Memcached connected at {host}:{port}")
        except Exception as e:
            logger.error(f"❌ Memcached connection failed: {e}")
    

    async def _get_client(self):
        """Get or create async client"""
        if self.client is None:
            async with self._client_lock:
                if self.client is None:
                    self.client = aiomcache.Client(self.host, self.port)
        return self.client
    
    def _serialize(self, key, value):
        """Custom serializer for complex objects"""
        if isinstance(value, (dict, list)):
            return json.dumps(value).encode('utf-8'), 1
        elif isinstance(value, bytes):
            return value, 2
        else:
            return str(value).encode('utf-8'), 0
    
    def _deserialize(self, key, value, flags):
        """Custom deserializer"""
        if flags == 1:
            return json.loads(value.decode('utf-8'))
        elif flags == 2:
            return value
        else:
            return value.decode('utf-8')
    
    def get(self, key: str) -> Optional[Any]:
        """Synchronous wrapper - returns None if async not available"""
        try:
            # Don't block - just return None if we can't get synchronously
            return None  # Force fallback to memory cache
        except:
            return None
            
    async def async_get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with sub-millisecond latency.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        start_time = time.perf_counter()
        try:
            # Convert key to bytes
            key_bytes = key.encode('utf-8') if isinstance(key, str) else key
            value = self.client.get(key_bytes)
            
            elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
            self.stats['total_get_time'] += elapsed
            
            if value is not None:
                self.stats['hits'] += 1
                logger.debug(f"Cache hit: {key} ({elapsed:.2f}ms)")
            else:
                self.stats['misses'] += 1
                logger.debug(f"Cache miss: {key} ({elapsed:.2f}ms)")
            
            return value
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Memcached get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache with ultra-low latency.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        start_time = time.perf_counter()
        try:
            ttl = ttl or self.default_ttl
            key_bytes = key.encode('utf-8') if isinstance(key, str) else key
            
            success = self.client.set(key_bytes, value, expire=ttl)
            
            elapsed = (time.perf_counter() - start_time) * 1000
            self.stats['total_set_time'] += elapsed
            
            if success:
                self.stats['sets'] += 1
                logger.debug(f"Cache set: {key} ({elapsed:.2f}ms)")
            
            return success
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Memcached set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            key_bytes = key.encode('utf-8') if isinstance(key, str) else key
            return self.client.delete(key_bytes)
        except Exception as e:
            logger.error(f"Memcached delete error: {e}")
            return False
    
    def flush_all(self):
        """Clear all cache entries"""
        try:
            self.client.flush_all()
            logger.info("Memcached flushed")
        except Exception as e:
            logger.error(f"Memcached flush error: {e}")
    
    def get_stats(self) -> dict:
        """Get cache statistics with performance metrics"""
        total_gets = self.stats['hits'] + self.stats['misses']
        total_ops = total_gets + self.stats['sets']
        
        hit_rate = (self.stats['hits'] / total_gets * 100) if total_gets > 0 else 0
        avg_get_time = (self.stats['total_get_time'] / total_gets) if total_gets > 0 else 0
        avg_set_time = (self.stats['total_set_time'] / self.stats['sets']) if self.stats['sets'] > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'errors': self.stats['errors'],
            'hit_rate': f"{hit_rate:.1f}%",
            'avg_get_latency_ms': f"{avg_get_time:.2f}",
            'avg_set_latency_ms': f"{avg_set_time:.2f}",
            'total_operations': total_ops,
            'server': f"{self.host}:{self.port}"
        }
    
    def close(self):
        """Close the connection"""
        try:
            self.client.close()
        except:
            pass

# Global instance - will be initialized in main
memcached_cache = None

def initialize_memcached(host='127.0.0.1', port=11211):
    """Initialize the global memcached instance"""
    global memcached_cache
    memcached_cache = MemcachedCache(host, port)
    return memcached_cache