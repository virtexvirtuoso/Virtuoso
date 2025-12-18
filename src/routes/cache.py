"""
Cache management and monitoring API routes
Phase 1 Implementation - Cache metrics and management

Non Nobis Domine - Not to us, O Lord
But to your name give glory
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
from src.core.cache.unified_cache import get_cache

router = APIRouter(prefix="/cache", tags=["cache"])
logger = logging.getLogger(__name__)

@router.get("/metrics")
async def get_cache_metrics() -> Dict[str, Any]:
    """
    Get cache performance metrics
    
    Returns detailed statistics about cache usage:
    - Hit rate percentage
    - Average response times
    - Total requests served
    - Performance gain vs direct computation
    """
    try:
        cache = get_cache()
        metrics = cache.get_metrics()
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "cache_config": {
                "host": cache.host,
                "port": cache.port,
                "memcached_available": cache.memcached_available,
                "local_fallback_enabled": cache.enable_local_fallback
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving cache metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def cache_health_check() -> Dict[str, Any]:
    """
    Check cache system health
    
    Tests connectivity to Memcached and returns status
    """
    try:
        cache = get_cache()
        
        # Test Memcached connectivity
        test_key = "health:check"
        test_value = {"timestamp": datetime.now(timezone.utc).isoformat()}
        
        # Try to set and get
        await cache.set(test_key, test_value, ttl=5)
        retrieved = await cache.get(test_key)
        
        memcached_healthy = retrieved is not None
        
        return {
            "status": "healthy" if memcached_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memcached": {
                "connected": cache.memcached_available,
                "healthy": memcached_healthy,
                "host": f"{cache.host}:{cache.port}"
            },
            "local_cache": {
                "enabled": cache.enable_local_fallback,
                "entries": len(cache.local_cache) if cache.enable_local_fallback else 0
            }
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }

@router.post("/clear")
async def clear_cache(pattern: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear cache entries
    
    Args:
        pattern: Optional pattern to match keys (local cache only)
                If not provided, clears all local cache
    
    Note: Memcached doesn't support pattern-based deletion,
          so this only affects the local fallback cache
    """
    try:
        cache = get_cache()
        
        if pattern:
            await cache.clear_pattern(pattern)
            message = f"Cleared local cache entries matching pattern: {pattern}"
        else:
            # Clear all local cache
            if cache.enable_local_fallback:
                cleared_count = len(cache.local_cache)
                cache.local_cache.clear()
                message = f"Cleared {cleared_count} entries from local cache"
            else:
                message = "Local cache not enabled"
        
        return {
            "status": "success",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_cache_statistics() -> Dict[str, Any]:
    """
    Get detailed cache statistics and performance analysis
    """
    try:
        cache = get_cache()
        metrics = cache.get_metrics()
        
        # Calculate additional statistics
        if metrics['hit_rate_percent'] > 0:
            estimated_time_saved_ms = (
                metrics['hits'] * metrics['avg_miss_compute_ms'] - 
                metrics['hits'] * metrics['avg_hit_response_ms']
            )
        else:
            estimated_time_saved_ms = 0
        
        # Calculate cost savings (example: $0.001 per API call saved)
        api_calls_saved = metrics['hits']
        estimated_cost_saved = api_calls_saved * 0.001
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_requests": metrics['total_requests'],
                "hit_rate": f"{metrics['hit_rate_percent']}%",
                "performance_gain": metrics.get('performance_gain', 'N/A'),
                "uptime_hours": round(metrics['uptime_seconds'] / 3600, 2)
            },
            "performance": {
                "avg_cache_response_ms": metrics['avg_hit_response_ms'],
                "avg_compute_time_ms": metrics['avg_miss_compute_ms'],
                "total_time_saved_seconds": round(estimated_time_saved_ms / 1000, 2),
                "speedup_factor": metrics.get('performance_gain', 'N/A')
            },
            "efficiency": {
                "cache_hits": metrics['hits'],
                "cache_misses": metrics['misses'],
                "cache_errors": metrics['errors'],
                "successful_saves": metrics['cache_saves'],
                "failed_saves": metrics['cache_failures']
            },
            "cost_analysis": {
                "api_calls_saved": api_calls_saved,
                "estimated_cost_saved_usd": round(estimated_cost_saved, 2),
                "efficiency_score": min(100, metrics['hit_rate_percent'] * 1.2)  # Bonus for high hit rates
            }
        }
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/warmup")
async def warmup_cache() -> Dict[str, Any]:
    """
    Warmup cache with commonly accessed data
    
    Pre-loads frequently requested symbols and data
    """
    try:
        cache = get_cache()
        
        # Define warmup function
        async def warmup_func(cache_instance):
            # Common symbols to pre-cache
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]
            exchanges = ["bybit"]
            
            warmup_count = 0
            
            for exchange in exchanges:
                for symbol in symbols:
                    # Pre-cache ticker keys (without actual data for now)
                    key = f"ticker:{exchange}:{symbol}"
                    await cache_instance.set(
                        key, 
                        {"warmed_up": True, "symbol": symbol, "exchange": exchange},
                        ttl=5
                    )
                    warmup_count += 1
            
            return warmup_count
        
        # Run warmup
        count = await warmup_func(cache)
        
        return {
            "status": "success",
            "message": f"Cache warmup completed with {count} entries",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Soli Deo Gloria - Glory to God Alone