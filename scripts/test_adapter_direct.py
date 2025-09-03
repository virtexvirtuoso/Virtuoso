#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_adapter():
    # Import the adapter being used
    try:
        from src.api.cache_adapter_direct import cache_adapter
        print("Using Direct Cache Adapter")
    except ImportError:
        from src.api.cache_adapter_direct import cache_adapter
        print("Using standard cache adapter")
    
    # Test get_signals
    signals = await cache_adapter.get_signals()
    print(f"\nget_signals() returned: {len(signals.get('signals', []))} signals")
    if signals.get('signals'):
        print(f"  First signal: {signals['signals'][0]['symbol']} - Score: {signals['signals'][0]['score']}")
    
    # Test get_mobile_data
    mobile = await cache_adapter.get_mobile_data()
    print(f"\nget_mobile_data() confluence_scores: {len(mobile.get('confluence_scores', []))}")
    if mobile.get('confluence_scores'):
        print(f"  First score: {mobile['confluence_scores'][0]['symbol']} - Score: {mobile['confluence_scores'][0]['score']}")

if __name__ == "__main__":
    asyncio.run(test_adapter())