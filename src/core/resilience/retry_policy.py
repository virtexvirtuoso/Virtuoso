"""
Retry Policy Implementation with Exponential Backoff and Jitter.

Provides sophisticated retry mechanisms including:
- Multiple backoff strategies (exponential, linear, constant)
- Jitter to avoid thundering herd problems
- Configurable retry conditions based on exceptions
- Integration with circuit breaker patterns
- Comprehensive retry metrics and monitoring
- Support for both sync and async operations
"""

import asyncio
import random
import time
import logging
from typing import Any, Callable, Optional, Union, Type, Awaitable, List
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import math

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Available backoff strategies for retries."""
    CONSTANT = "constant"            # Fixed delay between retries
    LINEAR = "linear"               # Linearly increasing delay
    EXPONENTIAL = "exponential"     # Exponentially increasing delay
    EXPONENTIAL_JITTER = "exponential_jitter"  # Exponential with jitter


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    # Basic retry settings
    max_attempts: int = 3           # Maximum number of retry attempts
    base_delay: float = 1.0         # Base delay in seconds
    max_delay: float = 60.0         # Maximum delay between retries
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    
    # Backoff multipliers
    exponential_base: float = 2.0   # Base for exponential backoff
    linear_increment: float = 1.0   # Increment for linear backoff
    jitter_factor: float = 0.1      # Jitter factor (0.0 to 1.0)
    
    # Exception handling
    retry_exceptions: tuple = (Exception,)      # Exceptions to retry on
    stop_exceptions: tuple = ()                 # Exceptions to never retry
    retry_condition: Optional[Callable[[Exception], bool]] = None  # Custom retry condition
    
    # Monitoring
    name: str = "retry_policy"
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not (0.0 <= self.jitter_factor <= 1.0):
            raise ValueError("jitter_factor must be between 0.0 and 1.0")


@dataclass
class RetryMetrics:
    """Metrics collected by retry policy."""
    
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_retries: int = 0
    
    # Per-attempt metrics
    attempts_distribution: dict = field(default_factory=dict)  # attempt_number -> count
    exception_counts: dict = field(default_factory=dict)       # exception_type -> count
    
    # Timing metrics
    total_retry_time: float = 0.0
    max_retry_time: float = 0.0
    min_retry_time: float = float('inf')
    
    def add_operation(self, attempts: int, total_time: float, success: bool, exceptions: List[Exception]):
        """Record a completed operation."""
        self.total_operations += 1
        
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        
        # Track attempts
        if attempts > 1:
            retries = attempts - 1
            self.total_retries += retries
            
            # Update timing metrics
            if total_time > 0:
                self.total_retry_time += total_time
                self.max_retry_time = max(self.max_retry_time, total_time)
                if total_time < self.min_retry_time:
                    self.min_retry_time = total_time
        
        # Track attempt distribution
        self.attempts_distribution[attempts] = self.attempts_distribution.get(attempts, 0) + 1
        
        # Track exception types
        for exc in exceptions:
            exc_type = type(exc).__name__
            self.exception_counts[exc_type] = self.exception_counts.get(exc_type, 0) + 1
    
    @property
    def success_rate(self) -> float:
        """Calculate operation success rate."""
        if self.total_operations == 0:
            return 1.0
        return self.successful_operations / self.total_operations
    
    @property
    def average_attempts(self) -> float:
        """Calculate average attempts per operation."""
        if self.total_operations == 0:
            return 1.0
        return (self.total_operations + self.total_retries) / self.total_operations
    
    @property
    def average_retry_time(self) -> float:
        """Calculate average retry time."""
        retry_operations = self.total_operations - self.attempts_distribution.get(1, 0)
        if retry_operations == 0:
            return 0.0
        return self.total_retry_time / retry_operations


class RetryPolicy:
    """
    Comprehensive retry policy implementation.
    
    Features:
    - Multiple backoff strategies with jitter
    - Configurable retry conditions
    - Comprehensive metrics collection
    - Support for both sync and async operations
    - Integration with circuit breaker patterns
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.metrics = RetryMetrics()
        
        logger.info(f"Retry policy '{config.name}' initialized with config: {config}")
    
    @property
    def name(self) -> str:
        """Get retry policy name."""
        return self.config.name
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a specific attempt number."""
        if attempt <= 1:
            return 0.0
        
        retry_number = attempt - 1  # First retry is attempt 2
        
        if self.config.backoff_strategy == BackoffStrategy.CONSTANT:
            delay = self.config.base_delay
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay + (retry_number - 1) * self.config.linear_increment
        elif self.config.backoff_strategy in (BackoffStrategy.EXPONENTIAL, BackoffStrategy.EXPONENTIAL_JITTER):
            delay = self.config.base_delay * (self.config.exponential_base ** (retry_number - 1))
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if configured
        if self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER and self.config.jitter_factor > 0:
            jitter = delay * self.config.jitter_factor
            delay += random.uniform(-jitter, jitter)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if operation should be retried."""
        # Check if we've exceeded max attempts
        if attempt >= self.config.max_attempts:
            return False
        
        # Check stop exceptions (never retry these)
        if any(isinstance(exception, exc_type) for exc_type in self.config.stop_exceptions):
            return False
        
        # Check custom retry condition
        if self.config.retry_condition is not None:
            return self.config.retry_condition(exception)
        
        # Check retry exceptions
        return any(isinstance(exception, exc_type) for exc_type in self.config.retry_exceptions)
    
    async def call_async(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute an async function with retry policy."""
        attempt = 1
        start_time = time.time()
        exceptions = []
        
        while True:
            try:
                result = await func(*args, **kwargs)
                
                # Record successful operation
                total_time = time.time() - start_time
                self.metrics.add_operation(attempt, total_time, True, exceptions)
                
                if attempt > 1:
                    logger.info(f"Retry policy '{self.name}' succeeded after {attempt} attempts")
                
                return result
                
            except Exception as e:
                exceptions.append(e)
                
                if not self._should_retry(e, attempt):
                    # Record failed operation
                    total_time = time.time() - start_time
                    self.metrics.add_operation(attempt, total_time, False, exceptions)
                    
                    if attempt >= self.config.max_attempts:
                        logger.error(f"Retry policy '{self.name}' exhausted {self.config.max_attempts} attempts")
                    else:
                        logger.info(f"Retry policy '{self.name}' not retrying {type(e).__name__}: {e}")
                    
                    raise
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                if delay > 0:
                    logger.debug(f"Retry policy '{self.name}' waiting {delay:.2f}s before attempt {attempt + 1}")
                    await asyncio.sleep(delay)
                
                attempt += 1
                logger.info(f"Retry policy '{self.name}' attempting retry {attempt}/{self.config.max_attempts} after {type(e).__name__}: {e}")
    
    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a sync function with retry policy."""
        attempt = 1
        start_time = time.time()
        exceptions = []
        
        while True:
            try:
                result = func(*args, **kwargs)
                
                # Record successful operation
                total_time = time.time() - start_time
                self.metrics.add_operation(attempt, total_time, True, exceptions)
                
                if attempt > 1:
                    logger.info(f"Retry policy '{self.name}' succeeded after {attempt} attempts")
                
                return result
                
            except Exception as e:
                exceptions.append(e)
                
                if not self._should_retry(e, attempt):
                    # Record failed operation
                    total_time = time.time() - start_time
                    self.metrics.add_operation(attempt, total_time, False, exceptions)
                    
                    if attempt >= self.config.max_attempts:
                        logger.error(f"Retry policy '{self.name}' exhausted {self.config.max_attempts} attempts")
                    else:
                        logger.info(f"Retry policy '{self.name}' not retrying {type(e).__name__}: {e}")
                    
                    raise
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                if delay > 0:
                    logger.debug(f"Retry policy '{self.name}' waiting {delay:.2f}s before attempt {attempt + 1}")
                    time.sleep(delay)
                
                attempt += 1
                logger.info(f"Retry policy '{self.name}' attempting retry {attempt}/{self.config.max_attempts} after {type(e).__name__}: {e}")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator interface for retry policy."""
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
    
    def get_metrics(self) -> dict:
        """Get current retry policy metrics."""
        return {
            'name': self.name,
            'config': {
                'max_attempts': self.config.max_attempts,
                'base_delay': self.config.base_delay,
                'max_delay': self.config.max_delay,
                'backoff_strategy': self.config.backoff_strategy.value
            },
            'metrics': {
                'total_operations': self.metrics.total_operations,
                'successful_operations': self.metrics.successful_operations,
                'failed_operations': self.metrics.failed_operations,
                'success_rate': self.metrics.success_rate,
                'total_retries': self.metrics.total_retries,
                'average_attempts': self.metrics.average_attempts,
                'average_retry_time': self.metrics.average_retry_time,
                'max_retry_time': self.metrics.max_retry_time,
                'attempts_distribution': self.metrics.attempts_distribution,
                'exception_counts': self.metrics.exception_counts
            }
        }


# Convenience function for creating common retry policies
def create_exponential_retry(
    name: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_exceptions: tuple = (Exception,),
    stop_exceptions: tuple = ()
) -> RetryPolicy:
    """Create a retry policy with exponential backoff."""
    config = RetryConfig(
        name=name,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER if jitter else BackoffStrategy.EXPONENTIAL,
        retry_exceptions=retry_exceptions,
        stop_exceptions=stop_exceptions
    )
    return RetryPolicy(config)


def create_linear_retry(
    name: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    increment: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: tuple = (Exception,),
    stop_exceptions: tuple = ()
) -> RetryPolicy:
    """Create a retry policy with linear backoff."""
    config = RetryConfig(
        name=name,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.LINEAR,
        linear_increment=increment,
        retry_exceptions=retry_exceptions,
        stop_exceptions=stop_exceptions
    )
    return RetryPolicy(config)


def create_constant_retry(
    name: str,
    max_attempts: int = 3,
    delay: float = 1.0,
    retry_exceptions: tuple = (Exception,),
    stop_exceptions: tuple = ()
) -> RetryPolicy:
    """Create a retry policy with constant delay."""
    config = RetryConfig(
        name=name,
        max_attempts=max_attempts,
        base_delay=delay,
        max_delay=delay,
        backoff_strategy=BackoffStrategy.CONSTANT,
        retry_exceptions=retry_exceptions,
        stop_exceptions=stop_exceptions
    )
    return RetryPolicy(config)


# Decorator functions
def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER,
    retry_exceptions: tuple = (Exception,),
    stop_exceptions: tuple = (),
    name: Optional[str] = None
) -> Callable:
    """
    Decorator for applying retry policy.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay between retries
        backoff_strategy: Strategy for calculating delays
        retry_exceptions: Exceptions to retry on
        stop_exceptions: Exceptions to never retry
        name: Optional name for the retry policy
    
    Returns:
        Decorated function with retry protection
    """
    if name is None:
        name = f"retry_policy_{id(retry)}"
    
    config = RetryConfig(
        name=name,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        retry_exceptions=retry_exceptions,
        stop_exceptions=stop_exceptions
    )
    
    policy = RetryPolicy(config)
    return policy