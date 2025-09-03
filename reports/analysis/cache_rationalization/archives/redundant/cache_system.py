"""
Cache System Initialization
Initializes all cache optimization components for the Virtuoso CCXT system.
"""

import logging
import asyncio
from typing import Optional

from src.api.cache_adapter_direct import cache_adapter
from src.core.cache.batch_operations import BatchCacheManager  
from src.core.cache.ttl_strategy import TTLStrategy
from src.core.cache.warming import CacheWarmingService
from src.api.services.unified_dashboard import UnifiedDashboardService
from src.api.websocket.smart_broadcaster import smart_broadcaster

logger = logging.getLogger(__name__)

class CacheSystem:
    """Unified cache system manager"""
    
    def __init__(self):
        self.cache_adapter = cache_adapter
        self.batch_manager = BatchCacheManager(cache_adapter)
        self.ttl_strategy = TTLStrategy()
        self.warming_service = CacheWarmingService(
            cache_adapter, self.batch_manager, self.ttl_strategy
        )
        self.dashboard_service = UnifiedDashboardService(
            cache_adapter, self.batch_manager
        )
        self.websocket_broadcaster = smart_broadcaster
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all cache components"""
        if self._initialized:
            return
        
        try:
            # Start cache warming service
            await self.warming_service.start()
            
            # Start WebSocket broadcaster
            await self.websocket_broadcaster.start()
            
            # Warm critical cache paths
            await self.warming_service.warm_critical_paths()
            
            self._initialized = True
            logger.info("✅ Cache system initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache system: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all cache components"""
        if not self._initialized:
            return
        
        try:
            await self.warming_service.stop()
            await self.websocket_broadcaster.stop()
            
            self._initialized = False
            logger.info("Cache system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during cache system shutdown: {e}")
    
    def get_system_stats(self):
        """Get comprehensive system statistics"""
        return {
            "cache_adapter": self.cache_adapter.get_stats() if hasattr(self.cache_adapter, 'get_stats') else {},
            "batch_manager": self.batch_manager.get_stats(),
            "ttl_strategy": self.ttl_strategy.get_cache_strategy_summary(),
            "warming_service": self.warming_service.get_warming_stats(),
            "dashboard_service": self.dashboard_service.get_service_stats(),
            "websocket_broadcaster": self.websocket_broadcaster.get_statistics()
        }

# Global cache system instance
cache_system = CacheSystem()

async def initialize_cache_system():
    """Initialize the cache system"""
    await cache_system.initialize()

async def shutdown_cache_system():
    """Shutdown the cache system"""
    await cache_system.shutdown()

def get_cache_system_stats():
    """Get cache system statistics"""
    return cache_system.get_system_stats()
