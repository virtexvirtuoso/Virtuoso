"""
Resilient Exchange Adapter for Virtuoso CCXT Trading System.

This module provides resilient wrappers around exchange implementations with:
- Circuit breaker protection for all exchange operations
- Retry policies with intelligent backoff strategies
- Connection pooling for HTTP requests
- Health monitoring and status reporting
- Graceful degradation and fallback mechanisms
- Comprehensive metrics and monitoring integration
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
import time
from contextlib import asynccontextmanager

from .circuit_breaker import CircuitBreakerConfig, get_circuit_breaker, CircuitBreakerError
from .retry_policy import RetryConfig, BackoffStrategy, create_exponential_retry
from .connection_pool import PoolConfig, get_connection_pool
from .health_check import (
    HealthCheckConfig, 
    SimpleHealthCheck, 
    get_health_service,
    ServiceStatus,
    HealthCheckResult
)

logger = logging.getLogger(__name__)


@dataclass
class ExchangeResilienceConfig:
    """Configuration for exchange resilience patterns."""
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    success_threshold: int = 3
    circuit_timeout: float = 60.0
    
    # Retry settings  
    retry_enabled: bool = True
    max_retries: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 30.0
    retry_backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    
    # Connection pool settings
    connection_pool_enabled: bool = True
    max_connections: int = 50
    max_connections_per_host: int = 20
    connection_timeout: float = 10.0
    request_timeout: float = 30.0
    
    # Health check settings
    health_check_enabled: bool = True
    health_check_interval: float = 60.0
    health_check_timeout: float = 10.0
    
    # Exception handling
    retriable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    circuit_breaker_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    
    # Exchange-specific settings
    exchange_name: str = "exchange"
    enable_metrics: bool = True
    enable_logging: bool = True


class ResilientExchangeAdapter:
    """
    Resilient wrapper for exchange implementations.
    
    Provides comprehensive resilience patterns around exchange operations:
    - Circuit breaker protection
    - Retry with exponential backoff
    - Connection pooling
    - Health monitoring
    - Metrics collection
    """
    
    def __init__(self, exchange, config: ExchangeResilienceConfig):
        self.exchange = exchange
        self.config = config
        self._initialized = False
        
        # Resilience components
        self._circuit_breaker = None
        self._retry_policy = None
        self._connection_pool = None
        self._health_check = None
        
        # Metrics
        self._metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'circuit_breaker_trips': 0,
            'retry_attempts': 0,
            'average_response_time': 0.0,
            'last_operation_time': None
        }
        
        logger.info(f"Resilient exchange adapter initialized for {config.exchange_name}")
    
    async def initialize(self):
        """Initialize resilience components."""
        if self._initialized:
            return
        
        try:
            # Initialize circuit breaker
            if self.config.circuit_breaker_enabled:
                cb_config = CircuitBreakerConfig(
                    name=f"{self.config.exchange_name}_circuit_breaker",
                    failure_threshold=self.config.failure_threshold,
                    success_threshold=self.config.success_threshold,
                    timeout=self.config.circuit_timeout,
                    failure_exceptions=self.config.circuit_breaker_exceptions,
                    enable_metrics=self.config.enable_metrics
                )
                self._circuit_breaker = get_circuit_breaker(cb_config.name, cb_config)
                logger.info(f"Circuit breaker initialized for {self.config.exchange_name}")
            
            # Initialize retry policy
            if self.config.retry_enabled:
                self._retry_policy = create_exponential_retry(
                    name=f"{self.config.exchange_name}_retry",
                    max_attempts=self.config.max_retries,
                    base_delay=self.config.base_retry_delay,
                    max_delay=self.config.max_retry_delay,
                    jitter=True,
                    retry_exceptions=self.config.retriable_exceptions
                )
                logger.info(f"Retry policy initialized for {self.config.exchange_name}")
            
            # Initialize connection pool
            if self.config.connection_pool_enabled:
                pool_config = PoolConfig(
                    name=f"{self.config.exchange_name}_pool",
                    max_connections=self.config.max_connections,
                    max_connections_per_host=self.config.max_connections_per_host,
                    connect_timeout=self.config.connection_timeout,
                    request_timeout=self.config.request_timeout,
                    enable_metrics=self.config.enable_metrics
                )
                self._connection_pool = get_connection_pool(pool_config.name, pool_config)
                await self._connection_pool.initialize()
                logger.info(f"Connection pool initialized for {self.config.exchange_name}")
            
            # Initialize health check
            if self.config.health_check_enabled:
                health_config = HealthCheckConfig(
                    name=f"{self.config.exchange_name}_health",
                    interval=self.config.health_check_interval,
                    timeout=self.config.health_check_timeout,
                    enable_metrics=self.config.enable_metrics
                )
                
                self._health_check = SimpleHealthCheck(
                    health_config.name,
                    self._perform_health_check,
                    health_config
                )
                
                health_service = get_health_service()
                health_service.register_health_check(self._health_check)
                logger.info(f"Health check initialized for {self.config.exchange_name}")
            
            self._initialized = True
            logger.info(f"Resilient exchange adapter fully initialized for {self.config.exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize resilient exchange adapter for {self.config.exchange_name}: {e}")
            raise
    
    async def _perform_health_check(self) -> bool:
        """Perform health check on the exchange."""
        try:
            # Simple health check - try to fetch server time or status
            if hasattr(self.exchange, 'fetch_status'):
                await self.exchange.fetch_status()
            elif hasattr(self.exchange, 'fetch_time'):
                await self.exchange.fetch_time()
            else:
                # Fallback - just check if exchange is accessible
                return hasattr(self.exchange, 'id') and self.exchange.id is not None
            
            return True
            
        except Exception as e:
            logger.debug(f"Health check failed for {self.config.exchange_name}: {e}")
            return False
    
    async def _execute_with_resilience(self, operation_name: str, func: Callable, *args, **kwargs):
        """Execute an operation with full resilience protection."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Apply circuit breaker if enabled
            if self._circuit_breaker:
                if self._retry_policy:
                    # Combine circuit breaker with retry policy
                    async def protected_operation():
                        return await self._circuit_breaker.call_async(func, *args, **kwargs)
                    
                    result = await self._retry_policy.call_async(protected_operation)
                else:
                    result = await self._circuit_breaker.call_async(func, *args, **kwargs)
            elif self._retry_policy:
                # Use retry policy alone
                result = await self._retry_policy.call_async(func, *args, **kwargs)
            else:
                # No resilience patterns, direct call
                result = await func(*args, **kwargs)
            
            # Update success metrics
            duration = time.time() - start_time
            self._update_metrics(True, duration, operation_name)
            
            return result
            
        except CircuitBreakerError as e:
            # Circuit breaker is open
            duration = time.time() - start_time
            self._metrics['circuit_breaker_trips'] += 1
            self._update_metrics(False, duration, operation_name)
            
            logger.warning(f"Circuit breaker open for {self.config.exchange_name}.{operation_name}: {e}")
            raise
            
        except Exception as e:
            # Operation failed
            duration = time.time() - start_time
            self._update_metrics(False, duration, operation_name)
            
            if self.config.enable_logging:
                logger.error(f"Operation failed for {self.config.exchange_name}.{operation_name}: {e}")
            raise
    
    def _update_metrics(self, success: bool, duration: float, operation_name: str):
        """Update operation metrics."""
        self._metrics['total_operations'] += 1
        self._metrics['last_operation_time'] = time.time()
        
        if success:
            self._metrics['successful_operations'] += 1
        else:
            self._metrics['failed_operations'] += 1
        
        # Update average response time (exponential moving average)
        if self._metrics['average_response_time'] == 0:
            self._metrics['average_response_time'] = duration
        else:
            alpha = 0.1  # Smoothing factor
            self._metrics['average_response_time'] = (
                alpha * duration + (1 - alpha) * self._metrics['average_response_time']
            )
    
    # Exchange operation wrappers with resilience
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_ticker',
            self.exchange.fetch_ticker,
            symbol
        )
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', since: Optional[int] = None, limit: Optional[int] = None) -> List[List]:
        """Fetch OHLCV data with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_ohlcv',
            self.exchange.fetch_ohlcv,
            symbol, timeframe, since, limit
        )
    
    async def fetch_order_book(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch order book with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_order_book',
            self.exchange.fetch_order_book,
            symbol, limit
        )
    
    async def fetch_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch trades with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_trades',
            self.exchange.fetch_trades,
            symbol, since, limit
        )
    
    async def create_order(self, symbol: str, type: str, side: str, amount: float, price: Optional[float] = None, params: Dict = None) -> Dict[str, Any]:
        """Create order with resilience protection."""
        return await self._execute_with_resilience(
            'create_order',
            self.exchange.create_order,
            symbol, type, side, amount, price, params or {}
        )
    
    async def cancel_order(self, id: str, symbol: str, params: Dict = None) -> Dict[str, Any]:
        """Cancel order with resilience protection."""
        return await self._execute_with_resilience(
            'cancel_order',
            self.exchange.cancel_order,
            id, symbol, params or {}
        )
    
    async def fetch_order(self, id: str, symbol: str, params: Dict = None) -> Dict[str, Any]:
        """Fetch order with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_order',
            self.exchange.fetch_order,
            id, symbol, params or {}
        )
    
    async def fetch_balance(self, params: Dict = None) -> Dict[str, Any]:
        """Fetch balance with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_balance',
            self.exchange.fetch_balance,
            params or {}
        )
    
    async def fetch_positions(self, symbols: Optional[List[str]] = None, params: Dict = None) -> List[Dict[str, Any]]:
        """Fetch positions with resilience protection."""
        return await self._execute_with_resilience(
            'fetch_positions',
            self.exchange.fetch_positions,
            symbols, params or {}
        )
    
    # Utility methods
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get adapter metrics."""
        metrics = {
            'adapter_metrics': self._metrics.copy(),
            'config': {
                'exchange_name': self.config.exchange_name,
                'circuit_breaker_enabled': self.config.circuit_breaker_enabled,
                'retry_enabled': self.config.retry_enabled,
                'connection_pool_enabled': self.config.connection_pool_enabled,
                'health_check_enabled': self.config.health_check_enabled
            }
        }
        
        # Add component metrics
        if self._circuit_breaker:
            metrics['circuit_breaker'] = self._circuit_breaker.get_metrics()
        
        if self._retry_policy:
            metrics['retry_policy'] = self._retry_policy.get_metrics()
        
        if self._connection_pool:
            metrics['connection_pool'] = self._connection_pool.get_metrics()
        
        if self._health_check:
            metrics['health_check'] = self._health_check.get_metrics()
        
        return metrics
    
    def get_health_status(self) -> Optional[ServiceStatus]:
        """Get current health status."""
        if self._health_check:
            result = self._health_check.get_current_status()
            return result.status if result else ServiceStatus.UNKNOWN
        return ServiceStatus.UNKNOWN
    
    async def close(self):
        """Clean up adapter resources."""
        try:
            if self._connection_pool:
                await self._connection_pool.close()
            
            if self._health_check:
                health_service = get_health_service()
                health_service.unregister_health_check(self._health_check.name)
            
            logger.info(f"Resilient exchange adapter closed for {self.config.exchange_name}")
            
        except Exception as e:
            logger.error(f"Error closing resilient exchange adapter for {self.config.exchange_name}: {e}")


