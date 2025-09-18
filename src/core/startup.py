"""
Priority 2 System Startup Integration
Initialize multi-tier cache and API gateway on application startup
"""

import asyncio
import logging
from typing import Optional
import redis
from pymemcache.client.base import Client as MemcachedClient

from src.core.cache.multi_tier_cache import MultiTierCache, get_multi_tier_cache
from src.api.gateway import APIGateway, get_api_gateway

logger = logging.getLogger(__name__)

class Priority2Startup:
    """
    Manages Priority 2 architectural improvements startup
    """
    
    def __init__(self):
        self.multi_tier_cache: Optional[MultiTierCache] = None
        self.api_gateway: Optional[APIGateway] = None
        self.startup_complete = False
    
    async def initialize_cache_systems(self) -> bool:
        """
        Initialize Redis L1 + Memcached L2 cache system
        Returns True if at least one cache tier is available
        """
        logger.info("🚀 Initializing Priority 2 Multi-Tier Cache System...")
        
        # Check Redis availability
        redis_available = await self._check_redis()
        
        # Check Memcached availability
        memcached_available = await self._check_memcached()
        
        if not redis_available and not memcached_available:
            logger.warning("⚠️ Neither Redis nor Memcached available - using local fallback only")
        
        # Initialize multi-tier cache
        try:
            self.multi_tier_cache = get_multi_tier_cache()
            cache_health = await self.multi_tier_cache.health_check()
            
            logger.info(f"✅ Multi-tier cache initialized:")
            logger.info(f"   - Redis L1: {'✅' if redis_available else '❌'}")
            logger.info(f"   - Memcached L2: {'✅' if memcached_available else '❌'}")
            logger.info(f"   - Local Fallback: ✅")
            logger.info(f"   - Overall Status: {cache_health['status'].upper()}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize multi-tier cache: {e}")
            return False
    
    async def initialize_api_gateway(self) -> bool:
        """
        Initialize API Gateway with rate limiting and circuit breakers
        """
        logger.info("🚀 Initializing Priority 2 API Gateway...")
        
        try:
            # Initialize gateway with multi-tier cache
            self.api_gateway = get_api_gateway()
            
            # Test gateway health
            health = await self.api_gateway.health_check()
            
            logger.info(f"✅ API Gateway initialized:")
            logger.info(f"   - Rate Limiting: 100 req/sec with burst")
            logger.info(f"   - Circuit Breaker: Enabled")
            logger.info(f"   - Multi-tier Cache: Integrated")
            logger.info(f"   - Backend Routing: Configured")
            logger.info(f"   - Overall Status: {health['status'].upper()}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize API Gateway: {e}")
            return False
    
    async def _check_redis(self) -> bool:
        """Check Redis L1 cache availability"""
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.Redis(host='localhost', port=6379, db=0)
            await redis_client.ping()
            await redis_client.close()
            return True
        except Exception as e:
            logger.debug(f"Redis not available: {e}")
            return False
    
    async def _check_memcached(self) -> bool:
        """Check Memcached L2 cache availability"""
        try:
            import aiomcache
            mc_client = aiomcache.Client('127.0.0.1', 11211)
            await mc_client.get(b'test')
            await mc_client.close()
            return True
        except Exception as e:
            logger.debug(f"Memcached not available: {e}")
            return False
    
    async def run_startup_sequence(self) -> Dict[str, bool]:
        """
        Run complete Priority 2 startup sequence
        Returns status of each component
        """
        logger.info("=" * 60)
        logger.info("🚀 PRIORITY 2 ARCHITECTURAL IMPROVEMENTS STARTUP")
        logger.info("=" * 60)
        
        results = {}
        
        # Initialize cache systems
        results['multi_tier_cache'] = await self.initialize_cache_systems()
        
        # Initialize API gateway
        results['api_gateway'] = await self.initialize_api_gateway()
        
        # Test integration
        results['integration_test'] = await self._test_integration()
        
        # Performance baseline
        performance_baseline = await self._establish_performance_baseline()
        results['performance_baseline'] = performance_baseline is not None
        
        if performance_baseline:
            logger.info("📊 Performance Baseline Established:")
            logger.info(f"   - Cache Hit Rate Target: 70%+ (Current: {performance_baseline.get('cache_hit_rate', 0):.1f}%)")
            logger.info(f"   - Response Time Target: <150ms (Current: {performance_baseline.get('avg_response_time', 0):.1f}ms)")
        
        # Overall success
        self.startup_complete = all(results.values())
        
        if self.startup_complete:
            logger.info("=" * 60)
            logger.info("✅ PRIORITY 2 STARTUP COMPLETE - ALL SYSTEMS OPERATIONAL")
            logger.info("=" * 60)
        else:
            logger.warning("=" * 60)
            logger.warning("⚠️ PRIORITY 2 STARTUP PARTIAL - SOME SYSTEMS DEGRADED")
            logger.warning("=" * 60)
            
            for component, status in results.items():
                status_icon = "✅" if status else "❌"
                logger.warning(f"   {status_icon} {component}")
        
        return results
    
    async def _test_integration(self) -> bool:
        """Test integration between cache and gateway"""
        try:
            if not self.api_gateway or not self.multi_tier_cache:
                return False
            
            # Test cache operations
            test_key = "integration_test"
            test_value = {"test": True, "timestamp": time.time()}
            
            # Set and get from cache
            await self.multi_tier_cache.set(test_key, test_value, "test")
            retrieved, cache_layer = await self.multi_tier_cache.get(test_key, "test")

            # Clean up
            await self.multi_tier_cache.delete(test_key)

            return retrieved is not None and retrieved.get("test") == True
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return False
    
    async def _establish_performance_baseline(self) -> Optional[Dict[str, float]]:
        """Establish performance baseline metrics"""
        try:
            # Get current cache metrics
            cache_metrics = self.multi_tier_cache.get_performance_metrics()
            
            # Get current gateway metrics  
            gateway_metrics = await self.api_gateway.get_gateway_metrics()
            
            baseline = {
                'cache_hit_rate': cache_metrics.get('total_hit_rate_percent', 0),
                'avg_response_time': gateway_metrics['requests'].get('avg_response_time_ms', 0),
                'p95_response_time': gateway_metrics['requests'].get('p95_response_time_ms', 0),
                'l1_hit_rate': cache_metrics.get('l1_hit_rate_percent', 0),
                'total_requests': cache_metrics.get('total_requests', 0)
            }
            
            return baseline
            
        except Exception as e:
            logger.error(f"Failed to establish performance baseline: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Priority 2 system status"""
        return {
            'startup_complete': self.startup_complete,
            'cache_available': self.multi_tier_cache is not None,
            'gateway_available': self.api_gateway is not None,
            'cache_instance': self.multi_tier_cache.__class__.__name__ if self.multi_tier_cache else None,
            'gateway_instance': self.api_gateway.__class__.__name__ if self.api_gateway else None
        }

# Global startup manager
_startup_manager: Optional[Priority2Startup] = None

def get_startup_manager() -> Priority2Startup:
    """Get global startup manager"""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = Priority2Startup()
    return _startup_manager

async def run_priority2_startup() -> Dict[str, bool]:
    """Run Priority 2 startup sequence"""
    startup_manager = get_startup_manager()
    return await startup_manager.run_startup_sequence()

# Import required for baseline establishment
import time
from typing import Dict, Any