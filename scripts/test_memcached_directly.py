#!/usr/bin/env python3
"""Test memcached connection and operations directly"""

import asyncio
import json
import time
import aiomcache

async def test_memcached():
    """Test basic memcached operations"""
    
    print("Testing Memcached Connection...")
    print("-" * 50)
    
    try:
        # Create client
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        print("✓ Client created")
        
        # Test 1: Simple set/get
        print("\n1. Testing simple set/get:")
        test_key = b'test:simple'
        test_value = b'Hello World'
        
        result = await client.set(test_key, test_value, exptime=60)
        print(f"  Set result: {result}")
        
        retrieved = await client.get(test_key)
        print(f"  Get result: {retrieved}")
        print(f"  Match: {'✓' if retrieved == test_value else '✗'}")
        
        # Test 2: JSON data
        print("\n2. Testing JSON data:")
        json_key = b'test:json'
        json_data = {'symbols': 10, 'volume': 1234567.89}
        json_value = json.dumps(json_data).encode()
        
        result = await client.set(json_key, json_value, exptime=60)
        print(f"  Set result: {result}")
        
        retrieved = await client.get(json_key)
        if retrieved:
            parsed = json.loads(retrieved.decode())
            print(f"  Retrieved: {parsed}")
            print(f"  Match: {'✓' if parsed == json_data else '✗'}")
        else:
            print("  Retrieved: None ✗")
        
        # Test 3: Market data format
        print("\n3. Testing market data format:")
        market_key = b'market:overview'
        market_data = {
            "total_symbols": 15,
            "total_volume": 123456789,
            "total_volume_24h": 123456789,
            "average_change": 2.5,
            "timestamp": int(time.time())
        }
        market_value = json.dumps(market_data).encode()
        
        result = await client.set(market_key, market_value, exptime=60)
        print(f"  Set result: {result}")
        
        retrieved = await client.get(market_key)
        if retrieved:
            parsed = json.loads(retrieved.decode())
            print(f"  Retrieved: {parsed}")
        else:
            print("  Retrieved: None ✗")
        
        # Test 4: Check what the cache adapter reads
        print("\n4. Reading all expected keys:")
        keys = [b'market:overview', b'market:tickers', b'analysis:signals', b'dashboard:data']
        
        for key in keys:
            data = await client.get(key)
            if data:
                try:
                    parsed = json.loads(data.decode())
                    if isinstance(parsed, dict):
                        print(f"  {key.decode()}: {len(parsed)} items")
                    elif isinstance(parsed, list):
                        print(f"  {key.decode()}: list with {len(parsed)} items")
                    else:
                        print(f"  {key.decode()}: {type(parsed)}")
                except:
                    print(f"  {key.decode()}: {data.decode()[:50]}")
            else:
                print(f"  {key.decode()}: empty")
        
        # Close client
        await client.close()
        print("\n✓ Client closed")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_memcached())