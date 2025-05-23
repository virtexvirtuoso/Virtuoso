"""Standardized validation types and error handling."""

from enum import Enum
from typing import Dict, Any, Optional, Union, Type, TYPE_CHECKING, List
from datetime import datetime
import pytz

if TYPE_CHECKING:
    from data_processing.market_validator import MarketDataValidator
    from src.monitoring.alert_manager import AlertManager

class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"  # Fail on any validation error
    NORMAL = "normal"  # Allow some non-critical validation errors
    LENIENT = "lenient"  # Only fail on critical validation errors

class DataType(Enum):
    """Types of data that can be validated."""
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    TICKER = "ticker"
    KLINE = "kline"
    ORDERFLOW = "orderflow"
    MARKET = "market"
    SYSTEM = "system"

    @classmethod
    def from_str(cls, value: str) -> 'DataType':
        """Create DataType from string value."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValidationError(
                f"Invalid data type: {value}",
                cls.SYSTEM,
                {'available_types': [t.value for t in cls]}
            )

class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(
        self,
        is_valid: bool,
        data_type: DataType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        """Initialize validation result.
        
        Args:
            is_valid: Whether validation was successful
            data_type: Type of data that was validated
            message: Description of validation result
            details: Additional validation details
            timestamp: When validation occurred
            errors: List of validation errors
            warnings: List of validation warnings
        """
        self.is_valid = is_valid
        self.data_type = data_type
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(pytz.UTC)
        self.errors = errors or []
        self.warnings = warnings or []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary format.
        
        Returns:
            Dictionary containing validation result data
        """
        return {
            'is_valid': self.is_valid,
            'data_type': self.data_type.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'errors': self.errors,
            'warnings': self.warnings
        }
        
    @classmethod
    def success(
        cls,
        data_type: DataType,
        message: str = "Validation successful",
        details: Optional[Dict[str, Any]] = None
    ) -> 'ValidationResult':
        """Create a successful validation result.
        
        Args:
            data_type: Type of validated data
            message: Success message
            details: Additional validation details
            
        Returns:
            ValidationResult indicating success
        """
        return cls(True, data_type, message, details)
        
    @classmethod
    def failure(
        cls,
        data_type: DataType,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> 'ValidationResult':
        """Create a failed validation result.
        
        Args:
            data_type: Type of validated data
            message: Error message
            details: Error details
            
        Returns:
            ValidationResult indicating failure
        """
        return cls(False, data_type, message, details)

class ValidationError(Exception):
    """Base exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        data_type: DataType,
        details: Optional[Dict[str, Any]] = None,
        validation_level: ValidationLevel = ValidationLevel.NORMAL
    ):
        """Initialize validation error.
        
        Args:
            message: Error description
            data_type: Type of data that failed validation
            details: Additional error details
            validation_level: Severity level of the error
        """
        self.message = message
        self.data_type = data_type
        self.details = details or {}
        self.validation_level = validation_level
        self.timestamp = datetime.now(pytz.UTC)
        super().__init__(message)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format.
        
        Returns:
            Dictionary containing error data
        """
        return {
            'message': self.message,
            'data_type': self.data_type.value,
            'details': self.details,
            'validation_level': self.validation_level.value,
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.__class__.__name__
        }
        
    @classmethod
    def from_dict(
        cls: Type['ValidationError'],
        data: Dict[str, Any]
    ) -> Union['ValidationError', 'RequiredFieldError', 'TypeValidationError', 'ConstraintValidationError', 'TimeValidationError', 'DataIntegrityError']:
        """Create validation error from dictionary data.
        
        Args:
            data: Dictionary containing error data
            
        Returns:
            Appropriate validation error instance
        """
        error_type = data.get('error_type', cls.__name__)
        error_classes = {
            'ValidationError': ValidationError,
            'RequiredFieldError': RequiredFieldError,
            'TypeValidationError': TypeValidationError,
            'ConstraintValidationError': ConstraintValidationError,
            'TimeValidationError': TimeValidationError,
            'DataIntegrityError': DataIntegrityError
        }
        
        error_class = error_classes.get(error_type, cls)
        return error_class(
            message=data['message'],
            data_type=DataType(data['data_type']),
            details=data.get('details'),
            validation_level=ValidationLevel(data.get('validation_level', 'normal'))
        )

class RequiredFieldError(ValidationError):
    """Error for missing required fields."""
    pass

class TypeValidationError(ValidationError):
    """Error for incorrect data types."""
    pass

class ConstraintValidationError(ValidationError):
    """Error for failed data constraints."""
    pass

class TimeValidationError(ValidationError):
    """Error for timestamp/time-related validation failures."""
    pass

class DataIntegrityError(ValidationError):
    """Error for data integrity validation failures."""
    pass 