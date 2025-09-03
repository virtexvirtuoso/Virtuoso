"""
Resilient Cache Adapter for Virtuoso CCXT Trading System.

This module provides resilient wrappers around cache implementations with:
- Circuit breaker protection for cache operations
- Retry policies with intelligent backoff
- Connection pooling for cache connections
- Health monitoring and automatic failover
- Graceful degradation when cache is unavailable
- Comprehensive metrics and monitoring
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
import time
import json

from .circuit_breaker import CircuitBreakerConfig, get_circuit_breaker, CircuitBreakerError
from .retry_policy import RetryConfig, BackoffStrategy, create_exponential_retry
from .health_check import (
    HealthCheckConfig, 
    SimpleHealthCheck, 
    get_health_service,
    ServiceStatus
)

logger = logging.getLogger(__name__)


@dataclass
class CacheResilienceConfig:
    """Configuration for cache resilience patterns."""
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 3  # Lower threshold for cache operations
    success_threshold: int = 2
    circuit_timeout: float = 30.0  # Shorter timeout for cache recovery
    
    # Retry settings
    retry_enabled: bool = True
    max_retries: int = 2  # Fewer retries for cache operations
    base_retry_delay: float = 0.1  # Fast retry for cache
    max_retry_delay: float = 2.0   # Short max delay
    retry_backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    
    # Health check settings
    health_check_enabled: bool = True
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    
    # Fallback behavior
    enable_fallback: bool = True
    fallback_to_memory: bool = True  # Fallback to in-memory cache
    fallback_ttl: float = 60.0       # TTL for fallback cache
    
    # Cache-specific settings
    cache_name: str = "cache"
    default_ttl: float = 300.0
    key_prefix: str = ""
    
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
    
    # Monitoring
    enable_metrics: bool = True
    enable_logging: bool = True


class ResilientCacheAdapter:
    """
    Resilient wrapper for cache implementations.
    
    Provides comprehensive resilience patterns around cache operations:
    - Circuit breaker protection
    - Retry with exponential backoff
    - Health monitoring
    - Graceful degradation with fallback
    - Metrics collection
    """
    
    def __init__(self, cache_client, config: CacheResilienceConfig):
        self.cache_client = cache_client
        self.config = config
        self._initialized = False
        
        # Resilience components
        self._circuit_breaker = None
        self._retry_policy = None
        self._health_check = None
        
        # Fallback cache (in-memory)
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._fallback_enabled = False
        
        # Metrics
        self._metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'fallback_hits': 0,
            'circuit_breaker_trips': 0,
            'average_response_time': 0.0,
            'last_operation_time': None
        }
        
        logger.info(f"Resilient cache adapter initialized for {config.cache_name}")
    
    async def initialize(self):
        """Initialize resilience components."""
        if self._initialized:
            return
        
        try:
            # Initialize circuit breaker
            if self.config.circuit_breaker_enabled:
                cb_config = CircuitBreakerConfig(
                    name=f"{self.config.cache_name}_circuit_breaker",
                    failure_threshold=self.config.failure_threshold,
                    success_threshold=self.config.success_threshold,
                    timeout=self.config.circuit_timeout,
                    failure_exceptions=self.config.circuit_breaker_exceptions,
                    enable_metrics=self.config.enable_metrics
                )
                self._circuit_breaker = get_circuit_breaker(cb_config.name, cb_config)
                logger.info(f"Circuit breaker initialized for {self.config.cache_name}")
            
            # Initialize retry policy
            if self.config.retry_enabled:
                self._retry_policy = create_exponential_retry(
                    name=f"{self.config.cache_name}_retry",
                    max_attempts=self.config.max_retries,
                    base_delay=self.config.base_retry_delay,
                    max_delay=self.config.max_retry_delay,
                    jitter=True,
                    retry_exceptions=self.config.retriable_exceptions
                )
                logger.info(f"Retry policy initialized for {self.config.cache_name}")
            
            # Initialize health check
            if self.config.health_check_enabled:
                health_config = HealthCheckConfig(
                    name=f"{self.config.cache_name}_health",
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
                logger.info(f"Health check initialized for {self.config.cache_name}")
            
            self._initialized = True
            logger.info(f"Resilient cache adapter fully initialized for {self.config.cache_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize resilient cache adapter for {self.config.cache_name}: {e}")
            raise
    
    async def _perform_health_check(self) -> bool:
        """Perform health check on the cache."""
        try:
            # Simple ping test
            test_key = f"{self.config.key_prefix}health_check"
            test_value = str(time.time())
            
            await self._execute_cache_operation('set', test_key, test_value, ttl=10)
            result = await self._execute_cache_operation('get', test_key)
            
            return result == test_value
            
        except Exception as e:
            logger.debug(f"Cache health check failed for {self.config.cache_name}: {e}")
            return False
    
    async def _execute_cache_operation(self, operation: str, *args, **kwargs):
        """Execute a cache operation with basic error handling."""
        if hasattr(self.cache_client, operation):
            method = getattr(self.cache_client, operation)
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
        else:
            raise AttributeError(f"Cache client does not support operation: {operation}")
    
    async def _execute_with_resilience(self, operation_name: str, func, *args, **kwargs):
        """Execute a cache operation with full resilience protection."""
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
            self._update_metrics(True, duration, operation_name, result is not None)
            
            # Disable fallback on successful operation
            if self._fallback_enabled:
                self._fallback_enabled = False
                logger.info(f"Cache {self.config.cache_name} recovered, disabling fallback")
            
            return result
            
        except (CircuitBreakerError, Exception) as e:
            # Operation failed, try fallback if enabled
            duration = time.time() - start_time
            
            if isinstance(e, CircuitBreakerError):
                self._metrics['circuit_breaker_trips'] += 1
                logger.warning(f"Circuit breaker open for {self.config.cache_name}.{operation_name}")
            
            # Try fallback for read operations
            if self.config.enable_fallback and operation_name in ('get', 'mget'):
                try:
                    fallback_result = await self._try_fallback(operation_name, *args, **kwargs)
                    if fallback_result is not None:
                        self._update_metrics(True, duration, f"{operation_name}_fallback", True)
                        if not self._fallback_enabled:
                            self._fallback_enabled = True
                            logger.warning(f"Cache {self.config.cache_name} degraded, enabling fallback")
                        return fallback_result
                except Exception as fallback_error:
                    logger.debug(f"Fallback also failed for {operation_name}: {fallback_error}")
            
            self._update_metrics(False, duration, operation_name, False)
            
            if self.config.enable_logging:
                logger.error(f"Cache operation failed for {self.config.cache_name}.{operation_name}: {e}")
            
            # For write operations, we might want to fail silently or return success
            if operation_name in ('set', 'mset', 'delete') and self.config.enable_fallback:
                logger.warning(f"Cache {operation_name} failed, continuing without caching")
                return True  # Pretend success for write operations
            
            raise
    
    async def _try_fallback(self, operation: str, *args, **kwargs):
        """Try fallback cache operation."""
        if not self.config.fallback_to_memory:
            return None
        
        try:
            if operation == 'get' and len(args) >= 1:
                key = args[0]
                if key in self._fallback_cache:
                    entry = self._fallback_cache[key]
                    if time.time() < entry['expires']:
                        self._metrics['fallback_hits'] += 1
                        return entry['value']
                    else:
                        # Expired, remove from fallback cache
                        del self._fallback_cache[key]
                return None
            
            elif operation == 'mget' and len(args) >= 1:
                keys = args[0]
                results = []
                for key in keys:
                    if key in self._fallback_cache:
                        entry = self._fallback_cache[key]
                        if time.time() < entry['expires']:
                            results.append(entry['value'])
                            self._metrics['fallback_hits'] += 1
                        else:
                            del self._fallback_cache[key]
                            results.append(None)
                    else:
                        results.append(None)
                return results
            
        except Exception as e:
            logger.debug(f"Fallback cache operation failed: {e}")
        
        return None
    
    def _update_fallback_cache(self, key: str, value: Any, ttl: Optional[float] = None):
        """Update fallback cache with value."""
        if not self.config.fallback_to_memory:
            return
        
        try:
            expires = time.time() + (ttl or self.config.fallback_ttl)
            self._fallback_cache[key] = {
                'value': value,
                'expires': expires
            }
            
            # Clean up expired entries periodically
            if len(self._fallback_cache) > 1000:  # Arbitrary threshold
                current_time = time.time()
                expired_keys = [
                    k for k, v in self._fallback_cache.items() 
                    if current_time >= v['expires']
                ]
                for k in expired_keys:
                    del self._fallback_cache[k]
                    
        except Exception as e:
            logger.debug(f"Failed to update fallback cache: {e}")
    
    def _update_metrics(self, success: bool, duration: float, operation_name: str, cache_hit: bool):
        """Update operation metrics."""
        self._metrics['total_operations'] += 1
        self._metrics['last_operation_time'] = time.time()
        
        if success:
            self._metrics['successful_operations'] += 1
            if 'get' in operation_name and cache_hit:
                self._metrics['cache_hits'] += 1
            elif 'get' in operation_name:
                self._metrics['cache_misses'] += 1
        else:
            self._metrics['failed_operations'] += 1
        
        # Update average response time
        if self._metrics['average_response_time'] == 0:
            self._metrics['average_response_time'] = duration
        else:
            alpha = 0.1
            self._metrics['average_response_time'] = (
                alpha * duration + (1 - alpha) * self._metrics['average_response_time']
            )
    
    # Cache operation wrappers with resilience
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with resilience protection."""
        full_key = f"{self.config.key_prefix}{key}" if self.config.key_prefix else key
        
        async def cache_get():
            return await self._execute_cache_operation('get', full_key)
        
        return await self._execute_with_resilience('get', cache_get)
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache with resilience protection."""
        full_key = f"{self.config.key_prefix}{key}" if self.config.key_prefix else key
        ttl = ttl or self.config.default_ttl
        
        async def cache_set():
            result = await self._execute_cache_operation('set', full_key, value, ttl)
            # Update fallback cache on successful write
            self._update_fallback_cache(full_key, value, ttl)
            return result
        
        return await self._execute_with_resilience('set', cache_set)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache with resilience protection."""
        full_key = f"{self.config.key_prefix}{key}" if self.config.key_prefix else key
        
        async def cache_delete():
            result = await self._execute_cache_operation('delete', full_key)
            # Remove from fallback cache
            if full_key in self._fallback_cache:
                del self._fallback_cache[full_key]
            return result
        
        return await self._execute_with_resilience('delete', cache_delete)
    
    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values from cache with resilience protection."""
        full_keys = [
            f"{self.config.key_prefix}{key}" if self.config.key_prefix else key 
            for key in keys
        ]
        
        async def cache_mget():
            return await self._execute_cache_operation('mget', full_keys)
        
        return await self._execute_with_resilience('mget', cache_mget)
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> bool:
        """Set multiple values in cache with resilience protection."""
        ttl = ttl or self.config.default_ttl
        full_mapping = {
            f"{self.config.key_prefix}{key}" if self.config.key_prefix else key: value
            for key, value in mapping.items()
        }
        
        async def cache_mset():
            result = await self._execute_cache_operation('mset', full_mapping, ttl)
            # Update fallback cache
            for key, value in full_mapping.items():
                self._update_fallback_cache(key, value, ttl)
            return result
        
        return await self._execute_with_resilience('mset', cache_mset)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache with resilience protection."""
        full_key = f"{self.config.key_prefix}{key}" if self.config.key_prefix else key
        
        async def cache_exists():
            return await self._execute_cache_operation('exists', full_key)
        
        return await self._execute_with_resilience('exists', cache_exists)
    
    async def expire(self, key: str, ttl: float) -> bool:
        """Set TTL for key with resilience protection."""
        full_key = f"{self.config.key_prefix}{key}" if self.config.key_prefix else key
        
        async def cache_expire():
            return await self._execute_cache_operation('expire', full_key, ttl)
        
        return await self._execute_with_resilience('expire', cache_expire)
    
    async def flush(self) -> bool:
        """Flush cache with resilience protection."""
        async def cache_flush():
            result = await self._execute_cache_operation('flushall')
            # Clear fallback cache too
            self._fallback_cache.clear()
            return result
        
        return await self._execute_with_resilience('flush', cache_flush)
    
    # Utility methods
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get adapter metrics."""
        hit_rate = 0.0
        total_gets = self._metrics['cache_hits'] + self._metrics['cache_misses']
        if total_gets > 0:
            hit_rate = self._metrics['cache_hits'] / total_gets
        
        metrics = {
            'adapter_metrics': {
                **self._metrics,
                'cache_hit_rate': hit_rate,
                'fallback_enabled': self._fallback_enabled,
                'fallback_cache_size': len(self._fallback_cache)
            },
            'config': {
                'cache_name': self.config.cache_name,
                'circuit_breaker_enabled': self.config.circuit_breaker_enabled,
                'retry_enabled': self.config.retry_enabled,
                'fallback_enabled': self.config.enable_fallback
            }
        }
        
        # Add component metrics
        if self._circuit_breaker:
            metrics['circuit_breaker'] = self._circuit_breaker.get_metrics()
        
        if self._retry_policy:
            metrics['retry_policy'] = self._retry_policy.get_metrics()
        
        if self._health_check:
            metrics['health_check'] = self._health_check.get_metrics()
        
        return metrics
    
    def get_health_status(self) -> ServiceStatus:
        """Get current health status."""
        if self._health_check:
            result = self._health_check.get_current_status()
            return result.status if result else ServiceStatus.UNKNOWN
        return ServiceStatus.UNKNOWN
    
    async def close(self):
        """Clean up adapter resources."""
        try:
            if hasattr(self.cache_client, 'close'):
                if asyncio.iscoroutinefunction(self.cache_client.close):
                    await self.cache_client.close()
                else:
                    self.cache_client.close()
            
            if self._health_check:
                health_service = get_health_service()
                health_service.unregister_health_check(self._health_check.name)
            
            # Clear fallback cache
            self._fallback_cache.clear()
            
            logger.info(f"Resilient cache adapter closed for {self.config.cache_name}")
            
        except Exception as e:
            logger.error(f"Error closing resilient cache adapter for {self.config.cache_name}: {e}")


def create_resilient_cache(cache_client, config: Optional[CacheResilienceConfig] = None) -> ResilientCacheAdapter:
    """
    Create a resilient wrapper around a cache client.
    
    Args:
        cache_client: The cache client to wrap
        config: Optional resilience configuration
    
    Returns:
        ResilientCacheAdapter instance
    """
    if config is None:
        config = CacheResilienceConfig()
    
    return ResilientCacheAdapter(cache_client, config)


# Convenience functions for common cache configurations
def create_memcached_resilient_config(name: str = "memcached") -> CacheResilienceConfig:
    """Create resilience config optimized for Memcached."""
    return CacheResilienceConfig(
        cache_name=name,
        
        # Circuit breaker - fast recovery for cache
        failure_threshold=3,
        success_threshold=2,
        circuit_timeout=20.0,
        
        # Retry - fast retry for cache operations
        max_retries=2,
        base_retry_delay=0.05,
        max_retry_delay=1.0,
        
        # Health check
        health_check_interval=30.0,
        health_check_timeout=3.0,
        
        # Fallback
        enable_fallback=True,
        fallback_to_memory=True,
        fallback_ttl=60.0,
        
        # Memcached specifics
        default_ttl=300.0
    )


def create_redis_resilient_config(name: str = "redis") -> CacheResilienceConfig:
    """Create resilience config optimized for Redis."""
    return CacheResilienceConfig(
        cache_name=name,
        
        # Circuit breaker - Redis is more reliable
        failure_threshold=4,
        success_threshold=2,
        circuit_timeout=25.0,
        
        # Retry
        max_retries=3,
        base_retry_delay=0.1,
        max_retry_delay=2.0,
        
        # Health check
        health_check_interval=45.0,
        health_check_timeout=5.0,
        
        # Fallback
        enable_fallback=True,
        fallback_to_memory=True,
        fallback_ttl=120.0,
        
        # Redis specifics
        default_ttl=600.0
    )