#!/usr/bin/env python3
"""
Debug signals aggregation to understand why 0 signals are being generated
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def debug_aggregation():
    """Debug the signals aggregation process step by step"""
    print("=== Debugging Signals Aggregation ===")

    try:
        import aiomcache
        client = aiomcache.Client('localhost', 11211)

        # Check step 1: Do we have symbols?
        print("\n1. Checking for top symbols...")
        try:
            from src.core.market.top_symbols import TopSymbolsManager
            top_symbols_manager = TopSymbolsManager()
            symbols = await top_symbols_manager.get_top_symbols(limit=10)
            print(f"✅ Found {len(symbols)} top symbols:")
            for i, symbol in enumerate(symbols[:5]):
                print(f"   {i+1}. {symbol.get('symbol', 'N/A')} - Volume: ${symbol.get('volume', 0):,.0f}")

        except Exception as e:
            print(f"❌ Error getting top symbols: {e}")
            # Use fallback list
            symbols_list = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
            print(f"Using fallback symbols: {symbols_list}")

        # Check step 2: Do we have ticker data?
        print("\n2. Checking ticker data...")
        tickers_cache = await client.get(b'market:tickers')
        if tickers_cache:
            tickers_data = json.loads(tickers_cache.decode())
            ticker_count = len(tickers_data.get('tickers', []))
            print(f"✅ Found {ticker_count} tickers in cache")

            if ticker_count > 0:
                sample_ticker = tickers_data['tickers'][0]
                print(f"Sample ticker: {sample_ticker.get('symbol', 'N/A')} - ${sample_ticker.get('price', 0)}")
        else:
            print("❌ No ticker data in cache")

        # Check step 3: Do we have breakdown data?
        print("\n3. Checking breakdown data...")
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        breakdown_count = 0

        for symbol in test_symbols:
            cache_key = f'confluence:breakdown:{symbol}'.encode()
            breakdown_data = await client.get(cache_key)

            if breakdown_data:
                breakdown_count += 1
                breakdown = json.loads(breakdown_data.decode())
                score = breakdown.get('overall_score', 0)
                components = breakdown.get('components', {})
                print(f"✅ {symbol}: score={score}, components={len(components)}")
            else:
                print(f"❌ {symbol}: No breakdown data")

        print(f"\nFound breakdown data for {breakdown_count}/{len(test_symbols)} test symbols")

        # Check step 4: Manual aggregation
        print("\n4. Running manual aggregation...")

        if breakdown_count > 0:
            print("✅ Should be able to aggregate signals")

            # Run the actual aggregation
            from src.main import aggregate_confluence_signals
            await aggregate_confluence_signals()

            # Check results
            await asyncio.sleep(1)
            signals_data = await client.get(b'analysis:signals')

            if signals_data:
                data = json.loads(signals_data.decode())
                signal_count = len(data.get('signals', []))
                print(f"✅ Aggregation resulted in {signal_count} signals")

                if signal_count > 0:
                    sample = data['signals'][0]
                    print(f"Sample: {sample.get('symbol')} - {sample.get('confluence_score')}")
                else:
                    print("❌ Aggregation produced 0 signals - investigating...")

                    # Check the raw data structure
                    print("Raw signals data keys:", list(data.keys()))
                    print("Signals list type:", type(data.get('signals', [])))

            else:
                print("❌ No signals data after aggregation")
        else:
            print("❌ No breakdown data available for aggregation")

        await client.close()

    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

async def check_cache_keys():
    """Check what keys are in the cache"""
    print("\n=== Checking Cache Keys ===")

    try:
        import aiomcache
        client = aiomcache.Client('localhost', 11211)

        # Check common keys
        keys_to_check = [
            b'market:tickers',
            b'analysis:signals',
            b'market:overview',
            b'market:movers',
            b'confluence:breakdown:BTCUSDT',
            b'confluence:breakdown:ETHUSDT'
        ]

        for key in keys_to_check:
            data = await client.get(key)
            if data:
                try:
                    if key.startswith(b'confluence:'):
                        obj = json.loads(data.decode())
                        print(f"✅ {key.decode()}: {len(obj)} keys")
                    else:
                        obj = json.loads(data.decode())
                        if isinstance(obj, dict):
                            if 'tickers' in obj:
                                print(f"✅ {key.decode()}: {len(obj['tickers'])} items")
                            elif 'signals' in obj:
                                print(f"✅ {key.decode()}: {len(obj['signals'])} signals")
                            else:
                                print(f"✅ {key.decode()}: {len(obj)} keys")
                        else:
                            print(f"✅ {key.decode()}: {type(obj)}")
                except:
                    print(f"✅ {key.decode()}: {len(data)} bytes (non-JSON)")
            else:
                print(f"❌ {key.decode()}: Not found")

        await client.close()

    except Exception as e:
        print(f"❌ Cache check error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_aggregation())
    asyncio.run(check_cache_keys())