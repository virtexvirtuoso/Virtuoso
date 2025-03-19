"""Error handling module."""

import logging
from typing import Optional, Any, Callable, List

class CriticalError(Exception):
    """Base class for critical system errors."""
    pass

class ErrorHandler:
    """Simple error handler with logging and critical alerts."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize error handler.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_callbacks: List[Callable[[Exception, str], None]] = []
        
    def add_callback(self, callback: Callable[[Exception, str], None]) -> None:
        """Add error callback."""
        self.error_callbacks.append(callback)
        
    async def handle_error(self, error: Exception, context: str) -> None:
        """Handle an error with logging and callbacks.
        
        Args:
            error: Exception that occurred
            context: String describing where the error occurred
        """
        try:
            # Log the error with full traceback
            self.logger.error(f"{context}: {str(error)}", exc_info=True)
            
            # Execute callbacks
            for callback in self.error_callbacks:
                try:
                    callback(error, context)
                except Exception as e:
                    self.logger.error(f"Error callback failed: {str(e)}")
                    
        except Exception as e:
            # Fallback logging if error handling itself fails
            self.logger.error(f"Error in error handler: {str(e)}", exc_info=True) 