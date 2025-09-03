"""
Dependency Injection Registration for Resilience Patterns.

This module provides registration of resilience components with the DI container:
- Circuit breaker service registrations
- Retry policy configurations  
- Connection pool manager registration
- Health check service integration
- Resilient adapter factory registrations
- Configuration management integration
"""

import logging
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass

from ..di.container import DIContainer, ServiceLifetime
from ..interfaces.services import IAsyncDisposable

from .circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from .retry_policy import create_exponential_retry, RetryConfig, BackoffStrategy
from .connection_pool import get_connection_pool_manager, ConnectionPoolManager, PoolConfig
from .health_check import get_health_service, HealthCheckService
from .exchange_adapter import (
    ResilientExchangeAdapter, 
    ExchangeResilienceConfig,
    create_bybit_resilient_config,
    create_binance_resilient_config
)
from .cache_adapter import (
    ResilientCacheAdapter,
    CacheResilienceConfig, 
    create_memcached_resilient_config,
    create_redis_resilient_config
)

logger = logging.getLogger(__name__)


@dataclass
class ResilienceConfiguration:
    """Global configuration for resilience patterns."""
    
    # Feature flags
    enable_circuit_breakers: bool = True
    enable_retry_policies: bool = True
    enable_connection_pooling: bool = True
    enable_health_checks: bool = True
    
    # Global circuit breaker defaults
    default_failure_threshold: int = 5
    default_success_threshold: int = 3
    default_circuit_timeout: float = 60.0
    
    # Global retry defaults
    default_max_retries: int = 3
    default_base_delay: float = 1.0
    default_max_delay: float = 60.0
    default_backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    
    # Global connection pool defaults
    default_max_connections: int = 100
    default_max_connections_per_host: int = 30
    default_connection_timeout: float = 10.0
    default_request_timeout: float = 30.0
    
    # Health check defaults
    default_health_check_interval: float = 60.0
    default_health_check_timeout: float = 10.0
    
    # Service-specific overrides
    exchange_configs: Dict[str, ExchangeResilienceConfig] = None
    cache_configs: Dict[str, CacheResilienceConfig] = None
    
    def __post_init__(self):
        """Initialize default configurations."""
        if self.exchange_configs is None:
            self.exchange_configs = {
                'bybit': create_bybit_resilient_config(),
                'binance': create_binance_resilient_config()
            }
        
        if self.cache_configs is None:
            self.cache_configs = {
                'memcached': create_memcached_resilient_config(),
                'redis': create_redis_resilient_config()
            }


