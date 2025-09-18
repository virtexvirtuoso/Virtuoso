#!/usr/bin/env python3
import asyncio
import aiomcache
import json

async def check_cache():
    client = aiomcache.Client("127.0.0.1", 11211)
    
    # Check market overview
    result = await client.get(b"market:overview")
    if result:
        data = json.loads(result.decode())
        print("✅ market:overview found!")
        print(f"  - active_symbols: {data.get('active_symbols', 0)}")
        print(f"  - symbols count: {len(data.get('symbols', []))}")
        if data.get('symbols'):
            for sym in list(data['symbols'])[:3]:
                if isinstance(sym, dict):
                    print(f"    * {sym.get('symbol', sym)}: ${sym.get('price', 'N/A')}")
                else:
                    print(f"    * {sym}")
    else:
        print("❌ market:overview NOT in cache")
    
    # Check analysis signals  
    result = await client.get(b"analysis:signals")
    if result:
        data = json.loads(result.decode())
        print(f"✅ analysis:signals found: {len(data.get('signals', []))} signals")
    else:
        print("❌ analysis:signals NOT in cache")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_cache())