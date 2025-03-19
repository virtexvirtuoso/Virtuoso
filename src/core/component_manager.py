"""Component management system."""

import logging
from typing import Dict, Any, Optional
from asyncio import Lock

class ComponentManager:
    """Simple component lifecycle manager."""
    
    def __init__(self):
        """Initialize component manager."""
        self.components: Dict[str, Any] = {}
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        
    async def register(self, name: str, component: Any) -> None:
        """Register a component.
        
        Args:
            name: Component name
            component: Component instance
        """
        async with self.lock:
            if name in self.components:
                raise ValueError(f"Component {name} already registered")
                
            self.components[name] = component
            self.logger.info(f"Registered component: {name}")
            
    async def initialize(self, name: str) -> None:
        """Initialize a registered component.
        
        Args:
            name: Name of component to initialize
        """
        async with self.lock:
            if name not in self.components:
                raise ValueError(f"Component {name} not registered")
                
            component = self.components[name]
            try:
                if hasattr(component, 'initialize'):
                    await component.initialize()
                self.logger.info(f"Initialized component: {name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize {name}: {str(e)}")
                raise
                
    async def cleanup(self) -> None:
        """Cleanup all registered components."""
        async with self.lock:
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    self.logger.info(f"Cleaned up component: {name}")
                except Exception as e:
                    self.logger.error(f"Cleanup error for {name}: {str(e)}")
                    
    def get_component(self, name: str) -> Optional[Any]:
        """Get a registered component by name."""
        return self.components.get(name)
        
    async def check_health(self, name: str) -> bool:
        """Check health of a component."""
        component = self.get_component(name)
        if not component:
            return False
            
        try:
            if hasattr(component, 'is_healthy'):
                return await component.is_healthy()
            return True
        except Exception as e:
            self.logger.error(f"Health check failed for {name}: {str(e)}")
            return False 