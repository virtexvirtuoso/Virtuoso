#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
from data_acquisition.binance.futures_client import BinanceFuturesClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_improved_error_handling():
    """Test the improved error handling for 400 Bad Request errors."""
    
    print('🧪 Testing Improved Error Handling')
    print('=' * 40)
    
    # Test symbols that might have 400 errors
    test_symbols = ['ALPACAUSDT', 'BTCUSDT', 'INVALIDUSDT']
    
    async with BinanceFuturesClient() as client:
        for symbol in test_symbols:
            print(f'\n🎯 Testing {symbol}:')
            try:
                oi = await client.get_open_interest(symbol)
                print(f'   ✅ Open Interest: {oi["openInterest"]:,.0f}')
            except Exception as e:
                print(f'   ❌ Exception: {e}')

if __name__ == "__main__":
    asyncio.run(test_improved_error_handling()) 