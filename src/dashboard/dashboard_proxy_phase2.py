"""
Dashboard Integration Proxy Phase 2 - With Memcached Caching
Optimized for sub-millisecond response times

Deo Gratias - Thanks be to God
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)

class DashboardIntegrationProxyPhase2:
    """
    Phase 2 Dashboard Proxy with Memcached caching.
    Achieves <1ms latency for cached responses.
    """
    
    def __init__(self, main_service_url: str = "http://localhost:8002"):
        self.main_service_url = main_service_url
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Initialize cache router for Phase 2
        self._cache_router = None
        self._init_cache()
        
        # Cache TTLs by data type
        self.cache_ttls = {
            'overview': 10,         # 10 seconds for overview
            'signals': 5,           # 5 seconds for signals
            'alerts': 5,            # 5 seconds for alerts
            'alpha': 15,            # 15 seconds for alpha opportunities
            'market': 30,           # 30 seconds for market overview
            'confluence': 60,       # 60 seconds for confluence analysis
            'symbols': 300,         # 5 minutes for symbols
            'performance': 5        # 5 seconds for performance metrics
        }
        
    def _init_cache(self):
        """Initialize the cache router."""
        try:
            from src.core.cache.cache_router import cache_router
            self._cache_router = cache_router
            logger.info("✅ Phase 2 cache router initialized for dashboard")
        except Exception as e:
            logger.warning(f"Cache router not available, using direct fetch: {e}")
            
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            
    async def _fetch_from_main(self, endpoint: str) -> Dict[str, Any]:
        """Fetch data from main service."""
        try:
            await self._ensure_session()
            url = f"{self.main_service_url}{endpoint}"
            
            async with self._session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Main service returned {resp.status} for {endpoint}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {endpoint} from main service")
            return None
        except Exception as e:
            logger.error(f"Error fetching from main service: {e}")
            return None
            
    async def _get_cached_or_fetch(self, cache_key: str, endpoint: str, 
                                  ttl_type: str = 'overview') -> Optional[Dict]:
        """
        Get data from cache or fetch from main service.
        Uses Phase 2 cache router for optimal performance.
        """
        start_time = time.perf_counter()
        
        # Try cache first if available
        if self._cache_router:
            cached_data = self._cache_router.get(cache_key, use_memcached=True)
            if cached_data:
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Cache hit for {cache_key}: {elapsed:.2f}ms")
                return cached_data
        
        # Fetch from main service
        data = await self._fetch_from_main(endpoint)
        
        # Cache the result if we have data
        if data and self._cache_router:
            ttl = self.cache_ttls.get(ttl_type, 30)
            success = self._cache_router.set(
                cache_key, data, ttl=ttl,
                use_memcached=True, use_fallback=True
            )
            if success:
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Cached {cache_key} (fetch took {elapsed:.2f}ms)")
        
        return data
            
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get dashboard overview with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:overview',
            '/api/dashboard/overview',
            'overview'
        )
        
        if data:
            return data
            
        # Fallback response
        return {
            "status": "no_integration",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals": {"total": 0, "strong": 0, "medium": 0, "weak": 0},
            "alerts": {"total": 0, "critical": 0, "warning": 0},
            "alpha_opportunities": {"total": 0, "high_confidence": 0, "medium_confidence": 0},
            "system_status": {
                "monitoring": "disconnected",
                "data_feed": "disconnected",
                "alerts": "disabled",
                "websocket": "disconnected",
                "last_update": 0
            }
        }
        
    async def get_signals_data(self) -> List[Dict[str, Any]]:
        """Get signals data with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:signals',
            '/api/signals',
            'signals'
        )
        return data if data else []
        
    async def get_alerts_data(self) -> List[Dict[str, Any]]:
        """Get alerts data with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:alerts',
            '/api/alerts/recent',
            'alerts'
        )
        return data if data else []
        
    async def get_alpha_opportunities(self) -> List[Dict[str, Any]]:
        """Get alpha opportunities with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:alpha',
            '/api/alpha-opportunities',
            'alpha'
        )
        return data if data else []
        
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:market',
            '/api/market-overview',
            'market'
        )
        
        if data:
            return data
            
        return {
            "active_symbols": 0,
            "total_volume": 0,
            "market_regime": "unknown",
            "volatility": 0
        }
        
    async def get_confluence_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get confluence analysis for a symbol with Phase 2 caching."""
        cache_key = f'dashboard:confluence:{symbol}'
        data = await self._get_cached_or_fetch(
            cache_key,
            f'/api/confluence-analysis/{symbol}',
            'confluence'
        )
        
        if data:
            return data
            
        return {
            "status": "error",
            "error": "Main service not available",
            "symbol": symbol
        }
        
    async def get_symbols_data(self) -> Dict[str, Any]:
        """Get symbols data with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:symbols',
            '/api/symbols',
            'symbols'
        )
        
        if data:
            return data
            
        return {
            "symbols": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics with Phase 2 caching."""
        data = await self._get_cached_or_fetch(
            'dashboard:performance',
            '/api/performance',
            'performance'
        )
        
        if data:
            return data
            
        # Fallback with cache stats if available
        cache_stats = {}
        if self._cache_router:
            cache_stats = self._cache_router.get_stats()
            
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "api_latency": 0,
            "active_connections": 0,
            "uptime": "0h 0m",
            "cache_stats": cache_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def get_cache_performance(self) -> Dict[str, Any]:
        """Get Phase 2 cache performance metrics."""
        if not self._cache_router:
            return {"status": "cache_not_available"}
            
        stats = self._cache_router.get_stats()
        health = self._cache_router.health_check()
        
        return {
            "stats": stats,
            "health": health,
            "cache_type": "Phase 2 - Memcached",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

# Global instance for Phase 2
_proxy_phase2_instance: Optional[DashboardIntegrationProxyPhase2] = None

def get_dashboard_integration_phase2() -> Optional[DashboardIntegrationProxyPhase2]:
    """Get the Phase 2 dashboard integration proxy instance."""
    global _proxy_phase2_instance
    if _proxy_phase2_instance is None:
        _proxy_phase2_instance = DashboardIntegrationProxyPhase2()
        logger.info("🚀 Phase 2 Dashboard Proxy initialized with Memcached")
    return _proxy_phase2_instance

# Compatibility function - use Phase 2 if available
def get_dashboard_integration() -> Any:
    """
    Get dashboard integration - prefers Phase 2 with fallback to Phase 1.
    """
    try:
        # Try Phase 2 first
        phase2 = get_dashboard_integration_phase2()
        if phase2 and phase2._cache_router:
            logger.debug("Using Phase 2 dashboard integration with Memcached")
            return phase2
    except Exception as e:
        logger.warning(f"Phase 2 not available: {e}")
    
    # Fallback to Phase 1
    from src.dashboard.dashboard_proxy import get_dashboard_integration as get_phase1
    logger.debug("Falling back to Phase 1 dashboard integration")
    return get_phase1()