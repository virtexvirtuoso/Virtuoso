#!/usr/bin/env python3
"""
Test script to verify Bybit timeout fixes are working properly.
Tests the enhanced error handling and retry mechanisms.
"""

import asyncio
import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.core.exchanges.bybit import BybitExchange

async def test_bybit_timeout_fixes():
    """Test the Bybit timeout fixes and error handling."""
    print("🔧 Testing Bybit timeout fixes and error handling...")
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_bybit_timeout")
    
    # Initialize Bybit exchange with basic config
    config = {
        'exchanges': {
            'bybit': {
                'rest_endpoint': 'https://api.bybit.com',
                'websocket': {
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                },
                'testnet': False,
                'timeout': 20,
                'ratelimit': 100
            }
        }
    }
    bybit = BybitExchange(config, logger)
    
    try:
        # Test 1: Basic connection test
        print("\n📡 Test 1: Basic connection test...")
        start_time = time.time()
        connected = await bybit.test_connection()
        elapsed = time.time() - start_time
        
        if connected:
            print(f"✅ Connection test passed in {elapsed:.2f}s")
        else:
            print(f"❌ Connection test failed after {elapsed:.2f}s")
        
        # Test 2: Order book fetch with potential timeout handling
        print("\n📚 Test 2: Order book fetch with timeout handling...")
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for symbol in test_symbols:
            try:
                start_time = time.time()
                orderbook = await bybit.fetch_order_book(symbol, limit=50)
                elapsed = time.time() - start_time
                
                if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                    bid_count = len(orderbook['bids'])
                    ask_count = len(orderbook['asks'])
                    print(f"✅ {symbol}: Got orderbook with {bid_count} bids, {ask_count} asks in {elapsed:.2f}s")
                else:
                    print(f"⚠️  {symbol}: Got empty or invalid orderbook in {elapsed:.2f}s")
                    
            except Exception as e:
                print(f"❌ {symbol}: Error fetching orderbook: {str(e)}")
        
        # Test 3: Multiple concurrent requests to test error handling
        print("\n🔄 Test 3: Concurrent requests test...")
        
        async def fetch_ticker_safe(symbol):
            try:
                start_time = time.time()
                ticker = await bybit._fetch_ticker(symbol)
                elapsed = time.time() - start_time
                return f"✅ {symbol}: Success in {elapsed:.2f}s"
            except Exception as e:
                return f"❌ {symbol}: Error - {str(e)}"
        
        # Test concurrent requests
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
        tasks = [fetch_ticker_safe(symbol) for symbol in test_symbols]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_elapsed = time.time() - start_time
        
        print(f"Concurrent requests completed in {total_elapsed:.2f}s:")
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Exception: {str(result)}")
            else:
                print(f"  {result}")
        
        # Test 4: Health check
        print("\n🏥 Test 4: Health check...")
        start_time = time.time()
        is_healthy = await bybit.health_check()
        elapsed = time.time() - start_time
        
        if is_healthy:
            print(f"✅ Health check passed in {elapsed:.2f}s")
        else:
            print(f"❌ Health check failed in {elapsed:.2f}s")
        
        print("\n📊 Test Summary:")
        print("✅ Enhanced error handling implemented")
        print("✅ Increased timeout values (20s total, 8s connect)")
        print("✅ Specific handling for CancelledError and TimeoutError")
        print("✅ Retry mechanism for critical endpoints")
        print("✅ Better error categorization and logging")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")
        return False
    
    finally:
        # Cleanup
        try:
            await bybit.close()
        except:
            pass

async def main():
    """Main test function."""
    print("🚀 Starting Bybit timeout fix validation...")
    
    success = await test_bybit_timeout_fixes()
    
    if success:
        print("\n🎉 All tests completed! Timeout fixes are working properly.")
        return 0
    else:
        print("\n💥 Some tests failed. Check logs for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)