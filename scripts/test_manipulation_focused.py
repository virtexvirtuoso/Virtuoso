#!/usr/bin/env python3
"""Focused Manipulation Detection Test - Quick Analysis"""

import ccxt
import sys
import os
from datetime import datetime
import time
import numpy as np
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.enhanced_manipulation_detector import EnhancedManipulationDetector
from src.indicators.cached_manipulation_detector import CachedManipulationDetector
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('FocusedTest')

def main():
    """Run focused manipulation test"""
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    exchange.load_markets()
    
    # Configuration
    config = {
        'manipulation_detection': {
            'enabled': True,
            'history': {'max_snapshots': 50},
            'spoofing': {'enabled': True, 'min_order_size_usd': 10000},
            'layering': {'enabled': True},
            'wash_trading': {'enabled': True},
            'fake_liquidity': {'enabled': True},
            'iceberg': {'enabled': True},
            'trade_correlation': {'enabled': True}
        }
    }
    
    detector = EnhancedManipulationDetector(config, logger)
    cached_detector = CachedManipulationDetector(config, logger)
    
    # Test symbols
    symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']
    results = defaultdict(list)
    
    print(f"🔍 FOCUSED MANIPULATION ANALYSIS")
    print(f"Testing {len(symbols)} symbols with 10 snapshots each\n")
    
    for symbol in symbols:
        print(f"\n📊 Analyzing {symbol}:")
        previous_orderbook = None
        
        for i in range(10):
            try:
                # Fetch data
                orderbook = exchange.fetch_order_book(symbol, limit=50)
                trades = exchange.fetch_trades(symbol, limit=100)
                
                # Format
                formatted_orderbook = {
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks'],
                    'timestamp': orderbook['timestamp']
                }
                
                formatted_trades = [{
                    'id': trade['id'],
                    'price': trade['price'],
                    'size': trade['amount'],
                    'side': trade['side'],
                    'timestamp': trade['timestamp']
                } for trade in trades]
                
                # Analyze
                start = time.time()
                result = detector.analyze_manipulation(
                    formatted_orderbook, formatted_trades, previous_orderbook
                )
                elapsed = (time.time() - start) * 1000
                
                results[symbol].append(result)
                
                # Display significant results
                if i >= 2 and result['overall_likelihood'] > 0.3:  # Skip first 2 for warmup
                    print(f"  [{i+1:2}/10] {result['overall_likelihood']:.1%} - "
                          f"{result['manipulation_type']} (conf: {result['confidence']:.1%}, "
                          f"time: {elapsed:.1f}ms)")
                    
                    # Show detection breakdown
                    detections = []
                    if result['spoofing']['likelihood'] > 0.4:
                        detections.append(f"Spoof:{result['spoofing']['likelihood']:.0%}")
                    if result['layering']['likelihood'] > 0.4:
                        detections.append(f"Layer:{result['layering']['likelihood']:.0%}")
                    if result.get('wash_trading', {}).get('likelihood', 0) > 0.4:
                        detections.append(f"Wash:{result['wash_trading']['likelihood']:.0%}")
                    if result.get('fake_liquidity', {}).get('likelihood', 0) > 0.4:
                        detections.append(f"Fake:{result['fake_liquidity']['likelihood']:.0%}")
                    if result.get('iceberg_orders', {}).get('likelihood', 0) > 0.4:
                        detections.append(f"Ice:{result['iceberg_orders']['likelihood']:.0%}")
                    
                    if detections:
                        print(f"         {' | '.join(detections)}")
                
                previous_orderbook = formatted_orderbook
                time.sleep(1)  # 1 second between snapshots
                
            except Exception as e:
                print(f"  Error in snapshot {i+1}: {str(e)}")
    
    # Summary Analysis
    print(f"\n{'='*60}")
    print(f"SUMMARY ANALYSIS")
    print(f"{'='*60}")
    
    for symbol, symbol_results in results.items():
        if not symbol_results:
            continue
            
        # Skip first 2 results for warmup
        analysis_results = symbol_results[2:] if len(symbol_results) > 2 else symbol_results
        
        if not analysis_results:
            continue
            
        likelihoods = [r['overall_likelihood'] for r in analysis_results]
        avg_likelihood = np.mean(likelihoods)
        max_likelihood = max(likelihoods)
        
        detections = sum(1 for l in likelihoods if l > 0.5)
        
        print(f"\n{symbol}:")
        print(f"  Snapshots analyzed: {len(analysis_results)}")
        print(f"  Average likelihood: {avg_likelihood:.1%}")
        print(f"  Maximum likelihood: {max_likelihood:.1%}")
        print(f"  High detections (>50%): {detections}/{len(analysis_results)}")
        
        # Pattern breakdown
        manipulation_types = [r['manipulation_type'] for r in analysis_results if r['overall_likelihood'] > 0.5]
        if manipulation_types:
            type_counts = defaultdict(int)
            for mtype in manipulation_types:
                type_counts[mtype] += 1
            
            print(f"  Detected patterns:")
            for mtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"    • {mtype}: {count} times ({count/len(manipulation_types)*100:.0f}%)")
        
        # Advanced metrics from last result
        if analysis_results:
            last_result = analysis_results[-1]
            if 'advanced_metrics' in last_result:
                metrics = last_result['advanced_metrics']
                print(f"  Advanced metrics:")
                print(f"    • Tracked orders: {metrics.get('tracked_orders', 0)}")
                print(f"    • Phantom orders: {metrics.get('phantom_orders', 0)}")
                print(f"    • Iceberg candidates: {metrics.get('iceberg_candidates', 0)}")
                print(f"    • Correlation accuracy: {metrics.get('correlation_accuracy', 0):.1%}")
    
    # Enhanced detector final stats
    enhanced_stats = detector.get_enhanced_statistics()
    print(f"\nENHANCED DETECTOR FINAL STATISTICS:")
    print(f"  Order Tracking:")
    print(f"    • Active orders: {enhanced_stats['order_tracking']['active_orders']}")
    print(f"    • Completed orders: {enhanced_stats['order_tracking']['completed_orders']}")
    print(f"    • Phantom orders: {enhanced_stats['order_tracking']['phantom_orders']}")
    print(f"    • Avg order lifetime: {enhanced_stats['order_tracking']['avg_order_lifetime']:.0f}ms")
    
    print(f"  Trade Patterns:")
    print(f"    • Trade clusters: {enhanced_stats['trade_patterns']['trade_clusters']}")
    print(f"    • Avg velocity: {enhanced_stats['trade_patterns']['avg_trade_velocity']:.2f} trades/sec")
    print(f"    • Wash pairs: {enhanced_stats['trade_patterns']['wash_pairs_detected']}")
    
    print(f"  Performance:")
    print(f"    • Correlation accuracy: {enhanced_stats['performance']['correlation_accuracy']:.1%}")
    print(f"    • Total detections: {enhanced_stats['detection_count']}")
    
    # Cache performance test
    print(f"\nCACHE PERFORMANCE TEST:")
    test_symbol = 'BTC/USDT'
    orderbook = exchange.fetch_order_book(test_symbol, limit=25)
    trades = exchange.fetch_trades(test_symbol, limit=50)
    
    formatted_orderbook = {
        'bids': orderbook['bids'],
        'asks': orderbook['asks'],
        'timestamp': orderbook['timestamp']
    }
    
    formatted_trades = [{
        'id': trade['id'],
        'price': trade['price'],
        'size': trade['amount'],
        'side': trade['side'],
        'timestamp': trade['timestamp']
    } for trade in trades]
    
    # Run same analysis 5 times to test cache
    cache_times = []
    for i in range(5):
        start = time.time()
        result = cached_detector.analyze_manipulation(formatted_orderbook, formatted_trades)
        elapsed = (time.time() - start) * 1000
        cache_times.append(elapsed)
        cached = result.get('cached', False)
        print(f"  Analysis {i+1}: {elapsed:.1f}ms {'(CACHED)' if cached else '(COMPUTED)'}")
    
    cache_stats = cached_detector.get_performance_stats()
    print(f"  Cache hit rate: {cache_stats['cache_hit_rate']:.1%}")
    print(f"  Average time: {np.mean(cache_times):.1f}ms")
    
    print(f"\n✅ COMPREHENSIVE TEST COMPLETED")

if __name__ == '__main__':
    main()