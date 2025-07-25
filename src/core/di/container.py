"""
Enhanced Dependency Injection Container for Virtuoso.

This module provides a comprehensive DI container with service lifetime management,
constructor injection, interface-based registration, and advanced features for
enterprise-grade dependency management.
"""

from typing import Dict, Any, Optional, Type, TypeVar, Generic, Callable, Union, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import inspect
import uuid
import weakref
from contextlib import asynccontextmanager

T = TypeVar('T')

class ServiceLifetime(Enum):
    """Service lifetime options for dependency injection."""
    SINGLETON = "singleton"    # Single instance for entire application
    TRANSIENT = "transient"    # New instance every time
    SCOPED = "scoped"         # Single instance per scope (request/operation)


@dataclass
class ServiceDescriptor:
    """Descriptor for registered services."""
    service_type: Type
    implementation_type: Optional[Type] = None
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    dependencies: Optional[Dict[str, Type]] = None
    
    def __post_init__(self):
        """Analyze dependencies if implementation type is provided."""
        if self.implementation_type and not self.dependencies:
            self.dependencies = self._analyze_dependencies()
    
    def _analyze_dependencies(self) -> Dict[str, Type]:
        """Analyze constructor dependencies using type hints."""
        if not self.implementation_type:
            return {}
            
        try:
            sig = inspect.signature(self.implementation_type.__init__)
            type_hints = get_type_hints(self.implementation_type.__init__)
            dependencies = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                # Get type from hints or annotation
                param_type = type_hints.get(param_name, param.annotation)
                
                if param_type and param_type != inspect.Parameter.empty:
                    dependencies[param_name] = param_type
                    
            return dependencies
        except Exception as e:
            logging.warning(f"Could not analyze dependencies for {self.implementation_type}: {e}")
            return {}


