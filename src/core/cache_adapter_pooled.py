"""
Direct Cache Adapter with Connection Pooling
High-performance cache operations with singleton connection pool
"""

import asyncio
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import aiomcache
import time

logger = logging.getLogger(__name__)

class SingletonMeta(type):
    """Singleton metaclass for connection pool"""
    _instances = {}
    _locks = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            if cls not in cls._locks:
                cls._locks[cls] = asyncio.Lock()
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class ConnectionPool:
    """Singleton connection pool for memcached"""
    def __init__(self):
        self._client = None
        self._lock = asyncio.Lock()
        self._last_reset = time.time()
        
    async def get_client(self):
        """Get or create pooled client"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = aiomcache.Client('localhost', 11211)
                    logger.info("Created new memcached connection pool with size 20")
        
        # Reset connection pool every hour to prevent stale connections
        if time.time() - self._last_reset > 3600:
            await self.reset_pool()
            
        return self._client
    
    async def reset_pool(self):
        """Reset the connection pool"""
        async with self._lock:
            if self._client:
                try:
                    await self._client.close()
                except:
                    pass
                self._client = None
                self._last_reset = time.time()
                logger.info("Reset memcached connection pool")

# Global connection pool instance
_connection_pool = ConnectionPool()

class DirectCacheAdapter:
    """High-performance cache adapter with connection pooling"""
    
    def __init__(self):
        self.logger = logger
        self._stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }
        
    async def _get_client(self):
        """Get pooled client"""
        return await _connection_pool.get_client()
    
    async def _get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with timeout protection"""
        self._stats['total_requests'] += 1
        
        try:
            client = await self._get_client()
            
            # Add timeout protection
            data = await asyncio.wait_for(
                client.get(key.encode() if isinstance(key, str) else key),
                timeout=0.5  # 500ms timeout
            )
            
            if data is not None:
                self._stats['hits'] += 1
                return json.loads(data.decode()) if isinstance(data, bytes) else data
            else:
                self._stats['misses'] += 1
                return default
                
        except asyncio.TimeoutError:
            self.logger.warning(f"Cache timeout for key: {key}")
            self._stats['errors'] += 1
            return default
        except Exception as e:
            self.logger.error(f"Cache get error for {key}: {e}")
            self._stats['errors'] += 1
            return default
    
    async def _set(self, key: str, value: Any, ttl: int = 30) -> bool:
        """Set value in cache"""
        try:
            client = await self._get_client()
            
            if value is None:
                return False
                
            data = json.dumps(value) if not isinstance(value, (str, bytes)) else value
            
            await asyncio.wait_for(
                client.set(
                    key.encode() if isinstance(key, str) else key,
                    data.encode() if isinstance(data, str) else data,
                    exptime=ttl
                ),
                timeout=0.5  # 500ms timeout
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Cache set error for {key}: {e}")
            return False
    
    async def _delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            client = await self._get_client()
            await client.delete(key.encode() if isinstance(key, str) else key)
            return True
        except Exception as e:
            self.logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values in parallel"""
        try:
            client = await self._get_client()
            
            # Encode keys
            encoded_keys = [k.encode() if isinstance(k, str) else k for k in keys]
            
            # Get all values in parallel
            results = await asyncio.wait_for(
                client.multi_get(*encoded_keys),
                timeout=1.0
            )
            
            # Decode results - aiomcache returns tuple format
            decoded = {}
            if isinstance(results, dict):
                for key, value in results.items():
                    if value:
                        try:
                            decoded_key = key.decode() if isinstance(key, bytes) else key
                            decoded[decoded_key] = json.loads(value.decode()) if isinstance(value, bytes) else value
                        except:
                            pass
            elif isinstance(results, (list, tuple)):
                # Handle tuple format from aiomcache
                for i, key in enumerate(encoded_keys):
                    if i < len(results) and results[i]:
                        try:
                            decoded_key = key.decode() if isinstance(key, bytes) else key
                            decoded[decoded_key] = json.loads(results[i].decode()) if isinstance(results[i], bytes) else results[i]
                        except:
                            pass
                        
            return decoded
            
        except Exception as e:
            self.logger.error(f"Multi-get error: {e}")
            return {}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = 0
        if self._stats['total_requests'] > 0:
            hit_rate = (self._stats['hits'] / self._stats['total_requests']) * 100
            
        return {
            'hit_rate': round(hit_rate, 2),
            'total_requests': self._stats['total_requests'],
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'errors': self._stats['errors']
        }
    
    # Public methods for backward compatibility
    async def get(self, key: str, default: Any = None) -> Any:
        return await self._get(key, default)
    
    async def set(self, key: str, value: Any, ttl: int = 30) -> bool:
        return await self._set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        return await self._delete(key)

# Global cache adapter instance
cache_adapter = DirectCacheAdapter()
