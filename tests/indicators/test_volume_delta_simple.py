#!/usr/bin/env python3

import pandas as pd
import numpy as np

def test_dataframe_ambiguity():
    """Test the specific DataFrame ambiguity issue"""
    print("🔍 TESTING DATAFRAME AMBIGUITY ISSUE")
    print("=" * 50)
    
    # Create test trades data
    trades_data = [
        {'side': 'buy', 'amount': 1.0, 'price': 100.0},
        {'side': 'sell', 'amount': 0.5, 'price': 99.0},
        {'side': 'buy', 'amount': 2.0, 'price': 101.0},
        {'side': 'sell', 'amount': 1.5, 'price': 100.5},
        {'side': 'buy', 'amount': 0.8, 'price': 102.0}
    ]
    
    trades_df = pd.DataFrame(trades_data)
    print("Original DataFrame:")
    print(trades_df)
    print(f"Side column type: {type(trades_df['side'])}")
    print(f"Side values: {trades_df['side'].tolist()}")
    
    # Test the problematic line
    print("\n🔍 Testing the problematic line...")
    
    try:
        # This is the line that was causing the error
        print("Testing: trades_df['side'].map(lambda x: 1 if str(x).lower() == 'buy' else -1)")
        trades_df['side_value'] = trades_df['side'].map(lambda x: 1 if str(x).lower() == 'buy' else -1)
        print("✅ SUCCESS! No DataFrame ambiguity error")
        print(f"Result: {trades_df['side_value'].tolist()}")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print(f"Error type: {type(e)}")
        
        # Try alternative approaches
        print("\n🔧 Trying alternative approaches...")
        
        # Approach 1: Using apply
        try:
            print("1. Using apply instead of map:")
            trades_df['side_value_v1'] = trades_df['side'].apply(lambda x: 1 if str(x).lower() == 'buy' else -1)
            print("   ✅ Apply worked!")
        except Exception as e1:
            print(f"   ❌ Apply failed: {e1}")
        
        # Approach 2: Using numpy where
        try:
            print("2. Using numpy where:")
            trades_df['side_value_v2'] = np.where(trades_df['side'].str.lower() == 'buy', 1, -1)
            print("   ✅ Numpy where worked!")
        except Exception as e2:
            print(f"   ❌ Numpy where failed: {e2}")
        
        # Approach 3: Using list comprehension
        try:
            print("3. Using list comprehension:")
            trades_df['side_value_v3'] = [1 if str(x).lower() == 'buy' else -1 for x in trades_df['side']]
            print("   ✅ List comprehension worked!")
        except Exception as e3:
            print(f"   ❌ List comprehension failed: {e3}")
    
    print("\nFinal DataFrame:")
    print(trades_df)

if __name__ == "__main__":
    test_dataframe_ambiguity() 