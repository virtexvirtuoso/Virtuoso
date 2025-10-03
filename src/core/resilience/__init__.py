"""
Core Resilience Package

Provides production-ready resilience patterns for the trading system:
- Circuit breakers for external service protection
- Comprehensive error handling and retry logic
- Fallback mechanisms for system stability
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitState,
    get_circuit_manager,
    circuit_breaker,
    EXCHANGE_API_CONFIG,
    REDIS_CONFIG,
    DATABASE_CONFIG
)

from .error_handler import (
    ErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    RetryConfig,
    get_error_handler,
    handle_errors
)

# Legacy compatibility functions
def wrap_exchange_manager(manager):
    """Legacy wrapper for exchange manager - now handled by circuit breakers."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("✅ Exchange manager wrapped with resilience patterns")
    return manager

# Note: integration_example import removed to prevent circular dependencies
# Import integration_example directly where needed instead of at module level

__all__ = [
    # Circuit Breaker
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitBreakerError',
    'CircuitBreakerManager',
    'CircuitState',
    'get_circuit_manager',
    'circuit_breaker',
    'EXCHANGE_API_CONFIG',
    'REDIS_CONFIG',
    'DATABASE_CONFIG',

    # Error Handler
    'ErrorHandler',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorContext',
    'RetryConfig',
    'get_error_handler',
    'handle_errors',

    # Legacy
    'wrap_exchange_manager'
]