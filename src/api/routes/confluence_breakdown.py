"""
API routes for detailed confluence breakdown data.

NAMING CONVENTION NOTE:
"Confluence" terminology is retained in API endpoints for backward compatibility.
User-facing branding uses "Alpha Analysis" / "Alpha Score".

Endpoints (DO NOT RENAME):
- /confluence/breakdown/{symbol} -> Alpha Analysis breakdown
- /confluence/latest -> Latest Alpha scores
- /confluence/all -> All Alpha analyses
- /confluence/components/{symbol} -> Alpha component details

See docs/07-technical/CONFLUENCE_TO_ALPHA_MIGRATION_PLAN.md
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import aiomcache
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_cache_client():
    """Get cache client."""
    return aiomcache.Client('localhost', 11211, pool_size=2)

@router.get("/confluence/breakdown/{symbol}")
async def get_confluence_breakdown(symbol: str) -> Dict[str, Any]:
    """Get detailed confluence breakdown for a symbol."""
    try:
        client = await get_cache_client()
        
        # Try to get full breakdown
        data = await client.get(f'confluence:breakdown:{symbol}'.encode())
        
        if data:
            breakdown = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'data': breakdown
            }
        
        # Fallback to simple confluence data
        data = await client.get(f'confluence:{symbol}'.encode())
        
        if data:
            simple_data = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'data': {
                    'symbol': symbol,
                    'overall_score': simple_data.get('score'),
                    'sentiment': simple_data.get('sentiment'),
                    'components': simple_data.get('components', {}),
                    'has_breakdown': False
                }
            }
        
        await client.close()
        raise HTTPException(status_code=404, detail=f"No confluence data for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting confluence breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/confluence/latest")
async def get_latest_confluence() -> Dict[str, Any]:
    """Get the latest confluence breakdown available."""
    try:
        client = await get_cache_client()
        
        # Get latest breakdown
        data = await client.get(b'dashboard:latest_breakdown')
        
        if data:
            breakdown = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'data': breakdown
            }
        
        # Fallback to signals
        data = await client.get(b'analysis:signals')
        
        if data:
            signals = json.loads(data.decode())
            if signals.get('signals'):
                # Return the first signal with breakdown
                for signal in signals['signals']:
                    if signal.get('has_breakdown'):
                        await client.close()
                        return {
                            'status': 'success',
                            'data': signal
                        }
            
            await client.close()
            return {
                'status': 'success',
                'data': signals.get('signals', [])[0] if signals.get('signals') else None
            }
        
        await client.close()
        return {
            'status': 'error',
            'message': 'No confluence data available'
        }
        
    except Exception as e:
        logger.error(f"Error getting latest confluence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/confluence/all")
async def get_all_confluence() -> Dict[str, Any]:
    """Get confluence data for all tracked symbols."""
    try:
        client = await get_cache_client()
        
        # Get all signals
        data = await client.get(b'analysis:signals')
        
        if data:
            signals = json.loads(data.decode())
            
            # Enhance with breakdown data if available
            enhanced_signals = []
            for signal in signals.get('signals', []):
                symbol = signal.get('symbol')
                if symbol:
                    # Try to get breakdown
                    breakdown_data = await client.get(f'confluence:breakdown:{symbol}'.encode())
                    if breakdown_data:
                        breakdown = json.loads(breakdown_data.decode())
                        signal.update({
                            'has_breakdown': True,
                            'components': breakdown.get('components', {}),
                            'sub_components': breakdown.get('sub_components', {}),
                            'interpretations': breakdown.get('interpretations', {}),
                            'reliability': breakdown.get('reliability')
                        })
                enhanced_signals.append(signal)
            
            await client.close()
            return {
                'status': 'success',
                'count': len(enhanced_signals),
                'data': enhanced_signals
            }
        
        await client.close()
        return {
            'status': 'success',
            'count': 0,
            'data': []
        }
        
    except Exception as e:
        logger.error(f"Error getting all confluence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/confluence/components/{symbol}")
async def get_component_scores(symbol: str) -> Dict[str, Any]:
    """Get just the component scores for a symbol."""
    try:
        client = await get_cache_client()
        
        # Try breakdown first
        data = await client.get(f'confluence:breakdown:{symbol}'.encode())
        
        if data:
            breakdown = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'symbol': symbol,
                'overall_score': breakdown.get('overall_score'),
                'components': breakdown.get('components', {}),
                'sub_components': breakdown.get('sub_components', {})
            }
        
        # Try simple confluence
        data = await client.get(f'confluence:{symbol}'.encode())
        
        if data:
            simple_data = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'symbol': symbol,
                'overall_score': simple_data.get('score'),
                'components': simple_data.get('components', {})
            }
        
        await client.close()
        raise HTTPException(status_code=404, detail=f"No component data for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting component scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))