class ServiceContainer:
    """
    Enhanced dependency injection container with service lifetime management.
    
    Features:
    - Service lifetime management (singleton, transient, scoped)
    - Constructor injection with type analysis
    - Interface-based service registration
    - Factory-based service creation
    - Service scoping and cleanup
    - Circular dependency detection
    - Health monitoring and metrics
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._building_stack: set = set()  # For circular dependency detection
        self._health_checks: Dict[Type, Callable] = {}
        self._logger = logging.getLogger(__name__)
        self._stats = {
            'services_registered': 0,
            'instances_created': 0,
            'resolution_calls': 0,
            'errors': 0
        }
    
    # Registration methods
    
    def register_singleton(self, service_type: Type[T], implementation_type: Type[T]) -> 'ServiceContainer':
        """Register a singleton service (single instance for entire application)."""
        return self._register_service(service_type, implementation_type, ServiceLifetime.SINGLETON)
    
    def register_transient(self, service_type: Type[T], implementation_type: Type[T]) -> 'ServiceContainer':
        """Register a transient service (new instance every time)."""
        return self._register_service(service_type, implementation_type, ServiceLifetime.TRANSIENT)
    
    def register_scoped(self, service_type: Type[T], implementation_type: Type[T]) -> 'ServiceContainer':
        """Register a scoped service (single instance per scope)."""
        return self._register_service(service_type, implementation_type, ServiceLifetime.SCOPED)
    
    def register_factory(
        self, 
        service_type: Type[T], 
        factory: Callable[..., Union[T, Callable[[], T]]], 
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    ) -> 'ServiceContainer':
        """Register a service with a factory function."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=None,
            lifetime=lifetime,
            factory=factory
        )
        self._services[service_type] = descriptor
        self._stats['services_registered'] += 1
        self._logger.debug(f"Registered factory for {service_type.__name__} with {lifetime.value} lifetime")
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """Register a pre-created instance as a singleton."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=type(instance),
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance
        )
        self._services[service_type] = descriptor
        self._instances[service_type] = instance
        self._stats['services_registered'] += 1
        self._logger.debug(f"Registered instance for {service_type.__name__}")
        return self
    
    def _register_service(self, service_type: Type[T], implementation_type: Type[T], lifetime: ServiceLifetime) -> 'ServiceContainer':
        """Internal service registration method."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=lifetime
        )
        self._services[service_type] = descriptor
        self._stats['services_registered'] += 1
        self._logger.debug(f"Registered {implementation_type.__name__} for {service_type.__name__} with {lifetime.value} lifetime")
        return self
    
    # Service resolution
    
    async def get_service(self, service_type: Type[T], scope_id: Optional[str] = None) -> T:
        """Get a service instance with proper lifetime management."""
        self._stats['resolution_calls'] += 1
        
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        
        # Circular dependency detection
        if service_type in self._building_stack:
            raise ValueError(f"Circular dependency detected for {service_type.__name__}")
        
        try:
            self._building_stack.add(service_type)
            descriptor = self._services[service_type]
            
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                return await self._get_singleton(service_type, descriptor)
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                return await self._get_scoped(service_type, descriptor, scope_id or "default")
            else:  # TRANSIENT
                return await self._create_instance(descriptor)
                
        except Exception as e:
            self._stats['errors'] += 1
            self._logger.error(f"Error resolving service {service_type.__name__}: {e}")
            raise
        finally:
            self._building_stack.discard(service_type)
    
    async def _get_singleton(self, service_type: Type[T], descriptor: ServiceDescriptor) -> T:
        """Get or create singleton instance."""
        if descriptor.instance:
            return descriptor.instance
            
        if service_type not in self._instances:
            instance = await self._create_instance(descriptor)
            self._instances[service_type] = instance
            descriptor.instance = instance
            self._logger.debug(f"Created singleton instance of {service_type.__name__}")
        
        return self._instances[service_type]
    
    async def _get_scoped(self, service_type: Type[T], descriptor: ServiceDescriptor, scope_id: str) -> T:
        """Get or create scoped instance."""
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}
        
        scope = self._scoped_instances[scope_id]
        if service_type not in scope:
            instance = await self._create_instance(descriptor)
            scope[service_type] = instance
            self._logger.debug(f"Created scoped instance of {service_type.__name__} for scope {scope_id}")
        
        return scope[service_type]
    
    async def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance with dependency injection."""
        self._stats['instances_created'] += 1
        
        if descriptor.factory:
            return await self._call_factory(descriptor.factory)
        elif descriptor.implementation_type:
            return await self._create_from_type(descriptor)
        else:
            raise ValueError(f"No implementation or factory provided for {descriptor.service_type}")
    
    async def _create_from_type(self, descriptor: ServiceDescriptor) -> Any:
        """Create instance using constructor injection."""
        impl_type = descriptor.implementation_type
        
        if not descriptor.dependencies:
            # No dependencies, simple instantiation
            return impl_type()
        
        # Resolve dependencies
        kwargs = {}
        for param_name, param_type in descriptor.dependencies.items():
            if param_type in self._services:
                kwargs[param_name] = await self.get_service(param_type)
            else:
                # Check if parameter has default value
                sig = inspect.signature(impl_type.__init__)
                param = sig.parameters.get(param_name)
                if param and param.default != inspect.Parameter.empty:
                    continue  # Skip, will use default
                else:
                    self._logger.warning(f"No service registered for dependency {param_type.__name__} of {impl_type.__name__}")
        
        return impl_type(**kwargs)
    
    async def _call_factory(self, factory: Callable) -> Any:
        """Call factory function with dependency injection."""
        if asyncio.iscoroutinefunction(factory):
            return await factory()
        else:
            return factory()
    
    # Service scoping
    
    def create_scope(self, scope_id: Optional[str] = None) -> 'ServiceScope':
        """Create a new service scope for scoped service instances."""
        scope_id = scope_id or str(uuid.uuid4())
        return ServiceScope(self, scope_id)
    
    @asynccontextmanager
    async def scope(self, scope_id: Optional[str] = None):
        """Context manager for service scoping."""
        scope = self.create_scope(scope_id)
        try:
            yield scope
        finally:
            await scope.dispose()
    
    # Health and diagnostics
    
    def register_health_check(self, service_type: Type, health_check: Callable[[], bool]) -> 'ServiceContainer':
        """Register a health check for a service."""
        self._health_checks[service_type] = health_check
        return self
    
    async def check_health(self) -> Dict[str, bool]:
        """Check health of all registered services."""
        health_status = {}
        
        for service_type, health_check in self._health_checks.items():
            try:
                if asyncio.iscoroutinefunction(health_check):
                    is_healthy = await health_check()
                else:
                    is_healthy = health_check()
                health_status[service_type.__name__] = is_healthy
            except Exception as e:
                self._logger.error(f"Health check failed for {service_type.__name__}: {e}")
                health_status[service_type.__name__] = False
        
        return health_status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get container statistics."""
        return {
            **self._stats,
            'services_registered_count': len(self._services),
            'singleton_instances': len(self._instances),
            'active_scopes': len(self._scoped_instances)
        }
    
    def get_service_info(self, service_type: Type) -> Optional[Dict[str, Any]]:
        """Get information about a registered service."""
        if service_type not in self._services:
            return None
        
        descriptor = self._services[service_type]
        return {
            'service_type': service_type.__name__,
            'implementation_type': descriptor.implementation_type.__name__ if descriptor.implementation_type else None,
            'lifetime': descriptor.lifetime.value,
            'has_factory': descriptor.factory is not None,
            'dependencies': [dep.__name__ for dep in descriptor.dependencies.values()] if descriptor.dependencies else [],
            'has_instance': descriptor.instance is not None
        }
    
    # Cleanup
    
    def dispose(self):
        """Cleanup container resources."""
        # Dispose singleton instances that support it
        for instance in self._instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    self._logger.error(f"Error disposing instance: {e}")
        
        # Clear all instances and scopes
        self._instances.clear()
        self._scoped_instances.clear()
        self._building_stack.clear()
        
        self._logger.info("Container disposed")


class ServiceScope:
    """
    Service scope for managing scoped service instances.
    
    Provides a context for scoped services that ensures proper cleanup
    when the scope is disposed.
    """
    
    def __init__(self, container: ServiceContainer, scope_id: str):
        self.container = container
        self.scope_id = scope_id
        self._disposed = False
    
    async def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance within this scope."""
        if self._disposed:
            raise RuntimeError("Scope has been disposed")
        return await self.container.get_service(service_type, self.scope_id)
    
    async def dispose(self):
        """Dispose of this scope and cleanup scoped instances."""
        if self._disposed:
            return
        
        if self.scope_id in self.container._scoped_instances:
            # Dispose instances that support it
            for instance in self.container._scoped_instances[self.scope_id].values():
                if hasattr(instance, 'dispose'):
                    try:
                        if asyncio.iscoroutinefunction(instance.dispose):
                            await instance.dispose()
                        else:
                            instance.dispose()
                    except Exception as e:
                        logging.error(f"Error disposing scoped instance: {e}")
            
            # Remove scope
            del self.container._scoped_instances[self.scope_id]
        
        self._disposed = True
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.dispose()