#!/usr/bin/env python3
"""
Alpha Performance Monitor - Production Rollout Dashboard
Real-time monitoring of alpha scanning system performance
"""

import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class AlertQualityMetrics:
    """Alert quality tracking metrics."""
    timestamp: datetime
    scanner_type: str
    total_alerts: int
    high_value_alerts: int  # >15% alpha
    critical_alerts: int    # >50% alpha
    average_alpha: float
    average_confidence: float
    average_value_score: float
    profitable_alerts: int  # Alerts that led to profit
    false_positives: int
    processing_time_ms: float
    memory_usage_mb: float

@dataclass
class SystemHealthMetrics:
    """System health monitoring."""
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_mb: float
    active_connections: int
    error_rate: float
    uptime_hours: float
    alerts_per_hour: float
    scanner_mode: str
    rollout_percentage: float

class AlphaPerformanceMonitor:
    """
    Monitors alpha scanning system performance during production rollout.
    
    Features:
    - Real-time performance tracking
    - Alert quality metrics
    - System health monitoring
    - Automatic rollback triggers
    - Performance comparison dashboard
    """
    
    def __init__(self, integration_manager, config: Dict[str, Any]):
        """Initialize the performance monitor."""
        self.integration_manager = integration_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.alert_quality_history = []
        self.system_health_history = []
        self.performance_alerts = []
        
        # Monitoring configuration
        monitor_config = config.get('alpha_performance_monitoring', {})
        self.monitoring_interval = monitor_config.get('interval_seconds', 60)
        self.history_retention_hours = monitor_config.get('history_retention_hours', 24)
        self.alert_thresholds = monitor_config.get('alert_thresholds', {
            'max_error_rate': 0.05,
            'min_average_alpha': 0.10,
            'max_processing_time_ms': 5000,
            'min_profitable_rate': 0.60
        })
        
        # Performance tracking
        self.start_time = time.time()
        self.last_monitoring_time = 0
        self.monitoring_active = False
        
        # Alert tracking for profitability analysis
        self.alert_outcomes = {}  # alert_id -> outcome
        
        self.logger.info("AlphaPerformanceMonitor initialized")
    
    async def start_monitoring(self):
        """Start continuous performance monitoring."""
        self.monitoring_active = True
        self.logger.info("Starting alpha performance monitoring")
        
        while self.monitoring_active:
            try:
                await self._collect_metrics()
                await self._check_health_thresholds()
                await self._cleanup_old_data()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {str(e)}")
                await asyncio.sleep(self.monitoring_interval)
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        self.logger.info("Stopping alpha performance monitoring")
    
    async def _collect_metrics(self):
        """Collect current performance metrics."""
        current_time = datetime.now(timezone.utc)
        
        # Get integration manager performance summary
        performance_summary = self.integration_manager.get_performance_summary()
        
        # Collect alert quality metrics
        await self._collect_alert_quality_metrics(current_time, performance_summary)
        
        # Collect system health metrics
        await self._collect_system_health_metrics(current_time, performance_summary)
        
        self.last_monitoring_time = time.time()
    
    async def _collect_alert_quality_metrics(self, timestamp: datetime, performance_summary: Dict):
        """Collect alert quality metrics."""
        try:
            # Legacy scanner metrics
            legacy_perf = performance_summary.get('legacy_performance', {})
            if legacy_perf:
                legacy_metrics = AlertQualityMetrics(
                    timestamp=timestamp,
                    scanner_type='legacy',
                    total_alerts=int(legacy_perf.get('avg_alerts_per_scan', 0) * 24),  # Daily estimate
                    high_value_alerts=int(legacy_perf.get('avg_high_value_alerts', 0) * 24),
                    critical_alerts=0,  # Legacy doesn't track critical tier
                    average_alpha=legacy_perf.get('avg_alpha', 0),
                    average_confidence=legacy_perf.get('avg_confidence', 0),
                    average_value_score=0,  # Legacy doesn't have value scores
                    profitable_alerts=self._estimate_profitable_alerts('legacy'),
                    false_positives=self._estimate_false_positives('legacy'),
                    processing_time_ms=legacy_perf.get('avg_processing_time_ms', 0),
                    memory_usage_mb=self._get_memory_usage()
                )
                self.alert_quality_history.append(legacy_metrics)
            
            # Optimized scanner metrics
            optimized_perf = performance_summary.get('optimized_performance', {})
            if optimized_perf:
                optimized_metrics = AlertQualityMetrics(
                    timestamp=timestamp,
                    scanner_type='optimized',
                    total_alerts=int(optimized_perf.get('avg_alerts_per_scan', 0) * 24),
                    high_value_alerts=int(optimized_perf.get('avg_high_value_alerts', 0) * 24),
                    critical_alerts=self._estimate_critical_alerts(),
                    average_alpha=optimized_perf.get('avg_alpha', 0),
                    average_confidence=optimized_perf.get('avg_confidence', 0),
                    average_value_score=self._estimate_average_value_score(),
                    profitable_alerts=self._estimate_profitable_alerts('optimized'),
                    false_positives=self._estimate_false_positives('optimized'),
                    processing_time_ms=optimized_perf.get('avg_processing_time_ms', 0),
                    memory_usage_mb=self._get_memory_usage()
                )
                self.alert_quality_history.append(optimized_metrics)
                
        except Exception as e:
            self.logger.error(f"Error collecting alert quality metrics: {str(e)}")
    
    async def _collect_system_health_metrics(self, timestamp: datetime, performance_summary: Dict):
        """Collect system health metrics."""
        try:
            uptime_hours = (time.time() - self.start_time) / 3600
            
            health_metrics = SystemHealthMetrics(
                timestamp=timestamp,
                cpu_usage_percent=self._get_cpu_usage(),
                memory_usage_mb=self._get_memory_usage(),
                active_connections=self._get_active_connections(),
                error_rate=self._calculate_error_rate(),
                uptime_hours=uptime_hours,
                alerts_per_hour=self._calculate_alerts_per_hour(),
                scanner_mode=performance_summary.get('mode', 'unknown'),
                rollout_percentage=performance_summary.get('rollout_percentage', 0)
            )
            
            self.system_health_history.append(health_metrics)
            
        except Exception as e:
            self.logger.error(f"Error collecting system health metrics: {str(e)}")
    
    async def _check_health_thresholds(self):
        """Check if any health thresholds are exceeded."""
        if not self.alert_quality_history or not self.system_health_history:
            return
        
        latest_quality = self.alert_quality_history[-1]
        latest_health = self.system_health_history[-1]
        
        alerts = []
        
        # Check error rate
        if latest_health.error_rate > self.alert_thresholds['max_error_rate']:
            alerts.append({
                'type': 'high_error_rate',
                'message': f"Error rate {latest_health.error_rate:.2%} exceeds threshold {self.alert_thresholds['max_error_rate']:.2%}",
                'severity': 'critical',
                'timestamp': latest_health.timestamp
            })
        
        # Check average alpha quality
        if latest_quality.average_alpha < self.alert_thresholds['min_average_alpha']:
            alerts.append({
                'type': 'low_alpha_quality',
                'message': f"Average alpha {latest_quality.average_alpha:.2%} below threshold {self.alert_thresholds['min_average_alpha']:.2%}",
                'severity': 'warning',
                'timestamp': latest_quality.timestamp
            })
        
        # Check processing time
        if latest_quality.processing_time_ms > self.alert_thresholds['max_processing_time_ms']:
            alerts.append({
                'type': 'slow_processing',
                'message': f"Processing time {latest_quality.processing_time_ms:.0f}ms exceeds threshold {self.alert_thresholds['max_processing_time_ms']:.0f}ms",
                'severity': 'warning',
                'timestamp': latest_quality.timestamp
            })
        
        # Check profitable rate
        profitable_rate = latest_quality.profitable_alerts / max(latest_quality.total_alerts, 1)
        if profitable_rate < self.alert_thresholds['min_profitable_rate']:
            alerts.append({
                'type': 'low_profitable_rate',
                'message': f"Profitable rate {profitable_rate:.2%} below threshold {self.alert_thresholds['min_profitable_rate']:.2%}",
                'severity': 'critical',
                'timestamp': latest_quality.timestamp
            })
        
        # Store and log alerts
        for alert in alerts:
            self.performance_alerts.append(alert)
            self.logger.warning(f"Performance Alert: {alert['message']}")
            
            # Trigger automatic rollback for critical alerts
            if alert['severity'] == 'critical':
                await self._trigger_automatic_rollback(alert)
    
    async def _trigger_automatic_rollback(self, alert: Dict):
        """Trigger automatic rollback to legacy scanner."""
        self.logger.critical(f"Triggering automatic rollback due to: {alert['message']}")
        
        try:
            self.integration_manager.force_rollback()
            
            # Log rollback event
            rollback_event = {
                'type': 'automatic_rollback',
                'trigger': alert,
                'timestamp': datetime.now(timezone.utc),
                'rollback_successful': True
            }
            
            self.performance_alerts.append(rollback_event)
            
        except Exception as e:
            self.logger.error(f"Failed to execute automatic rollback: {str(e)}")
            rollback_event = {
                'type': 'rollback_failed',
                'trigger': alert,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc),
                'rollback_successful': False
            }
            self.performance_alerts.append(rollback_event)
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.history_retention_hours)
        
        # Clean alert quality history
        self.alert_quality_history = [
            m for m in self.alert_quality_history 
            if m.timestamp > cutoff_time
        ]
        
        # Clean system health history
        self.system_health_history = [
            m for m in self.system_health_history 
            if m.timestamp > cutoff_time
        ]
        
        # Clean performance alerts (keep longer for analysis)
        alert_cutoff = datetime.now(timezone.utc) - timedelta(hours=self.history_retention_hours * 2)
        self.performance_alerts = [
            a for a in self.performance_alerts 
            if a['timestamp'] > alert_cutoff
        ]
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get current performance dashboard data."""
        current_time = datetime.now(timezone.utc)
        
        # Get recent metrics (last hour)
        recent_cutoff = current_time - timedelta(hours=1)
        recent_quality = [m for m in self.alert_quality_history if m.timestamp > recent_cutoff]
        recent_health = [m for m in self.system_health_history if m.timestamp > recent_cutoff]
        
        # Calculate summary statistics
        dashboard = {
            'timestamp': current_time,
            'monitoring_status': 'active' if self.monitoring_active else 'inactive',
            'uptime_hours': (time.time() - self.start_time) / 3600,
            
            # Current status
            'current_mode': self.integration_manager.mode.value if self.integration_manager.mode else 'unknown',
            'rollout_percentage': self.integration_manager.rollout_percentage,
            
            # Alert quality summary
            'alert_quality': self._summarize_alert_quality(recent_quality),
            
            # System health summary
            'system_health': self._summarize_system_health(recent_health),
            
            # Performance comparison
            'performance_comparison': self._generate_performance_comparison(),
            
            # Recent alerts
            'recent_alerts': self.performance_alerts[-10:],  # Last 10 alerts
            
            # Recommendations
            'recommendations': self._generate_recommendations()
        }
        
        return dashboard
    
    def _summarize_alert_quality(self, metrics: List[AlertQualityMetrics]) -> Dict[str, Any]:
        """Summarize alert quality metrics."""
        if not metrics:
            return {}
        
        legacy_metrics = [m for m in metrics if m.scanner_type == 'legacy']
        optimized_metrics = [m for m in metrics if m.scanner_type == 'optimized']
        
        summary = {}
        
        for scanner_type, scanner_metrics in [('legacy', legacy_metrics), ('optimized', optimized_metrics)]:
            if scanner_metrics:
                summary[scanner_type] = {
                    'total_alerts': sum(m.total_alerts for m in scanner_metrics),
                    'high_value_alerts': sum(m.high_value_alerts for m in scanner_metrics),
                    'average_alpha': sum(m.average_alpha for m in scanner_metrics) / len(scanner_metrics),
                    'average_confidence': sum(m.average_confidence for m in scanner_metrics) / len(scanner_metrics),
                    'profitable_rate': sum(m.profitable_alerts for m in scanner_metrics) / max(sum(m.total_alerts for m in scanner_metrics), 1),
                    'false_positive_rate': sum(m.false_positives for m in scanner_metrics) / max(sum(m.total_alerts for m in scanner_metrics), 1),
                    'avg_processing_time_ms': sum(m.processing_time_ms for m in scanner_metrics) / len(scanner_metrics)
                }
        
        return summary
    
    def _summarize_system_health(self, metrics: List[SystemHealthMetrics]) -> Dict[str, Any]:
        """Summarize system health metrics."""
        if not metrics:
            return {}
        
        return {
            'avg_cpu_usage': sum(m.cpu_usage_percent for m in metrics) / len(metrics),
            'avg_memory_usage_mb': sum(m.memory_usage_mb for m in metrics) / len(metrics),
            'avg_error_rate': sum(m.error_rate for m in metrics) / len(metrics),
            'avg_alerts_per_hour': sum(m.alerts_per_hour for m in metrics) / len(metrics),
            'current_rollout_percentage': metrics[-1].rollout_percentage if metrics else 0
        }
    
    def _generate_performance_comparison(self) -> Dict[str, Any]:
        """Generate performance comparison between scanners."""
        if not self.alert_quality_history:
            return {}
        
        # Get recent metrics for comparison
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_metrics = [m for m in self.alert_quality_history if m.timestamp > recent_cutoff]
        
        legacy_metrics = [m for m in recent_metrics if m.scanner_type == 'legacy']
        optimized_metrics = [m for m in recent_metrics if m.scanner_type == 'optimized']
        
        if not legacy_metrics or not optimized_metrics:
            return {}
        
        # Calculate improvement ratios
        legacy_avg_alpha = sum(m.average_alpha for m in legacy_metrics) / len(legacy_metrics)
        optimized_avg_alpha = sum(m.average_alpha for m in optimized_metrics) / len(optimized_metrics)
        
        legacy_processing_time = sum(m.processing_time_ms for m in legacy_metrics) / len(legacy_metrics)
        optimized_processing_time = sum(m.processing_time_ms for m in optimized_metrics) / len(optimized_metrics)
        
        return {
            'alpha_improvement_ratio': optimized_avg_alpha / max(legacy_avg_alpha, 0.01),
            'processing_time_ratio': optimized_processing_time / max(legacy_processing_time, 1),
            'alert_volume_reduction': 1 - (len(optimized_metrics) / max(len(legacy_metrics), 1)),
            'quality_score_improvement': self._calculate_quality_score_improvement(legacy_metrics, optimized_metrics)
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on current performance."""
        recommendations = []
        
        if not self.alert_quality_history or not self.system_health_history:
            return recommendations
        
        latest_quality = self.alert_quality_history[-1]
        latest_health = self.system_health_history[-1]
        
        # Check if rollout should be increased
        if (latest_health.error_rate < 0.02 and 
            latest_quality.average_alpha > 0.15 and
            latest_health.rollout_percentage < 100):
            recommendations.append("Consider increasing rollout percentage - performance metrics are strong")
        
        # Check if rollout should be paused
        if latest_health.error_rate > 0.03:
            recommendations.append("Consider pausing rollout - error rate is elevated")
        
        # Check processing performance
        if latest_quality.processing_time_ms > 2000:
            recommendations.append("Optimize processing performance - scan times are high")
        
        # Check alert quality
        profitable_rate = latest_quality.profitable_alerts / max(latest_quality.total_alerts, 1)
        if profitable_rate < 0.70:
            recommendations.append("Review alert quality - profitable rate is below target")
        
        return recommendations
    
    # Helper methods for metric calculation
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _get_active_connections(self) -> int:
        """Get number of active connections."""
        # This would be implemented based on your specific connection tracking
        return 0
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        # This would be implemented based on your error tracking
        return 0.0
    
    def _calculate_alerts_per_hour(self) -> float:
        """Calculate alerts per hour rate."""
        if not self.alert_quality_history:
            return 0.0
        
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_alerts = [m for m in self.alert_quality_history if m.timestamp > recent_cutoff]
        
        return sum(m.total_alerts for m in recent_alerts)
    
    def _estimate_profitable_alerts(self, scanner_type: str) -> int:
        """Estimate number of profitable alerts."""
        # This would be implemented based on actual trading outcome tracking
        return 0
    
    def _estimate_false_positives(self, scanner_type: str) -> int:
        """Estimate number of false positive alerts."""
        # This would be implemented based on actual trading outcome tracking
        return 0
    
    def _estimate_critical_alerts(self) -> int:
        """Estimate number of critical tier alerts."""
        # This would be calculated from actual optimized scanner data
        return 0
    
    def _estimate_average_value_score(self) -> float:
        """Estimate average value score for optimized alerts."""
        # This would be calculated from actual optimized scanner data
        return 0.0
    
    def _calculate_quality_score_improvement(self, legacy_metrics: List, optimized_metrics: List) -> float:
        """Calculate overall quality score improvement."""
        # This would implement a composite quality score calculation
        return 0.0
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics data for external analysis."""
        data = {
            'alert_quality_history': [asdict(m) for m in self.alert_quality_history],
            'system_health_history': [asdict(m) for m in self.system_health_history],
            'performance_alerts': self.performance_alerts,
            'dashboard': self.get_performance_dashboard()
        }
        
        if format == 'json':
            return json.dumps(data, default=str, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}") 