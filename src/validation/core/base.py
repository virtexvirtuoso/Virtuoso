"""
Base interfaces and types for validation system.
Merged from: core/validation/base.py and validation/core/base.py
"""

import dataclasses
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Type, Union
from typing_extensions import Protocol

from .models import ValidationErrorData, ValidationLevel
from .exceptions import ValidationError

@dataclasses.dataclass
class ValidationContext:
    """Context for validation operations."""
    data_type: str
    strict_mode: bool = False
    max_errors: Optional[int] = None
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))

@dataclasses.dataclass
class ValidationResult:
    """Standardized validation result class."""
    success: bool = True
    errors: List[ValidationError] = dataclasses.field(default_factory=list)
    warnings: List[ValidationError] = dataclasses.field(default_factory=list)
    context: Optional[str] = None
    validated_data: Optional[Any] = None
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))

    def add_error(self, error: Union[str, ValidationError], level: ValidationLevel=ValidationLevel.ERROR) -> None:
        """Add an error and set success to False."""
        if isinstance(error, str):
            error = ValidationError(code='validation_error', message=error, level=level)
        if error.level == ValidationLevel.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)
            self.success = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(ValidationError(code='validation_warning', message=message, level=ValidationLevel.WARNING))

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.success and (not self.errors)

    def __bool__(self) -> bool:
        """Boolean representation of validation result."""
        return self.is_valid

class ValidationProvider(Protocol):
    """Protocol for validation providers."""

    @abstractmethod
    async def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data with context."""
        pass

class ValidationRegistry:
    """Registry for validation providers."""

    def __init__(self):
        self._providers: Dict[str, ValidationProvider] = {}
