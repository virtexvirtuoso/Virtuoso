"""
Async Performance Monitoring Module

Provides performance monitoring decorators and utilities for async operations.
"""

import asyncio
import time
import functools
import logging
from typing import Any, Callable, Dict, Optional, Union, List
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Container for performance metrics."""
    function_name: str
    execution_time_ms: float
    start_time: float
    end_time: float
    memory_usage_mb: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)

class AsyncPerformanceMonitor:
    """
    Monitor and collect performance metrics for async operations.
    """
    
    def __init__(self, max_metrics: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            max_metrics: Maximum number of metrics to store in memory
        """
        self.max_metrics = max_metrics
        self.metrics: List[PerformanceMetric] = []
        self.function_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'call_count': 0,
            'total_time_ms': 0.0,
            'avg_time_ms': 0.0,
            'min_time_ms': float('inf'),
            'max_time_ms': 0.0,
            'error_count': 0
        })
        self._lock = threading.Lock()
        
    def record_metric(self, metric: PerformanceMetric):
        """
        Record a performance metric.
        
        Args:
            metric: Performance metric to record
        """
        with self._lock:
            # Add to metrics list
            self.metrics.append(metric)
            
            # Limit memory usage
            if len(self.metrics) > self.max_metrics:
                self.metrics = self.metrics[-self.max_metrics:]
            
            # Update function statistics
            stats = self.function_stats[metric.function_name]
            stats['call_count'] += 1
            
            if metric.success:
                stats['total_time_ms'] += metric.execution_time_ms
                stats['avg_time_ms'] = stats['total_time_ms'] / stats['call_count']
                stats['min_time_ms'] = min(stats['min_time_ms'], metric.execution_time_ms)
                stats['max_time_ms'] = max(stats['max_time_ms'], metric.execution_time_ms)
            else:
                stats['error_count'] += 1
    
    def get_function_stats(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for functions.
        
        Args:
            function_name: Specific function name, or None for all functions
            
        Returns:
            Performance statistics
        """
        with self._lock:
            if function_name:
                return dict(self.function_stats.get(function_name, {}))
            return {name: dict(stats) for name, stats in self.function_stats.items()}
    
    def get_recent_metrics(self, count: int = 10) -> List[PerformanceMetric]:
        """
        Get recent performance metrics.
        
        Args:
            count: Number of recent metrics to return
            
        Returns:
            List of recent metrics
        """
        with self._lock:
            return self.metrics[-count:] if self.metrics else []
    
    def clear_metrics(self):
        """Clear all stored metrics and statistics."""
        with self._lock:
            self.metrics.clear()
            self.function_stats.clear()

# Global performance monitor
_global_monitor = AsyncPerformanceMonitor()

def get_performance_monitor() -> AsyncPerformanceMonitor:
    """Get the global performance monitor instance."""
    return _global_monitor

def async_monitor_performance(
    func: Optional[Callable] = None,
    *,
    include_args: bool = False,
    measure_memory: bool = False,
    log_slow_calls: bool = True,
    slow_threshold_ms: float = 1000.0
) -> Callable:
    """
    Decorator to monitor async function performance.
    
    Args:
        func: Function to decorate
        include_args: Whether to include function arguments in metrics
        measure_memory: Whether to measure memory usage (experimental)
        log_slow_calls: Whether to log slow function calls
        slow_threshold_ms: Threshold in milliseconds to consider a call slow
        
    Returns:
        Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            function_name = f.__name__
            success = True
            error_msg = None
            result = None
            
            try:
                if asyncio.iscoroutinefunction(f):
                    result = await f(*args, **kwargs)
                else:
                    result = f(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                error_msg = str(e)
                logger.error(f"Error in {function_name}: {error_msg}")
                raise
                
            finally:
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000
                
                # Create metric
                metric = PerformanceMetric(
                    function_name=function_name,
                    execution_time_ms=execution_time_ms,
                    start_time=start_time,
                    end_time=end_time,
                    success=success,
                    error=error_msg
                )
                
                # Include arguments if requested
                if include_args:
                    try:
                        # Only include serializable arguments
                        metric.arguments = {
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                    except Exception:
                        pass
                
                # Record the metric
                _global_monitor.record_metric(metric)
                
                # Log slow calls
                if log_slow_calls and execution_time_ms > slow_threshold_ms:
                    logger.warning(
                        f"Slow async call detected: {function_name} took "
                        f"{execution_time_ms:.2f}ms (threshold: {slow_threshold_ms}ms)"
                    )
        
        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            function_name = f.__name__
            success = True
            error_msg = None
            result = None
            
            try:
                result = f(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                error_msg = str(e)
                logger.error(f"Error in {function_name}: {error_msg}")
                raise
                
            finally:
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000
                
                # Create metric
                metric = PerformanceMetric(
                    function_name=function_name,
                    execution_time_ms=execution_time_ms,
                    start_time=start_time,
                    end_time=end_time,
                    success=success,
                    error=error_msg
                )
                
                # Include arguments if requested
                if include_args:
                    try:
                        metric.arguments = {
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                    except Exception:
                        pass
                
                # Record the metric
                _global_monitor.record_metric(metric)
                
                # Log slow calls
                if log_slow_calls and execution_time_ms > slow_threshold_ms:
                    logger.warning(
                        f"Slow call detected: {function_name} took "
                        f"{execution_time_ms:.2f}ms (threshold: {slow_threshold_ms}ms)"
                    )
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(f) else sync_wrapper
    
    # Handle both @async_monitor_performance and @async_monitor_performance() usage
    if func is None:
        return decorator
    else:
        return decorator(func)

def monitor_performance(
    func: Optional[Callable] = None,
    *,
    include_args: bool = False,
    log_slow_calls: bool = True,
    slow_threshold_ms: float = 1000.0
) -> Callable:
    """
    Decorator to monitor function performance (supports both sync and async).
    
    This is an alias for async_monitor_performance for backward compatibility.
    """
    return async_monitor_performance(
        func,
        include_args=include_args,
        log_slow_calls=log_slow_calls,
        slow_threshold_ms=slow_threshold_ms
    )

class PerformanceContext:
    """Context manager for measuring performance of code blocks."""
    
    def __init__(self, name: str, log_result: bool = True):
        """
        Initialize performance context.
        
        Args:
            name: Name for this performance measurement
            log_result: Whether to log the result
        """
        self.name = name
        self.log_result = log_result
        self.start_time = None
        self.execution_time_ms = None
    
    def __enter__(self):
        """Enter the context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        end_time = time.time()
        self.execution_time_ms = (end_time - self.start_time) * 1000
        
        if self.log_result:
            if exc_type is None:
                logger.info(f"Performance: {self.name} completed in {self.execution_time_ms:.2f}ms")
            else:
                logger.error(f"Performance: {self.name} failed after {self.execution_time_ms:.2f}ms")
        
        # Record metric
        metric = PerformanceMetric(
            function_name=self.name,
            execution_time_ms=self.execution_time_ms,
            start_time=self.start_time,
            end_time=end_time,
            success=(exc_type is None),
            error=str(exc_val) if exc_val else None
        )
        _global_monitor.record_metric(metric)

def get_performance_summary() -> Dict[str, Any]:
    """
    Get a summary of all performance metrics.
    
    Returns:
        Performance summary dictionary
    """
    monitor = get_performance_monitor()
    stats = monitor.get_function_stats()
    recent_metrics = monitor.get_recent_metrics(count=5)
    
    return {
        'function_statistics': stats,
        'recent_metrics': [
            {
                'function_name': m.function_name,
                'execution_time_ms': m.execution_time_ms,
                'success': m.success,
                'error': m.error
            }
            for m in recent_metrics
        ],
        'total_functions_monitored': len(stats),
        'total_calls_monitored': sum(s.get('call_count', 0) for s in stats.values())
    }

# Utility function for backward compatibility
async def measure_async_performance(coroutine, name: str = None) -> Any:
    """
    Measure performance of an async operation.
    
    Args:
        coroutine: Coroutine to measure
        name: Optional name for the measurement
        
    Returns:
        Result of the coroutine
    """
    context_name = name or f"async_operation_{id(coroutine)}"
    
    with PerformanceContext(context_name):
        return await coroutine

# Thread-safe singleton implementation
import threading

_monitor_instance = None
_monitor_lock = threading.Lock()

def get_async_monitor():
    """Get the global async performance monitor instance (thread-safe)"""
    global _monitor_instance
    if _monitor_instance is None:
        with _monitor_lock:
            # Double-check locking pattern
            if _monitor_instance is None:
                _monitor_instance = AsyncPerformanceMonitor()
                logger.info("AsyncPerformanceMonitor singleton instance created")
    return _monitor_instance

def reset_monitor_singleton():
    """Reset the singleton instance (for testing purposes)"""
    global _monitor_instance
    with _monitor_lock:
        if _monitor_instance:
            _monitor_instance = None
            logger.info("AsyncPerformanceMonitor singleton instance reset")
