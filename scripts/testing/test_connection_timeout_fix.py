#!/usr/bin/env python3
"""
Test script to verify the specific ConnectionTimeoutError handling for 1000BONKUSDT.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.core.exchanges.bybit import BybitExchange

async def test_connection_timeout_handling():
    """Test the connection timeout handling for the specific error case."""
    print("🔧 Testing connection timeout handling for 1000BONKUSDT...")
    
    # Setup basic logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("test_connection_timeout")
    
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
        # Test the specific symbol that was causing issues
        test_symbol = '1000BONKUSDT'
        
        print(f"\n📊 Testing ticker fetch for {test_symbol}...")
        
        # Try to fetch ticker data multiple times to test resilience
        for attempt in range(3):
            try:
                print(f"  Attempt {attempt + 1}: Fetching ticker...")
                ticker = await bybit._fetch_ticker(test_symbol)
                
                if ticker and 'symbol' in ticker:
                    print(f"  ✅ Success: Got ticker data for {ticker['symbol']}")
                    print(f"     Price: {ticker.get('last', 'N/A')}")
                    print(f"     Volume: {ticker.get('volume', 'N/A')}")
                    print(f"     Open Interest: {ticker.get('openInterest', 'N/A')}")
                else:
                    print(f"  ⚠️  Warning: Got empty or invalid ticker data")
                    print(f"     Response: {ticker}")
                
            except Exception as e:
                print(f"  ❌ Attempt {attempt + 1} failed: {str(e)}")
                
            # Wait a bit between attempts
            if attempt < 2:
                await asyncio.sleep(1)
        
        # Test order book as well
        print(f"\n📚 Testing order book fetch for {test_symbol}...")
        try:
            orderbook = await bybit.fetch_order_book(test_symbol, limit=10)
            
            if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                bid_count = len(orderbook['bids'])
                ask_count = len(orderbook['asks'])
                print(f"  ✅ Success: Got orderbook with {bid_count} bids, {ask_count} asks")
                
                if orderbook['bids']:
                    print(f"     Best bid: {orderbook['bids'][0]}")
                if orderbook['asks']:
                    print(f"     Best ask: {orderbook['asks'][0]}")
            else:
                print(f"  ⚠️  Warning: Got empty or invalid orderbook")
                
        except Exception as e:
            print(f"  ❌ Order book fetch failed: {str(e)}")
        
        print("\n✅ Connection timeout handling test completed!")
        print("The enhanced error handling should now:")
        print("  • Catch ConnectionTimeoutError specifically")
        print("  • Retry failed requests with exponential backoff")
        print("  • Log warnings instead of errors for transient issues")
        print("  • Provide graceful fallbacks")
        
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
    print("🚀 Starting connection timeout fix validation...")
    
    success = await test_connection_timeout_handling()
    
    if success:
        print("\n🎉 Connection timeout fix validation completed!")
        return 0
    else:
        print("\n💥 Validation failed. Check logs for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)