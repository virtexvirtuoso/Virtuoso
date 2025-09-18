#!/usr/bin/env python3
"""Check what ticker/market data is available in cache"""

import asyncio
import json
import aiomcache

async def check_cache():
    """Check various cache keys for market data"""
    client = aiomcache.Client("localhost", 11211)
    
    keys_to_check = [
        'symbols:top',
        'dashboard:symbols', 
        'market:overview',
        'market:tickers',
        'tickers:all',
        'ticker:BTCUSDT',
        'price:BTCUSDT',
        'market_data:BTCUSDT',
        'confluence:BTCUSDT'
    ]
    
    print("Checking cache keys for market data:")
    print("-" * 40)
    
    for key in keys_to_check:
        try:
            data = await client.get(key.encode())
            if data:
                parsed = json.loads(data.decode())
                if isinstance(parsed, dict):
                    print(f"✓ {key}: {list(parsed.keys())[:5]}")
                    # Check if it has price data
                    if 'price' in str(parsed) or 'last' in str(parsed):
                        print(f"  → Contains price data")
                elif isinstance(parsed, list) and len(parsed) > 0:
                    print(f"✓ {key}: List with {len(parsed)} items")
                    if isinstance(parsed[0], dict):
                        print(f"  → First item keys: {list(parsed[0].keys())[:5]}")
                else:
                    print(f"✓ {key}: Found ({type(parsed).__name__})")
            else:
                print(f"✗ {key}: Not found")
        except Exception as e:
            print(f"✗ {key}: Error - {e}")

if __name__ == "__main__":
    asyncio.run(check_cache())