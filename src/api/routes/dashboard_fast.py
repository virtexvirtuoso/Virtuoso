"""
Ultra-Fast Dashboard Routes - Phase 3
Direct cache access, no abstractions, <50ms response times
"""
from fastapi import APIRouter
from typing import Dict, Any
import time
import logging

from src.core.direct_cache import DirectCache

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/overview")
async def overview() -> Dict[str, Any]:
    """Dashboard overview - direct from cache"""
    start = time.perf_counter()
    data = await DirectCache.get_dashboard_data()
    data['response_ms'] = (time.perf_counter() - start) * 1000
    return data

@router.get("/market")
async def market() -> Dict[str, Any]:
    """Market overview - direct from cache"""
    start = time.perf_counter()
    data = await DirectCache.get_market_overview()
    data['response_ms'] = (time.perf_counter() - start) * 1000
    return data

@router.get("/signals")
async def signals() -> Dict[str, Any]:
    """Trading signals - direct from cache"""
    start = time.perf_counter()
    data = await DirectCache.get_signals()
    data['response_ms'] = (time.perf_counter() - start) * 1000
    return data

@router.get("/movers")
async def movers() -> Dict[str, Any]:
    """Market movers - direct from cache"""
    start = time.perf_counter()
    data = await DirectCache.get_movers()
    data['response_ms'] = (time.perf_counter() - start) * 1000
    return data

@router.get("/mobile")
async def mobile() -> Dict[str, Any]:
    """Mobile dashboard data - optimized for speed"""
    start = time.perf_counter()
    
    # Get essential data only
    overview = await DirectCache.get('market:overview', {})
    signals = await DirectCache.get('analysis:signals', {})
    movers = await DirectCache.get('market:movers', {})
    
    # Build mobile response
    signal_list = signals.get('signals', [])[:10]  # Top 10 only
    
    response = {
        'market_overview': {
            'market_regime': await DirectCache.get('analysis:market_regime', 'unknown'),
            'total_volume_24h': overview.get('total_volume_24h', 0),
            'volatility': overview.get('volatility', 0)
        },
        'confluence_scores': [
            {
                'symbol': s.get('symbol', ''),
                'score': s.get('score', 50),
                'change_24h': s.get('change_24h', 0)
            } for s in signal_list
        ],
        'top_movers': {
            'gainers': movers.get('gainers', [])[:5],
            'losers': movers.get('losers', [])[:5]
        },
        'response_ms': (time.perf_counter() - start) * 1000
    }
    
    return response

@router.get("/mobile-data")
async def mobile_data() -> Dict[str, Any]:
    """Mobile data endpoint - alias for mobile"""
    return await mobile()

@router.get("/health")
async def health() -> Dict[str, Any]:
    """Cache health check"""
    start = time.perf_counter()
    
    # Test cache connection
    test_value = await DirectCache.get('test:ping', None)
    
    return {
        'status': 'healthy' if test_value is not None else 'degraded',
        'cache_connected': test_value is not None,
        'response_ms': (time.perf_counter() - start) * 1000
    }