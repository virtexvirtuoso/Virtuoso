"""
Service Coordinator for Breaking Circular Dependencies.

This module provides a central coordination service that manages communication
between services without creating direct dependencies between them. It uses
event-driven architecture to eliminate circular imports.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..interfaces.signal_processing import (
    ISignalProcessor, IAlertService, IMarketDataProvider, 
    IEventPublisher, IEventSubscriber
)


class EventType(Enum):
    """Types of events that can flow through the system."""
    MARKET_DATA_UPDATED = "market_data_updated"
    ANALYSIS_COMPLETED = "analysis_completed"  
    SIGNAL_GENERATED = "signal_generated"
    ALERT_TRIGGERED = "alert_triggered"
    METRICS_UPDATED = "metrics_updated"
    HEALTH_CHECK = "health_check"


@dataclass
class Event:
    """Event data structure for service coordination."""
    event_type: EventType
    source_service: str
    target_services: Optional[List[str]]
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: int = 0  # Higher number = higher priority


class ServiceCoordinator:
    """
    Central coordinator for service communication without direct dependencies.
    
    This eliminates circular dependencies by providing an event-driven
    communication mechanism between services.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Service registry
        self._services: Dict[str, Any] = {}
        self._subscribers: Dict[EventType, List[str]] = {}
        self._event_handlers: Dict[str, Callable] = {}
        
        # Event processing
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._stats = {
            'events_processed': 0,
            'events_failed': 0,
            'services_registered': 0,
            'subscribers_count': 0
        }
    
    async def start(self):
        """Start the event processing loop."""
        if self._running:
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        self.logger.info("ServiceCoordinator started")
    
    async def stop(self):
        """Stop the event processing loop."""
        if not self._running:
            return
        
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("ServiceCoordinator stopped")
    
    def register_service(self, service_name: str, service_instance: Any) -> None:
        """Register a service with the coordinator."""
        self._services[service_name] = service_instance
        self._stats['services_registered'] += 1
        
        # Auto-register event handlers if the service implements IEventSubscriber
        if hasattr(service_instance, 'handle_event') and hasattr(service_instance, 'get_subscribed_events'):
            for event_type in service_instance.get_subscribed_events():
                self.subscribe_to_event(service_name, EventType(event_type))
                
        self.logger.info(f"Registered service: {service_name}")
    
    def subscribe_to_event(self, service_name: str, event_type: EventType) -> None:
        """Subscribe a service to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if service_name not in self._subscribers[event_type]:
            self._subscribers[event_type].append(service_name)
            self._stats['subscribers_count'] += 1
            self.logger.debug(f"Service {service_name} subscribed to {event_type.value}")
    
    async def publish_event(self, event: Event) -> None:
        """Publish an event to the coordination system."""
        await self._event_queue.put(event)
        self.logger.debug(f"Event published: {event.event_type.value} from {event.source_service}")
    
    async def coordinate_signal_flow(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """
        Coordinate the complete signal flow from market data to alerts.
        
        This replaces direct dependencies with event-driven coordination.
        """
        correlation_id = f"signal_flow_{symbol}_{datetime.now().timestamp()}"
        
        # Step 1: Publish market data update
        await self.publish_event(Event(
            event_type=EventType.MARKET_DATA_UPDATED,
            source_service="coordinator",
            target_services=["analyzer", "signal_processor"],
            data={
                "symbol": symbol,
                "market_data": market_data,
                "timestamp": datetime.now().isoformat()
            },
            correlation_id=correlation_id
        ))
        
        self.logger.debug(f"Started signal flow coordination for {symbol}")
    
    async def _process_events(self):
        """Event processing loop."""
        while self._running:
            try:
                # Get event with timeout to allow clean shutdown
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                self._stats['events_processed'] += 1
                
            except asyncio.TimeoutError:
                continue  # Normal timeout, continue loop
            except Exception as e:
                self._stats['events_failed'] += 1
                self.logger.error(f"Error processing event: {e}")
    
    async def _handle_event(self, event: Event) -> None:
        """Handle a single event by dispatching to subscribers."""
        subscribers = self._subscribers.get(event.event_type, [])
        
        # If event has target services specified, filter subscribers
        if event.target_services:
            subscribers = [s for s in subscribers if s in event.target_services]
        
        if not subscribers:
            self.logger.debug(f"No subscribers for event: {event.event_type.value}")
            return
        
        # Dispatch to all subscribers concurrently
        tasks = []
        for service_name in subscribers:
            if service_name in self._services:
                service = self._services[service_name]
                if hasattr(service, 'handle_event'):
                    task = asyncio.create_task(
                        self._safe_handle_event(service, event, service_name)
                    )
                    tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_handle_event(self, service: Any, event: Event, service_name: str) -> None:
        """Safely handle event with error handling."""
        try:
            await service.handle_event(event.event_type.value, event.data, event.source_service)
        except Exception as e:
            self.logger.error(f"Error in {service_name} handling {event.event_type.value}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            **self._stats,
            'registered_services': list(self._services.keys()),
            'event_subscriptions': {
                event_type.value: subscribers 
                for event_type, subscribers in self._subscribers.items()
            },
            'is_running': self._running
        }


# Utility functions for common coordination patterns

async def coordinate_market_analysis(
    coordinator: ServiceCoordinator,
    symbol: str,
    market_data: Dict[str, Any]
) -> None:
    """Coordinate market analysis flow without circular dependencies."""
    
    # Trigger analysis
    await coordinator.publish_event(Event(
        event_type=EventType.MARKET_DATA_UPDATED,
        source_service="market_data_provider",
        target_services=["confluence_analyzer"],
        data={
            "symbol": symbol,
            "market_data": market_data,
            "analysis_request": True
        }
    ))


async def coordinate_signal_generation(
    coordinator: ServiceCoordinator,
    symbol: str,
    analysis_result: Dict[str, Any]
) -> None:
    """Coordinate signal generation without direct dependencies."""
    
    # Trigger signal generation
    await coordinator.publish_event(Event(
        event_type=EventType.ANALYSIS_COMPLETED,
        source_service="confluence_analyzer",
        target_services=["signal_generator"],
        data={
            "symbol": symbol,
            "analysis_result": analysis_result,
            "signal_request": True
        }
    ))


async def coordinate_alert_dispatch(
    coordinator: ServiceCoordinator,
    signal_data: Dict[str, Any],
    symbol: str
) -> None:
    """Coordinate alert dispatch without circular dependencies."""
    
    # Trigger alert processing
    await coordinator.publish_event(Event(
        event_type=EventType.SIGNAL_GENERATED,
        source_service="signal_generator", 
        target_services=["alert_manager"],
        data={
            "symbol": symbol,
            "signal_data": signal_data,
            "alert_request": True
        }
    ))