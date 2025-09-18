"""
Infrastructure Resilience Patterns for Virtuoso CCXT Trading System.

This module provides comprehensive resilience patterns including:
- Circuit Breaker with half-open state
- Retry policies with exponential backoff and jitter
- Connection pooling with health monitoring
- Timeout management with configurable thresholds
- Bulkhead pattern for resource isolation
- Graceful degradation for non-critical services
"""

from .circuit_breaker import (
    CircuitBreaker, 
    CircuitBreakerConfig, 
    CircuitBreakerState,
    CircuitBreakerError,
    get_circuit_breaker,
    circuit_breaker,
    get_all_circuit_breakers,
    get_circuit_breaker_metrics
)
from .retry_policy import (
    RetryPolicy, 
    RetryConfig, 
    BackoffStrategy,
    create_exponential_retry,
    create_linear_retry,
    create_constant_retry,
    retry
)
from .connection_pool import (
    ConnectionPoolManager, 
    ConnectionPool, 
    PoolConfig,
    ConnectionBackend,
    ConnectionStatus,
    get_connection_pool_manager,
    get_connection_pool,
    shutdown_connection_pools
)
from .health_check import (
    HealthCheckService, 
    HealthCheck, 
    ServiceStatus,
    HealthCheckResult,
    HealthCheckConfig,
    SimpleHealthCheck,
    ConnectionPoolHealthCheck,
    CircuitBreakerHealthCheck,
    get_health_service,
    shutdown_health_service
)
from .exchange_adapter import (
    ResilientExchangeAdapter,
    ExchangeResilienceConfig,
    create_resilient_exchange,
    create_bybit_resilient_config,
    create_binance_resilient_config
)
from .exchange_wrapper import wrap_exchange_manager
from .cache_adapter import (
    ResilientCacheAdapter,
    CacheResilienceConfig,
    create_resilient_cache,
    create_memcached_resilient_config,
    create_redis_resilient_config
)
from .di_registration import (
    ResilienceManager,
    ResilienceConfiguration,
    ResilienceServiceRegistrar,
    register_resilience_services,
    create_default_resilience_config
)
from .integration_example import (
    ResilientVirtuosoIntegration,
    integrate_with_main_application
)

__all__ = [
    # Circuit Breaker
    'CircuitBreaker',
    'CircuitBreakerConfig', 
    'CircuitBreakerState',
    'CircuitBreakerError',
    'get_circuit_breaker',
    'circuit_breaker',
    'get_all_circuit_breakers',
    'get_circuit_breaker_metrics',
    
    # Retry Policy
    'RetryPolicy',
    'RetryConfig',
    'BackoffStrategy',
    'create_exponential_retry',
    'create_linear_retry', 
    'create_constant_retry',
    'retry',
    
    # Connection Pool
    'ConnectionPoolManager',
    'ConnectionPool',
    'PoolConfig',
    'ConnectionBackend',
    'ConnectionStatus',
    'get_connection_pool_manager',
    'get_connection_pool',
    'shutdown_connection_pools',
    
    # Health Check
    'HealthCheckService',
    'HealthCheck',
    'ServiceStatus',
    'HealthCheckResult',
    'HealthCheckConfig',
    'SimpleHealthCheck',
    'ConnectionPoolHealthCheck',
    'CircuitBreakerHealthCheck',
    'get_health_service',
    'shutdown_health_service',
    
    # Exchange Adapter
    'ResilientExchangeAdapter',
    'ExchangeResilienceConfig',
    'create_resilient_exchange',
    'create_bybit_resilient_config',
    'create_binance_resilient_config',
    'wrap_exchange_manager',
    
    # Cache Adapter
    'ResilientCacheAdapter',
    'CacheResilienceConfig', 
    'create_resilient_cache',
    'create_memcached_resilient_config',
    'create_redis_resilient_config',
    
    # DI Registration
    'ResilienceManager',
    'ResilienceConfiguration',
    'ResilienceServiceRegistrar',
    'register_resilience_services',
    'create_default_resilience_config',
    
    # Integration
    'ResilientVirtuosoIntegration',
    'integrate_with_main_application'
]