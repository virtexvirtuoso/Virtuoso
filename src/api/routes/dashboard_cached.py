"""
Cache-optimized Dashboard Routes
All existing dashboard endpoints now read from cache
Ultra-fast response times with fallback to direct fetch if needed
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
import time

# Import cache adapter - ALWAYS use direct version
from src.api.cache_adapter_direct import cache_adapter
print("Using Direct Cache Adapter (zero abstraction)")

router = APIRouter()
logger = logging.getLogger(__name__)

# Track response times
from functools import wraps

def track_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        if isinstance(result, dict):
            result['response_time_ms'] = elapsed
        logger.debug(f"{func.__name__} responded in {elapsed:.2f}ms")
        return result
    return wrapper

@router.get("/market-overview")
@track_time
async def get_market_overview() -> Dict[str, Any]:
    """
    Get market overview from cache
    Replaces the original endpoint with cache-based data
    """
    return await cache_adapter.get_market_overview()

@router.get("/overview")
@track_time
async def get_dashboard_overview() -> Dict[str, Any]:
    """
    Get complete dashboard overview from cache
    """
    return await cache_adapter.get_dashboard_overview()

@router.get("/symbols")
@track_time
async def get_dashboard_symbols() -> Dict[str, Any]:
    """
    Get symbol data from cache
    """
    return await cache_adapter.get_dashboard_symbols()

@router.get("/signals")
@track_time
async def get_signals() -> Dict[str, Any]:
    """
    Get trading signals from cache analysis
    """
    return await cache_adapter.get_signals()

@router.get("/market-analysis")
@track_time
async def get_market_analysis() -> Dict[str, Any]:
    """
    Get market analysis from cache
    """
    return await cache_adapter.get_market_analysis()

@router.get("/market-movers")
@track_time
async def get_market_movers() -> Dict[str, Any]:
    """
    Get top gainers and losers from cache
    """
    return await cache_adapter.get_market_movers()

@router.get("/alerts")
@track_time
async def get_alerts() -> Dict[str, Any]:
    """
    Get alerts based on cache analysis
    """
    analysis = await cache_adapter.get_market_analysis()
    
    alerts = []
    
    # High volatility alert
    if analysis.get('volatility', {}).get('level') == 'high':
        alerts.append({
            'type': 'volatility',
            'severity': 'warning',
            'message': 'High market volatility detected',
            'timestamp': int(time.time())
        })
    
    # Momentum alerts
    momentum = analysis.get('momentum', {})
    if momentum.get('momentum_score', 0) > 0.7:
        alerts.append({
            'type': 'momentum',
            'severity': 'info',
            'message': f"Strong bullish momentum: {momentum.get('gainers', 0)} gainers",
            'timestamp': int(time.time())
        })
    elif momentum.get('momentum_score', 0) < -0.7:
        alerts.append({
            'type': 'momentum',
            'severity': 'warning',
            'message': f"Strong bearish momentum: {momentum.get('losers', 0)} losers",
            'timestamp': int(time.time())
        })
    
    return {
        'alerts': alerts,
        'count': len(alerts),
        'source': 'cache'
    }

@router.get("/health")
@track_time
async def get_health() -> Dict[str, Any]:
    """
    Get system health from cache
    """
    return await cache_adapter.get_health_status()

# Backward compatibility aliases
@router.get("/market-analysis-summary")
@track_time
async def get_market_analysis_summary() -> Dict[str, Any]:
    """Alias for market analysis"""
    return await get_market_analysis()

@router.get("/confluence-scores")
@track_time
async def get_confluence_scores() -> Dict[str, Any]:
    """
    Get confluence scores (generated from cache analysis)
    """
    symbols = await cache_adapter.get_dashboard_symbols()
    analysis = await cache_adapter.get_market_analysis()
    
    # Generate confluence scores from analysis
    scores = []
    for symbol in symbols.get('symbols', [])[:20]:
        # Simple scoring based on change and volume
        change_score = min(abs(symbol.get('change_24h', 0)) / 10, 1) * 100
        volume_score = 50  # Default volume score
        
        scores.append({
            'symbol': symbol['symbol'],
            'score': (change_score + volume_score) / 2,
            'change_24h': symbol.get('change_24h', 0),
            'volume': symbol.get('volume', 0)
        })
    
    # Sort by score
    scores.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'scores': scores,
        'count': len(scores),
        'market_regime': analysis.get('market_regime', 'unknown'),
        'source': 'cache'
    }

# Mobile-specific endpoints
@router.get("/mobile/overview")
@track_time
async def get_mobile_overview() -> Dict[str, Any]:
    """
    Lightweight overview for mobile dashboards
    """
    overview = await cache_adapter.get_dashboard_overview()
    movers = await cache_adapter.get_market_movers()
    
    # Simplify for mobile
    return {
        'summary': overview.get('summary', {}),
        'market_regime': overview.get('market_regime', 'unknown'),
        'top_gainers': movers.get('gainers', [])[:3],
        'top_losers': movers.get('losers', [])[:3],
        'source': 'cache',
        'timestamp': int(time.time())
    }

@router.get("/mobile/signals")
@track_time
async def get_mobile_signals() -> Dict[str, Any]:
    """
    Simplified signals for mobile
    """
    signals = await cache_adapter.get_signals()
    
    # Limit to top 5 for mobile
    return {
        'signals': signals.get('signals', [])[:5],
        'count': min(len(signals.get('signals', [])), 5),
        'source': 'cache'
    }

@router.get("/mobile-data")
@track_time
async def get_mobile_data() -> Dict[str, Any]:
    """
    Complete mobile dashboard data from cache
    Includes market overview, confluence scores, and top movers
    
    This now delegates to cache_adapter.get_mobile_data() which includes
    high_24h, low_24h, range_24h, and reliability for each symbol
    """
    # Use the cache adapter's get_mobile_data method which has all the fields
    return await cache_adapter.get_mobile_data()

@router.get("/debug-cache")
async def debug_cache() -> Dict[str, Any]:
    """Debug endpoint to check cache directly"""
    import aiomcache
    import json
    
    client = aiomcache.Client('localhost', 11211)
    
    # Check signals directly
    signals_data = await client.get(b'analysis:signals')
    signal_count = 0
    first_signal = None
    if signals_data:
        signals = json.loads(signals_data.decode())
        signal_count = len(signals.get('signals', []))
        if signals.get('signals'):
            first_signal = signals['signals'][0]['symbol']
    
    await client.close()
    
    # Also check via adapter
    adapter_signals = await cache_adapter.get_signals()
    
    return {
        'direct_cache_signals': signal_count,
        'direct_first_signal': first_signal,
        'adapter_signals': len(adapter_signals.get('signals', [])),
        'adapter_type': type(cache_adapter).__name__,
        'adapter_module': cache_adapter.__module__ if hasattr(cache_adapter, '__module__') else 'unknown'
    }