#!/usr/bin/env python3
"""
Test Confluence Analysis with Fixed Indicators
Verify that confluence analysis now works properly with real indicator calculations.
"""

import asyncio
import pandas as pd
import numpy as np
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_confluence_with_fixed_indicators():
    """Test confluence analysis with our fixed indicators."""
    print("=" * 80)
    print("TESTING CONFLUENCE ANALYSIS WITH FIXED INDICATORS")
    print("=" * 80)
    
    try:
        # Initialize exchange and fetch live data
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
                        'min_candles': 50
                    },
                    'weight': 0.4
                },
                'ltf': {
                    'interval': 5,
                    'required': 200,
                    'validation': {
                        'max_gap': 300,
                        'min_candles': 30
                    },
                    'weight': 0.3
                },
                'mtf': {
                    'interval': 15,
                    'required': 100,
                    'validation': {
                        'max_gap': 900,
                        'min_candles': 20
                    },
                    'weight': 0.2
                },
                'htf': {
                    'interval': 60,
                    'required': 50,
                    'validation': {
                        'max_gap': 3600,
                        'min_candles': 15
                    },
                    'weight': 0.1
                }
            },
            'confluence': {
                'weights': {
                    'components': {
                        'technical': 0.20,
                        'volume': 0.10,
                        'orderflow': 0.25,
                        'sentiment': 0.15,
                        'orderbook': 0.20,
                        'price_structure': 0.10
                    },
                    'sub_components': {
                        'technical': {
                            'rsi': 0.2,
                            'macd': 0.2,
                            'williams_r': 0.15,
                            'atr': 0.15,
                            'cci': 0.15,
                            'adx': 0.15
                        },
                        'volume': {
                            'obv': 0.2,
                            'adl': 0.2,
                            'relative_volume': 0.2,
                            'cmf': 0.2,
                            'volume_delta': 0.2
                        }
                    }
                }
            },
            'analysis': {
                'indicators': {
                    'technical': {'components': {}},
                    'volume': {'components': {}},
                    'orderflow': {'components': {}},
                    'price_structure': {'components': {}},
                    'sentiment': {'components': {}},
                    'orderbook': {'components': {}}
                }
            },
            'optimization': {
                'level': 'auto',
                'use_talib': True,
                'fallback_on_error': True
            },
            'validation_requirements': {
                'ohlcv': {
                    'timeframes': {
                        'base': {'min_candles': 50},
                        'ltf': {'min_candles': 30},
                        'mtf': {'min_candles': 20},
                        'htf': {'min_candles': 15}
                    }
                },
                'trades': {
                    'min_trades': 20,
                    'max_age': 3600
                },
                'orderbook': {
                    'min_levels': 5
                }
            }
        }
        
        # Initialize exchange
        exchange = BybitExchange(config)
        print("✅ Exchange initialized")
        
        # Fetch live data for BTC
        symbol = 'BTCUSDT'
        print(f"\n📊 Fetching live data for {symbol}...")
        
        # Fetch multiple timeframes
        base_data = await exchange.fetch_ohlcv(symbol, '1m', 500)
        ltf_data = await exchange.fetch_ohlcv(symbol, '5m', 200)
        mtf_data = await exchange.fetch_ohlcv(symbol, '15m', 100)
        htf_data = await exchange.fetch_ohlcv(symbol, '1h', 50)
        
        if not all([base_data, ltf_data, mtf_data, htf_data]):
            print("❌ Failed to fetch required data")
            return
        
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
        
        # Create enhanced market data with simulated trades and orderbook
        base_df = timeframes_data['base']
        
        # Generate simulated trade data
        trades = []
        for i, (timestamp, row) in enumerate(base_df.tail(100).iterrows()):  # Last 100 candles
            for j in range(np.random.randint(5, 15)): 
                trade_price = np.random.uniform(row['low'], row['high'])
                trade_size = np.random.exponential(row['volume'] / 10)
                trade_side = 'buy' if trade_price > row['open'] else 'sell'
                
                trades.append({
                    'id': f"{i}_{j}",
                    'price': trade_price,
                    'size': trade_size,
                    'side': trade_side,
                    'time': timestamp
                })
        
        # Generate simulated orderbook
        latest_price = base_df['close'].iloc[-1]
        bids = []
        asks = []
        
        for i in range(20):
            bid_price = latest_price * (1 - (i + 1) * 0.001)
            ask_price = latest_price * (1 + (i + 1) * 0.001)
            bid_size = np.random.exponential(1000)
            ask_size = np.random.exponential(1000)
            
            bids.append([bid_price, bid_size])
            asks.append([ask_price, ask_size])
        
        market_data = {
            'ohlcv': timeframes_data,
            'trades': trades,
            'orderbook': {
                'bids': bids,
                'asks': asks,
                'timestamp': base_df.index[-1]
            },
            'timestamp': base_df.index[-1],
            'symbol': symbol
        }
        
        print(f"✅ Market data prepared:")
        print(f"  • Base: {len(timeframes_data['base'])} candles")
        print(f"  • LTF: {len(timeframes_data['ltf'])} candles")
        print(f"  • MTF: {len(timeframes_data['mtf'])} candles") 
        print(f"  • HTF: {len(timeframes_data['htf'])} candles")
        print(f"  • Trades: {len(trades)} simulated trades")
        print(f"  • Orderbook: {len(bids)} bid/ask levels")
        print(f"  • Latest Price: ${latest_price:,.2f}")
        
        # Initialize ConfluenceAnalyzer
        print(f"\n🔄 Initializing Confluence Analyzer...")
        from src.analysis.core.confluence import ConfluenceAnalyzer
        
        confluence = ConfluenceAnalyzer(config)
        print("✅ Confluence analyzer initialized")
        
        # Run confluence analysis
        print(f"\n📈 Running confluence analysis...")
        start_time = time.perf_counter()
        
        result = await confluence.analyze(market_data)
        
        end_time = time.perf_counter()
        analysis_time = (end_time - start_time) * 1000
        
        print(f"✅ Analysis completed in {analysis_time:.2f}ms")
        
        # Display results
        print(f"\n{'='*60}")
        print("CONFLUENCE ANALYSIS RESULTS")
        print("="*60)
        
        if result and isinstance(result, dict):
            # Overall confluence score
            overall_score = result.get('confluence_score', 'N/A')
            print(f"\n🎯 OVERALL CONFLUENCE SCORE: {overall_score}")
            
            # Individual indicator scores
            indicator_scores = result.get('indicator_scores', {})
            if indicator_scores:
                print(f"\n📊 INDIVIDUAL INDICATOR SCORES:")
                for indicator, score in indicator_scores.items():
                    status = "🟢" if score > 60 else "🟡" if score > 40 else "🔴"
                    print(f"  {status} {indicator.replace('_', ' ').title()}: {score:.1f}")
            
            # Component analysis
            components = result.get('components', {})
            if components:
                print(f"\n📋 COMPONENT BREAKDOWN:")
                for component, data in components.items():
                    if isinstance(data, dict) and 'score' in data:
                        score = data['score']
                        weight = data.get('weight', 0)
                        contribution = score * weight
                        print(f"  • {component.replace('_', ' ').title()}: {score:.1f} (weight: {weight:.2f}, contrib: {contribution:.1f})")
            
            # Signal analysis
            signals = result.get('signals', {})
            if signals:
                print(f"\n🚨 SIGNALS:")
                signal_type = signals.get('type', 'NEUTRAL')
                signal_strength = signals.get('strength', 'MEDIUM')
                signal_confidence = signals.get('confidence', 50)
                
                print(f"  Signal Type: {signal_type}")
                print(f"  Signal Strength: {signal_strength}")
                print(f"  Confidence: {signal_confidence}%")
            
            # Metadata
            metadata = result.get('metadata', {})
            if metadata:
                print(f"\n📝 ANALYSIS METADATA:")
                processing_time = metadata.get('processing_time', analysis_time)
                indicators_processed = metadata.get('indicators_processed', 0)
                data_quality = metadata.get('data_quality', 'N/A')
                
                print(f"  Processing Time: {processing_time:.2f}ms")
                print(f"  Indicators Processed: {indicators_processed}")
                print(f"  Data Quality: {data_quality}")
            
            # Check for meaningful scores (not defaults)
            meaningful_scores = []
            default_scores = []
            
            for indicator, score in indicator_scores.items():
                if isinstance(score, (int, float)):
                    if score != 50.0:
                        meaningful_scores.append((indicator, score))
                    else:
                        default_scores.append(indicator)
            
            print(f"\n💡 SCORE ANALYSIS:")
            print(f"  Meaningful Scores: {len(meaningful_scores)}/{len(indicator_scores)}")
            print(f"  Default Scores: {len(default_scores)}")
            
            if meaningful_scores:
                print(f"  ✅ Real Calculations Working:")
                for indicator, score in meaningful_scores:
                    print(f"    • {indicator.replace('_', ' ').title()}: {score:.1f}")
            
            if default_scores:
                print(f"  ⚠️  Still Using Defaults:")
                for indicator in default_scores:
                    print(f"    • {indicator.replace('_', ' ').title()}")
            
            # Overall assessment
            meaningful_rate = len(meaningful_scores) / len(indicator_scores) * 100 if indicator_scores else 0
            
            print(f"\n🚀 CONFLUENCE SYSTEM STATUS:")
            if meaningful_rate >= 80:
                print(f"  ✅ EXCELLENT: {meaningful_rate:.1f}% meaningful scores")
                print(f"  🎯 Confluence analysis is working with real calculations")
            elif meaningful_rate >= 50:
                print(f"  ⚠️  GOOD: {meaningful_rate:.1f}% meaningful scores")
                print(f"  🔧 Some indicators still need optimization")
            else:
                print(f"  ❌ NEEDS WORK: {meaningful_rate:.1f}% meaningful scores")
                print(f"  🚨 Most indicators still using default values")
        
        else:
            print("❌ No valid result from confluence analysis")
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    
    print(f"\n{'='*80}")
    print("CONFLUENCE TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    import traceback
    asyncio.run(test_confluence_with_fixed_indicators())