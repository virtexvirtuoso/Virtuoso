"""
Validation exception classes.

This module now imports all validation errors from the unified error system
to maintain backward compatibility while eliminating duplication.
"""

# Import all validation errors from the unified system
from src.core.error.unified_exceptions import (
    ValidationError,
    ConfigValidationError, 
    BinanceValidationError,
    SignalValidationError,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext
)

# Legacy ValidationWarning for backward compatibility
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .models import ValidationLevel

@dataclass
class ValidationWarning(ValidationError):
    """Validation warning (non-blocking)."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            field=field,
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            details=details
        )

# Export all for backward compatibility
__all__ = [
    'ValidationError',
    'ValidationWarning', 
    'ConfigValidationError',
    'BinanceValidationError',
    'SignalValidationError',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorContext'
]