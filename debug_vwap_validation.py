#!/usr/bin/env python3
"""
Simple diagnostic script to test DataFrame validation mismatch.
Run this on the VPS to capture the actual validation logic.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import logging

# Setup logging to see debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_dataframe_validation():
    """Test DataFrame validation logic mismatch"""
    
    print("🔍 Testing DataFrame Validation Logic Mismatch")
    print("=" * 50)
    
    # Create test DataFrames that simulate different scenarios
    scenarios = {
        "valid_ohlcv": pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=100, freq='1min'),
            'open': [100.0 + i for i in range(100)],
            'high': [101.0 + i for i in range(100)],
            'low': [99.0 + i for i in range(100)],
            'close': [100.5 + i for i in range(100)],
            'volume': [1000.0 + i*10 for i in range(100)]
        }),
        
        "numeric_index_df": pd.DataFrame([
            [1640995200000, 50000, 50100, 49900, 50050, 1000],
            [1640995260000, 50050, 50150, 49950, 50100, 1100]
        ]),
        
        "empty_df": pd.DataFrame(),
        
        "missing_columns": pd.DataFrame({
            'price': [100, 101, 102],
            'vol': [1000, 1100, 1200]
        }),
        
        "string_columns": pd.DataFrame({
            'open': ['100', '101', '102'],
            'high': ['101', '102', '103'],
            'low': ['99', '100', '101'],
            'close': ['100', '101', '102'],
            'volume': ['1000', '1100', '1200']
        })
    }
    
    # Test each scenario
    for scenario_name, test_df in scenarios.items():
        print(f"\n🧪 Testing scenario: {scenario_name}")
        print(f"   DataFrame type: {type(test_df)}")
        print(f"   DataFrame shape: {test_df.shape}")
        print(f"   DataFrame empty: {test_df.empty}")
        
        if not test_df.empty:
            print(f"   DataFrame columns: {list(test_df.columns)}")
            print(f"   DataFrame dtypes: {test_df.dtypes.to_dict()}")
            print(f"   DataFrame index type: {type(test_df.index)}")
        
        # Test various validation approaches
        
        # 1. Basic validation (monitor style)
        monitor_valid = isinstance(test_df, pd.DataFrame) and not test_df.empty
        print(f"   Monitor validation: {'✅ PASS' if monitor_valid else '❌ FAIL'}")
        
        # 2. Column validation (confluence style)
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        has_required_cols = all(col in test_df.columns for col in required_cols) if not test_df.empty else False
        print(f"   Column validation: {'✅ PASS' if has_required_cols else '❌ FAIL'}")
        
        # 3. Data type validation
        if has_required_cols:
            numeric_valid = all(pd.api.types.is_numeric_dtype(test_df[col]) for col in required_cols)
            print(f"   Numeric validation: {'✅ PASS' if numeric_valid else '❌ FAIL'}")
        else:
            print(f"   Numeric validation: ⏭️  SKIP (no required columns)")
        
        # 4. Shape validation (minimum data points)
        min_points = 10
        shape_valid = len(test_df) >= min_points if not test_df.empty else False
        print(f"   Shape validation (>={min_points}): {'✅ PASS' if shape_valid else '❌ FAIL'}")
        
        # 5. NaN validation
        if not test_df.empty and has_required_cols:
            has_nans = test_df[required_cols].isnull().any().any()
            nan_valid = not has_nans
            print(f"   NaN validation: {'✅ PASS' if nan_valid else '❌ FAIL'}")
        else:
            print(f"   NaN validation: ⏭️  SKIP")
        
        # 6. Index validation
        try:
            index_types = [pd.DatetimeIndex, pd.RangeIndex]
            # Try to add Int64Index if it exists (older pandas versions)
            if hasattr(pd, 'Int64Index'):
                index_types.append(pd.Int64Index)
            index_valid = any(isinstance(test_df.index, idx_type) for idx_type in index_types)
        except:
            index_valid = True  # Skip validation if index types not available
        print(f"   Index validation: {'✅ PASS' if index_valid else '❌ FAIL'} ({type(test_df.index).__name__})")
        
        print("-" * 40)
    
    print("\n🔍 Testing CCXT-style data conversion...")
    
    # Test CCXT-style data (what we get from Bybit API)
    ccxt_ohlcv = [
        [1640995200000, 50000, 50100, 49900, 50050, 1000],
        [1640995260000, 50050, 50150, 49950, 50100, 1100],
        [1640995320000, 50100, 50200, 50000, 50150, 1200]
    ]
    
    print(f"Raw CCXT data: {ccxt_ohlcv[:2]}...")
    
    # Convert to DataFrame (monitor style)
    df_monitor = pd.DataFrame(ccxt_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_monitor['timestamp'] = pd.to_datetime(df_monitor['timestamp'], unit='ms')
    df_monitor.set_index('timestamp', inplace=True)
    
    print(f"Monitor converted:")
    print(f"   Shape: {df_monitor.shape}")
    print(f"   Columns: {list(df_monitor.columns)}")
    print(f"   Index type: {type(df_monitor.index)}")
    print(f"   Dtypes: {df_monitor.dtypes.to_dict()}")
    
    # Test potential issues with numeric columns
    print(f"\n🔬 Testing numeric column edge cases...")
    
    # Case 1: Numeric columns with integer dtype
    test_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in test_cols:
        dtype = df_monitor[col].dtype
        is_numeric = pd.api.types.is_numeric_dtype(dtype)
        print(f"   {col}: {dtype} -> numeric: {is_numeric}")
    
    # Case 2: What if columns have names as integers (CCXT sometimes does this)
    df_numeric_cols = pd.DataFrame(ccxt_ohlcv)
    print(f"\nNumeric column names DataFrame:")
    print(f"   Shape: {df_numeric_cols.shape}")
    print(f"   Columns: {list(df_numeric_cols.columns)}")
    print(f"   Column types: {[type(col) for col in df_numeric_cols.columns]}")
    
    # Test if this passes basic validation
    basic_valid = isinstance(df_numeric_cols, pd.DataFrame) and not df_numeric_cols.empty
    print(f"   Basic validation: {'✅ PASS' if basic_valid else '❌ FAIL'}")
    
    # Test column access
    try:
        if hasattr(df_numeric_cols.columns, 'dtype') and df_numeric_cols.columns.dtype == 'int64':
            print("   ⚠️  WARNING: Columns are numeric indexes, not names!")
            print(f"   This could cause validation failures in confluence analyzer")
    except:
        pass
    
    print("\n" + "=" * 50)
    print("✅ DataFrame validation testing completed!")
    print("\n💡 Key insights to look for:")
    print("1. Are DataFrames being created with numeric column indexes instead of names?")
    print("2. Are data types not matching expected numeric types?") 
    print("3. Are minimum row count requirements not being met?")
    print("4. Are NaN values causing validation failures?")
    print("5. Are index types causing issues?")

if __name__ == "__main__":
    test_dataframe_validation()