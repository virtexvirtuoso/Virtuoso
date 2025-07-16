"""Error handling for data acquisition components."""

import logging
import traceback
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from monitoring.alert_manager import AlertManager
    from monitoring.metrics_manager import MetricsManager

from src.core.error.models import ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)

class SimpleErrorHandler:
    """Simple error handler with Discord webhook support."""
    
    def __init__(self, discord_webhook_url: Optional[str] = None):
        """Initialize error handler.
        
        Args:
            discord_webhook_url: Optional Discord webhook URL for error notifications
        """
        self.discord_webhook_url = discord_webhook_url
        self.logger = logging.getLogger(__name__)
        
    async def handle_error(
        self,
        error: Exception,
        context: 'ErrorContext',
        severity: 'ErrorSeverity' = None
    ) -> None:
        """Handle an error.
        
        Args:
            error: The exception that occurred
            context: Error context information
            severity: Error severity level
        """
        try:
            # Log error details
            message = f"Error in {context.component}.{context.operation}: {str(error)}"
            if context.details:
                message += f"\nDetails: {str(context.details)}"
            
            # Add stack trace
            stack_trace = context.stack_trace or "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            full_message = f"{message}\nStack trace:\n{stack_trace}"
            
            # Log based on severity
            if severity == ErrorSeverity.HIGH:
                self.logger.critical(full_message)
            elif severity == ErrorSeverity.MEDIUM:
                self.logger.error(full_message)
            else:
                self.logger.warning(full_message)
                
            # Send Discord notification if configured
            if self.discord_webhook_url:
                await self._send_discord_notification(error, context, severity)
                
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
    async def _send_discord_notification(
        self,
        error: Exception,
        context: 'ErrorContext',
        severity: Optional['ErrorSeverity'] = None
    ) -> None:
        """Send error notification to Discord.
        
        Args:
            error: The exception that occurred
            context: Error context information
            severity: Error severity level
        """
        try:
            # Create error message
            message = f"**{severity.name if severity else 'ERROR'} in {context.component}.{context.operation}**\n"
            message += f"```{str(error)}```\n"
            
            if context.details:
                message += f"**Details:**\n```{str(context.details)}```"
                
            # Send webhook request
            async with aiohttp.ClientSession() as session:
                webhook_data = {
                    'embeds': [{
                        'title': f"{severity.name if severity else 'ERROR'} - {context.component}",
                        'description': message,
                        'color': 0xFF0000 if severity == ErrorSeverity.HIGH else 0xFFA500
                    }]
                }
                async with session.post(self.discord_webhook_url, json=webhook_data) as response:
                    if response.status != 204:
                        self.logger.error(f"Failed to send Discord notification: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending Discord notification: {str(e)}")
            self.logger.debug(traceback.format_exc()) 