class ResilienceServiceRegistrar:
    """Service registrar for resilience patterns."""
    
    def __init__(self, container: DIContainer, config: ResilienceConfiguration):
        self.container = container
        self.config = config
    
    def register_all_services(self):
        """Register all resilience services with the DI container."""
        logger.info("Registering resilience services with DI container")
        
        # Register core services
        self._register_core_services()
        
        # Register factories
        self._register_factories()
        
        # Register adapters
        self._register_adapters()
        
        # Register health checks
        if self.config.enable_health_checks:
            self._register_health_checks()
        
        logger.info("Resilience services registration completed")
    
    def _register_core_services(self):
        """Register core resilience services."""
        
        # Register resilience configuration as singleton
        self.container.register_instance(
            ResilienceConfiguration,
            self.config,
            name="resilience_config"
        )
        
        # Register connection pool manager as singleton
        if self.config.enable_connection_pooling:
            self.container.register_factory(
                ConnectionPoolManager,
                lambda: get_connection_pool_manager(),
                lifetime=ServiceLifetime.SINGLETON,
                name="connection_pool_manager"
            )
        
        # Register health check service as singleton
        if self.config.enable_health_checks:
            self.container.register_factory(
                HealthCheckService,
                lambda: get_health_service(),
                lifetime=ServiceLifetime.SINGLETON,
                name="health_check_service"
            )
    
    def _register_factories(self):
        """Register factory functions for creating resilience components."""
        
        # Circuit breaker factory
        if self.config.enable_circuit_breakers:
            def circuit_breaker_factory(name: str, config: Optional[CircuitBreakerConfig] = None):
                if config is None:
                    config = CircuitBreakerConfig(
                        name=name,
                        failure_threshold=self.config.default_failure_threshold,
                        success_threshold=self.config.default_success_threshold,
                        timeout=self.config.default_circuit_timeout
                    )
                return get_circuit_breaker(name, config)
            
            self.container.register_factory(
                "circuit_breaker_factory",
                circuit_breaker_factory,
                lifetime=ServiceLifetime.SINGLETON
            )
        
        # Retry policy factory
        if self.config.enable_retry_policies:
            def retry_policy_factory(name: str, config: Optional[RetryConfig] = None):
                if config is None:
                    config = RetryConfig(
                        name=name,
                        max_attempts=self.config.default_max_retries,
                        base_delay=self.config.default_base_delay,
                        max_delay=self.config.default_max_delay,
                        backoff_strategy=self.config.default_backoff_strategy
                    )
                return create_exponential_retry(
                    name=config.name,
                    max_attempts=config.max_attempts,
                    base_delay=config.base_delay,
                    max_delay=config.max_delay,
                    jitter=config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER
                )
            
            self.container.register_factory(
                "retry_policy_factory",
                retry_policy_factory,
                lifetime=ServiceLifetime.SINGLETON
            )
        
        # Connection pool factory
        if self.config.enable_connection_pooling:
            def connection_pool_factory(name: str, config: Optional[PoolConfig] = None):
                if config is None:
                    config = PoolConfig(
                        name=name,
                        max_connections=self.config.default_max_connections,
                        max_connections_per_host=self.config.default_max_connections_per_host,
                        connect_timeout=self.config.default_connection_timeout,
                        request_timeout=self.config.default_request_timeout
                    )
                
                manager = get_connection_pool_manager()
                return manager.get_pool(name, config)
            
            self.container.register_factory(
                "connection_pool_factory",
                connection_pool_factory,
                lifetime=ServiceLifetime.SINGLETON
            )
    
    def _register_adapters(self):
        """Register adapter factories."""
        
        # Resilient exchange adapter factory
        def exchange_adapter_factory(exchange, exchange_name: str):
            config = self.config.exchange_configs.get(
                exchange_name, 
                ExchangeResilienceConfig(exchange_name=exchange_name)
            )
            return ResilientExchangeAdapter(exchange, config)
        
        self.container.register_factory(
            "resilient_exchange_factory",
            exchange_adapter_factory,
            lifetime=ServiceLifetime.TRANSIENT
        )
        
        # Resilient cache adapter factory
        def cache_adapter_factory(cache_client, cache_name: str):
            config = self.config.cache_configs.get(
                cache_name,
                CacheResilienceConfig(cache_name=cache_name)
            )
            return ResilientCacheAdapter(cache_client, config)
        
        self.container.register_factory(
            "resilient_cache_factory", 
            cache_adapter_factory,
            lifetime=ServiceLifetime.TRANSIENT
        )
    
    def _register_health_checks(self):
        """Register health check implementations."""
        
        from .health_check import ConnectionPoolHealthCheck, CircuitBreakerHealthCheck
        
        # Connection pool health check factory
        def pool_health_check_factory(pool_name: str):
            config = HealthCheckConfig(
                name=f"{pool_name}_pool_health",
                interval=self.config.default_health_check_interval,
                timeout=self.config.default_health_check_timeout
            )
            return ConnectionPoolHealthCheck(config.name, pool_name, config)
        
        self.container.register_factory(
            "pool_health_check_factory",
            pool_health_check_factory,
            lifetime=ServiceLifetime.TRANSIENT
        )
        
        # Circuit breaker health check factory
        def circuit_breaker_health_check_factory(cb_name: str):
            config = HealthCheckConfig(
                name=f"{cb_name}_cb_health",
                interval=self.config.default_health_check_interval,
                timeout=self.config.default_health_check_timeout
            )
            return CircuitBreakerHealthCheck(config.name, cb_name, config)
        
        self.container.register_factory(
            "circuit_breaker_health_check_factory",
            circuit_breaker_health_check_factory,
            lifetime=ServiceLifetime.TRANSIENT
        )


