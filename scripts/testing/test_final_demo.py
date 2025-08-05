#!/usr/bin/env python3
"""Final demo of manipulation detection with Bybit data"""

import ccxt
import sys
import os
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Bybit Manipulation Detection Demo ===\n")

# Initialize exchange
exchange = ccxt.bybit({
    'enableRateLimit': True,
    'options': {'defaultType': 'linear'},
    'timeout': 10000
})

try:
    exchange.load_markets()
    symbol = 'BTC/USDT'
    
    # Fetch multiple snapshots
    print(f"Monitoring {symbol} for manipulation patterns...\n")
    
    snapshots = []
    for i in range(5):
        print(f"Snapshot {i+1}/5:", end=' ')
        
        # Fetch data
        ob = exchange.fetch_order_book(symbol, 25)
        trades = exchange.fetch_trades(symbol, 50)
        
        # Basic analysis
        spread = ob['asks'][0][0] - ob['bids'][0][0]
        mid_price = (ob['asks'][0][0] + ob['bids'][0][0]) / 2
        
        # Volume imbalance
        bid_volume = sum(b[1] for b in ob['bids'][:10])
        ask_volume = sum(a[1] for a in ob['asks'][:10])
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
        # Check for layering
        bid_sizes = [b[1] for b in ob['bids'][:5]]
        size_std = np.std(bid_sizes) / np.mean(bid_sizes)
        
        # Trade velocity
        recent_trades = [t for t in trades if t['timestamp'] > trades[0]['timestamp'] - 5000]
        trade_rate = len(recent_trades) / 5.0  # trades per second
        
        snapshot = {
            'time': datetime.now(),
            'mid_price': mid_price,
            'spread': spread,
            'imbalance': imbalance,
            'size_uniformity': size_std,
            'trade_rate': trade_rate,
            'bid_sizes': bid_sizes
        }
        snapshots.append(snapshot)
        
        print(f"Price: ${mid_price:,.2f} | Spread: ${spread:.2f} | Imbalance: {imbalance:+.2%}")
        
        # Simple detection logic
        manipulation_score = 0
        reasons = []
        
        # Check for tight spread with high imbalance
        if spread < 1 and abs(imbalance) > 0.3:
            manipulation_score += 0.3
            reasons.append("tight spread with high imbalance")
        
        # Check for uniform sizes (potential layering)
        if size_std < 0.2:
            manipulation_score += 0.4
            reasons.append(f"uniform order sizes (std: {size_std:.2f})")
        
        # Check for high trade rate
        if trade_rate > 10:
            manipulation_score += 0.3
            reasons.append(f"high trade velocity ({trade_rate:.1f}/s)")
        
        if manipulation_score > 0.5:
            print(f"  ⚠️  POTENTIAL MANIPULATION (score: {manipulation_score:.0%})")
            for reason in reasons:
                print(f"     - {reason}")
        
        import time
        if i < 4:
            time.sleep(2)
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"Snapshots analyzed: {len(snapshots)}")
    
    avg_spread = np.mean([s['spread'] for s in snapshots])
    avg_imbalance = np.mean([abs(s['imbalance']) for s in snapshots])
    avg_trade_rate = np.mean([s['trade_rate'] for s in snapshots])
    
    print(f"Average spread: ${avg_spread:.2f}")
    print(f"Average imbalance: {avg_imbalance:.1%}")
    print(f"Average trade rate: {avg_trade_rate:.1f} trades/second")
    
    print("\n✅ Live data test completed successfully!")
    print("\nNOTE: The full manipulation detection system includes:")
    print("- Order lifecycle tracking")
    print("- Trade correlation analysis")
    print("- Wash trading detection")
    print("- Fake liquidity identification")
    print("- Iceberg order detection")
    print("- ML-based anomaly detection")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()