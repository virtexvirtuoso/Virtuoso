"""
Phase 2 Cache-Based Dashboard Routes
All data is read from cache - no direct service calls
Ultra-fast response times (< 10ms)
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import json
import logging
import time
import aiomcache

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache client (singleton)
_cache_client = None

async def get_cache_client():
    """Get or create cache client"""
    global _cache_client
    if _cache_client is None:
        _cache_client = aiomcache.Client('localhost', 11211)
    return _cache_client

async def get_from_cache(key: bytes, default: Any = None) -> Any:
    """
    Get data from cache with fallback default
    Always returns something - never fails
    """
    try:
        cache = await get_cache_client()
        data = await cache.get(key)
        if data:
            if key == b'analysis:market_regime':
                return data.decode()
            return json.loads(data.decode())
        return default
    except Exception as e:
        logger.error(f"Cache read error for {key}: {e}")
        return default

@router.get("/cache/overview")
async def get_cache_overview() -> Dict[str, Any]:
    """
    Get complete dashboard overview from cache
    Response time: < 10ms
    """
    start = time.perf_counter()
    
    # Fetch all data in parallel
    overview = await get_from_cache(b'market:overview', {})
    regime = await get_from_cache(b'analysis:market_regime', 'unknown')
    health = await get_from_cache(b'market:health', {})
    analysis = await get_from_cache(b'analysis:results', {})
    
    # Build response
    response = {
        'status': 'success',
        'source': 'cache',
        'response_time_ms': (time.perf_counter() - start) * 1000,
        'market': {
            'total_symbols': overview.get('total_symbols', 0),
            'total_volume_24h': overview.get('total_volume_24h', 0),
            'average_change_24h': overview.get('average_change_24h', 0),
            'data_source': overview.get('data_source', 'Unknown'),
            'regime': regime
        },
        'health': {
            'data_age_seconds': int(time.time() - health.get('last_update', time.time())),
            'fetch_time_ms': health.get('fetch_time_ms', 0),
            'status': health.get('status', 'unknown')
        }
    }
    
    # Add analysis if available
    if analysis and 'momentum' in analysis:
        response['momentum'] = {
            'gainers': analysis['momentum'].get('gainers', 0),
            'losers': analysis['momentum'].get('losers', 0),
            'score': analysis['momentum'].get('momentum_score', 0)
        }
    
    if analysis and 'volatility' in analysis:
        response['volatility'] = analysis['volatility']
    
    return response

@router.get("/cache/tickers")
async def get_cache_tickers(limit: int = 20) -> Dict[str, Any]:
    """
    Get market tickers from cache
    """
    start = time.perf_counter()
    
    tickers = await get_from_cache(b'market:tickers', {})
    
    # Limit the number of tickers returned
    if tickers and isinstance(tickers, dict):
        limited_tickers = dict(list(tickers.items())[:limit])
    else:
        limited_tickers = {}
    
    return {
        'status': 'success',
        'source': 'cache',
        'response_time_ms': (time.perf_counter() - start) * 1000,
        'count': len(limited_tickers),
        'data': limited_tickers
    }

@router.get("/cache/movers")
async def get_cache_movers() -> Dict[str, Any]:
    """
    Get top gainers and losers from cache
    """
    start = time.perf_counter()
    
    gainers = await get_from_cache(b'market:top_gainers', [])
    losers = await get_from_cache(b'market:top_losers', [])
    
    return {
        'status': 'success',
        'source': 'cache',
        'response_time_ms': (time.perf_counter() - start) * 1000,
        'top_gainers': gainers[:5] if gainers else [],
        'top_losers': losers[:5] if losers else []
    }

@router.get("/cache/analysis")
async def get_cache_analysis() -> Dict[str, Any]:
    """
    Get analysis results from cache
    """
    start = time.perf_counter()
    
    analysis = await get_from_cache(b'analysis:results', {})
    regime = await get_from_cache(b'analysis:market_regime', 'unknown')
    
    return {
        'status': 'success',
        'source': 'cache',
        'response_time_ms': (time.perf_counter() - start) * 1000,
        'market_regime': regime,
        'analysis': analysis
    }

@router.get("/cache/dashboard")
async def get_cache_dashboard() -> Dict[str, Any]:
    """
    Complete dashboard data from cache - everything needed for UI
    Ultra-fast: All data from memory
    """
    start = time.perf_counter()
    
    # Fetch everything in parallel
    dashboard = await get_from_cache(b'market:dashboard', {})
    overview = await get_from_cache(b'market:overview', {})
    gainers = await get_from_cache(b'market:top_gainers', [])
    losers = await get_from_cache(b'market:top_losers', [])
    analysis = await get_from_cache(b'analysis:results', {})
    regime = await get_from_cache(b'analysis:market_regime', 'unknown')
    health = await get_from_cache(b'market:health', {})
    
    return {
        'status': 'success',
        'source': 'cache',
        'response_time_ms': (time.perf_counter() - start) * 1000,
        'timestamp': int(time.time()),
        'overview': overview,
        'top_gainers': gainers[:10] if gainers else [],
        'top_losers': losers[:10] if losers else [],
        'market_regime': regime,
        'momentum': analysis.get('momentum', {}) if analysis else {},
        'volatility': analysis.get('volatility', {}) if analysis else {},
        'breadth': analysis.get('breadth', {}) if analysis else {},
        'health': {
            'data_fresh': int(time.time() - health.get('last_update', 0)) < 30 if health else False,
            'last_update': health.get('last_update', 0) if health else 0,
            'fetch_time_ms': health.get('fetch_time_ms', 0) if health else 0
        }
    }

@router.get("/cache/health")
async def get_cache_health() -> Dict[str, Any]:
    """
    Check cache and service health
    """
    start = time.perf_counter()
    
    # Check all health indicators
    market_status = await get_from_cache(b'service:market:status', {})
    analysis_status = await get_from_cache(b'service:analysis:status', {})
    market_health = await get_from_cache(b'market:health', {})
    analysis_health = await get_from_cache(b'analysis:health', {})
    
    # Test cache connectivity
    cache_ok = False
    try:
        cache = await get_cache_client()
        await cache.set(b'health:ping', b'pong', exptime=5)
        result = await cache.get(b'health:ping')
        cache_ok = (result == b'pong')
    except:
        pass
    
    return {
        'status': 'healthy' if cache_ok else 'degraded',
        'response_time_ms': (time.perf_counter() - start) * 1000,
        'cache': {
            'connected': cache_ok,
            'response_time_ms': (time.perf_counter() - start) * 1000
        },
        'services': {
            'market': {
                'status': market_status.get('status', 'unknown') if market_status else 'stopped',
                'last_update': market_status.get('last_update', None) if market_status else None,
                'error_count': market_status.get('error_count', 0) if market_status else 0
            },
            'analysis': {
                'status': analysis_status.get('status', 'unknown') if analysis_status else 'stopped',
                'last_analysis': analysis_status.get('last_analysis', None) if analysis_status else None,
                'error_count': analysis_status.get('error_count', 0) if analysis_status else 0
            }
        },
        'data': {
            'market_age_seconds': int(time.time() - market_health.get('last_update', 0)) if market_health else -1,
            'analysis_age_seconds': int(time.time() - analysis_health.get('last_analysis', 0)) if analysis_health else -1
        }
    }

@router.get("/cache/test")
async def test_cache_performance() -> Dict[str, Any]:
    """
    Test cache performance with multiple operations
    """
    results = []
    
    test_keys = [
        (b'market:tickers', 'Market Tickers'),
        (b'market:overview', 'Market Overview'),
        (b'analysis:results', 'Analysis Results'),
        (b'market:top_gainers', 'Top Gainers'),
        (b'market:top_losers', 'Top Losers')
    ]
    
    for key, name in test_keys:
        start = time.perf_counter()
        data = await get_from_cache(key)
        elapsed = (time.perf_counter() - start) * 1000
        
        results.append({
            'operation': name,
            'response_time_ms': elapsed,
            'has_data': data is not None
        })
    
    # Calculate average
    avg_time = sum(r['response_time_ms'] for r in results) / len(results)
    
    return {
        'status': 'success',
        'average_response_ms': avg_time,
        'tests': results,
        'summary': f"Cache responding in {avg_time:.2f}ms average"
    }