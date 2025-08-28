"""
Standardized handler for validation operations.
"""

from .models import ValidationResult

class BaseHandler:
    """Base class for standardized error handling."""
    
    async def handle_error(self, error: Exception, context: str) -> ValidationResult:
        """Handle errors in a standardized way."""
        result = ValidationResult(
            success=False,
            errors=[str(error)],
            warnings=[],
            context=context
        )
        
        if hasattr(self, 'alert_manager'):
            await self.alert_manager.send_alert(
                message=f"{context}: {str(error)}",
                level="error"
            )
            
        if hasattr(self, 'logger'):
            self.logger.error(f"{context}: {str(error)}", exc_info=True)
            
        return result

    def create_validation_result(self, success: bool = True) -> ValidationResult:
        """Create a new validation result."""
        return ValidationResult(
            success=success,
            errors=[],
            warnings=[],
            context=self.__class__.__name__
        ) 