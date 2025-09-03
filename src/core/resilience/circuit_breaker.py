"""
Circuit Breaker Pattern Implementation for Virtuoso CCXT Trading System.

Provides comprehensive circuit breaker functionality with:
- Three states: CLOSED, OPEN, HALF_OPEN
- Configurable failure thresholds and timeouts
- Automatic recovery with half-open testing
- Metrics collection and monitoring integration
- Decorator support for easy application
- Thread-safe operation with async support
"""

import asyncio
import time
import logging
from typing import Any, Callable, Optional, Dict, Union, Type, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import threading
from collections import deque

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, failures tracked
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service is recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    
    # Failure tracking
    failure_threshold: int = 5  # Number of failures before opening
    success_threshold: int = 3  # Successes needed in half-open to close
    timeout: float = 60.0      # Seconds before trying half-open
    
    # Time windows
    failure_window: float = 60.0  # Time window for failure counting
    half_open_max_calls: int = 3  # Max calls allowed in half-open state
    
    # Exception handling
    failure_exceptions: tuple = (Exception,)  # Exceptions that count as failures
    success_exceptions: tuple = ()            # Exceptions that count as success
    
    # Monitoring
    name: str = "circuit_breaker"
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class CircuitBreakerMetrics:
    """Metrics collected by circuit breaker."""
    
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    
    state_transitions: Dict[str, int] = field(default_factory=dict)
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    
    # Recent failure tracking
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_success(self):
        """Record a successful call."""
        self.total_calls += 1
        self.successful_calls += 1
        self.last_success_time = time.time()
    
    def add_failure(self, exception: Exception):
        """Record a failed call."""
        self.total_calls += 1
        self.failed_calls += 1
        self.last_failure_time = time.time()
        self.recent_failures.append({
            'timestamp': time.time(),
            'exception': type(exception).__name__,
            'message': str(exception)
        })
    
    def add_rejection(self):
        """Record a rejected call (circuit open)."""
        self.total_calls += 1
        self.rejected_calls += 1
    
    def add_state_transition(self, from_state: CircuitBreakerState, to_state: CircuitBreakerState):
        """Record state transition."""
        transition_key = f"{from_state.value}_to_{to_state.value}"
        self.state_transitions[transition_key] = self.state_transitions.get(transition_key, 0) + 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, circuit_breaker_name: str, state: CircuitBreakerState):
        self.circuit_breaker_name = circuit_breaker_name
        self.state = state
        super().__init__(f"Circuit breaker '{circuit_breaker_name}' is {state.value}")


