import logging
import os
import time
import json
import psutil
import asyncio
import datetime as dt
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Set, Tuple
import pandas as pd
import numpy as np
import traceback
from dataclasses import dataclass, field, asdict

from src.monitoring.metrics_manager import MetricsManager
from src.utils.task_tracker import create_tracked_task


@dataclass
class HealthStatus:
    """Data class to represent system health status."""
    status: str = "unknown"  # "healthy", "degraded", "critical", "unknown"
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage: float = 0.0
    disk_available_gb: float = 0.0
    uptime_seconds: int = 0
    timestamp: float = field(default_factory=time.time)
    api_statuses: Dict[str, str] = field(default_factory=dict)
    active_alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class HealthMetric:
    """Data class to represent a health metric over time."""
    name: str
    values: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    thresholds: Dict[str, float] = field(default_factory=dict)  # warning, critical
    
    def add_value(self, value: float, timestamp: Optional[float] = None) -> None:
        """Add a new value with timestamp."""
        self.values.append(value)
        self.timestamps.append(timestamp or time.time())
    
    def get_latest(self) -> Optional[float]:
        """Get the latest value."""
        if not self.values:
            return None
        return self.values[-1]
    
    def get_avg(self, window: int = 10) -> Optional[float]:
        """Get average over the last n values."""
        if not self.values:
            return None
        return np.mean(self.values[-window:])
    
    def is_warning(self) -> bool:
        """Check if latest value exceeds warning threshold."""
        latest = self.get_latest()
        if latest is None or 'warning' not in self.thresholds:
            return False
        return latest >= self.thresholds['warning']
    
    def is_critical(self) -> bool:
        """Check if latest value exceeds critical threshold."""
        latest = self.get_latest()
        if latest is None or 'critical' not in self.thresholds:
            return False
        return latest >= self.thresholds['critical']


@dataclass
class ApiHealth:
    """Data class to represent API health status."""
    exchange_id: str
    status: str = "unknown"  # "healthy", "degraded", "critical", "unknown"
    last_successful_call: float = 0
    last_failed_call: float = 0
    consecutive_failures: int = 0
    success_rate: float = 1.0  # 0.0 to 1.0
    avg_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    def record_success(self, response_time: float) -> None:
        """Record a successful API call."""
        self.status = "healthy" if self.consecutive_failures == 0 else "degraded"
        self.last_successful_call = time.time()
        self.consecutive_failures = 0
        self.response_times.append(response_time)
        
        # Keep last 100 response times
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        
        # Update average response time
        self.avg_response_time = sum(self.response_times) / len(self.response_times)
        
        # Update success rate
        total_calls = len(self.response_times) + sum(self.error_counts.values())
        if total_calls > 0:
            self.success_rate = len(self.response_times) / total_calls
    
    def record_failure(self, error_type: str) -> None:
        """Record a failed API call."""
        self.last_failed_call = time.time()
        self.consecutive_failures += 1
        
        # Update error counts
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Update success rate
        total_calls = len(self.response_times) + sum(self.error_counts.values())
        if total_calls > 0:
            self.success_rate = len(self.response_times) / total_calls
        
        # Update status based on consecutive failures
        if self.consecutive_failures >= 10:
            self.status = "critical"
        elif self.consecutive_failures >= 3:
            self.status = "degraded"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'exchange_id': self.exchange_id,
            'status': self.status,
            'last_successful_call': self.last_successful_call,
            'last_failed_call': self.last_failed_call,
            'consecutive_failures': self.consecutive_failures,
            'success_rate': self.success_rate,
            'avg_response_time': self.avg_response_time,
            'error_counts': self.error_counts
        }


