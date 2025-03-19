"""Validation service module."""

import logging
from typing import Dict, Any, Optional, List, Type
import asyncio

from .base import ValidationContext, ValidationResult, ValidationProvider, ValidationRegistry
from .models import ValidationRule, ValidationLevel, ValidationError
from .validators import Validator

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
        self._registry = registry
        self._max_errors = max_errors
        self._strict_mode = strict_mode
        self._rules: Dict[str, List[ValidationRule]] = {}
        self._validators: Dict[str, Validator] = {}
        
    def register_validator(self, name: str, validator: Validator) -> None:
        """Register a validator.
        
        Args:
            name: Validator name
            validator: Validator instance
        """
        if name in self._validators:
            logger.warning(f"Overwriting existing validator: {name}")
        self._validators[name] = validator
        logger.debug(f"Registered validator: {name}")
        
    def register_rule(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        if rule.name not in self._rules:
            self._rules[rule.name] = []
        self._rules[rule.name].append(rule)
        logger.debug(f"Registered validation rule: {rule.name}")
        
    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data with context."""
        result = ValidationResult(success=True)
        
        # Get validator for this context
        validator = self._validators.get(context.data_type)
        if validator:
            try:
                validator_result = validator.validate(data, context)
                result.errors.extend(validator_result.errors)
                result.warnings.extend(validator_result.warnings)
                
                if not validator_result.success and (context.strict_mode or self._strict_mode):
                    return result
                    
            except Exception as e:
                logger.error(f"Error applying validator {context.data_type}: {str(e)}")
                result.add_error(
                    ValidationError(
                        code="validator_error",
                        message=f"Validator error: {str(e)}",
                        level=ValidationLevel.ERROR
                    )
                )
                if context.strict_mode or self._strict_mode:
                    return result
        
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
                result.add_error(
                    ValidationError(
                        code="rule_error",
                        message=f"Rule error: {str(e)}",
                        level=ValidationLevel.ERROR
                    )
                )
                if context.strict_mode or self._strict_mode:
                    break
                    
        return result

class AsyncValidationService(ValidationProvider):
    """Asynchronous validation service."""
    
    def __init__(
        self,
        registry: Optional[ValidationRegistry] = None,
        max_errors: int = 100,
        strict_mode: bool = False
    ):
        """Initialize async validation service.
        
        Args:
            registry: Optional validation registry
            max_errors: Maximum number of errors to collect
            strict_mode: Whether to stop on first error
        """
        self._registry = registry
        self._max_errors = max_errors
        self._strict_mode = strict_mode
        self._rules: Dict[str, List[ValidationRule]] = {}
        self._validators: Dict[str, Validator] = {}
        
    def register_validator(self, name: str, validator: Validator) -> None:
        """Register a validator.
        
        Args:
            name: Validator name
            validator: Validator instance
        """
        if name in self._validators:
            logger.warning(f"Overwriting existing validator: {name}")
        self._validators[name] = validator
        logger.debug(f"Registered validator: {name}")
        
    def register_rule(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        if rule.name not in self._rules:
            self._rules[rule.name] = []
        self._rules[rule.name].append(rule)
        logger.debug(f"Registered validation rule: {rule.name}")
        
    async def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        """Validate data with context."""
        result = ValidationResult(success=True)
        
        # Get validator for this context
        validator = self._validators.get(context.data_type)
        if validator:
            try:
                validator_result = await validator.validate(data, context)
                result.errors.extend(validator_result.errors)
                result.warnings.extend(validator_result.warnings)
                
                if not validator_result.success and (context.strict_mode or self._strict_mode):
                    return result
                    
            except Exception as e:
                logger.error(f"Error applying validator {context.data_type}: {str(e)}")
                result.add_error(
                    ValidationError(
                        code="validator_error",
                        message=f"Validator error: {str(e)}",
                        level=ValidationLevel.ERROR
                    )
                )
                if context.strict_mode or self._strict_mode:
                    return result
        
        # Get rules for this context
        rules = self._rules.get(context.data_type, [])
        if not rules:
            return result
            
        # Apply rules in order
        for rule in rules:
            if not rule.active:
                continue
                
            try:
                rule_result = await rule.validate(data, context)
                result.errors.extend(rule_result.errors)
                result.warnings.extend(rule_result.warnings)
                
                if len(result.errors) >= self._max_errors:
                    break
                    
                if not rule_result.success and (context.strict_mode or self._strict_mode):
                    break
                    
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {str(e)}")
                result.add_error(
                    ValidationError(
                        code="rule_error",
                        message=f"Rule error: {str(e)}",
                        level=ValidationLevel.ERROR
                    )
                )
                if context.strict_mode or self._strict_mode:
                    break
                    
        return result

    async def validate_batch(self, data: List[Dict]) -> List[Dict]:
        """Return validated market data dictionaries"""
        return [item for item in data if 
                isinstance(item, dict) and 
                'turnover24h' in item and 
                'symbol' in item]

    async def _validate_items(self, data: List[Dict]) -> List[bool]:
        """Validate batch and return boolean statuses"""
        return [await self._validate_item(item) for item in data]

    async def _validate_item(self, item: Dict) -> bool:
        """Validate single market data item"""
        if 'turnover24h' in item:
            try:
                item['turnover24h'] = float(item['turnover24h'])
            except ValueError:
                return False
        return all(await asyncio.gather(
            *[rule.check(item) for rule in self._rules.get(item['symbol'], [])]
        )) 