"""
Enhanced Error Handler with Circuit Breaker Integration

Provides comprehensive error handling, retry logic, and fallback mechanisms
for production trading system stability.
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Union, Type
from dataclasses import dataclass
from enum import Enum
import random

from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError,
    get_circuit_manager
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for different handling strategies"""
    NETWORK = "network"
    API_RATE_LIMIT = "api_rate_limit"
    API_ERROR = "api_error"
    DATA_VALIDATION = "data_validation"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    component: str
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class ErrorHandler:
    """
    Production-grade error handler with circuit breaker integration.
    
    Features:
    - Intelligent retry logic with exponential backoff
    - Circuit breaker integration for external services
    - Error categorization and severity assessment
    - Comprehensive logging and monitoring
    - Fallback mechanisms
    """
    
    def __init__(self):
        self.circuit_manager = get_circuit_manager()
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'retry_attempts': 0,
            'circuit_breaker_activations': 0
        }
        
        # Define retryable exceptions
        self.retryable_exceptions = {
            # Network-related errors
            asyncio.TimeoutError,
            ConnectionError,
            ConnectionResetError,
            # HTTP-related errors that might be temporary
            # Add specific exchange API exceptions here
        }
        
        # Define error category mappings
        self.error_mappings = {
            asyncio.TimeoutError: ErrorCategory.NETWORK,
            ConnectionError: ErrorCategory.NETWORK,
            ConnectionResetError: ErrorCategory.NETWORK,
            ValueError: ErrorCategory.DATA_VALIDATION,
            KeyError: ErrorCategory.DATA_VALIDATION,
            # Add more specific mappings as needed
        }
    
    def categorize_error(self, exception: Exception) -> ErrorCategory:
        """Categorize error type for appropriate handling"""
        exception_type = type(exception)
        
        # Check direct mappings
        if exception_type in self.error_mappings:
            return self.error_mappings[exception_type]
        
        # Check for specific patterns in error messages
        error_msg = str(exception).lower()
        
        if any(term in error_msg for term in ['rate limit', 'too many requests', '429']):
            return ErrorCategory.API_RATE_LIMIT
        
        if any(term in error_msg for term in ['timeout', 'connection', 'network']):
            return ErrorCategory.NETWORK
        
        if any(term in error_msg for term in ['invalid', 'validation', 'format']):
            return ErrorCategory.DATA_VALIDATION
        
        if any(term in error_msg for term in ['api', 'service', 'server']):
            return ErrorCategory.API_ERROR
        
        return ErrorCategory.SYSTEM
    
    def assess_severity(self, exception: Exception, context: ErrorContext) -> ErrorSeverity:
        """Assess error severity based on exception and context"""
        category = self.categorize_error(exception)
        
        # Critical errors that affect core functionality
        if isinstance(exception, (MemoryError, SystemError)):
            return ErrorSeverity.CRITICAL
        
        # High severity for exchange API failures
        if category == ErrorCategory.API_ERROR and context.component == 'exchange':
            return ErrorSeverity.HIGH
        
        # Medium severity for network issues (might be temporary)
        if category in [ErrorCategory.NETWORK, ErrorCategory.API_RATE_LIMIT]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for data validation (likely input issue)
        if category == ErrorCategory.DATA_VALIDATION:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def should_retry(self, exception: Exception, attempt: int, max_attempts: int) -> bool:
        """Determine if error should be retried"""
        if attempt >= max_attempts:
            return False
        
        # Check if exception type is retryable
        if type(exception) in self.retryable_exceptions:
            return True
        
        # Check for specific error patterns
        error_msg = str(exception).lower()
        
        # Retry on temporary network/service issues
        if any(term in error_msg for term in [
            'timeout', 'connection', 'temporary', 'service unavailable',
            'rate limit', 'too many requests'
        ]):
            return True
        
        # Don't retry on permanent errors
        if any(term in error_msg for term in [
            'unauthorized', 'forbidden', 'not found', 'invalid api key',
            'bad request', 'validation'
        ]):
            return False
        
        return False
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt with exponential backoff"""
        delay = config.base_delay * (config.exponential_base ** (attempt - 1))
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0, 0.1) * delay
            delay += jitter
        
        return delay
    
    async def execute_with_retry(
        self,
        func: Callable,
        context: ErrorContext,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_name: Optional[str] = None,
        fallback: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with comprehensive error handling and retry logic.
        
        Args:
            func: Function to execute
            context: Error context for logging and monitoring
            retry_config: Retry configuration (uses default if None)
            circuit_breaker_name: Name of circuit breaker to use
            fallback: Fallback function if all retries fail
            *args, **kwargs: Arguments for the function
        
        Returns:
            Function result or fallback result
        
        Raises:
            Exception: If all retries fail and no fallback provided
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        last_exception = None
        
        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                # Use circuit breaker if specified
                if circuit_breaker_name:
                    breaker = self.circuit_manager.get_or_create(
                        circuit_breaker_name,
                        CircuitBreakerConfig()
                    )
                    return await breaker.call_async(func, *args, **kwargs)
                else:
                    # Direct execution
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                
            except CircuitBreakerError as e:
                # Circuit breaker is open, try fallback immediately
                logger.warning(
                    f"Circuit breaker open for {context.operation} - {context.component}: {e}"
                )
                self.error_stats['circuit_breaker_activations'] += 1
                break
                
            except Exception as e:
                last_exception = e
                self.error_stats['total_errors'] += 1
                
                # Categorize and assess error
                category = self.categorize_error(e)
                severity = self.assess_severity(e, context)
                
                # Update statistics
                self.error_stats['errors_by_category'][category.value] = (
                    self.error_stats['errors_by_category'].get(category.value, 0) + 1
                )
                self.error_stats['errors_by_severity'][severity.value] = (
                    self.error_stats['errors_by_severity'].get(severity.value, 0) + 1
                )
                
                # Log error with context
                self._log_error(e, context, category, severity, attempt, retry_config.max_attempts)
                
                # Check if we should retry
                if not self.should_retry(e, attempt, retry_config.max_attempts):
                    logger.info(f"Not retrying {context.operation} - error not retryable")
                    break
                
                if attempt < retry_config.max_attempts:
                    # Calculate delay and wait
                    delay = self.calculate_delay(attempt, retry_config)
                    logger.info(f"Retrying {context.operation} in {delay:.2f}s (attempt {attempt + 1})")
                    self.error_stats['retry_attempts'] += 1
                    await asyncio.sleep(delay)
        
        # All retries failed, try fallback
        if fallback:
            try:
                logger.info(f"Executing fallback for {context.operation}")
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                else:
                    return fallback(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback failed for {context.operation}: {fallback_error}")
                # Fall through to raise original exception
        
        # No fallback or fallback failed, raise original exception
        if last_exception:
            logger.error(f"All retries exhausted for {context.operation}")
            raise last_exception
        else:
            raise Exception(f"Unknown error in {context.operation}")
    
    def _log_error(
        self,
        exception: Exception,
        context: ErrorContext,
        category: ErrorCategory,
        severity: ErrorSeverity,
        attempt: int,
        max_attempts: int
    ):
        """Log error with comprehensive context"""
        log_data = {
            'operation': context.operation,
            'component': context.component,
            'error_type': type(exception).__name__,
            'error_message': str(exception),
            'category': category.value,
            'severity': severity.value,
            'attempt': attempt,
            'max_attempts': max_attempts,
            'symbol': context.symbol,
            'exchange': context.exchange,
            'user_id': context.user_id,
            'request_id': context.request_id
        }
        
        if context.additional_data:
            log_data.update(context.additional_data)
        
        # Choose log level based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR in {context.operation}: {log_data}")
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH severity error in {context.operation}: {log_data}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM severity error in {context.operation}: {log_data}")
        else:
            logger.info(f"LOW severity error in {context.operation}: {log_data}")
        
        # Log stack trace for high/critical errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"Stack trace for {context.operation}: {traceback.format_exc()}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            'timestamp': time.time(),
            'stats': self.error_stats.copy(),
            'circuit_breakers': self.circuit_manager.get_all_states()
        }
    
    def reset_statistics(self):
        """Reset error statistics"""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'retry_attempts': 0,
            'circuit_breaker_activations': 0
        }
        logger.info("Error statistics reset")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
        logger.info("✅ Global error handler initialized")
    return _error_handler


def handle_errors(
    operation: str,
    component: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    fallback: Optional[Callable] = None,
    **context_kwargs
):
    """
    Decorator for automatic error handling with retries and circuit breaker.
    
    Usage:
        @handle_errors('fetch_ticker', 'exchange', circuit_breaker_name='bybit_api')
        async def fetch_ticker(symbol):
            # API call here
            pass
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            context = ErrorContext(
                operation=operation,
                component=component,
                **context_kwargs
            )
            
            return await error_handler.execute_with_retry(
                func,
                context,
                retry_config,
                circuit_breaker_name,
                fallback,
                *args,
                **kwargs
            )
        
        return wrapper
    return decorator