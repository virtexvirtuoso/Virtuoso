from typing import Dict, Any, List, Optional, Union
from collections import defaultdict
import time
import psutil
import logging
from datetime import datetime
from functools import wraps
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)

class MetricsCollector:
    """Centralized metrics collection system."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
            self.initialized = True
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value with optional tags."""
        metric_point = MetricPoint(value=value, tags=tags or {})
        self.metrics[name].append(metric_point)
        logger.debug(f"Recorded metric {name}: {value} with tags {tags}")
    
    def record_timing(self, operation: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing information for an operation."""
        self.record_metric(f"{operation}_duration", duration, tags)
    
    def record_memory(self, operation: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Record memory usage for an operation."""
        process = psutil.Process()
        memory_info = process.memory_info()
        self.record_metric(f"{operation}_memory_rss", memory_info.rss / 1024 / 1024, tags)  # MB
        self.record_metric(f"{operation}_memory_vms", memory_info.vms / 1024 / 1024, tags)  # MB
    
    def get_metrics(self, metric_name: str, start_time: Optional[datetime] = None) -> List[MetricPoint]:
        """Get recorded metrics for a given name."""
        metrics = self.metrics.get(metric_name, [])
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        return metrics
    
    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        self.metrics.clear()

def track_timing(operation: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to track timing of operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                MetricsCollector().record_timing(operation, duration, tags)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_tags = {**(tags or {}), 'error': str(e)}
                MetricsCollector().record_timing(operation, duration, error_tags)
                raise
        return wrapper
    return decorator

def track_memory(operation: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to track memory usage of operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                MetricsCollector().record_memory(operation, tags)
                return result
            except Exception as e:
                error_tags = {**(tags or {}), 'error': str(e)}
                MetricsCollector().record_memory(operation, error_tags)
                raise
        return wrapper
    return decorator

# Example usage:
# @track_timing('calculate_indicator')
# @track_memory('calculate_indicator')
# def calculate_indicator(data):
#     # Function implementation
#     pass 