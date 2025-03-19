"""Validation management system.

This module provides the ValidationManager class which coordinates validation
operations across the system:
- Managing validators
- Coordinating validation operations
- Caching validation results
- Error handling and reporting
"""

import logging
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass, field
from datetime import datetime

from ..error.manager import ErrorManager
from ..error.models import ErrorSeverity, ErrorContext

from .models import ValidationResult, ValidationError, ValidationLevel
from .context import ValidationContext, ValidationConfig
from .cache import ValidationCache
from .validators import (
    Validator,
    SchemaValidator,
    DataValidator,
    RuleValidator
)

logger = logging.getLogger(__name__)

@dataclass
class ValidationStats:
    """Statistics for validation operations.
    
    Attributes:
        total_validations: Total validation operations
        successful_validations: Successful validations
        failed_validations: Failed validations
        cache_hits: Cache hit count
        cache_misses: Cache miss count
        average_duration: Average validation duration
        error_counts: Count of each error type
    """
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_duration: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=dict)

class ValidationManager:
    """Manages validation operations across the system.
    
    Coordinates validation operations, manages validators, and handles
    caching and error reporting.
    """
    
    def __init__(
        self,
        error_manager: ErrorManager,
        config: Optional[ValidationConfig] = None
    ):
        """Initialize the validation manager.
        
        Args:
            error_manager: System error manager
            config: Optional validation configuration
        """
        self._error_manager = error_manager
        self._config = config or ValidationConfig()
        
        # Initialize components
        self._cache = ValidationCache(
            ttl=self._config.cache_ttl,
            cleanup_interval=60
        )
        
        # Initialize validators
        self._validators: Dict[str, Validator] = {}
        self._schema_validator = SchemaValidator()
        self._data_validator = DataValidator()
        self._rule_validator = RuleValidator()
        
        # Initialize stats
        self._stats = ValidationStats()
        
    async def start(self) -> None:
        """Start the validation manager."""
        await self._cache.start()
        logger.info("Started validation manager")
        
    async def stop(self) -> None:
        """Stop the validation manager."""
        await self._cache.stop()
        logger.info("Stopped validation manager")
        
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
        start_time = datetime.now()
        self._stats.total_validations += 1
        
        try:
            # Check cache if enabled
            if context.should_cache:
                cached = await self._cache.get(context.cache_key, context)
                if cached is not None:
                    self._stats.cache_hits += 1
                    return cached
                self._stats.cache_misses += 1
                
            # Create validation result
            result = ValidationResult(is_valid=True)
            
            # Apply schema validation if available
            schema = await self._schema_validator.get_schema(
                context.data_type,
                context.schema_version
            )
            if schema:
                schema_result = await self._schema_validator.validate_schema(
                    data,
                    schema,
                    context
                )
                result.merge(schema_result)
                
                if not result.is_valid and context.strict_mode:
                    return result
                    
            # Apply data validation
            data_result = await self._data_validator.validate_data(
                data,
                context.data_type,
                context
            )
            result.merge(data_result)
            
            if not result.is_valid and context.strict_mode:
                return result
                
            # Apply custom validators
            for validator_name, validator in self._validators.items():
                custom_result = await validator.validate(data, context)
                result.merge(custom_result)
                
                if not result.is_valid and context.strict_mode:
                    break
                    
            # Update stats
            if result.is_valid:
                self._stats.successful_validations += 1
            else:
                self._stats.failed_validations += 1
                
            # Cache result if appropriate
            if context.should_cache:
                await self._cache.set(context.cache_key, result, context)
                
            # Update timing stats
            duration = (datetime.now() - start_time).total_seconds()
            self._update_timing_stats(duration)
            
            return result
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            self._stats.failed_validations += 1
            
            # Report error
            await self._error_manager.handle_error(
                error=e,
                context=ErrorContext(
                    operation="validation",
                    data_type=context.data_type
                ),
                severity=ErrorSeverity.ERROR
            )
            
            # Return error result
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        code="validation_error",
                        message=str(e),
                        level=ValidationLevel.ERROR
                    )
                ]
            )
            
    def register_validator(
        self,
        name: str,
        validator: Validator
    ) -> None:
        """Register a custom validator.
        
        Args:
            name: Validator name
            validator: Validator instance
        """
        if name in self._validators:
            raise ValueError(f"Validator {name} already registered")
            
        self._validators[name] = validator
        logger.info(f"Registered validator: {name}")
        
    def unregister_validator(self, name: str) -> None:
        """Unregister a custom validator.
        
        Args:
            name: Validator name
        """
        self._validators.pop(name, None)
        logger.info(f"Unregistered validator: {name}")
        
    async def clear_cache(self) -> None:
        """Clear the validation cache."""
        await self._cache.clear()
        
    def _update_timing_stats(self, duration: float) -> None:
        """Update timing statistics.
        
        Args:
            duration: Operation duration in seconds
        """
        if self._stats.total_validations == 1:
            self._stats.average_duration = duration
        else:
            # Running average
            self._stats.average_duration = (
                (self._stats.average_duration * (self._stats.total_validations - 1) +
                 duration) / self._stats.total_validations
            )
            
    @property
    def stats(self) -> ValidationStats:
        """Get validation statistics.
        
        Returns:
            ValidationStats: Current statistics
        """
        return self._stats
        
    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return self._cache.stats 