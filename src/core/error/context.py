"""Canonical ErrorContext definition for the entire system.

This module provides the single source of truth for ErrorContext,
consolidating multiple conflicting definitions into one flexible implementation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import traceback


@dataclass
class ErrorContext:
    """
    Unified error context information.
    
    This class consolidates all ErrorContext definitions in the system.
    It supports both required fields (component, operation) for backward
    compatibility and optional fields for extended functionality.
    
    Args:
        component: The component where the error occurred (required)
        operation: The operation being performed (required)
        timestamp: When the error occurred (auto-generated)
        details: Additional error details
        symbol: Trading symbol if applicable
        exchange: Exchange name if applicable
        user_id: User ID if applicable
        correlation_id: For tracing related errors
        metadata: Flexible metadata storage
        stack_trace: Stack trace (auto-captured if not provided)
    """
    # Required fields for backward compatibility
    component: str
    operation: str
    
    # Auto-generated timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Common optional fields
    details: Dict[str, Any] = field(default_factory=dict)
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization to capture stack trace if not provided."""
        if self.stack_trace is None and self.should_capture_trace():
            self.stack_trace = ''.join(traceback.format_stack()[:-2])
    
    def should_capture_trace(self) -> bool:
        """Determine if stack trace should be auto-captured."""
        # Only capture for errors, not for normal operations
        return 'error' in self.operation.lower() or 'exception' in self.operation.lower()
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add detail to error context."""
        self.details[key] = value
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to error context."""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary."""
        result = {
            'component': self.component,
            'operation': self.operation,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }
        
        # Add optional fields if present
        if self.symbol:
            result['symbol'] = self.symbol
        if self.exchange:
            result['exchange'] = self.exchange
        if self.user_id:
            result['user_id'] = self.user_id
        if self.correlation_id:
            result['correlation_id'] = self.correlation_id
        if self.metadata:
            result['metadata'] = self.metadata
        if self.stack_trace:
            result['stack_trace'] = self.stack_trace
            
        return result
    
    @classmethod
    def from_exception(cls, exception: Exception, component: str, operation: str, **kwargs) -> 'ErrorContext':
        """Create ErrorContext from an exception."""
        context = cls(
            component=component,
            operation=operation,
            **kwargs
        )
        context.add_detail('exception_type', type(exception).__name__)
        context.add_detail('exception_message', str(exception))
        if not context.stack_trace:
            context.stack_trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        return context