#!/usr/bin/env python3
"""Test if signals in cache have components"""

import asyncio
import json
import aiomcache

async def test_cache():
    """Check cache content"""
    client = aiomcache.Client("localhost", 11211)
    
    # Check analysis:signals
    data = await client.get(b"analysis:signals")
    if data:
        signals = json.loads(data.decode())
        print(f"Found {len(signals.get('signals', []))} signals")
        if signals.get('signals'):
            first = signals['signals'][0]
            print(f"First signal keys: {list(first.keys())}")
            print(f"Has components: {'components' in first}")
            if 'components' in first:
                print(f"Components: {first['components']}")
    else:
        print("No analysis:signals in cache")
    
    # Check a breakdown key
    breakdown = await client.get(b"confluence:breakdown:BTCUSDT")
    if breakdown:
        data = json.loads(breakdown.decode())
        print(f"\nBTCUSDT breakdown keys: {list(data.keys())}")
        if 'components' in data:
            print(f"Components: {data['components']}")

if __name__ == "__main__":
    asyncio.run(test_cache())