@dataclass
class Alert:
    """Data class to represent an alert."""
    id: str
    level: str  # "info", "warning", "critical"
    source: str
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    resolution_timestamp: Optional[float] = None
    
    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.acknowledged = True
    
    def resolve(self) -> None:
        """Resolve the alert."""
        self.resolved = True
        self.resolution_timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class HealthMonitor:
    """Monitor system and API health."""
    
    def __init__(
        self, 
        metrics_manager: MetricsManager, 
        alert_callback: Optional[Callable[[Alert], None]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize HealthMonitor.
        
        Args:
            metrics_manager: Metrics manager instance
            alert_callback: Optional callback function for alerts
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.metrics_manager = metrics_manager
        self.alert_callback = alert_callback
        
        # Configure with reasonable defaults
        self.config = {
            'check_interval_seconds': 60,
            'history_length': 100,
            'cpu_warning_threshold': 80,
            'cpu_critical_threshold': 95,
            'memory_warning_threshold': 80,
            'memory_critical_threshold': 95,
            'disk_warning_threshold': 80,
            'disk_critical_threshold': 95,
            'api_degraded_threshold': 0.7,  # 70% success rate
            'api_critical_threshold': 0.5,  # 50% success rate
            'alert_log_path': 'logs/alerts.json'
        }
        
        # Update with any user-provided config
        if config:
            self.config.update(config)
        
        # Initialize health metrics
        self.metrics = {
            'cpu': HealthMetric(
                name='cpu',
                thresholds={
                    'warning': self.config['cpu_warning_threshold'],
                    'critical': self.config['cpu_critical_threshold']
                }
            ),
            'memory': HealthMetric(
                name='memory',
                thresholds={
                    'warning': self.config['memory_warning_threshold'],
                    'critical': self.config['memory_critical_threshold']
                }
            ),
            'disk': HealthMetric(
                name='disk',
                thresholds={
                    'warning': self.config['disk_warning_threshold'],
                    'critical': self.config['disk_critical_threshold']
                }
            )
        }
        
        # API health tracking
        self.api_health: Dict[str, ApiHealth] = {}
        
        # Alert management
        self.alerts: Dict[str, Alert] = {}
        self.active_alert_ids: Set[str] = set()
        
        # Ensure alert log directory exists
        Path(self.config['alert_log_path']).parent.mkdir(parents=True, exist_ok=True)
        
        # Background task
        self.monitoring_task = None
        self.running = False
    
    async def start_monitoring(self) -> None:
        """Start the health monitoring background task."""
        if self.running:
            self.logger.warning("Health monitoring is already running")
            return
        
        self.running = True
        self.logger.info("Starting health monitoring")
        
        # Create the monitoring task
        self.monitoring_task = create_tracked_task(self._monitoring_loop(), name="auto_tracked_task")
    
    async def stop_monitoring(self) -> None:
        """Stop the health monitoring background task."""
        if not self.running:
            self.logger.warning("Health monitoring is not running")
            return
        
        self.running = False
        self.logger.info("Stopping health monitoring")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            
            self.monitoring_task = None
    
    async def _monitoring_loop(self) -> None:
        """Background task to monitor system health."""
        try:
            while self.running:
                operation = self.metrics_manager.start_operation("health_check")
                
                try:
                    # Check system health
                    self._check_system_health()
                    
                    # Check API health for all registered APIs
                    for exchange_id in list(self.api_health.keys()):
                        self._check_api_health(exchange_id)
                    
                    # Generate overall health status
                    status = self._get_health_status()
                    
                    # Log current health status
                    self.logger.debug(f"Health status: {status.status}")
                    
                    # Record status with metrics manager
                    self.metrics_manager.record_metric('health_status', status.status)
                    self.metrics_manager.record_metric('cpu_usage', status.cpu_usage)
                    self.metrics_manager.record_metric('memory_usage', status.memory_usage)
                    self.metrics_manager.record_metric('disk_usage', status.disk_usage)
                    
                    self.metrics_manager.end_operation(operation)
                    
                except Exception as e:
                    self.logger.error(f"Error in health monitoring loop: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    self.metrics_manager.end_operation(operation, success=False)
                
                # Wait for next check interval
                await asyncio.sleep(self.config['check_interval_seconds'])
                
        except asyncio.CancelledError:
            self.logger.info("Health monitoring task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Unhandled exception in health monitoring task: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    def _check_system_health(self) -> None:
        """Check and record system health metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics['cpu'].add_value(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics['memory'].add_value(memory.percent)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.metrics['disk'].add_value(disk.percent)
        
        # Check for threshold violations and generate alerts
        self._check_threshold_violations()
    
    def _check_threshold_violations(self) -> None:
        """Check for threshold violations and generate alerts."""
        # Check CPU - Apply new CPU alerts configuration
        cpu_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})
        cpu_alerts_enabled = cpu_alerts_config.get('enabled', True)
        use_system_webhook = cpu_alerts_config.get('use_system_webhook', False)
        cpu_threshold = cpu_alerts_config.get('threshold', 
                                            self.config.get('cpu_warning_threshold', 80))
        cpu_cooldown = cpu_alerts_config.get('cooldown', 300)  # Default 5 minute cooldown
        
        # Update thresholds in the metric
        self.metrics['cpu'].thresholds['warning'] = cpu_threshold
        self.metrics['cpu'].thresholds['critical'] = cpu_threshold + 10  # Critical is 10% higher than warning
        
        if cpu_alerts_enabled:
            if self.metrics['cpu'].is_critical():
                self._create_alert(
                    level="critical",
                    source="system",
                    message=f"CPU usage is critical: {self.metrics['cpu'].get_latest()}%",
                    use_system_webhook=use_system_webhook
                )
            elif self.metrics['cpu'].is_warning():
                self._create_alert(
                    level="warning",
                    source="system",
                    message=f"CPU usage is high: {self.metrics['cpu'].get_latest()}%",
                    use_system_webhook=use_system_webhook
                )
        
        # Check Memory - Apply new memory tracking configuration
        memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})
        memory_warning_threshold = memory_tracking_config.get('warning_threshold_percent', 
                                                             self.config.get('memory_warning_threshold', 80))
        memory_critical_threshold = memory_tracking_config.get('critical_threshold_percent', 
                                                              self.config.get('memory_critical_threshold', 95))
        min_warning_size_mb = memory_tracking_config.get('min_warning_size_mb', 0)
        suppress_repeated = memory_tracking_config.get('suppress_repeated_warnings', False)
        disable_memory_warnings = memory_tracking_config.get('disable_memory_warnings', False)
        include_process_details = memory_tracking_config.get('include_process_details', True)
        
        # Update thresholds in the metric
        self.metrics['memory'].thresholds['warning'] = memory_warning_threshold
        self.metrics['memory'].thresholds['critical'] = memory_critical_threshold
        
        # Get current memory usage in MB
        memory = psutil.virtual_memory()
        current_memory_mb = memory.used / (1024 * 1024)
        total_memory_mb = memory.total / (1024 * 1024)
        available_memory_mb = memory.available / (1024 * 1024)
        
        # Only alert if memory usage is above minimum size threshold
        if current_memory_mb >= min_warning_size_mb:
            # Check for critical threshold
            if self.metrics['memory'].is_critical():
                # Get detailed memory information
                memory_details = self._get_detailed_memory_info() if include_process_details else ""
                
                self._create_alert(
                    level="critical",
                    source="system",
                    message=(
                        f"Memory usage is CRITICAL: {self.metrics['memory'].get_latest()}% ({current_memory_mb:.0f}MB)\n"
                        f"Total Memory: {total_memory_mb:.0f}MB\n"
                        f"Available Memory: {available_memory_mb:.0f}MB\n"
                        f"Used Memory: {current_memory_mb:.0f}MB\n"
                        f"{memory_details}"
                    )
                )
            # Check for warning threshold - only if warnings aren't disabled
            elif self.metrics['memory'].is_warning() and not disable_memory_warnings:
                # Check if we should suppress repeated warnings
                if not suppress_repeated or not self._has_recent_memory_warning():
                    log_level = memory_tracking_config.get('log_level', 'WARNING').upper()
                    
                    # Get detailed memory information
                    memory_details = self._get_detailed_memory_info() if include_process_details else ""
                    
                    # Create alert with appropriate level
                    self._create_alert(
                        level=log_level.lower(),
                        source="system",
                        message=(
                            f"Memory usage is high: {self.metrics['memory'].get_latest()}% ({current_memory_mb:.0f}MB)\n"
                            f"Total Memory: {total_memory_mb:.0f}MB\n"
                            f"Available Memory: {available_memory_mb:.0f}MB\n"
                            f"Used Memory: {current_memory_mb:.0f}MB\n"
                            f"{memory_details}"
                        )
                    )
        
        # Check Disk
        if self.metrics['disk'].is_critical():
            self._create_alert(
                level="critical",
                source="system",
                message=f"Disk usage is critical: {self.metrics['disk'].get_latest()}%"
            )
        elif self.metrics['disk'].is_warning():
            self._create_alert(
                level="warning",
                source="system",
                message=f"Disk usage is high: {self.metrics['disk'].get_latest()}%"
            )
    
    def _get_detailed_memory_info(self) -> str:
        """Get detailed memory information including top memory-consuming processes.
        
        Returns:
            str: Formatted string with memory details
        """
        try:
            # Get top 5 memory-consuming processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_percent': proc.info['memory_percent'],
                        'memory_mb': proc.info['memory_info'].rss / (1024 * 1024) if proc.info['memory_info'] else 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by memory usage (descending)
            processes.sort(key=lambda x: x['memory_mb'], reverse=True)
            
            # Format the top 5 processes
            process_info = "\nTop Memory-Consuming Processes:\n"
            for i, proc in enumerate(processes[:5]):
                process_info += f"{i+1}. {proc['name']} (PID: {proc['pid']}): {proc['memory_mb']:.1f}MB ({proc['memory_percent']:.1f}%)\n"
            
            # Add swap information
            swap = psutil.swap_memory()
            swap_info = (
                f"\nSwap Usage: {swap.percent}%\n"
                f"Swap Total: {swap.total / (1024 * 1024):.1f}MB\n"
                f"Swap Used: {swap.used / (1024 * 1024):.1f}MB"
            )
            
            return process_info + swap_info
            
        except Exception as e:
            self.logger.error(f"Error getting detailed memory info: {str(e)}")
            return "\nError getting detailed memory information"
    
    def _check_api_health(self, exchange_id: str) -> None:
        """Check health status of a specific API."""
        if exchange_id not in self.api_health:
            self.logger.warning(f"API health not found for exchange: {exchange_id}")
            return
        
        api_health = self.api_health[exchange_id]
        
        # Generate alerts based on API health
        if api_health.status == "critical":
            self._create_alert(
                level="critical",
                source=f"api:{exchange_id}",
                message=f"API communication with {exchange_id} is critical. "
                        f"{api_health.consecutive_failures} consecutive failures."
            )
        elif api_health.status == "degraded":
            self._create_alert(
                level="warning",
                source=f"api:{exchange_id}",
                message=f"API communication with {exchange_id} is degraded. "
                        f"Success rate: {api_health.success_rate:.1%}"
            )
        
        # Check for response time issues
        if api_health.avg_response_time > 5.0 and len(api_health.response_times) >= 5:
            self._create_alert(
                level="warning",
                source=f"api:{exchange_id}",
                message=f"Slow API response times for {exchange_id}. "
                        f"Average: {api_health.avg_response_time:.2f}s"
            )
    
    def _get_health_status(self) -> HealthStatus:
        """Generate overall system health status."""
        # Get latest metric values
        cpu_usage = self.metrics['cpu'].get_latest() or 0.0
        memory_usage = self.metrics['memory'].get_latest() or 0.0
        disk_usage = self.metrics['disk'].get_latest() or 0.0
        
        # Get memory and disk available
        memory_available_mb = psutil.virtual_memory().available / (1024 * 1024)
        disk_available_gb = psutil.disk_usage('/').free / (1024 * 1024 * 1024)
        
        # Determine overall status
        status = "healthy"
        
        # Check system metrics for status degradation
        if (self.metrics['cpu'].is_critical() or 
            self.metrics['memory'].is_critical() or 
            self.metrics['disk'].is_critical()):
            status = "critical"
        elif (self.metrics['cpu'].is_warning() or 
              self.metrics['memory'].is_warning() or 
              self.metrics['disk'].is_warning()):
            status = "degraded"
        
        # Check API statuses
        api_statuses = {}
        for exchange_id, api_health in self.api_health.items():
            api_statuses[exchange_id] = api_health.status
            
            # Upgrade overall status based on API health
            if api_health.status == "critical" and status != "critical":
                status = "critical"
            elif api_health.status == "degraded" and status == "healthy":
                status = "degraded"
        
        # Create health status object
        health_status = HealthStatus(
            status=status,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_available_mb=memory_available_mb,
            disk_usage=disk_usage,
            disk_available_gb=disk_available_gb,
            uptime_seconds=int(time.time() - psutil.boot_time()),
            api_statuses=api_statuses,
            active_alerts=[self.alerts[alert_id].to_dict() for alert_id in self.active_alert_ids]
        )
        
        return health_status
    
    def register_api(self, exchange_id: str) -> None:
        """Register an API for health monitoring."""
        if exchange_id not in self.api_health:
            self.logger.info(f"Registering API for health monitoring: {exchange_id}")
            self.api_health[exchange_id] = ApiHealth(exchange_id=exchange_id)
    
    def record_api_success(self, exchange_id: str, response_time: float) -> None:
        """Record a successful API call."""
        if exchange_id not in self.api_health:
            self.register_api(exchange_id)
        
        self.api_health[exchange_id].record_success(response_time)
        
        # If API was previously in critical state but is now healthy, create recovery alert
        if (self.api_health[exchange_id].status == "healthy" and 
            self.api_health[exchange_id].consecutive_failures == 0 and
            any(a.source == f"api:{exchange_id}" and a.level == "critical" and not a.resolved 
                for a in self.alerts.values())):
            
            # Resolve existing critical alerts for this API
            for alert in self.alerts.values():
                if (alert.source == f"api:{exchange_id}" and 
                    alert.level == "critical" and 
                    not alert.resolved):
                    alert.resolve()
                    if alert.id in self.active_alert_ids:
                        self.active_alert_ids.remove(alert.id)
            
            # Create recovery alert
            self._create_alert(
                level="info",
                source=f"api:{exchange_id}",
                message=f"API communication with {exchange_id} has recovered"
            )
    
    def record_api_failure(self, exchange_id: str, error_type: str) -> None:
        """Record a failed API call."""
        if exchange_id not in self.api_health:
            self.register_api(exchange_id)
        
        self.api_health[exchange_id].record_failure(error_type)
    
    def _create_alert(self, level: str, source: str, message: str, use_system_webhook: bool = False) -> None:
        """Create a new alert.
        
        Args:
            level: Alert level (info, warning, critical)
            source: Alert source (system, api, etc.)
            message: Alert message
            use_system_webhook: Whether to use the system webhook instead of the main webhook
        """
        # Filter out memory warnings completely
        if level.lower() == "warning" and ("memory" in message.lower() or "memory_usage" in message.lower()):
            memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})
            disable_memory_warnings = memory_tracking_config.get('disable_memory_warnings', False)
            if disable_memory_warnings:
                self.logger.debug(f"Suppressing memory warning alert: {message}")
                return
        
        # Check if this alert should be mirrored
        should_mirror = False
        mirror_to_both = False
        system_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('system_alerts', {})
        mirror_config = system_alerts_config.get('mirror_alerts', {})
        
        # Extract alert type from source and details
        alert_type = None
        source_parts = source.split(':')
        source_type = source_parts[0] if len(source_parts) > 0 else source
        
        # Map source type to alert type
        source_type_map = {
            'system': ['cpu', 'memory', 'disk'],
            'api': ['api', 'network'],
            'database': ['database'],
            'validator': ['validation'],
            'config': ['configuration'],
            'task': ['tasks'],
            'lifecycle': ['lifecycle'],
            'market_report': ['market_report'],
            'report': ['market_report']
        }
        
        # Check if the source maps to an alert type
        for map_source, alert_types in source_type_map.items():
            if source_type.lower() == map_source.lower():
                for a_type in alert_types:
                    if mirror_config.get('enabled', False) and mirror_config.get('types', {}).get(a_type, False):
                        should_mirror = True
                        mirror_to_both = True
                        alert_type = a_type
                        break
                if should_mirror:
                    break
        
        # If no direct mapping, check if this is a market report
        if not should_mirror and 'market report' in message.lower():
            if mirror_config.get('enabled', False) and mirror_config.get('types', {}).get('market_report', False):
                should_mirror = True
                mirror_to_both = True
                alert_type = 'market_report'
        
        # Check if this should use the system webhook (if not explicitly set and not mirroring)
        if not use_system_webhook and not mirror_to_both and system_alerts_config.get('enabled', False) and system_alerts_config.get('use_system_webhook', False):
            # Check if the source type is configured to use system webhook
            alert_types = system_alerts_config.get('types', {})
            
            # Check if any mapped alert types are enabled for system webhook
            for alert_category, alert_types_list in source_type_map.items():
                if source_type.lower() == alert_category.lower():
                    for alert_type in alert_types_list:
                        if alert_types.get(alert_type, False):
                            use_system_webhook = True
                            break
                    if use_system_webhook:
                        break
        
        # Generate a unique ID based on source and level
        alert_id = f"{source}:{level}:{int(time.time())}"
        
        # Check if a similar active alert already exists
        for existing_id in self.active_alert_ids:
            existing = self.alerts[existing_id]
            # If same source and level and was created in the last hour, don't create duplicate
            if (existing.source == source and 
                existing.level == level and 
                time.time() - existing.timestamp < 3600):
                return
        
        # Create the alert
        alert = Alert(
            id=alert_id,
            level=level,
            source=source,
            message=message
        )
        
        # Store the alert
        self.alerts[alert_id] = alert
        self.active_alert_ids.add(alert_id)
        
        # Log the alert
        if level == "critical":
            self.logger.critical(f"ALERT: {message}")
        elif level == "warning":
            self.logger.warning(f"ALERT: {message}")
        else:
            self.logger.info(f"ALERT: {message}")
        
        # Save to persistent storage
        self._save_alerts()
        
        # Call alert callback if provided
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {str(e)}")
        
        # Handle webhook routing based on mirroring configuration
        if mirror_to_both:
            # Send to both webhooks
            self._send_system_webhook(message, source, level, alert_type)
            # Main webhook will be handled by the alert manager
        elif use_system_webhook:
            # Send only to system webhook
            self._send_system_webhook(message, source, level, alert_type)
        # Otherwise, the main webhook will be used by default by the alert manager

    def _send_system_webhook(self, message: str, source: str, level: str, alert_type: str = None) -> None:
        """Send an alert to the system webhook.
        
        Args:
            message: Alert message
            source: Alert source
            level: Alert level
            alert_type: Alert type (e.g., cpu, memory, market_report)
        """
        try:
            # Get system webhook URL from config
            system_webhook_raw = self.config.get('monitoring', {}).get('alerts', {}).get('system_alerts_webhook_url', '')
            
            # Handle environment variable substitution
            if system_webhook_raw and system_webhook_raw.startswith('${') and system_webhook_raw.endswith('}'):
                env_var_name = system_webhook_raw[2:-1]  # Remove ${ and }
                system_webhook_url = os.getenv(env_var_name, '')
            else:
                system_webhook_url = system_webhook_raw or ''
            
            if not system_webhook_url:
                self.logger.warning("Cannot send system alert: webhook URL not set")
                return
            
            # Determine alert color
            color_map = {
                'info': 0x3498db,     # Blue
                'warning': 0xf39c12,  # Orange
                'error': 0xe74c3c,    # Red
                'critical': 0x9b59b6  # Purple
            }
            color = color_map.get(level.lower(), 0x95a5a6)  # Default to gray
            
            # Set title based on alert type or level
            if alert_type:
                title_map = {
                    'cpu': 'CPU Usage Alert',
                    'memory': 'Memory Usage Alert',
                    'disk': 'Disk Space Alert',
                    'database': 'Database Alert',
                    'api': 'API Alert',
                    'network': 'Network Alert',
                    'market_report': 'Market Report Generated'
                }
                title = title_map.get(alert_type, f"{level.capitalize()} Alert")
            else:
                title = f"{level.capitalize()} Alert"
                
            # Create webhook payload
            payload = {
                'username': 'Virtuoso System Monitor',
                'content': f'⚠️ **SYSTEM ALERT** ⚠️\n{message}',
                'embeds': [{
                    'title': title,
                    'color': color,
                    'description': message,
                    'fields': [
                        {
                            'name': 'Timestamp',
                            'value': f'<t:{int(time.time())}:F>',
                            'inline': True
                        },
                        {
                            'name': 'Environment',
                            'value': self.config.get('system', {}).get('environment', 'unknown'),
                            'inline': True
                        },
                        {
                            'name': 'Source',
                            'value': source,
                            'inline': True
                        },
                        {
                            'name': 'Level',
                            'value': level,
                            'inline': True
                        }
                    ],
                    'footer': {
                        'text': 'Virtuoso System Monitoring'
                    }
                }]
            }
            
            # For market reports, customize the message
            if alert_type == 'market_report':
                payload['content'] = f'📊 **MARKET REPORT NOTIFICATION** 📊'
                payload['embeds'][0]['title'] = 'Market Report Generated'
                payload['embeds'][0]['description'] = 'A new market report has been generated. See main channel for the full report with attachments.'
            
            # Send webhook asynchronously
            import threading
            threading.Thread(target=self._send_webhook_request, args=(system_webhook_url, payload)).start()
            
            self.logger.debug(f"System alert sent to webhook: {message}")
            
        except Exception as e:
            self.logger.error(f"Error sending system webhook alert: {str(e)}")
            
    def _send_webhook_request(self, webhook_url: str, payload: dict) -> None:
        """Send webhook request in a separate thread.
        
        Args:
            webhook_url: Webhook URL
            payload: Webhook payload
        """
        try:
            import requests
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code >= 400:
                self.logger.error(f"Error sending webhook: status {response.status_code}, response: {response.text}")
            
        except Exception as e:
            self.logger.error(f"Error in webhook request: {str(e)}")
            
    def _save_alerts(self) -> None:
        """Save alerts to persistent storage."""
        try:
            # Convert alerts to dictionaries
            alert_dicts = [alert.to_dict() for alert in self.alerts.values()]
            
            # Write to file
            with open(self.config['alert_log_path'], 'w') as f:
                json.dump(alert_dicts, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving alerts: {str(e)}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get list of active alerts."""
        return [self.alerts[alert_id] for alert_id in self.active_alert_ids]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledge()
            self._save_alerts()
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolve()
            if alert_id in self.active_alert_ids:
                self.active_alert_ids.remove(alert_id)
            self._save_alerts()
            return True
        return False
    
    def get_health_metrics_df(self) -> pd.DataFrame:
        """Convert health metrics to DataFrame for analysis."""
        # Prepare data
        data = []
        
        # Get all timestamps from all metrics
        all_timestamps = set()
        for metric_name, metric in self.metrics.items():
            all_timestamps.update(metric.timestamps)
        
        all_timestamps = sorted(all_timestamps)
        
        # Create rows for each timestamp
        for ts in all_timestamps:
            row = {'timestamp': ts}
            
            # Get the closest value for each metric
            for metric_name, metric in self.metrics.items():
                if not metric.timestamps:
                    continue
                    
                # Find the closest timestamp
                closest_idx = min(range(len(metric.timestamps)), 
                                  key=lambda i: abs(metric.timestamps[i] - ts))
                
                row[metric_name] = metric.values[closest_idx]
            
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_api_health_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of API health for all exchanges."""
        return {exchange_id: api_health.to_dict() 
                for exchange_id, api_health in self.api_health.items()}
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get summary of system health metrics."""
        return {
            'cpu': {
                'current': self.metrics['cpu'].get_latest(),
                'avg_10': self.metrics['cpu'].get_avg(10),
                'warning_threshold': self.metrics['cpu'].thresholds.get('warning'),
                'critical_threshold': self.metrics['cpu'].thresholds.get('critical')
            },
            'memory': {
                'current': self.metrics['memory'].get_latest(),
                'avg_10': self.metrics['memory'].get_avg(10),
                'warning_threshold': self.metrics['memory'].thresholds.get('warning'),
                'critical_threshold': self.metrics['memory'].thresholds.get('critical'),
                'available_mb': psutil.virtual_memory().available / (1024 * 1024)
            },
            'disk': {
                'current': self.metrics['disk'].get_latest(),
                'avg_10': self.metrics['disk'].get_avg(10),
                'warning_threshold': self.metrics['disk'].thresholds.get('warning'),
                'critical_threshold': self.metrics['disk'].thresholds.get('critical'),
                'available_gb': psutil.disk_usage('/').free / (1024 * 1024 * 1024)
            }
        }

    def _has_recent_memory_warning(self) -> bool:
        """Check if there was a recent memory warning alert."""
        memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})
        check_interval = memory_tracking_config.get('check_interval_seconds', 60)
        
        # Look for recent memory warnings
        current_time = time.time()
        for alert_id in self.active_alert_ids:
            alert = self.alerts.get(alert_id)
            if (alert and 
                alert.source == "system" and 
                "memory usage" in alert.message.lower() and
                current_time - alert.timestamp < check_interval):
                return True
        
        return False 