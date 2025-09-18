#!/usr/bin/env python3
"""Check what's actually stored in cache"""

import asyncio
import aiomcache
import json

async def check_cache():
    client = aiomcache.Client('localhost', 11211)
    
    key = b'market:overview'
    data = await client.get(key)
    
    if data:
        parsed = json.loads(data.decode())
        print("Cache data structure:")
        for k, v in parsed.items():
            print(f"  {k}: {v}")
    else:
        print("No data in cache")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_cache())