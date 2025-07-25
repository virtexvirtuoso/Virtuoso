#!/usr/bin/env python3
"""
Integration test to ensure Phase 0 fixes don't break normal functionality.
"""

import asyncio
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indicators.volume_indicators import VolumeIndicators
from src.config.manager import ConfigManager

async def test_basic_integration():
    """Quick smoke test for integration."""
    print("🧪 Running Phase 0 Integration Test...")
    
    config = ConfigManager()._config
    indicator = VolumeIndicators(config)
    
    # Create realistic test data
    n_samples = 100
    dates = pd.date_range('2025-01-01', periods=n_samples, freq='1min')
    
    # Create base dataframe
    base_df = pd.DataFrame({
        'open': np.random.uniform(100, 101, n_samples),
        'high': np.random.uniform(101, 102, n_samples),
        'low': np.random.uniform(99, 100, n_samples),
        'close': np.random.uniform(100, 101, n_samples),
        'volume': np.random.uniform(1000, 10000, n_samples)
    }, index=dates)
    
    # Test with valid data - provide all required timeframes
    valid_data = {
        'ohlcv': {
            'base': base_df.copy(),
            'ltf': base_df.copy(),
            'mtf': base_df.copy(),
            'htf': base_df.copy()
        },
        'trades': []  # Add required field
    }
    
    # Ensure realistic OHLC relationships
    for tf in valid_data['ohlcv'].values():
        tf['high'] = np.maximum(tf['high'], tf[['open', 'close']].max(axis=1))
        tf['low'] = np.minimum(tf['low'], tf[['open', 'close']].min(axis=1))
    
    try:
        result = await indicator.calculate(valid_data)
        
        # Debug: print result structure
        print(f"Result keys: {list(result.keys())}")
        
        # Verify valid result (check if we got a score, not an error)
        assert 'score' in result, "Missing score in result"
        assert 0 <= result['score'] <= 100, f"Score {result['score']} out of bounds"
        assert 'components' in result, "Missing components"
        assert len(result['components']) > 0, "No components calculated"
        
        # Check it's not an error result
        assert result['score'] != 50.0 or result.get('metadata', {}).get('status') != 'ERROR', "Got error result"
        
        print("✅ Basic calculation test passed")
        print(f"   Score: {result['score']:.2f}")
        print(f"   Components: {len(result['components'])}")
        
        # Test get_signals method
        signals = await indicator.get_signals(valid_data)
        # Check that we got volume-related signals
        assert len(signals) > 0, "No signals returned"
        assert any(key in signals for key in ['relative_volume', 'volume_sma', 'volume_trend', 'volume_profile', 'score', 'signals']), f"Unexpected signal structure, got keys: {list(signals.keys())}"
        print("✅ get_signals test passed")
        
        # Successfully tested main functionality
        print("✅ All main functionality tests passed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test edge cases still work
    edge_cases = [
        {
            'name': 'Single timeframe only',
            'data': {
                'ohlcv': {
                    'base': valid_data['ohlcv']['base']
                },
                'trades': []
            }
        },
        {
            'name': 'Small data sample',
            'data': {
                'ohlcv': {
                    'base': valid_data['ohlcv']['base'].iloc[-20:]  # Only 20 samples
                },
                'trades': []
            }
        }
    ]
    
    for case in edge_cases:
        try:
            result = await indicator.calculate(case['data'])
            assert 'score' in result, f"{case['name']}: Missing score in result"
            assert 0 <= result['score'] <= 100, f"{case['name']}: Score out of bounds"
            print(f"✅ {case['name']} test passed")
        except Exception as e:
            print(f"❌ {case['name']} test failed: {e}")
            return False
    
    print("\n🎉 All integration tests passed!")
    print("   Phase 0 fixes are working correctly without breaking functionality.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_basic_integration())
    sys.exit(0 if success else 1)