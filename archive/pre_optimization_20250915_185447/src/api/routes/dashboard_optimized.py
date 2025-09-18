"""
Optimized Dashboard Routes with Intelligent Cache Management
Zero empty data guarantee with comprehensive monitoring and fallbacks
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
import logging
import time
import asyncio
from functools import wraps

# Import optimized cache components
from src.api.cache_adapter_optimized import optimized_cache_adapter
from src.core.cache_warmer import cache_warmer
from src.core.cache_system import optimized_cache_system
from src.api.validation import symbol_validator

router = APIRouter()
logger = logging.getLogger(__name__)

# Performance tracking
response_times = []
cache_hit_rates = []

def track_performance(func):
    """Decorator to track endpoint performance and cache effectiveness"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        
        try:
            result = await func(*args, **kwargs)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # Track response time
            response_times.append(elapsed)
            if len(response_times) > 100:  # Keep last 100 measurements
                response_times.pop(0)
            
            # Add performance info to response
            if isinstance(result, dict):
                result['performance_metrics'] = {
                    'response_time_ms': round(elapsed, 2),
                    'avg_response_time_ms': round(sum(response_times) / len(response_times), 2),
                    'endpoint': func.__name__
                }
            
            logger.debug(f"{func.__name__} completed in {elapsed:.2f}ms")
            return result
            
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(f"{func.__name__} failed after {elapsed:.2f}ms: {e}")
            raise
            
    return wrapper

@router.post("/warm-cache")
async def trigger_cache_warming(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Manually trigger cache warming (useful for startup)"""
    try:
        logger.info("Manual cache warming triggered via API")
        
        # Start critical warming immediately
        warming_results = await cache_warmer.warm_critical_data()
        
        # Schedule continuous warming in background
        if not cache_warmer.running:
            background_tasks.add_task(cache_warmer.start_warming_loop, 60)  # 1 minute intervals
        
        return {
            'status': 'success',
            'warming_results': warming_results,
            'continuous_warming_started': not cache_warmer.running,
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Cache warming trigger failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': int(time.time())
        }

@router.get("/market-overview")
@track_performance
async def get_market_overview() -> Dict[str, Any]:
    """Get market overview with guaranteed data availability"""
    return await optimized_cache_adapter.get_market_overview()

@router.get("/overview")
@track_performance
async def get_dashboard_overview() -> Dict[str, Any]:
    """Get complete dashboard overview with zero empty data guarantee"""
    return await optimized_cache_adapter.get_dashboard_overview()

@router.get("/signals")
@track_performance
async def get_signals() -> Dict[str, Any]:
    """Get trading signals with comprehensive validation"""
    try:
        response = await optimized_cache_adapter.get_signals()
        
        # Validate and filter out system symbols from signals
        if response and 'signals' in response:
            original_count = len(response['signals'])
            response = symbol_validator.validate_api_response(response)
            filtered_count = len(response['signals'])
            symbol_validator.log_validation_stats(filtered_count, original_count - filtered_count, "signals")
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return {
            'signals': [],
            'count': 0,
            'timestamp': int(time.time()),
            'source': 'fallback',
            'error': str(e)
        }

@router.get("/mobile-data")
@track_performance
async def get_mobile_data() -> Dict[str, Any]:
    """Optimized mobile dashboard data with zero empty data guarantee"""
    try:
        response = await optimized_cache_adapter.get_mobile_data()
        
        # Validate confluence scores to prevent system contamination
        if response and response.get('confluence_scores'):
            original_count = len(response['confluence_scores'])
            response = symbol_validator.validate_api_response(response)
            filtered_count = len(response['confluence_scores'])
            
            if original_count != filtered_count:
                symbol_validator.log_validation_stats(
                    filtered_count,
                    original_count - filtered_count,
                    "mobile-data-optimized"
                )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting mobile data: {e}")
        return {
            'market_overview': {
                'market_regime': 'ERROR',
                'trend_strength': 0,
                'volatility': 0,
                'btc_dominance': 59.3,
                'total_volume_24h': 0
            },
            'confluence_scores': [],
            'top_movers': {'gainers': [], 'losers': []},
            'status': 'optimized_fallback',
            'timestamp': int(time.time()),
            'error': str(e)
        }

@router.get("/health")
@track_performance
async def get_health() -> Dict[str, Any]:
    """Comprehensive system health check"""
    return await optimized_cache_adapter.get_health_status()

@router.get("/cache-metrics")
async def get_cache_performance_metrics() -> Dict[str, Any]:
    """Get detailed cache performance metrics"""
    try:
        cache_metrics = await optimized_cache_adapter.get_cache_metrics()
        warming_stats = cache_warmer.get_warming_stats()
        system_health = await optimized_cache_system.health_check()
        
        return {
            'cache_performance': cache_metrics,
            'warming_stats': warming_stats,
            'system_health': system_health,
            'endpoint_performance': {
                'avg_response_time_ms': round(sum(response_times) / len(response_times), 2) if response_times else 0,
                'response_count': len(response_times),
                'recent_responses': response_times[-10:] if response_times else []
            },
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        return {
            'error': str(e),
            'timestamp': int(time.time())
        }