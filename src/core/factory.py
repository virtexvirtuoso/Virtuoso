"""Component factory module."""

import logging
from typing import Dict, Any, Type, Optional

class ComponentFactory:
    """Simple factory for creating components."""
    
    def __init__(self):
        """Initialize component factory."""
        self.logger = logging.getLogger(__name__)
        self._component_types: Dict[str, Type[Any]] = {}
        
    def register_type(self, name: str, component_type: Type[Any]) -> None:
        """Register a component type.
        
        Args:
            name: Component type name
            component_type: Component class
        """
        self._component_types[name] = component_type
        self.logger.info(f"Registered component type: {name}")
        
    async def create(self, type_name: str, config: Optional[Dict[str, Any]] = None) -> Any:
        """Create a component instance.
        
        Args:
            type_name: Component type name
            config: Optional configuration dictionary
            
        Returns:
            Component instance
            
        Raises:
            ValueError: If component type not registered
        """
        if type_name not in self._component_types:
            raise ValueError(f"Component type not registered: {type_name}")
            
        try:
            component_type = self._component_types[type_name]
            component = component_type(**(config or {}))
            self.logger.info(f"Created component of type: {type_name}")
            return component
        except Exception as e:
            self.logger.error(f"Failed to create component {type_name}: {str(e)}")
            raise 