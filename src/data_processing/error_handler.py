"""Error handling for data processing.

This module provides error handling functionality for data processing operations.
"""

import logging
import traceback
from typing import Dict, Any, Optional
import aiohttp
import json

from src.core.error.models import ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)

class SimpleErrorHandler:
    """Simple error handler implementation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def handle_error(
        self, 
        error: Exception, 
        context: Optional[ErrorContext] = None, 
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> None:
        """Handle error with context.
        
        Args:
            error: The error that occurred
            context: Optional error context
            severity: Error severity level
        """
        try:
            # Log error with context if available
            if context:
                self.logger.error(
                    f"Error in {context.component}.{context.operation}: {str(error)}\n"
                    f"Details: {json.dumps(context.details, indent=2)}"
                )
            else:
                self.logger.error(f"Error: {str(error)}")
                
            # Log stack trace for debugging
            self.logger.debug(traceback.format_exc())
            
            # Handle based on severity
            # Convert severity to numeric value for comparison
            severity_levels = {
                ErrorSeverity.DEBUG: 0,
                ErrorSeverity.INFO: 1,
                ErrorSeverity.WARNING: 2,
                ErrorSeverity.ERROR: 3,
                ErrorSeverity.CRITICAL: 4,
                ErrorSeverity.LOW: 1,
                ErrorSeverity.MEDIUM: 2,
                ErrorSeverity.HIGH: 3
            }

            current_level = severity_levels.get(severity, 2)  # Default to MEDIUM
            high_level = severity_levels.get(ErrorSeverity.HIGH, 3)

            if current_level >= high_level:
                # For high severity errors, we might want to:
                # - Send alerts
                # - Stop processing
                # - Trigger recovery procedures
                self.logger.critical(f"High severity error: {str(error)}")
                
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            self.logger.debug(traceback.format_exc()) 