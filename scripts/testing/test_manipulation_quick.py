#!/usr/bin/env python3
"""Quick test of manipulation detection with live Bybit data"""

import asyncio
import ccxt.async_support as ccxt
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.manipulation_detector import ManipulationDetector
import logging

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('QuickTest')


async def quick_test():
    """Quick test with just 3 snapshots"""
    
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    try:
        await exchange.load_markets()
        symbol = 'BTC/USDT'
        
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {'max_snapshots': 10},
                'spoofing': {'enabled': True},
                'layering': {'enabled': True}
            }
        }
        
        detector = ManipulationDetector(config, logger)
        
        print(f"Testing {symbol} manipulation detection...")
        
        previous_orderbook = None
        
        for i in range(5):  # Just 5 iterations
            print(f"\nFetching snapshot {i+1}...")
            
            # Fetch data
            orderbook_data = await exchange.fetch_order_book(symbol, limit=25)
            trades_data = await exchange.fetch_trades(symbol, limit=20)
            
            orderbook = {
                'bids': orderbook_data['bids'],
                'asks': orderbook_data['asks'],
                'timestamp': orderbook_data['timestamp']
            }
            
            trades = [
                {
                    'id': trade['id'],
                    'price': trade['price'],
                    'size': trade['amount'],
                    'side': trade['side'],
                    'timestamp': trade['timestamp']
                }
                for trade in trades_data
            ]
            
            # Analyze
            result = await detector.analyze_manipulation(orderbook, trades, previous_orderbook)
            
            print(f"✓ Analysis complete:")
            print(f"  - Overall Likelihood: {result['overall_likelihood']:.1%}")
            print(f"  - Type: {result['manipulation_type']}")
            print(f"  - Spoofing: {result['spoofing']['likelihood']:.1%}")
            print(f"  - Layering: {result['layering']['likelihood']:.1%}")
            
            if result['overall_likelihood'] > 0.5:
                print("  🚨 MANIPULATION DETECTED!")
            
            previous_orderbook = orderbook
            await asyncio.sleep(1)
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()


if __name__ == '__main__':
    asyncio.run(quick_test())