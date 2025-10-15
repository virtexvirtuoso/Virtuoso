"""
Base Schema Classes and Utilities
==================================

Provides the foundation for all cache schemas with:
- Automatic serialization/deserialization
- Built-in validation
- Version tracking for migrations
- Type safety via dataclasses
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, Type, TypeVar, ClassVar
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='CacheSchema')


class SchemaVersion(Enum):
    """
    Schema version enumeration for migration support

    When making breaking changes to schemas:
    1. Increment version (e.g., V1 → V2)
    2. Implement migration logic in from_dict()
    3. Update VERSION constant in schema class
    """
    V1 = "1.0"
    V2 = "2.0"  # Reserved for future use


@dataclass
class CacheSchema:
    """
    Base class for all cache schemas

    All cache schemas should inherit from this and define:
    - Fields as dataclass attributes with type hints
    - CACHE_KEY as class constant (the memcached key)
    - VERSION as class constant (for schema evolution)

    Example:
        @dataclass
        class MySchema(CacheSchema):
            CACHE_KEY = "my:cache:key"
            VERSION = SchemaVersion.V1

            my_field: int = 0
            my_value: str = "default"

            def validate(self) -> bool:
                return self.my_field >= 0

    Features:
    - Automatic to_dict() / from_dict() serialization
    - JSON export via to_json() / from_json()
    - Built-in validation framework
    - Version tracking for migrations
    - Comprehensive error logging
    """

    # Metadata fields (automatically populated)
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    version: str = field(default=SchemaVersion.V1.value)

    # Class constants (must be overridden in subclasses)
    # CRITICAL FIX: Use ClassVar to prevent dataclass from treating these as instance fields
    # Without ClassVar, these become instance attributes that shadow class constants in subclasses
    CACHE_KEY: ClassVar[str] = ""
    VERSION: ClassVar[SchemaVersion] = SchemaVersion.V1

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert schema instance to dictionary for cache storage

        Adds metadata fields for version tracking and debugging:
        - __schema_version: Schema version for migration support
        - __cache_key: Validates data came from expected key

        Returns:
            dict: Dictionary representation ready for JSON serialization

        Example:
            schema = MySchema(my_field=42)
            data = schema.to_dict()
            # {'my_field': 42, '__schema_version': '1.0', ...}
        """
        data = asdict(self)
        data['__schema_version'] = self.VERSION.value
        data['__cache_key'] = self.CACHE_KEY
        return data

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create schema instance from cached dictionary

        Handles:
        - Version compatibility checking
        - Metadata field filtering
        - Graceful degradation on errors
        - Missing field defaults

        Args:
            data: Dictionary from cache

        Returns:
            Schema instance with validated data

        Example:
            data = await cache.get('my:cache:key')
            schema = MySchema.from_dict(data)
            if schema.validate():
                print(schema.my_field)
        """
        if not isinstance(data, dict):
            logger.error(f"Cannot create {cls.__name__} from non-dict: {type(data)}")
            return cls()

        # Remove metadata fields
        clean_data = {
            k: v for k, v in data.items()
            if not k.startswith('__')
        }

        # Check version compatibility
        cached_version = data.get('__schema_version', SchemaVersion.V1.value)
        if cached_version != cls.VERSION.value:
            logger.warning(
                f"Schema version mismatch for {cls.__name__}: "
                f"cached={cached_version}, expected={cls.VERSION.value}"
            )
            # TODO: Implement migration logic here when V2 schemas are introduced

        try:
            return cls(**clean_data)
        except TypeError as e:
            logger.error(f"Failed to create {cls.__name__} from dict: {e}")
            logger.debug(f"Data keys: {list(clean_data.keys())}")
            # Return instance with default values
            return cls()

    def validate(self) -> bool:
        """
        Validate schema data integrity

        Override this method in subclasses to add custom validation logic.
        Base implementation checks for None values in required fields.

        Returns:
            bool: True if data is valid, False otherwise

        Example:
            @dataclass
            class MySchema(CacheSchema):
                value: int = 0

                def validate(self) -> bool:
                    if not super().validate():
                        return False
                    return 0 <= self.value <= 100
        """
        import typing

        # Basic validation - ensure no None values for required fields
        for field_name, field_type in self.__annotations__.items():
            # Skip metadata fields
            if field_name in ['timestamp', 'version']:
                continue

            value = getattr(self, field_name, None)

            # Check if field is Optional (Union[X, None])
            is_optional = False
            if hasattr(field_type, '__origin__'):
                # Optional[X] is Union[X, None]
                if field_type.__origin__ is typing.Union:
                    # Check if None is in the union args
                    is_optional = type(None) in field_type.__args__

            # Also check for direct Optional type
            if hasattr(field_type, '__class__') and field_type.__class__.__name__ == '_GenericAlias':
                if str(field_type).startswith('typing.Optional'):
                    is_optional = True

            if value is None and not is_optional:
                logger.error(
                    f"Required field '{field_name}' is None in {self.__class__.__name__}"
                )
                return False

        return True

    def to_json(self) -> str:
        """
        Convert schema to JSON string for cache storage

        Returns:
            str: JSON representation of schema

        Example:
            schema = MySchema(my_field=42)
            json_str = schema.to_json()
            await cache.set('my:key', json_str)
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """
        Create schema from JSON string from cache

        Args:
            json_str: JSON string from cache

        Returns:
            Schema instance

        Example:
            json_str = await cache.get('my:key')
            schema = MySchema.from_json(json_str)
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {cls.__name__}: {e}")
            logger.debug(f"JSON string: {json_str[:200]}")
            return cls()

    def __str__(self) -> str:
        """String representation for debugging"""
        return f"{self.__class__.__name__}({self.CACHE_KEY})"

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"{self.__class__.__name__}(key='{self.CACHE_KEY}', version={self.version})"
