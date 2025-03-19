"""Error management system."""

import logging
import asyncio
from typing import Dict, List, Optional, Type
from datetime import datetime, timedelta
from collections import deque

from .models import ErrorSeverity, ErrorContext, ErrorRecord
from .handlers import SimpleErrorHandler
from .exceptions import MarketMonitorError

logger = logging.getLogger(__name__)

class ErrorManager:
    """Manages error handling and recovery for the system."""
    
    def __init__(
        self,
        max_history_size: int = 1000,
        default_handler: Optional[SimpleErrorHandler] = None
    ):
        self._error_history: deque[ErrorRecord] = deque(maxlen=max_history_size)
        self._error_counts: Dict[Type[Exception], int] = {}
        self._handlers: Dict[ErrorSeverity, List[SimpleErrorHandler]] = {
            severity: [] for severity in ErrorSeverity
        }
        
        # Initialize with default handler if provided
        if default_handler:
            # Register default handler for all severity levels
            for severity in ErrorSeverity:
                self.register_handler(severity, default_handler)
            
        self._lock = asyncio.Lock()
        
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> bool:
        """Handle an error with the registered handlers for its severity level.
        
        Args:
            error: The exception to handle
            context: Error context information
            severity: Error severity level (default: ERROR)
            
        Returns:
            bool: True if error was handled by at least one handler
        """
        async with self._lock:
            # Create error record
            record = ErrorRecord(
                error=error,
                context=context,
                severity=severity
            )
            
            # Update error statistics
            self._error_history.append(record)
            self._error_counts[type(error)] = self._error_counts.get(type(error), 0) + 1
            
            # Handle error with appropriate handlers
            handled = False
            for handler in self._handlers[severity]:
                try:
                    await handler.handle_error(error, str(context))
                    handled = True
                    record.handled = True
                except Exception as e:
                    logger.error(f"Error handler failed: {str(e)}")
                    
            return handled
            
    def register_handler(self, severity: ErrorSeverity, handler: SimpleErrorHandler):
        """Register an error handler for a specific severity level."""
        if handler not in self._handlers[severity]:
            self._handlers[severity].append(handler)
            
    def unregister_handler(self, severity: ErrorSeverity, handler: SimpleErrorHandler):
        """Unregister an error handler from a specific severity level."""
        if handler in self._handlers[severity]:
            self._handlers[severity].remove(handler)
            
    def get_error_count(self, error_type: Optional[Type[Exception]] = None) -> int:
        """Get the count of errors of a specific type or total errors."""
        if error_type is None:
            return sum(self._error_counts.values())
        return self._error_counts.get(error_type, 0)
        
    def get_recent_errors(
        self,
        count: Optional[int] = None,
        severity: Optional[ErrorSeverity] = None,
        error_type: Optional[Type[Exception]] = None
    ) -> List[ErrorRecord]:
        """Get recent errors, optionally filtered by severity and type."""
        errors = list(self._error_history)
        
        if severity is not None:
            errors = [e for e in errors if e.severity == severity]
            
        if error_type is not None:
            errors = [e for e in errors if isinstance(e.error, error_type)]
            
        if count is not None:
            errors = errors[-count:]
            
        return errors
        
    def clear_history(self):
        """Clear error history and counts."""
        self._error_history.clear()
        self._error_counts.clear()
        
    async def __aenter__(self):
        """Context manager support."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Handle errors in context manager."""
        if exc_val is not None:
            context = ErrorContext(
                component="error_manager",
                operation="context_manager",
                stack_trace=''.join(exc_tb.format_stack()) if exc_tb else None
            )
            await self.handle_error(exc_val, context) 