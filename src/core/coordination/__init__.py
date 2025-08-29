"""
Service Coordination Module.

This module provides coordination services for breaking circular dependencies
through event-driven architecture.
"""

from .service_coordinator import (
    ServiceCoordinator,
    Event,
    EventType,
    coordinate_market_analysis,
    coordinate_signal_generation,
    coordinate_alert_dispatch
)

__all__ = [
    'ServiceCoordinator',
    'Event', 
    'EventType',
    'coordinate_market_analysis',
    'coordinate_signal_generation', 
    'coordinate_alert_dispatch'
]