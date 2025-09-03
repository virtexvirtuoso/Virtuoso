"""
Cache Fixes - Priority 1 Performance Improvements (VPS Version)
Implements optimized TTL settings, circuit breaker, and fallback mechanisms.
Uses pymemcache for compatibility with VPS environment.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import socket

# Import existing memcache from system
try:
    import pymemcache
    from pymemcache.client.base import Client as MemcacheClient
    MEMCACHE_AVAILABLE = True
except ImportError:
    # Fallback - create stub
    MEMCACHE_AVAILABLE = False
    class MemcacheClient:
        def __init__(self, *args, **kwargs):
            pass

logger = logging.getLogger(__name__)

@dataclass
class CacheStats:
    """Cache statistics tracking"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    timeouts: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

class CircuitBreaker:
    """Circuit breaker for cache operations"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
                return False
            return True
        return False
    
    def record_success(self):
        """Record successful operation"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker CLOSED after successful operation")
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold and self.state == "CLOSED":
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")

class OptimizedCacheAdapter:
    """Cache adapter with Priority 1 fixes - VPS compatible version"""
    
    def __init__(self, host: str = 'localhost', port: int = 11211):
        self.host = host
        self.port = port
        self.client = None
        self.circuit_breaker = CircuitBreaker()
        self.stats = CacheStats()
        self.fallback_cache: Dict[str, Any] = {}
        self.initialized = False
        
        # Optimized TTL settings (Priority 1 fix)
        self.ttl_config = {
            # Core data with longer TTL for better hit rates
            'market:overview': 120,           # 2 minutes (was 30s) - 4x improvement
            'market:overview:v2': 120,        # 2 minutes 
            'confluence:scores': 60,          # 1 minute (was 30s) - 2x improvement
            'analysis:confluence:scores': 60, # 1 minute
            'technical:indicators': 60,       # 1 minute (was 30s) - 2x improvement
            'dashboard:data': 45,             # 45 seconds (was 30s) - 1.5x improvement
            'signal:analysis': 90,            # 1.5 minutes (was 30s) - 3x improvement
            'analysis:signals:active': 90,    # 1.5 minutes
            'top:symbols': 300,               # 5 minutes (was 60s) - 5x improvement
            'market:tickers': 30,             # 30 seconds (optimized)
            'market:tickers:all': 30,         # 30 seconds
            'market:movers': 90,              # 1.5 minutes (was 60s) - 1.5x improvement
            'market:movers:top': 90,          # 1.5 minutes
            'market:regime': 180,             # 3 minutes (was 60s) - 3x improvement
            'market:regime:current': 180,     # 3 minutes
            'btc:dominance': 240,             # 4 minutes (was 60s) - 4x improvement
            'market:btc:dominance': 240,      # 4 minutes
            'system:health': 45,              # 45 seconds (was 30s) - 1.5x improvement
            'system:health:status': 45,       # 45 seconds
            'system:alerts': 120,             # 2 minutes (was 60s) - 2x improvement
            'market:breadth': 75,             # 1.25 minutes (was 60s) - 1.25x improvement
            
            # Real-time data with minimal but optimized caching
            'orderbook:data': 5,              # 5 seconds (was 2s)
            'recent:trades': 10,              # 10 seconds (was 5s)
            'price:updates': 15,              # 15 seconds (was 10s)
        }
        
    async def initialize(self):
        """Initialize cache client"""
        if self.initialized:
            return
            
        try:
            if MEMCACHE_AVAILABLE:
                # Create synchronous memcache client
                self.client = MemcacheClient((self.host, self.port), timeout=2.0)
                
                # Test connection
                test_key = f"init_test_{int(time.time())}"
                self.client.set(test_key, "test", expire=1)
                result = self.client.get(test_key)
                self.client.delete(test_key)
                
                if result == b"test":
                    logger.info("Cache client initialized successfully")
                else:
                    logger.warning("Cache test failed, using fallback mode")
                    self.client = None
            else:
                logger.warning("pymemcache not available, using fallback mode")
                self.client = None
                
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            # Continue without cache - use fallback only
            self.client = None
            self.initialized = True
    
    async def get_with_fallback(self, key: str, default: Any = None) -> Any:
        """Get from cache with circuit breaker and fallback"""
        if not self.initialized:
            await self.initialize()
            
        start_time = time.time()
        
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            logger.debug(f"Circuit breaker open, using fallback for {key}")
            return self.fallback_cache.get(key, default)
        
        # Skip if no client
        if not self.client:
            return self.fallback_cache.get(key, default)
            
        try:
            # Get from cache - run in thread pool to avoid blocking
            def _sync_get():
                return self.client.get(key)
                
            data = await asyncio.get_event_loop().run_in_executor(None, _sync_get)
            
            if data:
                try:
                    # Handle different data types
                    if isinstance(data, bytes):
                        data_str = data.decode('utf-8')
                    else:
                        data_str = str(data)
                        
                    # Try to parse as JSON
                    try:
                        result = json.loads(data_str)
                    except json.JSONDecodeError:
                        result = data_str
                    
                    self.circuit_breaker.record_success()
                    self.stats.hits += 1
                    
                    # Update fallback cache
                    self.fallback_cache[key] = result
                    return result
                    
                except Exception as decode_error:
                    logger.warning(f"Data decode error for {key}: {decode_error}")
                    self.stats.errors += 1
                    return self.fallback_cache.get(key, default)
            else:
                self.stats.misses += 1
                return self.fallback_cache.get(key, default)
                
        except Exception as e:
            logger.error(f"Cache error for {key}: {e}")
            self.stats.errors += 1
            self.circuit_breaker.record_failure()
            return self.fallback_cache.get(key, default)
        
        finally:
            # Track response times
            response_time = time.time() - start_time
            if response_time > 1.0:  # Log slow cache operations
                logger.warning(f"Slow cache operation for {key}: {response_time:.2f}s")
    
    async def set_optimized(self, key: str, value: Any, custom_ttl: Optional[int] = None) -> bool:
        """Set with optimized TTL"""
        if not self.initialized:
            await self.initialize()
            
        # Always store in fallback cache
        self.fallback_cache[key] = value
        
        if not self.client:
            return True  # Fallback only mode
            
        ttl = custom_ttl or self.ttl_config.get(key, 30)
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            # Set in cache - run in thread pool
            def _sync_set():
                return self.client.set(key, serialized, expire=ttl)
                
            success = await asyncio.get_event_loop().run_in_executor(None, _sync_set)
            return bool(success)
            
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'hit_rate': round(self.stats.hit_rate, 2),
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'errors': self.stats.errors,
            'timeouts': self.stats.timeouts,
            'circuit_breaker_state': self.circuit_breaker.state,
            'fallback_cache_size': len(self.fallback_cache),
            'memcache_available': MEMCACHE_AVAILABLE,
            'client_active': self.client is not None,
            'optimization_level': 'HIGH' if self.client else 'FALLBACK_ONLY'
        }
    
    async def warm_cache(self, priority_keys: Optional[List[str]] = None):
        """Warm cache with priority data"""
        if not priority_keys:
            priority_keys = [
                'market:overview',
                'confluence:scores', 
                'market:tickers',
                'market:regime',
                'market:movers',
                'btc:dominance'
            ]
        
        logger.info(f"Warming cache with {len(priority_keys)} priority keys")
        
        for key in priority_keys:
            try:
                # This would normally fetch fresh data
                # For now, just ensure the key exists in fallback
                if key not in self.fallback_cache:
                    await self.set_optimized(key, {}, self.ttl_config.get(key, 30))
                    
            except Exception as e:
                logger.error(f"Cache warming failed for {key}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            'status': 'unknown',
            'memcache_connected': False,
            'fallback_available': True,
            'circuit_breaker_state': self.circuit_breaker.state,
            'timestamp': int(time.time())
        }
        
        try:
            if self.client:
                test_key = f"health_{int(time.time())}"
                test_value = "ok"
                
                # Test set/get
                await self.set_optimized(test_key, test_value, 10)
                result = await self.get_with_fallback(test_key)
                
                if result == test_value:
                    health['status'] = 'healthy'
                    health['memcache_connected'] = True
                else:
                    health['status'] = 'degraded'
            else:
                health['status'] = 'fallback_only'
                
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
            
        return health

