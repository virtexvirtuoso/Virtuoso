"""System management module."""

import logging
from typing import Dict, Any, Optional
import asyncio

class SystemManager:
    """Simple system manager for component lifecycle."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize system manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.components: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        
    async def register_component(self, name: str, component: Any) -> None:
        """Register a component.
        
        Args:
            name: Component name
            component: Component instance
        """
        if name in self.components:
            raise ValueError(f"Component {name} already registered")
        self.components[name] = component
        self.logger.info(f"Registered component: {name}")
        
    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return
            
        try:
            for name, component in self.components.items():
                self.logger.info(f"Initializing {name}")
                if hasattr(component, 'initialize'):
                    await component.initialize()
            self._initialized = True
            self.logger.info("System initialization complete")
        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown all components."""
        for name, component in reversed(list(self.components.items())):
            try:
                if hasattr(component, 'cleanup'):
                    await component.cleanup()
                self.logger.info(f"Cleaned up component: {name}")
            except Exception as e:
                self.logger.error(f"Cleanup failed for {name}: {str(e)}")
                
    async def check_health(self) -> Dict[str, bool]:
        """Check health of all components.
        
        Returns:
            Dictionary mapping component names to health status
        """
        results = {}
        for name, component in self.components.items():
            try:
                is_healthy = await component.is_healthy() if hasattr(component, 'is_healthy') else True
                results[name] = is_healthy
                
                if not is_healthy:
                    self.logger.warning(f"Component {name} is unhealthy")
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {str(e)}")
                results[name] = False
                
        return results
        
    def get_component(self, name: str) -> Optional[Any]:
        """Get a registered component by name.
        
        Args:
            name: Component name
            
        Returns:
            Component instance if found, None otherwise
        """
        return self.components.get(name) 