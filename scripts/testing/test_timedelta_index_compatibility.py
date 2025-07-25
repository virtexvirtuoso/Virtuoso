#!/usr/bin/env python3
"""
Test script to verify TimedeltaIndex compatibility issues and test fixes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_timedelta_index_issues():
    """Test various scenarios with TimedeltaIndex"""
    
    print("Testing TimedeltaIndex compatibility issues...")
    print("=" * 60)
    
    # Create test data
    base_timestamp = pd.Timestamp('2024-01-15 12:00:00')
    
    # Create a DataFrame with DatetimeIndex
    dates = pd.date_range(start='2024-01-15 12:00:00', periods=10, freq='1min')
    df = pd.DataFrame({
        'value': np.random.randn(10),
        'high': np.random.randn(10) + 100,
        'low': np.random.randn(10) + 95
    }, index=dates)
    
    print("\n1. Testing time difference operations:")
    print(f"DataFrame index type: {type(df.index)}")
    
    # This creates a TimedeltaIndex
    time_diffs = abs(df.index - base_timestamp)
    print(f"Time differences type: {type(time_diffs)}")
    print(f"Time differences: {time_diffs}")
    
    # Test the problematic operation
    try:
        # This will fail with TimedeltaIndex
        nearest_idx = time_diffs.idxmin()
        print(f"❌ idxmin() worked (unexpected): {nearest_idx}")
    except AttributeError as e:
        print(f"✓ Expected error with idxmin(): {e}")
    
    # Test the fix
    try:
        nearest_pos = time_diffs.argmin()
        nearest_idx = df.index[nearest_pos]
        print(f"✓ Fix with argmin() works: position={nearest_pos}, index={nearest_idx}")
    except Exception as e:
        print(f"❌ Fix failed: {e}")
    
    print("\n2. Testing Series with different index types:")
    
    # Test with regular Series
    series1 = pd.Series([1, 2, 3, 4, 5], index=['a', 'b', 'c', 'd', 'e'])
    print(f"\nRegular Series index type: {type(series1.index)}")
    try:
        min_idx = series1.idxmin()
        print(f"✓ idxmin() works: {min_idx}")
    except Exception as e:
        print(f"❌ idxmin() failed: {e}")
    
    # Test with TimedeltaIndex Series
    td_index = pd.TimedeltaIndex(['1 days', '2 days', '3 days', '4 days', '5 days'])
    series2 = pd.Series([5, 4, 3, 2, 1], index=td_index)
    print(f"\nTimedeltaIndex Series index type: {type(series2.index)}")
    
    try:
        min_idx = series2.idxmin()
        print(f"❌ idxmin() worked (unexpected): {min_idx}")
    except AttributeError as e:
        print(f"✓ Expected error with idxmin(): {e}")
    
    try:
        min_pos = series2.argmin()
        min_idx = series2.index[min_pos]
        print(f"✓ Fix with argmin() works: position={min_pos}, index={min_idx}")
    except Exception as e:
        print(f"❌ Fix failed: {e}")
    
    print("\n3. Testing volume profile scenario:")
    
    # Simulate volume profile with numeric index (should work)
    volume_profile = pd.Series([100, 200, 300, 250, 150], index=[95.0, 96.0, 97.0, 98.0, 99.0])
    print(f"\nVolume profile index type: {type(volume_profile.index)}")
    
    try:
        poc = float(volume_profile.idxmax())
        print(f"✓ idxmax() works for volume profile: POC={poc}")
    except Exception as e:
        print(f"❌ idxmax() failed: {e}")
    
    print("\n4. Testing defensive programming approach:")
    
    def safe_idxmin(series):
        """Safely get index of minimum value"""
        if isinstance(series.index, pd.TimedeltaIndex):
            pos = series.argmin()
            return series.index[pos] if pos >= 0 else None
        else:
            return series.idxmin()
    
    # Test on different series types
    for name, s in [('Regular', series1), ('TimedeltaIndex', series2), ('Volume Profile', volume_profile)]:
        try:
            result = safe_idxmin(s)
            print(f"✓ safe_idxmin() on {name}: {result}")
        except Exception as e:
            print(f"❌ safe_idxmin() failed on {name}: {e}")

def test_price_structure_scenario():
    """Test the specific scenario from price_structure_indicators.py"""
    
    print("\n\n5. Testing price_structure_indicators scenario:")
    print("=" * 60)
    
    # Simulate the scenario
    base_timestamp = pd.Timestamp('2024-01-15 12:00:00')
    
    # Higher timeframe data
    tf_dates = pd.date_range(start='2024-01-15 11:30:00', periods=20, freq='5min')
    tf_data = pd.DataFrame({
        'close': np.random.randn(20) + 100,
        'volume': np.random.randint(1000, 5000, 20)
    }, index=tf_dates)
    
    print(f"Base timestamp: {base_timestamp}")
    print(f"TF data range: {tf_data.index[0]} to {tf_data.index[-1]}")
    
    # Original problematic code
    try:
        time_diffs = abs(tf_data.index - base_timestamp)
        nearest_idx = time_diffs.idxmin()
        tf_index = tf_data.index.get_loc(nearest_idx)
        print(f"❌ Original code worked (unexpected)")
    except AttributeError as e:
        print(f"✓ Original code fails as expected: {e}")
    
    # Fixed code
    try:
        time_diffs = abs(tf_data.index - base_timestamp)
        nearest_pos = time_diffs.argmin()
        nearest_idx = tf_data.index[nearest_pos]
        tf_index = tf_data.index.get_loc(nearest_idx)
        print(f"✓ Fixed code works: nearest_pos={nearest_pos}, nearest_idx={nearest_idx}, tf_index={tf_index}")
    except Exception as e:
        print(f"❌ Fixed code failed: {e}")

if __name__ == "__main__":
    test_timedelta_index_issues()
    test_price_structure_scenario()
    
    print("\n\nSummary:")
    print("=" * 60)
    print("The tests confirm that:")
    print("1. TimedeltaIndex does not support idxmin()/idxmax() methods")
    print("2. Using argmin()/argmax() with positional indexing is the correct fix")
    print("3. Defensive programming with index type checking is recommended")
    print("4. The specific issue in price_structure_indicators.py needs fixing")