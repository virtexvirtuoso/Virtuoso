#!/usr/bin/env python3
import asyncio
import json
import aiomcache

async def check():
    client = aiomcache.Client('localhost', 11211)
    
    keys = [
        b'market:overview',
        b'market:tickers', 
        b'analysis:signals',
        b'dashboard:data'
    ]
    
    for key in keys:
        try:
            data = await client.get(key)
            if data:
                decoded = data.decode()
                try:
                    parsed = json.loads(decoded)
                    if isinstance(parsed, dict):
                        print(f"{key.decode()}: {len(parsed)} items")
                    elif isinstance(parsed, list):
                        print(f"{key.decode()}: list with {len(parsed)} items")
                    else:
                        print(f"{key.decode()}: {type(parsed)}")
                except:
                    print(f"{key.decode()}: {decoded[:50]}...")
            else:
                print(f"{key.decode()}: empty")
        except Exception as e:
            print(f"{key.decode()}: error - {e}")
    
    await client.close()

asyncio.run(check())