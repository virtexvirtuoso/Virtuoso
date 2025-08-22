#!/usr/bin/env python3
"""Debug cache to API data flow issue"""

import asyncio
import json
import aiomcache
import aiohttp
import sys

async def debug_cache_flow():
    print("=" * 60)
    print("DEBUGGING CACHE TO API DATA FLOW")
    print("=" * 60)
    
    # Step 1: Check raw cache contents
    client = aiomcache.Client('localhost', 11211)
    
    print("\n1. RAW CACHE CONTENTS:")
    print("-" * 40)
    
    # Check market:overview
    overview_data = await client.get(b'market:overview')
    if overview_data:
        overview = json.loads(overview_data.decode())
        print("market:overview keys:", list(overview.keys()))
        print(f"  trend_strength: {overview.get('trend_strength')}")
        print(f"  btc_dominance: {overview.get('btc_dominance')}")
        print(f"  current_volatility: {overview.get('current_volatility')}")
        print(f"  volatility: {overview.get('volatility')}")
        print(f"  total_volume: {overview.get('total_volume')}")
        print(f"  market_regime: {overview.get('market_regime')}")
    else:
        print("❌ No data in market:overview")
    
    # Check market:breadth
    breadth_data = await client.get(b'market:breadth')
    if breadth_data:
        breadth = json.loads(breadth_data.decode())
        print("\nmarket:breadth:")
        print(f"  up_count: {breadth.get('up_count')}")
        print(f"  down_count: {breadth.get('down_count')}")
    
    await client.close()
    
    # Step 2: Test cache adapter directly
    print("\n2. CACHE ADAPTER OUTPUT:")
    print("-" * 40)
    
    # Import and test cache adapter
    sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt/src')
    from api.cache_adapter import CacheAdapter
    
    cache_adapter = CacheAdapter()
    overview_from_adapter = await cache_adapter.get_market_overview()
    
    print("CacheAdapter.get_market_overview() returned:")
    print(f"  Keys: {list(overview_from_adapter.keys())}")
    print(f"  trend_strength: {overview_from_adapter.get('trend_strength')}")
    print(f"  btc_dominance: {overview_from_adapter.get('btc_dominance')}")
    print(f"  current_volatility: {overview_from_adapter.get('current_volatility')}")
    print(f"  volatility: {overview_from_adapter.get('volatility')}")
    
    # Step 3: Test API endpoint directly
    print("\n3. API ENDPOINT RESPONSE:")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Test cache adapter endpoint
        url = "http://localhost:8001/api/dashboard-cached/overview"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                print(f"/api/dashboard-cached/overview:")
                print(f"  Keys: {list(data.keys())}")
                for key in ['trend_strength', 'btc_dominance', 'current_volatility', 'volatility']:
                    if key in data:
                        print(f"  {key}: {data[key]}")
        
        # Test mobile-data endpoint
        url = "http://localhost:8001/api/dashboard-cached/mobile-data"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                overview = data.get('market_overview', {})
                print(f"\n/api/dashboard-cached/mobile-data:")
                print(f"  market_overview keys: {list(overview.keys())}")
                print(f"  trend_strength: {overview.get('trend_strength')}")
                print(f"  btc_dominance: {overview.get('btc_dominance')}")
                print(f"  current_volatility: {overview.get('current_volatility')}")
    
    # Step 4: Check for overwrites
    print("\n4. CHECKING FOR CACHE OVERWRITES:")
    print("-" * 40)
    
    # Wait and check again
    print("Waiting 5 seconds...")
    await asyncio.sleep(5)
    
    client = aiomcache.Client('localhost', 11211)
    overview_data = await client.get(b'market:overview')
    if overview_data:
        overview = json.loads(overview_data.decode())
        print(f"After 5s - trend_strength: {overview.get('trend_strength')}")
        print(f"After 5s - btc_dominance: {overview.get('btc_dominance')}")
    await client.close()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_cache_flow())