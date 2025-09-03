"""
Optimized Monitoring Routes with Cache Performance Tracking
Provides comprehensive insights into cache system performance and dashboard data reliability
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
import time
import asyncio

# Import optimized cache components
from src.api.cache_adapter_optimized import optimized_cache_adapter
from src.core.cache_warmer import cache_warmer
from src.core.cache_system import optimized_cache_system

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/cache-status")
async def get_cache_system_status() -> Dict[str, Any]:
    """Get comprehensive cache system status"""
    try:
        health_check = await optimized_cache_system.health_check()
        cache_metrics = optimized_cache_system.get_cache_metrics()
        warming_stats = cache_warmer.get_warming_stats()
        
        # Calculate cache effectiveness scores
        global_metrics = cache_metrics.get('global_metrics', {})
        hit_rate = global_metrics.get('hit_rate', 0)
        avg_response_time = global_metrics.get('avg_response_time_ms', 0)
        
        # Performance scoring
        hit_rate_score = min(100, hit_rate)
        response_time_score = max(0, 100 - (avg_response_time / 2))  # 50ms = 75 points
        warming_success_rate = warming_stats.get('success_rate', 0)
        
        overall_score = (hit_rate_score * 0.4 + response_time_score * 0.3 + warming_success_rate * 0.3)
        
        return {
            'system_health': health_check,
            'cache_metrics': cache_metrics,
            'warming_stats': warming_stats,
            'performance_scores': {
                'overall_score': round(overall_score, 1),
                'hit_rate_score': round(hit_rate_score, 1),
                'response_time_score': round(response_time_score, 1),
                'warming_success_rate': round(warming_success_rate, 1)
            },
            'recommendations': _generate_performance_recommendations(
                hit_rate, avg_response_time, warming_success_rate, health_check
            ),
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return {
            'error': str(e),
            'timestamp': int(time.time())
        }

@router.get("/dashboard-data-quality")
async def get_dashboard_data_quality() -> Dict[str, Any]:
    """Analyze the quality and completeness of dashboard data"""
    try:
        # Test critical dashboard endpoints
        data_quality_checks = {}
        
        # Check market overview
        try:
            overview = await optimized_cache_adapter.get_market_overview()
            data_quality_checks['market_overview'] = _analyze_data_quality(overview, 'overview')
        except Exception as e:
            data_quality_checks['market_overview'] = {'status': 'error', 'error': str(e)}
        
        # Check signals
        try:
            signals = await optimized_cache_adapter.get_signals()
            data_quality_checks['signals'] = _analyze_data_quality(signals, 'signals')
        except Exception as e:
            data_quality_checks['signals'] = {'status': 'error', 'error': str(e)}
        
        # Check mobile data
        try:
            mobile_data = await optimized_cache_adapter.get_mobile_data()
            data_quality_checks['mobile_data'] = _analyze_data_quality(mobile_data, 'mobile')
        except Exception as e:
            data_quality_checks['mobile_data'] = {'status': 'error', 'error': str(e)}
        
        # Calculate overall data quality score
        quality_scores = [
            check.get('quality_score', 0) 
            for check in data_quality_checks.values() 
            if isinstance(check, dict) and 'quality_score' in check
        ]
        
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'overall_data_quality': round(overall_quality, 1),
            'endpoint_checks': data_quality_checks,
            'data_freshness_analysis': await _analyze_data_freshness(),
            'empty_data_incidents': _count_empty_data_incidents(data_quality_checks),
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Error analyzing dashboard data quality: {e}")
        return {
            'error': str(e),
            'timestamp': int(time.time())
        }

@router.get("/cache-key-analysis")
async def get_cache_key_analysis() -> Dict[str, Any]:
    """Analyze individual cache key performance and data patterns"""
    try:
        cache_metrics = optimized_cache_system.get_cache_metrics()
        key_metrics = cache_metrics.get('key_metrics', {})
        
        key_analysis = {}
        current_time = time.time()
        
        for key, metrics in key_metrics.items():
            total_ops = metrics.get('total_operations', 0)
            hit_rate = metrics.get('hit_rate', 0)
            avg_response = metrics.get('avg_response_time_ms', 0)
            data_age = metrics.get('data_age_seconds', 0)
            
            # Analyze key health
            health_score = 100
            issues = []
            
            if hit_rate < 80:
                health_score -= 20
                issues.append(f"Low hit rate: {hit_rate:.1f}%")
            
            if avg_response > 50:
                health_score -= 15
                issues.append(f"Slow response: {avg_response:.1f}ms")
            
            if data_age > 120:  # Data older than 2 minutes
                health_score -= 25
                issues.append(f"Stale data: {data_age:.0f}s old")
            
            if total_ops == 0:
                health_score = 0
                issues.append("No operations recorded")
            
            key_analysis[key] = {
                'health_score': max(0, health_score),
                'metrics': metrics,
                'issues': issues,
                'recommendations': _generate_key_recommendations(key, metrics, issues)
            }
        
        # Sort by health score (worst first)
        sorted_keys = sorted(key_analysis.items(), key=lambda x: x[1]['health_score'])
        
        return {
            'key_analysis': dict(sorted_keys),
            'summary': {
                'total_keys_analyzed': len(key_analysis),
                'healthy_keys': len([k for k in key_analysis.values() if k['health_score'] > 80]),
                'problematic_keys': len([k for k in key_analysis.values() if k['health_score'] < 60]),
                'average_health_score': round(
                    sum(k['health_score'] for k in key_analysis.values()) / len(key_analysis), 1
                ) if key_analysis else 0
            },
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Error analyzing cache keys: {e}")
        return {
            'error': str(e),
            'timestamp': int(time.time())
        }

@router.post("/trigger-warming")
async def trigger_emergency_cache_warming() -> Dict[str, Any]:
    """Emergency cache warming trigger for troubleshooting"""
    try:
        logger.warning("Emergency cache warming triggered via monitoring API")
        
        warming_results = await cache_warmer.warm_critical_data()
        
        # Also trigger a health check
        health_check = await optimized_cache_system.health_check()
        
        return {
            'status': 'completed',
            'warming_results': warming_results,
            'post_warming_health': health_check,
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Emergency cache warming failed: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': int(time.time())
        }

@router.get("/performance-trends")
async def get_performance_trends() -> Dict[str, Any]:
    """Get performance trends and historical analysis"""
    try:
        cache_metrics = optimized_cache_system.get_cache_metrics()
        warming_stats = cache_warmer.get_warming_stats()
        
        # Analyze trends (this would be more sophisticated with persistent storage)
        current_performance = {
            'hit_rate': cache_metrics.get('global_metrics', {}).get('hit_rate', 0),
            'avg_response_time': cache_metrics.get('global_metrics', {}).get('avg_response_time_ms', 0),
            'warming_success_rate': warming_stats.get('success_rate', 0),
            'total_operations': cache_metrics.get('global_metrics', {}).get('total_operations', 0)
        }
        
        # Performance trend analysis
        trend_analysis = {
            'current_performance': current_performance,
            'performance_status': _classify_performance_status(current_performance),
            'improvement_opportunities': _identify_improvement_opportunities(current_performance),
            'system_stability': _assess_system_stability(cache_metrics, warming_stats)
        }
        
        return {
            'trends': trend_analysis,
            'last_analyzed': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Error analyzing performance trends: {e}")
        return {
            'error': str(e),
            'timestamp': int(time.time())
        }

def _analyze_data_quality(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """Analyze the quality of data returned from cache"""
    if not isinstance(data, dict):
        return {'status': 'invalid', 'quality_score': 0, 'issue': 'Not a dictionary'}
    
    quality_score = 100
    issues = []
    
    if data_type == 'overview':
        # Check for essential overview fields
        required_fields = ['total_symbols', 'total_volume', 'market_regime']
        for field in required_fields:
            if field not in data or data[field] == 0:
                quality_score -= 20
                issues.append(f"Missing or zero {field}")
    
    elif data_type == 'signals':
        signals = data.get('signals', [])
        if not signals:
            quality_score -= 50
            issues.append("No signals available")
        else:
            # Check signal quality
            for signal in signals[:5]:
                if not signal.get('symbol') or signal.get('score', 0) <= 0:
                    quality_score -= 10
                    issues.append(f"Invalid signal: {signal.get('symbol', 'unknown')}")
    
    elif data_type == 'mobile':
        confluence_scores = data.get('confluence_scores', [])
        if not confluence_scores:
            quality_score -= 40
            issues.append("No confluence scores available")
        
        market_overview = data.get('market_overview', {})
        if not market_overview or market_overview.get('total_volume_24h', 0) == 0:
            quality_score -= 30
            issues.append("Market overview missing or empty")
    
    # Check data freshness
    timestamp = data.get('timestamp', 0)
    if timestamp > 0:
        age_seconds = time.time() - timestamp
        if age_seconds > 300:  # 5 minutes
            quality_score -= 20
            issues.append(f"Data is stale: {age_seconds:.0f}s old")
    else:
        quality_score -= 15
        issues.append("No timestamp available")
    
    return {
        'status': 'good' if quality_score > 80 else 'degraded' if quality_score > 40 else 'poor',
        'quality_score': max(0, quality_score),
        'issues': issues,
        'data_size': len(str(data)) if data else 0
    }

async def _analyze_data_freshness() -> Dict[str, Any]:
    """Analyze how fresh the cached data is"""
    try:
        cache_metrics = optimized_cache_system.get_cache_metrics()
        key_metrics = cache_metrics.get('key_metrics', {})
        
        freshness_analysis = {}
        current_time = time.time()
        
        for key, metrics in key_metrics.items():
            last_update = metrics.get('last_update', 0)
            if last_update > 0:
                age_seconds = current_time - last_update
                freshness_status = (
                    'fresh' if age_seconds < 60 else
                    'acceptable' if age_seconds < 180 else
                    'stale' if age_seconds < 600 else
                    'very_stale'
                )
                
                freshness_analysis[key] = {
                    'age_seconds': age_seconds,
                    'status': freshness_status,
                    'last_update': last_update
                }
        
        return {
            'key_freshness': freshness_analysis,
            'overall_freshness': _calculate_overall_freshness(freshness_analysis)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing data freshness: {e}")
        return {'error': str(e)}

def _count_empty_data_incidents(data_quality_checks: Dict[str, Any]) -> Dict[str, Any]:
    """Count incidents of empty or poor quality data"""
    incidents = {
        'empty_data_count': 0,
        'poor_quality_count': 0,
        'error_count': 0,
        'total_checks': len(data_quality_checks)
    }
    
    for check in data_quality_checks.values():
        if isinstance(check, dict):
            if check.get('status') == 'error':
                incidents['error_count'] += 1
            elif check.get('quality_score', 100) < 40:
                incidents['poor_quality_count'] += 1
            elif check.get('quality_score', 100) == 0:
                incidents['empty_data_count'] += 1
    
    incidents['incident_rate'] = (
        (incidents['empty_data_count'] + incidents['poor_quality_count'] + incidents['error_count']) /
        max(1, incidents['total_checks'])
    ) * 100
    
    return incidents

def _generate_performance_recommendations(hit_rate: float, avg_response_time: float, 
                                        warming_success_rate: float, health_check: Dict) -> List[str]:
    """Generate specific performance improvement recommendations"""
    recommendations = []
    
    if hit_rate < 90:
        recommendations.append(f"Cache hit rate is {hit_rate:.1f}% - consider increasing TTL or warming frequency")
    
    if avg_response_time > 50:
        recommendations.append(f"Average response time is {avg_response_time:.1f}ms - check network or memcached performance")
    
    if warming_success_rate < 80:
        recommendations.append(f"Cache warming success rate is {warming_success_rate:.1f}% - investigate data sources")
    
    if health_check.get('status') != 'healthy':
        recommendations.append("Cache system health is not optimal - check connectivity and configuration")
    
    critical_keys = health_check.get('checks', {}).get('critical_keys', {})
    missing_keys = [key for key, status in critical_keys.items() if not status.get('has_data', True)]
    if missing_keys:
        recommendations.append(f"Critical keys missing data: {', '.join(missing_keys)}")
    
    if not recommendations:
        recommendations.append("System performance is optimal - no immediate action required")
    
    return recommendations

def _generate_key_recommendations(key: str, metrics: Dict, issues: List[str]) -> List[str]:
    """Generate recommendations for specific cache keys"""
    recommendations = []
    
    hit_rate = metrics.get('hit_rate', 0)
    if hit_rate < 70:
        recommendations.append(f"Increase warming frequency for {key}")
    
    data_age = metrics.get('data_age_seconds', 0)
    if data_age > 180:
        recommendations.append(f"Investigate data source for {key} - data is too stale")
    
    avg_response = metrics.get('avg_response_time_ms', 0)
    if avg_response > 100:
        recommendations.append(f"Optimize cache size or network for {key}")
    
    if not recommendations:
        recommendations.append(f"Key {key} performance is acceptable")
    
    return recommendations

def _classify_performance_status(performance: Dict[str, Any]) -> str:
    """Classify overall system performance status"""
    hit_rate = performance.get('hit_rate', 0)
    response_time = performance.get('avg_response_time', 0)
    warming_rate = performance.get('warming_success_rate', 0)
    
    if hit_rate > 95 and response_time < 20 and warming_rate > 90:
        return 'excellent'
    elif hit_rate > 85 and response_time < 50 and warming_rate > 80:
        return 'good'
    elif hit_rate > 70 and response_time < 100 and warming_rate > 60:
        return 'acceptable'
    elif hit_rate > 50 and response_time < 200 and warming_rate > 40:
        return 'poor'
    else:
        return 'critical'

def _identify_improvement_opportunities(performance: Dict[str, Any]) -> List[str]:
    """Identify specific improvement opportunities"""
    opportunities = []
    
    hit_rate = performance.get('hit_rate', 0)
    if hit_rate < 95:
        opportunities.append("Improve cache hit rate through better warming strategies")
    
    response_time = performance.get('avg_response_time', 0)
    if response_time > 30:
        opportunities.append("Optimize cache response times through connection pooling")
    
    total_ops = performance.get('total_operations', 0)
    if total_ops < 100:
        opportunities.append("Increase cache utilization through more frequent dashboard updates")
    
    return opportunities

def _assess_system_stability(cache_metrics: Dict, warming_stats: Dict) -> Dict[str, Any]:
    """Assess overall system stability"""
    global_metrics = cache_metrics.get('global_metrics', {})
    circuit_breaker_open = global_metrics.get('circuit_breaker_open', False)
    
    stability_score = 100
    stability_issues = []
    
    if circuit_breaker_open:
        stability_score -= 50
        stability_issues.append("Circuit breaker is open")
    
    failures = global_metrics.get('circuit_breaker_failures', 0)
    if failures > 0:
        stability_score -= min(30, failures * 5)
        stability_issues.append(f"{failures} recent failures")
    
    warming_success = warming_stats.get('success_rate', 100)
    if warming_success < 90:
        stability_score -= (100 - warming_success) / 2
        stability_issues.append(f"Warming success rate: {warming_success:.1f}%")
    
    return {
        'stability_score': max(0, stability_score),
        'status': 'stable' if stability_score > 80 else 'unstable' if stability_score > 40 else 'critical',
        'issues': stability_issues
    }

def _calculate_overall_freshness(freshness_analysis: Dict) -> Dict[str, Any]:
    """Calculate overall data freshness metrics"""
    if not freshness_analysis:
        return {'status': 'unknown', 'score': 0}
    
    status_counts = {'fresh': 0, 'acceptable': 0, 'stale': 0, 'very_stale': 0}
    
    for analysis in freshness_analysis.values():
        status = analysis.get('status', 'unknown')
        if status in status_counts:
            status_counts[status] += 1
    
    total_keys = sum(status_counts.values())
    fresh_ratio = (status_counts['fresh'] + status_counts['acceptable']) / max(1, total_keys)
    
    return {
        'overall_status': 'fresh' if fresh_ratio > 0.8 else 'acceptable' if fresh_ratio > 0.6 else 'stale',
        'fresh_ratio': round(fresh_ratio * 100, 1),
        'status_distribution': status_counts
    }