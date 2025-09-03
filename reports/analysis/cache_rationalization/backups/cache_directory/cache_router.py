"""
Intelligent cache router for Phase 2 optimization
Routes data to optimal cache based on type and access patterns

In Hoc Signo Vinces - In this sign you will conquer
"""

import logging
from typing import Any, Optional, Dict
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class CacheRouter:
    """
    Routes data to optimal cache based on type and usage pattern.
    
    Phase 2 Decision Matrix:
    - Dashboard data → Memcached (fastest, <1ms latency)
    - Fallback → In-memory cache (Phase 1, <13ms latency)
    - Future: Time-series → InfluxDB
    - Future: Events → Redis/KeyDB
    """
    
    def __init__(self):
        # Import caches
        self.memcached = None
        self.memory_cache = None
        
        # Try to initialize caches
        self._initialize_caches()
        
        # Cache statistics
        self.stats = {
            'routed_to_memcached': 0,
            'routed_to_memory': 0,
            'fallback_used': 0,
            'errors': 0
        }
        
        # Performance tracking
        self.performance = {
            'memcached_total_time': 0,
            'memory_total_time': 0
        }
    
    def _initialize_caches(self):
        """Initialize cache connections - non-blocking"""
        # Skip memcached for now - it was blocking
        self.memcached = None
        logger.info("⚠️ Memcached disabled to prevent blocking")
        
        # Always have Phase 1 cache as fallback
        try:
            from src.core.api_cache import api_cache
            self.memory_cache = api_cache
            logger.info("✅ Phase 1 memory cache available as fallback")
        except Exception as e:
            logger.error(f"Failed to load Phase 1 cache: {e}")
            self.memory_cache = None
    
    def get(self, key: str, use_memcached: bool = True) -> Optional[Any]:
        """
        Get data from optimal cache.
        
        Args:
            key: Cache key
            use_memcached: Whether to try Memcached first (default: True)
            
        Returns:
            Cached value or None
            
        Performance targets:
        - Memcached: <1ms
        - Memory fallback: <13ms
        """
        start_time = time.perf_counter()
        
        # Try Memcached first if available and enabled
        if use_memcached and self.memcached:
            try:
                value = self.memcached.get(key)
                elapsed = (time.perf_counter() - start_time) * 1000
                self.performance['memcached_total_time'] += elapsed
                
                if value is not None:
                    self.stats['routed_to_memcached'] += 1
                    logger.debug(f"Cache hit from Memcached: {key} ({elapsed:.2f}ms)")
                    return value
            except Exception as e:
                logger.error(f"Memcached error, falling back: {e}")
                self.stats['errors'] += 1
        
        # Fallback to Phase 1 memory cache
        if self.memory_cache:
            try:
                value = self.memory_cache.get(key)
                elapsed = (time.perf_counter() - start_time) * 1000
                self.performance['memory_total_time'] += elapsed
                
                if value is not None:
                    self.stats['routed_to_memory'] += 1
                    self.stats['fallback_used'] += 1
                    logger.debug(f"Cache hit from memory (fallback): {key} ({elapsed:.2f}ms)")
                    return value
            except Exception as e:
                logger.error(f"Memory cache error: {e}")
                self.stats['errors'] += 1
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 30, 
            use_memcached: bool = True, use_fallback: bool = True) -> bool:
        """
        Set data in optimal cache(s).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            use_memcached: Whether to use Memcached
            use_fallback: Whether to also set in fallback cache
            
        Returns:
            Success status
        """
        success = False
        start_time = time.perf_counter()
        
        # Set in Memcached if available
        if use_memcached and self.memcached:
            try:
                if self.memcached.set(key, value, ttl):
                    success = True
                    self.stats['routed_to_memcached'] += 1
                    elapsed = (time.perf_counter() - start_time) * 1000
                    self.performance['memcached_total_time'] += elapsed
                    logger.debug(f"Set in Memcached: {key} ({elapsed:.2f}ms)")
            except Exception as e:
                logger.error(f"Memcached set error: {e}")
                self.stats['errors'] += 1
        
        # Also set in fallback cache for redundancy
        if use_fallback and self.memory_cache:
            try:
                self.memory_cache.set(key, value, ttl_seconds=ttl)
                self.stats['routed_to_memory'] += 1
                if not success:
                    success = True
                    self.stats['fallback_used'] += 1
                elapsed = (time.perf_counter() - start_time) * 1000
                self.performance['memory_total_time'] += elapsed
                logger.debug(f"Set in memory cache: {key}")
            except Exception as e:
                logger.error(f"Memory cache set error: {e}")
                self.stats['errors'] += 1
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete from all caches"""
        success = False
        
        if self.memcached:
            try:
                if self.memcached.delete(key):
                    success = True
            except:
                pass
        
        if self.memory_cache:
            try:
                # Phase 1 cache doesn't have delete, but we can set with 0 TTL
                self.memory_cache.set(key, None, ttl_seconds=0)
                success = True
            except:
                pass
        
        return success
    
    def get_stats(self) -> Dict:
        """Get routing statistics with performance comparison"""
        total_ops = self.stats['routed_to_memcached'] + self.stats['routed_to_memory']
        
        # Calculate average latencies
        memcached_ops = self.stats['routed_to_memcached']
        memory_ops = self.stats['routed_to_memory']
        
        avg_memcached_time = (
            self.performance['memcached_total_time'] / memcached_ops 
            if memcached_ops > 0 else 0
        )
        avg_memory_time = (
            self.performance['memory_total_time'] / memory_ops 
            if memory_ops > 0 else 0
        )
        
        # Calculate percentage improvement
        improvement = 0
        if avg_memory_time > 0 and avg_memcached_time > 0:
            improvement = ((avg_memory_time - avg_memcached_time) / avg_memory_time) * 100
        
        return {
            'total_operations': total_ops,
            'memcached_ops': memcached_ops,
            'memory_ops': memory_ops,
            'fallback_used': self.stats['fallback_used'],
            'errors': self.stats['errors'],
            'avg_memcached_latency_ms': f"{avg_memcached_time:.2f}",
            'avg_memory_latency_ms': f"{avg_memory_time:.2f}",
            'performance_improvement': f"{improvement:.1f}%",
            'memcached_available': self.memcached is not None,
            'memory_cache_available': self.memory_cache is not None
        }
    
    def health_check(self) -> Dict:
        """Check health of all cache layers"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'caches': {}
        }
        
        # Check Memcached
        if self.memcached:
            try:
                self.memcached.set('health_check', 'ok', ttl=1)
                if self.memcached.get('health_check') == 'ok':
                    health['caches']['memcached'] = 'healthy'
                else:
                    health['caches']['memcached'] = 'unhealthy'
            except:
                health['caches']['memcached'] = 'error'
        else:
            health['caches']['memcached'] = 'not_configured'
        
        # Check memory cache
        if self.memory_cache:
            try:
                self.memory_cache.set('health_check', 'ok', ttl_seconds=1)
                if self.memory_cache.get('health_check') == 'ok':
                    health['caches']['memory'] = 'healthy'
                else:
                    health['caches']['memory'] = 'unhealthy'
            except:
                health['caches']['memory'] = 'error'
        else:
            health['caches']['memory'] = 'not_configured'
        
        # Add statistics
        health['stats'] = self.get_stats()
        
        return health

# Global router instance
cache_router = CacheRouter()