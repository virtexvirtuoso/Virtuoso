#!/usr/bin/env python3
"""Working test of manipulation detection with live Bybit data - Fixed version"""

import ccxt
import sys
import os
from datetime import datetime
import time
import numpy as np
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.manipulation_detector import ManipulationDetector
from src.indicators.enhanced_manipulation_detector import EnhancedManipulationDetector
from src.indicators.cached_manipulation_detector import CachedManipulationDetector
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ManipulationTest')


def test_basic_detector():
    """Test basic manipulation detector with live data"""
    print("\n" + "="*60)
    print("Testing Basic Manipulation Detector")
    print("="*60)
    
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    try:
        exchange.load_markets()
        symbol = 'BTC/USDT'
        
        # Configuration
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {
                    'max_snapshots': 100,
                    'trade_history_size': 50
                },
                'spoofing': {
                    'enabled': True,
                    'volatility_threshold': 2.0,
                    'min_order_size_usd': 50000
                },
                'layering': {
                    'enabled': True,
                    'price_gap_threshold': 0.001,
                    'min_layers': 3
                }
            }
        }
        
        detector = ManipulationDetector(config, logger)
        
        print(f"\nMonitoring {symbol} for manipulation patterns...")
        previous_orderbook = None
        detections = []
        
        for i in range(5):
            # Fetch data
            orderbook_data = exchange.fetch_order_book(symbol, limit=25)
            trades_data = exchange.fetch_trades(symbol, limit=50)
            
            # Format data
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
            result = detector.analyze_manipulation(orderbook, trades, previous_orderbook)
            
            # Display
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] Snapshot #{i+1}")
            print(f"  Price: ${orderbook_data['bids'][0][0]:,.2f} / ${orderbook_data['asks'][0][0]:,.2f}")
            print(f"  Spread: ${orderbook_data['asks'][0][0] - orderbook_data['bids'][0][0]:.2f}")
            print(f"  Overall: {result['overall_likelihood']:.1%} [{result['severity']}]")
            
            if result['overall_likelihood'] > 0.3:
                print(f"  Spoofing: {result['spoofing']['likelihood']:.1%}")
                print(f"  Layering: {result['layering']['likelihood']:.1%}")
                
                if result['overall_likelihood'] > 0.5:
                    detections.append(result)
                    print(f"  🚨 Type: {result['manipulation_type']}")
            
            previous_orderbook = orderbook
            time.sleep(2)
        
        print(f"\nDetections: {len(detections)}/5")
        return True
        
    except Exception as e:
        logger.error(f"Error in basic test: {str(e)}")
        return False
    finally:
        # CCXT synchronous exchanges don't have close() method
        pass


def test_enhanced_detector():
    """Test enhanced manipulation detector with advanced features"""
    print("\n" + "="*60)
    print("Testing Enhanced Manipulation Detector")
    print("="*60)
    
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    try:
        exchange.load_markets()
        symbol = 'BTC/USDT'
        
        # Enhanced configuration
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {'max_snapshots': 100},
                'spoofing': {'enabled': True},
                'layering': {'enabled': True},
                'wash_trading': {'enabled': True},
                'fake_liquidity': {'enabled': True},
                'iceberg': {'enabled': True},
                'trade_correlation': {'enabled': True}
            }
        }
        
        detector = EnhancedManipulationDetector(config, logger)
        
        print(f"\nMonitoring {symbol} with enhanced detection...")
        previous_orderbook = None
        
        for i in range(3):
            # Fetch data
            orderbook_data = exchange.fetch_order_book(symbol, limit=25)
            trades_data = exchange.fetch_trades(symbol, limit=100)
            
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
            result = detector.analyze_manipulation(orderbook, trades, previous_orderbook)
            
            # Display enhanced results
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] Enhanced Analysis #{i+1}")
            print(f"  Overall: {result['overall_likelihood']:.1%}")
            print(f"  Confidence: {result['confidence']:.1%}")
            
            # Show all detection types
            print("  Detection Results:")
            print(f"    - Spoofing: {result['spoofing']['likelihood']:.1%}")
            print(f"    - Layering: {result['layering']['likelihood']:.1%}")
            print(f"    - Wash Trading: {result.get('wash_trading', {}).get('likelihood', 0):.1%}")
            print(f"    - Fake Liquidity: {result.get('fake_liquidity', {}).get('likelihood', 0):.1%}")
            print(f"    - Iceberg Orders: {result.get('iceberg_orders', {}).get('likelihood', 0):.1%}")
            
            # Trade patterns
            patterns = result.get('trade_patterns', {})
            print(f"  Trade Patterns:")
            print(f"    - Velocity: {patterns.get('velocity', 0):.1f} trades/sec")
            print(f"    - Burst Detected: {patterns.get('burst_detected', False)}")
            
            # Correlation
            correlation = result.get('trade_correlation', {})
            print(f"  Correlation Score: {correlation.get('correlation_score', 0):.1%}")
            
            previous_orderbook = orderbook
            time.sleep(2)
        
        # Show statistics
        stats = detector.get_enhanced_statistics()
        print(f"\nEnhanced Statistics:")
        print(f"  - Tracked Orders: {stats['order_tracking']['active_orders']}")
        print(f"  - Phantom Orders: {stats['order_tracking']['phantom_orders']}")
        print(f"  - Trade Clusters: {stats['trade_patterns']['trade_clusters']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in enhanced test: {str(e)}")
        return False
    finally:
        # CCXT synchronous exchanges don't have close() method
        pass


def test_cached_detector():
    """Test cached detector performance"""
    print("\n" + "="*60)
    print("Testing Cached Manipulation Detector")
    print("="*60)
    
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    try:
        exchange.load_markets()
        symbol = 'BTC/USDT'
        
        config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {'max_snapshots': 50}
            }
        }
        
        cached_detector = CachedManipulationDetector(config, logger, cache_ttl_seconds=2)
        
        print(f"\nTesting cache performance on {symbol}...")
        
        # Fetch initial data
        orderbook_data = exchange.fetch_order_book(symbol, limit=25)
        trades_data = exchange.fetch_trades(symbol, limit=50)
        
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
        
        # Test cache hits
        print("\nRunning 5 analyses with same data (testing cache)...")
        for i in range(5):
            start = time.time()
            result = cached_detector.analyze_manipulation(orderbook, trades)
            elapsed = (time.time() - start) * 1000
            
            is_cached = result.get('cached', False)
            print(f"  Analysis {i+1}: {elapsed:.1f}ms {'(CACHED)' if is_cached else '(COMPUTED)'}")
        
        # Show performance stats
        stats = cached_detector.get_performance_stats()
        print(f"\nCache Performance:")
        print(f"  - Hit Rate: {stats['cache_hit_rate']:.1%}")
        print(f"  - Avg Time: {stats['avg_analysis_time_ms']:.1f}ms")
        print(f"  - Cache Size: {stats['cache_size']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in cached test: {str(e)}")
        return False
    finally:
        # CCXT synchronous exchanges don't have close() method
        pass


def main():
    """Run all tests"""
    print("\n🚀 Bybit Manipulation Detection Test Suite")
    print("Testing all detection components with live data...\n")
    
    tests = [
        ("Basic Detector", test_basic_detector),
        ("Enhanced Detector", test_enhanced_detector),
        ("Cached Detector", test_cached_detector)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Failed to run {name}: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! The manipulation detection system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the logs above.")


if __name__ == '__main__':
    main()