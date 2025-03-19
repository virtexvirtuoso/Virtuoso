"""Event related models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

from .component import ComponentState

class EventTypes:
    """Event type constants."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    MARKET_UPDATE = "market_update"
    ERROR = "error"
    HEALTH_CHECK = "health_check"
    CLEANUP = "cleanup"
    COMPONENT_INITIALIZED = "component_initialized"
    COMPONENT_ERROR = "component_error"
    CACHE_EVICTION = "cache_eviction"
    STATE_CHANGE = "state_change"

@dataclass
class MarketEvent:
    """Base class for market data events."""
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationEvent:
    """Event for validation results."""
    event_type: str
    symbol: str
    is_valid: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class ProcessingEvent:
    """Event for data processing results."""
    event_type: str
    symbol: str
    operation: str
    success: bool
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

@dataclass
class StateChangeEvent:
    """Event for component state changes."""
    event_type: str
    component: str
    old_state: ComponentState
    new_state: ComponentState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass
class HealthCheckEvent:
    """Event for component health checks."""
    event_type: str
    component: str
    is_healthy: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None 