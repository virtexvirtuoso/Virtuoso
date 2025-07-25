"""
Monitoring interfaces for dependency injection and type safety.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional, List, runtime_checkable
from datetime import datetime

@runtime_checkable
class MonitorInterface(Protocol):
    """Interface for monitoring components."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start monitoring."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop monitoring."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status."""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if monitor is running."""
        pass

@runtime_checkable
class AlertInterface(Protocol):
    """Interface for alert systems."""
    
    @abstractmethod
    async def send_alert(self, message: str, level: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Send an alert."""
        pass
    
    @abstractmethod
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        pass
    
    @abstractmethod
    def set_alert_threshold(self, metric: str, threshold: float) -> None:
        """Set alert threshold for a metric."""
        pass

@runtime_checkable
class MetricsInterface(Protocol):
    """Interface for metrics collection."""
    
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        pass
    
    @abstractmethod
    def get_metric(self, name: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get metric data."""
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get all available metric names."""
        pass

@runtime_checkable
class HealthCheckInterface(Protocol):
    """Interface for health check providers."""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Dict with keys:
            - status: 'healthy', 'degraded', or 'unhealthy'
            - message: Human-readable status message
            - details: Additional health details
            - timestamp: Check timestamp
        """
        pass
    
    @abstractmethod
    def get_component_name(self) -> str:
        """Get the name of the component being checked."""
        pass

class MonitoringAdapter:
    """Adapter to make existing monitors compatible with MonitorInterface."""
    
    def __init__(self, monitor: Any):
        self.monitor = monitor
        
    async def start(self) -> None:
        """Start monitoring."""
        if hasattr(self.monitor, 'start'):
            await self.monitor.start()
        elif hasattr(self.monitor, 'run'):
            await self.monitor.run()
            
    async def stop(self) -> None:
        """Stop monitoring."""
        if hasattr(self.monitor, 'stop'):
            await self.monitor.stop()
        elif hasattr(self.monitor, 'shutdown'):
            await self.monitor.shutdown()
            
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status."""
        if hasattr(self.monitor, 'get_status'):
            return self.monitor.get_status()
        elif hasattr(self.monitor, 'status'):
            return {'status': self.monitor.status}
        else:
            return {'status': 'unknown'}
            
    def is_running(self) -> bool:
        """Check if monitor is running."""
        if hasattr(self.monitor, 'is_running'):
            return self.monitor.is_running()
        elif hasattr(self.monitor, 'running'):
            return self.monitor.running
        else:
            return False