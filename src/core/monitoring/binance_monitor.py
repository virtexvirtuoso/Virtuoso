"""
Binance Integration Monitoring

Comprehensive monitoring for Binance integration in the Virtuoso trading system.
Tracks performance, errors, and provides alerts for production deployment.
"""

import asyncio
import logging
import time
import psutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    timestamp: float
    api_response_time_ms: float
    websocket_latency_ms: float
    message_throughput_per_sec: float
    active_connections: int
    error_rate_percent: float
    memory_usage_mb: float
    cpu_usage_percent: float
    
@dataclass
class MonitoringAlert:
    """Monitoring alert data."""
    timestamp: float
    level: AlertLevel
    component: str
    message: str
    metrics: Dict[str, Any]
    
class BinanceMonitor:
    """
    Comprehensive monitoring for Binance integration.
    
    Features:
    - Performance metrics collection
    - Error rate monitoring
    - Connection health tracking
    - Resource usage monitoring
    - Automated alerting
    - Performance optimization suggestions
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize monitoring system.
        
        Args:
            config: Monitoring configuration
        """
        self.config = config
        self.monitoring_config = config.get('monitoring', {})
        
        # Monitoring state
        self.enabled = self.monitoring_config.get('enabled', True)
        self.check_interval = self.monitoring_config.get('interval', 30)
        self.alert_cooldown = self.monitoring_config.get('alerts', {}).get('cooldown_period', 300)
        
        # Metrics storage
        self.metrics_history = []
        self.max_history = 1000
        self.last_metrics = None
        
        # Error tracking
        self.error_count = 0
        self.last_error_time = 0
        self.error_patterns = {}
        
        # Alert tracking
        self.last_alerts = {}
        self.alert_callbacks = []
        
        # Performance thresholds
        self.thresholds = self.monitoring_config.get('performance', {}).get('thresholds', {
            'max_response_time': 5000,  # 5 seconds
            'max_error_rate': 0.05,     # 5%
            'max_memory_usage': 512,    # 512MB
            'max_cpu_usage': 80,        # 80%
            'min_message_throughput': 1 # 1 message/sec minimum
        })
        
        # Component references (set by external components)
        self.binance_exchange = None
        self.data_fetcher = None
        self.websocket_handler = None
        
        self.logger = logger
        self.logger.info("Binance Monitor initialized")
    
    def register_components(self, 
                          exchange=None, 
                          data_fetcher=None, 
                          websocket_handler=None):
        """Register components for monitoring."""
        self.binance_exchange = exchange
        self.data_fetcher = data_fetcher
        self.websocket_handler = websocket_handler
        
        self.logger.info("Components registered for monitoring")
    
    def add_alert_callback(self, callback: Callable[[MonitoringAlert], None]):
        """Add callback for handling alerts."""
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start the monitoring loop."""
        if not self.enabled:
            self.logger.info("Monitoring disabled in configuration")
            return
        
        self.logger.info("Starting Binance monitoring...")
        
        while self.enabled:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                if metrics:
                    self.metrics_history.append(metrics)
                    
                    # Trim history if too long
                    if len(self.metrics_history) > self.max_history:
                        self.metrics_history = self.metrics_history[-self.max_history:]
                    
                    # Check for alerts
                    await self.check_alerts(metrics)
                    
                    self.last_metrics = metrics
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.check_interval)
    
    async def collect_metrics(self) -> Optional[PerformanceMetrics]:
        """Collect current performance metrics."""
        try:
            timestamp = time.time()
            
            # Get system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Initialize metrics with system data
            api_response_time = 0
            websocket_latency = 0
            message_throughput = 0
            active_connections = 0
            error_rate = 0
            
            # Collect Binance-specific metrics
            if self.binance_exchange:
                try:
                    # Test API response time
                    start_time = time.time()
                    await self.binance_exchange.fetch_ticker('BTC/USDT')
                    api_response_time = (time.time() - start_time) * 1000
                except Exception as e:
                    self.logger.warning(f"Error testing API response: {str(e)}")
                    self.error_count += 1
                    self.last_error_time = timestamp
            
            # Get WebSocket metrics
            if self.websocket_handler:
                try:
                    stats = self.websocket_handler.get_connection_stats()
                    message_throughput = self._calculate_message_rate(stats.get('message_count', 0))
                    active_connections = 1 if stats.get('connected', False) else 0
                    websocket_latency = self._estimate_websocket_latency()
                except Exception as e:
                    self.logger.warning(f"Error collecting WebSocket metrics: {str(e)}")
            
            # Get data fetcher metrics
            if self.data_fetcher:
                try:
                    stats = self.data_fetcher.get_performance_stats()
                    error_rate = 1 - stats.get('success_rate', 1.0)
                except Exception as e:
                    self.logger.warning(f"Error collecting data fetcher metrics: {str(e)}")
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=timestamp,
                api_response_time_ms=api_response_time,
                websocket_latency_ms=websocket_latency,
                message_throughput_per_sec=message_throughput,
                active_connections=active_connections,
                error_rate_percent=error_rate * 100,
                memory_usage_mb=memory_info.used / (1024 * 1024),
                cpu_usage_percent=cpu_percent
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {str(e)}")
            return None
    
    async def check_alerts(self, metrics: PerformanceMetrics):
        """Check metrics against thresholds and generate alerts."""
        try:
            current_time = time.time()
            
            # API Response Time Alert
            if metrics.api_response_time_ms > self.thresholds['max_response_time']:
                await self._send_alert(
                    AlertLevel.WARNING,
                    "api_response_time",
                    f"API response time is high: {metrics.api_response_time_ms:.1f}ms (threshold: {self.thresholds['max_response_time']}ms)",
                    {"response_time_ms": metrics.api_response_time_ms}
                )
            
            # Error Rate Alert
            if metrics.error_rate_percent > self.thresholds['max_error_rate'] * 100:
                await self._send_alert(
                    AlertLevel.ERROR,
                    "error_rate",
                    f"Error rate is high: {metrics.error_rate_percent:.2f}% (threshold: {self.thresholds['max_error_rate'] * 100}%)",
                    {"error_rate_percent": metrics.error_rate_percent}
                )
            
            # Memory Usage Alert
            if metrics.memory_usage_mb > self.thresholds['max_memory_usage']:
                await self._send_alert(
                    AlertLevel.WARNING,
                    "memory_usage",
                    f"Memory usage is high: {metrics.memory_usage_mb:.1f}MB (threshold: {self.thresholds['max_memory_usage']}MB)",
                    {"memory_usage_mb": metrics.memory_usage_mb}
                )
            
            # CPU Usage Alert
            if metrics.cpu_usage_percent > self.thresholds['max_cpu_usage']:
                await self._send_alert(
                    AlertLevel.WARNING,
                    "cpu_usage",
                    f"CPU usage is high: {metrics.cpu_usage_percent:.1f}% (threshold: {self.thresholds['max_cpu_usage']}%)",
                    {"cpu_usage_percent": metrics.cpu_usage_percent}
                )
            
            # Connection Alert
            if metrics.active_connections == 0:
                await self._send_alert(
                    AlertLevel.ERROR,
                    "connection",
                    "WebSocket connection is down",
                    {"active_connections": metrics.active_connections}
                )
            
            # Message Throughput Alert
            if metrics.message_throughput_per_sec < self.thresholds['min_message_throughput']:
                await self._send_alert(
                    AlertLevel.WARNING,
                    "message_throughput",
                    f"Message throughput is low: {metrics.message_throughput_per_sec:.1f}/sec (minimum: {self.thresholds['min_message_throughput']}/sec)",
                    {"message_throughput": metrics.message_throughput_per_sec}
                )
                
        except Exception as e:
            self.logger.error(f"Error checking alerts: {str(e)}")
    
    async def _send_alert(self, level: AlertLevel, component: str, message: str, metrics: Dict[str, Any]):
        """Send an alert if not in cooldown period."""
        try:
            current_time = time.time()
            alert_key = f"{component}_{level.value}"
            
            # Check cooldown
            if alert_key in self.last_alerts:
                if current_time - self.last_alerts[alert_key] < self.alert_cooldown:
                    return  # Still in cooldown
            
            # Create alert
            alert = MonitoringAlert(
                timestamp=current_time,
                level=level,
                component=component,
                message=message,
                metrics=metrics
            )
            
            # Log alert
            log_level = {
                AlertLevel.INFO: self.logger.info,
                AlertLevel.WARNING: self.logger.warning,
                AlertLevel.ERROR: self.logger.error,
                AlertLevel.CRITICAL: self.logger.critical
            }[level]
            
            log_level(f"ALERT [{level.value.upper()}] {component}: {message}")
            
            # Call alert callbacks
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {str(e)}")
            
            # Update last alert time
            self.last_alerts[alert_key] = current_time
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")
    
    def _calculate_message_rate(self, message_count: int) -> float:
        """Calculate message rate from previous measurement."""
        if not hasattr(self, '_last_message_count'):
            self._last_message_count = message_count
            self._last_rate_check = time.time()
            return 0
        
        current_time = time.time()
        time_diff = current_time - self._last_rate_check
        
        if time_diff > 0:
            rate = (message_count - self._last_message_count) / time_diff
        else:
            rate = 0
        
        self._last_message_count = message_count
        self._last_rate_check = current_time
        
        return max(0, rate)
    
    def _estimate_websocket_latency(self) -> float:
        """Estimate WebSocket latency (simplified implementation)."""
        # This is a simplified estimation
        # In production, you'd implement actual ping/pong measurement
        return 50.0  # Assume 50ms baseline latency
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        if not self.last_metrics:
            return {"status": "no_data", "message": "No metrics available yet"}
        
        metrics = self.last_metrics
        
        # Determine overall health
        issues = []
        
        if metrics.api_response_time_ms > self.thresholds['max_response_time']:
            issues.append(f"High API response time: {metrics.api_response_time_ms:.1f}ms")
        
        if metrics.error_rate_percent > self.thresholds['max_error_rate'] * 100:
            issues.append(f"High error rate: {metrics.error_rate_percent:.2f}%")
        
        if metrics.active_connections == 0:
            issues.append("WebSocket disconnected")
        
        if metrics.memory_usage_mb > self.thresholds['max_memory_usage']:
            issues.append(f"High memory usage: {metrics.memory_usage_mb:.1f}MB")
        
        if metrics.cpu_usage_percent > self.thresholds['max_cpu_usage']:
            issues.append(f"High CPU usage: {metrics.cpu_usage_percent:.1f}%")
        
        # Determine status
        if not issues:
            status = "healthy"
            health_score = 100
        elif len(issues) <= 2:
            status = "warning"
            health_score = 70
        else:
            status = "critical"
            health_score = 30
        
        return {
            "status": status,
            "health_score": health_score,
            "issues": issues,
            "last_update": datetime.fromtimestamp(metrics.timestamp).isoformat(),
            "metrics": asdict(metrics)
        }
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the specified period."""
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"error": "No data available for the specified period"}
        
        # Calculate averages
        avg_response_time = sum(m.api_response_time_ms for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.message_throughput_per_sec for m in recent_metrics) / len(recent_metrics)
        
        # Find extremes
        max_response_time = max(m.api_response_time_ms for m in recent_metrics)
        max_memory = max(m.memory_usage_mb for m in recent_metrics)
        max_cpu = max(m.cpu_usage_percent for m in recent_metrics)
        
        return {
            "period_hours": hours,
            "data_points": len(recent_metrics),
            "averages": {
                "api_response_time_ms": avg_response_time,
                "error_rate_percent": avg_error_rate,
                "memory_usage_mb": avg_memory,
                "cpu_usage_percent": avg_cpu,
                "message_throughput_per_sec": avg_throughput
            },
            "maximums": {
                "api_response_time_ms": max_response_time,
                "memory_usage_mb": max_memory,
                "cpu_usage_percent": max_cpu
            },
            "recommendations": self._get_performance_recommendations(recent_metrics)
        }
    
    def _get_performance_recommendations(self, metrics: List[PerformanceMetrics]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if not metrics:
            return recommendations
        
        avg_response_time = sum(m.api_response_time_ms for m in metrics) / len(metrics)
        avg_memory = sum(m.memory_usage_mb for m in metrics) / len(metrics)
        avg_cpu = sum(m.cpu_usage_percent for m in metrics) / len(metrics)
        max_memory = max(m.memory_usage_mb for m in metrics)
        
        if avg_response_time > 2000:
            recommendations.append("Consider implementing request caching to reduce API response times")
        
        if avg_memory > 256:
            recommendations.append("Memory usage is elevated - consider reducing cache sizes or implementing memory cleanup")
        
        if max_memory > 512:
            recommendations.append("Peak memory usage is high - monitor for memory leaks")
        
        if avg_cpu > 60:
            recommendations.append("CPU usage is consistently high - consider optimizing calculations or reducing update frequency")
        
        # Connection stability check
        disconnections = sum(1 for m in metrics if m.active_connections == 0)
        if disconnections > len(metrics) * 0.1:  # More than 10% disconnected
            recommendations.append("Frequent WebSocket disconnections detected - check network stability")
        
        return recommendations
    
    async def stop_monitoring(self):
        """Stop the monitoring system."""
        self.enabled = False
        self.logger.info("Binance monitoring stopped")

# Integration helper
async def setup_monitoring(config: Dict[str, Any], 
                          exchange=None, 
                          data_fetcher=None, 
                          websocket_handler=None) -> BinanceMonitor:
    """Set up and start Binance monitoring."""
    monitor = BinanceMonitor(config)
    monitor.register_components(exchange, data_fetcher, websocket_handler)
    
    # Start monitoring in background
    asyncio.create_task(monitor.start_monitoring())
    
    return monitor 