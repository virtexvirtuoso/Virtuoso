"""
Dependency Injection system for Virtuoso.

This package provides a comprehensive dependency injection container with:
- Service lifetime management (singleton, transient, scoped)
- Interface-based service registration
- Constructor injection
- Factory-based service creation
- Service scoping and cleanup
"""

from .container import ServiceContainer, ServiceLifetime, ServiceDescriptor, ServiceScope
from .registration import (
    register_core_services, 
    register_analysis_services, 
    register_monitoring_services,
    register_exchange_services,
    register_indicator_services,
    register_api_services,
    bootstrap_container,
    register_with_factory,
    register_conditional
)

__all__ = [
    'ServiceContainer',
    'ServiceLifetime', 
    'ServiceDescriptor',
    'ServiceScope',
    'register_core_services',
    'register_analysis_services',
    'register_monitoring_services',
    'register_exchange_services',
    'register_indicator_services',
    'register_api_services',
    'bootstrap_container',
    'register_with_factory',
    'register_conditional'
]