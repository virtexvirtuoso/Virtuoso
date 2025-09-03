"""Common type definitions to avoid circular imports."""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, Optional, List, Union, TypeVar, Callable, TYPE_CHECKING
from datetime import datetime
from enum import Enum, auto

if TYPE_CHECKING:
    from monitoring.metrics_manager import MetricsManager
    from monitoring.alert_manager import AlertManager

# Type aliases
ConfigDict = Dict[str, Any]  # Configuration dictionary type
ValidationResult = Dict[str, Any]  # Validation result type
DataDict = Dict[str, Any]  # Generic data dictionary type
TimeseriesData = List[Dict[str, Any]]  # Timeseries data type

# Protocol definitions
class MetricsProtocol(Protocol):
    """Protocol for metrics management."""
    def update_metric(self, name: str, value: float) -> None: ...
    def get_metric(self, name: str) -> Optional[float]: ...
    def reset_metrics(self) -> None: ...

class AlertProtocol(Protocol):
    """Protocol for alert management."""
    async def send_alert(self, message: str, level: str = "info") -> None: ...
    def clear_alerts(self) -> None: ...

# Custom types
T = TypeVar('T')
Validator = Callable[[Any], bool]
Handler = Callable[[Any], None]

# Constants
VALID_INTERVALS = {'1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'W', 'M'}
VALID_TIMEFRAMES = {'1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M'}

class DataType(Enum):
    TICKER = auto()
    ORDERBOOK = auto()
    TRADE = auto()
    KLINE = auto()
    FUNDING = auto()
    LIQUIDATION = auto()

class ValidationLevel(Enum):
    ERROR = auto()
    WARNING = auto()
    INFO = auto()

# Export all types
__all__ = [
    'ConfigDict',
    'ValidationResult',
    'DataDict',
    'TimeseriesData',
    'MetricsProtocol',
    'AlertProtocol',
    'Validator',
    'Handler',
    'DataType',
    'ValidationLevel',
    'VALID_INTERVALS',
    'VALID_TIMEFRAMES'
] 