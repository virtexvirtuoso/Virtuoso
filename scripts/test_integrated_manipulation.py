#!/usr/bin/env python3
"""Test integrated manipulation detection in OrderbookIndicators"""

import ccxt
import sys
import os
from datetime import datetime
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.orderbook_indicators import OrderbookIndicators
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IntegratedTest')

async def test_integrated_manipulation():
    """Test the integrated manipulation detection in OrderbookIndicators"""
    
    # Configuration with manipulation detection enabled
    config = {
        'timeframes': {
            '1m': {'enabled': True}
        },
        'manipulation_detection': {
            'enabled': True,
            'history': {'max_snapshots': 50},
            'spoofing': {'enabled': True, 'min_order_size_usd': 10000},
            'layering': {'enabled': True},
            'wash_trading': {'enabled': True},
            'fake_liquidity': {'enabled': True},
            'iceberg': {'enabled': True}
        },
        'orderbook': {
            'depth_levels': 10,
            'weights': {
                'imbalance': 0.3,
                'pressure': 0.3,
                'liquidity': 0.2,
                'spread': 0.2
            }
        }
    }
    
    # Initialize OrderbookIndicators with integrated manipulation detection
    indicators = OrderbookIndicators(config, logger)
    
    # Initialize exchange
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    exchange.load_markets()
    symbol = 'BTC/USDT'
    
    print(f"🔍 Testing Integrated Manipulation Detection in OrderbookIndicators")
    print(f"Symbol: {symbol}")
    print(f"Manipulation Detection: {'✅ ENABLED' if indicators.manipulation_enabled else '❌ DISABLED'}")
    print()
    
    # Test with 5 snapshots
    for i in range(5):
        try:
            # Fetch market data
            orderbook = exchange.fetch_order_book(symbol, limit=50)
            trades = exchange.fetch_trades(symbol, limit=100)
            
            # Format market data for indicators
            market_data = {
                'orderbook': {
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks'],
                    'timestamp': orderbook['timestamp']
                },
                'trades': [
                    {
                        'id': trade['id'],
                        'price': trade['price'],
                        'size': trade['amount'],
                        'side': trade['side'],
                        'timestamp': trade['timestamp']
                    }
                    for trade in trades
                ]
            }
            
            # Calculate indicators (which now includes integrated manipulation detection)
            result = await indicators.calculate(symbol, market_data)
            
            # Extract manipulation results
            manipulation_analysis = result.get('analysis', {}).get('manipulation_analysis', {})
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Snapshot #{i+1}")
            print(f"  Orderbook Score: {result.get('score', 0):.1f}")
            print(f"  Manipulation Likelihood: {manipulation_analysis.get('overall_likelihood', 0):.1%}")
            print(f"  Manipulation Type: {manipulation_analysis.get('manipulation_type', 'none')}")
            print(f"  Confidence: {manipulation_analysis.get('confidence', 0):.1%}")
            
            # Show specific detections if significant
            if manipulation_analysis.get('overall_likelihood', 0) > 0.3:
                print(f"  🚨 Detection Details:")
                spoofing = manipulation_analysis.get('spoofing', {})
                layering = manipulation_analysis.get('layering', {})
                wash = manipulation_analysis.get('wash_trading', {})
                fake = manipulation_analysis.get('fake_liquidity', {})
                iceberg = manipulation_analysis.get('iceberg_orders', {})
                
                if spoofing.get('likelihood', 0) > 0.4:
                    print(f"    • Spoofing: {spoofing['likelihood']:.1%}")
                if layering.get('likelihood', 0) > 0.4:
                    print(f"    • Layering: {layering['likelihood']:.1%}")
                if wash.get('likelihood', 0) > 0.4:
                    print(f"    • Wash Trading: {wash['likelihood']:.1%}")
                if fake.get('likelihood', 0) > 0.4:
                    print(f"    • Fake Liquidity: {fake['likelihood']:.1%}")
                if iceberg.get('likelihood', 0) > 0.4:
                    print(f"    • Iceberg Orders: {iceberg['likelihood']:.1%}")
            
            # Show advanced metrics if available
            advanced = manipulation_analysis.get('advanced_metrics', {})
            if advanced:
                print(f"  📊 Advanced Metrics:")
                print(f"    • Tracked Orders: {advanced.get('tracked_orders', 0)}")
                print(f"    • Phantom Orders: {advanced.get('phantom_orders', 0)}")
                print(f"    • Iceberg Candidates: {advanced.get('iceberg_candidates', 0)}")
            
            print()
            
            # Wait between snapshots
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error in snapshot {i+1}: {str(e)}")
    
    print("✅ Integrated manipulation detection test completed successfully!")
    print(f"Final detection count: {indicators.manipulation_detection_count}")

if __name__ == '__main__':
    asyncio.run(test_integrated_manipulation())