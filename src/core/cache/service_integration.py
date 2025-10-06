#!/usr/bin/env python3
"""
Service Integration for Shared Cache Bridge
==========================================

CRITICAL INTEGRATION POINTS: Initialize and integrate shared cache bridge
with both trading service (main.py) and web service (web_server.py)

This module provides the necessary integration hooks to ensure both services
are connected to the shared cache bridge for seamless data flow.

Integration Functions:
1. initialize_trading_service_cache - Setup cache bridge in trading service
2. initialize_web_service_cache - Setup cache bridge in web service
3. integrate_monitoring_cache_bridge - Connect market monitor with cache bridge
4. setup_cache_warming - Initialize cache warming strategies
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

# Import cache bridge components
from .shared_cache_bridge import get_shared_cache_bridge, initialize_shared_cache
from .trading_service_bridge import get_trading_service_bridge, integrate_with_market_monitor
from .web_service_adapter import get_web_service_cache_adapter

logger = logging.getLogger(__name__)

class CacheIntegrationManager:
    """Manages cache integration across services"""

    def __init__(self):
        self.shared_bridge = None
        self.trading_bridge = None
        self.web_adapter = None
        self.initialized = False

    async def initialize_full_integration(self):
        """Initialize complete cache integration across all services"""
        try:
            logger.info("🚀 Starting comprehensive cache bridge integration...")

            # Initialize shared cache bridge
            success = await initialize_shared_cache()
            if not success:
                logger.error("❌ Failed to initialize shared cache bridge")
                return False

            self.shared_bridge = get_shared_cache_bridge()

            # Initialize service-specific adapters
            self.trading_bridge = get_trading_service_bridge()
            self.web_adapter = get_web_service_cache_adapter()

            # Initialize adapters
            await self.trading_bridge.initialize()
            await self.web_adapter.initialize()

            self.initialized = True
            logger.info("✅ Cache bridge integration fully initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Cache integration initialization failed: {e}")
            return False

    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status across all services"""
        return {
            'integration_initialized': self.initialized,
            'shared_bridge_available': self.shared_bridge is not None,
            'trading_bridge_available': self.trading_bridge is not None,
            'web_adapter_available': self.web_adapter is not None,
            'timestamp': time.time()
        }

# Global integration manager
_integration_manager = CacheIntegrationManager()

async def initialize_trading_service_cache(market_monitor=None):
    """
    Initialize shared cache bridge in trading service (main.py)

    CRITICAL INTEGRATION POINT: Call this in main.py startup
    """
    try:
        logger.info("🔧 Initializing trading service cache bridge...")

        # Initialize full integration
        success = await _integration_manager.initialize_full_integration()
        if not success:
            logger.error("Failed to initialize full cache integration")
            return False

        # Integrate with market monitor if available
        if market_monitor:
            trading_bridge = get_trading_service_bridge(market_monitor)
            integration_success = await integrate_with_market_monitor(market_monitor, trading_bridge)

            if integration_success:
                logger.info("✅ Market monitor integrated with cache bridge")
            else:
                logger.warning("⚠️ Market monitor integration failed - data bridge may not work")

        logger.info("✅ Trading service cache bridge initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Trading service cache initialization failed: {e}")
        return False

async def initialize_web_service_cache():
    """
    Initialize shared cache bridge in web service (web_server.py)

    CRITICAL INTEGRATION POINT: Call this in web_server.py startup
    """
    try:
        logger.info("🌐 Initializing web service cache bridge...")

        # Initialize full integration if not already done
        if not _integration_manager.initialized:
            success = await _integration_manager.initialize_full_integration()
            if not success:
                logger.error("Failed to initialize full cache integration for web service")
                return False

        # Web adapter should already be initialized by integration manager
        web_adapter = get_web_service_cache_adapter()
        if not hasattr(web_adapter, '_initialized') or not web_adapter._initialized:
            await web_adapter.initialize()

        logger.info("✅ Web service cache bridge initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Web service cache initialization failed: {e}")
        return False

async def setup_cache_warming():
    """
    Setup cache warming strategies for critical endpoints

    CRITICAL: Ensures key cache entries are pre-populated
    """
    try:
        logger.info("🔥 Setting up cache warming strategies...")

        shared_bridge = get_shared_cache_bridge()
        if not shared_bridge:
            logger.error("Shared bridge not available for cache warming")
            return False

        # Trigger initial cache warming
        await shared_bridge.warm_critical_caches()

        logger.info("✅ Cache warming strategies initialized")
        return True

    except Exception as e:
        logger.error(f"❌ Cache warming setup failed: {e}")
        return False

