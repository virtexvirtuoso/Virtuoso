"""Caching layer for analysis results."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, field
import logging

@dataclass
class CacheEntry:
    """Cache entry with data and metadata."""
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: Optional[timedelta] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if not self.ttl:
            return False
        return (datetime.utcnow() - self.timestamp) > self.ttl

@dataclass
class AnalysisCache:
    """Cache for analysis results."""
    
    max_size: int = 1000
    default_ttl: Optional[timedelta] = timedelta(minutes=5)
    cleanup_interval: int = 300  # 5 minutes
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("AnalysisCache")
    )
    
    _cache: Dict[str, CacheEntry] = field(default_factory=dict)
    _cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start cache cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop cache cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if available and not expired."""
        entry = self._cache.get(key)
        if not entry:
            return None
            
        if entry.is_expired:
            del self._cache[key]
            return None
            
        return entry.data
    
    def set(self, 
            key: str, 
            data: Dict[str, Any],
            ttl: Optional[timedelta] = None) -> None:
        """Cache analysis results."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.items(), 
                           key=lambda x: x[1].timestamp)[0]
            del self._cache[oldest_key]
        
        self._cache[key] = CacheEntry(
            data=data,
            ttl=ttl or self.default_ttl
        )
    
    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.utcnow()
        expired = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        for key in expired:
            del self._cache[key] 