"""
API Cache Manager

Implements a sophisticated caching layer for API responses to reduce redundant calls
and improve performance, especially for high-latency connections.
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from collections import OrderedDict
import pickle

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for different data types."""
    AGGRESSIVE = "aggressive"      # Long TTL, for slow-changing data
    MODERATE = "moderate"          # Medium TTL, for regular updates  
    CONSERVATIVE = "conservative"  # Short TTL, for real-time data
    NO_CACHE = "no_cache"         # No caching


@dataclass
class CacheConfig:
    """Configuration for different endpoint caching strategies."""
    strategy: CacheStrategy
    ttl: int  # Time to live in seconds
    max_size: int = 1000  # Max entries for this cache type
    
    # Endpoint-specific configs
    CONFIGS = {
        # Market structure - changes slowly
        '/v5/market/instruments-info': (CacheStrategy.AGGRESSIVE, 3600),  # 1 hour
        '/v5/market/risk-limit': (CacheStrategy.AGGRESSIVE, 3600),
        
        # Market data - moderate caching
        '/v5/market/tickers': (CacheStrategy.MODERATE, 10),  # 10 seconds
        '/v5/market/kline': (CacheStrategy.MODERATE, 30),    # 30 seconds for historical
        
        # Real-time data - minimal caching
        '/v5/market/orderbook': (CacheStrategy.CONSERVATIVE, 2),  # 2 seconds
        '/v5/market/recent-trade': (CacheStrategy.CONSERVATIVE, 1),  # 1 second
        
        # No caching for critical operations
        '/v5/order/create': (CacheStrategy.NO_CACHE, 0),
        '/v5/order/cancel': (CacheStrategy.NO_CACHE, 0),
        '/v5/position': (CacheStrategy.NO_CACHE, 0),
    }
    
    @classmethod
    def get_config(cls, endpoint: str) -> 'CacheConfig':
        """Get cache configuration for an endpoint."""
        # Try exact match first
        if endpoint in cls.CONFIGS:
            strategy, ttl = cls.CONFIGS[endpoint]
            return cls(strategy=strategy, ttl=ttl)
        
        # Try prefix match
        for path, (strategy, ttl) in cls.CONFIGS.items():
            if endpoint.startswith(path):
                return cls(strategy=strategy, ttl=ttl)
        
        # Default to conservative caching
        return cls(strategy=CacheStrategy.CONSERVATIVE, ttl=5)


