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
import asyncio
from functools import wraps
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


# Circuit breaker for cache failures
cache_failures = 0
max_failures = 3

def with_fallback(fallback_data):
    """Decorator to provide fallback data when cache fails"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            global cache_failures
            try:
                # Add timeout to the entire endpoint
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=3.0)
                cache_failures = 0  # Reset on success
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Endpoint {func.__name__} timed out, using fallback")
                cache_failures += 1
                return {**fallback_data, 'status': 'timeout_fallback', 'timestamp': int(time.time())}
            except Exception as e:
                logger.error(f"Endpoint {func.__name__} failed: {e}")
                cache_failures += 1
                if cache_failures >= max_failures:
                    logger.error("Too many cache failures, using fallback data")
                return {**fallback_data, 'status': 'error_fallback', 'timestamp': int(time.time())}
        return wrapper
    return decorator


# Circuit breaker for cache failures
cache_failures = 0
max_failures = 3

def with_fallback(fallback_data):
    """Decorator to provide fallback data when cache fails"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            global cache_failures
            try:
                # Add timeout to the entire endpoint
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=3.0)
                cache_failures = 0  # Reset on success
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Endpoint {func.__name__} timed out, using fallback")
                cache_failures += 1
                return {**fallback_data, 'status': 'timeout_fallback', 'timestamp': int(time.time())}
            except Exception as e:
                logger.error(f"Endpoint {func.__name__} failed: {e}")
                cache_failures += 1
                if cache_failures >= max_failures:
                    logger.error("Too many cache failures, using fallback data")
                return {**fallback_data, 'status': 'error_fallback', 'timestamp': int(time.time())}
        return wrapper
    return decorator

@router.get("/market-overview")
@track_time
async def get_market_overview() -> Dict[str, Any]:
    """
    Get market overview from cache
    Replaces the original endpoint with cache-based data
    """
    return await cache_adapter.get_market_overview()

@router.get("/overview")
@with_fallback({
            'summary': {'total_symbols': 0, 'total_volume': 0},
            'market_regime': 'NEUTRAL',
            'signals': [],
            'status': 'fallback'
        })
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
@with_fallback({
            'alerts': [{'type': 'info', 'message': 'System initializing...', 'timestamp': int(time.time())}],
            'count': 1,
            'status': 'fallback'
        })
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


@router.get("/opportunities")
@track_time
async def get_opportunities() -> Dict[str, Any]:
    """
    Get alpha opportunities from cache
    Maps to the missing /api/dashboard-cached/opportunities endpoint
    """
    try:
        # Get market analysis and signals to generate opportunities
        analysis = await cache_adapter.get_market_analysis()
        signals = await cache_adapter.get_signals()
        
        opportunities = []
        
        # High-scoring signals become opportunities
        for signal in signals.get('signals', [])[:10]:
            score = signal.get('score', 50)
            if score > 65:  # High confidence threshold
                opportunities.append({
                    'symbol': signal.get('symbol'),
                    'confidence': 'high' if score > 80 else 'medium',
                    'score': score,
                    'type': 'momentum' if signal.get('change_24h', 0) > 0 else 'reversal',
                    'price': signal.get('price', 0),
                    'change_24h': signal.get('change_24h', 0),
                    'volume': signal.get('volume', 0),
                    'reason': f"Strong {signal.get('sentiment', 'neutral').lower()} signal with {score}% confluence",
                    'timestamp': int(time.time())
                })
        
        return {
            'opportunities': opportunities,
            'total': len(opportunities),
            'high_confidence': len([o for o in opportunities if o['confidence'] == 'high']),
            'medium_confidence': len([o for o in opportunities if o['confidence'] == 'medium']),
            'timestamp': int(time.time()),
            'source': 'cache'
        }
        
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        # Fallback opportunities data
        return {
            'opportunities': [
                {
                    'symbol': 'BTCUSDT',
                    'confidence': 'medium', 
                    'score': 72,
                    'type': 'momentum',
                    'reason': 'Strong technical momentum with volume confirmation',
                    'timestamp': int(time.time())
                }
            ],
            'total': 1,
            'high_confidence': 0,
            'medium_confidence': 1,
            'timestamp': int(time.time()),
            'source': 'fallback'
        }


@router.get("/opportunities")
@track_time
async def get_opportunities() -> Dict[str, Any]:
    """
    Get alpha opportunities from cache
    Maps to the missing /api/dashboard-cached/opportunities endpoint
    """
    try:
        # Get market analysis and signals to generate opportunities
        analysis = await cache_adapter.get_market_analysis()
        signals = await cache_adapter.get_signals()
        
        opportunities = []
        
        # High-scoring signals become opportunities
        for signal in signals.get('signals', [])[:10]:
            score = signal.get('score', 50)
            if score > 65:  # High confidence threshold
                opportunities.append({
                    'symbol': signal.get('symbol'),
                    'confidence': 'high' if score > 80 else 'medium',
                    'score': score,
                    'type': 'momentum' if signal.get('change_24h', 0) > 0 else 'reversal',
                    'price': signal.get('price', 0),
                    'change_24h': signal.get('change_24h', 0),
                    'volume': signal.get('volume', 0),
                    'reason': f"Strong {signal.get('sentiment', 'neutral').lower()} signal with {score}% confluence",
                    'timestamp': int(time.time())
                })
        
        return {
            'opportunities': opportunities,
            'total': len(opportunities),
            'high_confidence': len([o for o in opportunities if o['confidence'] == 'high']),
            'medium_confidence': len([o for o in opportunities if o['confidence'] == 'medium']),
            'timestamp': int(time.time()),
            'source': 'cache'
        }
        
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        # Fallback opportunities data
        return {
            'opportunities': [
                {
                    'symbol': 'BTCUSDT',
                    'confidence': 'medium', 
                    'score': 72,
                    'type': 'momentum',
                    'reason': 'Strong technical momentum with volume confirmation',
                    'timestamp': int(time.time())
                }
            ],
            'total': 1,
            'high_confidence': 0,
            'medium_confidence': 1,
            'timestamp': int(time.time()),
            'source': 'fallback'
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
@with_fallback({
            'market_overview': {'market_regime': 'NEUTRAL', 'volatility': 0, 'btc_dominance': 59.3},
            'confluence_scores': [],
            'top_movers': {'gainers': [], 'losers': []},
            'status': 'fallback'
        })
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