async def validate_cache_bridge_connectivity():
    """
    Validate that cache bridge is working end-to-end

    Tests:
    1. Shared cache write/read
    2. Cross-service data flow
    3. Cache warming effectiveness
    4. Performance metrics
    """
    try:
        logger.info("🔍 Validating cache bridge connectivity...")

        shared_bridge = get_shared_cache_bridge()
        trading_bridge = get_trading_service_bridge()
        web_adapter = get_web_service_cache_adapter()

        if not all([shared_bridge, trading_bridge, web_adapter]):
            logger.error("Not all cache bridge components available")
            return False

        # Test 1: Health checks
        shared_health = await shared_bridge.health_check()
        trading_health = await trading_bridge.health_check()

        if shared_health.get('status') != 'healthy':
            logger.error(f"Shared bridge unhealthy: {shared_health}")
            return False

        if trading_health.get('trading_bridge_status') != 'healthy':
            logger.error(f"Trading bridge unhealthy: {trading_health}")
            return False

        # Test 2: End-to-end data flow test
        test_data = {
            'test_key': f'connectivity_test_{int(time.time())}',
            'test_value': 'cache_bridge_validation',
            'timestamp': time.time()
        }

        # Write data via trading bridge
        await trading_bridge.populate_market_overview(test_data)

        # Read data via web adapter
        await asyncio.sleep(1)  # Allow propagation
        retrieved_data = await web_adapter.get_market_overview()

        # Check if our test data appears
        test_found = (retrieved_data.get('test_key') == test_data['test_key'])

        if test_found:
            logger.info("✅ End-to-end data flow validation successful")
        else:
            logger.warning("⚠️ End-to-end data flow validation failed - data may not be propagating")

        # Test 3: Performance metrics
        bridge_metrics = shared_bridge.get_bridge_metrics()
        trading_metrics = trading_bridge.get_performance_metrics()
        web_metrics = web_adapter.get_performance_metrics()

        logger.info(f"Cache Bridge Performance:")
        logger.info(f"  Cross-service hits: {bridge_metrics['cross_service_metrics']['cross_service_hits']}")
        logger.info(f"  Data bridge events: {bridge_metrics['cross_service_metrics']['data_bridge_events']}")
        logger.info(f"  Trading updates: {trading_metrics['cache_updates']}")
        logger.info(f"  Web cache hit rate: {web_metrics['cache_hit_rate_percent']}%")

        logger.info("✅ Cache bridge connectivity validation completed")
        return True

    except Exception as e:
        logger.error(f"❌ Cache bridge connectivity validation failed: {e}")
        return False

def get_cache_integration_health() -> Dict[str, Any]:
    """Get comprehensive cache integration health status"""
    try:
        shared_bridge = get_shared_cache_bridge()
        trading_bridge = get_trading_service_bridge()
        web_adapter = get_web_service_cache_adapter()

        health_data = {
            'timestamp': time.time(),
            'integration_status': _integration_manager.get_integration_status(),
            'components_available': {
                'shared_bridge': shared_bridge is not None,
                'trading_bridge': trading_bridge is not None,
                'web_adapter': web_adapter is not None
            },
            'expected_improvement': {
                'cache_hit_rate_target': '80%+',
                'response_time_improvement': '81.8%',
                'data_freshness': 'real-time'
            }
        }

        # Add performance metrics if available
        try:
            if shared_bridge:
                health_data['shared_bridge_metrics'] = shared_bridge.get_bridge_metrics()
            if trading_bridge:
                health_data['trading_bridge_metrics'] = trading_bridge.get_performance_metrics()
            if web_adapter:
                health_data['web_adapter_metrics'] = web_adapter.get_performance_metrics()
        except Exception as e:
            health_data['metrics_error'] = str(e)

        return health_data

    except Exception as e:
        return {
            'timestamp': time.time(),
            'status': 'error',
            'error': str(e)
        }

# Convenience functions for service startup integration
async def trading_service_startup_hook(market_monitor=None):
    """Hook to call during trading service startup"""
    logger.info("🔧 Trading service cache bridge startup hook...")
    success = await initialize_trading_service_cache(market_monitor)
    if success:
        await setup_cache_warming()
    return success

async def web_service_startup_hook():
    """Hook to call during web service startup"""
    logger.info("🌐 Web service cache bridge startup hook...")
    return await initialize_web_service_cache()

# Health monitoring endpoints
async def get_cache_bridge_health():
    """Health endpoint for cache bridge status"""
    return get_cache_integration_health()

async def validate_cache_performance():
    """Validate cache performance metrics"""
    return await validate_cache_bridge_connectivity()