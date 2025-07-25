"""
Merged validation module
Merged from: core/validation/startup_validator.py and validation/validators/startup_validator.py
"""

from ..core.base import ValidationResult, ValidationContext
from src.core.error.exceptions import InitializationError as StartupError, ConfigurationError
from src.core.error.handlers import SimpleErrorHandler as ErrorHandler
from src.core.error.models import ErrorSeverity
from src.core.error.context import ErrorContext
from src.core.exchanges.bybit import BybitExchange
from src.data_acquisition.websocket_handler import WebSocketHandler
from src.data_processing.data_manager import DataManager
from src.data_processing.data_processor import DataProcessor
from src.data_storage.database import DatabaseClient
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from typing import Any, Optional, Dict, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from src.monitoring.monitor import MarketMonitor

class StartupSequenceValidator:
    """Validates the startup sequence of the application."""

    def __init__(self, config: Dict[str, Any], app: 'MarketDataApplication', error_handler: ErrorHandler) -> None:
        """Initialize startup sequence validator.
        
        Args:
            config: Configuration dictionary
            app: MarketDataApplication instance
            error_handler: Error handler instance
        """
        self.config = config
        self.app = app
        self.error_handler = error_handler
        self.required_components = {'websocket_handler': WebSocketHandler, 'exchange': BybitExchange, 'data_manager': DataManager, 'data_processor': DataProcessor, 'database_client': DatabaseClient, 'alert_manager': AlertManager, 'metrics_manager': MetricsManager}

    async def validate(self) -> None:
        """Validate the startup sequence."""
        try:
            for component_name, component_class in self.required_components.items():
                if not hasattr(self.app, component_name):
                    raise StartupError(f'Missing required component: {component_name}')
                component = getattr(self.app, component_name)
                if not isinstance(component, component_class):
                    raise StartupError(f'Invalid component type for {component_name}. Expected {component_class.__name__}, got {type(component).__name__}')
            self._validate_config()
            await self._check_dependencies()
            await self._check_resources()
            logger.info('Startup sequence validation completed successfully')
        except Exception as e:
            error_context = ErrorContext(component='startup_validator', operation='validate', details={'error': str(e)})
            await self.error_handler.handle_error(error=e, context=error_context, severity=ErrorSeverity.HIGH)
            raise StartupError(f'Startup validation failed: {str(e)}')

    def _validate_config(self) -> None:
        """Validate configuration."""
        required_sections = ['exchanges', 'market_data', 'database', 'monitoring']
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f'Missing required configuration section: {section}')

    async def _check_dependencies(self) -> None:
        """Check external dependencies."""
        try:
            self.logger.debug('Testing exchange connection...')
            exchange = self.app.exchange
            if not isinstance(exchange, BybitExchange):
                raise StartupError(f'Invalid exchange type: {type(exchange).__name__}')
            if not await exchange.test_connection():
                self.logger.error('Exchange connection test failed')
                raise StartupError('Failed to connect to exchange')
            if not exchange.initialized:
                self.logger.error('Exchange not properly initialized')
                raise StartupError('Exchange not initialized')
            self.logger.info('Exchange connection and initialization verified')
            if not await self.app.database_client.test_connection():
                raise StartupError('Failed to connect to database')
        except Exception as e:
            self.logger.error(f'Dependency check failed: {str(e)}')
            raise StartupError(f'Dependency check failed: {str(e)}')

    async def _check_resources(self) -> None:
        """Check system resources."""
        pass

class StartupValidator:
    """Validates system startup requirements."""

    async def validate(self, data: Any, context: Optional[ValidationContext]=None) -> ValidationResult:
        """Validate startup requirements."""
        result = ValidationResult(success=True)
        return result

def __init__(self, config: Dict[str, Any], app: 'MarketDataApplication', error_handler: ErrorHandler) -> None:
    """Initialize startup sequence validator.
        
        Args:
            config: Configuration dictionary
            app: MarketDataApplication instance
            error_handler: Error handler instance
        """
    self.config = config
    self.app = app
    self.error_handler = error_handler
    self.required_components = {'websocket_handler': WebSocketHandler, 'exchange': BybitExchange, 'data_manager': DataManager, 'data_processor': DataProcessor, 'database_client': DatabaseClient, 'alert_manager': AlertManager, 'metrics_manager': MetricsManager}

def _validate_config(self) -> None:
    """Validate configuration."""
    required_sections = ['exchanges', 'market_data', 'database', 'monitoring']
    for section in required_sections:
        if section not in self.config:
            raise ConfigurationError(f'Missing required configuration section: {section}')
