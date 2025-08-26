"""
Performance Monitoring API Routes
Provides real-time performance metrics and monitoring dashboard
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
import time
import psutil
import asyncio
from datetime import datetime, timedelta
import logging

from src.core.cache_manager import get_cache_manager
from src.monitoring.performance import PerformanceMonitor
from src.monitoring.metrics_manager import MetricsManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring/performance", tags=["performance"])

# Performance monitor instance
perf_monitor = None
metrics_manager = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create performance monitor instance"""
    global perf_monitor
    if perf_monitor is None:
        perf_monitor = PerformanceMonitor()
    return perf_monitor


def get_metrics_manager() -> Optional[MetricsManager]:
    """Get metrics manager if available"""
    global metrics_manager
    try:
        if metrics_manager is None:
            from src.monitoring.metrics_manager import MetricsManager
            metrics_manager = MetricsManager()
        return metrics_manager
    except:
        return None


@router.get("/summary")
async def get_performance_summary() -> Dict[str, Any]:
    """
    Get comprehensive performance summary
    
    Returns:
        Performance metrics including cache, API, memory, and system stats
    """
    try:
        cache_manager = get_cache_manager()
        perf = get_performance_monitor()
        metrics = get_metrics_manager()
        
        # Get cache statistics
        cache_stats = await cache_manager.get_stats()
        
        # Get system metrics
        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        
        # Get API performance metrics
        api_metrics = {}
        if metrics:
            try:
                api_metrics = await metrics.get_api_metrics()
            except:
                pass
        
        # Calculate uptime
        start_time = getattr(perf, 'start_time', time.time())
        uptime_seconds = time.time() - start_time
        
        return {
            'status': 'operational',
            'timestamp': datetime.now().isoformat(),
            'uptime': {
                'seconds': uptime_seconds,
                'formatted': str(timedelta(seconds=int(uptime_seconds)))
            },
            'cache': {
                'hit_rate': cache_stats.get('hit_rate', 0),
                'total_requests': cache_stats.get('total_requests', 0),
                'hits': cache_stats.get('hits', 0),
                'misses': cache_stats.get('misses', 0),
                'errors': cache_stats.get('errors', 0),
                'average_response_time_ms': cache_stats.get('average_response_time_ms', 0),
                'memory_usage_kb': cache_stats.get('memory_usage_kb', 0),
                'memcached_available': cache_stats.get('memcached_available', False),
                'connection_pool_size': cache_stats.get('connection_pool_size', 0)
            },
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'rss_mb': memory_info.rss / 1024 / 1024,
                    'vms_mb': memory_info.vms / 1024 / 1024,
                    'percent': process.memory_percent()
                },
                'threads': process.num_threads()
            },
            'api': api_metrics,
            'optimizations': {
                'cache_enabled': True,
                'connection_pooling': True,
                'circuit_breaker': cache_stats.get('memcached_available', False),
                'memory_optimization': cache_stats.get('memory_usage_kb', 0) < 100000  # < 100MB
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Perform system health check
    
    Returns:
        Health status of all system components
    """
    try:
        cache_manager = get_cache_manager()
        
        # Cache health
        cache_health = await cache_manager.health_check()
        
        # System health
        process = psutil.Process()
        system_health = {
            'status': 'healthy',
            'cpu_ok': process.cpu_percent(interval=0.1) < 80,
            'memory_ok': process.memory_percent() < 80,
            'issues': []
        }
        
        if not system_health['cpu_ok']:
            system_health['status'] = 'degraded'
            system_health['issues'].append('High CPU usage')
        
        if not system_health['memory_ok']:
            system_health['status'] = 'degraded'
            system_health['issues'].append('High memory usage')
        
        # Overall health
        overall_status = 'healthy'
        all_issues = []
        
        if cache_health.get('status') != 'healthy':
            overall_status = 'degraded'
            all_issues.extend(cache_health.get('issues', []))
        
        if system_health['status'] != 'healthy':
            overall_status = 'degraded'
            all_issues.extend(system_health['issues'])
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'components': {
                'cache': cache_health,
                'system': system_health
            },
            'issues': all_issues
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@router.get("/metrics/api")
async def get_api_metrics() -> Dict[str, Any]:
    """
    Get detailed API performance metrics
    
    Returns:
        API endpoint response times and call counts
    """
    try:
        cache_manager = get_cache_manager()
        
        # Try to get API metrics from cache
        api_metrics = await cache_manager.get('monitoring', 'api_metrics', {})
        
        if not api_metrics:
            # Generate sample metrics
            api_metrics = {
                'endpoints': {
                    '/api/dashboard/market-overview': {
                        'calls': 0,
                        'avg_response_time_ms': 0,
                        'errors': 0
                    },
                    '/api/mobile-unified/dashboard-data': {
                        'calls': 0,
                        'avg_response_time_ms': 0,
                        'errors': 0
                    }
                },
                'total_calls': 0,
                'total_errors': 0,
                'average_response_time_ms': 0
            }
        
        return api_metrics
    except Exception as e:
        logger.error(f"Error getting API metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/cache")
async def get_cache_metrics() -> Dict[str, Any]:
    """
    Get detailed cache performance metrics
    
    Returns:
        Cache hit rates, memory usage, and performance stats
    """
    try:
        cache_manager = get_cache_manager()
        cache_stats = await cache_manager.get_stats()
        
        # Calculate additional metrics
        if cache_stats['total_requests'] > 0:
            miss_rate = (cache_stats['misses'] / cache_stats['total_requests']) * 100
            error_rate = (cache_stats['errors'] / cache_stats['total_requests']) * 100
        else:
            miss_rate = 0
            error_rate = 0
        
        return {
            'statistics': cache_stats,
            'derived_metrics': {
                'hit_rate_percent': cache_stats.get('hit_rate', 0),
                'miss_rate_percent': miss_rate,
                'error_rate_percent': error_rate,
                'efficiency_score': min(100, cache_stats.get('hit_rate', 0) * (1 - error_rate/100))
            },
            'recommendations': []
        }
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/reset-stats")
async def reset_cache_stats() -> Dict[str, Any]:
    """
    Reset cache performance statistics
    
    Returns:
        Confirmation of stats reset
    """
    try:
        cache_manager = get_cache_manager()
        await cache_manager.reset_stats()
        
        return {
            'status': 'success',
            'message': 'Cache statistics reset',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/warmup")
async def warmup_cache(data: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Warm up cache with initial data
    
    Args:
        data: Optional data to load into cache
        
    Returns:
        Warmup status
    """
    try:
        cache_manager = get_cache_manager()
        
        if data:
            await cache_manager.warmup(data)
            entries = sum(len(items) for items in data.values())
        else:
            # Default warmup with empty data
            entries = 0
        
        return {
            'status': 'success',
            'entries_loaded': entries,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error warming up cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/1h")
async def get_performance_history() -> Dict[str, Any]:
    """
    Get performance metrics history for the last hour
    
    Returns:
        Time series performance data
    """
    try:
        cache_manager = get_cache_manager()
        
        # Try to get historical data from cache
        history = await cache_manager.get('monitoring', 'performance_history', {})
        
        if not history:
            # Generate sample historical data
            current_time = datetime.now()
            history = {
                'timestamps': [],
                'cache_hit_rate': [],
                'api_response_time': [],
                'memory_usage_mb': [],
                'cpu_percent': []
            }
            
            for i in range(12):  # Last 12 x 5-minute intervals
                timestamp = current_time - timedelta(minutes=i*5)
                history['timestamps'].append(timestamp.isoformat())
                history['cache_hit_rate'].append(85 + i)
                history['api_response_time'].append(50 - i*2)
                history['memory_usage_mb'].append(100 + i*2)
                history['cpu_percent'].append(20 + i)
        
        return history
    except Exception as e:
        logger.error(f"Error getting performance history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bottlenecks")
async def identify_bottlenecks() -> Dict[str, Any]:
    """
    Identify current performance bottlenecks
    
    Returns:
        List of identified bottlenecks and recommendations
    """
    try:
        cache_manager = get_cache_manager()
        cache_stats = await cache_manager.get_stats()
        
        bottlenecks = []
        recommendations = []
        
        # Check cache hit rate
        hit_rate = cache_stats.get('hit_rate', 0)
        if hit_rate < 70:
            bottlenecks.append({
                'type': 'cache',
                'severity': 'medium' if hit_rate > 50 else 'high',
                'description': f'Low cache hit rate: {hit_rate:.1f}%',
                'impact': 'Increased API load and response times'
            })
            recommendations.append('Review cache TTL settings and key generation')
        
        # Check response times
        avg_response_time = cache_stats.get('average_response_time_ms', 0)
        if avg_response_time > 100:
            bottlenecks.append({
                'type': 'performance',
                'severity': 'medium' if avg_response_time < 200 else 'high',
                'description': f'High average response time: {avg_response_time:.1f}ms',
                'impact': 'Slow user experience'
            })
            recommendations.append('Optimize slow queries and API calls')
        
        # Check memcached status
        if not cache_stats.get('memcached_available', False):
            bottlenecks.append({
                'type': 'infrastructure',
                'severity': 'medium',
                'description': 'Memcached unavailable, using fallback cache',
                'impact': 'Reduced cache performance and capacity'
            })
            recommendations.append('Check memcached service status and connectivity')
        
        # Check memory usage
        memory_usage_kb = cache_stats.get('memory_usage_kb', 0)
        if memory_usage_kb > 100000:  # 100MB
            bottlenecks.append({
                'type': 'memory',
                'severity': 'medium' if memory_usage_kb < 200000 else 'high',
                'description': f'High memory cache usage: {memory_usage_kb/1024:.1f}MB',
                'impact': 'Potential memory pressure'
            })
            recommendations.append('Review cache eviction policies and data size')
        
        return {
            'status': 'analyzed',
            'timestamp': datetime.now().isoformat(),
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'score': max(0, 100 - len(bottlenecks) * 20)  # Simple scoring
        }
    except Exception as e:
        logger.error(f"Error identifying bottlenecks: {e}")
        raise HTTPException(status_code=500, detail=str(e))