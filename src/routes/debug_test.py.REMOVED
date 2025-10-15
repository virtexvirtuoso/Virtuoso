"""
Debug route to test cache access in web context
"""
from fastapi import APIRouter
import aiomcache
import json
import asyncio
from typing import Dict, Any

router = APIRouter()

@router.get("/test-cache")
async def test_cache() -> Dict[str, Any]:
    """Test various cache access methods"""
    results = {}
    
    # Test 1: Direct aiomcache
    try:
        client = aiomcache.Client('localhost', 11211)
        data = await client.get(b'analysis:signals')
        if data:
            signals = json.loads(data.decode())
            results['direct_aiomcache'] = len(signals.get('signals', []))
        else:
            results['direct_aiomcache'] = 0
        await client.close()
    except Exception as e:
        results['direct_aiomcache'] = f"error: {e}"
    
    # Test 2: New client each time
    try:
        async def get_with_new_client():
            c = aiomcache.Client('localhost', 11211)
            d = await c.get(b'analysis:signals')
            await c.close()
            return d
        
        data = await get_with_new_client()
        if data:
            signals = json.loads(data.decode())
            results['new_client'] = len(signals.get('signals', []))
        else:
            results['new_client'] = 0
    except Exception as e:
        results['new_client'] = f"error: {e}"
    
    # Test 3: Check event loop
    results['event_loop'] = str(asyncio.get_event_loop())
    results['loop_running'] = asyncio.get_event_loop().is_running()
    
    # Test 4: Raw test key
    try:
        client = aiomcache.Client('localhost', 11211)
        # First set a test value
        await client.set(b'test:debug', b'test_value', exptime=60)
        # Then get it back
        test_val = await client.get(b'test:debug')
        results['test_key'] = test_val.decode() if test_val else None
        await client.close()
    except Exception as e:
        results['test_key'] = f"error: {e}"
    
    # Test 5: List all keys (stats)
    try:
        client = aiomcache.Client('localhost', 11211)
        stats = await client.stats()
        results['cache_items'] = stats.get(b'curr_items', b'0').decode()
        await client.close()
    except Exception as e:
        results['cache_items'] = f"error: {e}"
    
    return results

@router.get("/test-import")
async def test_import() -> Dict[str, Any]:
    """Test importing and using DirectCache"""
    from src.core.direct_cache import DirectCache
    
    # Test DirectCache
    signals = await DirectCache.get_signals()
    
    return {
        'DirectCache.get_signals': signals.get('count', 0),
        'client_class': str(DirectCache._client)
    }