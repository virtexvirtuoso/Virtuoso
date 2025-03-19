"""Dependency injection container."""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .components.manager import ComponentManager
from .resources.manager import ResourceManager, ResourceLimits
from .error.handlers import ErrorHandler
from .lifecycle.states import ComponentState

@dataclass
class Container:
    """Main dependency injection container."""
    
    settings: Dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("Container")
    )
    
    def __post_init__(self):
        """Initialize container after creation."""
        self._configure_logging()
        self._initialize_core()
    
    def _configure_logging(self) -> None:
        """Configure logging based on settings."""
        log_level = self.settings.get('logging', {}).get('level', 'INFO')
        self.logger.setLevel(log_level)
    
    def _initialize_core(self) -> None:
        """Initialize core components."""
        # Create error handler
        self.error_handler = ErrorHandler()
        
        # Create resource manager
        resource_limits = ResourceLimits(
            max_memory_mb=self.settings.get('resources', {}).get('max_memory_mb', 1024),
            max_concurrent_operations=self.settings.get('resources', {}).get('max_concurrent_ops', 100)
        )
        self.resource_manager = ResourceManager(limits=resource_limits)
        
        # Create component manager
        self.component_manager = ComponentManager(
            settings=self.settings,
            error_handler=self.error_handler,
            resource_manager=self.resource_manager
        )
    
    async def initialize(self) -> None:
        """Initialize all container components."""
        try:
            # Define initialization order
            init_order = [
                'event_bus',
                'validation_cache',
                'data_validator',
                'data_processor',
                'alert_manager'
            ]
            
            # Initialize components
            await self.component_manager.initialize_all(init_order)
            self.logger.info("Container initialization complete")
            
        except Exception as e:
            self.logger.error(f"Container initialization failed: {str(e)}")
            await self.error_handler.handle_error(e, "container_init", "critical")
            raise
    
    async def cleanup(self) -> None:
        """Clean up container resources."""
        try:
            # Define cleanup order (reverse of initialization)
            cleanup_order = [
                'alert_manager',
                'data_processor',
                'data_validator',
                'validation_cache',
                'event_bus'
            ]
            
            # Cleanup components
            await self.component_manager.cleanup_all(cleanup_order)
            self.logger.info("Container cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Container cleanup failed: {str(e)}")
            await self.error_handler.handle_error(e, "container_cleanup", "warning")
            raise
    
    def get_component(self, name: str) -> Optional[Any]:
        """Get a component by name."""
        return self.component_manager.get_component(name)
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get overall system state."""
        return {
            'components': self.component_manager.get_system_state(),
            'resources': self.resource_manager.get_system_stats()
        }