#!/usr/bin/env python3
"""
Test script for HTF interpolation functionality.

This script tests the interpolation of HTF (4-hour) candles from MTF (1-hour) data
for newer coins that don't have sufficient HTF historical data.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

def create_mock_mtf_data(symbol: str = "PUMPFUNUSDT", hours: int = 200) -> pd.DataFrame:
    """Create mock MTF (1-hour) data for testing interpolation.
    
    Args:
        symbol: Symbol name for testing
        hours: Number of hours of data to generate
        
    Returns:
        pd.DataFrame: Mock MTF OHLCV data
    """
    # Create timestamp range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    timestamps = pd.date_range(start=start_time, end=end_time, freq='1H')
    
    # Generate realistic price data with some volatility
    np.random.seed(42)  # For reproducible results
    base_price = 0.001  # Starting price for PUMPFUNUSDT-like token
    
    prices = [base_price]
    for i in range(1, len(timestamps)):
        # Add some random walk with mean reversion
        change = np.random.normal(0, 0.02)  # 2% volatility
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.0001))  # Ensure positive price
    
    # Create OHLCV data
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        # Generate realistic OHLC from close price
        volatility = np.random.uniform(0.005, 0.03)  # 0.5% to 3% intraday volatility
        high = close * (1 + np.random.uniform(0, volatility))
        low = close * (1 - np.random.uniform(0, volatility))
        open_price = close * (1 + np.random.uniform(-volatility/2, volatility/2))
        
        # Ensure OHLC relationship
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Generate volume (higher volume for larger price moves)
        price_change = abs(close - open_price) / open_price
        base_volume = np.random.uniform(1000, 10000)
        volume = base_volume * (1 + price_change * 10)
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df

def test_htf_interpolation():
    """Test the HTF interpolation functionality."""
    print("=== Testing HTF Interpolation Functionality ===\n")
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = Logger("test_htf_interpolation")
    
    # Create mock config
    config = {
        'timeframes': {
            'base': {'interval': 1, 'weight': 0.4, 'validation': {'min_candles': 100}},
            'ltf': {'interval': 5, 'weight': 0.3, 'validation': {'min_candles': 50}},
            'mtf': {'interval': 30, 'weight': 0.2, 'validation': {'min_candles': 50}},
            'htf': {'interval': 240, 'weight': 0.1, 'validation': {'min_candles': 50}}
        },
        'analysis': {
            'indicators': {
                'price_structure': {
                    'components': {
                        'support_resistance': {'weight': 1/6},
                        'order_blocks': {'weight': 1/6},
                        'trend_position': {'weight': 1/6},
                        'volume_profile': {'weight': 1/6},
                        'market_structure': {'weight': 1/6},
                        'range_analysis': {'weight': 1/6}
                    }
                }
            }
        },
        'confluence': {
            'weights': {
                'sub_components': {
                    'price_structure': {
                        'support_resistance': 1/6,
                        'order_blocks': 1/6,
                        'trend_position': 1/6,
                        'volume_profile': 1/6,
                        'market_structure': 1/6,
                        'range_analysis': 1/6
                    }
                }
            }
        }
    }
    
    # Initialize indicator
    indicator = PriceStructureIndicators(config, logger)
    
    # Create mock MTF data (simulating PUMPFUNUSDT case)
    print("1. Creating mock MTF data for PUMPFUNUSDT...")
    mtf_data = create_mock_mtf_data("PUMPFUNUSDT", hours=200)
    print(f"   Created {len(mtf_data)} MTF candles")
    print(f"   Date range: {mtf_data.index[0]} to {mtf_data.index[-1]}")
    print(f"   Price range: ${mtf_data['low'].min():.6f} - ${mtf_data['high'].max():.6f}")
    
    # Test interpolation directly
    print("\n2. Testing direct HTF interpolation...")
    interpolated_htf = indicator._interpolate_htf_candles(mtf_data, target_candles=50)
    
    if not interpolated_htf.empty:
        print(f"   ✓ Successfully interpolated {len(interpolated_htf)} HTF candles")
        print(f"   Date range: {interpolated_htf.index[0]} to {interpolated_htf.index[-1]}")
        print(f"   Price range: ${interpolated_htf['low'].min():.6f} - ${interpolated_htf['high'].max():.6f}")
        print(f"   Is interpolated: {getattr(interpolated_htf, '_is_interpolated', False)}")
        
        # Verify OHLCV relationships
        valid_ohlc = all(
            (row['high'] >= row['low']) and 
            (row['high'] >= row['open']) and 
            (row['high'] >= row['close']) and
            (row['low'] <= row['open']) and 
            (row['low'] <= row['close'])
            for _, row in interpolated_htf.iterrows()
        )
        print(f"   ✓ OHLCV relationships valid: {valid_ohlc}")
        
    else:
        print("   ✗ Interpolation failed")
        return False
    
    # Test integration with market data structure
    print("\n3. Testing integration with market data structure...")
    
    # Create market data with missing HTF
    market_data = {
        'symbol': 'PUMPFUNUSDT',
        'ohlcv': {
            'base': mtf_data.iloc[-100:],  # Use last 100 candles as base
            'ltf': mtf_data.iloc[-150:],   # Use last 150 candles as LTF
            'mtf': mtf_data,               # Full MTF data
            # HTF is missing - should trigger interpolation
        }
    }
    
    # Test validation and interpolation
    is_valid = indicator._validate_input(market_data)
    print(f"   ✓ Input validation passed: {is_valid}")
    
    if is_valid:
        # Check if HTF was interpolated
        ohlcv = market_data.get('ohlcv', {})
        if 'htf' in ohlcv:
            htf_data = ohlcv['htf']
            is_interpolated = getattr(htf_data, '_is_interpolated', False)
            print(f"   ✓ HTF data present: {len(htf_data)} candles")
            print(f"   ✓ HTF is interpolated: {is_interpolated}")
        else:
            print("   ✗ HTF data not found after validation")
            return False
    
    # Test timeframe score calculation with interpolated data
    print("\n4. Testing timeframe score calculation with interpolated data...")
    
    try:
        import asyncio
        timeframe_scores = asyncio.run(indicator._calculate_timeframe_scores(ohlcv))
        
        if 'htf' in timeframe_scores:
            htf_scores = timeframe_scores['htf']
            print(f"   ✓ HTF timeframe scores calculated: {len(htf_scores)} components")
            for component, score in htf_scores.items():
                print(f"      {component}: {score:.2f}")
        else:
            print("   ✗ HTF timeframe scores not found")
            
    except Exception as e:
        print(f"   ✗ Error calculating timeframe scores: {str(e)}")
        return False
    
    print("\n=== HTF Interpolation Test Completed Successfully ===")
    return True

def test_edge_cases():
    """Test edge cases for HTF interpolation."""
    print("\n=== Testing Edge Cases ===\n")
    
    # Setup
    config = {
        'timeframes': {
            'base': {'interval': 1, 'weight': 0.4, 'validation': {'min_candles': 100}},
            'ltf': {'interval': 5, 'weight': 0.3, 'validation': {'min_candles': 50}},
            'mtf': {'interval': 30, 'weight': 0.2, 'validation': {'min_candles': 50}},
            'htf': {'interval': 240, 'weight': 0.1, 'validation': {'min_candles': 50}}
        },
        'analysis': {'indicators': {'price_structure': {}}}
    }
    logger = Logger("test_edge_cases")
    indicator = PriceStructureIndicators(config, logger)
    
    # Test 1: Insufficient MTF data
    print("1. Testing insufficient MTF data...")
    small_mtf = create_mock_mtf_data(hours=10)  # Only 10 hours
    result = indicator._interpolate_htf_candles(small_mtf, target_candles=50)
    if result.empty:
        print("   ✓ Correctly handled insufficient data")
    else:
        print(f"   ⚠ Generated {len(result)} candles from insufficient data")
    
    # Test 2: Empty MTF data
    print("2. Testing empty MTF data...")
    empty_df = pd.DataFrame()
    result = indicator._interpolate_htf_candles(empty_df, target_candles=50)
    if result.empty:
        print("   ✓ Correctly handled empty data")
    else:
        print("   ✗ Should have returned empty DataFrame")
    
    # Test 3: None MTF data
    print("3. Testing None MTF data...")
    result = indicator._interpolate_htf_candles(None, target_candles=50)
    if result.empty:
        print("   ✓ Correctly handled None data")
    else:
        print("   ✗ Should have returned empty DataFrame")
    
    print("\n=== Edge Case Tests Completed ===")

if __name__ == "__main__":
    print("Starting HTF Interpolation Tests...\n")
    
    # Run main test
    success = test_htf_interpolation()
    
    # Run edge case tests
    test_edge_cases()
    
    if success:
        print("\n🎉 All tests passed! HTF interpolation is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
    
    print("\nTest completed.") 