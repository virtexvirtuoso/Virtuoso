#!/usr/bin/env python3
"""
Test cache fix - check if signals are being read correctly
"""
import asyncio
import aiomcache
import json

async def test_cache():
    client = aiomcache.Client('localhost', 11211)
    
    # Test reading signals key
    print("Testing cache key 'analysis:signals':")
    
    # Method 1: Direct read
    signals_data = await client.get(b'analysis:signals')
    if signals_data:
        signals = json.loads(signals_data.decode())
        print(f"  ✅ Direct read: {len(signals.get('signals', []))} signals")
        if signals.get('signals'):
            print(f"     First: {signals['signals'][0]['symbol']} - {signals['signals'][0]['score']}")
    else:
        print("  ❌ Direct read: No data")
    
    # Method 2: Using the exact method from adapter
    key = 'analysis:signals'
    data = await client.get(key.encode())
    
    result = {}
    if data:
        try:
            result = json.loads(data.decode())
        except:
            result = {}
    
    print(f"  Adapter method: {len(result.get('signals', []))} signals")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_cache())