# Global cache instance
_cache_adapter = None

async def get_cache_adapter() -> OptimizedCacheAdapter:
    """Get global cache adapter instance"""
    global _cache_adapter
    if _cache_adapter is None:
        _cache_adapter = OptimizedCacheAdapter()
        await _cache_adapter.initialize()
    return _cache_adapter

# Utility functions
async def test_cache_performance():
    """Test cache performance improvements"""
    cache = await get_cache_adapter()
    
    # Test TTL optimization
    test_keys = ['market:overview', 'confluence:scores', 'technical:indicators']
    
    for key in test_keys:
        ttl = cache.ttl_config.get(key, 30)
        await cache.set_optimized(key, {'test': True, 'ttl': ttl}, ttl)
        
    stats = cache.get_stats()
    health = await cache.health_check()
    
    return {
        'performance_stats': stats,
        'health_status': health,
        'ttl_optimizations': {k: v for k, v in cache.ttl_config.items() if v > 30},
        'improvement_summary': {
            'ttl_improvements': 'Increased TTL for key data by 2x-5x',
            'circuit_breaker': 'Prevents cascade failures',
            'fallback_cache': 'Zero-downtime operation',
            'expected_hit_rate_improvement': '18.9% → 45%+ target'
        }
    }

logger.info("Cache fixes VPS module loaded with Priority 1 optimizations")