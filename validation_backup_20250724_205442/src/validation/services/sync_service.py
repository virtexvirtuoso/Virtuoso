"""Synchronous validation service."""

import logging
from typing import Dict, Any, Optional, List

from ..core.base import ValidationContext, ValidationResult, ValidationRegistry
from ..core.models import ValidationRule, ValidationLevel
from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class ValidationService:
    """Synchronous validation service."""
    
    def __init__(
        self,
        registry: Optional[ValidationRegistry] = None,
        max_errors: int = 100,
        strict_mode: bool = False
    ):
        """Initialize validation service.
        
        Args:
            registry: Optional validation registry
            max_errors: Maximum number of errors to collect
            strict_mode: Whether to stop on first error
        """
        self._registry = registry or ValidationRegistry()
        self._max_errors = max_errors
        self._strict_mode = strict_mode
        self._rules: Dict[str, List[ValidationRule]] = {}
        
    def add_rule(self, data_type: str, rule: ValidationRule) -> None:
        """Register a validation rule.
        
        Args:
            data_type: Data type to validate
            rule: Validation rule to add
        """
        if data_type not in self._rules:
            self._rules[data_type] = []
        self._rules[data_type].append(rule)
        logger.debug(f"Registered validation rule: {rule.name} for data type {data_type}")
        
    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data with context."""
        result = ValidationResult(success=True)
        
        # Get rules for this context
        rules = self._rules.get(context.data_type, [])
        if not rules:
            return result
            
        # Apply rules in order
        for rule in rules:
            if not rule.active:
                continue
                
            try:
                rule_result = rule.validate(data, context)
                result.errors.extend(rule_result.errors)
                result.warnings.extend(rule_result.warnings)
                
                if len(result.errors) >= self._max_errors:
                    break
                    
                if not rule_result.success and (context.strict_mode or self._strict_mode):
                    break
                    
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {str(e)}")
                result.add_error(f"Rule error: {str(e)}")
                if context.strict_mode or self._strict_mode:
                    break
                    
        return result