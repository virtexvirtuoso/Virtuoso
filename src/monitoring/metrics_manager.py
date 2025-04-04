import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import time
import psutil
import traceback
from logging import getLogger
import numpy as np
from scipy import stats
import asyncio
import math
import statistics
from collections import defaultdict, deque
import uuid
import os
import tracemalloc
from typing import Union

if TYPE_CHECKING:
    from .alert_manager import AlertManager

logger = getLogger(__name__)

class MetricsManager:
    """Manages system-wide metrics collection and monitoring."""
    
    def __init__(self, config: Dict[str, Any], alert_manager: 'AlertManager'):
        """Initialize the MetricsManager with configuration."""
        self.config = config
        self.alert_manager = alert_manager
        
        # Standardize configuration names
        metrics_config = config.get('metrics', {})
        self.metrics_interval_seconds = metrics_config.get('collection_interval', 60)
        self.metrics_history_size = metrics_config.get('history_size', 1000)
        self.metrics_alert_threshold = metrics_config.get('alert_threshold', 0.9)
        
        # Standardize metric store names
        self.performance_metrics = defaultdict(lambda: defaultdict(lambda: deque(maxlen=self.metrics_history_size)))
        self.system_metrics = defaultdict(lambda: defaultdict(float))
        self.last_metric_update = defaultdict(lambda: defaultdict(float))
        
        # Standardize task names
        self.collection_task = None
        self.monitoring_task = None
        
        self.logger = logging.getLogger(__name__)
        
        # Get thresholds from config
        self.thresholds = self.config.get('thresholds', {})
        self.performance_config = self.config.get('performance', {})
        self.system_config = self.config.get('system', {})
        
        # Initialize metrics storage with defaultdict(list)
        self._metrics = defaultdict(lambda: defaultdict(list))
        self._stats = defaultdict(dict)
        self._last_update = defaultdict(dict)
        self._collection_task: Optional[asyncio.Task] = None
        
        # Initialize metrics storage
        self.metrics = {}
        self.operation_metrics = {}
        self.api_call_counts = {}
        self.last_metrics_time = time.time()
        
        # Operation tracking
        self.operations = {}
        self.active_operations = {}
        
        # Error tracking
        self.errors = {}
        self.error_counts = {}
        
        # Memory tracking
        self.memory_snapshots = {}
        self.memory_baselines = {}
        self.memory_trends = {}
        
        # Initialize tracemalloc if enabled
        self.memory_tracking_enabled = self.config.get('monitoring', {}).get('memory_tracking', True)
        if self.memory_tracking_enabled:
            try:
                if not tracemalloc.is_tracing():
                    tracemalloc.start()
                self.logger.info("Memory tracking initialized with tracemalloc")
            except Exception as e:
                self.logger.warning(f"Failed to initialize tracemalloc: {str(e)}")
                self.memory_tracking_enabled = False
        
    async def start(self) -> None:
        """Start metrics collection."""
        if not self._collection_task:
            self._collection_task = asyncio.create_task(self._collect_system_metrics())
            logger.info("Metrics collection started")
            
    async def stop(self) -> None:
        """Stop metrics collection."""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
                
            self._collection_task = None
            logger.info("Metrics collection stopped")
            
    async def update_performance_metrics(self, processing_time: float,
                                    component: str,
                                    operation: str) -> None:
        """Update performance metrics."""
        try:
            metric_key = f"{component}_{operation}_time"
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Add to history
            self._metrics[component][operation].append(float(processing_time))
            
            # Update statistics
            times = [float(t) for t in self._metrics[component][operation]]
            if len(times) >= self.performance_config.get('min_samples', 10):
                self._stats[component][f"{operation}_avg"] = float(statistics.mean(times))
                self._stats[component][f"{operation}_min"] = float(min(times))
                self._stats[component][f"{operation}_max"] = float(max(times))
                self._stats[component][f"{operation}_std"] = float(statistics.stdev(times) if len(times) > 1 else 0)
                
                # Check for performance issues using configured thresholds
                slow_op_threshold = float(self.performance_config.get('slow_operation_threshold', 2.0))
                if float(processing_time) > float(self._stats[component][f"{operation}_avg"]) * slow_op_threshold:
                    if self.performance_config.get('log_slow_operations', True):
                        await self.alert_manager.send_alert(
                            level="WARNING",
                            message=f"High processing time for {component}.{operation}",
                            details={
                                'time': float(processing_time),
                                'average': float(self._stats[component][f"{operation}_avg"]),
                                'threshold': slow_op_threshold
                            }
                        )
                
            self._last_update[component][operation] = timestamp
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {str(e)}")
            logger.debug(traceback.format_exc())
            
    async def update_api_metrics(self, endpoint: str, status_code: int, response_time: float) -> None:
        """Update API-related metrics.
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            response_time: Response time in seconds
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Add to history
            self._metrics['api'][endpoint].append({
                'status_code': int(status_code),
                'response_time': float(response_time),
                'timestamp': timestamp
            })
            
            # Update statistics
            times = [float(m['response_time']) for m in self._metrics['api'][endpoint]]
            self._stats['api'][f"{endpoint}_avg"] = float(statistics.mean(times))
            self._stats['api'][f"{endpoint}_min"] = float(min(times))
            self._stats['api'][f"{endpoint}_max"] = float(max(times))
            
            # Check for API issues
            if status_code >= 400:
                await self.alert_manager.send_alert(
                    level="WARNING",
                    message=f"API error for {endpoint}",
                    details={
                        'status_code': int(status_code),
                        'response_time': float(response_time)
                    }
                )
            elif float(response_time) > float(self._stats['api'][f"{endpoint}_avg"]) * 2:
                await self.alert_manager.send_alert(
                    level="WARNING",
                    message=f"High API response time for {endpoint}",
                    details={
                        'time': float(response_time),
                        'average': float(self._stats['api'][f"{endpoint}_avg"])
                    }
                )
                
            self._last_update['api'][endpoint] = timestamp
            
        except Exception as e:
            logger.error(f"Error updating API metrics: {str(e)}")
            logger.debug(traceback.format_exc())
            
    async def update_monitoring_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update monitoring metrics.
        
        Args:
            metrics: Dictionary containing monitoring metrics:
                - total_messages: Total number of messages processed
                - invalid_messages: Number of invalid messages
                - delayed_messages: Number of delayed messages
                - error_count: Number of errors encountered
                - last_update_time: Last update timestamp
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Ensure metrics is a dictionary
            if not isinstance(metrics, dict):
                logger.error(f"Invalid metrics type: {type(metrics)}")
                return
                
            # Process monitoring metrics
            monitoring_metrics = {
                'total_messages': metrics.get('total_messages', 0),
                'invalid_messages': metrics.get('invalid_messages', 0),
                'delayed_messages': metrics.get('delayed_messages', 0),
                'error_count': metrics.get('error_count', 0)
            }
            
            # Update monitoring metrics
            for metric_name, value in monitoring_metrics.items():
                try:
                    float_value = float(value)
                    self._metrics['monitoring'][metric_name].append(float_value)
                    
                    # Update statistics if we have enough samples
                    values = list(self._metrics['monitoring'][metric_name])
                    if len(values) >= self.system_config.get('min_samples', 10):
                        self._stats['monitoring'][f"{metric_name}_avg"] = float(statistics.mean(values))
                        self._stats['monitoring'][f"{metric_name}_min"] = float(min(values))
                        self._stats['monitoring'][f"{metric_name}_max"] = float(max(values))
                        self._stats['monitoring'][f"{metric_name}_std"] = float(statistics.stdev(values) if len(values) > 1 else 0)
                        
                    # Check thresholds for specific metrics
                    if metric_name == 'invalid_messages':
                        invalid_threshold = float(self.system_config.get('invalid_messages_threshold', 100.0))
                        if float_value > invalid_threshold:
                            await self.alert_manager.send_alert(
                                level="WARNING",
                                message="High number of invalid messages",
                                details={
                                    'count': float_value,
                                    'threshold': invalid_threshold
                                }
                            )
                    elif metric_name == 'error_count':
                        error_threshold = float(self.system_config.get('error_count_threshold', 50.0))
                        if float_value > error_threshold:
                            await self.alert_manager.send_alert(
                                level="WARNING",
                                message="High error count",
                                details={
                                    'count': float_value,
                                    'threshold': error_threshold
                                }
                            )
                            
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing monitoring metric: {metric_name}={value}, error={str(e)}")
                    continue
            
            # Update last update timestamp
            self._last_update['monitoring']['metrics'] = timestamp
            
        except Exception as e:
            logger.error(f"Error updating monitoring metrics: {str(e)}")
            logger.debug(traceback.format_exc())

    async def update_system_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update system metrics.
        
        Args:
            metrics: Dictionary containing system metrics:
                - cpu_usage: CPU usage percentage
                - memory_usage: Memory usage percentage
                - disk_usage: Disk usage percentage
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Ensure metrics is a dictionary
            if not isinstance(metrics, dict):
                logger.error(f"Invalid metrics type: {type(metrics)}")
                return
                
            # Process system metrics
            system_metrics = {
                'cpu_usage': metrics.get('cpu_usage', 0),
                'memory_usage': metrics.get('memory_usage', 0),
                'disk_usage': metrics.get('disk_usage', 0)
            }
            
            # Update system metrics
            for metric_name, value in system_metrics.items():
                try:
                    float_value = float(value)
                    self._metrics['system'][metric_name].append(float_value)
                    
                    # Update statistics if we have enough samples
                    values = list(self._metrics['system'][metric_name])
                    if len(values) >= self.system_config.get('min_samples', 10):
                        self._stats['system'][f"{metric_name}_avg"] = float(statistics.mean(values))
                        self._stats['system'][f"{metric_name}_min"] = float(min(values))
                        self._stats['system'][f"{metric_name}_max"] = float(max(values))
                        self._stats['system'][f"{metric_name}_std"] = float(statistics.stdev(values) if len(values) > 1 else 0)
                        
                    # Check thresholds for system metrics
                    threshold = float(self.system_config.get(f'{metric_name}_threshold', 90.0))
                    if float_value > threshold:
                        # Skip memory warnings if disabled in config
                        if 'memory' in metric_name.lower():
                            memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})
                            disable_memory_warnings = memory_tracking_config.get('disable_memory_warnings', False)
                            if disable_memory_warnings and float_value < memory_tracking_config.get('critical_threshold_percent', 98):
                                self.logger.debug(f"Suppressing memory warning for {metric_name}: {float_value}% > {threshold}%")
                                continue
                        
                        await self.alert_manager.send_alert(
                            level="WARNING",
                            message=f"High {metric_name}",
                            details={
                                'value': float_value,
                                'threshold': threshold
                            }
                        )
                        
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing system metric: {metric_name}={value}, error={str(e)}")
                    continue
            
            # Update last update timestamp
            self._last_update['system']['metrics'] = timestamp
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {str(e)}")
            logger.debug(traceback.format_exc())

    async def _collect_system_metrics(self) -> None:
        """Collect system metrics periodically."""
        while True:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_times = psutil.cpu_times_percent()
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Update metrics
                await self.update_system_metrics({
                    'cpu_usage': float(cpu_percent),
                    'cpu_user': float(cpu_times.user),
                    'cpu_system': float(cpu_times.system),
                    'memory_usage': float(memory.percent),
                    'memory_available': int(memory.available),
                    'disk_usage': float(disk.percent),
                    'disk_free': int(disk.free)
                })
                
                await asyncio.sleep(int(self.metrics_interval_seconds))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting system metrics: {str(e)}")
                logger.debug(traceback.format_exc())
                await asyncio.sleep(5)  # Wait before retrying
                
    def get_performance_metrics(self, component: str) -> Dict[str, Any]:
        """Get performance metrics for component."""
        try:
            metrics = {}
            
            # Get all operations for component
            for operation in self._metrics[component].keys():
                times = list(self._metrics[component][operation])
                if not times:
                    continue
                    
                metrics[operation] = {
                    'current': float(times[-1]),
                    'average': float(self._stats[component][f"{operation}_avg"]),
                    'min': float(self._stats[component][f"{operation}_min"]),
                    'max': float(self._stats[component][f"{operation}_max"]),
                    'std_dev': float(self._stats[component][f"{operation}_std"]),
                    'samples': int(len(times))
                }
                
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {}
            
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        try:
            metrics = {}
            
            for metric_name in self._metrics['system'].keys():
                values = list(self._metrics['system'][metric_name])
                if not values:
                    continue
                    
                metrics[metric_name] = {
                    'current': float(values[-1]) if isinstance(values[-1], (int, float)) else values[-1],
                    'average': float(self._stats['system'][f"{metric_name}_avg"]),
                    'min': float(self._stats['system'][f"{metric_name}_min"]),
                    'max': float(self._stats['system'][f"{metric_name}_max"]),
                    'samples': int(len(values))
                }
                
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
            
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics.
        
        Returns:
            Dict[str, Any]: Metrics summary
        """
        return {
            'performance': {
                component: self.get_performance_metrics(component)
                for component in self._metrics.keys()
                if component != 'system'
            },
            'system': self.get_system_metrics(),
            'last_update': dict(self._last_update)
        }

    async def send_metric_alert(self, metric_name: str, value: float, threshold: float, message: str) -> None:
        """Send alert when metric exceeds threshold."""
        if self.alert_manager:
            await self.alert_manager.send_alert(
                level="WARNING",
                message=f"Metric Alert: {metric_name}\n{message}\nValue: {value}\nThreshold: {threshold}",
                details={
                    'metric': metric_name,
                    'value': value,
                    'threshold': threshold
                }
            )

    async def update_health_metrics(self, component: str, status: bool) -> None:
        """Update health metrics for a component.
        
        Args:
            component: Name of the component
            status: Health status (True if healthy, False if not)
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Add to history
            self._metrics['health'][component].append({
                'status': bool(status),
                'timestamp': timestamp
            })
            
            # Update statistics
            statuses = [m['status'] for m in self._metrics['health'][component]]
            self._stats['health'][f"{component}_uptime"] = float(sum(statuses) / len(statuses))
            
            # Check for health issues
            if not status:
                await self.alert_manager.send_alert(
                    level="WARNING",
                    message=f"Component {component} is unhealthy",
                    details={
                        'uptime': float(self._stats['health'][f"{component}_uptime"])
                    }
                )
                
            self._last_update['health'][component] = timestamp
            
        except Exception as e:
            logger.error(f"Error updating health metrics: {str(e)}")
            logger.debug(traceback.format_exc())

    async def update_analysis_metrics(self, symbol: str, scores: Dict[str, float]) -> None:
        """Update analysis metrics for a symbol
        
        Args:
            symbol: Trading symbol
            scores: Dictionary of analysis scores
        """
        try:
            # Update individual scores
            for indicator, score in scores.items():
                if indicator != 'confluence_score' and indicator != 'timestamp':
                    try:
                        # Skip non-numeric values
                        if isinstance(score, (int, float)):
                            value = float(score)
                        elif isinstance(score, str) and score.replace('.', '', 1).isdigit():
                            value = float(score)
                        else:
                            self.logger.debug(f"Skipping non-numeric score for {indicator}: {score}")
                            continue
                            
                        await self.update_metric(
                            name=f"analysis.{indicator}.score",
                            value=value,
                            tags={'symbol': symbol}
                        )
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Could not convert {indicator} score '{score}' to float: {str(e)}")
            
            # Update confluence score separately
            if 'confluence_score' in scores:
                try:
                    value = float(scores['confluence_score'])
                    await self.update_metric(
                        name="analysis.confluence.score",
                        value=value,
                        tags={'symbol': symbol}
                    )
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Could not convert confluence_score '{scores['confluence_score']}' to float: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error updating analysis metrics: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def update_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Update a single metric.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Add to history
            metric_data = {
                'value': float(value),
                'timestamp': timestamp,
                'tags': tags or {}
            }
            
            self._metrics[name]['values'].append(metric_data)
            
            # Update statistics
            values = [float(m['value']) for m in self._metrics[name]['values']]
            if len(values) >= 10:  # Only calculate stats with enough samples
                self._stats[name]['avg'] = float(statistics.mean(values))
                self._stats[name]['min'] = float(min(values))
                self._stats[name]['max'] = float(max(values))
                self._stats[name]['std'] = float(statistics.stdev(values) if len(values) > 1 else 0)
            
            self._last_update[name]['timestamp'] = timestamp
            
        except Exception as e:
            self.logger.error(f"Error updating metric {name}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def update_metrics(
        self,
        metrics: Dict[str, float],
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Update multiple metrics at once.
        
        Args:
            metrics: Dictionary of metric names and their values
            tags: Optional dictionary of tags to attach to the metrics
        """
        try:
            # Ensure metrics is a dictionary
            if not isinstance(metrics, dict):
                logger.error(f"Invalid metrics type: {type(metrics)}")
                return
                
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Process each metric
            for metric_name, value in metrics.items():
                try:
                    # Convert value to float if it's not already
                    try:
                        float_value = float(value)
                    except (ValueError, TypeError):
                        logger.error(f"Could not convert metric value to float: {metric_name}={value}")
                        continue
                        
                    # Add to history
                    self._metrics['system'][metric_name].append(float_value)
                    
                    # Update statistics if we have enough samples
                    values = list(self._metrics['system'][metric_name])
                    if len(values) >= self.system_config.get('min_samples', 10):
                        self._stats['system'][f"{metric_name}_avg"] = float(statistics.mean(values))
                        self._stats['system'][f"{metric_name}_min"] = float(min(values))
                        self._stats['system'][f"{metric_name}_max"] = float(max(values))
                        self._stats['system'][f"{metric_name}_std"] = float(statistics.stdev(values) if len(values) > 1 else 0)
                        
                    # Check thresholds if configured
                    threshold = self.thresholds.get(metric_name)
                    if threshold is not None:
                        try:
                            threshold_value = float(threshold)
                            if float_value > threshold_value:
                                await self.alert_manager.send_alert(
                                    level="WARNING",
                                    message=f"Metric {metric_name} exceeded threshold",
                                    details={
                                        'value': float_value,
                                        'threshold': threshold_value,
                                        'tags': tags
                                    }
                                )
                        except (ValueError, TypeError):
                            logger.error(f"Invalid threshold value for {metric_name}: {threshold}")
                            
                except Exception as e:
                    logger.error(f"Error processing metric: {metric_name}={value}, error={str(e)}")
                    continue
                    
            # Update last update timestamp
            self._last_update['system']['metrics'] = timestamp
            
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            logger.debug(traceback.format_exc())

    async def update_error_metrics(self, component: str, error_type: str, is_critical: bool = False) -> None:
        """Update error-related metrics.
        
        Args:
            component: Component where error occurred
            error_type: Type of error
            is_critical: Whether error is critical
        """
        try:
            metrics = {
                'error_count': 1,
                'critical_error_count': 1 if is_critical else 0
            }
            
            tags = {
                'component': component,
                'error_type': error_type,
                'severity': 'critical' if is_critical else 'error'
            }
            
            await self.update_metrics(metrics, tags)
            
        except Exception as e:
            logger.error(f"Error updating error metrics: {str(e)}")
            
    async def update_warning_metrics(self, component: str, warning_type: str) -> None:
        """Update warning-related metrics.
        
        Args:
            component: Component where warning occurred
            warning_type: Type of warning
        """
        try:
            metrics = {
                'warning_count': 1
            }
            
            tags = {
                'component': component,
                'warning_type': warning_type
            }
            
            await self.update_metrics(metrics, tags)
            
        except Exception as e:
            logger.error(f"Error updating warning metrics: {str(e)}")

    async def store_metrics(self, symbol: str, metrics: Dict[str, Any]) -> None:
        """Store analysis metrics for a symbol."""
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Store core metrics
            self._metrics[symbol]['history'].append({
                'timestamp': timestamp,
                'score': metrics.get('score', 0),
                'components': metrics.get('components', {}),
                'weights': metrics.get('weights', {})
            })
            
            # Trim old metrics
            max_history = self.config.get('metrics_history_size', 1000)
            if len(self._metrics[symbol]['history']) > max_history:
                self._metrics[symbol]['history'] = self._metrics[symbol]['history'][-max_history:]
                
            self.logger.debug(f"Stored metrics for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error storing metrics for {symbol}: {str(e)}")

    def store_metric(self, key: str, value: Any) -> None:
        """Store a single metric with the given key.
        
        Args:
            key: The key to store the metric under
            value: The metric value to store
        """
        try:
            if not hasattr(self, '_custom_metrics'):
                self._custom_metrics = {}
            
            self._custom_metrics[key] = {
                'value': value,
                'timestamp': datetime.now(timezone.utc)
            }
            
            self.logger.debug(f"Stored metric: {key}")
        except Exception as e:
            self.logger.error(f"Error storing metric {key}: {str(e)}")

    def start_operation(self, operation_name: str) -> Dict[str, Any]:
        """Start tracking an operation with performance metrics.
        
        Args:
            operation_name: Name of the operation to track
            
        Returns:
            Operation context dictionary
        """
        start_time = time.time()
        
        # Take memory snapshot before operation
        memory_before = self._get_memory_usage() if self.memory_tracking_enabled else 0
        tracemalloc_snapshot = None
        
        if self.memory_tracking_enabled:
            try:
                tracemalloc_snapshot = tracemalloc.take_snapshot()
            except Exception as e:
                self.logger.warning(f"Failed to take tracemalloc snapshot: {str(e)}")
        
        # Create operation context
        op_context = {
            "id": str(uuid.uuid4()),
            "name": operation_name,
            "start_time": start_time,
            "memory_before": memory_before,
            "tracemalloc_snapshot": tracemalloc_snapshot
        }
        
        # Store in active operations
        self.active_operations[op_context["id"]] = op_context
        
        # Initialize operation in metrics if needed
        if operation_name not in self.operation_metrics:
            self.operation_metrics[operation_name] = {
                "count": 0,
                "total_duration": 0,
                "min_duration": float('inf'),
                "max_duration": 0,
                "avg_duration": 0,
                "total_memory_change": 0,
                "last_memory_change": 0,
                "success_count": 0,
                "error_count": 0
            }
        
        self.logger.debug(f"Started operation: {operation_name}")
        return op_context
    
    def end_operation(self, op_context: Dict[str, Any], success: bool = True) -> float:
        """End tracking an operation and record metrics.
        
        Args:
            op_context: Operation context from start_operation
            success: Whether the operation completed successfully
            
        Returns:
            Duration of the operation in seconds
        """
        if not op_context or "id" not in op_context:
            self.logger.warning("Invalid operation context provided to end_operation")
            return 0
        
        # Get operation ID and check if it exists in active operations
        op_id = op_context["id"]
        if op_id not in self.active_operations:
            self.logger.warning(f"Operation {op_context.get('name', 'unknown')} not found in active operations")
            return 0
        
        # Calculate duration
        end_time = time.time()
        start_time = op_context["start_time"]
        duration = end_time - start_time
        
        # Get memory usage after operation
        memory_after = self._get_memory_usage() if self.memory_tracking_enabled else 0
        memory_change = memory_after - op_context["memory_before"] if self.memory_tracking_enabled else 0
        
        # Check for memory leaks using tracemalloc if available
        leak_report = None
        if self.memory_tracking_enabled and op_context.get("tracemalloc_snapshot"):
            try:
                current_snapshot = tracemalloc.take_snapshot()
                leak_report = self._analyze_memory_leak(op_context["tracemalloc_snapshot"], current_snapshot, op_context["name"])
            except Exception as e:
                self.logger.warning(f"Failed to analyze memory leak: {str(e)}")
        
        # Get operation name
        operation_name = op_context["name"]
        
        # Update operation metrics
        if operation_name in self.operation_metrics:
            metrics = self.operation_metrics[operation_name]
            metrics["count"] += 1
            metrics["total_duration"] += duration
            metrics["min_duration"] = min(metrics["min_duration"], duration)
            metrics["max_duration"] = max(metrics["max_duration"], duration)
            metrics["avg_duration"] = metrics["total_duration"] / metrics["count"]
            metrics["total_memory_change"] += memory_change
            metrics["last_memory_change"] = memory_change
            
            if success:
                metrics["success_count"] += 1
            else:
                metrics["error_count"] += 1
        
        # Remove from active operations
        self.active_operations.pop(op_id, None)
        
        # Log completion
        log_level = logging.DEBUG if success else logging.WARNING
        self.logger.log(log_level, f"Completed operation: {operation_name} in {duration:.3f}s (Memory change: {memory_change:.2f} MB)")
        
        # Log memory leak analysis if available
        if leak_report:
            self.logger.warning(f"Potential memory leak in {operation_name}: {leak_report}")
        
        return duration
    
    def record_metric(self, metric_name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value to record
            tags: Optional tags for the metric
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = {
                "values": [],
                "timestamps": [],
                "count": 0,
                "sum": 0,
                "min": float('inf'),
                "max": float('-inf'),
                "avg": 0,
                "last_value": None,
                "tags": set()
            }
        
        metric = self.metrics[metric_name]
        metric["values"].append(value)
        metric["timestamps"].append(time.time())
        metric["count"] += 1
        metric["sum"] += value
        metric["min"] = min(metric["min"], value)
        metric["max"] = max(metric["max"], value)
        metric["avg"] = metric["sum"] / metric["count"]
        metric["last_value"] = value
        
        # Store tags
        if tags:
            for tag_key, tag_value in tags.items():
                metric["tags"].add(f"{tag_key}:{tag_value}")
        
        # Limit values history to prevent excessive memory use
        max_history = self.config.get('monitoring', {}).get('max_metric_history', 1000)
        if len(metric["values"]) > max_history:
            metric["values"] = metric["values"][-max_history:]
            metric["timestamps"] = metric["timestamps"][-max_history:]
    
    def record_memory_usage(self, label: str = "general") -> float:
        """Record current memory usage with optional label.
        
        Args:
            label: Label for this memory snapshot
            
        Returns:
            Current memory usage in MB
        """
        if not self.memory_tracking_enabled:
            return 0
        
        current_time = time.time()
        memory_usage = self._get_memory_usage()
        
        # Create new entry if label doesn't exist
        if label not in self.memory_snapshots:
            self.memory_snapshots[label] = {
                "timestamps": [],
                "values": [],
                "baseline": memory_usage
            }
            self.memory_baselines[label] = memory_usage
        
        # Add to history
        self.memory_snapshots[label]["timestamps"].append(current_time)
        self.memory_snapshots[label]["values"].append(memory_usage)
        
        # Limit history length
        max_history = self.config.get('monitoring', {}).get('max_memory_history', 100)
        if len(self.memory_snapshots[label]["timestamps"]) > max_history:
            self.memory_snapshots[label]["timestamps"] = self.memory_snapshots[label]["timestamps"][-max_history:]
            self.memory_snapshots[label]["values"] = self.memory_snapshots[label]["values"][-max_history:]
        
        # Calculate trend
        if len(self.memory_snapshots[label]["values"]) >= 5:
            self._calculate_memory_trend(label)
        
        return memory_usage
    
    def _calculate_memory_trend(self, label: str) -> None:
        """Calculate memory usage trend for a label.
        
        Args:
            label: Memory snapshot label
        """
        if label not in self.memory_snapshots:
            return
        
        values = self.memory_snapshots[label]["values"]
        timestamps = self.memory_snapshots[label]["timestamps"]
        
        if len(values) < 5:
            return
        
        # Calculate slope of memory usage over time
        x = np.array(timestamps[-5:])
        y = np.array(values[-5:])
        
        try:
            slope, _, _, _, _ = stats.linregress(x, y)
            
            # Store trend information
            self.memory_trends[label] = {
                "slope": slope,  # MB/second
                "slope_per_hour": slope * 3600,  # MB/hour
                "baseline": self.memory_baselines[label],
                "current": values[-1],
                "change": values[-1] - self.memory_baselines[label]
            }
            
            # Get memory tracking configuration
            memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})
            min_warning_size_mb = memory_tracking_config.get('min_warning_size_mb', 0)
            warning_threshold_mb_per_hour = memory_tracking_config.get('warning_threshold_mb_per_hour', 10)
            disable_memory_warnings = memory_tracking_config.get('disable_memory_warnings', False)
            
            # Skip warnings if disabled
            if disable_memory_warnings:
                return
            
            # Only warn if current memory usage is above minimum threshold
            current_memory_mb = values[-1]
            if current_memory_mb >= min_warning_size_mb:
                # Check for significant upward trend (configurable threshold)
                if slope * 3600 > warning_threshold_mb_per_hour:
                    # Use configured log level
                    log_level = memory_tracking_config.get('log_level', 'WARNING').upper()
                    
                    # Get the appropriate logging method
                    log_method = getattr(self.logger, log_level.lower(), self.logger.warning)
                    
                    # Check if we should suppress repeated warnings
                    suppress_repeated = memory_tracking_config.get('suppress_repeated_warnings', False)
                    check_interval = memory_tracking_config.get('check_interval_seconds', 60)
                    
                    # Only log if not suppressing or enough time has passed since last warning
                    last_warning_time = getattr(self, f'_last_{label}_warning_time', 0)
                    current_time = time.time()
                    
                    if not suppress_repeated or (current_time - last_warning_time) >= check_interval:
                        log_method(f"Potential memory leak detected in {label}: +{slope * 3600:.2f} MB/hour")
                        # Update last warning time
                        setattr(self, f'_last_{label}_warning_time', current_time)
                
        except Exception as e:
            self.logger.warning(f"Failed to calculate memory trend for {label}: {str(e)}")
    
    def _analyze_memory_leak(self, snapshot1, snapshot2, operation_name: str) -> Optional[str]:
        """Analyze two tracemalloc snapshots to detect memory leaks.
        
        Args:
            snapshot1: First tracemalloc snapshot
            snapshot2: Second tracemalloc snapshot
            operation_name: Name of the operation being analyzed
            
        Returns:
            String describing potential memory leak, or None if no leak detected
        """
        if not snapshot1 or not snapshot2:
            return None
        
        # Compare snapshots
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        # Filter for significant allocations (more than 1MB)
        significant_stats = [stat for stat in top_stats if stat.size_diff > 1024 * 1024]
        
        if not significant_stats:
            return None
        
        # Format the top 3 memory consumers
        leak_info = []
        for i, stat in enumerate(significant_stats[:3]):
            frame = stat.traceback[0]
            filename = os.path.basename(frame.filename)
            line = frame.lineno
            leak_info.append(f"{filename}:{line}: +{stat.size_diff / 1024 / 1024:.2f}MB")
        
        return ", ".join(leak_info)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB.
        
        Returns:
            Memory usage in MB
        """
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except Exception as e:
            self.logger.warning(f"Failed to get memory usage: {str(e)}")
            return 0
    
    def record_api_call(self, endpoint: str, status_code: Optional[int] = None, duration: Optional[float] = None) -> None:
        """Record API call with status and duration.
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        if endpoint not in self.api_call_counts:
            self.api_call_counts[endpoint] = {
                "count": 0,
                "success_count": 0,
                "error_count": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "status_codes": {},
                "last_call_time": None
            }
        
        metric = self.api_call_counts[endpoint]
        current_time = time.time()
        
        # Update counts
        metric["count"] += 1
        metric["last_call_time"] = current_time
        
        # Update status code counts
        if status_code is not None:
            if status_code not in metric["status_codes"]:
                metric["status_codes"][status_code] = 0
            metric["status_codes"][status_code] += 1
            
            # Update success/error counts
            if 200 <= status_code < 300:
                metric["success_count"] += 1
            else:
                metric["error_count"] += 1
        
        # Update duration stats
        if duration is not None:
            metric["total_duration"] += duration
            metric["avg_duration"] = metric["total_duration"] / metric["count"]
            
            # Record as a time-series metric as well
            self.record_metric(f"api.{endpoint}.duration", duration)
        
        # Record call count as a metric
        self.record_metric(f"api.{endpoint}.calls", 1)
        
        # Log API call
        log_level = logging.DEBUG
        log_msg = f"API call: {endpoint}"
        if status_code is not None:
            log_msg += f" (Status: {status_code})"
        if duration is not None:
            log_msg += f" in {duration:.3f}s"
        
        self.logger.log(log_level, log_msg)
    
    def record_error(self, context: str, error_message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record an error with context.
        
        Args:
            context: Error context (e.g., operation name)
            error_message: Error message
            details: Additional error details
        """
        current_time = time.time()
        
        # Initialize context if needed
        if context not in self.errors:
            self.errors[context] = []
            self.error_counts[context] = 0
        
        # Add error
        self.errors[context].append({
            "timestamp": current_time,
            "message": error_message,
            "details": details or {}
        })
        
        # Update count
        self.error_counts[context] += 1
        
        # Limit error history
        max_errors = self.config.get('monitoring', {}).get('max_error_history', 100)
        if len(self.errors[context]) > max_errors:
            self.errors[context] = self.errors[context][-max_errors:]
        
        # Record as a metric
        self.record_metric(f"errors.{context}", 1)
        
        # Log error
        self.logger.error(f"Error in {context}: {error_message}")
    
    def get_metrics_report(self) -> Dict[str, Any]:
        """Get a comprehensive metrics report.
        
        Returns:
            Dictionary containing metrics report
        """
        current_time = time.time()
        
        # Calculate reporting interval
        interval = current_time - self.last_metrics_time
        self.last_metrics_time = current_time
        
        report = {
            "timestamp": current_time,
            "interval_seconds": interval,
            "metrics": {},
            "operations": {},
            "api_calls": {},
            "errors": {},
            "memory": {}
        }
        
        # Add metrics
        for name, metric in self.metrics.items():
            report["metrics"][name] = {
                "count": metric["count"],
                "sum": metric["sum"],
                "min": metric["min"] if metric["min"] != float('inf') else None,
                "max": metric["max"] if metric["max"] != float('-inf') else None,
                "avg": metric["avg"],
                "last_value": metric["last_value"],
                "tags": list(metric["tags"])
            }
        
        # Add operation metrics
        for name, op_metrics in self.operation_metrics.items():
            report["operations"][name] = {
                "count": op_metrics["count"],
                "total_duration": op_metrics["total_duration"],
                "min_duration": op_metrics["min_duration"] if op_metrics["min_duration"] != float('inf') else None,
                "max_duration": op_metrics["max_duration"],
                "avg_duration": op_metrics["avg_duration"],
                "success_rate": op_metrics["success_count"] / op_metrics["count"] if op_metrics["count"] > 0 else None,
                "total_memory_change": op_metrics["total_memory_change"],
                "last_memory_change": op_metrics["last_memory_change"]
            }
        
        # Add API call metrics
        for endpoint, api_metrics in self.api_call_counts.items():
            report["api_calls"][endpoint] = {
                "count": api_metrics["count"],
                "success_count": api_metrics["success_count"],
                "error_count": api_metrics["error_count"],
                "avg_duration": api_metrics["avg_duration"],
                "status_codes": api_metrics["status_codes"]
            }
        
        # Add error counts
        for context, count in self.error_counts.items():
            report["errors"][context] = count
        
        # Add memory trends
        for label, trend in self.memory_trends.items():
            report["memory"][label] = {
                "current_mb": trend["current"],
                "change_mb": trend["change"],
                "trend_mb_per_hour": trend["slope_per_hour"]
            }
        
        return report
    
    def generate_memory_report(self) -> Dict[str, Any]:
        """Generate a detailed memory usage report.
        
        Returns:
            Dictionary containing memory report
        """
        if not self.memory_tracking_enabled:
            return {"error": "Memory tracking not enabled"}
        
        report = {
            "current_usage_mb": self._get_memory_usage(),
            "trends": self.memory_trends,
            "snapshots": {},
            "top_consumers": []
        }
        
        # Add snapshot summaries
        for label, snapshot in self.memory_snapshots.items():
            if snapshot["values"]:
                report["snapshots"][label] = {
                    "baseline_mb": snapshot["baseline"],
                    "current_mb": snapshot["values"][-1],
                    "change_mb": snapshot["values"][-1] - snapshot["baseline"],
                    "num_samples": len(snapshot["values"])
                }
        
        # Get top memory consumers using tracemalloc
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            # Get top 10 memory consumers
            for i, stat in enumerate(top_stats[:10]):
                frame = stat.traceback[0]
                filename = os.path.basename(frame.filename)
                line = frame.lineno
                size_mb = stat.size / 1024 / 1024
                
                report["top_consumers"].append({
                    "rank": i + 1,
                    "location": f"{filename}:{line}",
                    "size_mb": size_mb
                })
        except Exception as e:
            report["top_consumers_error"] = str(e)
        
        return report
    
    def print_metrics_summary(self) -> None:
        """Print a summary of metrics to the logs."""
        report = self.get_metrics_report()
        
        self.logger.info("\n===== METRICS SUMMARY =====")
        self.logger.info(f"Reporting interval: {report['interval_seconds']:.2f}s")
        
        # Log top operations by duration
        self.logger.info("\n----- OPERATIONS BY DURATION -----")
        operations = sorted(
            [(name, data["avg_duration"]) for name, data in report["operations"].items()],
            key=lambda x: x[1] if x[1] is not None else 0,
            reverse=True
        )
        
        for name, duration in operations[:10]:  # Top 10
            count = report["operations"][name]["count"]
            success_rate = report["operations"][name]["success_rate"]
            self.logger.info(f"{name}: {duration:.3f}s avg ({count} calls, {success_rate*100:.1f}% success)")
        
        # Log top API endpoints
        self.logger.info("\n----- API CALLS -----")
        api_calls = sorted(
            [(endpoint, data["count"]) for endpoint, data in report["api_calls"].items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        for endpoint, count in api_calls[:10]:  # Top 10
            avg_duration = report["api_calls"][endpoint]["avg_duration"]
            self.logger.info(f"{endpoint}: {count} calls, {avg_duration:.3f}s avg")
        
        # Log memory usage
        self.logger.info("\n----- MEMORY USAGE -----")
        memory_report = self.generate_memory_report()
        self.logger.info(f"Current usage: {memory_report['current_usage_mb']:.2f} MB")
        
        # Log memory trends
        for label, trend in memory_report.get("trends", {}).items():
            self.logger.info(f"{label}: {trend['current_mb']:.2f} MB "
                            f"({trend['change_mb']:+.2f} MB change, "
                            f"{trend['trend_mb_per_hour']:+.2f} MB/hour)")
        
        # Log errors
        self.logger.info("\n----- ERRORS -----")
        error_counts = sorted(
            [(context, count) for context, count in report["errors"].items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        for context, count in error_counts:
            self.logger.info(f"{context}: {count} errors")
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics = {}
        self.operation_metrics = {}
        self.api_call_counts = {}
        self.errors = {}
        self.error_counts = {}
        
        # Keep memory baselines but reset snapshots
        for label in self.memory_snapshots:
            current = self._get_memory_usage()
            self.memory_snapshots[label] = {
                "timestamps": [time.time()],
                "values": [current],
                "baseline": current
            }
            self.memory_baselines[label] = current
        
        self.memory_trends = {}
        self.last_metrics_time = time.time()
        
        self.logger.info("Metrics reset completed")