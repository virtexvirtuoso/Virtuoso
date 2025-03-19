from typing import Dict, Set, List, Optional, Type, Awaitable, Callable
from dataclasses import dataclass
import asyncio
from enum import Enum
import logging

from .protocols import ComponentProtocol, HealthStatus
from .models.component import ComponentState

logger = logging.getLogger(__name__)

class ComponentType(Enum):
    CORE = "core"
    DATA = "data"
    ANALYSIS = "analysis"
    MONITORING = "monitoring"
    TRADING = "trading"

@dataclass
class ComponentMetadata:
    """Metadata for registered components."""
    name: str
    type: ComponentType
    dependencies: Set[str]
    priority: int
    is_required: bool
    startup_timeout: float
    shutdown_timeout: float
    health_check_interval: float

class ComponentRegistry:
    """Enhanced component registry with dependency management."""
    
    def __init__(self):
        self._components: Dict[str, ComponentProtocol] = {}
        self._metadata: Dict[str, ComponentMetadata] = {}
        self._initialized: Set[str] = set()
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
        self._locks: Dict[str, asyncio.Lock] = {}
        
    async def register(
        self,
        name: str,
        component: ComponentProtocol,
        metadata: ComponentMetadata
    ) -> None:
        """Register a component with metadata."""
        if name in self._components:
            raise ValueError(f"Component {name} already registered")
            
        self._components[name] = component
        self._metadata[name] = metadata
        self._locks[name] = asyncio.Lock()
        
        # Update dependency order
        self._update_dependency_order()
        
    async def initialize_all(self, timeout: Optional[float] = None) -> bool:
        """Initialize all components in dependency order."""
        try:
            for component_name in self._startup_order:
                metadata = self._metadata[component_name]
                component = self._components[component_name]
                
                # Check dependencies
                if not await self._check_dependencies(component_name):
                    raise RuntimeError(f"Dependencies not met for {component_name}")
                
                # Initialize with timeout
                try:
                    async with asyncio.timeout(metadata.startup_timeout):
                        await component.initialize()
                    self._initialized.add(component_name)
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Initialization timeout for {component_name}")
                
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            return False
            
    async def shutdown_all(self) -> None:
        """Shutdown all components in reverse dependency order."""
        for component_name in reversed(self._shutdown_order):
            try:
                component = self._components[component_name]
                metadata = self._metadata[component_name]
                
                async with asyncio.timeout(metadata.shutdown_timeout):
                    await component.cleanup()
                    
            except Exception as e:
                logger.error(f"Error shutting down {component_name}: {str(e)}")
                
    async def get_component(self, name: str) -> Optional[ComponentProtocol]:
        """Get a registered component by name."""
        return self._components.get(name)
        
    async def check_health(self) -> Dict[str, HealthStatus]:
        """Check health of all components."""
        results = {}
        for name, component in self._components.items():
            try:
                results[name] = await component.is_healthy()
            except Exception as e:
                results[name] = HealthStatus(
                    is_healthy=False,
                    message=f"Health check failed: {str(e)}"
                )
        return results
        
    def _update_dependency_order(self) -> None:
        """Update component initialization and shutdown order based on dependencies."""
        # Build dependency graph
        graph = {name: meta.dependencies for name, meta in self._metadata.items()}
        
        # Topological sort for startup order
        self._startup_order = self._topological_sort(graph)
        
        # Reverse for shutdown
        self._shutdown_order = list(reversed(self._startup_order))
        
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """Perform topological sort of components."""
        result = []
        visited = set()
        
        def visit(node: str):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, set()):
                visit(dep)
            result.append(node)
            
        for node in graph:
            visit(node)
            
        return result
        
    async def _check_dependencies(self, component_name: str) -> bool:
        """Check if all dependencies for a component are initialized."""
        metadata = self._metadata[component_name]
        return all(dep in self._initialized for dep in metadata.dependencies) 