"""
Integration Example for Applying Resilience Patterns to Existing Components.

This module demonstrates how to integrate the resilience patterns with existing
Virtuoso CCXT components including:
- Bybit exchange with circuit breaker protection
- Cache systems with retry and fallback
- Health monitoring for all critical services
- Metrics collection and monitoring integration
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from ..di.container import DIContainer
from ..exchanges.bybit import BybitExchange
from ...api.cache_adapter_direct import DirectCacheAdapter

from .di_registration import (
    ResilienceManager, 
    ResilienceConfiguration,
    register_resilience_services,
    create_default_resilience_config
)
from .exchange_adapter import create_bybit_resilient_config
from .cache_adapter import create_memcached_resilient_config, create_redis_resilient_config

logger = logging.getLogger(__name__)


class ResilientVirtuosoIntegration:
    """
    Integration class for applying resilience patterns to Virtuoso CCXT components.
    
    This class demonstrates how to wrap existing components with resilience patterns
    and integrate them into the system architecture.
    """
    
    def __init__(self, container: DIContainer):
        self.container = container
        self.resilience_manager: Optional[ResilienceManager] = None
        self._resilient_exchanges: Dict[str, Any] = {}
        self._resilient_caches: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self, config: Optional[ResilienceConfiguration] = None):
        """Initialize resilience integration."""
        if self._initialized:
            return
        
        try:
            # Register resilience services
            self.resilience_manager = register_resilience_services(
                self.container, 
                config or create_default_resilience_config()
            )
            
            # Initialize the resilience manager
            await self.resilience_manager.initialize()
            
            logger.info("Resilient Virtuoso integration initialized")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize resilient integration: {e}")
            raise
    
    async def create_resilient_bybit_exchange(self, config: Dict[str, Any]) -> Any:
        """
        Create a resilient Bybit exchange with circuit breaker protection.
        
        Args:
            config: Exchange configuration dictionary
            
        Returns:
            Resilient exchange adapter wrapping BybitExchange
        """
        if not self._initialized:
            raise RuntimeError("Integration not initialized")
        
        try:
            # Create original Bybit exchange
            bybit_exchange = await BybitExchange.get_instance(config)
            
            # Wrap with resilience patterns
            resilient_exchange = self.resilience_manager.create_resilient_exchange(
                bybit_exchange, 
                "bybit"
            )
            
            # Initialize the resilient wrapper
            await resilient_exchange.initialize()
            
            # Store for management
            self._resilient_exchanges["bybit"] = resilient_exchange
            
            logger.info("Resilient Bybit exchange created successfully")
            return resilient_exchange
            
        except Exception as e:
            logger.error(f"Failed to create resilient Bybit exchange: {e}")
            raise
    
    async def create_resilient_cache_system(self, cache_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create resilient cache adapters for the cache system.
        
        Args:
            cache_config: Cache configuration dictionary
            
        Returns:
            Dictionary of resilient cache adapters
        """
        if not self._initialized:
            raise RuntimeError("Integration not initialized")
        
        resilient_caches = {}
        
        try:
            # Create resilient Memcached adapter if configured
            if cache_config.get('memcached', {}).get('enabled', False):
                # Create original cache client (simplified for example)
                memcached_client = DirectCacheAdapter()  # This would be the actual memcached client
                
                # Wrap with resilience patterns
                resilient_memcached = self.resilience_manager.create_resilient_cache(
                    memcached_client,
                    "memcached"
                )
                
                # Initialize the resilient wrapper
                await resilient_memcached.initialize()
                
                resilient_caches["memcached"] = resilient_memcached
                self._resilient_caches["memcached"] = resilient_memcached
                
                logger.info("Resilient Memcached adapter created")
            
            # Create resilient Redis adapter if configured
            if cache_config.get('redis', {}).get('enabled', False):
                # In a real implementation, you'd create the Redis client here
                redis_client = None  # Placeholder for actual Redis client
                
                if redis_client:  # Only if Redis is actually configured
                    resilient_redis = self.resilience_manager.create_resilient_cache(
                        redis_client,
                        "redis"
                    )
                    
                    await resilient_redis.initialize()
                    
                    resilient_caches["redis"] = resilient_redis
                    self._resilient_caches["redis"] = resilient_redis
                    
                    logger.info("Resilient Redis adapter created")
            
            return resilient_caches
            
        except Exception as e:
            logger.error(f"Failed to create resilient cache system: {e}")
            raise
    
    def setup_health_monitoring(self):
        """Set up comprehensive health monitoring for all resilient components."""
        if not self._initialized:
            raise RuntimeError("Integration not initialized")
        
        try:
            health_service = self.resilience_manager.get_health_service()
            
            # Add status change listener for alerts
            async def on_status_change(status):
                logger.info(f"Overall system health status changed to: {status.value}")
                
                # Here you could integrate with alerting systems
                if status.value in ('unhealthy', 'critical'):
                    logger.critical(f"ALERT: System health is {status.value}")
                    # Send alert to Discord, email, etc.
            
            health_service.add_status_listener(on_status_change)
            
            logger.info("Health monitoring setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup health monitoring: {e}")
            raise
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics from all resilient components."""
        if not self._initialized:
            return {"error": "Integration not initialized"}
        
        try:
            metrics = {
                "timestamp": asyncio.get_event_loop().time(),
                "resilience_manager": self.resilience_manager.get_metrics(),
                "exchanges": {},
                "caches": {}
            }
            
            # Collect exchange metrics
            for name, exchange in self._resilient_exchanges.items():
                if hasattr(exchange, 'get_metrics'):
                    metrics["exchanges"][name] = exchange.get_metrics()
            
            # Collect cache metrics
            for name, cache in self._resilient_caches.items():
                if hasattr(cache, 'get_metrics'):
                    metrics["caches"][name] = cache.get_metrics()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect comprehensive metrics: {e}")
            return {"error": str(e)}
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform immediate health check on all components."""
        if not self._initialized:
            return {"error": "Integration not initialized"}
        
        try:
            health_service = self.resilience_manager.get_health_service()
            results = await health_service.check_all_health()
            
            return {
                "overall_status": health_service.get_overall_status().value,
                "individual_checks": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "timestamp": result.timestamp
                    }
                    for name, result in results.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to perform health check: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Gracefully shutdown all resilient components."""
        try:
            # Close resilient exchanges
            for name, exchange in self._resilient_exchanges.items():
                if hasattr(exchange, 'close'):
                    await exchange.close()
                    logger.info(f"Closed resilient exchange: {name}")
            
            # Close resilient caches
            for name, cache in self._resilient_caches.items():
                if hasattr(cache, 'close'):
                    await cache.close()
                    logger.info(f"Closed resilient cache: {name}")
            
            # Dispose resilience manager
            if self.resilience_manager:
                await self.resilience_manager.dispose()
                logger.info("Disposed resilience manager")
            
            self._resilient_exchanges.clear()
            self._resilient_caches.clear()
            self._initialized = False
            
            logger.info("Resilient integration shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during resilient integration shutdown: {e}")


# Example usage and integration functions

async def example_integration_with_existing_system():
    """
    Example showing how to integrate resilience patterns with existing Virtuoso CCXT system.
    """
    # This would be called from your main application initialization
    
    # Get existing DI container (from your main application)
    container = DIContainer()  # This would be your existing container
    
    # Create resilience integration
    integration = ResilientVirtuosoIntegration(container)
    
    try:
        # Initialize with custom configuration
        resilience_config = create_default_resilience_config()
        resilience_config.enable_circuit_breakers = True
        resilience_config.enable_retry_policies = True
        resilience_config.enable_connection_pooling = True
        resilience_config.enable_health_checks = True
        
        await integration.initialize(resilience_config)
        
        # Create resilient Bybit exchange
        bybit_config = {
            'exchanges': {
                'bybit': {
                    'apiKey': 'your_api_key',
                    'secret': 'your_secret',
                    'rest_endpoint': 'https://api.bybit.com',
                    'testnet': False
                }
            }
        }
        
        resilient_bybit = await integration.create_resilient_bybit_exchange(bybit_config)
        
        # Create resilient cache system
        cache_config = {
            'memcached': {'enabled': True},
            'redis': {'enabled': False}
        }
        
        resilient_caches = await integration.create_resilient_cache_system(cache_config)
        
        # Setup health monitoring
        integration.setup_health_monitoring()
        
        # Example usage of resilient exchange
        try:
            # This will use circuit breaker, retry, and connection pooling
            ticker = await resilient_bybit.fetch_ticker('BTCUSDT')
            logger.info(f"Successfully fetched ticker: {ticker['symbol']}")
            
        except Exception as e:
            logger.error(f"Failed to fetch ticker even with resilience patterns: {e}")
        
        # Example usage of resilient cache
        if 'memcached' in resilient_caches:
            cache = resilient_caches['memcached']
            
            # This will use circuit breaker, retry, and fallback
            await cache.set('test_key', {'data': 'test_value'}, ttl=60)
            value = await cache.get('test_key')
            logger.info(f"Successfully cached and retrieved: {value}")
        
        # Get comprehensive metrics
        metrics = integration.get_comprehensive_metrics()
        logger.info(f"System metrics: {metrics}")
        
        # Perform health check
        health_results = await integration.health_check_all()
        logger.info(f"Health check results: {health_results}")
        
        # In a real application, you'd keep the system running
        # For this example, we'll shutdown after a short time
        await asyncio.sleep(10)
        
    except Exception as e:
        logger.error(f"Error in integration example: {e}")
        
    finally:
        # Always cleanup
        await integration.shutdown()


def integrate_with_main_application(container: DIContainer, app_config: Dict[str, Any]) -> ResilientVirtuosoIntegration:
    """
    Integration function to be called from main application startup.
    
    Args:
        container: Existing DI container
        app_config: Application configuration
        
    Returns:
        ResilientVirtuosoIntegration instance
    """
    # Create resilience configuration from app config
    resilience_config = ResilienceConfiguration(
        enable_circuit_breakers=app_config.get('resilience', {}).get('circuit_breakers', True),
        enable_retry_policies=app_config.get('resilience', {}).get('retry_policies', True),
        enable_connection_pooling=app_config.get('resilience', {}).get('connection_pooling', True),
        enable_health_checks=app_config.get('resilience', {}).get('health_checks', True)
    )
    
    # Create and return integration instance
    integration = ResilientVirtuosoIntegration(container)
    
    # Register for later initialization
    container.register_instance(
        ResilientVirtuosoIntegration, 
        integration, 
        name="resilient_integration"
    )
    
    logger.info("Resilience integration registered with main application")
    return integration


if __name__ == "__main__":
    # Run the example
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_integration_with_existing_system())