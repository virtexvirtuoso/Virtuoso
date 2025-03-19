import time
import logging
import functools
from typing import Dict, Any, Callable
from datetime import datetime
import psutil
import threading
from collections import defaultdict
from functools import wraps

# Add TRACE level
TRACE_LEVEL = 5  # Lower than DEBUG (10)
logging.addLevelName(TRACE_LEVEL, 'TRACE')
def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)
logging.Logger.trace = trace

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Track and store performance metrics."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PerformanceMetrics, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._metrics = defaultdict(list)
            self._initialized = True
    
    def add_metric(self, category: str, name: str, value: float, metadata: Dict[str, Any] = None):
        """Add a performance metric."""
        with self._lock:
            self._metrics[category].append({
                'name': name,
                'value': value,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            })
    
    def get_metrics(self, category: str = None) -> Dict[str, Any]:
        """Get performance metrics for a category or all metrics."""
        with self._lock:
            if category:
                return dict(self._metrics[category])
            return dict(self._metrics)
    
    def clear_metrics(self, category: str = None):
        """Clear metrics for a category or all metrics."""
        with self._lock:
            if category:
                self._metrics[category].clear()
            else:
                self._metrics.clear()

def track_performance(category: str = 'default'):
    """Decorator to track function execution time and resource usage."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            metrics = PerformanceMetrics()
            
            # Get initial measurements
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            start_cpu = psutil.Process().cpu_percent()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate metrics
                execution_time = time.time() - start_time
                memory_used = psutil.Process().memory_info().rss - start_memory
                cpu_used = psutil.Process().cpu_percent() - start_cpu
                
                # Record metrics
                metrics.add_metric(category, func.__name__, execution_time, {
                    'type': 'execution_time',
                    'unit': 'seconds'
                })
                
                metrics.add_metric(category, f"{func.__name__}_memory", memory_used, {
                    'type': 'memory_usage',
                    'unit': 'bytes'
                })
                
                metrics.add_metric(category, f"{func.__name__}_cpu", cpu_used, {
                    'type': 'cpu_usage',
                    'unit': 'percent'
                })
                
                # Log performance data
                logger.trace(
                    f"Performance metrics for {func.__name__}: "
                    f"time={execution_time:.3f}s, "
                    f"memory={memory_used/1024/1024:.2f}MB, "
                    f"cpu={cpu_used:.1f}%"
                )
                
                return result
                
            except Exception as e:
                # Record error in metrics
                metrics.add_metric(category, f"{func.__name__}_error", 0, {
                    'type': 'error',
                    'error': str(e)
                })
                raise
                
        return wrapper
    return decorator

def track_async_performance(category: str = 'default'):
    """Decorator to track async function execution time and resource usage."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            metrics = PerformanceMetrics()
            
            # Get initial measurements
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            start_cpu = psutil.Process().cpu_percent()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Calculate metrics
                execution_time = time.time() - start_time
                memory_used = psutil.Process().memory_info().rss - start_memory
                cpu_used = psutil.Process().cpu_percent() - start_cpu
                
                # Record metrics
                metrics.add_metric(category, func.__name__, execution_time, {
                    'type': 'execution_time',
                    'unit': 'seconds',
                    'async': True
                })
                
                metrics.add_metric(category, f"{func.__name__}_memory", memory_used, {
                    'type': 'memory_usage',
                    'unit': 'bytes',
                    'async': True
                })
                
                metrics.add_metric(category, f"{func.__name__}_cpu", cpu_used, {
                    'type': 'cpu_usage',
                    'unit': 'percent',
                    'async': True
                })
                
                # Log performance data
                logger.trace(
                    f"Async performance metrics for {func.__name__}: "
                    f"time={execution_time:.3f}s, "
                    f"memory={memory_used/1024/1024:.2f}MB, "
                    f"cpu={cpu_used:.1f}%"
                )
                
                return result
                
            except Exception as e:
                # Record error in metrics
                metrics.add_metric(category, f"{func.__name__}_error", 0, {
                    'type': 'error',
                    'error': str(e),
                    'async': True
                })
                raise
                
        return wrapper
    return decorator

class ResourceMonitor:
    """Monitor system resource usage."""
    
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._running = False
        self._thread = None
        self.metrics = PerformanceMetrics()
    
    def start(self):
        """Start resource monitoring."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_resources)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """Stop resource monitoring."""
        self._running = False
        if self._thread:
            self._thread.join()
    
    def _monitor_resources(self):
        """Monitor system resources periodically."""
        while self._running:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Record metrics
                self.metrics.add_metric('system', 'cpu_usage', cpu_percent, {
                    'type': 'system_cpu',
                    'unit': 'percent'
                })
                
                self.metrics.add_metric('system', 'memory_usage', memory.percent, {
                    'type': 'system_memory',
                    'unit': 'percent'
                })
                
                self.metrics.add_metric('system', 'disk_usage', disk.percent, {
                    'type': 'system_disk',
                    'unit': 'percent'
                })
                
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Error monitoring resources: {str(e)}")
                time.sleep(self.interval)

def log_performance(func):
    """Decorator to log performance metrics of functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.Process().cpu_percent()

        result = func(*args, **kwargs)

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.Process().cpu_percent()

        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        cpu_used = end_cpu - start_cpu

        message = (
            f"Performance metrics for {func.__name__}: "
            f"time={execution_time:.3f}s, "
            f"memory={memory_used:.2f}MB, "
            f"cpu={cpu_used:.1f}%"
        )

        # Try trace level first, fall back to debug
        try:
            logger.trace(message)
        except AttributeError:
            logger.debug(message)

        return result
    return wrapper 