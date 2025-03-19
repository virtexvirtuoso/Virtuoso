import pytest
import time
from datetime import datetime, timedelta
from src.monitoring.metrics import (
    MetricsCollector,
    MetricPoint,
    track_timing,
    track_memory
)

@pytest.fixture
def metrics_collector():
    collector = MetricsCollector()
    collector.clear_metrics()
    return collector

def test_singleton_pattern():
    """Test that MetricsCollector follows singleton pattern."""
    collector1 = MetricsCollector()
    collector2 = MetricsCollector()
    assert collector1 is collector2

def test_record_metric(metrics_collector):
    """Test basic metric recording."""
    metrics_collector.record_metric("test_metric", 42.0, {"tag": "value"})
    metrics = metrics_collector.get_metrics("test_metric")
    
    assert len(metrics) == 1
    assert metrics[0].value == 42.0
    assert metrics[0].tags == {"tag": "value"}
    assert isinstance(metrics[0].timestamp, datetime)

def test_record_timing(metrics_collector):
    """Test timing metric recording."""
    metrics_collector.record_timing("test_operation", 0.5, {"tag": "value"})
    metrics = metrics_collector.get_metrics("test_operation_duration")
    
    assert len(metrics) == 1
    assert metrics[0].value == 0.5
    assert metrics[0].tags == {"tag": "value"}

def test_record_memory(metrics_collector):
    """Test memory metric recording."""
    metrics_collector.record_memory("test_operation", {"tag": "value"})
    rss_metrics = metrics_collector.get_metrics("test_operation_memory_rss")
    vms_metrics = metrics_collector.get_metrics("test_operation_memory_vms")
    
    assert len(rss_metrics) == 1
    assert len(vms_metrics) == 1
    assert rss_metrics[0].tags == {"tag": "value"}
    assert vms_metrics[0].tags == {"tag": "value"}
    assert rss_metrics[0].value > 0
    assert vms_metrics[0].value > 0

def test_get_metrics_with_time_filter(metrics_collector):
    """Test getting metrics with time filter."""
    now = datetime.utcnow()
    old_time = now - timedelta(hours=1)
    
    # Record metrics at different times
    metrics_collector.metrics["test_metric"] = [
        MetricPoint(value=1.0, timestamp=old_time),
        MetricPoint(value=2.0, timestamp=now)
    ]
    
    # Get recent metrics
    recent_metrics = metrics_collector.get_metrics(
        "test_metric",
        start_time=now - timedelta(minutes=5)
    )
    assert len(recent_metrics) == 1
    assert recent_metrics[0].value == 2.0

def test_timing_decorator(metrics_collector):
    """Test timing decorator functionality."""
    @track_timing("decorated_operation", {"tag": "test"})
    def slow_operation():
        time.sleep(0.1)
        return 42
    
    result = slow_operation()
    assert result == 42
    
    metrics = metrics_collector.get_metrics("decorated_operation_duration")
    assert len(metrics) == 1
    assert metrics[0].value >= 0.1
    assert metrics[0].tags == {"tag": "test"}

def test_memory_decorator(metrics_collector):
    """Test memory decorator functionality."""
    @track_memory("memory_operation", {"tag": "test"})
    def memory_intensive_operation():
        # Create some data to measure memory
        data = [i for i in range(1000000)]
        return len(data)
    
    result = memory_intensive_operation()
    assert result == 1000000
    
    rss_metrics = metrics_collector.get_metrics("memory_operation_memory_rss")
    assert len(rss_metrics) == 1
    assert rss_metrics[0].tags == {"tag": "test"}
    assert rss_metrics[0].value > 0

def test_decorator_error_handling(metrics_collector):
    """Test decorator behavior with errors."""
    @track_timing("error_operation")
    @track_memory("error_operation")
    def failing_operation():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        failing_operation()
    
    timing_metrics = metrics_collector.get_metrics("error_operation_duration")
    memory_metrics = metrics_collector.get_metrics("error_operation_memory_rss")
    
    assert len(timing_metrics) == 1
    assert len(memory_metrics) == 1
    assert "error" in timing_metrics[0].tags
    assert "error" in memory_metrics[0].tags

def test_clear_metrics(metrics_collector):
    """Test clearing all metrics."""
    metrics_collector.record_metric("test_metric", 42.0)
    assert len(metrics_collector.get_metrics("test_metric")) == 1
    
    metrics_collector.clear_metrics()
    assert len(metrics_collector.get_metrics("test_metric")) == 0 