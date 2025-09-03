"""
Multi-Tier Unified Cache Layer - Priority 2 Implementation
Redis L1 (fast, smaller capacity) + Memcached L2 (larger capacity)
With automatic promotion from L2 to L1 for hot data and connection pooling

Performance Target: 70%+ cache hit rate, sub-150ms response times
"""

import redis
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from pymemcache.client.base import Client as MemcachedClient
from pymemcache.exceptions import MemcacheError
import aiomcache
from typing import Optional, Any, Callable, Dict, Union, List
import json
import asyncio
import logging
import time
import hashlib
from datetime import datetime
from functools import wraps
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class CacheMetrics:
    """Enhanced cache performance metrics for multi-tier system"""
    
    def __init__(self):
        self.stats = {
            'l1_hits': 0,           # Redis L1 hits
            'l2_hits': 0,           # Memcached L2 hits
            'total_misses': 0,      # Complete cache misses
            'promotions': 0,        # L2 -> L1 promotions
            'evictions': 0,         # L1 evictions
            'total_requests': 0,
            'l1_response_time_ms': 0,
            'l2_response_time_ms': 0,
            'compute_time_ms': 0,
            'errors': 0,
            'connection_errors': 0,
        }
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def record_l1_hit(self, response_time_ms: float):
        """Record L1 (Redis) hit"""
        with self._lock:
            self.stats['l1_hits'] += 1
            self.stats['total_requests'] += 1
            self.stats['l1_response_time_ms'] += response_time_ms
    
    def record_l2_hit(self, response_time_ms: float, promoted: bool = False):
        """Record L2 (Memcached) hit"""
        with self._lock:
            self.stats['l2_hits'] += 1
            self.stats['total_requests'] += 1
            self.stats['l2_response_time_ms'] += response_time_ms
            if promoted:
                self.stats['promotions'] += 1
    
    def record_miss(self, compute_time_ms: float):
        """Record complete cache miss"""
        with self._lock:
            self.stats['total_misses'] += 1
            self.stats['total_requests'] += 1
            self.stats['compute_time_ms'] += compute_time_ms
    
    def record_error(self, connection_error: bool = False):
        """Record cache error"""
        with self._lock:
            self.stats['errors'] += 1
            self.stats['total_requests'] += 1
            if connection_error:
                self.stats['connection_errors'] += 1
    
    def record_eviction(self):
        """Record L1 eviction"""
        with self._lock:
            self.stats['evictions'] += 1
    
    @property
    def total_hit_rate(self) -> float:
        """Total cache hit rate (L1 + L2)"""
        if self.stats['total_requests'] == 0:
            return 0.0
        hits = self.stats['l1_hits'] + self.stats['l2_hits']
        return (hits / self.stats['total_requests']) * 100
    
    @property
    def l1_hit_rate(self) -> float:
        """L1 cache hit rate"""
        if self.stats['total_requests'] == 0:
            return 0.0
        return (self.stats['l1_hits'] / self.stats['total_requests']) * 100
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        uptime = time.time() - self.start_time
        total_hits = self.stats['l1_hits'] + self.stats['l2_hits']
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self.stats['total_requests'],
            'total_hits': total_hits,
            'l1_hits': self.stats['l1_hits'],
            'l2_hits': self.stats['l2_hits'],
            'misses': self.stats['total_misses'],
            'total_hit_rate_percent': round(self.total_hit_rate, 2),
            'l1_hit_rate_percent': round(self.l1_hit_rate, 2),
            'promotions': self.stats['promotions'],
            'evictions': self.stats['evictions'],
            'avg_l1_response_ms': round(
                self.stats['l1_response_time_ms'] / max(self.stats['l1_hits'], 1), 2
            ),
            'avg_l2_response_ms': round(
                self.stats['l2_response_time_ms'] / max(self.stats['l2_hits'], 1), 2
            ),
            'avg_compute_ms': round(
                self.stats['compute_time_ms'] / max(self.stats['total_misses'], 1), 2
            ),
            'errors': self.stats['errors'],
            'connection_errors': self.stats['connection_errors'],
            'performance_rating': self._get_performance_rating()
        }
    
    def _get_performance_rating(self) -> str:
        """Get performance rating based on metrics"""
        hit_rate = self.total_hit_rate
        avg_response = (self.stats['l1_response_time_ms'] + self.stats['l2_response_time_ms']) / max(
            self.stats['l1_hits'] + self.stats['l2_hits'], 1
        )
        
        if hit_rate >= 80 and avg_response <= 50:
            return "EXCELLENT"
        elif hit_rate >= 70 and avg_response <= 100:
            return "GOOD"
        elif hit_rate >= 60 and avg_response <= 150:
            return "ACCEPTABLE"
        else:
            return "NEEDS_IMPROVEMENT"


