"""Validation context management.

This module provides classes for managing validation context:
- ValidationConfig: Configuration for validation operations
- ValidationContext: Context for validation operations
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import timedelta

@dataclass
class ValidationConfig:
    """Configuration for validation operations.
    
    Attributes:
        strict_mode: Whether to stop on first error
        cache_ttl: Cache time-to-live
        max_errors: Maximum errors before stopping
        max_warnings: Maximum warnings before stopping
        default_level: Default validation level
        async_validation: Whether to run validations async
        validation_timeout: Timeout for validation operations
    """
    strict_mode: bool = False
    cache_ttl: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    max_errors: Optional[int] = None
    max_warnings: Optional[int] = None
    default_level: str = "error"
    async_validation: bool = True
    validation_timeout: timedelta = field(
        default_factory=lambda: timedelta(seconds=30)
    )

@dataclass
class ValidationContext:
    """Context for validation operations.
    
    Attributes:
        data_type: Type of data being validated
        schema_version: Optional schema version
        config: Validation configuration
        metadata: Additional context metadata
        parent_context: Optional parent context
        should_cache: Whether to cache results
        cache_key: Optional cache key
        validation_chain: Chain of validation operations
    """
    data_type: str
    schema_version: Optional[str] = None
    config: ValidationConfig = field(default_factory=ValidationConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_context: Optional['ValidationContext'] = None
    should_cache: bool = True
    cache_key: Optional[str] = None
    validation_chain: List[str] = field(default_factory=list)
    
    DATA_TYPES = [
        'market_data',
        'symbol_data', 
        'analysis_integration',
        'trade',
        'ticker'
    ]
    
    def __post_init__(self):
        """Post-initialization setup."""
        if not self.cache_key and self.should_cache:
            self.cache_key = self._generate_cache_key()
            
    def create_child_context(
        self,
        data_type: Optional[str] = None,
        **kwargs
    ) -> 'ValidationContext':
        """Create a child validation context.
        
        Args:
            data_type: Optional override for data type
            **kwargs: Additional context attributes
            
        Returns:
            ValidationContext: New child context
        """
        child_context = ValidationContext(
            data_type=data_type or self.data_type,
            schema_version=self.schema_version,
            config=self.config,
            parent_context=self,
            should_cache=self.should_cache,
            validation_chain=self.validation_chain.copy()
        )
        
        # Copy metadata
        child_context.metadata = self.metadata.copy()
        child_context.metadata.update(kwargs)
        
        return child_context
        
    def _generate_cache_key(self) -> str:
        """Generate cache key for context.
        
        Returns:
            str: Generated cache key
        """
        components = [
            self.data_type,
            self.schema_version or "no_schema",
            str(hash(frozenset(self.metadata.items())))
        ]
        return ":".join(components)
        
    @property
    def strict_mode(self) -> bool:
        """Whether strict validation is enabled.
        
        Returns:
            bool: True if strict mode
        """
        return self.config.strict_mode
        
    @property
    def validation_timeout(self) -> timedelta:
        """Get validation timeout.
        
        Returns:
            timedelta: Validation timeout
        """
        return self.config.validation_timeout
        
    @property
    def max_errors(self) -> Optional[int]:
        """Get maximum allowed errors.
        
        Returns:
            Optional[int]: Max errors or None
        """
        return self.config.max_errors
        
    @property
    def max_warnings(self) -> Optional[int]:
        """Get maximum allowed warnings.
        
        Returns:
            Optional[int]: Max warnings or None
        """
        return self.config.max_warnings
        
    def __str__(self) -> str:
        """Get string representation.
        
        Returns:
            str: String representation
        """
        return (
            f"ValidationContext(type={self.data_type}, "
            f"schema={self.schema_version or 'none'}, "
            f"strict={self.strict_mode})"
        ) 