"""System exception classes."""

class SystemError(Exception):
    """Base class for system errors."""
    pass

class ComponentError(SystemError):
    """Base class for component-related errors."""
    pass

class InitializationError(ComponentError):
    """Error during component initialization."""
    pass

class DependencyError(ComponentError):
    """Error related to component dependencies."""
    pass

class ConfigurationError(SystemError):
    """Error in system configuration."""
    pass

class ResourceError(SystemError):
    """Error related to system resources."""
    pass

class ResourceLimitError(ResourceError):
    """Error when system resource limits are exceeded."""
    pass

class TemporaryError(SystemError):
    """Error that is expected to be temporary and may resolve itself."""
    
    def __init__(self, message: str, retry_after: float = None):
        """Initialize temporary error.
        
        Args:
            message: Error message
            retry_after: Suggested time to wait before retry in seconds
        """
        super().__init__(message)
        self.retry_after = retry_after

class ValidationError(SystemError):
    """Error in data validation."""
    pass

class StateError(ComponentError):
    """Error in component state transitions."""
    pass

class CommunicationError(SystemError):
    """Error in component communication."""
    pass

class OperationError(SystemError):
    """Error during operation execution."""
    pass

class TimeoutError(SystemError):
    """Operation timeout error."""
    pass

class DataError(SystemError):
    """Error in data handling or processing."""
    pass

class SecurityError(SystemError):
    """Security-related error."""
    pass

class MarketMonitorError(ComponentError):
    """Error in market monitoring component."""
    
    def __init__(self, message: str, component: str = None, operation: str = None):
        """Initialize market monitor error.
        
        Args:
            message: Error message
            component: Component name where error occurred
            operation: Operation name where error occurred
        """
        super().__init__(message)
        self.component = component or "market_monitor"
        self.operation = operation 