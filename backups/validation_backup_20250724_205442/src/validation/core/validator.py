"""
Core validator implementation for dependency injection.

This module provides a basic validation service that can be used
throughout the application for data validation.
"""

from typing import Dict, Any, List, Optional, Union
import logging
from ...core.interfaces.services import IValidationService, ValidationResult

logger = logging.getLogger(__name__)


class CoreValidator(IValidationService):
    """
    Core validation service implementation.
    
    Provides basic validation functionality for the dependency injection system.
    """
    
    def __init__(self):
        """Initialize the core validator."""
        self.logger = logging.getLogger(__name__)
        self.validation_rules = {}
    
    async def validate(self, data: Dict[str, Any], rules: Optional[List[str]] = None) -> ValidationResult:
        """Validate data against specified rules."""
        try:
            errors = []
            warnings = []
            
            if rules:
                for rule_name in rules:
                    if rule_name in self.validation_rules:
                        rule = self.validation_rules[rule_name]
                        if not self.validate_data(data, rule):
                            errors.append(f"Validation rule '{rule_name}' failed")
                    else:
                        warnings.append(f"Unknown validation rule: {rule_name}")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata={"validated_at": str(self.logger.name)}
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                warnings=[],
                metadata={}
            )
    
    def add_rule(self, rule_name: str, rule: Any) -> None:
        """Add a validation rule."""
        self.validation_rules[rule_name] = rule
    
    def remove_rule(self, rule_name: str) -> None:
        """Remove a validation rule."""
        if rule_name in self.validation_rules:
            del self.validation_rules[rule_name]
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "total_rules": len(self.validation_rules),
            "available_rules": list(self.validation_rules.keys())
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data."""
        try:
            errors = []
            warnings = []
            
            # Basic config validation
            if not isinstance(config, dict):
                errors.append("Config must be a dictionary")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata={"config_keys": list(config.keys()) if isinstance(config, dict) else []}
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Config validation error: {e}"],
                warnings=[],
                metadata={}
            )
    
    async def validate_market_data(self, market_data: Dict[str, Any]) -> ValidationResult:
        """Validate market data structure and completeness."""
        try:
            errors = []
            warnings = []
            
            # Basic market data validation
            required_fields = ['symbol', 'timestamp']
            for field in required_fields:
                if field not in market_data:
                    errors.append(f"Missing required field: {field}")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata={"data_fields": list(market_data.keys())}
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Market data validation error: {e}"],
                warnings=[],
                metadata={}
            )
    
    def validate_data(self, data: Any, rules: Dict[str, Any]) -> bool:
        """
        Validate data against provided rules.
        
        Args:
            data: Data to validate
            rules: Validation rules
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check required fields
            if 'required_fields' in rules and rules['required_fields']:
                if not isinstance(data, dict):
                    self.logger.warning("Data must be a dictionary for required field validation")
                    return False
                
                for field in rules['required_fields']:
                    if field not in data:
                        self.logger.warning(f"Required field '{field}' missing from data")
                        return False
            
            # Check data type
            if 'data_type' in rules:
                expected_type = rules['data_type']
                if not isinstance(data, expected_type):
                    self.logger.warning(f"Data type mismatch: expected {expected_type}, got {type(data)}")
                    return False
            
            # Check minimum length for collections
            if 'min_length' in rules:
                min_length = rules['min_length']
                if hasattr(data, '__len__'):
                    if len(data) < min_length:
                        self.logger.warning(f"Data length {len(data)} is less than minimum {min_length}")
                        return False
                else:
                    self.logger.warning("Cannot check min_length on data without __len__ method")
                    return False
            
            # Check maximum length for collections
            if 'max_length' in rules:
                max_length = rules['max_length']
                if hasattr(data, '__len__'):
                    if len(data) > max_length:
                        self.logger.warning(f"Data length {len(data)} exceeds maximum {max_length}")
                        return False
            
            # Check numeric ranges
            if isinstance(data, (int, float)):
                if 'min_value' in rules and data < rules['min_value']:
                    self.logger.warning(f"Value {data} is less than minimum {rules['min_value']}")
                    return False
                
                if 'max_value' in rules and data > rules['max_value']:
                    self.logger.warning(f"Value {data} exceeds maximum {rules['max_value']}")
                    return False
            
            # Check string patterns
            if isinstance(data, str) and 'pattern' in rules:
                import re
                pattern = rules['pattern']
                if not re.match(pattern, data):
                    self.logger.warning(f"String '{data}' does not match pattern '{pattern}'")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        Validate data against a schema and return list of errors.
        
        Args:
            data: Data to validate
            schema: Schema definition
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            if not isinstance(data, dict):
                errors.append("Data must be a dictionary")
                return errors
            
            # Check required fields
            required_fields = schema.get('required', [])
            for field in required_fields:
                if field not in data:
                    errors.append(f"Required field '{field}' is missing")
            
            # Check field types and constraints
            properties = schema.get('properties', {})
            for field, field_schema in properties.items():
                if field in data:
                    field_errors = self._validate_field(data[field], field_schema, field)
                    errors.extend(field_errors)
            
            # Check for unexpected fields if strict mode
            if schema.get('strict', False):
                allowed_fields = set(properties.keys())
                actual_fields = set(data.keys())
                unexpected = actual_fields - allowed_fields
                for field in unexpected:
                    errors.append(f"Unexpected field '{field}'")
            
        except Exception as e:
            errors.append(f"Schema validation error: {e}")
        
        return errors
    
    def _validate_field(self, value: Any, field_schema: Dict[str, Any], field_name: str) -> List[str]:
        """Validate a single field against its schema."""
        errors = []
        
        try:
            # Check type
            if 'type' in field_schema:
                expected_type = field_schema['type']
                type_map = {
                    'string': str,
                    'integer': int,
                    'number': (int, float),
                    'boolean': bool,
                    'array': list,
                    'object': dict
                }
                
                if expected_type in type_map:
                    expected_python_type = type_map[expected_type]
                    if not isinstance(value, expected_python_type):
                        errors.append(f"Field '{field_name}' should be {expected_type}, got {type(value).__name__}")
            
            # Check string constraints
            if isinstance(value, str):
                if 'minLength' in field_schema and len(value) < field_schema['minLength']:
                    errors.append(f"Field '{field_name}' is too short (minimum {field_schema['minLength']} characters)")
                
                if 'maxLength' in field_schema and len(value) > field_schema['maxLength']:
                    errors.append(f"Field '{field_name}' is too long (maximum {field_schema['maxLength']} characters)")
                
                if 'pattern' in field_schema:
                    import re
                    if not re.match(field_schema['pattern'], value):
                        errors.append(f"Field '{field_name}' does not match required pattern")
            
            # Check numeric constraints
            if isinstance(value, (int, float)):
                if 'minimum' in field_schema and value < field_schema['minimum']:
                    errors.append(f"Field '{field_name}' is below minimum value {field_schema['minimum']}")
                
                if 'maximum' in field_schema and value > field_schema['maximum']:
                    errors.append(f"Field '{field_name}' exceeds maximum value {field_schema['maximum']}")
            
            # Check array constraints
            if isinstance(value, list):
                if 'minItems' in field_schema and len(value) < field_schema['minItems']:
                    errors.append(f"Field '{field_name}' has too few items (minimum {field_schema['minItems']})")
                
                if 'maxItems' in field_schema and len(value) > field_schema['maxItems']:
                    errors.append(f"Field '{field_name}' has too many items (maximum {field_schema['maxItems']})")
                
                # Validate array items if schema provided
                if 'items' in field_schema:
                    item_schema = field_schema['items']
                    for i, item in enumerate(value):
                        item_errors = self._validate_field(item, item_schema, f"{field_name}[{i}]")
                        errors.extend(item_errors)
            
        except Exception as e:
            errors.append(f"Field validation error for '{field_name}': {e}")
        
        return errors
    
    def is_valid_email(self, email: str) -> bool:
        """Check if string is a valid email address."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL."""
        import re
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        return bool(re.match(pattern, url))
    
    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string by removing dangerous characters."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Truncate if max_length specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized