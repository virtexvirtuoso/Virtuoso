"""
Signal Processing Interfaces for Breaking Circular Dependencies.

This module defines interfaces for signal processing components to enable
proper dependency inversion and eliminate circular import patterns.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from abc import ABC, abstractmethod
import asyncio


@runtime_checkable
class ISignalProcessor(Protocol):
    """Interface for signal processing services."""
    
    async def process_signal(
        self, 
        signal_data: Dict[str, Any], 
        symbol: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Process a trading signal."""
        ...
    
    async def validate_signal(
        self, 
        signal_data: Dict[str, Any]
    ) -> bool:
        """Validate signal data before processing."""
        ...


@runtime_checkable
class ISignalGenerator(Protocol):
    """Interface for signal generation services."""
    
    async def generate_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a trading signal based on market data and analysis."""
        ...
    
    async def calculate_confluence_score(
        self,
        analysis_data: Dict[str, Any]
    ) -> float:
        """Calculate confluence score from analysis data."""
        ...
    
    def get_signal_thresholds(self) -> Dict[str, float]:
        """Get current signal generation thresholds."""
        ...


@runtime_checkable  
class IAlertService(Protocol):
    """Interface for alert services (already exists, but re-defining for completeness)."""
    
    async def send_alert(
        self, 
        message: str, 
        level: str, 
        context: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send an alert with specified level and context."""
        ...
    
    async def process_signal_alert(
        self,
        signal_data: Dict[str, Any],
        symbol: str
    ) -> bool:
        """Process a signal-specific alert."""
        ...


@runtime_checkable
class IMarketDataProvider(Protocol):
    """Interface for market data provision services."""
    
    async def get_market_data(
        self,
        symbol: str,
        timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get market data for a symbol."""
        ...
    
    async def subscribe_to_updates(
        self,
        symbols: List[str],
        callback: callable
    ) -> None:
        """Subscribe to market data updates."""
        ...


@runtime_checkable
class IMarketAnalyzer(Protocol):
    """Interface for market analysis services."""
    
    async def analyze_market(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze market data and return analysis results."""
        ...
    
    async def calculate_confluence(
        self,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate confluence analysis."""
        ...


# Abstract base classes for more complex interface implementations

class SignalProcessorBase(ABC):
    """Base class for signal processors with common functionality."""
    
    def __init__(self, alert_service: IAlertService):
        self.alert_service = alert_service
    
    @abstractmethod
    async def process_signal(
        self, 
        signal_data: Dict[str, Any], 
        symbol: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Process a trading signal."""
        pass
    
    async def validate_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Default signal validation logic."""
        required_fields = ['symbol', 'signal_type', 'confidence', 'timestamp']
        return all(field in signal_data for field in required_fields)


class MarketAnalyzerBase(ABC):
    """Base class for market analyzers with common functionality."""
    
    def __init__(self, signal_processor: ISignalProcessor):
        self.signal_processor = signal_processor
    
    @abstractmethod
    async def analyze_market(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze market data and return analysis results."""
        pass
    
    async def notify_analysis_complete(
        self,
        symbol: str,
        analysis_result: Dict[str, Any]
    ) -> None:
        """Notify signal processor of completed analysis."""
        if analysis_result.get('signal_data'):
            await self.signal_processor.process_signal(
                analysis_result['signal_data'],
                symbol,
                {'analysis_id': analysis_result.get('analysis_id')}
            )


# Event-based communication interfaces

@runtime_checkable
class IEventPublisher(Protocol):
    """Interface for event publishing."""
    
    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        target_services: Optional[List[str]] = None
    ) -> None:
        """Publish an event to subscribers."""
        ...


@runtime_checkable
class IEventSubscriber(Protocol):
    """Interface for event subscription."""
    
    async def handle_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        source_service: str
    ) -> None:
        """Handle an incoming event."""
        ...
    
    def get_subscribed_events(self) -> List[str]:
        """Get list of event types this subscriber handles."""
        ...


# Service coordination interfaces

@runtime_checkable
class IServiceCoordinator(Protocol):
    """Interface for coordinating between services without direct dependencies."""
    
    async def coordinate_signal_flow(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> None:
        """Coordinate the flow from market data to signal generation to alerts."""
        ...
    
    async def register_service(
        self,
        service_type: str,
        service_instance: Any
    ) -> None:
        """Register a service with the coordinator."""
        ...