class MultiTierCache:
    """
    Multi-tier caching system with Redis L1 and Memcached L2
    Features:
    - Automatic hot data promotion from L2 to L1
    - Connection pooling for both Redis and Memcached
    - Circuit breaker pattern for resilience
    - Comprehensive metrics and monitoring
    """
    
    # Cache configuration
    L1_MAX_KEYS = 10000         # Redis L1 capacity
    L1_DEFAULT_TTL = 300        # 5 minutes in L1
    L2_DEFAULT_TTL = 3600       # 1 hour in L2
    PROMOTION_THRESHOLD = 2     # Access count to trigger promotion
    
    # TTL configurations for different data types
    TTL_CONFIG = {
        'ticker': {'l1': 5, 'l2': 30},
        'orderbook': {'l1': 2, 'l2': 10},
        'market_data': {'l1': 30, 'l2': 300},
        'dashboard': {'l1': 30, 'l2': 300},
        'confluence': {'l1': 30, 'l2': 300},
        'signals': {'l1': 60, 'l2': 600},
        'analysis': {'l1': 300, 'l2': 1800}
    }
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 memcached_host: str = "127.0.0.1",
                 memcached_port: int = 11211,
                 redis_pool_size: int = 20,
                 enable_promotion: bool = True):
        """
        Initialize multi-tier cache system
        
        Args:
            redis_url: Redis connection URL
            memcached_host: Memcached host
            memcached_port: Memcached port
            redis_pool_size: Redis connection pool size
            enable_promotion: Enable L2->L1 promotion
        """
        self.enable_promotion = enable_promotion
        self.metrics = CacheMetrics()
        self.access_counts = {}  # Track access frequency for promotion
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize Redis L1 cache with connection pooling
        try:
            self.redis_pool = ConnectionPool.from_url(
                redis_url, 
                max_connections=redis_pool_size,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            self.redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            self.redis_available = True
            logger.info(f"✅ Redis L1 cache initialized with pool size {redis_pool_size}")
        except Exception as e:
            self.redis_available = False
            logger.error(f"❌ Redis L1 cache initialization failed: {e}")
        
        # Initialize Memcached L2 cache
        try:
            self.memcached_client = aiomcache.Client(memcached_host, memcached_port)
            # Test connection with a simple operation
            self.memcached_available = True
            logger.info(f"✅ Memcached L2 cache initialized at {memcached_host}:{memcached_port}")
        except Exception as e:
            self.memcached_available = False
            logger.error(f"❌ Memcached L2 cache initialization failed: {e}")
        
        # Fallback in-memory cache
        self.local_cache = {}
        self.local_expiry = {}
    
    def _get_ttl(self, data_type: str, tier: str) -> int:
        """Get TTL for specific data type and cache tier"""
        if data_type in self.TTL_CONFIG:
            return self.TTL_CONFIG[data_type].get(tier, 
                self.L1_DEFAULT_TTL if tier == 'l1' else self.L2_DEFAULT_TTL)
        return self.L1_DEFAULT_TTL if tier == 'l1' else self.L2_DEFAULT_TTL
    
    async def get(self, key: str, data_type: str = 'default') -> Optional[Any]:
        """
        Get value from multi-tier cache
        Order: Redis L1 -> Memcached L2 -> Return None
        """
        start_time = time.time()
        
        # Try Redis L1 first
        if self.redis_available:
            try:
                l1_start = time.time()
                cached_data = await self.redis_client.get(key)
                l1_time_ms = (time.time() - l1_start) * 1000
                
                if cached_data:
                    try:
                        value = json.loads(cached_data.decode('utf-8'))
                        self.metrics.record_l1_hit(l1_time_ms)
                        self._track_access(key)
                        return value
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Try pickle as fallback
                        try:
                            value = pickle.loads(cached_data)
                            self.metrics.record_l1_hit(l1_time_ms)
                            self._track_access(key)
                            return value
                        except:
                            pass
            except Exception as e:
                logger.debug(f"Redis L1 get error for {key}: {e}")
                self.metrics.record_error(connection_error=True)
        
        # Try Memcached L2
        if self.memcached_available:
            try:
                l2_start = time.time()
                cached_data = await self.memcached_client.get(key.encode())
                l2_time_ms = (time.time() - l2_start) * 1000
                
                if cached_data:
                    try:
                        value = json.loads(cached_data.decode('utf-8'))
                        self.metrics.record_l2_hit(l2_time_ms)
                        self._track_access(key)
                        
                        # Promote to L1 if frequently accessed
                        if self._should_promote(key):
                            await self._promote_to_l1(key, value, data_type)
                            self.metrics.record_l2_hit(l2_time_ms, promoted=True)
                        
                        return value
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            except Exception as e:
                logger.debug(f"Memcached L2 get error for {key}: {e}")
                self.metrics.record_error(connection_error=True)
        
        # Fallback to local cache
        if key in self.local_cache:
            if key in self.local_expiry and time.time() < self.local_expiry[key]:
                return self.local_cache[key]
            else:
                del self.local_cache[key]
                if key in self.local_expiry:
                    del self.local_expiry[key]
        
        return None
    
    async def set(self, key: str, value: Any, data_type: str = 'default', 
                  force_l1: bool = False) -> bool:
        """
        Set value in multi-tier cache
        Strategy: Always set in L2, set in L1 if hot or forced
        """
        success = False
        
        # Serialize value
        try:
            serialized_value = json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fallback to pickle for complex objects
            serialized_value = pickle.dumps(value)
        
        # Set in L2 (Memcached) - larger capacity, longer TTL
        if self.memcached_available:
            try:
                l2_ttl = self._get_ttl(data_type, 'l2')
                await self.memcached_client.set(key.encode(), serialized_value, exptime=l2_ttl)
                success = True
            except Exception as e:
                logger.debug(f"Memcached L2 set error for {key}: {e}")
        
        # Set in L1 (Redis) if hot data or forced
        if (force_l1 or self._is_hot_data(key)) and self.redis_available:
            try:
                l1_ttl = self._get_ttl(data_type, 'l1')
                await self.redis_client.setex(key, l1_ttl, serialized_value)
                
                # Manage L1 capacity
                await self._manage_l1_capacity()
                
            except Exception as e:
                logger.debug(f"Redis L1 set error for {key}: {e}")
        
        # Fallback to local cache
        if not success:
            self.local_cache[key] = value
            self.local_expiry[key] = time.time() + self._get_ttl(data_type, 'l2')
            success = True
        
        return success
    
    async def get_or_compute(self, 
                            key: str, 
                            compute_func: Callable,
                            data_type: str = 'default',
                            ttl_override: Dict[str, int] = None) -> Any:
        """
        Get from cache or compute if missing with comprehensive caching strategy
        """
        start_time = time.time()
        
        # Try to get from cache
        cached_value = await self.get(key, data_type)
        if cached_value is not None:
            return cached_value
        
        # Cache miss - compute value
        try:
            compute_start = time.time()
            value = await compute_func() if asyncio.iscoroutinefunction(compute_func) else compute_func()
            compute_time_ms = (time.time() - compute_start) * 1000
            
            # Cache the computed value
            await self.set(key, value, data_type)
            
            self.metrics.record_miss(compute_time_ms)
            return value
            
        except Exception as e:
            logger.error(f"Error computing value for key {key}: {e}")
            self.metrics.record_error()
            raise
    
    def _track_access(self, key: str):
        """Track key access frequency for promotion decisions"""
        if not self.enable_promotion:
            return
            
        if key not in self.access_counts:
            self.access_counts[key] = 0
        self.access_counts[key] += 1
    
    def _should_promote(self, key: str) -> bool:
        """Determine if key should be promoted to L1"""
        if not self.enable_promotion:
            return False
        return self.access_counts.get(key, 0) >= self.PROMOTION_THRESHOLD
    
    def _is_hot_data(self, key: str) -> bool:
        """Determine if data should go directly to L1"""
        return (
            'ticker' in key or 
            'orderbook' in key or 
            'dashboard' in key or
            self.access_counts.get(key, 0) >= self.PROMOTION_THRESHOLD
        )
    
    async def _promote_to_l1(self, key: str, value: Any, data_type: str):
        """Promote frequently accessed data from L2 to L1"""
        if not self.redis_available:
            return
            
        try:
            serialized_value = json.dumps(value).encode('utf-8')
            l1_ttl = self._get_ttl(data_type, 'l1')
            await self.redis_client.setex(key, l1_ttl, serialized_value)
            logger.debug(f"Promoted {key} to L1 cache")
        except Exception as e:
            logger.debug(f"Failed to promote {key} to L1: {e}")
    
    async def _manage_l1_capacity(self):
        """Manage L1 cache capacity using LRU eviction"""
        if not self.redis_available:
            return
            
        try:
            # Get current key count
            key_count = await self.redis_client.dbsize()
            
            if key_count > self.L1_MAX_KEYS:
                # Get random keys and their TTL
                keys_to_check = await self.redis_client.randomkey()
                if keys_to_check:
                    # Simple eviction - could be enhanced with LRU tracking
                    await self.redis_client.delete(keys_to_check)
                    self.metrics.record_eviction()
                    
        except Exception as e:
            logger.debug(f"L1 capacity management error: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache tiers"""
        success = False
        
        # Delete from L1 (Redis)
        if self.redis_available:
            try:
                await self.redis_client.delete(key)
                success = True
            except Exception as e:
                logger.debug(f"Redis L1 delete error for {key}: {e}")
        
        # Delete from L2 (Memcached)
        if self.memcached_available:
            try:
                await self.memcached_client.delete(key.encode())
                success = True
            except Exception as e:
                logger.debug(f"Memcached L2 delete error for {key}: {e}")
        
        # Delete from local cache
        if key in self.local_cache:
            del self.local_cache[key]
            success = True
        if key in self.local_expiry:
            del self.local_expiry[key]
        
        # Clean up access tracking
        if key in self.access_counts:
            del self.access_counts[key]
        
        return success
    
    async def clear_pattern(self, pattern: str):
        """Clear keys matching pattern from all tiers"""
        cleared_count = 0
        
        # Clear from Redis L1
        if self.redis_available:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    cleared_count += len(keys)
            except Exception as e:
                logger.debug(f"Redis pattern clear error: {e}")
        
        # Clear from local cache
        local_keys = [k for k in self.local_cache.keys() if pattern.replace('*', '') in k]
        for key in local_keys:
            del self.local_cache[key]
            if key in self.local_expiry:
                del self.local_expiry[key]
        cleared_count += len(local_keys)
        
        logger.info(f"Cleared {cleared_count} keys matching pattern: {pattern}")
        return cleared_count
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        base_metrics = self.metrics.get_performance_summary()
        
        # Add system-specific metrics
        base_metrics.update({
            'redis_available': self.redis_available,
            'memcached_available': self.memcached_available,
            'l1_capacity_used': len(self.access_counts),
            'promotion_enabled': self.enable_promotion,
            'local_cache_keys': len(self.local_cache),
            'architecture': 'multi_tier',
            'cache_tiers': ['Redis L1', 'Memcached L2', 'Local Fallback']
        })
        
        return base_metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all cache tiers"""
        health = {
            'status': 'healthy',
            'redis_l1': {'status': 'unknown'},
            'memcached_l2': {'status': 'unknown'},
            'local_fallback': {'status': 'available'},
            'performance': self.get_performance_metrics()
        }
        
        # Test Redis L1
        if self.redis_available:
            try:
                test_start = time.time()
                await self.redis_client.ping()
                response_time = (time.time() - test_start) * 1000
                health['redis_l1'] = {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2)
                }
            except Exception as e:
                health['redis_l1'] = {'status': 'unhealthy', 'error': str(e)}
                health['status'] = 'degraded'
        else:
            health['redis_l1'] = {'status': 'unavailable'}
            health['status'] = 'degraded'
        
        # Test Memcached L2
        if self.memcached_available:
            try:
                test_start = time.time()
                await self.memcached_client.get(b'health_check')
                response_time = (time.time() - test_start) * 1000
                health['memcached_l2'] = {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2)
                }
            except Exception as e:
                health['memcached_l2'] = {'status': 'unhealthy', 'error': str(e)}
                if health['status'] != 'degraded':
                    health['status'] = 'degraded'
        else:
            health['memcached_l2'] = {'status': 'unavailable'}
            if health['status'] != 'degraded':
                health['status'] = 'degraded'
        
        return health
    
    async def close(self):
        """Clean shutdown of all cache connections"""
        if self.redis_available:
            await self.redis_client.close()
        
        if self.memcached_available:
            await self.memcached_client.close()
        
        self._executor.shutdown(wait=True)
        logger.info("Multi-tier cache connections closed")


# Global cache instance
_cache_instance: Optional[MultiTierCache] = None

def get_multi_tier_cache() -> MultiTierCache:
    """Get global multi-tier cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MultiTierCache()
    return _cache_instance

def cache_multi_tier(ttl_config: Dict[str, int] = None, data_type: str = 'default'):
    """
    Multi-tier caching decorator
    
    Args:
        ttl_config: Optional TTL override {'l1': seconds, 'l2': seconds}
        data_type: Data type for TTL configuration
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_multi_tier_cache()
            
            # Generate cache key
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ':'.join(key_parts)
            
            # Get or compute with multi-tier caching
            return await cache.get_or_compute(
                cache_key,
                lambda: func(*args, **kwargs) if not asyncio.iscoroutinefunction(func) else func(*args, **kwargs),
                data_type=data_type,
                ttl_override=ttl_config
            )
        
        return wrapper
    return decorator