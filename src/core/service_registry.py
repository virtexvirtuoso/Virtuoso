"""
Service Registry - Shared service instances across the application

This module provides a central registry for shared service instances,
avoiding circular imports and enabling clean dependency access.
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Singleton registry for shared service instances.

    This allows API endpoints and other modules to access services
    without creating circular imports or duplicate instances.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance

    def register(self, name: str, service: any) -> None:
        """Register a service instance."""
        self._services[name] = service
        logger.debug(f"Registered service: {name}")

    def get(self, name: str) -> Optional[any]:
        """Get a service instance by name."""
        return self._services.get(name)

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def clear(self) -> None:
        """Clear all registered services (mainly for testing)."""
        self._services.clear()


# Global registry instance
_registry = ServiceRegistry()


def register_service(name: str, service: any) -> None:
    """Register a service in the global registry."""
    _registry.register(name, service)


def get_service(name: str) -> Optional[any]:
    """Get a service from the global registry."""
    return _registry.get(name)


def has_service(name: str) -> bool:
    """Check if a service exists in the global registry."""
    return _registry.has(name)


# Convenience functions for commonly accessed services

def get_signal_generator():
    """Get the shared SignalGenerator instance."""
    return get_service('signal_generator')


def get_config_manager():
    """Get the shared ConfigManager instance."""
    return get_service('config_manager')


def get_market_data_manager():
    """Get the shared MarketDataManager instance."""
    return get_service('market_data_manager')
