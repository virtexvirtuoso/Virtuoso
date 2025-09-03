"""
Merged validation module
Merged from: core/validation/protocols.py and validation/core/protocols.py
"""

from .base import ValidationResult, ValidationContext
from .models import ValidationRule
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, Optional, List
from typing_extensions import runtime_checkable

@runtime_checkable
class ValidationProtocol(Protocol):
    """Base protocol for validation providers."""

    async def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data with context.
        
        Args:
            data: Data to validate
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...

@runtime_checkable
class ContextProviderProtocol(Protocol):
    """Protocol for context providers."""

    def create_context(self, data_type: str, **kwargs) -> ValidationContext:
        """Create validation context."""
        ...

class DataValidationProtocol(ValidationProtocol):
    """Protocol for data validation providers."""

    async def validate_data(self, data: Any, data_type: str, context: ValidationContext) -> ValidationResult:
        """Validate data of type.
        
        Args:
            data: Data to validate
            data_type: Type of data
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...

    async def get_validators(self, data_type: str) -> List[ValidationRule]:
        """Get validators for data type.
        
        Args:
            data_type: Type of data
            
        Returns:
            List[ValidationRule]: List of validation rules
        """
        ...

@runtime_checkable
class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection."""

    def collect_metrics(self, result: ValidationResult, duration: float) -> None:
        """Collect validation metrics."""
        ...

@runtime_checkable
class RuleProtocol(Protocol):
    """Protocol for validation rules."""

    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data against this rule."""
        ...

class RuleValidationProtocol(ValidationProtocol):
    """Protocol for rule validation providers."""

    async def validate_rule(self, data: Any, rule: ValidationRule, context: ValidationContext) -> ValidationResult:
        """Validate data against rule.
        
        Args:
            data: Data to validate
            rule: Validation rule
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...

    async def validate_rules(self, data: Any, rules: List[ValidationRule], context: ValidationContext) -> ValidationResult:
        """Validate data against multiple rules.
        
        Args:
            data: Data to validate
            rules: List of validation rules
            context: Validation context
            
        Returns:
            ValidationResult: Combined result
        """
        ...

class SchemaValidationProtocol(ValidationProtocol):
    """Protocol for schema validation providers."""

    async def validate_schema(self, data: Any, schema: Dict[str, Any], context: ValidationContext) -> ValidationResult:
        """Validate data against schema.
        
        Args:
            data: Data to validate
            schema: Validation schema
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...

@runtime_checkable
class ValidatorProtocol(Protocol):
    """Protocol for validators."""

    @property
    def name(self) -> str:
        """Get validator name."""
        ...

    @property
    def version(self) -> str:
        """Get validator version."""
        ...

    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate data."""
        ...

    def get_config(self) -> Dict[str, Any]:
        """Get validator configuration."""
        ...

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update validator configuration."""
        ...

@runtime_checkable
class ValidationManagerProtocol(Protocol):
    """Protocol for validation managers."""

    async def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data."""
        ...

    def add_validator(self, validator: ValidatorProtocol) -> None:
        """Add validator."""
        ...

    def remove_validator(self, name: str) -> None:
        """Remove validator."""
        ...

    def get_validators(self) -> List[ValidatorProtocol]:
        """Get all validators."""
        ...