"""Validation system protocols.

This module defines protocols for validation providers:
- ValidationProtocol: Base protocol for validation providers
- SchemaValidationProtocol: Protocol for schema validation
- DataValidationProtocol: Protocol for data validation
- RuleValidationProtocol: Protocol for rule validation
"""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, Optional, List
from typing_extensions import runtime_checkable

from .models import ValidationResult, ValidationRule
from .context import ValidationContext

@runtime_checkable
class ValidationProtocol(Protocol):
    """Base protocol for validation providers."""
    
    async def validate(
        self,
        data: Any,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data with context.
        
        Args:
            data: Data to validate
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...

@runtime_checkable
class SchemaValidationProtocol(ValidationProtocol):
    """Protocol for schema validation providers."""
    
    async def get_schema(
        self,
        data_type: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get schema for data type.
        
        Args:
            data_type: Type of data
            version: Optional schema version
            
        Returns:
            Optional[Dict[str, Any]]: Schema if found
        """
        ...
        
    async def validate_schema(
        self,
        data: Any,
        schema: Dict[str, Any],
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data against schema.
        
        Args:
            data: Data to validate
            schema: Schema to validate against
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...

@runtime_checkable
class DataValidationProtocol(ValidationProtocol):
    """Protocol for data validation providers."""
    
    async def validate_data(
        self,
        data: Any,
        data_type: str,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data of type.
        
        Args:
            data: Data to validate
            data_type: Type of data
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...
        
    async def get_validators(
        self,
        data_type: str
    ) -> List[ValidationRule]:
        """Get validators for data type.
        
        Args:
            data_type: Type of data
            
        Returns:
            List[ValidationRule]: List of validation rules
        """
        ...

@runtime_checkable
class RuleValidationProtocol(ValidationProtocol):
    """Protocol for rule validation providers."""
    
    async def validate_rule(
        self,
        data: Any,
        rule: ValidationRule,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data against rule.
        
        Args:
            data: Data to validate
            rule: Validation rule
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        ...
        
    async def get_rules(
        self,
        data_type: str
    ) -> List[ValidationRule]:
        """Get rules for data type.
        
        Args:
            data_type: Type of data
            
        Returns:
            List[ValidationRule]: List of validation rules
        """
        ... 