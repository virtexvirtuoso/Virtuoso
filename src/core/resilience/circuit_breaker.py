"""
Production-ready Circuit Breaker Implementation for Trading System

Implements circuit breaker pattern to prevent cascading failures in external API calls.
Critical for system stability when exchange APIs fail or become unstable.
"""

import time
import logging
import asyncio
from enum import Enum
from typing import Callable, Any, Dict, Optional, Union
from dataclasses import dataclass
from threading import Lock
import functools

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: int = 60          # Seconds before attempting recovery
    expected_exception: type = Exception  # Exception type to monitor
    success_threshold: int = 3          # Successes needed in half-open to close
    timeout: float = 30.0               # Request timeout in seconds


class CircuitBreakerError(Exception):
    """Raised when circuit breaker blocks a request"""
    pass


class CircuitBreaker:
    """
    Production-ready circuit breaker for external service calls.
    
    Prevents cascading failures by monitoring failures and opening
    the circuit when failure threshold is exceeded.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        
        # Thread safety
        self._lock = Lock()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'circuit_open_count': 0,
            'timeout_count': 0
        }
        
        logger.info(f"Circuit breaker '{name}' initialized with threshold {config.failure_threshold}")
    
    def _can_execute(self) -> bool:
        """Check if request can be executed based on circuit state"""
        with self._lock:
            current_time = time.time()
            
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if current_time - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    return True
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                return True
            
            return False
    
    def _record_success(self):
        """Record successful execution"""
        with self._lock:
            self.stats['successful_requests'] += 1
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker '{self.name}' closed after recovery")
            
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _record_failure(self, exception: Exception):
        """Record failed execution"""
        with self._lock:
            self.stats['failed_requests'] += 1
            
            # Only count expected exceptions as failures
            if isinstance(exception, self.config.expected_exception):
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == CircuitState.CLOSED:
                    if self.failure_count >= self.config.failure_threshold:
                        self.state = CircuitState.OPEN
                        self.stats['circuit_open_count'] += 1
                        logger.error(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")
                
                elif self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker '{self.name}' reopened during recovery attempt")
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        self.stats['total_requests'] += 1
        
        if not self._can_execute():
            logger.warning(f"Circuit breaker '{self.name}' blocking request - circuit is OPEN")
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            self._record_success()
            return result
            
        except asyncio.TimeoutError as e:
            self.stats['timeout_count'] += 1
            self._record_failure(e)
            logger.error(f"Circuit breaker '{self.name}' timeout after {self.config.timeout}s")
            raise
        
        except Exception as e:
            self._record_failure(e)
            logger.error(f"Circuit breaker '{self.name}' caught exception: {e}")
            raise
    
    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with circuit breaker protection"""
        self.stats['total_requests'] += 1
        
        if not self._can_execute():
            logger.warning(f"Circuit breaker '{self.name}' blocking request - circuit is OPEN")
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure(e)
            logger.error(f"Circuit breaker '{self.name}' caught exception: {e}")
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state and statistics"""
        with self._lock:
            total_requests = self.stats['total_requests']
            success_rate = (
                (self.stats['successful_requests'] / total_requests * 100) 
                if total_requests > 0 else 0.0
            )
            
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': self.last_failure_time,
                'stats': self.stats.copy(),
                'success_rate': round(success_rate, 2),
                'is_healthy': self.state == CircuitState.CLOSED,
                'next_retry_time': (
                    self.last_failure_time + self.config.recovery_timeout
                    if self.state == CircuitState.OPEN else None
                )
            }
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerManager:
    """
    Global manager for all circuit breakers in the system.
    Provides centralized monitoring and control.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()
    
    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing circuit breaker or create new one"""
        with self._lock:
            if name not in self._breakers:
                if config is None:
                    config = CircuitBreakerConfig()
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers"""
        with self._lock:
            return {name: breaker.get_state() for name, breaker in self._breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")
    
    def get_healthy_breakers(self) -> Dict[str, CircuitBreaker]:
        """Get only healthy (closed) circuit breakers"""
        with self._lock:
            return {
                name: breaker for name, breaker in self._breakers.items()
                if breaker.state == CircuitState.CLOSED
            }
    
    def get_unhealthy_breakers(self) -> Dict[str, CircuitBreaker]:
        """Get unhealthy (open/half-open) circuit breakers"""
        with self._lock:
            return {
                name: breaker for name, breaker in self._breakers.items()
                if breaker.state != CircuitState.CLOSED
            }


# Global circuit breaker manager
_circuit_manager: Optional[CircuitBreakerManager] = None


def get_circuit_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager instance"""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to add circuit breaker protection to functions.
    
    Usage:
        @circuit_breaker('exchange_api', CircuitBreakerConfig(failure_threshold=3))
        async def fetch_ticker(symbol):
            # API call here
            pass
    """
    def decorator(func: Callable) -> Callable:
        manager = get_circuit_manager()
        breaker = manager.get_or_create(name, config)
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call_sync(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


# Pre-configured circuit breakers for common use cases
EXCHANGE_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception,
    success_threshold=3,
    timeout=30.0
)

REDIS_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception,
    success_threshold=2,
    timeout=5.0
)

DATABASE_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=45,
    expected_exception=Exception,
    success_threshold=2,
    timeout=10.0
)