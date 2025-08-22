#!/usr/bin/env python3
"""Debug the analysis endpoint cache access"""

import asyncio
import aiomcache
import json

async def debug_cache():
    client = aiomcache.Client('localhost', 11211, pool_size=2)
    
    # Test different symbols
    symbols = ['LINKUSDT', 'BTCUSDT', 'ETHUSDT']
    
    for symbol in symbols:
        print(f"\n🔍 Testing {symbol}:")
        
        # Check breakdown cache
        breakdown_key = f'confluence:breakdown:{symbol}'
        data = await client.get(breakdown_key.encode())
        
        if data:
            breakdown = json.loads(data.decode())
            print(f"  ✅ breakdown data found: score={breakdown.get('overall_score')}")
            print(f"  📊 components: {len(breakdown.get('components', {}))}")
            print(f"  📋 interpretations: {len(breakdown.get('interpretations', {}))}")
        else:
            print(f"  ❌ No breakdown data found for key: {breakdown_key}")
        
        # Check simple confluence cache
        simple_key = f'confluence:{symbol}'
        simple_data = await client.get(simple_key.encode())
        
        if simple_data:
            simple = json.loads(simple_data.decode())
            print(f"  ✅ simple data found: score={simple.get('score')}")
        else:
            print(f"  ❌ No simple data found for key: {simple_key}")
    
    # Check latest breakdown
    latest_data = await client.get(b'dashboard:latest_breakdown')
    if latest_data:
        latest = json.loads(latest_data.decode())
        print(f"\n📈 Latest breakdown: {latest.get('symbol')} - {latest.get('overall_score')}")
    else:
        print("\n❌ No latest breakdown found")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(debug_cache())