from src.utils.task_tracker import create_tracked_task
"""
Phase 4 Performance Monitoring Dashboard
========================================

Real-time performance monitoring and metrics visualization for the optimized
event processing pipeline. Provides comprehensive insights into system
performance, bottlenecks, and optimization opportunities.

Key Features:
- Real-time event processing metrics and visualization
- Performance threshold monitoring with automated alerts
- Memory usage and optimization tracking
- Cache performance analytics
- Event sourcing audit trail monitoring
- System health and stability indicators

Performance Targets Monitoring:
- Event throughput: >10,000 events/second
- Latency: <50ms end-to-end for critical paths
- Memory usage: <1GB for normal operation
- Cache hit rates: >95% for stable data
- Zero message loss verification

Dashboard Components:
- Real-time metrics streaming
- Historical performance trends
- Bottleneck identification and analysis
- Resource utilization monitoring
- Alert and notification management
- Performance optimization recommendations
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import threading
import weakref
import psutil
import os
from pathlib import Path

# FastAPI imports for web dashboard
from fastapi import FastAPI, WebSocket, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from ..core.events.optimized_event_processor import OptimizedEventProcessor
from ..core.events.event_sourcing import EventSourcingManager
from ..core.cache.event_driven_cache import EventDrivenCacheController
from ..core.interfaces.services import IAsyncDisposable


class MetricType(Enum):
    """Types of performance metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    name: str
    metric_type: MetricType
    value: float = 0.0
    unit: str = ""
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    history: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def update(self, value: float, tags: Optional[Dict[str, str]] = None):
        """Update metric value."""
        self.value = value
        self.timestamp = time.time()
        if tags:
            self.tags.update(tags)
        
        self.history.append({
            'value': value,
            'timestamp': self.timestamp
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistical summary of metric history."""
        if not self.history:
            return {}
        
        values = [h['value'] for h in self.history]
        return {
            'current': self.value,
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'count': len(values),
            'last_updated': self.timestamp
        }


@dataclass
class PerformanceAlert:
    """Performance alert definition and state."""
    alert_id: str
    name: str
    metric_name: str
    condition: str  # e.g., "> 100", "< 0.95"
    level: AlertLevel
    description: str
    enabled: bool = True
    triggered: bool = False
    trigger_count: int = 0
    last_triggered: Optional[float] = None
    last_resolved: Optional[float] = None
    callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    
    def check_condition(self, value: float) -> bool:
        """Check if alert condition is met."""
        try:
            # Simple condition parsing - can be enhanced
            if self.condition.startswith('>'):
                threshold = float(self.condition[1:].strip())
                return value > threshold
            elif self.condition.startswith('<'):
                threshold = float(self.condition[1:].strip())
                return value < threshold
            elif self.condition.startswith('=='):
                threshold = float(self.condition[2:].strip())
                return value == threshold
            elif self.condition.startswith('!='):
                threshold = float(self.condition[2:].strip())
                return value != threshold
            return False
        except (ValueError, IndexError):
            return False
    
    async def trigger(self, value: float, context: Dict[str, Any] = None):
        """Trigger the alert."""
        if not self.enabled:
            return
        
        self.triggered = True
        self.trigger_count += 1
        self.last_triggered = time.time()
        
        if self.callback:
            alert_context = {
                'alert_id': self.alert_id,
                'name': self.name,
                'metric_name': self.metric_name,
                'value': value,
                'condition': self.condition,
                'level': self.level.value,
                'description': self.description,
                'trigger_time': self.last_triggered,
                'context': context or {}
            }
            try:
                await self.callback(alert_context)
            except Exception as e:
                logging.getLogger(__name__).error(f"Alert callback failed: {e}")
    
    async def resolve(self):
        """Resolve the alert."""
        self.triggered = False
        self.last_resolved = time.time()


class PerformanceThresholds:
    """Performance threshold definitions for the system."""
    
    # Event processing thresholds
    EVENT_THROUGHPUT_MIN = 1000     # events/second
    EVENT_LATENCY_MAX = 50          # milliseconds
    EVENT_ERROR_RATE_MAX = 0.01     # 1% error rate
    
    # Memory thresholds
    MEMORY_USAGE_MAX = 1024         # MB
    MEMORY_GROWTH_RATE_MAX = 100    # MB/hour
    
    # Cache thresholds
    CACHE_HIT_RATE_MIN = 0.95       # 95%
    CACHE_RESPONSE_TIME_MAX = 10    # milliseconds
    
    # System thresholds
    CPU_USAGE_MAX = 80              # percent
    DISK_USAGE_MAX = 90             # percent
    
    @classmethod
    def get_all_thresholds(cls) -> Dict[str, Any]:
        """Get all threshold definitions."""
        return {
            'event_processing': {
                'throughput_min': cls.EVENT_THROUGHPUT_MIN,
                'latency_max': cls.EVENT_LATENCY_MAX,
                'error_rate_max': cls.EVENT_ERROR_RATE_MAX
            },
            'memory': {
                'usage_max': cls.MEMORY_USAGE_MAX,
                'growth_rate_max': cls.MEMORY_GROWTH_RATE_MAX
            },
            'cache': {
                'hit_rate_min': cls.CACHE_HIT_RATE_MIN,
                'response_time_max': cls.CACHE_RESPONSE_TIME_MAX
            },
            'system': {
                'cpu_usage_max': cls.CPU_USAGE_MAX,
                'disk_usage_max': cls.DISK_USAGE_MAX
            }
        }


class MetricsCollector:
    """Collects and aggregates performance metrics from various system components."""
    
    def __init__(
        self,
        event_processor: Optional[OptimizedEventProcessor] = None,
        event_sourcing: Optional[EventSourcingManager] = None,
        cache_controller: Optional[EventDrivenCacheController] = None
    ):
        """Initialize metrics collector."""
        self.event_processor = event_processor
        self.event_sourcing = event_sourcing
        self.cache_controller = cache_controller
        
        # Metrics storage
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.alerts: Dict[str, PerformanceAlert] = {}
        
        # System metrics
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()
        
        # Metric collection intervals
        self.collection_interval = 1.0  # seconds
        self.collection_task: Optional[asyncio.Task] = None
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize default metrics
        self._initialize_default_metrics()
        self._initialize_default_alerts()
    
    def _initialize_default_metrics(self):
        """Initialize default performance metrics."""
        default_metrics = [
            # Event processing metrics
            ('events_per_second', MetricType.GAUGE, 'events/s', 'Event processing throughput'),
            ('avg_event_latency', MetricType.GAUGE, 'ms', 'Average event processing latency'),
            ('event_queue_size', MetricType.GAUGE, 'events', 'Current event queue size'),
            ('event_error_rate', MetricType.GAUGE, '%', 'Event processing error rate'),
            ('batch_processing_time', MetricType.HISTOGRAM, 'ms', 'Batch processing time distribution'),
            
            # Memory metrics
            ('memory_usage', MetricType.GAUGE, 'MB', 'Process memory usage'),
            ('memory_growth_rate', MetricType.GAUGE, 'MB/h', 'Memory growth rate'),
            ('gc_collections', MetricType.COUNTER, 'count', 'Garbage collection count'),
            
            # Cache metrics
            ('cache_hit_rate', MetricType.GAUGE, '%', 'Overall cache hit rate'),
            ('cache_response_time', MetricType.HISTOGRAM, 'ms', 'Cache response time distribution'),
            ('cache_operations_per_second', MetricType.GAUGE, 'ops/s', 'Cache operations per second'),
            
            # System metrics
            ('cpu_usage', MetricType.GAUGE, '%', 'CPU usage percentage'),
            ('disk_usage', MetricType.GAUGE, '%', 'Disk usage percentage'),
            ('network_io', MetricType.GAUGE, 'bytes/s', 'Network I/O rate'),
            
            # Event sourcing metrics
            ('events_sourced', MetricType.COUNTER, 'events', 'Total events sourced'),
            ('event_store_size', MetricType.GAUGE, 'MB', 'Event store size'),
            ('replay_performance', MetricType.HISTOGRAM, 'ms', 'Event replay performance'),
        ]
        
        for name, metric_type, unit, description in default_metrics:
            self.metrics[name] = PerformanceMetric(
                name=name,
                metric_type=metric_type,
                unit=unit,
                description=description
            )
    
    def _initialize_default_alerts(self):
        """Initialize default performance alerts."""
        thresholds = PerformanceThresholds.get_all_thresholds()
        
        default_alerts = [
            ('low_throughput', 'events_per_second', f"< {thresholds['event_processing']['throughput_min']}", 
             AlertLevel.WARNING, 'Event processing throughput below threshold'),
            ('high_latency', 'avg_event_latency', f"> {thresholds['event_processing']['latency_max']}", 
             AlertLevel.CRITICAL, 'Event processing latency above threshold'),
            ('high_error_rate', 'event_error_rate', f"> {thresholds['event_processing']['error_rate_max']}", 
             AlertLevel.CRITICAL, 'Event processing error rate above threshold'),
            ('high_memory_usage', 'memory_usage', f"> {thresholds['memory']['usage_max']}", 
             AlertLevel.WARNING, 'Memory usage above threshold'),
            ('low_cache_hit_rate', 'cache_hit_rate', f"< {thresholds['cache']['hit_rate_min']}", 
             AlertLevel.WARNING, 'Cache hit rate below threshold'),
            ('high_cpu_usage', 'cpu_usage', f"> {thresholds['system']['cpu_usage_max']}", 
             AlertLevel.WARNING, 'CPU usage above threshold'),
        ]
        
        for alert_id, metric_name, condition, level, description in default_alerts:
            self.alerts[alert_id] = PerformanceAlert(
                alert_id=alert_id,
                name=alert_id.replace('_', ' ').title(),
                metric_name=metric_name,
                condition=condition,
                level=level,
                description=description
            )
    
    async def start_collection(self):
        """Start metrics collection."""
        if self.collection_task:
            return
        
        self.collection_task = create_tracked_task(self._collection_loop(), name="auto_tracked_task")
        self.logger.info("Metrics collection started")
    
    async def stop_collection(self):
        """Stop metrics collection."""
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
            self.collection_task = None
        
        self.logger.info("Metrics collection stopped")
    
    async def _collection_loop(self):
        """Main metrics collection loop."""
        while True:
            try:
                await self._collect_all_metrics()
                await self._check_alerts()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_all_metrics(self):
        """Collect metrics from all sources."""
        with self.lock:
            # Collect event processing metrics
            if self.event_processor:
                await self._collect_event_processor_metrics()
            
            # Collect cache metrics
            if self.cache_controller:
                await self._collect_cache_metrics()
            
            # Collect event sourcing metrics
            if self.event_sourcing:
                await self._collect_event_sourcing_metrics()
            
            # Collect system metrics
            await self._collect_system_metrics()
    
    async def _collect_event_processor_metrics(self):
        """Collect event processor metrics."""
        try:
            processor_metrics = self.event_processor.get_metrics()
            
            if processor_metrics:
                # Event throughput
                processing = processor_metrics.get('processing', {})
                peak_eps = processing.get('peak_events_per_second', 0)
                self.metrics['events_per_second'].update(peak_eps)
                
                # Processing time
                avg_time_ms = processing.get('avg_processing_time_ms', 0)
                self.metrics['avg_event_latency'].update(avg_time_ms)
                
                # Queue sizes
                queues = processor_metrics.get('queues', {})
                total_queue_size = queues.get('total_queue_size', 0)
                self.metrics['event_queue_size'].update(total_queue_size)
                
                # Error rate
                errors = processing.get('errors_count', 0)
                total_events = processing.get('total_events_processed', 1)
                error_rate = (errors / total_events) * 100
                self.metrics['event_error_rate'].update(error_rate)
                
        except Exception as e:
            self.logger.error(f"Failed to collect event processor metrics: {e}")
    
    async def _collect_cache_metrics(self):
        """Collect cache performance metrics."""
        try:
            cache_metrics = self.cache_controller.get_comprehensive_metrics()
            
            if cache_metrics:
                # Overall hit rate
                key_mgmt = cache_metrics.get('key_management', {})
                avg_hit_rate = key_mgmt.get('avg_hit_rate', 0)
                self.metrics['cache_hit_rate'].update(avg_hit_rate)
                
                # Response times
                response_times = cache_metrics.get('response_times', {})
                avg_response_time = statistics.mean([
                    rt.get('avg_ms', 0) for rt in response_times.values()
                ]) if response_times else 0
                self.metrics['cache_response_time'].update(avg_response_time)
                
                # Operations per second
                operations = cache_metrics.get('operations', {})
                total_ops = sum(operations.values())
                uptime = time.time() - self.start_time
                ops_per_second = total_ops / max(uptime, 1)
                self.metrics['cache_operations_per_second'].update(ops_per_second)
                
        except Exception as e:
            self.logger.error(f"Failed to collect cache metrics: {e}")
    
    async def _collect_event_sourcing_metrics(self):
        """Collect event sourcing metrics."""
        try:
            sourcing_metrics = self.event_sourcing.get_performance_metrics()
            
            if sourcing_metrics:
                # Events sourced
                events_sourced = sourcing_metrics.get('events_sourced', 0)
                self.metrics['events_sourced'].update(events_sourced)
                
                # Storage stats
                storage_stats = sourcing_metrics.get('storage_stats', {})
                storage_perf = storage_stats.get('performance', {})
                avg_append_time = storage_perf.get('avg_append_time_ms', 0)
                self.metrics['replay_performance'].update(avg_append_time)
                
        except Exception as e:
            self.logger.error(f"Failed to collect event sourcing metrics: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.metrics['memory_usage'].update(memory_mb)
            
            # CPU usage
            cpu_percent = self.process.cpu_percent()
            self.metrics['cpu_usage'].update(cpu_percent)
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = disk_usage.percent
            self.metrics['disk_usage'].update(disk_percent)
            
            # Network I/O
            net_io = psutil.net_io_counters()
            net_bytes_per_sec = (net_io.bytes_sent + net_io.bytes_recv) / max(time.time() - self.start_time, 1)
            self.metrics['network_io'].update(net_bytes_per_sec)
            
            # Memory growth rate calculation
            if len(self.metrics['memory_usage'].history) >= 2:
                recent_memory = list(self.metrics['memory_usage'].history)[-10:]  # Last 10 samples
                if len(recent_memory) >= 2:
                    time_diff = recent_memory[-1]['timestamp'] - recent_memory[0]['timestamp']
                    memory_diff = recent_memory[-1]['value'] - recent_memory[0]['value']
                    if time_diff > 0:
                        growth_rate = (memory_diff / time_diff) * 3600  # MB/hour
                        self.metrics['memory_growth_rate'].update(growth_rate)
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    async def _check_alerts(self):
        """Check all alerts against current metrics."""
        for alert in self.alerts.values():
            if not alert.enabled:
                continue
            
            if alert.metric_name not in self.metrics:
                continue
            
            current_value = self.metrics[alert.metric_name].value
            condition_met = alert.check_condition(current_value)
            
            if condition_met and not alert.triggered:
                await alert.trigger(current_value, {
                    'metric': self.metrics[alert.metric_name].get_stats()
                })
                self.logger.warning(f"Alert triggered: {alert.name} - {current_value}")
            
            elif not condition_met and alert.triggered:
                await alert.resolve()
                self.logger.info(f"Alert resolved: {alert.name}")
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all current metrics with statistics."""
        with self.lock:
            return {
                name: metric.get_stats() 
                for name, metric in self.metrics.items()
            }
    
    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        with self.lock:
            if metric_name not in self.metrics:
                return []
            
            history = list(self.metrics[metric_name].history)
            return history[-limit:]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently active alerts."""
        active_alerts = []
        
        for alert in self.alerts.values():
            if alert.triggered:
                active_alerts.append({
                    'alert_id': alert.alert_id,
                    'name': alert.name,
                    'metric_name': alert.metric_name,
                    'level': alert.level.value,
                    'description': alert.description,
                    'trigger_count': alert.trigger_count,
                    'last_triggered': alert.last_triggered,
                    'current_value': self.metrics[alert.metric_name].value if alert.metric_name in self.metrics else None
                })
        
        return active_alerts


class PerformanceDashboard:
    """Web-based performance dashboard for real-time monitoring."""
    
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        port: int = 8002,
        host: str = "0.0.0.0"
    ):
        """Initialize performance dashboard."""
        self.metrics_collector = metrics_collector
        self.port = port
        self.host = host
        
        # FastAPI app
        self.app = FastAPI(title="Virtuoso Performance Dashboard", version="1.0.0")
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Template and static files
        self.templates = Jinja2Templates(directory="templates")
        
        # Setup routes
        self._setup_routes()
        
        # Background task for broadcasting metrics
        self.broadcast_task: Optional[asyncio.Task] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page."""
            return self.templates.TemplateResponse("performance_dashboard.html", {
                "request": request,
                "title": "Virtuoso Performance Dashboard"
            })
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get all current metrics."""
            return JSONResponse(self.metrics_collector.get_all_metrics())
        
        @self.app.get("/api/metrics/{metric_name}/history")
        async def get_metric_history(metric_name: str, limit: int = 100):
            """Get historical data for specific metric."""
            history = self.metrics_collector.get_metric_history(metric_name, limit)
            return JSONResponse(history)
        
        @self.app.get("/api/alerts")
        async def get_alerts():
            """Get active alerts."""
            return JSONResponse(self.metrics_collector.get_active_alerts())
        
        @self.app.get("/api/health")
        async def health_check():
            """System health check."""
            metrics = self.metrics_collector.get_all_metrics()
            alerts = self.metrics_collector.get_active_alerts()
            
            # Determine overall health status
            critical_alerts = [a for a in alerts if a['level'] == 'critical']
            warning_alerts = [a for a in alerts if a['level'] == 'warning']
            
            if critical_alerts:
                status = "critical"
            elif warning_alerts:
                status = "warning"
            else:
                status = "healthy"
            
            return JSONResponse({
                "status": status,
                "timestamp": time.time(),
                "metrics_count": len(metrics),
                "active_alerts": len(alerts),
                "critical_alerts": len(critical_alerts),
                "warning_alerts": len(warning_alerts),
                "uptime_seconds": time.time() - self.metrics_collector.start_time
            })
        
        @self.app.get("/api/performance-report")
        async def performance_report():
            """Generate comprehensive performance report."""
            metrics = self.metrics_collector.get_all_metrics()
            
            # Key performance indicators
            event_throughput = metrics.get('events_per_second', {}).get('current', 0)
            avg_latency = metrics.get('avg_event_latency', {}).get('current', 0)
            memory_usage = metrics.get('memory_usage', {}).get('current', 0)
            cache_hit_rate = metrics.get('cache_hit_rate', {}).get('current', 0)
            
            # Performance assessment
            performance_score = 100
            
            # Throughput assessment (target: >10,000 events/s)
            if event_throughput < 1000:
                performance_score -= 30
            elif event_throughput < 5000:
                performance_score -= 15
            elif event_throughput < 10000:
                performance_score -= 5
            
            # Latency assessment (target: <50ms)
            if avg_latency > 100:
                performance_score -= 25
            elif avg_latency > 50:
                performance_score -= 10
            
            # Memory assessment (target: <1GB)
            if memory_usage > 2048:
                performance_score -= 20
            elif memory_usage > 1024:
                performance_score -= 10
            
            # Cache assessment (target: >95%)
            if cache_hit_rate < 80:
                performance_score -= 15
            elif cache_hit_rate < 95:
                performance_score -= 5
            
            performance_grade = "A" if performance_score >= 90 else "B" if performance_score >= 80 else "C" if performance_score >= 70 else "D"
            
            return JSONResponse({
                "performance_score": max(0, performance_score),
                "performance_grade": performance_grade,
                "key_metrics": {
                    "event_throughput": event_throughput,
                    "avg_latency": avg_latency,
                    "memory_usage": memory_usage,
                    "cache_hit_rate": cache_hit_rate
                },
                "targets": {
                    "event_throughput": 10000,
                    "avg_latency": 50,
                    "memory_usage": 1024,
                    "cache_hit_rate": 95
                },
                "recommendations": self._generate_recommendations(metrics),
                "timestamp": time.time()
            })
        
        @self.app.websocket("/ws/metrics")
        async def websocket_metrics(websocket: WebSocket):
            """WebSocket endpoint for real-time metrics."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    await websocket.receive_text()  # Keep connection alive
            except Exception:
                pass
            finally:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
    
    def _generate_recommendations(self, metrics: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Event processing recommendations
        event_throughput = metrics.get('events_per_second', {}).get('current', 0)
        if event_throughput < 5000:
            recommendations.append("Consider increasing worker pool size for event processing")
        
        avg_latency = metrics.get('avg_event_latency', {}).get('current', 0)
        if avg_latency > 50:
            recommendations.append("Optimize event processing pipeline to reduce latency")
        
        # Memory recommendations
        memory_usage = metrics.get('memory_usage', {}).get('current', 0)
        memory_growth = metrics.get('memory_growth_rate', {}).get('current', 0)
        
        if memory_usage > 1024:
            recommendations.append("Memory usage is high - consider implementing memory optimization")
        
        if memory_growth > 50:  # MB/hour
            recommendations.append("Memory growth rate is concerning - check for memory leaks")
        
        # Cache recommendations
        cache_hit_rate = metrics.get('cache_hit_rate', {}).get('current', 0)
        if cache_hit_rate < 90:
            recommendations.append("Cache hit rate is low - review cache key patterns and TTL settings")
        
        cache_response_time = metrics.get('cache_response_time', {}).get('current', 0)
        if cache_response_time > 20:
            recommendations.append("Cache response time is high - consider cache backend optimization")
        
        # System recommendations
        cpu_usage = metrics.get('cpu_usage', {}).get('current', 0)
        if cpu_usage > 80:
            recommendations.append("CPU usage is high - consider scaling or optimization")
        
        if not recommendations:
            recommendations.append("System is performing well within target parameters")
        
        return recommendations
    
    async def start_dashboard(self):
        """Start the dashboard server."""
        # Start metrics broadcasting
        if not self.broadcast_task:
            self.broadcast_task = create_tracked_task(self._broadcast_metrics(), name="auto_tracked_task")
        
        # Start FastAPI server
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def _broadcast_metrics(self):
        """Broadcast metrics to WebSocket clients."""
        while True:
            try:
                if self.websocket_connections:
                    metrics_data = {
                        "type": "metrics_update",
                        "data": self.metrics_collector.get_all_metrics(),
                        "alerts": self.metrics_collector.get_active_alerts(),
                        "timestamp": time.time()
                    }
                    
                    # Send to all connected clients
                    disconnected = []
                    for ws in self.websocket_connections:
                        try:
                            await ws.send_json(metrics_data)
                        except Exception:
                            disconnected.append(ws)
                    
                    # Remove disconnected clients
                    for ws in disconnected:
                        self.websocket_connections.remove(ws)
                
                await asyncio.sleep(1)  # Broadcast every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics broadcast error: {e}")
                await asyncio.sleep(1)
    
    async def stop_dashboard(self):
        """Stop the dashboard server."""
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
            self.broadcast_task = None
        
        # Close all WebSocket connections
        for ws in self.websocket_connections:
            try:
                await ws.close()
            except Exception:
                pass
        self.websocket_connections.clear()


class Phase4PerformanceMonitor(IAsyncDisposable):
    """
    Main Phase 4 Performance Monitor integrating all monitoring components.
    
    Provides comprehensive real-time monitoring of the optimized event processing
    system with automated alerting and performance optimization recommendations.
    """
    
    def __init__(
        self,
        event_processor: OptimizedEventProcessor,
        event_sourcing: EventSourcingManager,
        cache_controller: EventDrivenCacheController,
        dashboard_port: int = 8002
    ):
        """Initialize Phase 4 performance monitor."""
        self.event_processor = event_processor
        self.event_sourcing = event_sourcing
        self.cache_controller = cache_controller
        
        # Initialize components
        self.metrics_collector = MetricsCollector(
            event_processor=event_processor,
            event_sourcing=event_sourcing,
            cache_controller=cache_controller
        )
        
        self.dashboard = PerformanceDashboard(
            metrics_collector=self.metrics_collector,
            port=dashboard_port
        )
        
        # State management
        self.running = False
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Phase 4 Performance Monitor initialized")
    
    async def start(self):
        """Start comprehensive performance monitoring."""
        if self.running:
            return
        
        try:
            # Start metrics collection
            await self.metrics_collector.start_collection()
            
            # Start dashboard (non-blocking)
            create_tracked_task(self.dashboard.start_dashboard(), name="auto_tracked_task")
            
            self.running = True
            self.logger.info(f"Phase 4 Performance Monitor started on port {self.dashboard.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start performance monitor: {e}")
            raise
    
    async def stop(self):
        """Stop performance monitoring."""
        if not self.running:
            return
        
        try:
            # Stop metrics collection
            await self.metrics_collector.stop_collection()
            
            # Stop dashboard
            await self.dashboard.stop_dashboard()
            
            self.running = False
            self.logger.info("Phase 4 Performance Monitor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping performance monitor: {e}")
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        metrics = self.metrics_collector.get_all_metrics()
        alerts = self.metrics_collector.get_active_alerts()
        
        # Calculate key performance indicators
        event_throughput = metrics.get('events_per_second', {}).get('current', 0)
        avg_latency = metrics.get('avg_event_latency', {}).get('current', 0)
        memory_usage = metrics.get('memory_usage', {}).get('current', 0)
        cache_hit_rate = metrics.get('cache_hit_rate', {}).get('current', 0)
        
        # Performance targets achievement
        targets_met = {
            'throughput': event_throughput >= PerformanceThresholds.EVENT_THROUGHPUT_MIN,
            'latency': avg_latency <= PerformanceThresholds.EVENT_LATENCY_MAX,
            'memory': memory_usage <= PerformanceThresholds.MEMORY_USAGE_MAX,
            'cache_hit_rate': cache_hit_rate >= PerformanceThresholds.CACHE_HIT_RATE_MIN
        }
        
        return {
            'timestamp': time.time(),
            'performance_targets': {
                'throughput_target': PerformanceThresholds.EVENT_THROUGHPUT_MIN,
                'latency_target': PerformanceThresholds.EVENT_LATENCY_MAX,
                'memory_target': PerformanceThresholds.MEMORY_USAGE_MAX,
                'cache_hit_rate_target': PerformanceThresholds.CACHE_HIT_RATE_MIN
            },
            'current_performance': {
                'event_throughput': event_throughput,
                'avg_latency': avg_latency,
                'memory_usage': memory_usage,
                'cache_hit_rate': cache_hit_rate
            },
            'targets_achievement': targets_met,
            'overall_performance': all(targets_met.values()),
            'active_alerts_count': len(alerts),
            'critical_alerts_count': len([a for a in alerts if a['level'] == 'critical']),
            'uptime_hours': (time.time() - self.metrics_collector.start_time) / 3600
        }
    
    async def dispose_async(self):
        """Dispose of performance monitor resources."""
        await self.stop()
        self.logger.info("Phase 4 Performance Monitor disposed")


# Global performance monitor instance
# Will be initialized with actual components during system startup
phase4_performance_monitor: Optional[Phase4PerformanceMonitor] = None