"""Validation related models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

@dataclass
class ValidationResult:
    """Standardized validation result class."""
    success: bool
    errors: List[str]
    warnings: List[str]
    context: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_error(self, error: str) -> None:
        """Add an error and set success to False."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def add_detail(self, key: str, value: Any) -> None:
        """Add a detail to the result."""
        self.details[key] = value

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

@dataclass
class ValidationMetrics:
    """Metrics for validation operations."""
    
    total_validations: int = 0
    failed_validations: int = 0
    avg_validation_time: float = 0.0
    last_validation: Optional[datetime] = None
    
    def record_validation(self, duration: float, success: bool) -> None:
        """Record validation operation."""
        self.total_validations += 1
        if not success:
            self.failed_validations += 1
        
        self.avg_validation_time = (
            (self.avg_validation_time * (self.total_validations - 1) + duration)
            / self.total_validations
        )
        self.last_validation = datetime.utcnow() 