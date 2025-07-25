"""Validation result caching.

This module provides caching functionality for validation results:
- ValidationCache: Cache for validation results
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field

from .models import ValidationResult
from .context import ValidationContext

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry for validation results.
    
    Attributes:
        result: Cached validation result
        context: Original validation context
        timestamp: When result was cached
        ttl: Time-to-live for entry
        metadata: Additional cache metadata
    """
    result: ValidationResult
    context: ValidationContext
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired.
        
        Returns:
            bool: True if expired
        """
        return datetime.now() - self.timestamp > self.ttl

class ValidationCache:
    """Cache for validation results.
    
    Provides caching functionality for validation results with:
    - TTL-based expiration
    - Automatic cleanup
    - Cache invalidation
    - Cache statistics
    """
    
    def __init__(
        self,
        ttl: timedelta = timedelta(minutes=5),
        cleanup_interval: int = 60
    ):
        """Initialize validation cache.
        
        Args:
            ttl: Default time-to-live for entries
            cleanup_interval: Seconds between cleanup runs
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = ttl
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._cleanups = 0
        
        # Locks
        self._cache_lock = asyncio.Lock()
        
    async def start(self) -> None:
        """Start cache cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(
                self._cleanup_loop()
            )
            logger.info("Started validation cache cleanup task")
            
    async def stop(self) -> None:
        """Stop cache cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped validation cache cleanup task")
            
    async def get(
        self,
        key: str,
        context: ValidationContext
    ) -> Optional[ValidationResult]:
        """Get cached validation result.
        
        Args:
            key: Cache key
            context: Validation context
            
        Returns:
            Optional[ValidationResult]: Cached result if found
        """
        async with self._cache_lock:
            entry = self._cache.get(key)
            if entry is not None:
                if entry.is_expired:
                    await self.invalidate(key)
                    self._misses += 1
                    return None
                    
                self._hits += 1
                return entry.result
                
            self._misses += 1
            return None
            
    async def set(
        self,
        key: str,
        result: ValidationResult,
        context: ValidationContext,
        ttl: Optional[timedelta] = None
    ) -> None:
        """Cache validation result.
        
        Args:
            key: Cache key
            result: Validation result to cache
            context: Validation context
            ttl: Optional TTL override
        """
        async with self._cache_lock:
            self._cache[key] = CacheEntry(
                result=result,
                context=context,
                ttl=ttl or self._default_ttl
            )
            
    async def invalidate(self, key: str) -> None:
        """Invalidate cached result.
        
        Args:
            key: Cache key to invalidate
        """
        async with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                self._invalidations += 1
                
    async def clear(self) -> None:
        """Clear all cached results."""
        async with self._cache_lock:
            self._cache.clear()
            self._invalidations += len(self._cache)
            
    async def _cleanup_loop(self) -> None:
        """Background task to clean expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}")
                
    async def _cleanup(self) -> None:
        """Clean expired cache entries."""
        async with self._cache_lock:
            expired = {
                key for key, entry in self._cache.items()
                if entry.is_expired
            }
            
            for key in expired:
                del self._cache[key]
                
            if expired:
                self._cleanups += 1
                logger.debug(f"Cleaned {len(expired)} expired cache entries")
                
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": (
                self._hits / (self._hits + self._misses)
                if self._hits + self._misses > 0
                else 0
            ),
            "invalidations": self._invalidations,
            "cleanups": self._cleanups
        } 