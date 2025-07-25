"""Validation system protocols.

This module defines protocols for validation providers.
"""

from typing import Protocol, Dict, Any, Optional, List
from typing_extensions import runtime_checkable

from .models import ValidationRule
from .base import ValidationResult, ValidationContext

@runtime_checkable
class ValidatorProtocol(Protocol):
    """Protocol for validator classes."""
    
    async def validate(
        self,
        data: Any,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data with context."""
        ...

@runtime_checkable
class RuleProtocol(Protocol):
    """Protocol for validation rules."""
    
    def validate(
        self,
        data: Any,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data against this rule."""
        ...

@runtime_checkable
class ContextProviderProtocol(Protocol):
    """Protocol for context providers."""
    
    def create_context(
        self,
        data_type: str,
        **kwargs
    ) -> ValidationContext:
        """Create validation context."""
        ...

@runtime_checkable
class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection."""
    
    def collect_metrics(
        self,
        result: ValidationResult,
        duration: float
    ) -> None:
        """Collect validation metrics."""
        ...