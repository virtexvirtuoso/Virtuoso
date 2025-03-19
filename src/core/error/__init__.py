"""Error handling system.

This package provides error handling functionality:
- Error models and severity levels
- Error handling and recovery
- Error boundaries for component isolation
- Error context and tracking
"""

from .models import ErrorContext, ErrorSeverity, ErrorRecord
from .exceptions import (
    ComponentError,
    InitializationError,
    DependencyError,
    TemporaryError,
    ResourceLimitError,
    StateError,
    ValidationError
)
from .handlers import SimpleErrorHandler
from .manager import ErrorManager
from .boundary import EnhancedErrorBoundary, ErrorBoundaryConfig

__all__ = [
    'ErrorContext',
    'ErrorSeverity',
    'ErrorRecord',
    'ComponentError',
    'InitializationError',
    'DependencyError',
    'TemporaryError',
    'ResourceLimitError',
    'StateError',
    'ValidationError',
    'SimpleErrorHandler',
    'ErrorManager',
    'EnhancedErrorBoundary',
    'ErrorBoundaryConfig'
] 