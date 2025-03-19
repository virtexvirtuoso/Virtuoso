from typing import Dict, Any, Optional, Callable, TypeVar, Union
from functools import wraps
import time
import logging
import psutil
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from src.monitoring.metrics import MetricsCollector
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
T = TypeVar('T')

@dataclass
class PerformanceMetrics:
    execution_time: float
    memory_usage: float
    cpu_usage: float
    cache_hits: int = 0
    cache_misses: int = 0

class PerformanceMonitor:
    """Performance monitoring system with Prometheus integration."""
    
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
            settings = get_settings()
            
            # Initialize Prometheus metrics
            self.function_calls = Counter(
                'function_calls_total',
                'Total number of function calls',
                ['function', 'status']
            )
            
            self.execution_time = Histogram(
                'function_execution_seconds',
                'Time spent executing functions',
                ['function'],
                buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float('inf'))
            )
            
            self.memory_usage = Gauge(
                'memory_usage_bytes',
                'Current memory usage',
                ['type']
            )
            
            self.cpu_usage = Gauge(
                'cpu_usage_percent',
                'Current CPU usage',
                ['type']
            )
            
            # Start Prometheus HTTP server if enabled
            if settings.metrics.ENABLED:
                start_http_server(settings.metrics.PROMETHEUS_PORT)
            
            # Initialize background monitoring
            self._start_background_monitoring(settings.metrics.COLLECTION_INTERVAL)
            
            self.initialized = True
    
    def _start_background_monitoring(self, interval: int):
        """Start background thread for system metrics collection."""
        def collect_system_metrics():
            while True:
                try:
                    process = psutil.Process()
                    
                    # Memory metrics
                    memory_info = process.memory_info()
                    self.memory_usage.labels(type='rss').set(memory_info.rss)
                    self.memory_usage.labels(type='vms').set(memory_info.vms)
                    
                    # CPU metrics
                    cpu_percent = process.cpu_percent(interval=1)
                    self.cpu_usage.labels(type='process').set(cpu_percent)
                    
                    # System CPU
                    system_cpu = psutil.cpu_percent()
                    self.cpu_usage.labels(type='system').set(system_cpu)
                    
                    # Record to MetricsCollector as well
                    metrics = MetricsCollector()
                    metrics.record_metric('system_cpu_usage', system_cpu)
                    metrics.record_metric('process_cpu_usage', cpu_percent)
                    
                except Exception as e:
                    logger.error(f"Error collecting system metrics: {str(e)}")
                
                time.sleep(interval)
        
        thread = threading.Thread(
            target=collect_system_metrics,
            daemon=True,
            name="SystemMetricsCollector"
        )
        thread.start()
    
    def record_function_call(self, function_name: str, status: str = "success"):
        """Record a function call with status."""
        self.function_calls.labels(
            function=function_name,
            status=status
        ).inc()
    
    def record_execution_time(self, function_name: str, duration: float):
        """Record function execution time."""
        self.execution_time.labels(function=function_name).observe(duration)

def monitor_performance(operation_name: Optional[str] = None,
                      tags: Optional[Dict[str, str]] = None):
    """Decorator for comprehensive performance monitoring."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        func_name = operation_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            monitor = PerformanceMonitor()
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                end_memory = psutil.Process().memory_info().rss
                memory_delta = end_memory - start_memory
                
                # Record metrics
                monitor.record_function_call(func_name, "success")
                monitor.record_execution_time(func_name, duration)
                
                # Record detailed metrics
                metrics = MetricsCollector()
                metrics.record_timing(func_name, duration, tags)
                metrics.record_metric(
                    f"{func_name}_memory_delta",
                    memory_delta / 1024 / 1024,  # Convert to MB
                    tags
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                monitor.record_function_call(func_name, "error")
                monitor.record_execution_time(func_name, duration)
                
                error_tags = {**(tags or {}), 'error': str(e)}
                metrics = MetricsCollector()
                metrics.record_timing(func_name, duration, error_tags)
                
                raise
                
        return wrapper
    return decorator

# Example usage:
# @monitor_performance("calculate_indicator", {"type": "momentum"})
# def calculate_indicator(data):
#     # Function implementation
#     pass 