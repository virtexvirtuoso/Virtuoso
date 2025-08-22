#!/usr/bin/env python3
"""Check cache contents on VPS"""
import asyncio
import aiomcache
import json

async def check_cache():
    client = aiomcache.Client('localhost', 11211)
    
    keys = [
        'market:overview',
        'market:tickers', 
        'analysis:signals',
        'analysis:market_regime',
        'market:movers'
    ]
    
    print("Checking cache contents...")
    for key in keys:
        try:
            data = await client.get(key.encode())
            if data:
                try:
                    parsed = json.loads(data.decode())
                    if isinstance(parsed, dict):
                        print(f"✓ {key}: {len(parsed)} items")
                    else:
                        print(f"✓ {key}: {type(parsed).__name__}")
                except:
                    print(f"✓ {key}: {data.decode()[:50]}...")
            else:
                print(f"✗ {key}: EMPTY")
        except Exception as e:
            print(f"✗ {key}: ERROR - {e}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_cache())