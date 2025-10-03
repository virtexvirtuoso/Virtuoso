from src.utils.task_tracker import create_tracked_task
"""Component management system."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Type, Set
from dataclasses import dataclass, field
from datetime import datetime

from ..error.handlers import SimpleErrorHandler as ErrorHandler
from ..error.decorators import handle_errors, measure_execution
from ..lifecycle.states import ComponentState
from ..resources.manager import ResourceManager

@dataclass
class ComponentHealth:
    """Component health information."""
    
    state: ComponentState
    last_health_check: datetime
    error_count: int = 0
    memory_usage_mb: float = 0.0
    operation_count: int = 0
    is_healthy: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ComponentManager:
    """Manages component lifecycle and dependencies."""
    
    settings: Dict[str, Any]
    error_handler: ErrorHandler
    resource_manager: ResourceManager
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("ComponentManager")
    )
    
    # Component registry
    _components: Dict[str, Any] = field(default_factory=dict)
    _states: Dict[str, ComponentState] = field(default_factory=dict)
    _dependencies: Dict[str, List[str]] = field(default_factory=dict)
    _health: Dict[str, ComponentHealth] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize after creation."""
        self._component_lock = asyncio.Lock()
        self._health_check_interval = self.settings.get('health_check_interval', 60)
        self._health_check_task = None
        
    async def start_monitoring(self) -> None:
        """Start component monitoring."""
        if self._health_check_task is None:
            self._health_check_task = create_tracked_task(self._monitor_components(), name="auto_tracked_task")
            
    async def stop_monitoring(self) -> None:
        """Stop component monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
    
    @measure_execution(logging.getLogger("ComponentManager"))
    async def _monitor_components(self) -> None:
        """Monitor component health periodically."""
        while True:
            try:
                for name in self._components:
                    await self._check_component_health(name)
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_handler.handle_error(
                    e, "component_manager_monitoring", "error"
                )
                await asyncio.sleep(5)  # Brief delay before retrying
    
    async def _check_component_health(self, name: str) -> None:
        """Check health of a specific component."""
        component = self._components[name]
        health = self._health.get(name) or ComponentHealth(
            state=self._states[name],
            last_health_check=datetime.utcnow()
        )
        
        try:
            # Update resource usage
            stats = self.resource_manager.get_component_stats(name)
            health.memory_usage_mb = stats['memory_usage_mb']
            health.operation_count = stats['operation_count']
            
            # Check component health
            if hasattr(component, 'check_health'):
                health_details = await component.check_health()
                health.details.update(health_details)
            
            # Update state
            health.state = self._states[name]
            health.last_health_check = datetime.utcnow()
            health.is_healthy = (
                health.state == ComponentState.RUNNING and
                health.memory_usage_mb < self.resource_manager.limits.max_memory_mb
            )
            
            self._health[name] = health
            
        except Exception as e:
            health.is_healthy = False
            health.error_count += 1
            await self.error_handler.handle_error(
                e, f"{name}_health_check", "warning"
            )
    
    @handle_errors(error_handler=ErrorHandler(), component="component_manager", severity="error")
    async def register_component(self, name: str, component: Any, 
                               dependencies: Optional[List[str]] = None) -> None:
        """Register a component and its dependencies."""
        async with self._component_lock:
            self._components[name] = component
            self._states[name] = ComponentState.REGISTERED
            if dependencies:
                self._dependencies[name] = dependencies
            self.resource_manager.register_component(name)
            
            # Initialize health tracking
            self._health[name] = ComponentHealth(
                state=ComponentState.REGISTERED,
                last_health_check=datetime.utcnow()
            )
    
    @handle_errors(error_handler=ErrorHandler(), component="component_manager", severity="critical")
    async def initialize_component(self, name: str) -> None:
        """Initialize a component and its dependencies."""
        async with self._component_lock:
            try:
                # Check if already initialized
                if self._states.get(name) == ComponentState.RUNNING:
                    return
                
                # Initialize dependencies first
                for dep in self._dependencies.get(name, []):
                    if self._states.get(dep) != ComponentState.RUNNING:
                        await self.initialize_component(dep)
                
                # Initialize component
                component = self._components[name]
                self._states[name] = ComponentState.INITIALIZING
                
                if hasattr(component, 'initialize'):
                    await component.initialize()
                
                if hasattr(component, 'start'):
                    await component.start()
                
                self._states[name] = ComponentState.RUNNING
                self.logger.info(f"Component {name} initialized successfully")
                
            except Exception as e:
                self._states[name] = ComponentState.ERROR
                self._health[name].error_count += 1
                raise
    
    async def initialize_all(self, init_order: Optional[List[str]] = None) -> None:
        """Initialize all components in specified order."""
        components_to_init = init_order if init_order else list(self._components.keys())
        
        for name in components_to_init:
            await self.initialize_component(name)
        
        # Start monitoring after initialization
        await self.start_monitoring()
    
    @handle_errors(error_handler=ErrorHandler(), component="component_manager", severity="warning")
    async def cleanup_component(self, name: str) -> None:
        """Clean up a component."""
        try:
            component = self._components.get(name)
            if not component:
                return
            
            self._states[name] = ComponentState.STOPPING
            
            if hasattr(component, 'stop'):
                await component.stop()
            
            if hasattr(component, 'cleanup'):
                await component.cleanup()
            
            self._states[name] = ComponentState.STOPPED
            self.resource_manager.unregister_component(name)
            
        except Exception as e:
            self._states[name] = ComponentState.ERROR
            self._health[name].error_count += 1
            raise
    
    async def cleanup_all(self, cleanup_order: Optional[List[str]] = None) -> None:
        """Clean up all components in specified order."""
        # Stop monitoring first
        await self.stop_monitoring()
        
        components_to_cleanup = cleanup_order if cleanup_order else reversed(list(self._components.keys()))
        
        for name in components_to_cleanup:
            await self.cleanup_component(name)
    
    def get_component(self, name: str) -> Optional[Any]:
        """Get a component by name."""
        return self._components.get(name)
    
    def get_component_state(self, name: str) -> Optional[ComponentState]:
        """Get the state of a component."""
        return self._states.get(name)
    
    def get_component_health(self, name: str) -> Optional[ComponentHealth]:
        """Get health information for a component."""
        return self._health.get(name)
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get overall system state."""
        return {
            'components': {
                name: {
                    'state': state.name,
                    'health': self._health[name].is_healthy,
                    'error_count': self._health[name].error_count,
                    'memory_usage_mb': self._health[name].memory_usage_mb,
                    'operation_count': self._health[name].operation_count,
                    'last_health_check': self._health[name].last_health_check.isoformat(),
                    'details': self._health[name].details
                } for name, state in self._states.items()
            },
            'resources': self.resource_manager.get_system_stats()
        } 