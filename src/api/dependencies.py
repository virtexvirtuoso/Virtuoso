"""
FastAPI dependency injection helpers for the new DI system.

Provides dependency functions that retrieve services from the DI container
for use in FastAPI routes with proper error handling and fallbacks.
"""

from fastapi import Request, HTTPException, Depends
from typing import Optional, Any
import logging

from ..core.interfaces.services import (
    IAlertService, IMetricsService, IInterpretationService,
    IConfigService, IValidationService, IFormattingService
)
from ..core.di.container import ServiceContainer

logger = logging.getLogger(__name__)


def get_container(request: Request) -> Optional[ServiceContainer]:
    """Get the DI container from FastAPI app state."""
    return getattr(request.app.state, 'container', None)


def get_alert_service(request: Request) -> Optional[IAlertService]:
    """Get alert service from DI container."""
    try:
        container = get_container(request)
        if container:
            # Use asyncio to get the service
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(container.get_service(IAlertService))
            except Exception:
                # Fallback to app state
                return getattr(request.app.state, 'alert_manager', None)
        return getattr(request.app.state, 'alert_manager', None)
    except Exception as e:
        logger.warning(f"Could not get alert service: {e}")
        return getattr(request.app.state, 'alert_manager', None)


def get_metrics_service(request: Request) -> Optional[IMetricsService]:
    """Get metrics service from DI container."""
    try:
        container = get_container(request)
        if container:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(container.get_service(IMetricsService))
            except Exception:
                return getattr(request.app.state, 'metrics_manager', None)
        return getattr(request.app.state, 'metrics_manager', None)
    except Exception as e:
        logger.warning(f"Could not get metrics service: {e}")
        return getattr(request.app.state, 'metrics_manager', None)


def get_config_service(request: Request) -> Optional[IConfigService]:
    """Get config service from DI container."""
    try:
        container = get_container(request)
        if container:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(container.get_service(IConfigService))
            except Exception:
                return getattr(request.app.state, 'config_manager', None)
        return getattr(request.app.state, 'config_manager', None)
    except Exception as e:
        logger.warning(f"Could not get config service: {e}")
        return getattr(request.app.state, 'config_manager', None)


def get_interpretation_service(request: Request) -> Optional[IInterpretationService]:
    """Get interpretation service from DI container."""
    try:
        container = get_container(request)
        if container:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(container.get_service(IInterpretationService))
            except Exception:
                return None
        return None
    except Exception as e:
        logger.warning(f"Could not get interpretation service: {e}")
        return None


def get_validation_service(request: Request) -> Optional[IValidationService]:
    """Get validation service from DI container."""
    try:
        container = get_container(request)
        if container:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(container.get_service(IValidationService))
            except Exception:
                return None
        return None
    except Exception as e:
        logger.warning(f"Could not get validation service: {e}")
        return None


def get_formatting_service(request: Request) -> Optional[IFormattingService]:
    """Get formatting service from DI container."""
    try:
        container = get_container(request)
        if container:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(container.get_service(IFormattingService))
            except Exception:
                return None
        return None
    except Exception as e:
        logger.warning(f"Could not get formatting service: {e}")
        return None


# Legacy compatibility functions
def get_config_manager(request: Request):
    """Legacy compatibility function for config manager."""
    config_service = get_config_service(request)
    if config_service:
        return config_service
    # Fallback to direct app state access
    return getattr(request.app.state, 'config_manager', None)


def get_alert_manager(request: Request):
    """Legacy compatibility function for alert manager."""
    alert_service = get_alert_service(request)
    if alert_service:
        return alert_service
    return getattr(request.app.state, 'alert_manager', None)


def get_metrics_manager(request: Request):
    """Legacy compatibility function for metrics manager."""
    metrics_service = get_metrics_service(request)
    if metrics_service:
        return metrics_service
    return getattr(request.app.state, 'metrics_manager', None)


# Optional dependency functions (don't raise exceptions if not available)
def optional_alert_service(request: Request) -> Optional[IAlertService]:
    """Get optional alert service."""
    return get_alert_service(request)


def optional_metrics_service(request: Request) -> Optional[IMetricsService]:
    """Get optional metrics service."""
    return get_metrics_service(request)


def optional_config_service(request: Request) -> Optional[IConfigService]:
    """Get optional config service."""
    return get_config_service(request)


# Required dependency functions (raise HTTPException if not available)
def required_alert_service(request: Request) -> IAlertService:
    """Get required alert service."""
    service = get_alert_service(request)
    if not service:
        raise HTTPException(status_code=503, detail="Alert service not available")
    return service


def required_metrics_service(request: Request) -> IMetricsService:
    """Get required metrics service."""
    service = get_metrics_service(request)
    if not service:
        raise HTTPException(status_code=503, detail="Metrics service not available")
    return service


def required_config_service(request: Request) -> IConfigService:
    """Get required config service."""
    service = get_config_service(request)
    if not service:
        raise HTTPException(status_code=503, detail="Config service not available")
    return service


# Async versions for async routes
async def get_alert_service_async(request: Request) -> Optional[IAlertService]:
    """Get alert service from DI container (async version)."""
    try:
        container = get_container(request)
        if container:
            try:
                return await container.get_service(IAlertService)
            except Exception:
                return getattr(request.app.state, 'alert_manager', None)
        return getattr(request.app.state, 'alert_manager', None)
    except Exception as e:
        logger.warning(f"Could not get alert service: {e}")
        return getattr(request.app.state, 'alert_manager', None)


async def get_metrics_service_async(request: Request) -> Optional[IMetricsService]:
    """Get metrics service from DI container (async version)."""
    try:
        container = get_container(request)
        if container:
            try:
                return await container.get_service(IMetricsService)
            except Exception:
                return getattr(request.app.state, 'metrics_manager', None)
        return getattr(request.app.state, 'metrics_manager', None)
    except Exception as e:
        logger.warning(f"Could not get metrics service: {e}")
        return getattr(request.app.state, 'metrics_manager', None)


async def get_config_service_async(request: Request) -> Optional[IConfigService]:
    """Get config service from DI container (async version)."""
    try:
        container = get_container(request)
        if container:
            try:
                return await container.get_service(IConfigService)
            except Exception:
                return getattr(request.app.state, 'config_manager', None)
        return getattr(request.app.state, 'config_manager', None)
    except Exception as e:
        logger.warning(f"Could not get config service: {e}")
        return getattr(request.app.state, 'config_manager', None)


# Dependency factory for FastAPI Depends()
AlertServiceDep = Depends(optional_alert_service)
MetricsServiceDep = Depends(optional_metrics_service)
ConfigServiceDep = Depends(optional_config_service)
InterpretationServiceDep = Depends(get_interpretation_service)
ValidationServiceDep = Depends(get_validation_service)
FormattingServiceDep = Depends(get_formatting_service)

# Required dependencies
RequiredAlertServiceDep = Depends(required_alert_service)
RequiredMetricsServiceDep = Depends(required_metrics_service)
RequiredConfigServiceDep = Depends(required_config_service)