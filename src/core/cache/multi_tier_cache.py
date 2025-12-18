#!/usr/bin/env python3
"""
Phase 2 Cache Optimization: Multi-Tier Cache Architecture
Implements 3-layer caching system for maximum performance

Layer 1: In-memory dict (ultra-fast, 10-30s TTL)
Layer 2: Memcached (fast, 30-90s TTL) 
Layer 3: Redis (persistent, 300s TTL)

Expected Impact: 40% performance boost through data locality
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, Union, List
from dataclasses import dataclass, field
from enum import Enum
import aiomcache

# Import high-performance LRU cache for L1
try:
    from .lru_cache import HighPerformanceLRUCache
except ImportError:
    # Fallback for older systems
    HighPerformanceLRUCache = None
try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)

class CacheLayer(Enum):
    L1_MEMORY = "l1_memory"
    L2_MEMCACHED = "l2_memcached" 
    L3_REDIS = "l3_redis"
    MISS = "miss"

@dataclass
class CacheItem:
    """Cache item with metadata"""
    value: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    layer: CacheLayer = CacheLayer.MISS
    
    def is_expired(self) -> bool:
        """Check if cache item is expired"""
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """Update access statistics"""
        self.access_count += 1

@dataclass
class CacheStats:
    """Cache performance statistics"""
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    total_misses: int = 0
    promotions: int = 0  # Items promoted between layers
    evictions: int = 0   # Items evicted from L1
    last_reset: float = field(default_factory=time.time)
    
    @property
    def total_hits(self) -> int:
        return self.l1_hits + self.l2_hits + self.l3_hits
    
    @property
    def hit_rate(self) -> float:
        total = self.total_hits + self.total_misses
        return (self.total_hits / total * 100) if total > 0 else 0.0
    
    @property
    def l1_hit_rate(self) -> float:
        total = self.total_hits + self.total_misses
        return (self.l1_hits / total * 100) if total > 0 else 0.0

class MultiTierCacheAdapter:
    """
    Phase 2 Multi-Tier Cache Architecture
    
    Implements intelligent 3-layer caching with automatic promotion/demotion
    and performance optimization for high-frequency trading data.
    """
    
    def __init__(self,
                 memcached_host: str = '127.0.0.1',
                 memcached_port: int = 11211,
                 redis_host: str = '127.0.0.1',
                 redis_port: int = 6379,
                 l1_max_size: int = 1000,
                 l1_default_ttl: int = 30,
                 cross_process_mode: bool = True,
                 cross_process_l1_ttl: int = 2):

        # Configuration
        self.memcached_host = memcached_host
        self.memcached_port = memcached_port
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.l1_max_size = l1_max_size
        self.l1_default_ttl = l1_default_ttl

        # Cross-process cache sharing configuration
        self.cross_process_mode = cross_process_mode
        self.cross_process_l1_ttl = cross_process_l1_ttl  # Very short TTL for cross-process keys

        # Define cross-process key patterns (shared between monitoring and web server)
        self.cross_process_prefixes = {
            'analysis:',      # Trading signals and analysis
            'market:',        # Market data, overview, movers
            'confluence:',    # Confluence scores and breakdowns
            'dashboard:',     # Dashboard-specific data
            'system:',        # System-wide alerts and status
            'unified:',       # Unified schema data
            'virtuoso:'       # Legacy virtuoso keys
        }
        
        # Layer 1: High-performance LRU cache (ultra-fast)
        if HighPerformanceLRUCache:
            self.l1_cache = HighPerformanceLRUCache(
                max_size=l1_max_size,
                default_ttl=l1_default_ttl
            )
            self._use_advanced_l1 = True
            logger.info(f"Using high-performance LRU cache for L1: {l1_max_size} items")
        else:
            # Fallback to simple dict-based cache
            self.l1_cache: Dict[str, CacheItem] = {}
            self._use_advanced_l1 = False
            logger.warning("Using fallback dict-based L1 cache")
        
        # Layer 2 & 3: External cache clients
        self._memcached_client: Optional[aiomcache.Client] = None
        self._redis_client: Optional[aioredis.Redis] = None
        
        # Performance tracking
        self.stats = CacheStats()
        
        # TTL strategy based on Phase 1 optimizations
        self.tier_ttls = {
            CacheLayer.L1_MEMORY: {
                'market:overview': 15,       # Ultra-fresh market data
                'market:movers': 20,         # Top movers 
                'dashboard:data': 20,        # Combined dashboard
                'analysis:signals': 30,      # Trading signals
                'confluence:scores': 45,     # Analysis results
                'default': 30
            },
            CacheLayer.L2_MEMCACHED: {
                'market:overview': 30,       # From Phase 1
                'market:movers': 45,         
                'dashboard:data': 45,        
                'analysis:signals': 60,      
                'confluence:scores': 90,     
                'default': 60
            },
            CacheLayer.L3_REDIS: {
                'market:overview': 120,      # Longer persistence
                'market:movers': 180,        
                'dashboard:data': 180,       
                'analysis:signals': 300,     
                'confluence:scores': 600,    
                'default': 300
            }
        }

        logger.info(f"Multi-tier cache adapter initialized (cross_process_mode={cross_process_mode}, cross_process_l1_ttl={cross_process_l1_ttl}s)")
    
    async def _get_memcached_client(self) -> aiomcache.Client:
        """Get or create Memcached client"""
        if self._memcached_client is None:
            self._memcached_client = aiomcache.Client(
                self.memcached_host,
                self.memcached_port,
                pool_size=20  # From Phase 1 optimization
            )
        return self._memcached_client
    
    async def _get_redis_client(self) -> Optional[aioredis.Redis]:
        """Get or create Redis client"""
        if aioredis is None:
            logger.warning("Redis not available - L3 cache disabled")
            return None
            
        if self._redis_client is None:
            try:
                self._redis_client = aioredis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=False,  # Handle binary data
                    max_connections=20
                )
                # Test connection
                await self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis_client = None
                
        return self._redis_client
    
    def _is_cross_process_key(self, key: str) -> bool:
        """Check if key is used for cross-process communication"""
        if not self.cross_process_mode:
            return False

        for prefix in self.cross_process_prefixes:
            if key.startswith(prefix):
                return True
        return False

    def _get_ttl_for_layer(self, key: str, layer: CacheLayer) -> int:
        """Get appropriate TTL for key and cache layer"""
        # For cross-process keys in L1, use very short TTL
        if layer == CacheLayer.L1_MEMORY and self._is_cross_process_key(key):
            return self.cross_process_l1_ttl

        layer_config = self.tier_ttls.get(layer, {})
        return layer_config.get(key, layer_config.get('default', 60))

    def _get_l1_metrics(self) -> Dict[str, Any]:
        """Get detailed L1 cache metrics"""
        if self._use_advanced_l1:
            # Get detailed metrics from high-performance LRU cache
            l1_stats = self.l1_cache.get_statistics()
            l1_perf = self.l1_cache.get_performance_metrics()

            return {
                'type': 'high_performance_lru',
                'current_items': l1_stats['size'],
                'max_items': l1_stats['max_size'],
                'utilization': round(l1_stats['capacity_usage'], 1),
                'lru_hits': l1_stats['hits'],
                'lru_misses': l1_stats['misses'],
                'lru_hit_rate': round(l1_stats['hit_rate'], 2),
                'lru_evictions': l1_stats['evictions'],
                'expired_removals': l1_stats['expired_removals'],
                'avg_get_time_ms': round(l1_perf['avg_get_time_ms'], 3),
                'avg_set_time_ms': round(l1_perf['avg_set_time_ms'], 3),
                'performance_target_met': l1_perf['performance_target_met']
            }
        else:
            # Fallback metrics for dict-based cache
            cache_size = len(self.l1_cache) if hasattr(self.l1_cache, '__len__') else 0
            return {
                'type': 'dict_fallback',
                'current_items': cache_size,
                'max_items': self.l1_max_size,
                'utilization': round(cache_size / self.l1_max_size * 100, 1),
                'lru_hits': 0,
                'lru_misses': 0,
                'lru_hit_rate': 0.0,
                'lru_evictions': 0,
                'expired_removals': 0,
                'avg_get_time_ms': 0.0,
                'avg_set_time_ms': 0.0,
                'performance_target_met': False
            }
    
    def _evict_l1_if_needed(self):
        """Evict least recently used items from L1 if over capacity"""
        if self._use_advanced_l1:
            # Advanced LRU cache handles eviction automatically
            return

        # Fallback eviction for dict-based cache
        if len(self.l1_cache) >= self.l1_max_size:
            # Sort by access count and timestamp (LRU strategy)
            items = [(k, v) for k, v in self.l1_cache.items()]
            items.sort(key=lambda x: (x[1].access_count, x[1].timestamp))

            # Remove oldest 20% to avoid frequent evictions
            evict_count = max(1, len(items) // 5)
            for i in range(evict_count):
                key = items[i][0]
                del self.l1_cache[key]
                self.stats.evictions += 1
    
    async def _get_l1(self, key: str) -> Optional[Any]:
        """Get from Layer 1 (in-memory) cache"""
        if self._use_advanced_l1:
            # Use high-performance LRU cache
            value = self.l1_cache.get(key)
            if value is not None:
                self.stats.l1_hits += 1
                logger.debug(f"L1 HIT: {key}")
                return value
            return None
        else:
            # Fallback dict-based cache
            if key in self.l1_cache:
                item = self.l1_cache[key]
                if not item.is_expired():
                    item.touch()
                    self.stats.l1_hits += 1
                    logger.debug(f"L1 HIT: {key}")
                    return item.value
                else:
                    # Remove expired item
                    del self.l1_cache[key]
            return None
    
    async def _set_l1(self, key: str, value: Any, ttl: int = None):
        """Set in Layer 1 (in-memory) cache"""
        if ttl is None:
            ttl = self._get_ttl_for_layer(key, CacheLayer.L1_MEMORY)

        if self._use_advanced_l1:
            # Use high-performance LRU cache
            self.l1_cache.set(key, value, ttl)
            logger.debug(f"L1 SET: {key} (TTL: {ttl}s)")
        else:
            # Fallback dict-based cache
            self._evict_l1_if_needed()

            self.l1_cache[key] = CacheItem(
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                layer=CacheLayer.L1_MEMORY
            )
            logger.debug(f"L1 SET: {key} (TTL: {ttl}s)")
    
    async def _get_l2(self, key: str) -> Optional[Any]:
        """Get from Layer 2 (Memcached) cache"""
        try:
            client = await self._get_memcached_client()
            data = await client.get(key.encode())
            if data:
                self.stats.l2_hits += 1
                logger.debug(f"L2 HIT: {key}")
                
                # Deserialize data
                try:
                    result = json.loads(data.decode())
                    # DOUBLE-DECODE FIX: Handle double-JSON-encoded data
                    if isinstance(result, str) and (result.startswith('{') or result.startswith('[')):
                        try:
                            result = json.loads(result)
                            logger.debug(f"Double-decoded L2 {key}")
                        except (json.JSONDecodeError, ValueError):
                            pass  # Not JSON, return as-is
                    return result
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"L2 deserialization failed for {key}: {e}")
                    return None
        except Exception as e:
            logger.warning(f"L2 get failed for {key}: {e}")
        return None
    
    async def _set_l2(self, key: str, value: Any, ttl: int = None):
        """Set in Layer 2 (Memcached) cache"""
        if ttl is None:
            ttl = self._get_ttl_for_layer(key, CacheLayer.L2_MEMCACHED)
        
        try:
            client = await self._get_memcached_client()
            data = json.dumps(value).encode()
            await client.set(key.encode(), data, ttl)
            logger.debug(f"L2 SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"L2 set failed for {key}: {e}")
    
    async def _get_l3(self, key: str) -> Optional[Any]:
        """Get from Layer 3 (Redis) cache"""
        try:
            client = await self._get_redis_client()
            if client:
                data = await client.get(key)
                if data:
                    self.stats.l3_hits += 1
                    logger.debug(f"L3 HIT: {key}")
                    
                    # Deserialize data
                    try:
                        result = json.loads(data.decode())
                        # DOUBLE-DECODE FIX: Handle double-JSON-encoded data
                        if isinstance(result, str) and (result.startswith('{') or result.startswith('[')):
                            try:
                                result = json.loads(result)
                                logger.debug(f"Double-decoded L3 {key}")
                            except (json.JSONDecodeError, ValueError):
                                pass  # Not JSON, return as-is
                        return result
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"L3 deserialization failed for {key}: {e}")
                        return None
        except Exception as e:
            logger.warning(f"L3 get failed for {key}: {e}")
        return None
    
    async def _set_l3(self, key: str, value: Any, ttl: int = None):
        """Set in Layer 3 (Redis) cache"""
        if ttl is None:
            ttl = self._get_ttl_for_layer(key, CacheLayer.L3_REDIS)
        
        try:
            client = await self._get_redis_client()
            if client:
                data = json.dumps(value).encode()
                await client.setex(key, ttl, data)
                logger.debug(f"L3 SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"L3 set failed for {key}: {e}")
    
    async def get(self, key: str, default: Any = None) -> Tuple[Any, CacheLayer]:
        """
        Get value from multi-tier cache with automatic promotion

        For cross-process keys, L1 is either skipped or has very short TTL
        to ensure fresh data across process boundaries.

        Returns:
            Tuple of (value, cache_layer_hit)
        """
        is_cross_process = self._is_cross_process_key(key)

        # Try L1 first (fastest) - but only for non-cross-process keys or with awareness of short TTL
        if not is_cross_process or self.cross_process_l1_ttl > 0:
            value = await self._get_l1(key)
            if value is not None:
                if is_cross_process:
                    logger.debug(f"L1 HIT for cross-process key: {key} (TTL: {self.cross_process_l1_ttl}s)")
                return value, CacheLayer.L1_MEMORY

        # Try L2 (fast, shared across processes)
        value = await self._get_l2(key)
        if value is not None:
            # Promote to L1 for faster future access (with appropriate TTL)
            await self._set_l1(key, value)
            self.stats.promotions += 1
            return value, CacheLayer.L2_MEMCACHED

        # Try L3 (persistent, shared across processes)
        value = await self._get_l3(key)
        if value is not None:
            # Promote to L2 and L1 (with appropriate TTLs)
            await self._set_l2(key, value)
            await self._set_l1(key, value)
            self.stats.promotions += 2  # Promoted through 2 layers
            return value, CacheLayer.L3_REDIS

        # Cache miss
        self.stats.total_misses += 1
        logger.debug(f"CACHE MISS: {key}")
        return default, CacheLayer.MISS
    
    async def set(self, key: str, value: Any, ttl_override: int = None):
        """
        Set value in all cache tiers with appropriate TTLs

        For cross-process keys, L1 gets a very short TTL to avoid stale data
        across process boundaries while still providing some performance benefit.
        """
        is_cross_process = self._is_cross_process_key(key)

        # For cross-process keys, use short TTL for L1 unless overridden
        l1_ttl = ttl_override
        if is_cross_process and ttl_override is None:
            l1_ttl = self.cross_process_l1_ttl

        # Set in all layers with appropriate TTLs
        await asyncio.gather(
            self._set_l1(key, value, l1_ttl),
            self._set_l2(key, value, ttl_override),
            self._set_l3(key, value, ttl_override),
            return_exceptions=True
        )

        if is_cross_process:
            logger.debug(f"MULTI-TIER SET (cross-process): {key} (L1 TTL: {l1_ttl}s)")
        else:
            logger.debug(f"MULTI-TIER SET: {key}")
    
    async def delete(self, key: str):
        """Delete from all cache tiers"""
        # Remove from L1
        if key in self.l1_cache:
            del self.l1_cache[key]
        
        # Remove from L2 and L3
        tasks = []
        
        try:
            client = await self._get_memcached_client()
            tasks.append(client.delete(key.encode()))
        except Exception as e:
            logger.warning(f"L2 delete failed for {key}: {e}")
        
        try:
            client = await self._get_redis_client()
            if client:
                tasks.append(client.delete(key))
        except Exception as e:
            logger.warning(f"L3 delete failed for {key}: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug(f"MULTI-TIER DELETE: {key}")
    
    async def clear_all(self):
        """Clear all cache tiers"""
        # Clear L1
        self.l1_cache.clear()
        
        # Clear L2 and L3
        tasks = []
        
        try:
            client = await self._get_memcached_client()
            # Note: aiomcache doesn't have flush_all, so we'll skip this
            # In production, you might want to implement this differently
        except Exception as e:
            logger.warning(f"L2 clear failed: {e}")
        
        try:
            client = await self._get_redis_client()
            if client:
                tasks.append(client.flushdb())
        except Exception as e:
            logger.warning(f"L3 clear failed: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Multi-tier cache cleared")

    async def warm_from_redis(self, keys: List[str] = None) -> Dict[str, bool]:
        """
        Warm L1/L2 cache from Redis (L3) on startup.

        This dramatically reduces startup time by promoting persisted data
        from Redis into faster cache layers immediately.

        Args:
            keys: List of specific keys to warm. If None, warms critical dashboard keys.

        Returns:
            Dict mapping key names to success status
        """
        # Default critical keys for dashboard startup
        if keys is None:
            keys = [
                'market:movers',
                'market:overview',
                'mobile:data',
                'confluence:summary',
                'vt_shared:market:movers',
                'vt_shared:market:overview'
            ]

        results = {}
        warmed_count = 0

        try:
            client = await self._get_redis_client()
            if not client:
                logger.warning("Redis not available - cannot warm cache from L3")
                return {k: False for k in keys}

            for key in keys:
                try:
                    # Read from Redis (L3)
                    data = await client.get(key)
                    if data:
                        # Deserialize
                        try:
                            value = json.loads(data)
                        except (json.JSONDecodeError, TypeError):
                            value = data

                        # Promote to L1 and L2 with shorter TTLs (fresh data will replace)
                        await self._set_l1(key, value, ttl=120)  # 2 min in L1
                        await self._set_l2(key, value, ttl=300)  # 5 min in L2

                        results[key] = True
                        warmed_count += 1
                        logger.debug(f"Warmed {key} from Redis")
                    else:
                        results[key] = False

                except Exception as e:
                    logger.warning(f"Failed to warm {key} from Redis: {e}")
                    results[key] = False

            logger.info(f"✅ Cache warming complete: {warmed_count}/{len(keys)} keys promoted from Redis")

        except Exception as e:
            logger.error(f"Cache warming from Redis failed: {e}")
            return {k: False for k in keys}

        return results

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        runtime = time.time() - self.stats.last_reset
        
        return {
            'hit_rates': {
                'overall': round(self.stats.hit_rate, 2),
                'l1_percentage': round(self.stats.l1_hit_rate, 2),
                'l2_percentage': round((self.stats.l2_hits / (self.stats.total_hits + self.stats.total_misses) * 100) if (self.stats.total_hits + self.stats.total_misses) > 0 else 0, 2),
                'l3_percentage': round((self.stats.l3_hits / (self.stats.total_hits + self.stats.total_misses) * 100) if (self.stats.total_hits + self.stats.total_misses) > 0 else 0, 2)
            },
            'operations': {
                'total_hits': self.stats.total_hits,
                'total_misses': self.stats.total_misses,
                'promotions': self.stats.promotions,
                'evictions': self.stats.evictions
            },
            'l1_memory': self._get_l1_metrics(),
            'performance': {
                'runtime_seconds': round(runtime, 1),
                'operations_per_second': round((self.stats.total_hits + self.stats.total_misses) / runtime if runtime > 0 else 0, 1)
            }
        }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.stats = CacheStats()
        logger.info("Cache statistics reset")

# Backwards compatibility adapter
class DirectCacheAdapter:
    """
    Backwards compatibility wrapper for existing code
    Routes calls to the new multi-tier cache system
    """
    
    def __init__(self):
        self.multi_tier_cache = MultiTierCacheAdapter()
        logger.info("DirectCacheAdapter initialized with multi-tier backend")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache (backwards compatible)"""
        value, layer = await self.multi_tier_cache.get(key, default)
        return value
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache (backwards compatible)"""
        await self.multi_tier_cache.set(key, value, ttl)
    
    async def delete(self, key: str):
        """Delete from cache (backwards compatible)"""
        await self.multi_tier_cache.delete(key)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.multi_tier_cache.get_performance_metrics()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics (alias for get_performance_metrics for backwards compatibility)"""
        return self.get_performance_metrics()

    async def health_check(self) -> Dict[str, Any]:
        """Get cache health status"""
        try:
            # Test basic connectivity with timestamp key
            test_key = f"health_check:{int(time.time())}"
            test_value = "health_test"
            await self.set(test_key, test_value, 5)
            retrieved_value = await self.get(test_key)

            metrics = self.get_performance_metrics()

            return {
                'status': 'healthy' if retrieved_value == test_value else 'unhealthy',
                'connectivity_test': retrieved_value == test_value,
                'performance_metrics': metrics,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }

    async def warm_from_redis(self, keys: List[str] = None) -> Dict[str, bool]:
        """
        Warm L1/L2 cache from Redis (L3) on startup.
        Delegates to multi-tier cache implementation.
        """
        return await self.multi_tier_cache.warm_from_redis(keys)


# Export for use in other modules
__all__ = ['MultiTierCacheAdapter', 'DirectCacheAdapter', 'CacheLayer', 'CacheStats']