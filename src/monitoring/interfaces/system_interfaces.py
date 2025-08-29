"""
System Interfaces for Monitoring Components.

Clean interfaces for metrics collection, health checking, and WebSocket management.
"""

from typing import Dict, Any, List, Optional, Protocol, runtime_checkable, Callable
from abc import ABC, abstractmethod
from datetime import datetime


@runtime_checkable
class IMetricsCollector(Protocol):
    """
    Interface for collecting metrics.
    
    Single Responsibility: Collect and record system and business metrics.
    """
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a single metric value.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for metric categorization
        """
        ...
    
    def record_counter(self, name: str, increment: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a counter metric.
        
        Args:
            name: Counter name
            increment: Increment value (default 1)
            tags: Optional tags
        """
        ...
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timer metric.
        
        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags
        """
        ...
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics.
        
        Returns:
            Metrics summary
        """
        ...


@runtime_checkable
class IHealthChecker(Protocol):
    """
    Interface for health checking.
    
    Single Responsibility: Check system health and component status.
    """
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health status with structure:
            {
                'status': 'healthy'|'degraded'|'unhealthy',
                'timestamp': str,
                'checks': Dict[str, Any],
                'uptime': float
            }
        """
        ...
    
    async def check_component_health(self, component_name: str) -> Dict[str, Any]:
        """
        Check health of specific component.
        
        Args:
            component_name: Name of component to check
            
        Returns:
            Component health status
        """
        ...
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function.
        
        Args:
            name: Name of the health check
            check_func: Function that returns health status
        """
        ...


@runtime_checkable
class IWebSocketConnectionManager(Protocol):
    """
    Interface for managing WebSocket connections.
    
    Single Responsibility: Manage WebSocket connections and basic message handling.
    """
    
    async def connect(self, url: str) -> bool:
        """
        Connect to WebSocket endpoint.
        
        Args:
            url: WebSocket URL
            
        Returns:
            True if connection successful
        """
        ...
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        ...
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message through WebSocket.
        
        Args:
            message: Message to send
            
        Returns:
            True if message sent successfully
        """
        ...
    
    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected.
        
        Returns:
            True if connected
        """
        ...
    
    def register_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register message handler for incoming messages.
        
        Args:
            handler: Function to handle incoming messages
        """
        ...


# Abstract base classes for concrete implementations

class MetricsCollectorBase(ABC):
    """Base class for metrics collectors with common functionality."""
    
    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger
        self.metrics_store = {}
        self.counters = {}
        self.timers = {}
        self.start_time = datetime.now()
    
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Implement metric recording."""
        pass
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        return datetime.now().timestamp()
    
    def _format_metric_name(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Format metric name with tags."""
        if not tags:
            return name
        tag_string = ','.join(f'{k}={v}' for k, v in tags.items())
        return f'{name}[{tag_string}]'


class HealthCheckerBase(ABC):
    """Base class for health checkers with common functionality."""
    
    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger
        self.health_checks = {}
        self.start_time = datetime.now()
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Implement health checking."""
        pass
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register health check function."""
        self.health_checks[name] = check_func
    
    def _get_uptime(self) -> float:
        """Get uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    async def _run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        for name, check_func in self.health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                results[name] = result
            except Exception as e:
                results[name] = {'status': 'error', 'error': str(e)}
        return results


class WebSocketConnectionManagerBase(ABC):
    """Base class for WebSocket connection managers."""
    
    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger
        self.connection = None
        self.message_handlers = []
        self.connection_url = None
        self._connected = False
    
    @abstractmethod
    async def connect(self, url: str) -> bool:
        """Implement WebSocket connection."""
        pass
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected
    
    def register_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register message handler."""
        self.message_handlers.append(handler)
    
    def _handle_incoming_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming message by calling all handlers."""
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in message handler: {e}")