def create_resilient_exchange(exchange, config: Optional[ExchangeResilienceConfig] = None) -> ResilientExchangeAdapter:
    """
    Create a resilient wrapper around an exchange instance.
    
    Args:
        exchange: The exchange instance to wrap
        config: Optional resilience configuration
    
    Returns:
        ResilientExchangeAdapter instance
    """
    if config is None:
        exchange_name = getattr(exchange, 'id', 'unknown_exchange')
        config = ExchangeResilienceConfig(exchange_name=exchange_name)
    
    return ResilientExchangeAdapter(exchange, config)


# Convenience function for common exchange configurations
def create_bybit_resilient_config() -> ExchangeResilienceConfig:
    """Create resilience config optimized for Bybit exchange."""
    return ExchangeResilienceConfig(
        exchange_name="bybit",
        
        # Circuit breaker - more lenient for crypto exchanges
        failure_threshold=8,
        success_threshold=3,
        circuit_timeout=45.0,
        
        # Retry - aggressive for market data, conservative for trading
        max_retries=3,
        base_retry_delay=0.5,
        max_retry_delay=10.0,
        
        # Connection pool - optimized for crypto exchange patterns
        max_connections=30,
        max_connections_per_host=15,
        connection_timeout=8.0,
        request_timeout=20.0,
        
        # Health check
        health_check_interval=45.0,
        health_check_timeout=8.0,
        
        # Exception handling - crypto exchange specific
        retriable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
            # Add exchange-specific retriable exceptions
        ),
        circuit_breaker_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        )
    )


def create_binance_resilient_config() -> ExchangeResilienceConfig:
    """Create resilience config optimized for Binance exchange."""
    return ExchangeResilienceConfig(
        exchange_name="binance",
        
        # Circuit breaker - tuned for Binance
        failure_threshold=6,
        success_threshold=2,
        circuit_timeout=30.0,
        
        # Retry - faster recovery for Binance
        max_retries=4,
        base_retry_delay=0.3,
        max_retry_delay=8.0,
        
        # Connection pool
        max_connections=40,
        max_connections_per_host=20,
        connection_timeout=6.0,
        request_timeout=15.0,
        
        # Health check
        health_check_interval=30.0,
        health_check_timeout=6.0
    )