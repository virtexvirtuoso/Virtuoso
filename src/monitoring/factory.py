"""Factory for creating monitoring components with proper dependency injection."""

from typing import Dict, Any, Optional, TYPE_CHECKING, Tuple
import logging

if TYPE_CHECKING:
    from .metrics_manager import MetricsManager
    from .alert_manager import AlertManager

logger = logging.getLogger(__name__)

class MonitoringFactory:
    """Factory for creating monitoring components with proper dependency injection."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the factory with configuration.
        
        Args:
            config: Configuration dictionary for all monitoring components
        """
        self.config = config
        self._metrics_manager: Optional['MetricsManager'] = None
        self._alert_manager: Optional['AlertManager'] = None
    
    def get_metrics_manager(self) -> 'MetricsManager':
        """Get or create a MetricsManager instance.
        
        Returns:
            MetricsManager: Singleton metrics manager instance
        """
        if self._metrics_manager is None:
            # Late import to avoid circular dependencies
            from .metrics_manager import MetricsManager
            
            # Create alert manager first if needed
            alert_manager = self.get_alert_manager()
            
            self._metrics_manager = MetricsManager(
                config=self.config,
                alert_manager=alert_manager
            )
        
        return self._metrics_manager
    
    def get_alert_manager(self) -> 'AlertManager':
        """Get or create an AlertManager instance.
        
        Returns:
            AlertManager: Singleton alert manager instance
        """
        if self._alert_manager is None:
            # Late import to avoid circular dependencies
            from .alert_manager import AlertManager
            
            self._alert_manager = AlertManager(
                config=self.config,
                database=self.config.get('database')
            )
        
        return self._alert_manager
    
    def create_data_batcher(self, config: Optional[Dict[str, Any]] = None) -> 'DataBatcher':
        """Create a DataBatcher with proper dependency injection.
        
        Args:
            config: Optional configuration for the data batcher
            
        Returns:
            DataBatcher: Configured data batcher instance
        """
        # Late import to avoid circular dependencies
        from ..data_processing.data_batcher import DataBatcher
        
        metrics_manager = self.get_metrics_manager()
        alert_manager = self.get_alert_manager()
        
        return DataBatcher(
            metrics_manager=metrics_manager,
            alert_manager=alert_manager,
            config=config or self.config
        )
    
    def create_database_client(self, db_url: str, **kwargs) -> 'DatabaseClient':
        """Create a DatabaseClient with proper dependency injection.
        
        Args:
            db_url: Database connection URL
            **kwargs: Additional configuration options
            
        Returns:
            DatabaseClient: Configured database client instance
        """
        # Late import to avoid circular dependencies
        from ..data_storage.database_client import DatabaseClient
        
        metrics_manager = self.get_metrics_manager()
        alert_manager = self.get_alert_manager()
        
        return DatabaseClient(
            metrics_manager=metrics_manager,
            alert_manager=alert_manager,
            db_url=db_url,
            **kwargs
        )
    
    def reset(self) -> None:
        """Reset all singleton instances (useful for testing)."""
        self._metrics_manager = None
        self._alert_manager = None


# Global factory instance for convenience
_global_factory: Optional[MonitoringFactory] = None

def get_global_factory() -> Optional[MonitoringFactory]:
    """Get the global factory instance.
    
    Returns:
        MonitoringFactory: Global factory instance or None if not initialized
    """
    return _global_factory

def initialize_global_factory(config: Dict[str, Any]) -> MonitoringFactory:
    """Initialize the global factory with configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        MonitoringFactory: Initialized global factory
    """
    global _global_factory
    _global_factory = MonitoringFactory(config)
    return _global_factory

def create_monitoring_components(config: Dict[str, Any]) -> Tuple['MetricsManager', 'AlertManager']:
    """Convenience function to create both monitoring components.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        tuple: (MetricsManager, AlertManager) instances
    """
    factory = MonitoringFactory(config)
    return factory.get_metrics_manager(), factory.get_alert_manager() 