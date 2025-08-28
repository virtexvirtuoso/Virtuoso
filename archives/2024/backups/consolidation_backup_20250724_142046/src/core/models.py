"""Core data models for market data processing."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum, auto

class ComponentState(Enum):
    """Component lifecycle states."""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    ERROR = auto()
    STOPPED = auto()

class ErrorSeverity(Enum):
    """Standard error severity levels."""
    CRITICAL = auto()  # System cannot continue, immediate attention required
    HIGH = auto()      # Major component failure, system degraded
    MEDIUM = auto()    # Component issue, functionality impaired
    LOW = auto()       # Minor issue, system functioning
    INFO = auto()      # Informational only

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
class ComponentStatus:
    """Component status information."""
    state: ComponentState
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    last_updated: Optional[float] = None

@dataclass
class ErrorContext:
    """Error context information."""
    component: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add detail to error context."""
        self.details[key] = value

@dataclass
class ResourceLimits:
    """Component resource limits."""
    max_memory_mb: int = 1024
    max_concurrent_operations: int = 100
    operation_timeout_seconds: float = 30.0
    
    def validate_limits(self, current_memory: int, current_operations: int) -> bool:
        """Validate current resource usage against limits."""
        return (
            current_memory <= self.max_memory_mb and
            current_operations <= self.max_concurrent_operations
        )

@dataclass
class CacheConfig:
    """Cache configuration settings."""
    cache_type: str = "memory"
    max_size: int = 10000
    eviction_strategy: str = "lru"
    ttl: Optional[int] = None
    cleanup_interval: int = 300
    
    def validate(self) -> List[str]:
        """Validate cache configuration."""
        errors = []
        if self.max_size <= 0:
            errors.append("max_size must be positive")
        if self.cleanup_interval <= 0:
            errors.append("cleanup_interval must be positive")
        if self.eviction_strategy not in ["lru", "lfu", "fifo"]:
            errors.append("invalid eviction_strategy")
        return errors

@dataclass
class ErrorBoundary:
    """Defines error handling boundaries."""
    
    max_retries: int = 3
    retry_delay: float = 1.0
    propagate_errors: List[str] = field(default_factory=list)
    handle_locally: List[str] = field(default_factory=list)
    
    def should_propagate(self, error: Exception) -> bool:
        """Determine if error should be propagated."""
        return (
            any(err_type in str(error) for err_type in self.propagate_errors) or
            not any(err_type in str(error) for err_type in self.handle_locally)
        )
    
    def should_retry(self, attempt: int) -> bool:
        """Determine if operation should be retried."""
        return attempt < self.max_retries

@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False
        
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

@dataclass
class ProcessingMetrics:
    """Metrics for data processing."""
    processed_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    processing_time: float = 0.0
    
    def update(self, result: ValidationResult, time_taken: float) -> None:
        """Update metrics with validation result."""
        self.processed_count += 1
        self.error_count += len(result.errors)
        self.warning_count += len(result.warnings)
        self.processing_time += time_taken

@dataclass
class CacheMetrics:
    """Metrics for validation cache."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    
    def update_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
        
    def update_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
        
    def update_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions += 1
        self.size -= 1
        
    def update_size(self, delta: int) -> None:
        """Update cache size."""
        self.size += delta

@dataclass
class MarketEvent:
    """Base class for market data events."""
    
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationEvent(MarketEvent):
    """Event for validation results."""
    
    symbol: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class ProcessingEvent(MarketEvent):
    """Event for data processing results."""
    
    symbol: str
    operation: str
    success: bool
    processing_time: float
    error_message: Optional[str] = None

@dataclass
class MarketMetrics:
    """Container for market analysis metrics."""
    
    symbol: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    volatility: float = 0.0
    volume: float = 0.0
    price_change: float = 0.0
    trend_strength: float = 0.0
    momentum: float = 0.0
    
    def update_metrics(self,
                      volatility: float,
                      volume: float,
                      price_change: float,
                      trend_strength: float,
                      momentum: float) -> None:
        """Update market metrics."""
        self.volatility = volatility
        self.volume = volume
        self.price_change = price_change
        self.trend_strength = trend_strength
        self.momentum = momentum 

@dataclass
class HealthStatus:
    """Component health status."""
    
    component: str
    is_healthy: bool
    last_check: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, is_healthy: bool, error: Optional[str] = None) -> None:
        """Update health status."""
        self.is_healthy = is_healthy
        self.error = error
        self.last_check = datetime.utcnow() 

@dataclass
class StateChangeEvent(MarketEvent):
    """Event for component state changes."""
    
    component: str
    old_state: ComponentState
    new_state: ComponentState
    error: Optional[str] = None 