"""Validation exception classes."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from .models import ValidationLevel


@dataclass
class ValidationError(Exception):
    """Base validation error with structured data."""
    code: str
    message: str
    level: ValidationLevel = ValidationLevel.ERROR
    field: Optional[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        super().__init__(self.message)


@dataclass 
class ValidationWarning(ValidationError):
    """Validation warning (non-blocking)."""
    level: ValidationLevel = ValidationLevel.WARNING


class ConfigValidationError(ValidationError):
    """Configuration validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code='config_validation_error',
            message=message,
            level=ValidationLevel.ERROR,
            field=field,
            details=details or {}
        )


class BinanceValidationError(ValidationError):
    """Binance-specific validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code='binance_validation_error', 
            message=message,
            level=ValidationLevel.ERROR,
            field=field,
            details=details or {}
        )


class SignalValidationError(ValidationError):
    """Signal data validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code='signal_validation_error',
            message=message, 
            level=ValidationLevel.ERROR,
            field=field,
            details=details or {}
        )