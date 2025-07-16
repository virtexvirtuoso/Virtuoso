#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
from data_acquisition.binance.futures_client import BinanceFuturesClient

# Configure logging to see warnings but keep output clean
logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_open_interest_comprehensive():
    """Test open interest retrieval across various symbol categories."""
    
    print('📊 Comprehensive Open Interest Test')
    print('=' * 45)
    
    # Categorize symbols for testing
    symbol_categories = {
        'Major Cryptocurrencies': [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT'
        ],
        'Large Cap Altcoins': [
            'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LINKUSDT', 'AVAXUSDT'
        ],
        'Popular Memecoins': [
            '1000PEPEUSDT', 'SHIBUSDT', 'WIFUSDT', 'BONKUSDT', 'FLOKIUSDT'
        ],
        'Newer/Smaller Tokens': [
            'FARTCOINUSDT', 'VIRTUALUSDT', 'MOODENGUSDT', 'SOPHUSDT', 'TONUSDT', 'SUIUSDT'
        ],
        'Potentially Problematic': [
            'ALPACAUSDT', 'WCTUSDT', 'LPTUSDT'  # These might have issues
        ],
        'Invalid/Test Cases': [
            'INVALIDUSDT', 'FAKECOINUSDT'  # These should fail gracefully
        ]
    }
    
    # Track results
    total_tested = 0
    successful_retrievals = 0
    graceful_failures = 0
    unexpected_errors = 0
    
    async with BinanceFuturesClient() as client:
        for category, symbols in symbol_categories.items():
            print(f'\n🎯 {category}:')
            print('-' * (len(category) + 4))
            
            for symbol in symbols:
                total_tested += 1
                try:
                    oi_data = await client.get_open_interest(symbol)
                    oi_value = oi_data['openInterest']
                    
                    if oi_value > 0:
                        successful_retrievals += 1
                        print(f'   ✅ {symbol:15s}: {oi_value:>15,.0f}')
                    else:
                        graceful_failures += 1
                        print(f'   ⚠️  {symbol:15s}: {oi_value:>15,.0f} (no futures/closed)')
                        
                except Exception as e:
                    unexpected_errors += 1
                    print(f'   ❌ {symbol:15s}: Error - {str(e)[:50]}...')
    
    # Summary
    print(f'\n📈 Test Summary:')
    print('=' * 25)
    print(f'Total symbols tested:     {total_tested:>3}')
    print(f'Successful retrievals:    {successful_retrievals:>3} ({successful_retrievals/total_tested*100:.1f}%)')
    print(f'Graceful failures:        {graceful_failures:>3} ({graceful_failures/total_tested*100:.1f}%)')
    print(f'Unexpected errors:        {unexpected_errors:>3} ({unexpected_errors/total_tested*100:.1f}%)')
    
    # Check if we're getting reasonable data
    if successful_retrievals > 0:
        print(f'\n✅ Open interest retrieval is working correctly!')
        print(f'   • Successfully retrieved data for {successful_retrievals} symbols')
        print(f'   • Gracefully handled {graceful_failures} symbols without futures')
        if unexpected_errors == 0:
            print(f'   • No unexpected errors encountered')
        else:
            print(f'   ⚠️  {unexpected_errors} unexpected errors need investigation')
    else:
        print(f'\n❌ No successful open interest retrievals - needs investigation')

if __name__ == "__main__":
    asyncio.run(test_open_interest_comprehensive()) 