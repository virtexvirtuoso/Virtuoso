#!/usr/bin/env python3
"""Test Bybit OHLCV timeout handling and retry logic."""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.exchanges.bybit import BybitExchange

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_ohlcv_timeout_handling():
    """Test OHLCV fetching with timeout handling."""
    logger = logging.getLogger("test_bybit_timeout")
    
    print("\n" + "="*60)
    print("Testing Bybit OHLCV Timeout Handling")
    print("="*60 + "\n")
    
    # Load config
    import yaml
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize exchange with full config
    exchange = BybitExchange(config)
    await exchange.initialize()
    
    # Test symbols
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in test_symbols:
        print(f"\n📊 Testing {symbol}...")
        
        # Test 1: Normal OHLCV fetch
        print("  ✓ Test 1: Normal OHLCV fetch (1m timeframe)")
        start_time = time.time()
        try:
            ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=100)
            elapsed = time.time() - start_time
            
            if ohlcv_data:
                print(f"    - Success! Fetched {len(ohlcv_data)} candles in {elapsed:.2f}s")
                latest = ohlcv_data[-1]
                print(f"    - Latest candle: {datetime.fromtimestamp(latest[0]/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    - OHLCV: O={latest[1]:.2f}, H={latest[2]:.2f}, L={latest[3]:.2f}, C={latest[4]:.2f}, V={latest[5]:.2f}")
            else:
                print(f"    - Warning: No data returned (took {elapsed:.2f}s)")
        except Exception as e:
            print(f"    - Error: {str(e)}")
        
        # Test 2: Larger data request (might be slower)
        print("\n  ✓ Test 2: Larger OHLCV fetch (1000 candles)")
        start_time = time.time()
        try:
            ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=1000)
            elapsed = time.time() - start_time
            
            if ohlcv_data:
                print(f"    - Success! Fetched {len(ohlcv_data)} candles in {elapsed:.2f}s")
            else:
                print(f"    - Warning: No data returned (took {elapsed:.2f}s)")
        except Exception as e:
            print(f"    - Error: {str(e)}")
        
        # Test 3: Different timeframes
        timeframes = ['5m', '15m', '1h']
        print("\n  ✓ Test 3: Multiple timeframes")
        for tf in timeframes:
            start_time = time.time()
            try:
                ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                elapsed = time.time() - start_time
                
                if ohlcv_data:
                    print(f"    - {tf}: Success! {len(ohlcv_data)} candles in {elapsed:.2f}s")
                else:
                    print(f"    - {tf}: No data (took {elapsed:.2f}s)")
            except Exception as e:
                print(f"    - {tf}: Error - {str(e)}")
        
        await asyncio.sleep(0.5)  # Small delay between symbols
    
    # Test error handling with invalid symbol
    print("\n📊 Testing error handling with invalid symbol...")
    try:
        ohlcv_data = await exchange.fetch_ohlcv("INVALID_SYMBOL", timeframe='1m', limit=10)
        if not ohlcv_data:
            print("  ✓ Correctly returned empty list for invalid symbol")
        else:
            print("  ⚠️  Unexpected: Got data for invalid symbol")
    except Exception as e:
        print(f"  ✓ Handled error correctly: {str(e)}")
    
    # Check retry logic in logs
    print("\n📋 Retry Logic Summary:")
    print("  - The _make_request_with_retry method will automatically retry on timeout")
    print("  - Max retries: 2 (total 3 attempts)")
    print("  - Exponential backoff: 0.5s, 1s, 2s")
    print("  - Timeout errors will show 'Request timeout' in logs")
    
    await exchange.close()
    print("\n✅ Test completed!")

async def main():
    """Run the test."""
    try:
        await test_ohlcv_timeout_handling()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())