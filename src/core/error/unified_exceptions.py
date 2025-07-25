"""
Unified Exception System for Virtuoso

This module provides a comprehensive, structured error hierarchy that consolidates
all error types across the application. It replaces scattered error definitions
with a unified system that provides rich context and consistent handling.

Design Principles:
1. Single source of truth for all error types
2. Rich error context with metadata support
3. Hierarchical organization by domain
4. Backward compatibility with existing error handling
5. Structured error data for logging and monitoring
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime
import traceback
import sys


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    DEBUG = 'debug'


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    SYSTEM = 'system'
    VALIDATION = 'validation'
    NETWORK = 'network'
    EXCHANGE = 'exchange'
    TRADING = 'trading'
    ANALYSIS = 'analysis'
    CONFIGURATION = 'configuration'
    RESOURCE = 'resource'
    SECURITY = 'security'
    USER_INPUT = 'user_input'


# Import the canonical ErrorContext
from .context import ErrorContext


# =============================================================================
# Base Error Classes
# =============================================================================

class VirtuosoError(Exception):
    """
    Base exception for all Virtuoso errors.
    
    Provides rich error context, structured data, and metadata support
    for comprehensive error tracking and debugging.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[ErrorContext] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.lower()
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.details = details or {}
        self.cause = cause
        
        # Set component from context if not already set
        if not self.context.component:
            self.context.component = self._infer_component()
    
    def _infer_component(self) -> str:
        """Infer component name from stack trace."""
        frame = sys._getframe(3)  # Go up the stack to find caller
        if frame and frame.f_code.co_filename:
            filename = frame.f_code.co_filename
            if 'src/' in filename:
                # Extract component from src path
                parts = filename.split('src/')[-1].split('/')
                return parts[0] if parts else 'unknown'
        return 'unknown'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'severity': self.severity.value,
            'category': self.category.value,
            'timestamp': self.context.timestamp.isoformat(),
            'component': self.context.component,
            'operation': self.context.operation,
            'symbol': self.context.symbol,
            'exchange': self.context.exchange,
            'correlation_id': self.context.correlation_id,
            'details': self.details,
            'cause': str(self.cause) if self.cause else None
        }


# =============================================================================
# System Errors
# =============================================================================

class SystemError(VirtuosoError):
    """Base class for system-level errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.SYSTEM,
            **kwargs
        )


class ComponentError(SystemError):
    """Base class for component-related errors."""
    
    def __init__(self, message: str, component: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext()
        if component:
            context.component = component
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class InitializationError(ComponentError):
    """Error during component initialization."""
    
    def __init__(self, message: str, component: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext()
        context.operation = 'initialization'
        kwargs['context'] = context
        super().__init__(message, component=component, **kwargs)


class ResourceError(SystemError):
    """Error related to system resources."""
    
    def __init__(self, message: str, resource_type: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            **kwargs
        )
        if resource_type:
            self.details['resource_type'] = resource_type


class ResourceLimitError(ResourceError):
    """Error when system resource limits are exceeded."""
    
    def __init__(self, message: str, limit: Union[int, float] = None, current: Union[int, float] = None, **kwargs):
        super().__init__(message, **kwargs)
        if limit is not None:
            self.details['limit'] = limit
        if current is not None:
            self.details['current'] = current


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(VirtuosoError):
    """Base validation error with structured data."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        validation_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code=validation_code or 'validation_error',
            category=ErrorCategory.VALIDATION,
            **kwargs
        )
        if field:
            self.details['field'] = field


class ConfigValidationError(ValidationError):
    """Configuration validation error."""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(
            message,
            field=config_key,
            validation_code='config_validation_error',
            category=ErrorCategory.CONFIGURATION,
            **kwargs
        )


class SignalValidationError(ValidationError):
    """Signal data validation error."""
    
    def __init__(self, message: str, signal_type: str = None, **kwargs):
        super().__init__(
            message,
            validation_code='signal_validation_error',
            **kwargs
        )
        if signal_type:
            self.details['signal_type'] = signal_type


class BinanceValidationError(ValidationError):
    """Binance-specific validation error."""
    
    def __init__(self, message: str, **kwargs):
        context = kwargs.get('context') or ErrorContext()
        context.exchange = 'binance'
        kwargs['context'] = context
        super().__init__(
            message,
            validation_code='binance_validation_error',
            **kwargs
        )


# =============================================================================
# Network and Exchange Errors
# =============================================================================

