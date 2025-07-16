#!/usr/bin/env python3
"""
Integration test for BOS/CHoCH scoring fix.
Tests the actual price structure indicators BOS/CHoCH functionality.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.logger import Logger

def create_test_ohlcv_data(num_candles: int = 200) -> pd.DataFrame:
    """Create realistic OHLCV test data."""
    np.random.seed(42)
    
    # Start with base price
    base_price = 50000.0
    
    # Generate price movements
    returns = np.random.normal(0, 0.02, num_candles)  # 2% volatility
    prices = [base_price]
    
    for ret in returns:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    # Create OHLCV data
    data = []
    for i in range(num_candles):
        close = prices[i+1]
        open_price = prices[i]
        
        # Create realistic high/low
        high = max(open_price, close) * (1 + np.random.uniform(0, 0.01))
        low = min(open_price, close) * (1 - np.random.uniform(0, 0.01))
        
        # Volume
        volume = np.random.uniform(100, 1000)
        
        # Timestamp
        timestamp = datetime.now() - timedelta(minutes=num_candles-i)
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

def test_bos_choch_scoring_directly():
    """Test BOS/CHoCH scoring function directly."""
    print("Direct BOS/CHoCH Scoring Test")
    print("=" * 50)
    
    # Import the specific functions we need to test
    try:
        from src.indicators.price_structure_indicators import PriceStructureIndicators
        
        # Create a minimal config
        config = {
            'analysis': {
                'indicators': {
                    'price_structure': {
                        'weights': {
                                                    'support_resistance': 0.15,
                        'order_block': 0.15,
                        'trend_position': 0.15,
                        'swing_structure': 0.15,
                        'composite_value': 0.15,
                        'volume_profile': 0.15,
                            'fair_value_gaps': 0.10,
                            'liquidity_zones': 0.10,
                            'bos_choch': 0.05
                        }
                    }
                }
            }
        }
        
        logger = Logger('test_bos_choch')
        psi = PriceStructureIndicators(config, logger)
        
        print("✓ Price structure indicators initialized")
        
        # Test the specific BOS/CHoCH scoring function that was broken
        print(f"\n1. Testing BOS/CHoCH scoring with various data...")
        
        # Test case 1: Normal data
        test_data_1 = {
            'bos': [
                {'type': 'bullish', 'break_index': 100, 'strength': 75.0},
                {'type': 'bearish', 'break_index': 150, 'strength': 60.0},
                {'type': 'bullish', 'break_index': 200, 'strength': 80.0},
            ],
            'choch': [
                {'type': 'bearish', 'break_index': 120, 'strength': 65.0},
                {'type': 'bullish', 'break_index': 180, 'strength': 70.0},
            ]
        }
        
        try:
            score_1 = psi._score_bos_choch(test_data_1)
            print(f"   ✓ Normal data score: {score_1:.2f}")
        except Exception as e:
            print(f"   ❌ Normal data failed: {str(e)}")
            return False
        
        # Test case 2: Empty data
        test_data_2 = {'bos': [], 'choch': []}
        try:
            score_2 = psi._score_bos_choch(test_data_2)
            print(f"   ✓ Empty data score: {score_2:.2f}")
        except Exception as e:
            print(f"   ❌ Empty data failed: {str(e)}")
            return False
        
        # Test case 3: Large dataset (>20 events)
        test_data_3 = {
            'bos': [{'type': 'bullish', 'break_index': i*10, 'strength': 50.0} for i in range(25)],
            'choch': [{'type': 'bearish', 'break_index': i*10+5, 'strength': 40.0} for i in range(15)]
        }
        try:
            score_3 = psi._score_bos_choch(test_data_3)
            print(f"   ✓ Large dataset score: {score_3:.2f}")
        except Exception as e:
            print(f"   ❌ Large dataset failed: {str(e)}")
            return False
        
        # Test case 4: Single event
        test_data_4 = {
            'bos': [{'type': 'bullish', 'break_index': 100, 'strength': 75.0}],
            'choch': []
        }
        try:
            score_4 = psi._score_bos_choch(test_data_4)
            print(f"   ✓ Single event score: {score_4:.2f}")
        except Exception as e:
            print(f"   ❌ Single event failed: {str(e)}")
            return False
        
        print(f"\n2. Testing with realistic OHLCV data...")
        
        # Create test data and try the full calculation
        base_df = create_test_ohlcv_data(100)
        ohlcv_data = {
            'base': base_df,
            'ltf': base_df.iloc[::2].copy(),
            'mtf': base_df.iloc[::5].copy(),
            'htf': base_df.iloc[::10].copy()
        }
        
        try:
            full_score = psi._calculate_bos_choch_score(ohlcv_data)
            print(f"   ✓ Full BOS/CHoCH calculation: {full_score:.2f}")
        except Exception as e:
            print(f"   ❌ Full calculation failed: {str(e)}")
            return False
        
        print(f"\n✅ All BOS/CHoCH scoring tests passed!")
        print(f"✅ The original 'cannot access local variable event' error has been fixed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bos_choch_scoring_directly()
    if success:
        print(f"\n🎉 BOS/CHoCH fix verification completed successfully!")
        print(f"🎯 The error 'cannot access local variable event where it is not associated with a value' is resolved!")
    else:
        print(f"\n💥 BOS/CHoCH fix verification failed!")
        sys.exit(1) 