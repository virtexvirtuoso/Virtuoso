#!/usr/bin/env python3
"""
Critical safety tests for timeframe access harmonization.
These tests verify that the emergency fixes prevent crashes.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.config.manager import ConfigManager

class TestCriticalSafetyFixes:
    """Test suite for critical safety fixes in timeframe access."""
    
    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return ConfigManager().get_config()
    
    @pytest.fixture
    def volume_indicator(self, config):
        """Create volume indicator instance."""
        return VolumeIndicators(config)
    
    @pytest.fixture
    def technical_indicator(self, config):
        """Create technical indicator instance."""
        return TechnicalIndicators(config)
    
    @pytest.fixture
    def price_structure_indicator(self, config):
        """Create price structure indicator instance."""
        return PriceStructureIndicators(config)
    
    def test_empty_ohlcv_crash_fix(self, volume_indicator):
        """Test fix for list(market_data['ohlcv'].keys())[0] crash."""
        # This would crash with IndexError before fix
        market_data = {'ohlcv': {}}  # Empty dictionary
        
        # Should not crash, should return neutral score
        result = volume_indicator.calculate(market_data)
        
        assert result['score'] == 50.0
        assert result['valid'] is False
        assert 'error' in result['metadata'] or 'reason' in result['metadata']
        
    def test_missing_base_keyerror_fix(self, volume_indicator):
        """Test fix for market_data['ohlcv']['base'] KeyError."""
        # This would crash with KeyError before fix
        market_data = {
            'ohlcv': {
                'ltf': pd.DataFrame(),  # Has ltf but missing base
                'mtf': pd.DataFrame()
            }
        }
        
        # Should not crash, should return neutral score
        result = volume_indicator.calculate(market_data)
        
        assert result['score'] == 50.0
        assert result['valid'] is False
    
    def test_none_ohlcv_access(self, volume_indicator):
        """Test handling when ohlcv is None."""
        market_data = {'ohlcv': None}
        
        # Should not crash
        result = volume_indicator.calculate(market_data)
        
        assert result['score'] == 50.0
        assert result['valid'] is False
    
    def test_missing_ohlcv_key_entirely(self, volume_indicator):
        """Test handling when ohlcv key is missing."""
        market_data = {'trades': [], 'orderbook': {}}  # No 'ohlcv' key
        
        # Should not crash
        result = volume_indicator.calculate(market_data)
        
        assert result['score'] == 50.0
        assert result['valid'] is False
        
    def test_real_world_crash_scenario(self, volume_indicator):
        """Test real-world scenario that caused production crashes."""
        # Simulate API returning partial data
        market_data = {
            'ohlcv': {
                'base': pd.DataFrame({
                    'close': [100, 101, 102],
                    'volume': [1000, 2000, 3000]
                    # Missing open, high, low - common API issue
                })
            }
        }
        
        # Should not crash, should return neutral score
        result = volume_indicator.calculate(market_data)
        assert result['score'] == 50.0
        assert result['valid'] is False
    
    def test_string_instead_of_dataframe(self, volume_indicator):
        """Test handling when timeframe contains string instead of DataFrame."""
        market_data = {
            'ohlcv': {
                'base': "not_a_dataframe",
                'ltf': [],
                'mtf': {},
                'htf': 12345
            }
        }
        
        # Should not crash
        result = volume_indicator.calculate(market_data)
        assert result['score'] == 50.0
        assert result['valid'] is False
    
    def test_get_signals_safety(self, volume_indicator):
        """Test get_signals method doesn't crash with missing data."""
        # Test with empty ohlcv
        market_data = {'ohlcv': {}}
        signals = volume_indicator.get_signals(market_data)
        assert 'error' in signals or signals.get('score') == 50.0
        
        # Test with None ohlcv
        market_data = {'ohlcv': None}
        signals = volume_indicator.get_signals(market_data)
        assert 'error' in signals or signals.get('score') == 50.0
    
    def test_volume_rsi_safety(self, volume_indicator):
        """Test volume RSI calculation doesn't crash with missing data."""
        # Test with empty ohlcv
        market_data = {'ohlcv': {}}
        result = volume_indicator.get_volume_rsi_signals(market_data)
        assert 'error' in result or result.get('score') == 50.0
    
    def test_valid_data_still_works(self, volume_indicator):
        """Test that valid data still produces valid results."""
        # Create valid test data
        dates = pd.date_range('2023-01-01', periods=100, freq='1min')
        valid_df = pd.DataFrame({
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 120, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }, index=dates)
        
        market_data = {
            'ohlcv': {
                'base': valid_df,
                'ltf': valid_df,
                'mtf': valid_df,
                'htf': valid_df
            }
        }
        
        # Should produce valid results
        result = volume_indicator.calculate(market_data)
        
        assert result['valid'] is True
        assert 0 <= result['score'] <= 100
        assert 'components' in result
        assert len(result['components']) > 0
    
    def test_cross_module_consistency(self, volume_indicator, technical_indicator, price_structure_indicator):
        """Test that all modules handle missing data consistently."""
        # Test with empty ohlcv
        market_data = {'ohlcv': {}}
        
        volume_result = volume_indicator.calculate(market_data)
        technical_result = technical_indicator.calculate(market_data)
        price_result = price_structure_indicator.calculate(market_data)
        
        # All should return neutral score
        assert volume_result['score'] == 50.0
        assert technical_result['score'] == 50.0
        assert price_result['score'] == 50.0
        
        # All should be invalid
        assert volume_result['valid'] is False
        assert technical_result['valid'] is False
        assert price_result['valid'] is False

async def run_quick_safety_check():
    """Run a quick safety check without pytest."""
    print("🔍 Running quick safety check...")
    
    config = ConfigManager()._config
    volume_indicator = VolumeIndicators(config)
    
    # Test 1: Empty OHLCV
    try:
        market_data = {'ohlcv': {}}
        result = await volume_indicator.calculate(market_data)
        assert result['score'] == 50.0
        print("✅ Empty OHLCV test passed")
    except Exception as e:
        print(f"❌ Empty OHLCV test failed: {e}")
        return False
    
    # Test 2: Missing base
    try:
        market_data = {'ohlcv': {'ltf': pd.DataFrame()}}
        result = await volume_indicator.calculate(market_data)
        assert result['score'] == 50.0
        print("✅ Missing base test passed")
    except Exception as e:
        print(f"❌ Missing base test failed: {e}")
        return False
    
    # Test 3: None OHLCV
    try:
        market_data = {'ohlcv': None}
        result = await volume_indicator.calculate(market_data)
        assert result['score'] == 50.0
        print("✅ None OHLCV test passed")
    except Exception as e:
        print(f"❌ None OHLCV test failed: {e}")
        return False
    
    print("\n🎉 All quick safety checks passed!")
    return True

if __name__ == "__main__":
    # Run quick check if not running through pytest
    if not any('pytest' in arg for arg in sys.argv):
        import asyncio
        success = asyncio.run(run_quick_safety_check())
        sys.exit(0 if success else 1)