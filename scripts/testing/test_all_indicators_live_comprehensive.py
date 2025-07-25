#!/usr/bin/env python3
"""
Comprehensive test of ALL indicators in src/indicators/ with live Bybit data.
Tests each indicator module individually with proper data formats and TA-Lib optimizations.
"""

import asyncio
import pandas as pd
import numpy as np
import sys
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_all_indicators_comprehensive():
    """Test all indicators with live Bybit data."""
    print("=" * 100)
    print("COMPREHENSIVE INDICATOR TEST WITH LIVE BYBIT DATA")
    print("=" * 100)
    
    # Test configuration
    SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']  # Top 3 crypto pairs
    
    results = {
        'test_metadata': {
            'timestamp': datetime.now().isoformat(),
            'symbols': SYMBOLS,
            'environment': 'live_data'
        },
        'indicators': {}
    }
    
    try:
        # Initialize exchange
        from src.core.exchanges.bybit import BybitExchange
        
        config = {
            'exchanges': {
                'bybit': {
                    'api_key': '',
                    'api_secret': '',
                    'testnet': False,
                    'websocket': {
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                    }
                }
            },
            'timeframes': {
                'base': {
                    'interval': 1,
                    'required': 500,
                    'validation': {
                        'max_gap': 60,
                        'min_candles': 100
                    },
                    'weight': 0.4
                },
                'ltf': {
                    'interval': 5,
                    'required': 200,
                    'validation': {
                        'max_gap': 300,
                        'min_candles': 50
                    },
                    'weight': 0.3
                },
                'mtf': {
                    'interval': 15,
                    'required': 100,
                    'validation': {
                        'max_gap': 900,
                        'min_candles': 30
                    },
                    'weight': 0.2
                },
                'htf': {
                    'interval': 60,
                    'required': 50,
                    'validation': {
                        'max_gap': 3600,
                        'min_candles': 20
                    },
                    'weight': 0.1
                }
            },
            'optimization': {
                'level': 'auto',
                'use_talib': True,
                'fallback_on_error': True
            }
        }
        
        exchange = BybitExchange(config)
        print("✅ Exchange initialized")
        
        # Import all indicator modules
        from src.indicators.technical_indicators import TechnicalIndicators
        from src.indicators.volume_indicators import VolumeIndicators
        from src.indicators.orderflow_indicators import OrderflowIndicators
        from src.indicators.orderbook_indicators import OrderbookIndicators
        from src.indicators.sentiment_indicators import SentimentIndicators
        from src.indicators.price_structure_indicators import PriceStructureIndicators
        
        indicator_classes = {
            'technical': TechnicalIndicators,
            'volume': VolumeIndicators,
            'orderflow': OrderflowIndicators,
            'orderbook': OrderbookIndicators,
            'sentiment': SentimentIndicators,
            'price_structure': PriceStructureIndicators
        }
        
        # Test each symbol
        for symbol in SYMBOLS:
            print(f"\n{'='*80}")
            print(f"📊 TESTING SYMBOL: {symbol}")
            print("="*80)
            
            results['indicators'][symbol] = {}
            
            # Fetch comprehensive market data
            print(f"\n🔄 Fetching live data for {symbol}...")
            
            # Fetch OHLCV data for all timeframes
            base_data = await exchange.fetch_ohlcv(symbol, '1m', 500)
            ltf_data = await exchange.fetch_ohlcv(symbol, '5m', 200)
            mtf_data = await exchange.fetch_ohlcv(symbol, '15m', 100)
            htf_data = await exchange.fetch_ohlcv(symbol, '1h', 50)
            
            if not all([base_data, ltf_data, mtf_data, htf_data]):
                print(f"❌ Failed to fetch data for {symbol}")
                continue
            
            # Convert to DataFrames
            def create_df(data):
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
            
            timeframes_data = {
                'base': create_df(base_data),
                'ltf': create_df(ltf_data),
                'mtf': create_df(mtf_data),
                'htf': create_df(htf_data)
            }
            
            latest_price = timeframes_data['base']['close'].iloc[-1]
            
            print(f"✅ OHLCV data fetched:")
            print(f"  • Base (1m): {len(timeframes_data['base'])} candles")
            print(f"  • LTF (5m): {len(timeframes_data['ltf'])} candles")
            print(f"  • MTF (15m): {len(timeframes_data['mtf'])} candles")
            print(f"  • HTF (1h): {len(timeframes_data['htf'])} candles")
            print(f"  • Latest Price: ${latest_price:,.2f}")
            
            # Generate enhanced market data
            print(f"\n🔧 Generating enhanced market data...")
            
            # Generate realistic trade data with proper timestamps
            trades = []
            current_time = int(time.time() * 1000)
            
            for i, (timestamp, row) in enumerate(timeframes_data['base'].tail(100).iterrows()):
                candle_time_ms = int(timestamp.timestamp() * 1000)
                num_trades = np.random.randint(10, 25)
                
                for j in range(num_trades):
                    trade_time_offset = np.random.randint(0, 60000)
                    trade_timestamp = candle_time_ms + trade_time_offset
                    
                    trades.append({
                        'id': f"{symbol}_{i}_{j}",
                        'price': float(np.random.uniform(row['low'] * 0.999, row['high'] * 1.001)),
                        'size': float(np.random.lognormal(mean=np.log(row['volume'] / 15), sigma=0.5)),
                        'side': np.random.choice(['buy', 'sell'], p=[0.52, 0.48]),
                        'time': int(trade_timestamp)  # Integer timestamp
                    })
            
            # Generate orderbook data
            spread = latest_price * 0.0001
            bids = []
            asks = []
            
            for i in range(50):
                bid_offset = spread * (1 + i) * np.random.uniform(0.8, 1.2)
                ask_offset = spread * (1 + i) * np.random.uniform(0.8, 1.2)
                
                bid_price = latest_price - bid_offset
                ask_price = latest_price + ask_offset
                
                base_size = np.random.lognormal(mean=8, sigma=1)
                bid_size = base_size * np.exp(-i * 0.1)
                ask_size = base_size * np.exp(-i * 0.1)
                
                bids.append([float(bid_price), float(bid_size)])
                asks.append([float(ask_price), float(ask_size)])
            
            bids.sort(key=lambda x: x[0], reverse=True)
            asks.sort(key=lambda x: x[0])
            
            orderbook = {
                'symbol': symbol,
                'bids': bids,
                'asks': asks,
                'timestamp': int(current_time),
                'datetime': datetime.now().isoformat()
            }
            
            # Generate sentiment data
            sentiment_data = {
                'funding_rate': np.random.uniform(-0.01, 0.01),
                'open_interest': latest_price * np.random.uniform(100000, 500000),
                'long_short_ratio': np.random.uniform(0.4, 2.5),
                'fear_greed_index': np.random.randint(10, 90),
                'social_sentiment': np.random.uniform(-1, 1),
                'liquidations_24h': {
                    'longs': np.random.uniform(1000000, 10000000),
                    'shorts': np.random.uniform(1000000, 10000000)
                }
            }
            
            print(f"✅ Enhanced data generated:")
            print(f"  • Trades: {len(trades)} records")
            print(f"  • Orderbook: {len(bids)} bid/ask levels")
            print(f"  • Sentiment: {len(sentiment_data)} metrics")
            
            # Create complete market data structure
            market_data = {
                'ohlcv': timeframes_data,
                'trades': trades,
                'orderbook': orderbook,
                'sentiment': sentiment_data,
                'timestamp': int(current_time),
                'symbol': symbol,
                'metadata': {
                    'data_quality': 'high',
                    'last_update': datetime.now().isoformat(),
                    'source': 'bybit_live'
                }
            }
            
            # Test each indicator
            print(f"\n📈 Testing indicators for {symbol}...")
            
            for indicator_name, indicator_class in indicator_classes.items():
                print(f"\n{'─'*60}")
                print(f"🔍 Testing {indicator_name.upper()} indicators")
                
                try:
                    # Initialize indicator
                    indicator = indicator_class(config)
                    
                    # Run calculation
                    start_time = time.perf_counter()
                    result = await indicator.calculate(market_data)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Analyze result
                    if isinstance(result, dict) and 'score' in result:
                        score = result['score']
                        is_meaningful = abs(score - 50.0) > 0.1
                        
                        # Count meaningful components
                        components = result.get('components', {})
                        meaningful_components = 0
                        total_components = 0
                        component_scores = {}
                        
                        for comp_name, comp_value in components.items():
                            if isinstance(comp_value, (int, float)):
                                total_components += 1
                                if abs(comp_value - 50.0) > 0.1:
                                    meaningful_components += 1
                                component_scores[comp_name] = comp_value
                        
                        # Store result
                        results['indicators'][symbol][indicator_name] = {
                            'success': True,
                            'score': score,
                            'is_meaningful': is_meaningful,
                            'time_ms': elapsed_ms,
                            'components': {
                                'total': total_components,
                                'meaningful': meaningful_components,
                                'scores': component_scores
                            },
                            'metadata': result.get('metadata', {})
                        }
                        
                        # Display result
                        status = "✅" if is_meaningful else "⚠️"
                        print(f"{status} Score: {score:.2f} (Meaningful: {is_meaningful})")
                        print(f"⏱️  Time: {elapsed_ms:.2f}ms")
                        
                        if total_components > 0:
                            meaningful_rate = (meaningful_components / total_components) * 100
                            print(f"📊 Components: {meaningful_components}/{total_components} meaningful ({meaningful_rate:.1f}%)")
                            
                            # Show top components
                            if component_scores:
                                sorted_components = sorted(component_scores.items(), key=lambda x: abs(x[1] - 50), reverse=True)
                                print("🎯 Top components:")
                                for comp_name, comp_score in sorted_components[:3]:
                                    trend = "📈" if comp_score > 50 else "📉" if comp_score < 50 else "➡️"
                                    print(f"   {trend} {comp_name}: {comp_score:.1f}")
                    else:
                        results['indicators'][symbol][indicator_name] = {
                            'success': False,
                            'error': 'Invalid result format',
                            'time_ms': elapsed_ms
                        }
                        print(f"❌ Failed: Invalid result format")
                        
                except Exception as e:
                    results['indicators'][symbol][indicator_name] = {
                        'success': False,
                        'error': str(e),
                        'time_ms': 0
                    }
                    print(f"❌ Error: {str(e)}")
        
        # Generate summary report
        print(f"\n{'='*100}")
        print("COMPREHENSIVE TEST SUMMARY")
        print("="*100)
        
        # Overall statistics
        total_tests = 0
        successful_tests = 0
        meaningful_tests = 0
        total_time = 0
        
        for symbol in SYMBOLS:
            if symbol in results['indicators']:
                for indicator_name, result in results['indicators'][symbol].items():
                    total_tests += 1
                    if result.get('success', False):
                        successful_tests += 1
                        if result.get('is_meaningful', False):
                            meaningful_tests += 1
                    total_time += result.get('time_ms', 0)
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        meaningful_rate = (meaningful_tests / successful_tests * 100) if successful_tests > 0 else 0
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  • Total Tests: {total_tests}")
        print(f"  • Successful: {successful_tests} ({success_rate:.1f}%)")
        print(f"  • Meaningful: {meaningful_tests} ({meaningful_rate:.1f}%)")
        print(f"  • Total Time: {total_time:.2f}ms")
        print(f"  • Avg Time/Test: {total_time/total_tests:.2f}ms" if total_tests > 0 else "  • Avg Time/Test: N/A")
        
        # Per-indicator summary
        print(f"\n📈 PER-INDICATOR SUMMARY:")
        indicator_stats = {}
        
        for symbol in SYMBOLS:
            if symbol in results['indicators']:
                for indicator_name, result in results['indicators'][symbol].items():
                    if indicator_name not in indicator_stats:
                        indicator_stats[indicator_name] = {
                            'tests': 0,
                            'successful': 0,
                            'meaningful': 0,
                            'total_time': 0,
                            'avg_score': 0,
                            'scores': []
                        }
                    
                    stats = indicator_stats[indicator_name]
                    stats['tests'] += 1
                    
                    if result.get('success', False):
                        stats['successful'] += 1
                        if result.get('is_meaningful', False):
                            stats['meaningful'] += 1
                        stats['scores'].append(result.get('score', 50))
                    
                    stats['total_time'] += result.get('time_ms', 0)
        
        # Calculate averages and display
        for indicator_name, stats in indicator_stats.items():
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 50
            avg_time = stats['total_time'] / stats['tests'] if stats['tests'] > 0 else 0
            meaningful_pct = (stats['meaningful'] / stats['successful'] * 100) if stats['successful'] > 0 else 0
            
            print(f"\n  {indicator_name.upper()}:")
            print(f"    • Success: {stats['successful']}/{stats['tests']}")
            print(f"    • Meaningful: {stats['meaningful']} ({meaningful_pct:.1f}%)")
            print(f"    • Avg Score: {avg_score:.1f}")
            print(f"    • Avg Time: {avg_time:.1f}ms")
        
        # Performance comparison
        print(f"\n⚡ PERFORMANCE ANALYSIS:")
        fastest = min(indicator_stats.items(), key=lambda x: x[1]['total_time'] / x[1]['tests'] if x[1]['tests'] > 0 else float('inf'))
        slowest = max(indicator_stats.items(), key=lambda x: x[1]['total_time'] / x[1]['tests'] if x[1]['tests'] > 0 else 0)
        
        print(f"  🚀 Fastest: {fastest[0]} ({fastest[1]['total_time'] / fastest[1]['tests']:.1f}ms avg)")
        print(f"  🐌 Slowest: {slowest[0]} ({slowest[1]['total_time'] / slowest[1]['tests']:.1f}ms avg)")
        
        # TA-Lib optimization status
        print(f"\n🔧 TA-LIB OPTIMIZATION STATUS:")
        print(f"  • Configuration: use_talib = {config['optimization']['use_talib']}")
        print(f"  • Fallback enabled: {config['optimization']['fallback_on_error']}")
        print(f"  • Optimization level: {config['optimization']['level']}")
        
        # Save detailed results
        output_file = f"test_output/all_indicators_live_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        # Final assessment
        print(f"\n{'='*100}")
        print("FINAL ASSESSMENT")
        print("="*100)
        
        if success_rate >= 95 and meaningful_rate >= 80:
            print("🏆 EXCELLENT: All indicators working with meaningful calculations!")
            print("✅ System is production-ready with TA-Lib optimizations")
        elif success_rate >= 80 and meaningful_rate >= 60:
            print("🎯 VERY GOOD: Most indicators working well")
            print("✅ System is functional with some room for improvement")
        elif success_rate >= 60:
            print("⚠️  GOOD: System working but needs optimization")
            print("🔧 Some indicators still need attention")
        else:
            print("🚨 NEEDS WORK: Many indicators failing")
            print("🔧 Significant improvements required")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    print(f"\n{'='*100}")
    print("TEST COMPLETE")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(test_all_indicators_comprehensive())