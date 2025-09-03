"""
Validation interfaces for dependency injection and type safety.
"""
from abc import ABC, abstractmethod
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Optional[Dict[str, Any]] = None
    
    def __bool__(self) -> bool:
        return self.is_valid

@runtime_checkable
class ValidatorInterface(Protocol):
    """Interface for validators."""
    
    @abstractmethod
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate data.
        
        Args:
            data: Data to validate
            context: Optional validation context
            
        Returns:
            ValidationResult with validation outcome
        """
        pass
    
    @abstractmethod
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules."""
        pass

@runtime_checkable
class DataValidatorInterface(Protocol):
    """Interface for data validators."""
    
    @abstractmethod
    def validate_dataframe(self, df: Any, schema: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate a dataframe."""
        pass
    
    @abstractmethod
    def validate_timeseries(self, data: Any, frequency: str) -> ValidationResult:
        """Validate timeseries data."""
        pass
    
    @abstractmethod
    def validate_market_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate market data structure."""
        pass

@runtime_checkable
class ConfigValidatorInterface(Protocol):
    """Interface for configuration validators."""
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate configuration."""
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        pass
    
    @abstractmethod
    def validate_field(self, field_name: str, value: Any) -> ValidationResult:
        """Validate a single configuration field."""
        pass

@runtime_checkable
class SchemaValidatorInterface(Protocol):
    """Interface for schema-based validators."""
    
    @abstractmethod
    def validate_against_schema(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Validate data against a schema."""
        pass
    
    @abstractmethod
    def compile_schema(self, schema: Dict[str, Any]) -> Any:
        """Compile schema for efficient validation."""
        pass

class ValidatorAdapter:
    """Adapter to make existing validators compatible with ValidatorInterface."""
    
    def __init__(self, validator: Any):
        self.validator = validator
        
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate data."""
        try:
            if hasattr(self.validator, 'validate'):
                result = self.validator.validate(data, context) if context else self.validator.validate(data)
                
                # Convert various result formats to ValidationResult
                if isinstance(result, ValidationResult):
                    return result
                elif isinstance(result, bool):
                    return ValidationResult(is_valid=result, errors=[], warnings=[])
                elif isinstance(result, dict):
                    return ValidationResult(
                        is_valid=result.get('is_valid', result.get('valid', False)),
                        errors=result.get('errors', []),
                        warnings=result.get('warnings', []),
                        metadata=result.get('metadata')
                    )
                else:
                    return ValidationResult(is_valid=bool(result), errors=[], warnings=[])
                    
            elif hasattr(self.validator, 'is_valid'):
                is_valid = self.validator.is_valid(data)
                errors = getattr(self.validator, 'errors', [])
                warnings = getattr(self.validator, 'warnings', [])
                return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
                
            else:
                raise NotImplementedError(f"Validator {type(self.validator)} has no validate method")
                
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                metadata={'exception': type(e).__name__}
            )
            
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules."""
        if hasattr(self.validator, 'get_validation_rules'):
            return self.validator.get_validation_rules()
        elif hasattr(self.validator, 'rules'):
            return self.validator.rules
        else:
            return {}