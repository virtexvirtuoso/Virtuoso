"""Error boundary implementation."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .models import ErrorSeverity
from .handlers import SimpleErrorHandler
from .exceptions import (
    InitializationError,
    DependencyError,
    TemporaryError,
    ResourceLimitError
)

@dataclass
class ErrorBoundaryConfig:
    """Configuration for error boundary."""
    max_retries: int = 3
    retry_delay: float = 1.0
    propagate_errors: List[str] = field(default_factory=list)
    handle_locally: List[str] = field(default_factory=list)

@dataclass
class EnhancedErrorBoundary:
    """Enhanced error boundary for component isolation.
    
    Features:
    - Configurable retry behavior
    - Error propagation control
    - Severity determination
    - Detailed error context
    - Async operation support
    """
    
    component_name: str
    error_handler: SimpleErrorHandler
    config: ErrorBoundaryConfig = field(default_factory=ErrorBoundaryConfig)
    
    def should_retry(self, attempt: int) -> bool:
        """Determine if operation should be retried.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            bool: True if should retry, False otherwise
        """
        return attempt < self.config.max_retries
        
    def should_propagate(self, error: Exception) -> bool:
        """Determine if error should be propagated.
        
        Args:
            error: The exception that occurred
            
        Returns:
            bool: True if error should be propagated, False otherwise
        """
        error_name = error.__class__.__name__
        return error_name in self.config.propagate_errors
        
    def _determine_severity(self, error: Exception, attempt: int) -> ErrorSeverity:
        """Determine error severity based on type and attempt count.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            ErrorSeverity: Determined severity level
        """
        if isinstance(error, (InitializationError, DependencyError)):
            return ErrorSeverity.HIGH
            
        if attempt >= self.config.max_retries - 1:
            return ErrorSeverity.HIGH
            
        if isinstance(error, (TemporaryError, ResourceLimitError)):
            return ErrorSeverity.LOW if attempt == 0 else ErrorSeverity.MEDIUM
            
        return ErrorSeverity.MEDIUM 