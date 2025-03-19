"""Component factory for creating system components."""

import logging
from typing import Dict, Any, Optional, Type

from .lifecycle.states import ComponentState
from .error.exceptions import ComponentCreationError

logger = logging.getLogger(__name__)

@dataclass
class ComponentConfig:
    """Configuration for component creation."""
    name: str
    config: Dict[str, Any]
    dependencies: Dict[str, ComponentProtocol]

class ComponentFactory:
    """Factory for creating system components with proper configuration and dependencies."""
    
    def __init__(self):
        self._component_types: Dict[str, Type[ComponentProtocol]] = {}
        self._component_configs: Dict[str, Dict[str, Any]] = {}
        self._created_components: Dict[str, ComponentProtocol] = {}
        
    def register_type(
        self,
        name: str,
        component_type: Type[ComponentProtocol],
        default_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a component type with optional default configuration."""
        if name in self._component_types:
            raise ComponentCreationError(f"Component type {name} already registered")
            
        self._component_types[name] = component_type
        if default_config:
            self._component_configs[name] = default_config.copy()
            
    def register_config(self, name: str, config: Dict[str, Any]) -> None:
        """Register or update configuration for a component type."""
        if name not in self._component_types:
            raise ComponentCreationError(f"Unknown component type: {name}")
            
        # Merge with existing config if any
        existing_config = self._component_configs.get(name, {})
        merged_config = {**existing_config, **config}
        self._component_configs[name] = merged_config
        
    async def create(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Dict[str, ComponentProtocol]] = None
    ) -> ComponentProtocol:
        """Create a component instance with given configuration and dependencies."""
        try:
            # Check if component type is registered
            if name not in self._component_types:
                raise ComponentCreationError(f"Unknown component type: {name}")
                
            # Get component type and merge configs
            component_type = self._component_types[name]
            merged_config = self._merge_configs(name, config or {})
            
            # Create component configuration
            component_config = ComponentConfig(
                name=name,
                config=merged_config,
                dependencies=dependencies or {}
            )
            
            # Create component instance
            component = component_type(component_config)
            
            # Store created component
            self._created_components[name] = component
            
            logger.info(f"Successfully created component: {name}")
            return component
            
        except Exception as e:
            error_msg = f"Error creating component {name}: {str(e)}"
            logger.error(error_msg)
            raise ComponentCreationError(error_msg) from e
            
    def get_component(self, name: str) -> Optional[ComponentProtocol]:
        """Get a previously created component instance."""
        return self._created_components.get(name)
        
    def _merge_configs(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge default and provided configurations."""
        default_config = self._component_configs.get(name, {})
        return {**default_config, **config}
        
    def _validate_dependencies(
        self,
        name: str,
        dependencies: Dict[str, ComponentProtocol]
    ) -> None:
        """Validate that all required dependencies are provided."""
        component_type = self._component_types[name]
        required_deps = getattr(component_type, 'required_dependencies', set())
        
        missing_deps = required_deps - set(dependencies.keys())
        if missing_deps:
            raise ComponentCreationError(
                f"Missing required dependencies for {name}: {missing_deps}"
            ) 