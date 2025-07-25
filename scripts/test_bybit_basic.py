#!/usr/bin/env python3
"""Basic test of Bybit connection and manipulation detection"""

import asyncio
import ccxt.async_support as ccxt
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.manipulation_detector import ManipulationDetector
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BasicTest')


async def main():
    print("Starting Bybit connection test...")
    
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    try:
        print("Loading markets...")
        await exchange.load_markets()
        print("✓ Markets loaded")
        
        symbol = 'BTC/USDT'
        print(f"\nFetching {symbol} orderbook...")
        orderbook = await exchange.fetch_order_book(symbol, limit=10)
        print(f"✓ Orderbook fetched: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
        
        print("\nFetching recent trades...")
        trades = await exchange.fetch_trades(symbol, limit=10)
        print(f"✓ Trades fetched: {len(trades)} trades")
        
        # Test manipulation detector
        print("\nInitializing manipulation detector...")
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {'max_snapshots': 10},
                'spoofing': {'enabled': True},
                'layering': {'enabled': True}
            }
        }
        
        detector = ManipulationDetector(config, logger)
        print("✓ Detector initialized")
        
        # Format data
        orderbook_formatted = {
            'bids': orderbook['bids'],
            'asks': orderbook['asks'],
            'timestamp': orderbook['timestamp']
        }
        
        trades_formatted = [
            {
                'id': trade['id'],
                'price': trade['price'],
                'size': trade['amount'],
                'side': trade['side'],
                'timestamp': trade['timestamp']
            }
            for trade in trades
        ]
        
        print("\nRunning manipulation analysis...")
        result = await detector.analyze_manipulation(orderbook_formatted, trades_formatted)
        
        print("\n=== RESULTS ===")
        print(f"Overall Likelihood: {result['overall_likelihood']:.1%}")
        print(f"Type: {result['manipulation_type']}")
        print(f"Severity: {result['severity']}")
        print(f"Spoofing: {result['spoofing']['likelihood']:.1%}")
        print(f"Layering: {result['layering']['likelihood']:.1%}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()
        print("Connection closed")


if __name__ == '__main__':
    asyncio.run(main())