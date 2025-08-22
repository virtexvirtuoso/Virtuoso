#!/usr/bin/env python3
"""Clear all test data from memcached"""

import asyncio
import aiomcache

async def clear_cache():
    """Clear all cache keys"""
    
    print("Clearing all test data from cache...")
    
    client = aiomcache.Client('localhost', 11211, pool_size=2)
    
    # List of all cache keys we've been using
    keys_to_clear = [
        b'market:overview',
        b'market:tickers', 
        b'market:movers',
        b'analysis:signals',
        b'analysis:market_regime',
        b'market:volume_leaders',
        b'market:statistics',
        b'dashboard:data',
        b'test:connection',
        b'test:heartbeat',
        b'test:simple',
        b'test:json'
    ]
    
    cleared_count = 0
    
    for key in keys_to_clear:
        try:
            # Check if key exists
            data = await client.get(key)
            if data:
                # Delete the key
                await client.delete(key)
                print(f"✓ Cleared {key.decode()}")
                cleared_count += 1
            else:
                print(f"- {key.decode()} (already empty)")
        except Exception as e:
            print(f"✗ Error clearing {key.decode()}: {e}")
    
    # Also try to flush all cache (if we have permission)
    try:
        await client.flush_all()
        print("✓ Flushed all cache data")
        cleared_count += 1
    except Exception as e:
        print(f"- Could not flush all: {e}")
    
    await client.close()
    
    print(f"\n✅ Cache cleanup complete! Cleared {cleared_count} items")
    print("Cache is now clean and ready for real market data")

async def verify_clean():
    """Verify cache is empty"""
    print("\nVerifying cache is clean...")
    print("-" * 30)
    
    client = aiomcache.Client('localhost', 11211, pool_size=2)
    
    keys_to_check = [
        b'market:overview',
        b'market:tickers', 
        b'market:movers',
        b'analysis:signals',
        b'analysis:market_regime',
        b'market:volume_leaders'
    ]
    
    all_empty = True
    
    for key in keys_to_check:
        data = await client.get(key)
        if data:
            print(f"⚠️  {key.decode()}: still has data")
            all_empty = False
        else:
            print(f"✓ {key.decode()}: empty")
    
    await client.close()
    
    if all_empty:
        print("\n✅ Cache is completely clean!")
    else:
        print("\n⚠️  Some data remains in cache")

async def main():
    await clear_cache()
    await verify_clean()

if __name__ == "__main__":
    asyncio.run(main())