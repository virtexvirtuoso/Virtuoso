"""
Dashboard Routes with Parallel Processing
Optimized for <1s response times
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
import asyncio
import aiohttp
import logging
import json
import time
from datetime import datetime, timezone
from functools import wraps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Import pooled cache adapter
try:
    from src.core.cache_adapter_pooled import cache_adapter
except ImportError:
    from src.api.cache_adapter_direct import DirectCacheAdapter
    cache_adapter = DirectCacheAdapter()

# Response cache decorator
response_cache = {}
cache_timestamps = {}

def cache_response(ttl_seconds=10):
    """Cache API responses"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}"
            now = time.time()
            
            # Check cache
            if cache_key in response_cache:
                cached_data, cache_time = response_cache[cache_key]
                if now - cache_time < ttl_seconds:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_data
            
            # Compute and cache
            result = await func(*args, **kwargs)
            response_cache[cache_key] = (result, now)
            
            # Cleanup old cache entries
            for key in list(response_cache.keys()):
                if key != cache_key:
                    _, timestamp = response_cache.get(key, (None, 0))
                    if now - timestamp > 60:  # Remove entries older than 60s
                        del response_cache[key]
                        
            return result
        return wrapper
    return decorator

@router.get("/mobile")
@cache_response(ttl_seconds=5)  # 5 second cache for mobile
async def get_mobile_dashboard_data() -> Dict[str, Any]:
    """Ultra-fast mobile dashboard endpoint with parallel processing"""
    
    start_time = time.time()
    
    try:
        # Define all data fetching tasks
        tasks = {
            'overview': cache_adapter.get("market:overview"),
            'breadth': cache_adapter.get("market:breadth"),
            'confluence': cache_adapter.get("confluence:scores"),
            'alerts': cache_adapter.get("alerts:active"),
            'symbols': cache_adapter.get("symbols:monitoring")
        }
        
        # Execute all tasks in parallel
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )
        
        # Map results back to keys
        data = {}
        for (key, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get {key}: {result}")
                data[key] = None
            else:
                data[key] = result
        
        # Build response
        response = {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time": round(time.time() - start_time, 3),
            "market_overview": data.get('overview', {}),
            "market_breadth": data.get('breadth', {}),
            "confluence_scores": data.get('confluence', [])[:10],  # Top 10
            "alerts": data.get('alerts', [])[:5],  # Latest 5
            "active_symbols": len(data.get('symbols', [])),
            "cache_stats": await cache_adapter.get_stats()
        }
        
        logger.info(f"Mobile dashboard served in {response['response_time']}s")
        return response
        
    except Exception as e:
        logger.error(f"Mobile dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
@cache_response(ttl_seconds=10)
async def get_dashboard_alerts() -> Dict[str, Any]:
    """Fast alerts endpoint"""
    
    start_time = time.time()
    
    try:
        # Parallel fetch different alert types
        alert_tasks = {
            'price': cache_adapter.get("alerts:price"),
            'volume': cache_adapter.get("alerts:volume"),
            'signal': cache_adapter.get("alerts:signal"),
            'system': cache_adapter.get("alerts:system")
        }
        
        results = await asyncio.gather(
            *alert_tasks.values(),
            return_exceptions=True
        )
        
        # Combine all alerts
        all_alerts = []
        for (alert_type, _), result in zip(alert_tasks.items(), results):
            if result and not isinstance(result, Exception):
                alerts = result if isinstance(result, list) else []
                for alert in alerts:
                    alert['type'] = alert_type
                    all_alerts.append(alert)
        
        # Sort by timestamp (most recent first)
        all_alerts.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return {
            "status": "success",
            "alerts": all_alerts[:20],  # Return top 20
            "count": len(all_alerts),
            "response_time": round(time.time() - start_time, 3)
        }
        
    except Exception as e:
        logger.error(f"Alerts endpoint error: {e}")
        return {
            "status": "error",
            "alerts": [],
            "count": 0,
            "error": str(e)
        }

@router.get("/data")
@cache_response(ttl_seconds=3)
async def get_dashboard_data() -> Dict[str, Any]:
    """Main dashboard data with parallel processing"""
    
    start_time = time.time()
    
    # Fetch all required data in parallel
    cache_keys = [
        "market:overview",
        "market:breadth",
        "confluence:scores",
        "signals:latest",
        "symbols:monitoring",
        "market:sentiment",
        "volume:analysis"
    ]
    
    # Use get_multiple for batch fetch
    cached_data = await cache_adapter.get_multiple(cache_keys)
    
    # Build response with defaults for missing data
    response = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market": {
            "overview": cached_data.get("market:overview", {}),
            "breadth": cached_data.get("market:breadth", {}),
            "sentiment": cached_data.get("market:sentiment", {})
        },
        "signals": cached_data.get("signals:latest", [])[:15],
        "confluence": cached_data.get("confluence:scores", [])[:20],
        "volume": cached_data.get("volume:analysis", {}),
        "symbols": {
            "monitoring": len(cached_data.get("symbols:monitoring", [])),
            "active": cached_data.get("symbols:monitoring", [])[:10]
        },
        "performance": {
            "response_time": round(time.time() - start_time, 3),
            "cache_stats": await cache_adapter.get_stats()
        }
    }
    
    logger.info(f"Dashboard data served in {response['performance']['response_time']}s")
    return response

@router.get("/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics"""
    
    cache_stats = await cache_adapter.get_stats()
    
    return {
        "cache": cache_stats,
        "response_cache": {
            "entries": len(response_cache),
            "keys": list(response_cache.keys())
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
