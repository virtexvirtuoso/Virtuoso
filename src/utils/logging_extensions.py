"""
Safe logging extensions without monkey patching.

This module provides logging extensions in a safe, non-invasive way.
"""

import logging
from typing import Any

# Define TRACE level
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, 'TRACE')

class SafeTraceLogger:
    """Safe wrapper for logging with TRACE level."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log message with TRACE level."""
        if self.logger.isEnabledFor(TRACE_LEVEL):
            self.logger._log(TRACE_LEVEL, message, args, **kwargs)
    
    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the wrapped logger."""
        return getattr(self.logger, name)

def get_logger(name: str) -> SafeTraceLogger:
    """Get a logger with TRACE support without monkey patching."""
    return SafeTraceLogger(name) 