class ResilienceManager(IAsyncDisposable):
    """
    Manager class for resilience patterns integration.
    
    Provides high-level interface for managing resilience components
    and integrating with the existing system architecture.
    """
    
    def __init__(self, container: DIContainer, config: ResilienceConfiguration):
        self.container = container
        self.config = config
        self._registrar = ResilienceServiceRegistrar(container, config)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the resilience manager."""
        if self._initialized:
            return
        
        try:
            # Register services with DI container
            self._registrar.register_all_services()
            
            # Initialize core services
            if self.config.enable_connection_pooling:
                pool_manager = self.container.resolve(ConnectionPoolManager, "connection_pool_manager")
                pool_manager.set_global_config(PoolConfig(
                    max_connections=self.config.default_max_connections,
                    max_connections_per_host=self.config.default_max_connections_per_host,
                    connect_timeout=self.config.default_connection_timeout,
                    request_timeout=self.config.default_request_timeout
                ))
            
            self._initialized = True
            logger.info("Resilience manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize resilience manager: {e}")
            raise
    
    def create_resilient_exchange(self, exchange, exchange_name: str) -> ResilientExchangeAdapter:
        """Create a resilient exchange adapter."""
        if not self._initialized:
            raise RuntimeError("Resilience manager not initialized")
        
        factory = self.container.resolve("resilient_exchange_factory")
        adapter = factory(exchange, exchange_name)
        
        logger.info(f"Created resilient exchange adapter for {exchange_name}")
        return adapter
    
    def create_resilient_cache(self, cache_client, cache_name: str) -> ResilientCacheAdapter:
        """Create a resilient cache adapter."""
        if not self._initialized:
            raise RuntimeError("Resilience manager not initialized")
        
        factory = self.container.resolve("resilient_cache_factory")
        adapter = factory(cache_client, cache_name)
        
        logger.info(f"Created resilient cache adapter for {cache_name}")
        return adapter
    
    def get_connection_pool_manager(self) -> ConnectionPoolManager:
        """Get the connection pool manager."""
        return self.container.resolve(ConnectionPoolManager, "connection_pool_manager")
    
    def get_health_service(self) -> HealthCheckService:
        """Get the health check service."""
        return self.container.resolve(HealthCheckService, "health_check_service")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive resilience metrics."""
        metrics = {
            'resilience_manager': {
                'initialized': self._initialized,
                'config': {
                    'circuit_breakers_enabled': self.config.enable_circuit_breakers,
                    'retry_policies_enabled': self.config.enable_retry_policies,
                    'connection_pooling_enabled': self.config.enable_connection_pooling,
                    'health_checks_enabled': self.config.enable_health_checks
                }
            }
        }
        
        try:
            # Add connection pool metrics
            if self.config.enable_connection_pooling:
                pool_manager = self.get_connection_pool_manager()
                metrics['connection_pools'] = pool_manager.get_global_metrics()
            
            # Add health check metrics  
            if self.config.enable_health_checks:
                health_service = self.get_health_service()
                metrics['health_checks'] = health_service.get_metrics()
            
            # Add circuit breaker metrics
            if self.config.enable_circuit_breakers:
                from .circuit_breaker import get_circuit_breaker_metrics
                metrics['circuit_breakers'] = get_circuit_breaker_metrics()
                
        except Exception as e:
            logger.error(f"Error collecting resilience metrics: {e}")
            metrics['metrics_error'] = str(e)
        
        return metrics
    
    async def dispose(self):
        """Clean up resilience manager resources."""
        try:
            # Shutdown health service
            if self.config.enable_health_checks:
                from .health_check import shutdown_health_service
                await shutdown_health_service()
            
            # Shutdown connection pools
            if self.config.enable_connection_pooling:
                from .connection_pool import shutdown_connection_pools
                await shutdown_connection_pools()
            
            logger.info("Resilience manager disposed successfully")
            
        except Exception as e:
            logger.error(f"Error disposing resilience manager: {e}")


def create_default_resilience_config() -> ResilienceConfiguration:
    """Create default resilience configuration for Virtuoso CCXT."""
    return ResilienceConfiguration(
        # Enable all features by default
        enable_circuit_breakers=True,
        enable_retry_policies=True,
        enable_connection_pooling=True,
        enable_health_checks=True,
        
        # Conservative defaults for trading system
        default_failure_threshold=5,
        default_success_threshold=3,
        default_circuit_timeout=60.0,
        
        default_max_retries=3,
        default_base_delay=1.0,
        default_max_delay=30.0,
        
        default_max_connections=50,
        default_max_connections_per_host=20,
        default_connection_timeout=10.0,
        default_request_timeout=30.0,
        
        default_health_check_interval=60.0,
        default_health_check_timeout=10.0
    )


def register_resilience_services(container: DIContainer, config: Optional[ResilienceConfiguration] = None) -> ResilienceManager:
    """
    Convenience function to register resilience services with DI container.
    
    Args:
        container: DI container to register services with
        config: Optional resilience configuration
    
    Returns:
        ResilienceManager instance
    """
    if config is None:
        config = create_default_resilience_config()
    
    manager = ResilienceManager(container, config)
    
    # Register the manager itself as a singleton
    container.register_instance(ResilienceManager, manager, name="resilience_manager")
    
    return manager