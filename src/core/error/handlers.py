"""Error handling system."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import ErrorSeverity, ErrorContext, ErrorEvent

@dataclass
class SimpleErrorHandler:
    """Simple implementation of error handling system."""
    
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("SimpleErrorHandler")
    )
    
    # Error event storage
    _error_events: List[ErrorEvent] = field(default_factory=list)
    _error_handlers: Dict[ErrorSeverity, List[Callable[[ErrorEvent], Awaitable[None]]]] = field(
        default_factory=lambda: {severity: [] for severity in ErrorSeverity}
    )
    
    def __post_init__(self):
        """Initialize after creation."""
        self._lock = asyncio.Lock()
    
    async def handle_error(self, error: Exception, context: str, 
                          severity_str: str = "error") -> None:
        """Handle an error event.
        
        Args:
            error: The exception that occurred
            context: Context string (e.g., "initialize_component")
            severity_str: Severity level as string
        """
        # Create error context
        error_context = ErrorContext(
            component=context.split('_')[0],
            operation=context.split('_', 1)[1] if '_' in context else context
        )
        
        # Map severity string to enum
        severity_map = {
            "debug": ErrorSeverity.DEBUG,
            "info": ErrorSeverity.INFO,
            "warning": ErrorSeverity.WARNING,
            "error": ErrorSeverity.ERROR,
            "critical": ErrorSeverity.CRITICAL
        }
        severity = severity_map.get(severity_str.lower(), ErrorSeverity.ERROR)
        
        # Create error event
        event = ErrorEvent(
            error=error,
            context=error_context,
            severity=severity
        )
        
        async with self._lock:
            # Store event
            self._error_events.append(event)
            
            # Log error
            self._log_error(event)
            
            # Call registered handlers
            await self._call_handlers(event)
    
    def _log_error(self, event: ErrorEvent) -> None:
        """Log error event with appropriate severity."""
        log_message = (
            f"Error in {event.context.component}.{event.context.operation}: "
            f"{str(event.error)}"
        )
        
        if event.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif event.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message, exc_info=True)
        elif event.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        elif event.severity == ErrorSeverity.INFO:
            self.logger.info(log_message)
        else:
            self.logger.debug(log_message)
    
    async def _call_handlers(self, event: ErrorEvent) -> None:
        """Call registered error handlers for severity level."""
        handlers = self._error_handlers.get(event.severity, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self.logger.error(f"Error in error handler: {str(e)}")
    
    def register_handler(self, severity: ErrorSeverity, 
                        handler: Callable[[ErrorEvent], Awaitable[None]]) -> None:
        """Register an error handler for a severity level."""
        self._error_handlers[severity].append(handler)
    
    def get_recent_errors(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent error events.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of error events as dictionaries
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            event.to_dict() for event in self._error_events
            if event.timestamp >= cutoff
        ]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        stats = {severity.value: 0 for severity in ErrorSeverity}
        components = {}
        
        for event in self._error_events:
            stats[event.severity.value] += 1
            
            component = event.context.component
            if component not in components:
                components[component] = {
                    'total_errors': 0,
                    'severity_counts': {severity.value: 0 for severity in ErrorSeverity}
                }
            
            components[component]['total_errors'] += 1
            components[component]['severity_counts'][event.severity.value] += 1
        
        return {
            'total_errors': len(self._error_events),
            'severity_counts': stats,
            'component_stats': components
        } 