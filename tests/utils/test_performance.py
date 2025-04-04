import pytest
import time
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY

from src.monitoring.performance import (
    PerformanceMonitor,
    PerformanceMetrics,
    monitor_performance
)
from src.monitoring.metrics import MetricsCollector

@pytest.fixture
def performance_monitor():
    monitor = PerformanceMonitor()
    # Clear any existing metrics
    for metric in REGISTRY._names_to_collectors.values():
        REGISTRY.unregister(metric)
    return monitor

def test_singleton_pattern():
    """Test that PerformanceMonitor follows singleton pattern."""
    monitor1 = PerformanceMonitor()
    monitor2 = PerformanceMonitor()
    assert monitor1 is monitor2

def test_performance_metrics_creation():
    """Test creation of PerformanceMetrics dataclass."""
    metrics = PerformanceMetrics(
        execution_time=1.5,
        memory_usage=1024.0,
        cpu_usage=50.0,
        cache_hits=10,
        cache_misses=2
    )
    
    assert metrics.execution_time == 1.5
    assert metrics.memory_usage == 1024.0
    assert metrics.cpu_usage == 50.0
    assert metrics.cache_hits == 10
    assert metrics.cache_misses == 2

def test_monitor_performance_decorator_success(performance_monitor):
    """Test monitor_performance decorator with successful execution."""
    @monitor_performance("test_operation", {"tag": "test"})
    def test_function():
        time.sleep(0.1)
        return 42
    
    result = test_function()
    assert result == 42
    
    # Check Prometheus metrics
    function_calls = performance_monitor.function_calls.labels(
        function="test_operation",
        status="success"
    )._value.get()
    assert function_calls == 1.0
    
    # Check MetricsCollector
    metrics = MetricsCollector()
    timing_metrics = metrics.get_metrics("test_operation_duration")
    assert len(timing_metrics) == 1
    assert timing_metrics[0].value >= 0.1
    assert timing_metrics[0].tags == {"tag": "test"}

def test_monitor_performance_decorator_error(performance_monitor):
    """Test monitor_performance decorator with error handling."""
    @monitor_performance("error_operation")
    def failing_function():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        failing_function()
    
    # Check Prometheus metrics
    function_calls = performance_monitor.function_calls.labels(
        function="error_operation",
        status="error"
    )._value.get()
    assert function_calls == 1.0
    
    # Check MetricsCollector
    metrics = MetricsCollector()
    timing_metrics = metrics.get_metrics("error_operation_duration")
    assert len(timing_metrics) == 1
    assert "error" in timing_metrics[0].tags

@patch('psutil.Process')
def test_system_metrics_collection(mock_process, performance_monitor):
    """Test collection of system metrics."""
    # Mock process metrics
    mock_memory_info = MagicMock()
    mock_memory_info.rss = 1024 * 1024  # 1MB
    mock_memory_info.vms = 2048 * 1024  # 2MB
    
    mock_process_instance = MagicMock()
    mock_process_instance.memory_info.return_value = mock_memory_info
    mock_process_instance.cpu_percent.return_value = 25.0
    
    mock_process.return_value = mock_process_instance
    
    with patch('psutil.cpu_percent', return_value=50.0):
        # Trigger metrics collection
        performance_monitor._start_background_monitoring(1)
        time.sleep(1.1)  # Wait for collection
        
        # Check memory metrics
        rss_value = performance_monitor.memory_usage.labels(type='rss')._value.get()
        vms_value = performance_monitor.memory_usage.labels(type='vms')._value.get()
        assert rss_value == 1024 * 1024
        assert vms_value == 2048 * 1024
        
        # Check CPU metrics
        process_cpu = performance_monitor.cpu_usage.labels(type='process')._value.get()
        system_cpu = performance_monitor.cpu_usage.labels(type='system')._value.get()
        assert process_cpu == 25.0
        assert system_cpu == 50.0

def test_memory_delta_tracking(performance_monitor):
    """Test tracking of memory delta during function execution."""
    test_data = [0] * 1000000  # Allocate some memory
    
    @monitor_performance("memory_test")
    def memory_intensive_function():
        nonlocal test_data
        test_data.extend([1] * 1000000)  # Allocate more memory
        return len(test_data)
    
    result = memory_intensive_function()
    assert result == 2000000
    
    # Check memory delta metrics
    metrics = MetricsCollector()
    memory_metrics = metrics.get_metrics("memory_test_memory_delta")
    assert len(memory_metrics) == 1
    assert memory_metrics[0].value > 0  # Should have positive memory delta

def test_execution_time_histogram(performance_monitor):
    """Test histogram recording of execution times."""
    @monitor_performance("histogram_test")
    def timed_function(sleep_time):
        time.sleep(sleep_time)
        return sleep_time
    
    # Execute with different durations
    timed_function(0.1)
    timed_function(0.5)
    
    # Check histogram metrics
    histogram = performance_monitor.execution_time.labels(function="histogram_test")
    assert histogram._sum.get() >= 0.6  # Total execution time
    assert histogram._count.get() == 2  # Number of observations 