class NetworkError(VirtuosoError):
    """Base class for network-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            **kwargs
        )


class TimeoutError(NetworkError):
    """Operation timeout error."""
    
    def __init__(self, message: str, timeout_duration: float = None, **kwargs):
        super().__init__(message, **kwargs)
        if timeout_duration:
            self.details['timeout_duration'] = timeout_duration


class ExchangeError(VirtuosoError):
    """Base class for exchange-related errors."""
    
    def __init__(self, message: str, exchange: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext()
        if exchange:
            context.exchange = exchange
        kwargs['context'] = context
        super().__init__(
            message,
            category=ErrorCategory.EXCHANGE,
            **kwargs
        )


class AuthenticationError(ExchangeError):
    """Exchange authentication error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_code='authentication_error',
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class RateLimitError(ExchangeError):
    """Exchange rate limit error."""
    
    def __init__(self, message: str, retry_after: float = None, **kwargs):
        super().__init__(message, **kwargs)
        if retry_after:
            self.details['retry_after'] = retry_after


class BybitExchangeError(ExchangeError):
    """Bybit-specific exchange error."""
    
    def __init__(self, message: str, **kwargs):
        context = kwargs.get('context') or ErrorContext()
        context.exchange = 'bybit'
        kwargs['context'] = context
        super().__init__(message, **kwargs)


# =============================================================================
# Trading Errors
# =============================================================================

class TradingError(VirtuosoError):
    """Base class for trading-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.TRADING,
            **kwargs
        )


class MarketDataError(TradingError):
    """Market data related error."""
    
    def __init__(self, message: str, symbol: str = None, **kwargs):
        context = kwargs.get('context') or ErrorContext()
        if symbol:
            context.symbol = symbol
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class CalculationError(TradingError):
    """Calculation or computation error."""
    
    def __init__(self, message: str, calculation_type: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if calculation_type:
            self.details['calculation_type'] = calculation_type


# =============================================================================
# Analysis Errors
# =============================================================================

class AnalysisError(VirtuosoError):
    """Base class for analysis-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.ANALYSIS,
            **kwargs
        )


class DataUnavailableError(AnalysisError):
    """Data required for analysis is unavailable."""
    
    def __init__(self, message: str, data_type: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if data_type:
            self.details['data_type'] = data_type


# =============================================================================
# Reporting Errors
# =============================================================================

class PDFGenerationError(VirtuosoError):
    """Base class for PDF generation errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class ChartGenerationError(PDFGenerationError):
    """Chart generation specific error."""
    
    def __init__(self, message: str, chart_type: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if chart_type:
            self.details['chart_type'] = chart_type


class DataValidationError(PDFGenerationError):
    """Data validation error in PDF generation."""
    pass


class FileOperationError(PDFGenerationError):
    """File operation error in PDF generation."""
    pass


class TemplateError(PDFGenerationError):
    """Template error in PDF generation."""
    pass


# =============================================================================
# Legacy Compatibility
# =============================================================================

# Maintain backward compatibility with existing code
ConfigurationError = ConfigValidationError  # Alias for utils/error_handling.py users
StateError = ComponentError  # Alias for existing StateError usage
CommunicationError = NetworkError  # Alias for existing CommunicationError usage
OperationError = SystemError  # Alias for existing OperationError usage
DataError = AnalysisError  # Alias for existing DataError usage
SecurityError = SystemError  # Keep as SystemError until security module is defined
MarketMonitorError = ComponentError  # Alias for market monitor errors
TemporaryError = SystemError  # Can be enhanced with retry logic later
CriticalError = SystemError  # Alias for critical errors
StateTransitionError = ComponentError  # Alias for state transition errors
ResourceAllocationError = ResourceError  # Alias for resource allocation errors
ExchangeNotInitializedError = InitializationError  # Alias for exchange initialization
ComponentInitializationError = InitializationError  # Alias
ComponentCleanupError = ComponentError  # Alias
DependencyError = ComponentError  # Alias


# =============================================================================
# Error Registry
# =============================================================================

class ErrorRegistry:
    """Registry for all error types in the system."""
    
    _errors = {}
    
    @classmethod
    def register(cls, error_class: type, category: ErrorCategory = None):
        """Register an error class."""
        cls._errors[error_class.__name__] = {
            'class': error_class,
            'category': category,
            'module': error_class.__module__
        }
    
    @classmethod
    def get_error_class(cls, name: str) -> Optional[type]:
        """Get error class by name."""
        return cls._errors.get(name, {}).get('class')
    
    @classmethod
    def list_errors(cls) -> List[Dict[str, Any]]:
        """List all registered errors."""
        return list(cls._errors.values())


# Auto-register all error classes
import inspect
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if (inspect.isclass(obj) and 
        issubclass(obj, VirtuosoError) and 
        obj != VirtuosoError):
        category = getattr(obj, 'category', ErrorCategory.SYSTEM)
        ErrorRegistry.register(obj, category)