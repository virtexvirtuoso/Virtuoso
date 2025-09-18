"""
Metrics Tracker Module

Handles performance monitoring, system health checks, and metrics tracking
for the Virtuoso CCXT trading system.

This module is responsible for:
- Tracking system performance metrics
- Monitoring health of various components
- Generating health status reports
- Managing resource usage monitoring
- Providing statistics and diagnostics
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, List, Any, Optional
import psutil

from src.core.error.models import ErrorContext, ErrorSeverity


class MetricsTracker:
    """
    Handles metrics tracking and system health monitoring.
    
    Provides comprehensive monitoring of system resources, component health,
    and performance metrics for the trading system.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        metrics_manager,
        market_data_manager,
        exchange_manager=None,
        error_handler=None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Metrics Tracker.
        
        Args:
            config: Configuration dictionary
            metrics_manager: Metrics manager instance
            market_data_manager: Market data manager instance
            exchange_manager: Exchange manager instance
            error_handler: Error handler instance
            logger: Logger instance
        """
        self.config = config
        self.metrics_manager = metrics_manager
        self.market_data_manager = market_data_manager
        self.exchange_manager = exchange_manager
        self.error_handler = error_handler
        self.logger = logger or logging.getLogger(__name__)
        
        # Internal statistics tracking
        self._stats = {
            'total_messages': 0,
            'invalid_messages': 0,
            'delayed_messages': 0,
            'error_count': 0,
            'last_update_time': None,
            'start_time': time.time()
        }
        
        # Health check thresholds
        self.health_thresholds = self.config.get('monitoring', {}).get('health_thresholds', {
            'memory_usage_warning': 85.0,
            'memory_usage_critical': 95.0,
            'cpu_usage_warning': 80.0,
            'cpu_usage_critical': 90.0,
            'websocket_message_timeout': 60,
            'data_freshness_warning': 300,  # 5 minutes
            'data_freshness_critical': 900  # 15 minutes
        })
        
        self.logger.info("Metrics Tracker initialized")

    async def initialize(self) -> bool:
        """Initialize the metrics tracker.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Metrics tracker is already initialized in __init__
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize MetricsTracker: {str(e)}")
            return False

    async def update_symbol_metrics(self, symbol: str, metrics: Dict[str, Any]) -> None:
        """Update metrics for a specific symbol.
        
        Args:
            symbol: Trading symbol
            metrics: Metrics dictionary
        """
        try:
            # Update symbol-specific metrics
            if not hasattr(self, 'symbol_metrics'):
                self.symbol_metrics = {}
            
            if symbol not in self.symbol_metrics:
                self.symbol_metrics[symbol] = {}
            
            self.symbol_metrics[symbol].update(metrics)
        except Exception as e:
            self.logger.error(f"Error updating symbol metrics for {symbol}: {str(e)}")

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics.
        
        Returns:
            Dictionary of system metrics
        """
        try:
            health_check = await self.check_system_health()
            memory_usage = await self.check_memory_usage()
            cpu_usage = await self.check_cpu_usage()
            
            return {
                'health': health_check,
                'memory': memory_usage,
                'cpu': cpu_usage,
                'timestamp': time.time()
            }
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {str(e)}")
            return {'error': str(e)}

    async def update_metrics(self, analysis_results: Optional[List[Dict[str, Any]]] = None) -> None:
        """Update monitoring metrics."""
        try:
            if not self.metrics_manager:
                return
                
            # Convert all values to float and ensure they are numeric
            metrics = {
                'total_messages': float(self._stats['total_messages']),
                'invalid_messages': float(self._stats['invalid_messages']),
                'delayed_messages': float(self._stats['delayed_messages']),
                'error_count': float(self._stats['error_count']),
                'last_update_time': float(time.time()),
                'uptime_seconds': float(time.time() - self._stats['start_time'])
            }
            
            # Add market data manager stats
            try:
                mdm_stats = self.market_data_manager.get_stats()
                metrics.update({
                    'rest_calls': float(mdm_stats.get('rest_calls', 0)),
                    'websocket_updates': float(mdm_stats.get('websocket_updates', 0)),
                })
            except Exception as e:
                self.logger.warning(f"Error getting market data manager stats: {str(e)}")
            
            # Add analysis results metrics if available
            if analysis_results:
                metrics.update({
                    'analysis_results_count': float(len(analysis_results)),
                    'avg_confluence_score': float(sum(r.get('confluence_score', 0) for r in analysis_results) / len(analysis_results)),
                    'signals_generated': float(sum(1 for r in analysis_results if r.get('signal_type') in ['BUY', 'SELL']))
                })
            
            # Update monitoring metrics as system metrics
            await self.metrics_manager.update_system_metrics(metrics)
            self._stats['last_update_time'] = time.time()
            
        except Exception as e:
            self._stats['error_count'] += 1
            await self._handle_metrics_error(e, "update_metrics")

    async def update_analysis_metrics(self, symbol: str, result: Dict[str, Any]) -> None:
        """Bridge method to update analysis metrics from monitor.SignalProcessor.
        Accepts the full analysis result dict and forwards numeric components to MetricsManager.update_analysis_metrics.
        """
        try:
            if not self.metrics_manager:
                return
            # Build a compact numeric score map
            scores: Dict[str, float] = {}
            # Overall
            if isinstance(result.get('confluence_score'), (int, float)):
                scores['confluence_score'] = float(result['confluence_score'])
            if isinstance(result.get('reliability'), (int, float)):
                scores['reliability'] = float(result['reliability'])
            # Components (may be dicts or floats)
            components = result.get('components', {}) or {}
            if isinstance(components, dict):
                for k, v in components.items():
                    if isinstance(v, (int, float)):
                        scores[k] = float(v)
                    elif isinstance(v, dict) and isinstance(v.get('score'), (int, float)):
                        scores[k] = float(v['score'])
            # Timestamp
            scores['timestamp'] = float(time.time())
            await self.metrics_manager.update_analysis_metrics(symbol, scores)
        except Exception as e:
            await self._handle_metrics_error(e, "update_analysis_metrics")

    async def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': time.time(),
                'components': {
                    'exchange': await self.check_exchange_health(),
                    'database': await self.check_database_health(),
                    'memory': await self.check_memory_usage(),
                    'cpu': await self.check_cpu_usage(),
                    'market_data_manager': await self.check_market_data_manager_health()
                }
            }
            
            # Determine overall status based on components
            overall_status = 'healthy'
            for component, status in health_status['components'].items():
                component_status = status.get('status', 'error')
                
                if component_status == 'critical':
                    overall_status = 'critical'
                    break
                elif component_status in ['warning', 'error'] and overall_status == 'healthy':
                    overall_status = 'warning'
            
            health_status['status'] = overall_status
            
            # Add summary information
            health_status['summary'] = self._generate_health_summary(health_status['components'])
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }

    async def check_exchange_health(self) -> Dict[str, Any]:
        """Check exchange connectivity and response times."""
        try:
            if not self.exchange_manager:
                return {
                    'status': 'warning',
                    'message': 'Exchange not initialized'
                }
                
            # Test API connection
            start_time = time.time()
            await self.exchange_manager.ping()
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Determine status based on response time
            status = 'healthy'
            if response_time > 5000:  # 5 seconds
                status = 'critical'
            elif response_time > 2000:  # 2 seconds
                status = 'warning'
            
            return {
                'status': status,
                'response_time_ms': response_time,
                'message': f'API response time: {response_time:.1f}ms'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Exchange connectivity error: {str(e)}'
            }

    async def check_market_data_manager_health(self) -> Dict[str, Any]:
        """Check health of the market data manager."""
        try:
            stats = self.market_data_manager.get_stats()
            websocket_status = stats.get('websocket', {})
            
            # Check WebSocket connection
            if not websocket_status.get('connected', False):
                return {
                    'status': 'warning',
                    'message': 'WebSocket not connected',
                    'details': websocket_status
                }
            
            # Check time since last WebSocket message
            seconds_since_last_message = websocket_status.get('seconds_since_last_message', 0)
            if seconds_since_last_message > self.health_thresholds['websocket_message_timeout']:
                status = 'critical' if seconds_since_last_message > 300 else 'warning'
                return {
                    'status': status,
                    'message': f'No WebSocket message received in {seconds_since_last_message:.1f}s',
                    'details': websocket_status
                }
            
            # Check data freshness (oldest symbol data)
            if 'data_freshness' in stats:
                max_age = 0
                oldest_symbol = None
                
                for symbol, freshness in stats['data_freshness'].items():
                    age = freshness.get('age_seconds', 0)
                    if age > max_age:
                        max_age = age
                        oldest_symbol = symbol
                
                if max_age > self.health_thresholds['data_freshness_critical']:
                    return {
                        'status': 'critical',
                        'message': f'Data for {oldest_symbol} is {max_age:.1f}s old',
                        'details': {
                            'oldest_symbol': oldest_symbol,
                            'age_seconds': max_age
                        }
                    }
                elif max_age > self.health_thresholds['data_freshness_warning']:
                    return {
                        'status': 'warning',
                        'message': f'Data for {oldest_symbol} is {max_age:.1f}s old',
                        'details': {
                            'oldest_symbol': oldest_symbol,
                            'age_seconds': max_age
                        }
                    }
            
            # All checks passed
            return {
                'status': 'healthy',
                'message': 'Market data manager operating normally',
                'websocket_connected': True,
                'last_message_age': seconds_since_last_message
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Market data manager health check failed: {str(e)}'
            }

    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            # TODO: Implement actual database health check
            # This would depend on the specific database being used
            return {
                'status': 'healthy',
                'message': 'Database connectivity check not implemented'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Database health check error: {str(e)}'
            }

    async def check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            # Determine status based on thresholds
            status = 'healthy'
            memory_critical = self.health_thresholds.get('memory_usage_critical', 95.0)
            memory_warning = self.health_thresholds.get('memory_usage_warning', 85.0)
            
            if usage_percent >= memory_critical:
                status = 'critical'
            elif usage_percent >= memory_warning:
                status = 'warning'
            
            return {
                'status': status,
                'usage_percent': usage_percent,
                'available_mb': memory.available // (1024 * 1024),
                'total_mb': memory.total // (1024 * 1024),
                'message': f'Memory usage: {usage_percent:.1f}%'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Memory check error: {str(e)}'
            }

    async def check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Determine status based on thresholds
            status = 'healthy'
            cpu_critical = self.health_thresholds.get('cpu_usage_critical', 95.0)
            cpu_warning = self.health_thresholds.get('cpu_usage_warning', 80.0)
            
            if cpu_percent >= cpu_critical:
                status = 'critical'
            elif cpu_percent >= cpu_warning:
                status = 'warning'
            
            return {
                'status': status,
                'usage_percent': cpu_percent,
                'core_count': psutil.cpu_count(),
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'message': f'CPU usage: {cpu_percent:.1f}%'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'CPU check error: {str(e)}'
            }

    async def check_thresholds(self) -> List[Dict[str, Any]]:
        """Check monitoring thresholds and generate alerts."""
        alerts = []
        
        try:
            # Check message processing ratios
            if self._stats['total_messages'] > 0:
                invalid_ratio = self._stats['invalid_messages'] / self._stats['total_messages']
                if invalid_ratio > 0.1:  # More than 10% invalid messages
                    alerts.append({
                        'type': 'threshold_violation',
                        'component': 'message_processing',
                        'metric': 'invalid_message_ratio',
                        'value': invalid_ratio,
                        'threshold': 0.1,
                        'severity': 'warning',
                        'message': f'High invalid message ratio: {invalid_ratio:.2%}'
                    })
                
                delayed_ratio = self._stats['delayed_messages'] / self._stats['total_messages']
                if delayed_ratio > 0.05:  # More than 5% delayed messages
                    alerts.append({
                        'type': 'threshold_violation',
                        'component': 'message_processing',
                        'metric': 'delayed_message_ratio',
                        'value': delayed_ratio,
                        'threshold': 0.05,
                        'severity': 'warning',
                        'message': f'High delayed message ratio: {delayed_ratio:.2%}'
                    })
            
            # Check error rate
            uptime_hours = (time.time() - self._stats['start_time']) / 3600
            if uptime_hours > 0:
                error_rate = self._stats['error_count'] / uptime_hours
                if error_rate > 10:  # More than 10 errors per hour
                    alerts.append({
                        'type': 'threshold_violation',
                        'component': 'system',
                        'metric': 'error_rate_per_hour',
                        'value': error_rate,
                        'threshold': 10,
                        'severity': 'warning' if error_rate < 50 else 'critical',
                        'message': f'High error rate: {error_rate:.1f} errors/hour'
                    })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error checking thresholds: {str(e)}")
            return [{
                'type': 'system_error',
                'component': 'metrics_tracker',
                'message': f'Threshold check failed: {str(e)}',
                'severity': 'error'
            }]

    def get_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics."""
        uptime = time.time() - self._stats['start_time']
        
        stats = {
            'uptime_seconds': uptime,
            'uptime_formatted': self._format_uptime(uptime),
            'total_messages': self._stats['total_messages'],
            'invalid_messages': self._stats['invalid_messages'],
            'delayed_messages': self._stats['delayed_messages'],
            'error_count': self._stats['error_count'],
            'last_update_time': self._stats['last_update_time']
        }
        
        # Add calculated rates
        if uptime > 0:
            stats.update({
                'messages_per_second': self._stats['total_messages'] / uptime,
                'errors_per_hour': (self._stats['error_count'] / uptime) * 3600,
                'invalid_message_rate': self._stats['invalid_messages'] / max(self._stats['total_messages'], 1)
            })
        
        return stats

    def record_message(self, is_valid: bool = True, is_delayed: bool = False) -> None:
        """Record a processed message."""
        self._stats['total_messages'] += 1
        
        if not is_valid:
            self._stats['invalid_messages'] += 1
            
        if is_delayed:
            self._stats['delayed_messages'] += 1

    def record_error(self) -> None:
        """Record an error occurrence."""
        self._stats['error_count'] += 1

    def _generate_health_summary(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of component health."""
        summary = {
            'healthy': 0,
            'warning': 0,
            'critical': 0,
            'error': 0,
            'total': len(components)
        }
        
        issues = []
        
        for component, status in components.items():
            component_status = status.get('status', 'error')
            summary[component_status] = summary.get(component_status, 0) + 1
            
            if component_status != 'healthy':
                issues.append({
                    'component': component,
                    'status': component_status,
                    'message': status.get('message', 'Unknown issue')
                })
        
        summary['issues'] = issues
        return summary

    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        uptime = int(uptime_seconds)
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    async def _handle_metrics_error(self, error: Exception, operation: str) -> None:
        """Handle errors in metrics operations."""
        if self.error_handler:
            error_context = ErrorContext(
                component="metrics_tracker",
                operation=operation
            )
            await self.error_handler.handle_error(
                error=error,
                context=error_context,
                severity=ErrorSeverity.LOW
            )
        else:
            self.logger.error(f"Error in {operation}: {str(error)}")
            self.logger.debug(traceback.format_exc())

    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        try:
            stats = self.get_stats()
            health = await self.check_system_health()
            alerts = await self.check_thresholds()
            
            report = {
                'timestamp': time.time(),
                'system_health': health,
                'statistics': stats,
                'alerts': alerts,
                'performance_metrics': {
                    'message_processing_rate': stats.get('messages_per_second', 0),
                    'error_rate': stats.get('errors_per_hour', 0),
                    'data_quality': {
                        'invalid_message_rate': stats.get('invalid_message_rate', 0),
                        'delayed_message_count': stats.get('delayed_messages', 0)
                    }
                }
            }
            
            # Add market data manager metrics if available
            try:
                mdm_stats = self.market_data_manager.get_stats()
                report['market_data_metrics'] = mdm_stats
            except Exception as e:
                self.logger.warning(f"Error getting market data metrics: {str(e)}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {str(e)}")
            return {
                'timestamp': time.time(),
                'error': str(e),
                'status': 'report_generation_failed'
            }