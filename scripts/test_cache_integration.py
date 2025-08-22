#!/usr/bin/env python3
"""
Test script to verify cache integration is working
Checks if ContinuousAnalysisManager is pushing data to memcached
"""

import asyncio
import json
import time
import aiomcache

async def test_cache_data():
    """Test if cache is receiving data from ContinuousAnalysisManager"""
    
    client = aiomcache.Client('localhost', 11211, pool_size=2)
    
    print("Testing cache integration...")
    print("-" * 50)
    
    # Check multiple times over 10 seconds
    for i in range(5):
        print(f"\nCheck #{i+1}:")
        
        try:
            # Check market overview
            overview = await client.get(b'market:overview')
            if overview:
                data = json.loads(overview.decode())
                print(f"✓ Market Overview: {data.get('total_symbols', 0)} symbols, "
                      f"Volume: {data.get('total_volume', 0):.2f}, "
                      f"Regime: {data.get('market_regime', 'unknown')}")
            else:
                print("✗ Market Overview: No data")
            
            # Check tickers
            tickers = await client.get(b'market:tickers')
            if tickers:
                data = json.loads(tickers.decode())
                print(f"✓ Tickers: {len(data)} symbols cached")
                # Show first 3 symbols
                for symbol in list(data.keys())[:3]:
                    ticker = data[symbol]
                    print(f"  - {symbol}: Price={ticker.get('price', 0):.4f}, "
                          f"Change={ticker.get('change_24h', 0):.2f}%, "
                          f"Signal={ticker.get('signal', 'N/A')}")
            else:
                print("✗ Tickers: No data")
            
            # Check signals
            signals = await client.get(b'analysis:signals')
            if signals:
                data = json.loads(signals.decode())
                print(f"✓ Signals: {data}")
            else:
                print("✗ Signals: No data")
            
            # Check market regime
            regime = await client.get(b'analysis:market_regime')
            if regime:
                print(f"✓ Market Regime: {regime.decode()}")
            else:
                print("✗ Market Regime: No data")
            
        except Exception as e:
            print(f"Error checking cache: {e}")
        
        if i < 4:
            print("\nWaiting 2 seconds before next check...")
            await asyncio.sleep(2)
    
    await client.close()
    
    print("\n" + "=" * 50)
    print("Test complete!")
    print("\nIf you see data above, the cache integration is working.")
    print("If not, ensure the main service is running with the fix applied.")

if __name__ == "__main__":
    asyncio.run(test_cache_data())