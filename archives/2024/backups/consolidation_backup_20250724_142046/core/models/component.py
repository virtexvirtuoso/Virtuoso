"""Component related models."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

class ComponentState(Enum):
    """Possible states for system components."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"

@dataclass
class ComponentStatus:
    """Status information for a component."""
    state: ComponentState
    is_healthy: bool
    last_health_check: datetime
    error: Optional[Exception] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class HealthStatus:
    """Health check result for a component."""
    is_healthy: bool
    message: str
    timestamp: datetime
    metrics: Optional[Dict[str, Any]] = None

@dataclass
class ResourceLimits:
    """Resource limits for a component."""
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    max_threads: Optional[int] = None
    max_connections: Optional[int] = None
    max_file_descriptors: Optional[int] = None
    max_queue_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ErrorContext:
    """Context information for error handling."""
    component_name: str
    error_type: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None

@dataclass
class ErrorBoundary:
    """Error boundary configuration for a component."""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    max_errors: int = 10
    error_window_seconds: float = 60.0
    should_propagate: bool = False
    metadata: Optional[Dict[str, Any]] = None 