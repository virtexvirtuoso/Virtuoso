"""
Unified Cache Client - Standardizes cache access across all Virtuoso components

This module provides a single, consistent interface for cache operations
used by both the main trading process and web server components.

Key features:
- Consistent string-based cache keys
- Standardized JSON serialization
- Connection pooling and error handling
- Circuit breaker pattern for resilience
- Compatible with existing DirectCacheAdapterFixed
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

# Import the fixed adapter
from src.api.cache_adapter_direct_fixed import DirectCacheAdapterFixed, CacheKeyManager

logger = logging.getLogger(__name__)

class UnifiedCacheClient:
    """
    Unified cache client that provides consistent cache access
    for both main process and web server components.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 11211):
        self.host = host
        self.port = port
        self._adapter: Optional[DirectCacheAdapterFixed] = None
        self.key_manager = CacheKeyManager()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the cache adapter"""
        if self._initialized:
            return
            
        self._adapter = DirectCacheAdapterFixed(self.host, self.port)
        await self._adapter.__aenter__()
        self._initialized = True
        logger.info(f"✅ Unified cache client initialized (memcached://{self.host}:{self.port})")
    
    async def close(self):
        """Close the cache adapter"""
        if self._adapter:
            await self._adapter.close()
            self._adapter = None
        self._initialized = False
        logger.info("Unified cache client closed")
    
    async def ensure_initialized(self):
        """Ensure cache client is initialized"""
        if not self._initialized:
            await self.initialize()
    
    # ==================== WRITE OPERATIONS ====================
    
    async def set_market_overview(self, data: Dict[str, Any], ttl: int = 30) -> bool:
        """Set market overview data with standardized key"""
        await self.ensure_initialized()
        return await self._set_json(self.key_manager.get_key('market_overview'), data, ttl)
    
    async def set_analysis_signals(self, signals: List[Dict[str, Any]], ttl: int = 30) -> bool:
        """Set analysis signals with standardized key"""
        await self.ensure_initialized()
        signals_data = {
            'signals': signals,
            'count': len(signals),
            'timestamp': int(time.time()),
            'source': 'continuous_analysis'
        }
        return await self._set_json(self.key_manager.get_key('analysis_signals'), signals_data, ttl)
    
    async def set_market_regime(self, regime: str, ttl: int = 10) -> bool:
        """Set market regime with standardized key"""
        await self.ensure_initialized()
        return await self._set_string(self.key_manager.get_key('market_regime'), regime, ttl)
    
    async def set_market_movers(self, gainers: List[Dict[str, Any]], losers: List[Dict[str, Any]], ttl: int = 10) -> bool:
        """Set market movers with standardized key"""
        await self.ensure_initialized()
        movers_data = {
            'gainers': gainers,
            'losers': losers,
            'timestamp': int(time.time())
        }
        return await self._set_json(self.key_manager.get_key('market_movers'), movers_data, ttl)
    
    async def set_market_breadth(self, breadth_data: Dict[str, Any], ttl: int = 10) -> bool:
        """Set market breadth with standardized key"""
        await self.ensure_initialized()
        return await self._set_json(self.key_manager.get_key('market_breadth'), breadth_data, ttl)
    
    async def set_market_tickers(self, tickers: Dict[str, Any], ttl: int = 10) -> bool:
        """Set market tickers with standardized key"""
        await self.ensure_initialized()
        return await self._set_json(self.key_manager.get_key('market_tickers'), tickers, ttl)
    
    async def set_confluence_breakdown(self, symbol: str, breakdown: Dict[str, Any], ttl: int = 60) -> bool:
        """Set confluence breakdown for a specific symbol"""
        await self.ensure_initialized()
        key = self.key_manager.get_breakdown_key(symbol)
        return await self._set_json(key, breakdown, ttl)
    
    # ==================== READ OPERATIONS ====================
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get comprehensive market overview using DirectCacheAdapterFixed"""
        await self.ensure_initialized()
        return await self._adapter.get_market_overview()
    
    async def get_analysis_signals(self) -> Dict[str, Any]:
        """Get analysis signals using DirectCacheAdapterFixed"""
        await self.ensure_initialized()
        return await self._adapter.get_signals()
    
    async def get_mobile_data(self) -> Dict[str, Any]:
        """Get mobile dashboard data using DirectCacheAdapterFixed"""
        await self.ensure_initialized()
        return await self._adapter.get_mobile_data()
    
    async def get_market_regime(self) -> str:
        """Get market regime"""
        await self.ensure_initialized()
        return await self._adapter._get_with_circuit_breaker(
            self.key_manager.get_key('market_regime'), 'unknown'
        )
    
    async def get_market_movers(self) -> Dict[str, Any]:
        """Get market movers"""
        await self.ensure_initialized()
        return await self._adapter._get_with_circuit_breaker(
            self.key_manager.get_key('market_movers'), {}
        )
    
    async def get_market_breadth(self) -> Dict[str, Any]:
        """Get market breadth"""
        await self.ensure_initialized()
        return await self._adapter._get_with_circuit_breaker(
            self.key_manager.get_key('market_breadth'), {}
        )
    
    async def get_market_tickers(self) -> Dict[str, Any]:
        """Get market tickers"""
        await self.ensure_initialized()
        return await self._adapter._get_with_circuit_breaker(
            self.key_manager.get_key('market_tickers'), {}
        )
    
    async def get_confluence_breakdown(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get confluence breakdown for a specific symbol"""
        await self.ensure_initialized()
        key = self.key_manager.get_breakdown_key(symbol)
        return await self._adapter._get_with_circuit_breaker(key, None)
    
    # ==================== HEALTH & STATS ====================
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        await self.ensure_initialized()
        return self._adapter.get_cache_stats()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get cache health status"""
        await self.ensure_initialized()
        return self._adapter.get_health_status()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        await self.ensure_initialized()
        try:
            result = await self._adapter._get_with_circuit_breaker(key, None)
            return result is not None
        except Exception:
            return False
    
    # ==================== PRIVATE METHODS ====================
    
    async def _set_json(self, key: str, data: Any, ttl: int) -> bool:
        """Set JSON data using the underlying adapter's connection pool"""
        try:
            async with self._adapter.pool_manager.get_connection() as conn:
                serialized_data = json.dumps(data).encode()
                await conn.set(key.encode(), serialized_data, exptime=ttl)
                logger.debug(f"✅ Set cache key '{key}' with TTL {ttl}s")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to set cache key '{key}': {e}")
            return False
    
    async def _set_string(self, key: str, data: str, ttl: int) -> bool:
        """Set string data using the underlying adapter's connection pool"""
        try:
            async with self._adapter.pool_manager.get_connection() as conn:
                await conn.set(key.encode(), data.encode(), exptime=ttl)
                logger.debug(f"✅ Set cache key '{key}' (string) with TTL {ttl}s")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to set cache key '{key}' (string): {e}")
            return False
    
    # ==================== CONTEXT MANAGER ====================
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# ==================== GLOBAL INSTANCE ====================

_global_unified_cache = None

async def get_unified_cache_client() -> UnifiedCacheClient:
    """Get or create the global unified cache client"""
    global _global_unified_cache
    if _global_unified_cache is None:
        _global_unified_cache = UnifiedCacheClient()
        await _global_unified_cache.initialize()
    return _global_unified_cache

@asynccontextmanager
async def unified_cache_context():
    """Context manager for unified cache client"""
    client = UnifiedCacheClient()
    try:
        async with client:
            yield client
    finally:
        await client.close()

# ==================== COMPATIBILITY HELPERS ====================

class CacheWriteMixin:
    """
    Mixin class that provides standardized cache write methods
    for classes that need to push data to cache.
    
    Usage:
        class MyCacheWriter(CacheWriteMixin):
            async def push_my_data(self):
                await self.push_market_overview({...})
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_client: Optional[UnifiedCacheClient] = None
    
    async def get_cache_client(self) -> UnifiedCacheClient:
        """Get or create cache client"""
        if self._cache_client is None:
            self._cache_client = UnifiedCacheClient()
            await self._cache_client.initialize()
        return self._cache_client
    
    async def push_market_overview(self, overview_data: Dict[str, Any], ttl: int = 30) -> bool:
        """Push market overview to cache"""
        cache_client = await self.get_cache_client()
        return await cache_client.set_market_overview(overview_data, ttl)
    
    async def push_analysis_signals(self, signals: List[Dict[str, Any]], ttl: int = 30) -> bool:
        """Push analysis signals to cache"""
        cache_client = await self.get_cache_client()
        return await cache_client.set_analysis_signals(signals, ttl)
    
    async def push_market_regime(self, regime: str, ttl: int = 10) -> bool:
        """Push market regime to cache"""
        cache_client = await self.get_cache_client()
        return await cache_client.set_market_regime(regime, ttl)
    
    async def push_market_movers(self, gainers: List[Dict[str, Any]], losers: List[Dict[str, Any]], ttl: int = 10) -> bool:
        """Push market movers to cache"""
        cache_client = await self.get_cache_client()
        return await cache_client.set_market_movers(gainers, losers, ttl)
    
    async def push_market_breadth(self, breadth_data: Dict[str, Any], ttl: int = 10) -> bool:
        """Push market breadth to cache"""
        cache_client = await self.get_cache_client()
        return await cache_client.set_market_breadth(breadth_data, ttl)
    
    async def push_market_tickers(self, tickers: Dict[str, Any], ttl: int = 10) -> bool:
        """Push market tickers to cache"""
        cache_client = await self.get_cache_client()
        return await cache_client.set_market_tickers(tickers, ttl)
    
    async def cleanup_cache_client(self):
        """Cleanup cache client resources"""
        if self._cache_client:
            await self._cache_client.close()
            self._cache_client = None