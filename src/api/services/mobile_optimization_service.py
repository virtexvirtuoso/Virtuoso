"""
Mobile Optimization Service
Provides ultra-fast mobile dashboard data with intelligent caching and fallbacks
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class MobileOptimizationService:
    """
    Optimized mobile data service with priority loading and intelligent fallbacks
    """
    
    def __init__(self):
        self.cache_adapter = None
        self.priority_warmer = None
        self.fallback_service = None
        self._initialization_complete = False
        self._mobile_data_cache = None
        self._cache_timestamp = 0
        self.mobile_ttl = 15  # 15 second TTL for mobile data
    
    async def initialize_dependencies(self):
        """Initialize service dependencies"""
        try:
            # Import here to avoid circular dependencies
            from src.api.cache_adapter_direct import cache_adapter
            from src.core.cache.priority_warmer import priority_cache_warmer
            from src.api.services.mobile_fallback_service import mobile_fallback_service
            
            self.cache_adapter = cache_adapter
            self.priority_warmer = priority_cache_warmer
            self.fallback_service = mobile_fallback_service
            self._initialization_complete = True
            
            logger.info("✅ Mobile optimization service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize mobile optimization service: {e}")
    
    async def get_optimized_mobile_data(self) -> Dict[str, Any]:
        """
        Get mobile data with intelligent optimization:
        1. Check local mobile cache (15s TTL)
        2. Try priority cache warming if system is starting
        3. Fall back to regular cache adapter
        4. Use direct exchange fallback as last resort
        """
        
        if not self._initialization_complete:
            await self.initialize_dependencies()
        
        try:
            # Step 1: Check local mobile cache (fastest)
            if self._mobile_data_cache and self._is_cache_valid():
                logger.debug("📱 Using local mobile cache")
                self._mobile_data_cache['cache_source'] = 'local_mobile_cache'
                return self._mobile_data_cache
            
            # Step 2: Try priority warming for fast mobile data
            if self.priority_warmer and not self.priority_warmer.warming_stats.get('priority_complete', False):
                logger.info("🔥 Using priority cache warming for mobile data")
                mobile_data = await self.priority_warmer.warm_mobile_cache()
                
                if mobile_data and mobile_data.get('confluence_scores'):
                    self._update_mobile_cache(mobile_data)
                    mobile_data['cache_source'] = 'priority_warming'
                    return mobile_data
            
            # Step 3: Regular cache adapter
            logger.debug("📊 Using regular cache adapter")
            mobile_data = await self.cache_adapter.get_mobile_data()
            
            if mobile_data and mobile_data.get('confluence_scores'):
                self._update_mobile_cache(mobile_data)
                mobile_data['cache_source'] = 'cache_adapter'
                return mobile_data
            
            # Step 4: Direct exchange fallback
            logger.info("🚨 Using direct exchange fallback for mobile")
            fallback_data = await self.fallback_service.get_fallback_mobile_data()
            
            if fallback_data:
                # Don't cache fallback data as heavily
                fallback_data['cache_source'] = 'direct_exchange_fallback'
                return fallback_data
            
            # Step 5: Emergency static fallback
            return self._get_emergency_fallback()
            
        except Exception as e:
            logger.error(f"Mobile optimization service failed: {e}")
            return self._get_emergency_fallback()
    
    async def get_mobile_data_with_performance_tracking(self) -> Dict[str, Any]:
        """Get mobile data with detailed performance tracking"""
        start_time = time.perf_counter()
        
        mobile_data = await self.get_optimized_mobile_data()
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Add performance metadata
        mobile_data.update({
            'performance': {
                'response_time_ms': round(elapsed_ms, 2),
                'cache_source': mobile_data.get('cache_source', 'unknown'),
                'optimization_level': self._get_optimization_level(mobile_data),
                'timestamp': int(time.time())
            }
        })
        
        # Log performance for monitoring
        if elapsed_ms > 1000:
            logger.warning(f"⚡ Mobile response slow: {elapsed_ms:.0f}ms via {mobile_data.get('cache_source')}")
        else:
            logger.debug(f"⚡ Mobile response: {elapsed_ms:.0f}ms via {mobile_data.get('cache_source')}")
        
        return mobile_data
    
    def _is_cache_valid(self) -> bool:
        """Check if local mobile cache is still valid"""
        return time.time() - self._cache_timestamp < self.mobile_ttl
    
    def _update_mobile_cache(self, mobile_data: Dict[str, Any]):
        """Update local mobile cache"""
        self._mobile_data_cache = mobile_data.copy()
        self._cache_timestamp = time.time()
        logger.debug(f"📱 Updated mobile cache with {len(mobile_data.get('confluence_scores', []))} symbols")
    
    def _get_optimization_level(self, mobile_data: Dict[str, Any]) -> str:
        """Determine optimization level based on data source and quality"""
        cache_source = mobile_data.get('cache_source', 'unknown')
        symbol_count = len(mobile_data.get('confluence_scores', []))
        
        if cache_source == 'local_mobile_cache':
            return 'optimal'
        elif cache_source == 'priority_warming' and symbol_count >= 5:
            return 'high'
        elif cache_source == 'cache_adapter' and symbol_count >= 10:
            return 'good'
        elif cache_source == 'direct_exchange_fallback':
            return 'fallback'
        else:
            return 'minimal'
    
    def _get_emergency_fallback(self) -> Dict[str, Any]:
        """Emergency fallback when all systems fail"""
        return {
            'market_overview': {
                'market_regime': 'UNKNOWN',
                'trend_strength': 0,
                'volatility': 0,
                'btc_dominance': 59.3,
                'total_volume_24h': 0
            },
            'confluence_scores': [],
            'top_movers': {
                'gainers': [],
                'losers': []
            },
            'status': 'emergency_fallback',
            'cache_source': 'emergency_static',
            'timestamp': int(time.time()),
            'error_info': 'All data sources failed'
        }
    
    async def preload_mobile_data(self):
        """Preload mobile data to warm local cache"""
        try:
            logger.info("🔄 Preloading mobile data...")
            mobile_data = await self.get_optimized_mobile_data()
            
            if mobile_data and mobile_data.get('confluence_scores'):
                logger.info(f"✅ Mobile data preloaded: {len(mobile_data['confluence_scores'])} symbols")
            else:
                logger.warning("⚠️ Mobile data preload resulted in empty data")
                
        except Exception as e:
            logger.error(f"Mobile data preload failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            'mobile_cache_valid': self._is_cache_valid(),
            'cache_age_seconds': time.time() - self._cache_timestamp if self._cache_timestamp > 0 else 0,
            'cached_symbol_count': len(self._mobile_data_cache.get('confluence_scores', [])) if self._mobile_data_cache else 0,
            'initialization_complete': self._initialization_complete,
            'priority_warmer_stats': self.priority_warmer.get_warming_stats() if self.priority_warmer else {}
        }

# Global service instance
mobile_optimization_service = MobileOptimizationService()