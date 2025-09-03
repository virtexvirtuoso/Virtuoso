"""
Service Locator Pattern Implementation for Virtuoso.

This module provides a service discovery pattern that allows services to locate
and resolve dependencies without tight coupling to the DI container implementation.
It acts as a bridge between the traditional direct instantiation pattern and
full dependency injection.
"""

from typing import Type, TypeVar, Optional, Dict, Any, Callable, List
import logging
import asyncio
from contextlib import asynccontextmanager
from ..interfaces.services import *
from .container import ServiceContainer

T = TypeVar('T')
logger = logging.getLogger(__name__)


class ServiceLocator:
    """
    Service locator that provides centralized service discovery and resolution.
    
    This class acts as a singleton registry that allows services to locate
    dependencies without needing direct access to the DI container.
    """
    
    _instance: Optional['ServiceLocator'] = None
    _container: Optional[ServiceContainer] = None
    _cache: Dict[Type, Any] = {}
    _resolving: set = set()  # Track services currently being resolved to prevent cycles
    
    def __new__(cls) -> 'ServiceLocator':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, container: ServiceContainer) -> 'ServiceLocator':
        """Initialize the service locator with a DI container."""
        instance = cls()
        instance._container = container
        instance._cache.clear()
        instance._resolving.clear()
        logger.info("ServiceLocator initialized with DI container")
        return instance
    
    @classmethod
    def get_instance(cls) -> Optional['ServiceLocator']:
        """Get the current service locator instance."""
        return cls._instance
    
    async def resolve(self, service_type: Type[T]) -> Optional[T]:
        """
        Resolve a service instance using the DI container with fallback support.
        
        Args:
            service_type: The service type/interface to resolve
            
        Returns:
            Service instance or None if not resolvable
        """
        if not self._container:
            logger.warning("ServiceLocator not initialized with container")
            return None
        
        # Check for circular resolution
        if service_type in self._resolving:
            logger.warning(f"Circular dependency detected for {service_type.__name__}")
            return None
        
        # Check cache first
        if service_type in self._cache:
            return self._cache[service_type]
        
        try:
            self._resolving.add(service_type)
            
            # Try to resolve from DI container
            service = await self._container.get_service(service_type)
            
            # Cache singleton and scoped services
            descriptor = self._container._services.get(service_type)
            if descriptor and descriptor.lifetime.value in ('singleton', 'scoped'):
                self._cache[service_type] = service
            
            logger.debug(f"Resolved service {service_type.__name__} via DI container")
            return service
            
        except Exception as e:
            logger.debug(f"Could not resolve {service_type.__name__} from DI container: {e}")
            
            # Try fallback resolution strategies
            return await self._fallback_resolve(service_type)
            
        finally:
            self._resolving.discard(service_type)
    
    async def _fallback_resolve(self, service_type: Type[T]) -> Optional[T]:
        """
        Fallback resolution strategies when DI container fails.
        
        Args:
            service_type: The service type to resolve
            
        Returns:
            Service instance or None
        """
        try:
            # Strategy 1: Check if it's a concrete class we can instantiate
            if hasattr(service_type, '__init__') and not getattr(service_type, '__abstractmethods__', None):
                try:
                    # Try simple instantiation for classes with no required dependencies
                    import inspect
                    sig = inspect.signature(service_type.__init__)
                    params = [p for name, p in sig.parameters.items() if name != 'self']
                    
                    # Only instantiate if no required parameters or all have defaults
                    if not params or all(p.default != inspect.Parameter.empty for p in params):
                        instance = service_type()
                        logger.info(f"Created {service_type.__name__} via fallback instantiation")
                        return instance
                except Exception as e:
                    logger.debug(f"Could not instantiate {service_type.__name__}: {e}")
            
            # Strategy 2: Look for factory functions or builders
            factory_name = f"create_{service_type.__name__.lower().replace('i', '', 1)}"
            if hasattr(service_type, factory_name):
                factory = getattr(service_type, factory_name)
                if callable(factory):
                    instance = await factory() if asyncio.iscoroutinefunction(factory) else factory()
                    logger.info(f"Created {service_type.__name__} via factory method")
                    return instance
            
            # Strategy 3: Check for known service mappings
            return await self._resolve_known_service(service_type)
            
        except Exception as e:
            logger.debug(f"All fallback strategies failed for {service_type.__name__}: {e}")
            return None
    
    async def _resolve_known_service(self, service_type: Type[T]) -> Optional[T]:
        """
        Resolve known service types using predefined strategies.
        
        Args:
            service_type: The service type to resolve
            
        Returns:
            Service instance or None
        """
        try:
            # Known service type mappings
            if service_type == IConfigService:
                from ...config.manager import ConfigManager
                return ConfigManager()
                
            elif service_type == IValidationService:
                from ...validation import AsyncValidationService
                return AsyncValidationService()
                
            elif service_type == IFormattingService:
                from ...utils.formatters import DataFormatter
                return DataFormatter()
                
            # Add more known mappings as needed
            logger.debug(f"No known mapping for service type: {service_type.__name__}")
            return None
            
        except Exception as e:
            logger.debug(f"Error resolving known service {service_type.__name__}: {e}")
            return None
    
    async def resolve_optional(self, service_type: Type[T]) -> Optional[T]:
        """
        Resolve a service that is optional - returns None if not available.
        
        Args:
            service_type: The service type to resolve
            
        Returns:
            Service instance or None (no exceptions)
        """
        try:
            return await self.resolve(service_type)
        except Exception as e:
            logger.debug(f"Optional service {service_type.__name__} not available: {e}")
            return None
    
    async def resolve_required(self, service_type: Type[T]) -> T:
        """
        Resolve a required service - raises exception if not available.
        
        Args:
            service_type: The service type to resolve
            
        Returns:
            Service instance
            
        Raises:
            ServiceNotAvailableError: If service cannot be resolved
        """
        service = await self.resolve(service_type)
        if service is None:
            raise ServiceNotAvailableError(f"Required service {service_type.__name__} not available")
        return service
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register a service instance directly with the locator.
        
        Args:
            service_type: The service type/interface
            instance: The service instance
        """
        self._cache[service_type] = instance
        logger.debug(f"Registered instance of {service_type.__name__} with ServiceLocator")
    
    def clear_cache(self) -> None:
        """Clear the service cache."""
        self._cache.clear()
        logger.debug("ServiceLocator cache cleared")
    
    def get_cached_services(self) -> List[str]:
        """Get list of currently cached services."""
        return [service_type.__name__ for service_type in self._cache.keys()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service locator statistics."""
        return {
            'initialized': self._container is not None,
            'cached_services': len(self._cache),
            'services': self.get_cached_services(),
            'currently_resolving': [t.__name__ for t in self._resolving]
        }
    
    @asynccontextmanager
    async def scoped_resolution(self, scope_id: str = None):
        """
        Context manager for scoped service resolution.
        
        Args:
            scope_id: Optional scope identifier
        """
        if self._container:
            async with self._container.scope(scope_id) as scope:
                yield scope
        else:
            yield self


