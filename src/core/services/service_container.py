"""
Service Container for managing component lifecycle and dependencies.

This service container eliminates initialization issues by:
1. Managing component creation and lifecycle
2. Handling dependency injection properly  
3. Eliminating redundant component storage
4. Providing clear initialization order
"""

import asyncio
import logging
from typing import Dict, Any, Optional, TypeVar, Type
from dataclasses import dataclass, field
from enum import Enum
import traceback

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceState(Enum):
    """Service lifecycle states"""
    UNINITIALIZED = "uninitialized"
    CREATED = "created"
    CONFIGURED = "configured"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """Information about a registered service"""
    name: str
    instance: Any = None
    state: ServiceState = ServiceState.UNINITIALIZED
    dependencies: list = field(default_factory=list)
    creation_order: int = 0
    error: Optional[str] = None


class ServiceContainer:
    """
    Centralized service container for managing component lifecycle.
    
    Benefits:
    - Eliminates redundant component storage
    - Handles proper dependency injection
    - Manages service lifecycle consistently
    - Provides clear initialization order
    - Reduces circular dependencies
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._creation_counter = 0
        self._initialization_order = []
        self.logger = logging.getLogger(__name__)
        
    def register_service(self, name: str, instance: Any, dependencies: list = None) -> None:
        """Register a service instance with its dependencies"""
        if dependencies is None:
            dependencies = []
            
        self._services[name] = ServiceInfo(
            name=name,
            instance=instance,
            state=ServiceState.CREATED,
            dependencies=dependencies,
            creation_order=self._creation_counter
        )
        self._creation_counter += 1
        self.logger.debug(f"Registered service: {name}")
        
    def get_service(self, name: str) -> Any:
        """Get a service instance by name"""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")
        return self._services[name].instance
        
    def has_service(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services
        
    def get_service_state(self, name: str) -> ServiceState:
        """Get the current state of a service"""
        if name not in self._services:
            return ServiceState.UNINITIALIZED
        return self._services[name].state
        
    def _resolve_initialization_order(self) -> list:
        """Resolve proper initialization order based on dependencies"""
        ordered = []
        resolved = set()
        
        def resolve_service(service_name: str):
            if service_name in resolved:
                return
                
            if service_name not in self._services:
                raise ValueError(f"Service '{service_name}' not registered")
                
            service_info = self._services[service_name]
            
            # Resolve dependencies first
            for dep in service_info.dependencies:
                if dep not in resolved:
                    resolve_service(dep)
                    
            ordered.append(service_name)
            resolved.add(service_name)
            
        # Resolve all services
        for service_name in self._services:
            resolve_service(service_name)
            
        return ordered
        
    async def initialize_all(self) -> bool:
        """Initialize all services in proper dependency order"""
        try:
            self.logger.info("Starting service container initialization...")
            
            # Resolve initialization order
            self._initialization_order = self._resolve_initialization_order()
            self.logger.info(f"Service initialization order: {self._initialization_order}")
            
            # Initialize services in order
            for service_name in self._initialization_order:
                await self._initialize_service(service_name)
                
            self.logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Service initialization failed: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False
            
    async def _initialize_service(self, service_name: str) -> bool:
        """Initialize a single service"""
        try:
            service_info = self._services[service_name]
            instance = service_info.instance
            
            self.logger.debug(f"Initializing service: {service_name}")
            
            # Check if service has async initialize method
            if hasattr(instance, 'initialize') and callable(getattr(instance, 'initialize')):
                if asyncio.iscoroutinefunction(instance.initialize):
                    await instance.initialize()
                else:
                    instance.initialize()
                    
            service_info.state = ServiceState.CONFIGURED
            self.logger.debug(f"✅ Service {service_name} initialized")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize service {service_name}: {str(e)}"
            self.logger.error(error_msg)
            self._services[service_name].state = ServiceState.ERROR
            self._services[service_name].error = error_msg
            raise
            
    async def start_all(self) -> bool:
        """Start all services that have been initialized"""
        try:
            self.logger.info("Starting all services...")
            
            for service_name in self._initialization_order:
                await self._start_service(service_name)
                
            self.logger.info("✅ All services started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Service startup failed: {str(e)}")
            return False
            
    async def _start_service(self, service_name: str) -> bool:
        """Start a single service"""
        try:
            service_info = self._services[service_name]
            instance = service_info.instance
            
            # Check if service has async start method
            if hasattr(instance, 'start') and callable(getattr(instance, 'start')):
                self.logger.debug(f"Starting service: {service_name}")
                
                if asyncio.iscoroutinefunction(instance.start):
                    await instance.start()
                else:
                    instance.start()
                    
                service_info.state = ServiceState.STARTED
                self.logger.debug(f"✅ Service {service_name} started")
            else:
                # Service doesn't have start method, mark as started anyway
                service_info.state = ServiceState.STARTED
                self.logger.debug(f"✅ Service {service_name} (no start method)")
                
            return True
            
        except Exception as e:
            error_msg = f"Failed to start service {service_name}: {str(e)}"
            self.logger.error(error_msg)
            self._services[service_name].state = ServiceState.ERROR
            self._services[service_name].error = error_msg
            raise
            
    async def stop_all(self) -> None:
        """Stop all services in reverse order"""
        try:
            self.logger.info("Stopping all services...")
            
            # Stop in reverse order
            for service_name in reversed(self._initialization_order):
                await self._stop_service(service_name)
                
            self.logger.info("✅ All services stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Service shutdown failed: {str(e)}")
            
    async def _stop_service(self, service_name: str) -> None:
        """Stop a single service"""
        try:
            service_info = self._services[service_name]
            instance = service_info.instance
            
            # Check if service has async stop/cleanup method
            for method_name in ['stop', 'cleanup', 'close']:
                if hasattr(instance, method_name) and callable(getattr(instance, method_name)):
                    method = getattr(instance, method_name)
                    self.logger.debug(f"Stopping service {service_name} using {method_name}")
                    
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    break
                    
            service_info.state = ServiceState.STOPPED
            self.logger.debug(f"✅ Service {service_name} stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {str(e)}")
            self._services[service_name].state = ServiceState.ERROR
            
    def get_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        status = {
            "total_services": len(self._services),
            "initialization_order": self._initialization_order,
            "services": {}
        }
        
        for name, info in self._services.items():
            status["services"][name] = {
                "state": info.state.value,
                "dependencies": info.dependencies,
                "creation_order": info.creation_order,
                "error": info.error
            }
            
        return status
        
    def validate_dependencies(self) -> bool:
        """Validate that all dependencies are satisfied"""
        try:
            self._resolve_initialization_order()
            return True
        except Exception as e:
            self.logger.error(f"Dependency validation failed: {str(e)}")
            return False


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Get the global service container instance"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container


def register_service(name: str, instance: Any, dependencies: list = None) -> None:
    """Register a service with the global container"""
    container = get_service_container()
    container.register_service(name, instance, dependencies)


def get_service(name: str) -> Any:
    """Get a service from the global container"""
    container = get_service_container()
    return container.get_service(name)


def has_service(name: str) -> bool:
    """Check if service exists in global container"""
    container = get_service_container()
    return container.has_service(name) 