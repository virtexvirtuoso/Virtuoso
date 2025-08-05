#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging

from data_acquisition.binance.futures_client import BinanceFuturesClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_static_limits():
    """Test the static risk limits functionality."""
    
    print("🛡️  Testing Static Risk Limits Implementation")
    print("=" * 50)
    
    # Create futures client without API keys (public mode)
    futures_client = BinanceFuturesClient()
    
    try:
        # Test different symbol categories
        test_categories = {
            'Major Crypto (Tier 1)': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            'Large Cap (Tier 2)': ['ADAUSDT', 'SOLUSDT', 'XRPUSDT'],
            'Memecoins (Tier 3)': ['DOGEUSDT', '1000PEPEUSDT', 'WIFUSDT'],
            'Newer Tokens (Tier 4)': ['ALPACAUSDT', 'FARTCOINUSDT', 'VIRTUALUSDT'],
            'Unknown USDT': ['UNKNOWNUSDT'],
            'Non-USDT': ['BTCETH']
        }
        
        for category, symbols in test_categories.items():
            print(f"\n📊 {category}:")
            for symbol in symbols:
                try:
                    static_limits = futures_client.get_static_risk_limits(symbol)
                    max_lev = static_limits['maxLeverage']
                    brackets = len(static_limits['brackets'])
                    source = static_limits.get('source', 'unknown')
                    print(f"   ✅ {symbol}: {max_lev}x leverage, {brackets} brackets [{source}]")
                    
                    # Show bracket details for major symbols
                    if symbol in ['BTCUSDT', 'ETHUSDT', 'DOGEUSDT', 'UNKNOWNUSDT', 'BTCETH']:
                        print(f"      Brackets: {[b['initialLeverage'] for b in static_limits['brackets']]}")
                        
                except Exception as e:
                    print(f"   ❌ {symbol}: Error - {e}")
        
        # Test the actual API fallback mechanism
        print(f"\n⚖️  Testing API Fallback Mechanism:")
        print("-" * 40)
        
        test_symbols = ['BTCUSDT', 'DOGEUSDT', 'UNKNOWNUSDT']
        for symbol in test_symbols:
            try:
                print(f"\n🔧 Testing {symbol} via get_leverage_bracket (should fallback):")
                
                # This should trigger the fallback to static limits
                async with futures_client:
                    result = await futures_client.get_leverage_bracket(symbol)
                    
                if result and result.get('source') == 'static_fallback':
                    print(f"   ✅ Fallback successful: {result['maxLeverage']}x leverage")
                    print(f"   ℹ️  Note: {result.get('note', 'No note')}")
                else:
                    print(f"   ⚠️  Unexpected result: {result}")
                    
            except Exception as e:
                print(f"   ❌ Error testing {symbol}: {e}")
        
        print("\n🎉 Static limits test completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_static_limits()) 