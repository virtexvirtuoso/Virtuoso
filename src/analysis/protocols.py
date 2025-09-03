"""Analysis module protocols."""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd

class DataProcessorProtocol(Protocol):
    """Protocol for data processing components."""
    
    async def process(self, request: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Process raw market data."""
        ...
        
    async def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate input data."""
        ...

class AlertManagerProtocol(Protocol):
    """Protocol for alert management components."""
    
    async def send_alert(self, 
                        message: str,
                        level: str,
                        context: str,
                        metadata: Dict[str, Any] = None) -> None:
        """Send an alert."""
        ...
    
    async def batch_send(self,
                        alerts: List[Dict[str, Any]]) -> List[bool]:
        """Send multiple alerts in batch."""
        ...

class ValidationProtocol(Protocol):
    """Protocol for validation components."""
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate data against rules."""
        ...
    
    async def validate_async(self, data: Dict[str, Any]) -> List[str]:
        """Validate data asynchronously."""
        ...

class SessionAnalyzerProtocol(Protocol):
    """Protocol for session analysis components."""
    
    async def analyze_session(self, 
                            symbol: str,
                            start_time: datetime,
                            end_time: datetime) -> Dict[str, Any]:
        """Analyze a market session."""
        ...

class MarketAnalyzerProtocol(Protocol):
    """Protocol for market analysis components."""
    
    async def analyze_market_conditions(self,
                                      market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions."""
        ...

class TechnicalAnalyzerProtocol(Protocol):
    """Protocol for technical analysis components."""
    
    async def analyze_technical_indicators(self,
                                         price_data: Dict[str, Any],
                                         volume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze technical indicators."""
        ...

class ResourceManagerProtocol(Protocol):
    """Protocol for resource management."""
    
    async def check_resources(self, component_name: str) -> bool:
        """Check if resources are available."""
        ...
    
    async def allocate(self, 
                      component_name: str,
                      resources: Dict[str, Any]) -> bool:
        """Allocate resources to a component."""
        ...
    
    async def release(self,
                     component_name: str,
                     resource_ids: List[str]) -> None:
        """Release allocated resources."""
        ...

class CacheProtocol(Protocol):
    """Protocol for caching components."""
    
    def get(self, key: str) -> Any:
        """Get cached value."""
        ...
    
    def set(self, 
            key: str,
            value: Any,
            ttl: int = None) -> None:
        """Set cache value."""
        ...
    
    def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        ... 