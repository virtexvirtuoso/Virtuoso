#!/usr/bin/env python3
"""
Monitor cache keys in real-time
"""
import asyncio
import aiomcache
import json
import time

async def monitor():
    client = aiomcache.Client('localhost', 11211)
    
    print("Monitoring cache keys...")
    for i in range(10):
        # Check signals
        signals_data = await client.get(b'analysis:signals')
        if signals_data:
            data = json.loads(signals_data.decode())
            count = len(data.get('signals', []))
            ts = data.get('timestamp', 0)
            age = int(time.time()) - ts if ts else 999
            print(f"[{i}] analysis:signals: {count} signals (age: {age}s)")
        else:
            print(f"[{i}] analysis:signals: NOT FOUND")
        
        await asyncio.sleep(2)
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(monitor())