"""Validation models.

This module provides the data models used by the validation system.
"""

import dataclasses
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime

class ValidationLevel(str, Enum):
    """Validation error severity levels."""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'

@dataclasses.dataclass
class ValidationError:
    """Validation error details."""
    code: str
    message: str
    level: ValidationLevel = ValidationLevel.ERROR
    field: Optional[str] = None
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)

@dataclasses.dataclass
class ValidationRule:
    """Validation rule configuration."""
    name: str
    active: bool = True
    level: ValidationLevel = ValidationLevel.ERROR
    field: Optional[str] = None
    parameters: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def rule_name(self) -> str:
        """Get rule name."""
        return self.name.lower().replace(' ', '_')

@dataclasses.dataclass
class ValidationContext:
    """Context for validation operations."""
    data_type: str
    strict_mode: bool = False
    max_errors: Optional[int] = None
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now())

@dataclasses.dataclass
class ValidationResult:
    """Result of validation operations."""
    success: bool = True
    errors: List[ValidationError] = dataclasses.field(default_factory=list)
    warnings: List[ValidationError] = dataclasses.field(default_factory=list)
    context: Optional[ValidationContext] = None
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def add_error(self, message: str, code: str = 'validation_error', level: ValidationLevel = ValidationLevel.ERROR) -> None:
        """Add an error to the validation result."""
        error = ValidationError(code=code, message=message, level=level)
        if level == ValidationLevel.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)
            self.success = False

    def add_warning(self, message: str, code: str = 'validation_warning') -> None:
        """Add a warning to the validation result."""
        self.warnings.append(ValidationError(
            code=code,
            message=message,
            level=ValidationLevel.WARNING
        ))

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.success and not self.errors


@dataclasses.dataclass
class ValidationMetrics:
    """Metrics for validation operations."""
    
    total_validations: int = 0
    failed_validations: int = 0
    avg_validation_time: float = 0.0
    last_validation: Optional[datetime] = None
    
    def record_validation(self, duration: float, success: bool) -> None:
        """Record validation operation."""
        self.total_validations += 1
        if not success:
            self.failed_validations += 1
        
        self.avg_validation_time = (
            (self.avg_validation_time * (self.total_validations - 1) + duration)
            / self.total_validations
        )
        self.last_validation = datetime.utcnow() 