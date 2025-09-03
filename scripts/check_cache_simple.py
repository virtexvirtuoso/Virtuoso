#!/usr/bin/env python3
"""
Simple cache check without dependencies
"""
import asyncio
import aiomcache
import json

async def check_cache():
    """Check memcached for interpretation data"""
    client = aiomcache.Client('localhost', 11211)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
    
    print("=" * 60)
    print("🔍 Checking Confluence Interpretations in Memcached")
    print("=" * 60)
    
    for symbol in symbols:
        print(f"\n📊 {symbol}:")
        cache_key = f'confluence:breakdown:{symbol}'
        
        try:
            data = await client.get(cache_key.encode())
            if data:
                breakdown = json.loads(data.decode())
                print(f"  ✅ Found breakdown data")
                print(f"  - Sentiment: {breakdown.get('sentiment', 'N/A')}")
                print(f"  - Score: {breakdown.get('overall_score', 'N/A'):.2f}")
                
                if 'interpretations' in breakdown:
                    interp = breakdown['interpretations']
                    print(f"  ✅ Has interpretations ({len(interp)} components)")
                    if 'overall' in interp:
                        print(f"  - Overall: {interp['overall'][:80]}...")
                else:
                    print(f"  ❌ No interpretations")
            else:
                print(f"  ❌ No data in cache")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_cache())
