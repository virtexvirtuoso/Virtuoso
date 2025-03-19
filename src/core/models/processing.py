"""Processing related models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class ProcessingMetrics:
    """Container for data processing metrics."""
    
    processed_count: int = 0
    error_count: int = 0
    avg_processing_time: float = 0.0
    peak_memory_usage: float = 0.0
    cache_hit_rate: float = 0.0
    last_processed: Optional[datetime] = None
    
    def update_metrics(self, 
                      processing_time: float,
                      memory_usage: float,
                      cache_hit: bool) -> None:
        """Update processing metrics."""
        self.processed_count += 1
        self.avg_processing_time = (
            (self.avg_processing_time * (self.processed_count - 1) + processing_time)
            / self.processed_count
        )
        self.peak_memory_usage = max(self.peak_memory_usage, memory_usage)
        if cache_hit:
            self.cache_hit_rate = (
                (self.cache_hit_rate * (self.processed_count - 1) + 1)
                / self.processed_count
            )
        self.last_processed = datetime.utcnow()

@dataclass
class ProcessingResult:
    """Container for processing operation results."""
    
    success: bool
    processing_time: float
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def has_error(self) -> bool:
        """Check if processing resulted in error."""
        return not self.success or self.error is not None 