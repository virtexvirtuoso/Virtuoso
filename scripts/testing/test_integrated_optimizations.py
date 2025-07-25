#!/usr/bin/env python3
"""
Test the integrated optimizations in technical_indicators.py
This script tests the new hybrid optimization approach with live data.
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

from src.indicators.technical_indicators import TechnicalIndicators
from src.core.exchanges.bybit import BybitExchange

async def test_integrated_optimizations():
    """Test the integrated optimization system with live data."""
    
    print("="*80)
    print("INTEGRATED OPTIMIZATIONS TEST")
    print("="*80)
    
    # Test configurations
    configs = {
        'auto': {
            'optimization': {
                'level': 'auto',
                'use_talib': True,
                'benchmark': True,
                'fallback_on_error': True
            }
        },
        'talib_only': {
            'optimization': {
                'level': 'talib',
                'use_talib': True,
                'benchmark': True,
                'fallback_on_error': False
            }
        },
        'pandas_only': {
            'optimization': {
                'level': 'pandas',
                'use_talib': False,
                'benchmark': True,
                'fallback_on_error': True
            }
        }
    }
    
    # Add required config structure
    base_config = {
        'analysis': {
            'indicators': {
                'technical': {}
            }
        },
        'confluence': {
            'weights': {
                'sub_components': {
                    'technical': {}
                }
            }
        },
        'timeframes': {
            'base': {'weight': 0.4, 'interval': '5m'},
            'ltf': {'weight': 0.3, 'interval': '1m'},
            'mtf': {'weight': 0.2, 'interval': '15m'},
            'htf': {'weight': 0.1, 'interval': '1h'}
        },
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
        'logging': {
            'level': 'WARNING'  # Reduce log noise
        }
    }
    
    # Merge configs
    for config_name, config in configs.items():
        configs[config_name] = {**base_config, **config}
    
    # 1. Generate test data 
    print("\n1. Generating test data...")
    df_test = generate_test_data(1000)
    print(f"   Generated {len(df_test)} test data points")
    
    # 2. Fetch live data
    print("\n2. Fetching live data from Bybit...")
    try:
        exchange = BybitExchange(base_config)
        symbol = 'BTCUSDT'
        klines = await exchange.fetch_ohlcv(symbol, '5m', 200)
        
        df_live = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_live['timestamp'] = pd.to_datetime(df_live['timestamp'], unit='ms')
        df_live.set_index('timestamp', inplace=True)
        
        print(f"   Fetched {len(df_live)} live candles for {symbol}")
        print(f"   Latest price: ${df_live['close'].iloc[-1]:,.2f}")
        
    except Exception as e:
        print(f"   Failed to fetch live data: {e}")
        print("   Using test data only")
        df_live = df_test
    
    # 3. Test different optimization levels
    print("\n3. Testing optimization levels...")
    
    results = {}
    
    for config_name, config in configs.items():
        print(f"\n   Testing {config_name} configuration...")
        
        try:
            # Initialize indicators
            indicators = TechnicalIndicators(config)
            print(f"     Optimization level: {indicators.actual_optimization}")
            
            # Test with live data
            print("     Testing with live data...")
            start_time = time.perf_counter()
            
            # Test individual indicators
            rsi_result = indicators._calculate_rsi_optimized(df_live['close'])
            macd_result = indicators._calculate_macd_optimized(df_live['close'])
            atr_result = indicators._calculate_atr_optimized(df_live['high'], df_live['low'], df_live['close'])
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000
            
            # Store results
            results[config_name] = {
                'optimization': indicators.actual_optimization,
                'execution_time': execution_time,
                'rsi_latest': float(rsi_result.iloc[-1]) if not pd.isna(rsi_result.iloc[-1]) else None,
                'macd_latest': float(macd_result[0].iloc[-1]) if not pd.isna(macd_result[0].iloc[-1]) else None,
                'atr_latest': float(atr_result.iloc[-1]) if not pd.isna(atr_result.iloc[-1]) else None,
                'success': True
            }
            
            print(f"     ✅ Success - {execution_time:.2f}ms")
            print(f"        RSI: {results[config_name]['rsi_latest']:.2f}")
            print(f"        MACD: {results[config_name]['macd_latest']:.4f}")
            print(f"        ATR: {results[config_name]['atr_latest']:.2f}")
            
        except Exception as e:
            print(f"     ❌ Failed: {e}")
            results[config_name] = {
                'optimization': 'failed',
                'execution_time': None,
                'error': str(e),
                'success': False
            }
    
    # 4. Performance comparison
    print("\n4. Performance comparison...")
    print("   " + "-"*60)
    
    successful_results = {k: v for k, v in results.items() if v['success']}
    
    if len(successful_results) > 1:
        baseline = None
        for config_name, result in successful_results.items():
            if result['optimization'] == 'pandas':
                baseline = result['execution_time']
                break
        
        if baseline:
            print(f"   {'Configuration':<15} {'Optimization':<12} {'Time (ms)':<10} {'Speedup':<8}")
            print("   " + "-"*60)
            
            for config_name, result in successful_results.items():
                speedup = baseline / result['execution_time'] if result['execution_time'] > 0 else 0
                print(f"   {config_name:<15} {result['optimization']:<12} {result['execution_time']:<10.2f} {speedup:.1f}x")
        else:
            for config_name, result in successful_results.items():
                print(f"   {config_name}: {result['optimization']} - {result['execution_time']:.2f}ms")
    
    # 5. Validation - ensure results are consistent
    print("\n5. Result validation...")
    
    if len(successful_results) > 1:
        rsi_values = [r['rsi_latest'] for r in successful_results.values() if r['rsi_latest'] is not None]
        macd_values = [r['macd_latest'] for r in successful_results.values() if r['macd_latest'] is not None]
        
        if len(rsi_values) > 1:
            rsi_diff = max(rsi_values) - min(rsi_values)
            print(f"   RSI variance: {rsi_diff:.4f} (should be < 0.01)")
            
        if len(macd_values) > 1:
            macd_diff = max(macd_values) - min(macd_values)
            print(f"   MACD variance: {macd_diff:.6f} (should be < 0.001)")
    
    # 6. Get performance reports
    print("\n6. Performance reports...")
    
    for config_name, config in configs.items():
        if config_name in successful_results:
            try:
                indicators = TechnicalIndicators(config)
                # Run a calculation to generate metrics
                indicators._calculate_rsi_optimized(df_live['close'])
                
                report = indicators.get_performance_report()
                if 'summary' in report and report['summary']:
                    print(f"   {config_name}: {report['summary']}")
                    
            except Exception as e:
                print(f"   {config_name}: Error getting report - {e}")
    
    print("\n" + "="*80)
    print("INTEGRATION TEST COMPLETE")
    print("="*80)
    
    return results

def generate_test_data(n=1000):
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=n, freq='5min')
    
    # Random walk with realistic price movements
    returns = np.random.normal(0.0001, 0.008, n)
    close_prices = 50000 * np.exp(np.cumsum(returns))
    
    # Convert to pandas Series for easier manipulation
    close_series = pd.Series(close_prices, index=dates)
    
    # Generate realistic OHLC data
    open_prices = close_series.shift(1).fillna(close_series.iloc[0])
    
    # High and low with some randomness
    high_mult = 1 + np.abs(np.random.normal(0, 0.002, n))
    low_mult = 1 - np.abs(np.random.normal(0, 0.002, n))
    
    high_prices = np.maximum(open_prices, close_series) * high_mult
    low_prices = np.minimum(open_prices, close_series) * low_mult
    
    # Ensure OHLC relationships are maintained
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_series))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_series))
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_series,
        'volume': np.random.uniform(100000, 1000000, n)
    }, index=dates)
    
    return df

def main():
    """Run the integration test."""
    asyncio.run(test_integrated_optimizations())

if __name__ == "__main__":
    main()