class LRUCache:
    """Least Recently Used cache implementation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Tuple[Any, float]]:
        """Get item from cache."""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def put(self, key: str, value: Any, timestamp: float):
        """Put item in cache."""
        if key in self.cache:
            # Update existing
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used
            self.cache.popitem(last=False)
        
        self.cache[key] = (value, timestamp)
    
    def clear_expired(self, current_time: float, ttl: int):
        """Remove expired entries."""
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > ttl
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0


class APICacheManager:
    """
    Manages multiple cache instances with different strategies for various API endpoints.
    """
    
    def __init__(self):
        # Separate caches for different strategies
        self.caches: Dict[CacheStrategy, LRUCache] = {
            CacheStrategy.AGGRESSIVE: LRUCache(max_size=500),
            CacheStrategy.MODERATE: LRUCache(max_size=2000),
            CacheStrategy.CONSERVATIVE: LRUCache(max_size=1000),
        }
        
        # Statistics
        self.total_requests = 0
        self.cache_bypasses = 0
        
        # Cleanup task
        self._cleanup_task = None
        self._running = False
    
    def _generate_cache_key(
        self, 
        endpoint: str, 
        method: str, 
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> str:
        """Generate unique cache key."""
        # Include relevant headers (e.g., API key for user-specific data)
        cache_data = {
            'endpoint': endpoint,
            'method': method,
            'params': params or {},
        }
        
        # Only include certain headers that affect response
        if headers:
            relevant_headers = {
                k: v for k, v in headers.items()
                if k.lower() in ['x-bapi-api-key', 'authorization']
            }
            if relevant_headers:
                cache_data['headers'] = relevant_headers
        
        # Create consistent hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    async def get(
        self,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        force_refresh: bool = False
    ) -> Optional[Any]:
        """
        Get cached response if available and valid.
        
        Returns:
            Cached response or None if not found/expired
        """
        self.total_requests += 1
        
        # Get cache configuration
        config = CacheConfig.get_config(endpoint)
        
        # Skip cache for certain strategies or methods
        if (config.strategy == CacheStrategy.NO_CACHE or 
            method not in ['GET', 'POST'] or 
            force_refresh):
            self.cache_bypasses += 1
            return None
        
        # Generate cache key
        cache_key = self._generate_cache_key(endpoint, method, params, headers)
        
        # Get from appropriate cache
        cache = self.caches.get(config.strategy)
        if not cache:
            return None
        
        # Check cache
        cached_entry = cache.get(cache_key)
        if cached_entry:
            value, timestamp = cached_entry
            
            # Check if still valid
            if time.time() - timestamp <= config.ttl:
                logger.debug(
                    f"Cache hit for {endpoint} "
                    f"(strategy: {config.strategy.value}, "
                    f"age: {time.time() - timestamp:.1f}s)"
                )
                return value
            else:
                logger.debug(f"Cache expired for {endpoint}")
        
        return None
    
    async def set(
        self,
        endpoint: str,
        method: str,
        params: Optional[Dict],
        headers: Optional[Dict],
        response: Any
    ):
        """Store response in cache."""
        # Get cache configuration
        config = CacheConfig.get_config(endpoint)
        
        # Skip if no caching
        if config.strategy == CacheStrategy.NO_CACHE:
            return
        
        # Only cache successful responses
        if not response or (isinstance(response, dict) and 
                           response.get('retCode', 0) != 0):
            return
        
        # Generate cache key
        cache_key = self._generate_cache_key(endpoint, method, params, headers)
        
        # Store in appropriate cache
        cache = self.caches.get(config.strategy)
        if cache:
            cache.put(cache_key, response, time.time())
            logger.debug(
                f"Cached response for {endpoint} "
                f"(strategy: {config.strategy.value}, ttl: {config.ttl}s)"
            )
    
    async def invalidate(
        self, 
        endpoint: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """
        Invalidate cache entries.
        
        Args:
            endpoint: Specific endpoint to invalidate
            pattern: Pattern to match endpoints (e.g., '/v5/market/*')
        """
        if endpoint:
            # Invalidate specific endpoint across all caches
            config = CacheConfig.get_config(endpoint)
            cache = self.caches.get(config.strategy)
            if cache:
                # Would need to track keys by endpoint for this
                # For now, clear the entire strategy cache
                cache.clear()
                logger.info(f"Invalidated cache for strategy: {config.strategy.value}")
        elif pattern:
            # Pattern-based invalidation would require tracking keys
            # For now, clear all caches
            for cache in self.caches.values():
                cache.clear()
            logger.info("Invalidated all caches")
        else:
            # Clear all
            for cache in self.caches.values():
                cache.clear()
            logger.info("Cleared all caches")
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired entries."""
        while self._running:
            try:
                current_time = time.time()
                
                # Clean each cache based on its strategy TTL
                for strategy, cache in self.caches.items():
                    if strategy == CacheStrategy.AGGRESSIVE:
                        cache.clear_expired(current_time, 3600)  # 1 hour
                    elif strategy == CacheStrategy.MODERATE:
                        cache.clear_expired(current_time, 300)   # 5 minutes
                    elif strategy == CacheStrategy.CONSERVATIVE:
                        cache.clear_expired(current_time, 60)    # 1 minute
                
                # Log statistics
                if self.total_requests % 1000 == 0 and self.total_requests > 0:
                    self._log_statistics()
                
                # Run cleanup every 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    def _log_statistics(self):
        """Log cache statistics."""
        stats = self.get_statistics()
        logger.info(
            f"Cache Stats - Total requests: {stats['total_requests']}, "
            f"Overall hit rate: {stats['overall_hit_rate']:.1f}%, "
            f"Bypasses: {stats['cache_bypasses']}"
        )
        
        for strategy, strategy_stats in stats['strategy_stats'].items():
            logger.info(
                f"  {strategy}: Size: {strategy_stats['size']}, "
                f"Hit rate: {strategy_stats['hit_rate']:.1f}%"
            )
    
    async def start(self):
        """Start the cache manager."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cache manager started")
    
    async def stop(self):
        """Stop the cache manager."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self._log_statistics()
        logger.info("Cache manager stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(cache.hits for cache in self.caches.values())
        total_misses = sum(cache.misses for cache in self.caches.values())
        total_attempts = total_hits + total_misses
        
        strategy_stats = {}
        for strategy, cache in self.caches.items():
            strategy_stats[strategy.value] = {
                'size': len(cache.cache),
                'hits': cache.hits,
                'misses': cache.misses,
                'hit_rate': cache.hit_rate * 100
            }
        
        return {
            'total_requests': self.total_requests,
            'cache_bypasses': self.cache_bypasses,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'overall_hit_rate': (total_hits / total_attempts * 100) if total_attempts > 0 else 0,
            'strategy_stats': strategy_stats
        }


# Decorator for automatic caching
def cached_api_call(
    strategy: CacheStrategy = CacheStrategy.MODERATE,
    ttl: Optional[int] = None
):
    """
    Decorator to automatically cache API calls.
    
    Usage:
        @cached_api_call(strategy=CacheStrategy.MODERATE, ttl=30)
        async def get_ticker(self, symbol):
            return await self._make_request(...)
    """
    def decorator(func: Callable):
        async def wrapper(self, *args, **kwargs):
            # Assuming self has cache_manager attribute
            if hasattr(self, 'cache_manager') and self.cache_manager:
                # Extract endpoint from function name or args
                endpoint = kwargs.get('endpoint', f"/{func.__name__}")
                method = kwargs.get('method', 'GET')
                params = kwargs.get('params', {})
                
                # Try cache first
                cached = await self.cache_manager.get(
                    endpoint=endpoint,
                    method=method,
                    params=params
                )
                
                if cached is not None:
                    return cached
                
                # Call original function
                result = await func(self, *args, **kwargs)
                
                # Cache result
                if result:
                    await self.cache_manager.set(
                        endpoint=endpoint,
                        method=method,
                        params=params,
                        headers=None,
                        response=result
                    )
                
                return result
            else:
                # No cache manager, call original
                return await func(self, *args, **kwargs)
        
        return wrapper
    return decorator