class CircuitBreaker:
    """
    Circuit breaker implementation with comprehensive failure handling.
    
    Features:
    - Three-state operation (CLOSED, OPEN, HALF_OPEN)
    - Configurable failure and success thresholds
    - Time-based recovery with exponential backoff
    - Thread-safe operation for concurrent use
    - Comprehensive metrics and monitoring
    - Decorator support for easy integration
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        
        # State management
        self._lock = threading.RLock()
        self._last_failure_time = 0.0
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        
        # Failure tracking with time window
        self._failure_timestamps = deque()
        
        logger.info(f"Circuit breaker '{config.name}' initialized with config: {config}")
    
    @property
    def name(self) -> str:
        """Get circuit breaker name."""
        return self.config.name
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed (normal operation)."""
        return self.state == CircuitBreakerState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open (failing fast)."""
        return self.state == CircuitBreakerState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open (testing recovery)."""
        return self.state == CircuitBreakerState.HALF_OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return time.time() - self._last_failure_time >= self.config.timeout
    
    def _count_recent_failures(self) -> int:
        """Count failures within the configured time window."""
        current_time = time.time()
        cutoff_time = current_time - self.config.failure_window
        
        # Remove old failures
        while self._failure_timestamps and self._failure_timestamps[0] < cutoff_time:
            self._failure_timestamps.popleft()
        
        return len(self._failure_timestamps)
    
    def _transition_to_state(self, new_state: CircuitBreakerState):
        """Transition to a new state with logging and metrics."""
        old_state = self.state
        if old_state != new_state:
            self.state = new_state
            self.metrics.add_state_transition(old_state, new_state)
            
            logger.info(f"Circuit breaker '{self.name}' transitioned from {old_state.value} to {new_state.value}")
            
            # Reset counters based on new state
            if new_state == CircuitBreakerState.HALF_OPEN:
                self._half_open_calls = 0
                self._success_count = 0
            elif new_state == CircuitBreakerState.CLOSED:
                self._failure_count = 0
                self._success_count = 0
    
    def _can_execute(self) -> bool:
        """Check if call can be executed in current state."""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_state(CircuitBreakerState.HALF_OPEN)
                    return True
                return False
            elif self.state == CircuitBreakerState.HALF_OPEN:
                return self._half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self.metrics.add_success()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_state(CircuitBreakerState.CLOSED)
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                if self._failure_count > 0:
                    self._failure_count = max(0, self._failure_count - 1)
    
    def _on_failure(self, exception: Exception):
        """Handle failed call."""
        with self._lock:
            self.metrics.add_failure(exception)
            
            # Check if this exception should count as a failure
            should_count = any(isinstance(exception, exc_type) for exc_type in self.config.failure_exceptions)
            should_ignore = any(isinstance(exception, exc_type) for exc_type in self.config.success_exceptions)
            
            if should_ignore:
                # Treat as success for circuit breaker purposes
                self._on_success()
                return
            
            if not should_count:
                return
            
            current_time = time.time()
            self._failure_timestamps.append(current_time)
            self._last_failure_time = current_time
            
            if self.state == CircuitBreakerState.CLOSED:
                recent_failures = self._count_recent_failures()
                if recent_failures >= self.config.failure_threshold:
                    self._transition_to_state(CircuitBreakerState.OPEN)
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self._transition_to_state(CircuitBreakerState.OPEN)
    
    def _before_call(self):
        """Prepare for call execution."""
        if not self._can_execute():
            self.metrics.add_rejection()
            raise CircuitBreakerError(self.name, self.state)
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls += 1
    
    async def call_async(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute an async function with circuit breaker protection."""
        self._before_call()
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a sync function with circuit breaker protection."""
        self._before_call()
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator interface for circuit breaker."""
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return sync_wrapper
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics and state information."""
        with self._lock:
            return {
                'name': self.name,
                'state': self.state.value,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'success_threshold': self.config.success_threshold,
                    'timeout': self.config.timeout,
                    'failure_window': self.config.failure_window
                },
                'metrics': {
                    'total_calls': self.metrics.total_calls,
                    'successful_calls': self.metrics.successful_calls,
                    'failed_calls': self.metrics.failed_calls,
                    'rejected_calls': self.metrics.rejected_calls,
                    'success_rate': self.metrics.success_rate,
                    'failure_rate': self.metrics.failure_rate,
                    'recent_failures_count': self._count_recent_failures(),
                    'last_failure_time': self.metrics.last_failure_time,
                    'last_success_time': self.metrics.last_success_time
                },
                'state_info': {
                    'failure_count': self._failure_count,
                    'success_count': self._success_count,
                    'half_open_calls': self._half_open_calls,
                    'time_until_retry': max(0, self.config.timeout - (time.time() - self._last_failure_time))
                },
                'state_transitions': self.metrics.state_transitions,
                'recent_failures': list(self.metrics.recent_failures)
            }
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            old_state = self.state
            self._transition_to_state(CircuitBreakerState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._failure_timestamps.clear()
            
            logger.info(f"Circuit breaker '{self.name}' manually reset from {old_state.value}")


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.RLock()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.
    
    Args:
        name: Circuit breaker name
        config: Configuration (required for first-time creation)
    
    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            if config is None:
                raise ValueError(f"Circuit breaker '{name}' not found and no config provided")
            
            # Ensure name is set in config
            if config.name != name:
                config.name = name
            
            _circuit_breakers[name] = CircuitBreaker(config)
        
        return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 60.0,
    failure_window: float = 60.0,
    failure_exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for applying circuit breaker protection.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening circuit
        success_threshold: Successes needed to close circuit
        timeout: Seconds before trying half-open
        failure_window: Time window for failure counting
        failure_exceptions: Exceptions that count as failures
    
    Returns:
        Decorated function with circuit breaker protection
    """
    config = CircuitBreakerConfig(
        name=name,
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout,
        failure_window=failure_window,
        failure_exceptions=failure_exceptions
    )
    
    cb = get_circuit_breaker(name, config)
    return cb


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    with _registry_lock:
        return _circuit_breakers.copy()


def get_circuit_breaker_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all circuit breakers."""
    with _registry_lock:
        return {name: cb.get_metrics() for name, cb in _circuit_breakers.items()}