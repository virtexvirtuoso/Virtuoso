"""
Event-Driven Architecture Module for Virtuoso Trading System

This module provides the complete event-driven infrastructure including:
- EventBus: Core pub/sub message bus with high performance
- EventPublisher: High-level publishing service with batching
- Event Types: Strongly-typed events for all system components
- Integration Services: Bridges to existing components
- Adapters: Event-driven wrappers for analyzers

The event-driven architecture enables:
- Loose coupling between components
- Better scalability and testability
- Event sourcing for audit trails
- Circuit breaker patterns for resilience
- Performance monitoring and metrics

Usage:
    from src.core.events import EventBus, EventPublisher
    
    # Initialize event infrastructure
    event_bus = EventBus()
    event_publisher = EventPublisher(event_bus)
    
    # Start services
    await event_bus.start()
    await event_publisher.start()
    
    # Subscribe to events
    await event_bus.subscribe(
        "market_data.ohlcv",
        my_handler_function
    )
    
    # Publish events
    await event_publisher.publish_ohlcv_data(
        symbol="BTC/USDT",
        exchange="bybit",
        timeframe="1m",
        candles_data=ohlcv_data
    )
"""

from .event_bus import EventBus, Event, EventPriority, EventHandler, CircuitBreaker
from .event_types import (
    # Base event types
    Event, EventPriority,
    
    # Data type enums
    DataType, AnalysisType, SignalType, AlertSeverity,
    
    # Market data events
    MarketDataUpdatedEvent, OHLCVDataEvent, OrderBookDataEvent,
    TradeDataEvent, LiquidationDataEvent,
    
    # Analysis events
    AnalysisCompletedEvent, TechnicalAnalysisEvent, VolumeAnalysisEvent,
    ConfluenceAnalysisEvent,
    
    # Signal events
    TradingSignalEvent, SignalUpdateEvent,
    
    # Alert events
    SystemAlertEvent, PerformanceAlertEvent, ExchangeAlertEvent,
    
    # System events
    ComponentStatusEvent, CacheEvent, DatabaseEvent,
    
    # Factory functions
    create_market_data_event, create_analysis_event, create_alert_event
)
from .event_publisher import EventPublisher
from .market_data_event_integration import MarketDataEventIntegration
from .confluence_event_adapter import ConfluenceEventAdapter

# Version information
__version__ = "1.0.0"
__author__ = "Virtuoso Team"

# Export all main classes
__all__ = [
    # Core infrastructure
    "EventBus",
    "EventPublisher", 
    "Event",
    "EventPriority",
    "EventHandler",
    "CircuitBreaker",
    
    # Event types
    "DataType",
    "AnalysisType", 
    "SignalType",
    "AlertSeverity",
    
    # Market data events
    "MarketDataUpdatedEvent",
    "OHLCVDataEvent",
    "OrderBookDataEvent", 
    "TradeDataEvent",
    "LiquidationDataEvent",
    
    # Analysis events
    "AnalysisCompletedEvent",
    "TechnicalAnalysisEvent",
    "VolumeAnalysisEvent", 
    "ConfluenceAnalysisEvent",
    
    # Signal events
    "TradingSignalEvent",
    "SignalUpdateEvent",
    
    # Alert events
    "SystemAlertEvent",
    "PerformanceAlertEvent",
    "ExchangeAlertEvent",
    
    # System events
    "ComponentStatusEvent",
    "CacheEvent",
    "DatabaseEvent",
    
    # Factory functions
    "create_market_data_event",
    "create_analysis_event", 
    "create_alert_event",
    
    # Integration services
    "MarketDataEventIntegration",
    "ConfluenceEventAdapter"
]