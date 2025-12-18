"""
Direct cache access routes - bypasses all adapters
"""
from fastapi import APIRouter
import aiomcache
import json
import time
from typing import Dict, Any

router = APIRouter()

@router.get("/signals")
async def get_signals_direct() -> Dict[str, Any]:
    """Get signals directly from cache"""
    try:
        client = aiomcache.Client('localhost', 11211)
        
        # Debug: Check if we can connect
        signals_data = await client.get(b'analysis:signals')
        
        signals = []
        raw_data = None
        if signals_data:
            raw_data = signals_data.decode()[:100]  # First 100 chars for debug
            data = json.loads(signals_data.decode())
            signals = data.get('signals', [])
        
        await client.close()
        
        return {
            'signals': signals,
            'count': len(signals),
            'debug': {
                'has_data': signals_data is not None,
                'raw_preview': raw_data
            },
            'timestamp': int(time.time()),
            'source': 'direct-cache'
        }
    except Exception as e:
        return {
            'signals': [],
            'count': 0,
            'error': str(e),
            'timestamp': int(time.time()),
            'source': 'direct-cache-error'
        }

@router.get("/mobile-data")
async def get_mobile_data_direct() -> Dict[str, Any]:
    """Get mobile data directly from cache"""
    client = aiomcache.Client('localhost', 11211)
    
    # Get signals for confluence scores
    signals_data = await client.get(b'analysis:signals')
    confluence_scores = []
    if signals_data:
        data = json.loads(signals_data.decode())
        for signal in data.get('signals', [])[:15]:
            confluence_scores.append({
                "symbol": signal.get('symbol', ''),
                "score": round(signal.get('score', 50), 2),
                "price": signal.get('price', 0),
                "change_24h": round(signal.get('change_24h', 0), 2),
                "volume_24h": signal.get('volume', 0),
                "components": signal.get('components', {})
            })
    
    # Get movers
    movers_data = await client.get(b'market:movers')
    top_movers = {"gainers": [], "losers": []}
    if movers_data:
        movers = json.loads(movers_data.decode())
        top_movers['gainers'] = movers.get('gainers', [])[:5]
        top_movers['losers'] = movers.get('losers', [])[:5]
    
    # Get overview
    overview_data = await client.get(b'market:overview')
    overview = {}
    if overview_data:
        overview = json.loads(overview_data.decode())
    
    await client.close()
    
    from datetime import datetime
    return {
        "market_overview": {
            "market_regime": "NEUTRAL",
            "trend_strength": 0,
            "volatility": overview.get('volatility', 0),
            "btc_dominance": 0,
            "total_volume_24h": overview.get('total_volume', 0)
        },
        "confluence_scores": confluence_scores,
        "top_movers": top_movers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "source": "direct-cache"
    }