class ServiceNotAvailableError(Exception):
    """Raised when a required service cannot be resolved."""
    pass


# Global service locator instance
_service_locator: Optional[ServiceLocator] = None


def get_service_locator() -> Optional[ServiceLocator]:
    """Get the global service locator instance."""
    return ServiceLocator.get_instance()


def initialize_service_locator(container: ServiceContainer) -> ServiceLocator:
    """Initialize the global service locator."""
    global _service_locator
    _service_locator = ServiceLocator.initialize(container)
    return _service_locator


async def resolve_service(service_type: Type[T]) -> Optional[T]:
    """
    Convenience function to resolve a service using the global locator.
    
    Args:
        service_type: The service type to resolve
        
    Returns:
        Service instance or None
    """
    locator = get_service_locator()
    if locator:
        return await locator.resolve(service_type)
    return None


async def resolve_required_service(service_type: Type[T]) -> T:
    """
    Convenience function to resolve a required service using the global locator.
    
    Args:
        service_type: The service type to resolve
        
    Returns:
        Service instance
        
    Raises:
        ServiceNotAvailableError: If service cannot be resolved
    """
    locator = get_service_locator()
    if not locator:
        raise ServiceNotAvailableError("ServiceLocator not initialized")
    return await locator.resolve_required(service_type)


# Convenience functions for common services
async def get_config_service() -> Optional[IConfigService]:
    """Get config service."""
    return await resolve_service(IConfigService)


async def get_alert_service() -> Optional[IAlertService]:
    """Get alert service."""
    return await resolve_service(IAlertService)


async def get_metrics_service() -> Optional[IMetricsService]:
    """Get metrics service."""
    return await resolve_service(IMetricsService)


async def get_market_monitor() -> Optional[IMarketMonitorService]:
    """Get market monitor service."""
    return await resolve_service(IMarketMonitorService)


async def get_dashboard_service() -> Optional[IDashboardService]:
    """Get dashboard service.""" 
    return await resolve_service(IDashboardService)