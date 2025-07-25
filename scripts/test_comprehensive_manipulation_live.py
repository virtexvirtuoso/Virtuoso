#!/usr/bin/env python3
"""Comprehensive Manipulation Detection Test with Live Bybit Data

This script performs extensive testing across multiple symbols and timeframes,
generating detailed reports and statistics.
"""

import ccxt
import sys
import os
from datetime import datetime, timedelta
import time
import numpy as np
import json
from collections import defaultdict
import pandas as pd
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.manipulation_detector import ManipulationDetector
from src.indicators.enhanced_manipulation_detector import EnhancedManipulationDetector
from src.indicators.cached_manipulation_detector import CachedManipulationDetector, ManipulationDetectorPool
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ComprehensiveManipulationTest')


class ComprehensiveManipulationTester:
    """Comprehensive testing suite for manipulation detection"""
    
    def __init__(self, exchange: ccxt.Exchange):
        self.exchange = exchange
        self.results = defaultdict(list)
        self.detection_stats = defaultdict(int)
        self.performance_metrics = []
        
        # Configuration
        self.config = {
            'manipulation_detection': {
                'enabled': True,
                'history': {
                    'max_snapshots': 100,
                    'trade_history_size': 100
                },
                'spoofing': {
                    'enabled': True,
                    'volatility_threshold': 2.0,
                    'min_order_size_usd': 10000
                },
                'layering': {
                    'enabled': True,
                    'price_gap_threshold': 0.001,
                    'min_layers': 3
                },
                'wash_trading': {
                    'enabled': True,
                    'time_window_ms': 1000,
                    'price_tolerance': 0.0001
                },
                'fake_liquidity': {
                    'enabled': True,
                    'withdrawal_threshold': 0.3
                },
                'iceberg': {
                    'enabled': True,
                    'refill_threshold': 0.8
                },
                'trade_correlation': {
                    'enabled': True,
                    'window_ms': 5000
                }
            }
        }
        
        # Initialize detectors
        self.basic_detector = ManipulationDetector(self.config, logger)
        self.enhanced_detector = EnhancedManipulationDetector(self.config, logger)
        self.cached_detector = CachedManipulationDetector(self.config, logger, cache_ttl_seconds=5)
        self.detector_pool = ManipulationDetectorPool(self.config, logger, pool_size=3)
    
    def test_multiple_symbols(self, symbols: List[str], duration_minutes: int = 5):
        """Test multiple symbols for specified duration"""
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE MULTI-SYMBOL TEST")
        print(f"Testing {len(symbols)} symbols for {duration_minutes} minutes")
        print(f"{'='*80}\n")
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Previous orderbooks for delta calculation
        previous_orderbooks = {}
        
        snapshot_count = 0
        
        while datetime.utcnow() < end_time:
            snapshot_count += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Snapshot #{snapshot_count}")
            
            for symbol in symbols:
                try:
                    # Fetch market data
                    orderbook = self.exchange.fetch_order_book(symbol, limit=50)
                    trades = self.exchange.fetch_trades(symbol, limit=100)
                    
                    # Format data
                    formatted_orderbook = {
                        'bids': orderbook['bids'],
                        'asks': orderbook['asks'],
                        'timestamp': orderbook['timestamp']
                    }
                    
                    formatted_trades = [
                        {
                            'id': trade['id'],
                            'price': trade['price'],
                            'size': trade['amount'],
                            'side': trade['side'],
                            'timestamp': trade['timestamp']
                        }
                        for trade in trades
                    ]
                    
                    # Get previous orderbook
                    previous = previous_orderbooks.get(symbol)
                    
                    # Run enhanced detection
                    result = self.enhanced_detector.analyze_manipulation(
                        formatted_orderbook, 
                        formatted_trades,
                        previous
                    )
                    
                    # Store result
                    self.results[symbol].append({
                        'timestamp': datetime.utcnow(),
                        'result': result,
                        'price': orderbook['bids'][0][0] if orderbook['bids'] else 0,
                        'spread': (orderbook['asks'][0][0] - orderbook['bids'][0][0]) if orderbook['bids'] and orderbook['asks'] else 0
                    })
                    
                    # Update previous orderbook
                    previous_orderbooks[symbol] = formatted_orderbook
                    
                    # Update statistics
                    if result['overall_likelihood'] > 0.5:
                        self.detection_stats[symbol] += 1
                        
                    # Display results
                    if result['overall_likelihood'] > 0.3:
                        print(f"  {symbol}: {result['overall_likelihood']:.1%} [{result['severity']}]")
                        if result['overall_likelihood'] > 0.7:
                            print(f"    🚨 Type: {result['manipulation_type']}")
                            print(f"    💡 Confidence: {result['confidence']:.1%}")
                            
                            # Show specific detections
                            detections = []
                            if result['spoofing']['likelihood'] > 0.5:
                                detections.append(f"Spoofing: {result['spoofing']['likelihood']:.1%}")
                            if result['layering']['likelihood'] > 0.5:
                                detections.append(f"Layering: {result['layering']['likelihood']:.1%}")
                            if result.get('wash_trading', {}).get('likelihood', 0) > 0.5:
                                detections.append(f"Wash Trading: {result['wash_trading']['likelihood']:.1%}")
                            if result.get('fake_liquidity', {}).get('likelihood', 0) > 0.5:
                                detections.append(f"Fake Liquidity: {result['fake_liquidity']['likelihood']:.1%}")
                            if result.get('iceberg_orders', {}).get('likelihood', 0) > 0.5:
                                detections.append(f"Iceberg: {result['iceberg_orders']['likelihood']:.1%}")
                            
                            if detections:
                                print(f"    📊 Detections: {', '.join(detections)}")
                    
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
            
            # Sleep between snapshots
            time.sleep(10)  # 10 seconds between snapshots
        
        print(f"\n{'='*60}")
        print(f"TEST COMPLETED")
        print(f"Total snapshots: {snapshot_count}")
        print(f"Duration: {(datetime.utcnow() - start_time).seconds} seconds")
    
    def test_high_frequency_monitoring(self, symbol: str, num_snapshots: int = 50):
        """High-frequency monitoring of a single symbol"""
        print(f"\n{'='*80}")
        print(f"HIGH-FREQUENCY MONITORING: {symbol}")
        print(f"Taking {num_snapshots} rapid snapshots")
        print(f"{'='*80}\n")
        
        previous_orderbook = None
        high_freq_results = []
        
        for i in range(num_snapshots):
            try:
                start = time.time()
                
                # Fetch data
                orderbook = self.exchange.fetch_order_book(symbol, limit=50)
                trades = self.exchange.fetch_trades(symbol, limit=50)
                
                # Format
                formatted_orderbook = {
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks'],
                    'timestamp': orderbook['timestamp']
                }
                
                formatted_trades = [
                    {
                        'id': trade['id'],
                        'price': trade['price'],
                        'size': trade['amount'],
                        'side': trade['side'],
                        'timestamp': trade['timestamp']
                    }
                    for trade in trades
                ]
                
                # Analyze with cached detector for performance
                result = self.cached_detector.analyze_manipulation(
                    formatted_orderbook,
                    formatted_trades,
                    previous_orderbook
                )
                
                elapsed = (time.time() - start) * 1000
                
                high_freq_results.append({
                    'snapshot': i + 1,
                    'likelihood': result['overall_likelihood'],
                    'type': result['manipulation_type'],
                    'analysis_time_ms': elapsed,
                    'cached': result.get('cached', False)
                })
                
                # Show progress
                if (i + 1) % 10 == 0:
                    avg_likelihood = np.mean([r['likelihood'] for r in high_freq_results[-10:]])
                    avg_time = np.mean([r['analysis_time_ms'] for r in high_freq_results[-10:]])
                    cache_hits = sum(1 for r in high_freq_results[-10:] if r.get('cached', False))
                    
                    print(f"[{i+1}/{num_snapshots}] Avg likelihood: {avg_likelihood:.1%}, "
                          f"Avg time: {avg_time:.1f}ms, Cache hits: {cache_hits}/10")
                
                previous_orderbook = formatted_orderbook
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in high-frequency test: {str(e)}")
        
        # Summary statistics
        print(f"\nHigh-Frequency Results Summary:")
        print(f"  Total detections (>50%): {sum(1 for r in high_freq_results if r['likelihood'] > 0.5)}")
        print(f"  Average likelihood: {np.mean([r['likelihood'] for r in high_freq_results]):.1%}")
        print(f"  Max likelihood: {max(r['likelihood'] for r in high_freq_results):.1%}")
        print(f"  Average analysis time: {np.mean([r['analysis_time_ms'] for r in high_freq_results]):.1f}ms")
        
        # Cache performance
        cache_stats = self.cached_detector.get_performance_stats()
        print(f"\nCache Performance:")
        print(f"  Hit rate: {cache_stats['cache_hit_rate']:.1%}")
        print(f"  Total analyses: {cache_stats['total_analyses']}")
        print(f"  Avg time: {cache_stats['avg_analysis_time_ms']:.1f}ms")
    
    def test_detector_pool_performance(self, symbols: List[str]):
        """Test detector pool with multiple symbols"""
        print(f"\n{'='*80}")
        print(f"DETECTOR POOL PERFORMANCE TEST")
        print(f"Testing {len(symbols)} symbols in parallel")
        print(f"{'='*80}\n")
        
        # Fetch data for all symbols
        market_data = []
        for symbol in symbols:
            try:
                orderbook = self.exchange.fetch_order_book(symbol, limit=50)
                trades = self.exchange.fetch_trades(symbol, limit=50)
                
                market_data.append((
                    symbol,
                    {
                        'bids': orderbook['bids'],
                        'asks': orderbook['asks'],
                        'timestamp': orderbook['timestamp']
                    },
                    [
                        {
                            'id': trade['id'],
                            'price': trade['price'],
                            'size': trade['amount'],
                            'side': trade['side'],
                            'timestamp': trade['timestamp']
                        }
                        for trade in trades
                    ]
                ))
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
        
        # Analyze with pool
        start = time.time()
        pool_results = self.detector_pool.batch_analyze(market_data)
        elapsed = (time.time() - start) * 1000
        
        print(f"Pool analysis completed in {elapsed:.1f}ms for {len(market_data)} symbols")
        print(f"Average per symbol: {elapsed/len(market_data):.1f}ms\n")
        
        # Display results
        for symbol, result in pool_results.items():
            if result['overall_likelihood'] > 0.3:
                print(f"{symbol}: {result['overall_likelihood']:.1%} - {result['manipulation_type']}")
        
        # Pool statistics
        pool_stats = self.detector_pool.get_pool_stats()
        print(f"\nPool Statistics:")
        print(f"  Pool size: {pool_stats['pool_size']}")
        print(f"  Symbols assigned: {pool_stats['symbol_count']}")
        
        for det_stats in pool_stats['detectors']:
            print(f"\n  Detector {det_stats['detector_id']}:")
            print(f"    Assigned symbols: {', '.join(det_stats['assigned_symbols'])}")
            print(f"    Cache hit rate: {det_stats['cache_hit_rate']:.1%}")
            print(f"    Total analyses: {det_stats['total_analyses']}")
    
    def generate_detailed_report(self):
        """Generate comprehensive report of all findings"""
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE MANIPULATION DETECTION REPORT")
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Overall statistics
        total_analyses = sum(len(results) for results in self.results.values())
        total_detections = sum(self.detection_stats.values())
        
        print(f"Overall Statistics:")
        print(f"  Total analyses performed: {total_analyses}")
        print(f"  Total detections (>50%): {total_detections}")
        print(f"  Detection rate: {total_detections/total_analyses*100:.1f}%\n")
        
        # Per-symbol analysis
        print(f"Per-Symbol Analysis:")
        for symbol, results in self.results.items():
            if not results:
                continue
                
            likelihoods = [r['result']['overall_likelihood'] for r in results]
            avg_likelihood = np.mean(likelihoods)
            max_likelihood = max(likelihoods)
            
            print(f"\n{symbol}:")
            print(f"  Snapshots analyzed: {len(results)}")
            print(f"  Average likelihood: {avg_likelihood:.1%}")
            print(f"  Max likelihood: {max_likelihood:.1%}")
            print(f"  Detections (>50%): {self.detection_stats.get(symbol, 0)}")
            
            # Manipulation type breakdown
            type_counts = defaultdict(int)
            for r in results:
                if r['result']['overall_likelihood'] > 0.5:
                    type_counts[r['result']['manipulation_type']] += 1
            
            if type_counts:
                print(f"  Manipulation types detected:")
                for mtype, count in type_counts.items():
                    print(f"    - {mtype}: {count} times")
            
            # Pattern analysis
            pattern_stats = self._analyze_patterns(results)
            if pattern_stats:
                print(f"  Pattern insights:")
                for key, value in pattern_stats.items():
                    print(f"    - {key}: {value}")
        
        # Enhanced detector statistics
        enhanced_stats = self.enhanced_detector.get_enhanced_statistics()
        print(f"\nEnhanced Detector Statistics:")
        print(f"  Order tracking:")
        print(f"    - Active orders: {enhanced_stats['order_tracking']['active_orders']}")
        print(f"    - Phantom orders: {enhanced_stats['order_tracking']['phantom_orders']}")
        print(f"    - Avg order lifetime: {enhanced_stats['order_tracking']['avg_order_lifetime']:.0f}ms")
        print(f"  Trade patterns:")
        print(f"    - Trade clusters: {enhanced_stats['trade_patterns']['trade_clusters']}")
        print(f"    - Avg trade velocity: {enhanced_stats['trade_patterns']['avg_trade_velocity']:.1f} trades/sec")
        print(f"  Performance:")
        print(f"    - Correlation accuracy: {enhanced_stats['performance']['correlation_accuracy']:.1%}")
    
    def _analyze_patterns(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in detection results"""
        patterns = {}
        
        # Time-based patterns
        if len(results) > 10:
            # Check for clustering of detections
            detection_times = [r['timestamp'] for r in results if r['result']['overall_likelihood'] > 0.5]
            if len(detection_times) > 2:
                time_diffs = [(detection_times[i+1] - detection_times[i]).seconds 
                              for i in range(len(detection_times)-1)]
                if time_diffs:
                    avg_interval = np.mean(time_diffs)
                    patterns['avg_detection_interval'] = f"{avg_interval:.0f} seconds"
        
        # Price correlation
        high_likelihood_prices = [r['price'] for r in results if r['result']['overall_likelihood'] > 0.5]
        if high_likelihood_prices:
            patterns['detection_price_range'] = f"${min(high_likelihood_prices):,.2f} - ${max(high_likelihood_prices):,.2f}"
        
        # Spread analysis
        high_likelihood_spreads = [r['spread'] for r in results if r['result']['overall_likelihood'] > 0.5]
        if high_likelihood_spreads:
            patterns['avg_spread_during_detection'] = f"${np.mean(high_likelihood_spreads):.2f}"
        
        return patterns


def main():
    """Run comprehensive manipulation detection tests"""
    # Initialize exchange
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    # Load markets
    exchange.load_markets()
    
    # Test configuration
    test_symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'SOL/USDT',
        'DOGE/USDT',
        'XRP/USDT'
    ]
    
    # Initialize tester
    tester = ComprehensiveManipulationTester(exchange)
    
    # Run tests
    try:
        # 1. Multi-symbol monitoring
        tester.test_multiple_symbols(test_symbols, duration_minutes=2)
        
        # 2. High-frequency monitoring
        tester.test_high_frequency_monitoring('BTC/USDT', num_snapshots=30)
        
        # 3. Detector pool performance
        tester.test_detector_pool_performance(test_symbols)
        
        # 4. Generate comprehensive report
        tester.generate_detailed_report()
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        tester.generate_detailed_report()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()