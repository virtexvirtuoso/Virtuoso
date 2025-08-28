"""
Cache Fixes - Priority 1 Performance Improvements
Implements optimized TTL settings, circuit breaker, and fallback mechanisms.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import aiomcache

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
    """Cache adapter with Priority 1 fixes"""
    
    def __init__(self, host: str = 'localhost', port: int = 11211):
        self.host = host
        self.port = port
        self.client = None
        self.circuit_breaker = CircuitBreaker()
        self.stats = CacheStats()
        self.fallback_cache: Dict[str, Any] = {}
        
        # Optimized TTL settings (Priority 1 fix)
        self.ttl_config = {
            'market:overview': 120,           # 2 minutes (was 30s)
            'market:overview:v2': 120,        # 2 minutes 
            'confluence:scores': 60,          # 1 minute (was 30s)
            'analysis:confluence:scores': 60, # 1 minute
            'technical:indicators': 60,       # 1 minute (was 30s)
            'dashboard:data': 45,             # 45 seconds (was 30s)
            'signal:analysis': 90,            # 1.5 minutes (was 30s)
            'analysis:signals:active': 90,    # 1.5 minutes
            'top:symbols': 300,               # 5 minutes (was 60s)
            'market:tickers': 30,             # 30 seconds
            'market:tickers:all': 30,         # 30 seconds
            'market:movers': 90,              # 1.5 minutes (was 60s) 
            'market:movers:top': 90,          # 1.5 minutes
            'market:regime': 180,             # 3 minutes (was 60s)
            'market:regime:current': 180,     # 3 minutes
            'btc:dominance': 240,             # 4 minutes (was 60s)
            'market:btc:dominance': 240,      # 4 minutes
            'system:health': 45,              # 45 seconds (was 30s)
            'system:health:status': 45,       # 45 seconds
            'system:alerts': 120,             # 2 minutes (was 60s)
            'market:breadth': 75,             # 1.25 minutes (was 60s)
        }
        
    async def initialize(self):
        """Initialize cache client"""
        try:
            self.client = aiomcache.Client(self.host, self.port)
            # Test connection
            test_key = f"init_test_{int(time.time())}"
            await asyncio.wait_for(
                self.client.set(test_key.encode(), b'test', exptime=1),
                timeout=2.0
            )
            await self.client.delete(test_key.encode())
            logger.info("Cache client initialized successfully")
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            # Continue without cache - use fallback only
            self.client = None
    
    async def get_with_fallback(self, key: str, default: Any = None) -> Any:
        """Get from cache with circuit breaker and fallback"""
        start_time = time.time()
        
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            logger.debug(f"Circuit breaker open, using fallback for {key}")
            return self.fallback_cache.get(key, default)
        
        # Skip if no client
        if not self.client:
            return self.fallback_cache.get(key, default)
            
        try:
            # Get from cache with timeout
            data = await asyncio.wait_for(
                self.client.get(key.encode()),
                timeout=1.5  # Reduced timeout for faster fallback
            )
            
            if data:
                try:
                    result = json.loads(data.decode())
                    self.circuit_breaker.record_success()
                    self.stats.hits += 1
                    
                    # Update fallback cache
                    self.fallback_cache[key] = result
                    return result
                    
                except json.JSONDecodeError:
                    result = data.decode()
                    self.circuit_breaker.record_success() 
                    self.stats.hits += 1
                    return result
            else:
                self.stats.misses += 1
                return self.fallback_cache.get(key, default)
                
        except asyncio.TimeoutError:
            logger.warning(f"Cache timeout for {key}")
            self.stats.timeouts += 1
            self.circuit_breaker.record_failure()
            return self.fallback_cache.get(key, default)
            
        except Exception as e:
            logger.error(f"Cache error for {key}: {e}")
            self.stats.errors += 1
            self.circuit_breaker.record_failure()
            return self.fallback_cache.get(key, default)
    
    async def set_optimized(self, key: str, value: Any, custom_ttl: Optional[int] = None) -> bool:
        """Set with optimized TTL"""
        if not self.client:
            # Store in fallback cache only
            self.fallback_cache[key] = value
            return True
            
        ttl = custom_ttl or self.ttl_config.get(key, 30)
        
        try:
            serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            
            await asyncio.wait_for(
                self.client.set(key.encode(), serialized.encode(), exptime=ttl),
                timeout=1.0
            )
            
            # Also store in fallback
            self.fallback_cache[key] = value
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            # Still store in fallback
            self.fallback_cache[key] = value
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
            'fallback_cache_size': len(self.fallback_cache)
        }

# Global cache instance
_cache_adapter = None

async def get_cache_adapter() -> OptimizedCacheAdapter:
    """Get global cache adapter instance"""
    global _cache_adapter
    if _cache_adapter is None:
        _cache_adapter = OptimizedCacheAdapter()
        await _cache_adapter.initialize()
    return _cache_adapter

logger.info("Cache fixes module loaded with Priority 1 optimizations")