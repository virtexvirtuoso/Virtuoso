"""Unified validation package for the trading system.

This package consolidates all validation functionality from across the codebase
into a single, well-organized package with clear separation of concerns.

Main components:
- core: Base validation classes and protocols
- rules: Validation rule implementations
- validators: Domain-specific validators
- services: Validation services (sync/async)
- cache: Validation result caching

Key exports:
- ValidationResult, ValidationContext, ValidationError
- ValidationService, AsyncValidationService
- Core validators and rules
"""

# Core validation classes
from .core.base import (
    ValidationResult,
    ValidationContext, 
    ValidationProvider,
    ValidationRegistry
)

from .core.exceptions import (
    ValidationError,
    ValidationWarning,
    ConfigValidationError,
    BinanceValidationError,
    SignalValidationError
)

from .core.models import (
    ValidationLevel,
    ValidationErrorData,
    ValidationRule,
    ValidationMetrics
)

# Validation rules
from .rules.market import (
    TimeRangeRule,
    SymbolRule,
    NumericRangeRule,
    CrossFieldValidationRule
)

# Validators
from .validators.data_validator import DataValidator
from .validators.market_validator import MarketDataValidator
from .validators.context_validator import MarketContextValidator
from .validators.timeseries_validator import TimeSeriesValidator
from .validators.orderbook_validator import OrderBookValidator
from .validators.trades_validator import TradesValidator

# Services
from .services.sync_service import ValidationService
from .services.async_service import AsyncValidationService

# Cache
from .cache.cache import ValidationCache, ValidationCacheEntry

__all__ = [
    # Core classes
    'ValidationResult',
    'ValidationContext',
    'ValidationProvider', 
    'ValidationRegistry',
    
    # Exceptions
    'ValidationError',
    'ValidationWarning',
    'ConfigValidationError',
    'BinanceValidationError', 
    'SignalValidationError',
    
    # Models
    'ValidationLevel',
    'ValidationErrorData',
    'ValidationRule',
    'ValidationMetrics',
    
    # Rules
    'TimeRangeRule',
    'SymbolRule',
    'NumericRangeRule',
    'CrossFieldValidationRule',
    
    # Validators
    'DataValidator',
    'MarketDataValidator',
    'MarketContextValidator',
    'TimeSeriesValidator',
    'OrderBookValidator',
    'TradesValidator',
    
    # Services
    'ValidationService',
    'AsyncValidationService',
    
    # Cache
    'ValidationCache',
    'ValidationCacheEntry'
]

# Version info
__version__ = '1.0.0'