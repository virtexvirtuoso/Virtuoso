#!/usr/bin/env python3
"""
Phase 2 Cache Optimization: Enhanced Monitoring and Metrics Collection
Real-time cache performance monitoring with comprehensive analytics

Features:
- Real-time performance metrics
- Cache layer analysis (L1/L2/L3)
- Hotkey detection and optimization recommendations
- Performance trend analysis
- Alert system for performance degradation

Expected Impact: 30% resource optimization through intelligent monitoring
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class MetricType(Enum):
    HIT_RATE = "hit_rate"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    THROUGHPUT = "throughput"

@dataclass
class PerformanceAlert:
    """Performance alert with context"""
    timestamp: float
    level: AlertLevel
    metric_type: MetricType
    message: str
    current_value: float
    threshold_value: float
    suggested_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'level': self.level.value,
            'metric_type': self.metric_type.value,
            'message': self.message,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'suggested_action': self.suggested_action
        }

@dataclass
class TimeSeriesMetric:
    """Time series metric with rolling window"""
    name: str
    max_size: int = 1000
    values: deque = field(default_factory=deque)
    timestamps: deque = field(default_factory=deque)
    
    def add_value(self, value: float, timestamp: float = None):
        """Add a new value to the time series"""
        if timestamp is None:
            timestamp = time.time()
        
        self.values.append(value)
        self.timestamps.append(timestamp)
        
        # Maintain max size
        while len(self.values) > self.max_size:
            self.values.popleft()
            self.timestamps.popleft()
    
    def get_recent_values(self, seconds: int = 300) -> List[float]:
        """Get values from the last N seconds"""
        cutoff_time = time.time() - seconds
        recent_values = []
        
        for value, timestamp in zip(self.values, self.timestamps):
            if timestamp >= cutoff_time:
                recent_values.append(value)
        
        return recent_values
    
    def get_statistics(self, seconds: int = 300) -> Dict[str, float]:
        """Get statistical summary of recent values"""
        values = self.get_recent_values(seconds)
        
        if not values:
            return {'count': 0, 'avg': 0, 'min': 0, 'max': 0, 'p95': 0, 'p99': 0}
        
        return {
            'count': len(values),
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            'p99': statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        }

class CachePerformanceMonitor:
    """
    Comprehensive cache performance monitoring system
    
    Provides real-time metrics, alerting, and optimization recommendations
    for multi-tier cache architecture.
    """
    
    def __init__(self, cache_adapter=None, intelligent_warmer=None):
        self.cache_adapter = cache_adapter
        self.intelligent_warmer = intelligent_warmer
        
        # Time series metrics
        self.metrics = {
            'hit_rate': TimeSeriesMetric('hit_rate'),
            'l1_hit_rate': TimeSeriesMetric('l1_hit_rate'),
            'l2_hit_rate': TimeSeriesMetric('l2_hit_rate'),
            'l3_hit_rate': TimeSeriesMetric('l3_hit_rate'),
            'response_time': TimeSeriesMetric('response_time'),
            'error_rate': TimeSeriesMetric('error_rate'),
            'throughput': TimeSeriesMetric('throughput'),
            'memory_usage': TimeSeriesMetric('memory_usage'),
            'promotions_rate': TimeSeriesMetric('promotions_rate'),
            'evictions_rate': TimeSeriesMetric('evictions_rate')
        }
        
        # Key-level analytics
        self.key_analytics = defaultdict(lambda: {
            'access_count': 0,
            'hit_count': 0,
            'miss_count': 0,
            'total_response_time': 0.0,
            'last_access': 0.0,
            'first_access': time.time()
        })
        
        # Alerts and recommendations
        self.active_alerts: List[PerformanceAlert] = []
        self.alert_history: deque = deque(maxlen=100)
        
        # Performance thresholds
        self.thresholds = {
            'hit_rate_warning': 90.0,      # Warn if hit rate < 90%
            'hit_rate_critical': 80.0,     # Critical if hit rate < 80%
            'response_time_warning': 50.0, # Warn if avg response > 50ms
            'response_time_critical': 100.0, # Critical if avg response > 100ms
            'error_rate_warning': 1.0,     # Warn if error rate > 1%
            'error_rate_critical': 5.0,    # Critical if error rate > 5%
            'memory_usage_warning': 80.0,  # Warn if memory usage > 80%
            'memory_usage_critical': 95.0  # Critical if memory usage > 95%
        }
        
        # Monitoring state
        self.is_monitoring = False
        self.last_metrics_update = 0
        self.monitoring_interval = 30  # seconds
        
        # Performance baselines
        self.baselines = {
            'hit_rate': 95.0,
            'response_time': 10.0,  # Target < 10ms average
            'error_rate': 0.1,      # Target < 0.1% errors
        }
        
        logger.info("Cache performance monitor initialized")
    
    def record_cache_operation(self, key: str, hit: bool, response_time: float, error: bool = False):
        """Record a cache operation for monitoring"""
        current_time = time.time()
        
        # Update key-level analytics
        key_stats = self.key_analytics[key]
        key_stats['access_count'] += 1
        key_stats['total_response_time'] += response_time
        key_stats['last_access'] = current_time
        
        if hit:
            key_stats['hit_count'] += 1
        else:
            key_stats['miss_count'] += 1
        
        # Update time series metrics
        if self.cache_adapter:
            try:
                adapter_metrics = self.cache_adapter.get_performance_metrics()
                
                # Extract multi-tier metrics
                if 'multi_tier' in adapter_metrics:
                    tier_metrics = adapter_metrics['multi_tier']
                    
                    self.metrics['hit_rate'].add_value(tier_metrics['hit_rates']['overall'])
                    self.metrics['l1_hit_rate'].add_value(tier_metrics['hit_rates']['l1_percentage'])
                    self.metrics['l2_hit_rate'].add_value(tier_metrics['hit_rates']['l2_percentage'])
                    self.metrics['l3_hit_rate'].add_value(tier_metrics['hit_rates']['l3_percentage'])
                    
                    # Memory usage
                    l1_utilization = tier_metrics['l1_memory']['utilization']
                    self.metrics['memory_usage'].add_value(l1_utilization)
                    
                    # Promotions and evictions rates
                    operations = tier_metrics['operations']
                    self.metrics['promotions_rate'].add_value(operations.get('promotions', 0))
                    self.metrics['evictions_rate'].add_value(operations.get('evictions', 0))
                
                # Adapter-level metrics
                if 'cache_adapter' in adapter_metrics:
                    adapter_stats = adapter_metrics['cache_adapter']
                    
                    # Error rate
                    total_ops = adapter_stats['total_operations']
                    error_rate = (adapter_stats['errors'] / total_ops * 100) if total_ops > 0 else 0
                    self.metrics['error_rate'].add_value(error_rate)
                    
                    # Response time
                    avg_response = adapter_stats['avg_response_time_ms']
                    self.metrics['response_time'].add_value(avg_response)
                
            except Exception as e:
                logger.warning(f"Error collecting cache metrics: {e}")
        
        # Record individual operation
        self.metrics['response_time'].add_value(response_time * 1000)  # Convert to ms
        
        # Check for alerts
        self._check_performance_alerts()
    
    def _check_performance_alerts(self):
        """Check metrics against thresholds and generate alerts"""
        current_time = time.time()
        
        # Only check alerts every 30 seconds to avoid spam
        if current_time - self.last_metrics_update < 30:
            return
        
        self.last_metrics_update = current_time
        
        # Clear expired alerts (older than 1 hour)
        self.active_alerts = [
            alert for alert in self.active_alerts 
            if current_time - alert.timestamp < 3600
        ]
        
        # Check hit rate
        hit_rate_stats = self.metrics['hit_rate'].get_statistics(300)  # Last 5 minutes
        if hit_rate_stats['count'] > 0:
            current_hit_rate = hit_rate_stats['avg']
            
            if current_hit_rate < self.thresholds['hit_rate_critical']:
                alert = PerformanceAlert(
                    timestamp=current_time,
                    level=AlertLevel.CRITICAL,
                    metric_type=MetricType.HIT_RATE,
                    message=f"Cache hit rate critically low: {current_hit_rate:.1f}%",
                    current_value=current_hit_rate,
                    threshold_value=self.thresholds['hit_rate_critical'],
                    suggested_action="Check cache configuration, increase TTLs, or investigate cache key patterns"
                )
                self._add_alert(alert)
            
            elif current_hit_rate < self.thresholds['hit_rate_warning']:
                alert = PerformanceAlert(
                    timestamp=current_time,
                    level=AlertLevel.WARNING,
                    metric_type=MetricType.HIT_RATE,
                    message=f"Cache hit rate below optimal: {current_hit_rate:.1f}%",
                    current_value=current_hit_rate,
                    threshold_value=self.thresholds['hit_rate_warning'],
                    suggested_action="Consider enabling intelligent cache warming or adjusting TTL strategy"
                )
                self._add_alert(alert)
        
        # Check response time
        response_stats = self.metrics['response_time'].get_statistics(300)
        if response_stats['count'] > 0:
            current_response = response_stats['avg']
            
            if current_response > self.thresholds['response_time_critical']:
                alert = PerformanceAlert(
                    timestamp=current_time,
                    level=AlertLevel.CRITICAL,
                    metric_type=MetricType.RESPONSE_TIME,
                    message=f"Cache response time critically high: {current_response:.1f}ms",
                    current_value=current_response,
                    threshold_value=self.thresholds['response_time_critical'],
                    suggested_action="Check network connectivity, increase connection pools, or investigate slow queries"
                )
                self._add_alert(alert)
        
        # Check error rate
        error_stats = self.metrics['error_rate'].get_statistics(300)
        if error_stats['count'] > 0:
            current_error_rate = error_stats['avg']
            
            if current_error_rate > self.thresholds['error_rate_critical']:
                alert = PerformanceAlert(
                    timestamp=current_time,
                    level=AlertLevel.CRITICAL,
                    metric_type=MetricType.ERROR_RATE,
                    message=f"Cache error rate critically high: {current_error_rate:.1f}%",
                    current_value=current_error_rate,
                    threshold_value=self.thresholds['error_rate_critical'],
                    suggested_action="Check cache service health, network connectivity, and system resources"
                )
                self._add_alert(alert)
        
        # Check memory usage
        memory_stats = self.metrics['memory_usage'].get_statistics(300)
        if memory_stats['count'] > 0:
            current_memory = memory_stats['avg']
            
            if current_memory > self.thresholds['memory_usage_critical']:
                alert = PerformanceAlert(
                    timestamp=current_time,
                    level=AlertLevel.CRITICAL,
                    metric_type=MetricType.MEMORY_USAGE,
                    message=f"L1 cache memory usage critically high: {current_memory:.1f}%",
                    current_value=current_memory,
                    threshold_value=self.thresholds['memory_usage_critical'],
                    suggested_action="Increase L1 cache size limit or optimize cache key TTLs"
                )
                self._add_alert(alert)
    
    def _add_alert(self, alert: PerformanceAlert):
        """Add alert if not already active"""
        # Check if similar alert is already active
        similar_alert_exists = any(
            existing.metric_type == alert.metric_type and 
            existing.level == alert.level and
            alert.timestamp - existing.timestamp < 300  # Within 5 minutes
            for existing in self.active_alerts
        )
        
        if not similar_alert_exists:
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            logger.warning(f"Performance alert: {alert.message}")
    
    def get_hot_keys(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most frequently accessed cache keys"""
        sorted_keys = sorted(
            self.key_analytics.items(),
            key=lambda x: x[1]['access_count'],
            reverse=True
        )[:limit]
        
        hot_keys = []
        for key, stats in sorted_keys:
            avg_response_time = (
                stats['total_response_time'] / stats['access_count'] 
                if stats['access_count'] > 0 else 0
            )
            hit_rate = (
                stats['hit_count'] / stats['access_count'] * 100 
                if stats['access_count'] > 0 else 0
            )
            
            hot_keys.append({
                'key': key,
                'access_count': stats['access_count'],
                'hit_rate': round(hit_rate, 1),
                'avg_response_time_ms': round(avg_response_time * 1000, 2),
                'last_access': stats['last_access'],
                'age_hours': round((time.time() - stats['first_access']) / 3600, 1)
            })
        
        return hot_keys
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on current metrics"""
        recommendations = []
        
        # Analyze hit rates
        hit_rate_stats = self.metrics['hit_rate'].get_statistics(900)  # Last 15 minutes
        if hit_rate_stats['count'] > 0 and hit_rate_stats['avg'] < 95:
            recommendations.append({
                'priority': 'high',
                'category': 'hit_rate',
                'title': 'Improve Cache Hit Rate',
                'description': f"Current hit rate is {hit_rate_stats['avg']:.1f}%, target is 95%+",
                'suggestions': [
                    'Enable intelligent cache warming for predictive data loading',
                    'Optimize TTL strategy based on data volatility',
                    'Increase L1 cache size for frequently accessed data'
                ]
            })
        
        # Analyze response times
        response_stats = self.metrics['response_time'].get_statistics(900)
        if response_stats['count'] > 0 and response_stats['avg'] > 20:
            recommendations.append({
                'priority': 'medium',
                'category': 'response_time',
                'title': 'Optimize Response Times',
                'description': f"Average response time is {response_stats['avg']:.1f}ms, target is <20ms",
                'suggestions': [
                    'Increase connection pool size for cache clients',
                    'Optimize network connectivity to cache servers',
                    'Consider co-locating cache servers with application'
                ]
            })
        
        # Analyze hot keys
        hot_keys = self.get_hot_keys(5)
        if hot_keys:
            low_hit_keys = [k for k in hot_keys if k['hit_rate'] < 90]
            if low_hit_keys:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'hot_keys',
                    'title': 'Optimize Hot Key Performance',
                    'description': f"Found {len(low_hit_keys)} frequently accessed keys with low hit rates",
                    'suggestions': [
                        f'Increase TTL for keys: {", ".join([k["key"] for k in low_hit_keys[:3]])}',
                        'Consider pre-loading these keys during cache warming',
                        'Investigate why these keys are frequently missed'
                    ]
                })
        
        # Memory usage recommendations
        memory_stats = self.metrics['memory_usage'].get_statistics(300)
        if memory_stats['count'] > 0 and memory_stats['avg'] > 70:
            recommendations.append({
                'priority': 'low',
                'category': 'memory',
                'title': 'Memory Usage Optimization',
                'description': f"L1 cache memory usage is {memory_stats['avg']:.1f}%",
                'suggestions': [
                    'Increase L1 cache size limit if system memory allows',
                    'Implement more aggressive LRU eviction policies',
                    'Optimize data serialization to reduce memory footprint'
                ]
            })
        
        return recommendations
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_time = time.time()
        
        # Get recent statistics for all metrics
        metric_stats = {}
        for name, metric in self.metrics.items():
            metric_stats[name] = metric.get_statistics(900)  # Last 15 minutes
        
        # Get cache adapter metrics if available
        adapter_metrics = {}
        if self.cache_adapter:
            try:
                adapter_metrics = self.cache_adapter.get_performance_metrics()
            except Exception as e:
                logger.warning(f"Could not get adapter metrics: {e}")
        
        # Get intelligent warmer stats if available
        warmer_stats = {}
        if self.intelligent_warmer:
            try:
                warmer_stats = self.intelligent_warmer.get_warming_statistics()
            except Exception as e:
                logger.warning(f"Could not get warmer stats: {e}")
        
        return {
            'timestamp': current_time,
            'monitoring_duration_hours': round((current_time - (min(
                min(m.timestamps) if m.timestamps else current_time 
                for m in self.metrics.values()
            ))) / 3600, 1),
            'performance_summary': {
                'overall_health': self._calculate_overall_health(),
                'hit_rate_current': round(metric_stats['hit_rate']['avg'], 2),
                'response_time_avg_ms': round(metric_stats['response_time']['avg'], 2),
                'error_rate_current': round(metric_stats['error_rate']['avg'], 2),
                'l1_hit_percentage': round(metric_stats['l1_hit_rate']['avg'], 2),
                'memory_utilization': round(metric_stats['memory_usage']['avg'], 1)
            },
            'detailed_metrics': metric_stats,
            'cache_adapter': adapter_metrics,
            'intelligent_warmer': warmer_stats,
            'hot_keys': self.get_hot_keys(10),
            'active_alerts': [alert.to_dict() for alert in self.active_alerts],
            'optimization_recommendations': self.get_optimization_recommendations(),
            'thresholds': self.thresholds
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall cache system health"""
        health_score = 0
        total_weight = 0
        
        # Hit rate (40% weight)
        hit_rate_stats = self.metrics['hit_rate'].get_statistics(300)
        if hit_rate_stats['count'] > 0:
            hit_rate_score = min(hit_rate_stats['avg'] / 95 * 100, 100)
            health_score += hit_rate_score * 0.4
            total_weight += 0.4
        
        # Response time (30% weight) - invert so lower is better
        response_stats = self.metrics['response_time'].get_statistics(300)
        if response_stats['count'] > 0:
            response_score = max(0, 100 - (response_stats['avg'] / 50 * 100))
            health_score += response_score * 0.3
            total_weight += 0.3
        
        # Error rate (20% weight) - invert so lower is better
        error_stats = self.metrics['error_rate'].get_statistics(300)
        if error_stats['count'] > 0:
            error_score = max(0, 100 - (error_stats['avg'] / 5 * 100))
            health_score += error_score * 0.2
            total_weight += 0.2
        
        # Memory usage (10% weight) - invert so lower is better
        memory_stats = self.metrics['memory_usage'].get_statistics(300)
        if memory_stats['count'] > 0:
            memory_score = max(0, 100 - (memory_stats['avg'] / 90 * 100))
            health_score += memory_score * 0.1
            total_weight += 0.1
        
        if total_weight == 0:
            return 'unknown'
        
        final_score = health_score / total_weight
        
        if final_score >= 90:
            return 'excellent'
        elif final_score >= 75:
            return 'good'
        elif final_score >= 60:
            return 'fair'
        elif final_score >= 40:
            return 'poor'
        else:
            return 'critical'
    
    def reset_metrics(self):
        """Reset all monitoring metrics"""
        for metric in self.metrics.values():
            metric.values.clear()
            metric.timestamps.clear()
        
        self.key_analytics.clear()
        self.active_alerts.clear()
        self.alert_history.clear()
        
        logger.info("All monitoring metrics reset")

# Export for use in other modules
__all__ = ['CachePerformanceMonitor', 'PerformanceAlert', 'AlertLevel', 'MetricType']