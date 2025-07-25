# Best Practices Guide

## Overview
This guide documents best practices and patterns established during the class reorganization project. Follow these patterns for consistent, maintainable code.

## Table of Contents
1. [Factory Functions](#factory-functions)
2. [TYPE_CHECKING Pattern](#type-checking-pattern)
3. [Validator Implementation](#validator-implementation)
4. [Error Handling](#error-handling)
5. [Interface Design](#interface-design)
6. [Import Organization](#import-organization)

## Factory Functions

### Purpose
Factory functions create service instances with proper dependency injection and error handling.

### Template Location
`templates/factory_function_template.py`

### Key Principles

1. **Validate Dependencies**
```python
def create_service(container: Container) -> Optional[Service]:
    # Check required dependencies
    config = container.get('ConfigManager')
    if not config:
        logger.error("Missing required dependency: ConfigManager")
        return None
```

2. **Handle Optional Dependencies**
```python
# Optional dependencies don't fail creation
cache = container.get('CacheManager', None)
if cache:
    logger.info("Cache enabled")
else:
    logger.info("Running without cache")
```

3. **Clear Error Messages**
```python
missing_deps = []
if not config:
    missing_deps.append('ConfigManager')
if missing_deps:
    error_msg = f"Missing dependencies: {', '.join(missing_deps)}"
    logger.error(error_msg)
    raise ValueError(error_msg)
```

4. **Graceful Degradation**
```python
try:
    service = create_primary_service(container)
    if service:
        return service
except Exception:
    logger.warning("Using fallback service")
    return FallbackService()
```

## TYPE_CHECKING Pattern

### Purpose
Avoid circular imports while maintaining type safety.

### Template Location
`templates/type_checking_pattern.py`

### Usage

1. **Basic Pattern**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from monitoring.monitor import MarketMonitor
    
class Service:
    def __init__(self):
        self.monitor: Optional['MarketMonitor'] = None
```

2. **Protocol-Based Typing**
```python
from typing import Protocol

class MonitorProtocol(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    
class Service:
    def __init__(self, monitor: MonitorProtocol):
        self.monitor = monitor
```

3. **Optional Dependencies**
```python
try:
    from pandas import DataFrame
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    DataFrame = Any
```

### When to Use
- Circular import prevention
- Optional dependency handling
- Heavy imports only needed for typing
- Cross-package type references

## Validator Implementation

### Purpose
Consistent validation across the codebase.

### Template Location
`templates/validator_implementation_guide.py`

### Structure

1. **Base Class**
```python
from validation.core.base import BaseValidator, ValidationResult

class MyValidator(BaseValidator):
    def validate(self, data: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
        result = ValidationResult()
        # Validation logic
        return result
```

2. **Error Handling**
```python
if not isinstance(data, dict):
    result.add_error(
        ValidationError(
            code='invalid_type',
            message=f"Expected dict, got {type(data).__name__}",
            level=ValidationLevel.ERROR,
            field='_root'
        )
    )
```

3. **Context-Aware Validation**
```python
if context and context.strict_mode:
    level = ValidationLevel.ERROR
else:
    level = ValidationLevel.WARNING
```

4. **Async Validation**
```python
async def validate_async(self, data: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
    result = self.validate(data, context)
    # Additional async checks
    market_data = await self.fetch_market_data()
    # Validate against market data
    return result
```

## Error Handling

### Location
All error classes in `src/core/error/`

### Patterns

1. **Custom Exceptions**
```python
from core.error.exceptions import ValidationError

class ServiceError(Exception):
    """Base exception for service errors"""
    pass

class ConfigurationError(ServiceError):
    """Configuration-related errors"""
    pass
```

2. **Error Context**
```python
from core.error.context import ErrorContext

try:
    # Operation
except Exception as e:
    context = ErrorContext(
        operation='data_processing',
        details={'symbol': symbol, 'timeframe': timeframe}
    )
    logger.error(f"Operation failed: {e}", extra={'context': context})
```

3. **Error Utilities**
```python
from core.error.utils import retry_on_error

@retry_on_error(max_attempts=3, delay=1.0)
async def fetch_data():
    # Automatically retries on failure
    pass
```

## Interface Design

### Location
All interfaces in `src/core/interfaces/`

### Principles

1. **Use Protocols**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ServiceInterface(Protocol):
    def process(self, data: Any) -> Any: ...
    def validate(self, data: Any) -> bool: ...
```

2. **Provide Adapters**
```python
class ServiceAdapter:
    def __init__(self, service: Any):
        self.service = service
        
    def process(self, data: Any) -> Any:
        if hasattr(self.service, 'process'):
            return self.service.process(data)
        elif hasattr(self.service, 'execute'):
            return self.service.execute(data)
```

3. **Clear Contracts**
```python
class DataProcessor(Protocol):
    """Process data according to configuration."""
    
    def process(self, data: Any, config: Dict[str, Any]) -> Any:
        """
        Args:
            data: Input data
            config: Processing configuration
            
        Returns:
            Processed data
            
        Raises:
            ProcessingError: If processing fails
        """
        ...
```

## Import Organization

### Order
1. Standard library imports
2. Third-party imports
3. Local application imports
4. TYPE_CHECKING imports

### Example
```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import pandas as pd
import numpy as np

# Local application
from core.base import BaseService
from validation.core import ValidationResult
from utils.helpers import format_data

# Type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from monitoring.monitor import MarketMonitor
```

### Import Paths
After reorganization:
- Validation: `from validation.core import ...`
- Error handling: `from core.error import ...`
- Interfaces: `from core.interfaces import ...`
- Utils: Only import true utilities from utils

## Summary

These best practices ensure:
1. **Consistency** - Same patterns across codebase
2. **Maintainability** - Easy to understand and modify
3. **Type Safety** - Proper typing without circular imports
4. **Error Resilience** - Graceful handling of failures
5. **Testability** - Easy to mock and test

Always refer to the templates in the `templates/` directory for complete examples.