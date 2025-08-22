#!/usr/bin/env python3
"""
Debug why web server can't read cache but scripts can
"""
import asyncio
import aiomcache
import json
import sys
import os

# Add project to path
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

async def test_direct_read():
    """Test direct cache read like scripts do"""
    print("=== DIRECT CACHE READ (like scripts) ===")
    client = aiomcache.Client('localhost', 11211)
    
    # Get all important keys
    keys_to_test = [
        b'analysis:signals',
        b'market:tickers',
        b'market:overview',
        b'market:movers'
    ]
    
    for key in keys_to_test:
        data = await client.get(key)
        if data:
            decoded = data.decode()
            try:
                parsed = json.loads(decoded)
                if isinstance(parsed, dict):
                    if 'signals' in parsed:
                        print(f"  {key.decode()}: {len(parsed.get('signals', []))} signals")
                    else:
                        print(f"  {key.decode()}: {list(parsed.keys())[:3]}...")
                else:
                    print(f"  {key.decode()}: {type(parsed)}")
            except:
                print(f"  {key.decode()}: string value")
        else:
            print(f"  {key.decode()}: NOT FOUND")
    
    await client.close()

async def test_shared_client():
    """Test with shared client like DirectCache does"""
    print("\n=== SHARED CLIENT (like DirectCache) ===")
    
    # Import DirectCache
    from src.core.direct_cache import DirectCache
    
    # Test get method
    signals = await DirectCache.get('analysis:signals', {})
    print(f"  DirectCache.get('analysis:signals'): {len(signals.get('signals', []))} signals")
    
    # Test get_signals method
    signals_data = await DirectCache.get_signals()
    print(f"  DirectCache.get_signals(): {signals_data.get('count', 0)} signals")

async def test_web_context():
    """Test in web-like context"""
    print("\n=== WEB CONTEXT SIMULATION ===")
    
    # Import FastAPI components
    from fastapi import FastAPI
    from src.api.routes import dashboard_fast
    
    # Create app instance
    app = FastAPI()
    
    # Test the actual endpoint function
    result = await dashboard_fast.signals()
    print(f"  dashboard_fast.signals(): {len(result.get('signals', []))} signals")
    
    # Test mobile endpoint
    mobile_result = await dashboard_fast.mobile()
    print(f"  dashboard_fast.mobile(): {len(mobile_result.get('confluence_scores', []))} scores")

async def test_adapter():
    """Test cache adapter"""
    print("\n=== CACHE ADAPTER TEST ===")
    
    # Import the adapter
    from src.api.cache_adapter_direct import cache_adapter
    
    # Test get_signals
    signals = await cache_adapter.get_signals()
    print(f"  cache_adapter.get_signals(): {signals.get('count', 0)} signals")
    
    # Test internal _get method
    signals_data = await cache_adapter._get('analysis:signals', {})
    print(f"  cache_adapter._get('analysis:signals'): {len(signals_data.get('signals', []))} signals")

async def main():
    print("CACHE DEBUG INVESTIGATION")
    print("=" * 40)
    
    await test_direct_read()
    await test_shared_client()
    await test_adapter()
    
    try:
        await test_web_context()
    except Exception as e:
        print(f"\n  Web context error: {e}")
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    print("If direct read works but others fail, it's a client initialization issue")
    print("If all work here but not in web server, it's a uvicorn context issue")

if __name__ == "__main__":
    asyncio.run(main())