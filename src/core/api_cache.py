"""
API Cache Implementation for Virtuoso Trading System
Phase 1 Emergency Fix - Memory-based caching with TTL

Christus Vincit, Christus Regnat, Christus Imperat
Christ Conquers, Christ Reigns, Christ Commands
- Ancient acclamation of the Knights of Columbus
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class APICache:
    """
    Simple in-memory cache with TTL support for API responses.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self, default_ttl_seconds: int = 30):
        """
        Initialize the API cache.
        
        Args:
            default_ttl_seconds: Default time-to-live for cache entries
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.lock = Lock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
        logger.info(f"API Cache initialized with {default_ttl_seconds}s TTL")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if valid, None if missing or expired
        """
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() - entry['timestamp'] < entry['ttl']:
                    self.stats['hits'] += 1
                    logger.debug(f"Cache HIT for key: {key}")
                    return entry['data']
                else:
                    # Entry expired, remove it
                    del self.cache[key]
                    self.stats['evictions'] += 1
                    logger.debug(f"Cache EXPIRED for key: {key}")
            
            self.stats['misses'] += 1
            logger.debug(f"Cache MISS for key: {key}")
            return None
    
    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        """
        Store a value in cache with TTL.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: Optional custom TTL in seconds
        """
        with self.lock:
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now(),
                'ttl': ttl
            }
            self.stats['sets'] += 1
            logger.debug(f"Cache SET for key: {key} with TTL: {ttl.seconds}s")
    
    def delete(self, key: str) -> bool:
        """
        Remove a key from cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was removed, False if key didn't exist
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache DELETE for key: {key}")
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            logger.info("Cache CLEARED")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'sets': self.stats['sets'],
                'evictions': self.stats['evictions'],
                'hit_rate': f"{hit_rate:.1f}%",
                'total_requests': total_requests
            }
    
    def cleanup_expired(self):
        """Remove all expired entries from cache."""
        with self.lock:
            now = datetime.now()
            expired_keys = []
            
            for key, entry in self.cache.items():
                if now - entry['timestamp'] >= entry['ttl']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                self.stats['evictions'] += 1
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


class DashboardCache:
    """
    Specialized cache for dashboard data with pre-computation support.
    """
    
    def __init__(self):
        """Initialize dashboard-specific cache."""
        self.cache = APICache(default_ttl_seconds=30)
        self.computing = {}  # Track what's being computed
        self.last_computation = {}  # Track computation times
        
    async def get_or_compute(self, key: str, compute_func, ttl: int = 30):
        """
        Get from cache or compute if missing.
        Prevents duplicate computations for the same key.
        
        Args:
            key: Cache key
            compute_func: Async function to compute the value
            ttl: Time-to-live in seconds
            
        Returns:
            Cached or computed value
        """
        # Check cache first
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        
        # Check if already computing
        if key in self.computing:
            # Wait for existing computation
            logger.info(f"Waiting for existing computation of {key}")
            while key in self.computing:
                await asyncio.sleep(0.1)
            # Try cache again
            cached = self.cache.get(key)
            if cached is not None:
                return cached
        
        # Mark as computing
        self.computing[key] = datetime.now()
        
        try:
            # Compute with timeout
            logger.info(f"Computing {key}...")
            start_time = datetime.now()
            
            try:
                result = await asyncio.wait_for(compute_func(), timeout=10.0)
                computation_time = (datetime.now() - start_time).total_seconds()
                
                # Store in cache
                self.cache.set(key, result, ttl)
                self.last_computation[key] = {
                    'time': computation_time,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"Computed {key} in {computation_time:.2f}s")
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"Computation timeout for {key}")
                # Return a default/error response
                return {
                    'status': 'computing',
                    'message': 'Data is being computed, please try again',
                    'data': []
                }
                
        finally:
            # Remove from computing
            if key in self.computing:
                del self.computing[key]
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get cache and computation status.
        
        Returns:
            Status dictionary
        """
        return {
            'cache_stats': self.cache.get_stats(),
            'computing': list(self.computing.keys()),
            'last_computations': {
                k: {
                    'time_seconds': v['time'],
                    'age_seconds': (datetime.now() - v['timestamp']).total_seconds()
                }
                for k, v in self.last_computation.items()
            }
        }


# Global cache instances
api_cache = APICache(default_ttl_seconds=30)
dashboard_cache = DashboardCache()

# Background cleanup task
async def cache_cleanup_task():
    """Background task to periodically clean up expired cache entries."""
    while True:
        await asyncio.sleep(60)  # Run every minute
        api_cache.cleanup_expired()
        dashboard_cache.cache.cleanup_expired()
        logger.debug("Cache cleanup completed")