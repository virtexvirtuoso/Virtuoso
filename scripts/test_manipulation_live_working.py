#!/usr/bin/env python3
"""Working test of manipulation detection with live Bybit data"""

import ccxt
import sys
import os
from datetime import datetime
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.manipulation_detector import ManipulationDetector
import logging

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('LiveTest')


def test_manipulation_detection():
    """Test manipulation detection with real Bybit data"""
    
    print("Initializing Bybit exchange...")
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'},
        'timeout': 10000
    })
    
    try:
        exchange.load_markets()
        symbol = 'BTC/USDT'
        
        print(f"Testing manipulation detection on {symbol}")
        
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
                }
            }
        }
        
        # Create detector
        detector = ManipulationDetector(config, logger)
        
        print("\nCollecting data and analyzing...")
        print("=" * 60)
        
        previous_orderbook = None
        detections = []
        
        # Run for 10 iterations
        for i in range(10):
            try:
                # Fetch orderbook and trades
                orderbook_data = exchange.fetch_order_book(symbol, limit=25)
                trades_data = exchange.fetch_trades(symbol, limit=50)
                
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
                
                # Create async wrapper for the detector
                import asyncio
                
                async def analyze():
                    return await detector.analyze_manipulation(orderbook, trades, previous_orderbook)
                
                # Run the async function
                result = asyncio.run(analyze())
                
                # Display results
                timestamp = datetime.now().strftime('%H:%M:%S')
                likelihood = result['overall_likelihood']
                
                print(f"\n[{timestamp}] Snapshot #{i+1}")
                print(f"Price: ${orderbook_data['bids'][0][0]:,.2f} / ${orderbook_data['asks'][0][0]:,.2f}")
                print(f"Spread: ${orderbook_data['asks'][0][0] - orderbook_data['bids'][0][0]:.2f}")
                print(f"Overall Likelihood: {likelihood:.1%} [{result['severity']}]")
                
                # Show component scores
                if result['spoofing']['likelihood'] > 0:
                    print(f"  - Spoofing: {result['spoofing']['likelihood']:.1%}")
                if result['layering']['likelihood'] > 0:
                    print(f"  - Layering: {result['layering']['likelihood']:.1%}")
                
                # Detailed info if manipulation detected
                if likelihood > 0.5:
                    detections.append(result)
                    print("  🚨 MANIPULATION DETECTED!")
                    print(f"  Type: {result['manipulation_type']}")
                    
                    # Show spoofing details if detected
                    if result['spoofing']['detected']:
                        spoofing = result['spoofing']
                        print(f"  Spoofing Details:")
                        print(f"    - Volatility Ratio: {spoofing.get('volatility_ratio', 0):.2f}")
                        print(f"    - Execution Ratio: {spoofing.get('execution_ratio', 0):.1%}")
                        print(f"    - Reversals: {spoofing.get('reversals', 0)}")
                    
                    # Show layering details if detected
                    if result['layering']['detected']:
                        layering = result['layering']
                        print(f"  Layering Details:")
                        bid_side = layering.get('bid_side', {})
                        ask_side = layering.get('ask_side', {})
                        if bid_side.get('likelihood', 0) > 0.5:
                            print(f"    - Bid Side: {bid_side.get('likelihood', 0):.1%} ({bid_side.get('layers_analyzed', 0)} layers)")
                        if ask_side.get('likelihood', 0) > 0.5:
                            print(f"    - Ask Side: {ask_side.get('likelihood', 0):.1%} ({ask_side.get('layers_analyzed', 0)} layers)")
                
                # Update previous orderbook
                previous_orderbook = orderbook
                
                # Rate limit
                time.sleep(2)
                
            except Exception as e:
                print(f"\nError in iteration {i+1}: {str(e)}")
                continue
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total snapshots analyzed: 10")
        print(f"Manipulations detected: {len(detections)}")
        
        if detections:
            print("\nDetection breakdown:")
            types = {}
            for d in detections:
                mtype = d['manipulation_type']
                types[mtype] = types.get(mtype, 0) + 1
            
            for mtype, count in types.items():
                print(f"  - {mtype}: {count}")
            
            avg_likelihood = np.mean([d['overall_likelihood'] for d in detections])
            print(f"\nAverage manipulation likelihood: {avg_likelihood:.1%}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_manipulation_detection()