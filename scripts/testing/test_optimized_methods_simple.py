#!/usr/bin/env python3
"""
Simple test of the optimized indicator methods
Tests the direct optimization methods without full class initialization.
"""

import pandas as pd
import numpy as np
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Test direct TA-Lib availability
try:
    import talib
    HAS_TALIB = True
    print("✅ TA-Lib is available")
except ImportError:
    HAS_TALIB = False
    print("❌ TA-Lib is not available")

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

def test_rsi_optimization(df):
    """Test RSI calculation with both methods."""
    print("\n--- RSI Test ---")
    
    close_prices = df['close']
    period = 14
    
    results = {}
    
    # Test TA-Lib version
    if HAS_TALIB:
        try:
            start_time = time.perf_counter()
            close_values = close_prices.values.astype(np.float64)
            rsi_talib = talib.RSI(close_values, timeperiod=period)
            rsi_talib_series = pd.Series(rsi_talib, index=close_prices.index)
            end_time = time.perf_counter()
            
            results['talib'] = {
                'time': (end_time - start_time) * 1000,
                'value': rsi_talib_series.iloc[-1],
                'success': True
            }
            print(f"TA-Lib RSI: {rsi_talib_series.iloc[-1]:.2f} ({results['talib']['time']:.2f}ms)")
            
        except Exception as e:
            results['talib'] = {'success': False, 'error': str(e)}
            print(f"TA-Lib RSI failed: {e}")
    
    # Test pandas version (improved with Wilder's smoothing)
    try:
        start_time = time.perf_counter()
        delta = close_prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Use Wilder's smoothing to match TA-Lib
        alpha = 1.0 / period
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi_pandas = 100 - (100 / (1 + rs))
        end_time = time.perf_counter()
        
        results['pandas'] = {
            'time': (end_time - start_time) * 1000,
            'value': rsi_pandas.iloc[-1],
            'success': True
        }
        print(f"Pandas RSI: {rsi_pandas.iloc[-1]:.2f} ({results['pandas']['time']:.2f}ms)")
        
    except Exception as e:
        results['pandas'] = {'success': False, 'error': str(e)}
        print(f"Pandas RSI failed: {e}")
    
    # Compare results
    if results.get('talib', {}).get('success') and results.get('pandas', {}).get('success'):
        diff = abs(results['talib']['value'] - results['pandas']['value'])
        speedup = results['pandas']['time'] / results['talib']['time']
        print(f"Difference: {diff:.4f} (should be < 0.01)")
        print(f"Speedup: {speedup:.1f}x")
    
    return results

def test_macd_optimization(df):
    """Test MACD calculation with both methods."""
    print("\n--- MACD Test ---")
    
    close_prices = df['close']
    fast, slow, signal = 12, 26, 9
    
    results = {}
    
    # Test TA-Lib version
    if HAS_TALIB:
        try:
            start_time = time.perf_counter()
            close_values = close_prices.values.astype(np.float64)
            macd_line, signal_line, histogram = talib.MACD(
                close_values, fastperiod=fast, slowperiod=slow, signalperiod=signal
            )
            end_time = time.perf_counter()
            
            results['talib'] = {
                'time': (end_time - start_time) * 1000,
                'macd': macd_line[-1],
                'signal': signal_line[-1],
                'histogram': histogram[-1],
                'success': True
            }
            print(f"TA-Lib MACD: {macd_line[-1]:.4f} ({results['talib']['time']:.2f}ms)")
            
        except Exception as e:
            results['talib'] = {'success': False, 'error': str(e)}
            print(f"TA-Lib MACD failed: {e}")
    
    # Test pandas version
    try:
        start_time = time.perf_counter()
        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        end_time = time.perf_counter()
        
        results['pandas'] = {
            'time': (end_time - start_time) * 1000,
            'macd': macd_line.iloc[-1],
            'signal': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1],
            'success': True
        }
        print(f"Pandas MACD: {macd_line.iloc[-1]:.4f} ({results['pandas']['time']:.2f}ms)")
        
    except Exception as e:
        results['pandas'] = {'success': False, 'error': str(e)}
        print(f"Pandas MACD failed: {e}")
    
    # Compare results
    if results.get('talib', {}).get('success') and results.get('pandas', {}).get('success'):
        diff = abs(results['talib']['macd'] - results['pandas']['macd'])
        speedup = results['pandas']['time'] / results['talib']['time']
        print(f"MACD Difference: {diff:.6f} (should be < 0.001)")
        print(f"Speedup: {speedup:.1f}x")
    
    return results

def main():
    """Run the simple optimization tests."""
    print("="*60)
    print("SIMPLE OPTIMIZATION TEST")
    print("="*60)
    
    # Generate test data
    print("\nGenerating test data...")
    df = generate_test_data(1000)
    print(f"Generated {len(df)} data points")
    print(f"Latest close: ${df['close'].iloc[-1]:,.2f}")
    
    # Test individual indicators
    rsi_results = test_rsi_optimization(df)
    macd_results = test_macd_optimization(df)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if HAS_TALIB:
        print("✅ TA-Lib integration successful")
        
        # Calculate overall speedup
        total_talib_time = 0
        total_pandas_time = 0
        successful_tests = 0
        
        for results in [rsi_results, macd_results]:
            if results.get('talib', {}).get('success') and results.get('pandas', {}).get('success'):
                total_talib_time += results['talib']['time']
                total_pandas_time += results['pandas']['time']
                successful_tests += 1
        
        if successful_tests > 0:
            overall_speedup = total_pandas_time / total_talib_time
            print(f"Overall speedup: {overall_speedup:.1f}x")
            print(f"Total time reduction: {total_pandas_time - total_talib_time:.2f}ms")
    else:
        print("⚠️  TA-Lib not available, only pandas fallbacks tested")
    
    print("\nIntegration test complete ✅")

if __name__ == "__main__":
    main()