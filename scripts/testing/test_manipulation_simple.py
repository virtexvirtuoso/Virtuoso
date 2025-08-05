#!/usr/bin/env python3
"""Simple test of manipulation detection with live Bybit data"""

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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ManipulationTest')


async def test_manipulation_detection():
    """Test manipulation detection with real Bybit data"""
    
    # Initialize exchange
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'linear'
        }
    })
    
    try:
        # Load markets
        await exchange.load_markets()
        symbol = 'BTC/USDT'
        
        logger.info(f"Testing manipulation detection on {symbol}")
        
        # Configuration for detector
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {
                    'max_snapshots': 100,
                    'snapshot_interval_ms': 100,
                    'trade_history_size': 50
                },
                'spoofing': {
                    'enabled': True,
                    'volatility_threshold': 2.0,
                    'min_order_size_usd': 50000,
                    'execution_ratio_threshold': 0.1
                },
                'layering': {
                    'enabled': True,
                    'price_gap_threshold': 0.001,
                    'size_uniformity_threshold': 0.1,
                    'min_layers': 3
                },
                'alerts': {
                    'severity_levels': {
                        'low': 0.5,
                        'medium': 0.7,
                        'high': 0.85,
                        'critical': 0.95
                    }
                }
            }
        }
        
        # Create detector
        detector = ManipulationDetector(config, logger)
        
        # Collect data for 30 seconds
        logger.info("Collecting orderbook data for analysis...")
        
        previous_orderbook = None
        detection_count = 0
        
        for i in range(30):  # 30 iterations, 1 second each
            # Fetch orderbook and trades
            orderbook_data = await exchange.fetch_order_book(symbol, limit=25)
            trades_data = await exchange.fetch_trades(symbol, limit=50)
            
            # Format orderbook
            orderbook = {
                'bids': orderbook_data['bids'],
                'asks': orderbook_data['asks'],
                'timestamp': orderbook_data['timestamp']
            }
            
            # Format trades
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
            
            # Analyze for manipulation
            result = await detector.analyze_manipulation(orderbook, trades, previous_orderbook)
            
            # Display results
            print(f"\n--- Analysis #{i+1} at {datetime.now().strftime('%H:%M:%S')} ---")
            print(f"Overall Likelihood: {result['overall_likelihood']:.1%}")
            print(f"Manipulation Type: {result['manipulation_type']}")
            print(f"Severity: {result['severity']}")
            
            # Detailed results if manipulation detected
            if result['overall_likelihood'] > 0.5:
                detection_count += 1
                print("\n🚨 MANIPULATION DETECTED!")
                
                # Spoofing details
                if result['spoofing']['likelihood'] > 0.5:
                    print(f"\nSpoofing Analysis:")
                    print(f"  Likelihood: {result['spoofing']['likelihood']:.1%}")
                    print(f"  Volatility Ratio: {result['spoofing'].get('volatility_ratio', 0):.2f}")
                    print(f"  Execution Ratio: {result['spoofing'].get('execution_ratio', 0):.1%}")
                    print(f"  Reversals: {result['spoofing'].get('reversals', 0)}")
                
                # Layering details
                if result['layering']['likelihood'] > 0.5:
                    print(f"\nLayering Analysis:")
                    print(f"  Likelihood: {result['layering']['likelihood']:.1%}")
                    bid_side = result['layering'].get('bid_side', {})
                    ask_side = result['layering'].get('ask_side', {})
                    print(f"  Bid Side: {bid_side.get('likelihood', 0):.1%} (Layers: {bid_side.get('layers_analyzed', 0)})")
                    print(f"  Ask Side: {ask_side.get('likelihood', 0):.1%} (Layers: {ask_side.get('layers_analyzed', 0)})")
            
            # Update previous orderbook
            previous_orderbook = orderbook
            
            # Wait before next iteration
            await asyncio.sleep(1)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"SUMMARY: Detected manipulation in {detection_count}/30 snapshots ({detection_count/30*100:.1f}%)")
        
        # Get detector statistics
        stats = detector.get_statistics()
        print(f"\nDetector Statistics:")
        print(f"  Total Detections: {stats['detection_count']}")
        print(f"  History Size: {stats['history_size']}")
        print(f"  Trade History Size: {stats['trade_history_size']}")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()


if __name__ == '__main__':
    print("Starting Bybit manipulation detection test...")
    asyncio.run(test_manipulation_detection())