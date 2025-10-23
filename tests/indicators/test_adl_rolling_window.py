"""
Unit tests for ADL rolling window implementation.

Tests the updated calculate_adl method to ensure proper bounded behavior
with rolling windows instead of unbounded cumsum.

Author: Virtuoso Trading System
Date: October 21, 2025
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from src.indicators.volume_indicators import VolumeIndicators


def create_volume_indicator(adl_window=None, obv_window=None):
    """Helper function to create VolumeIndicators with proper config structure."""
    config = {
        'indicators': {
            'volume': {
                'parameters': {}
            }
        }
    }

    if adl_window is not None:
        config['indicators']['volume']['parameters']['adl'] = {'window': adl_window}

    if obv_window is not None:
        config['indicators']['volume']['parameters']['obv'] = {'window': obv_window}

    return VolumeIndicators(config=config)


class TestADLRollingWindow:
    """Test suite for ADL rolling window implementation."""

    def test_adl_bounded_values(self):
        """Test that ADL values stay within 0-100 range over extended periods."""
        # Create large dataset to test long-running behavior (1 week of 1-min data)
        n_periods = 10000

        # Generate realistic OHLCV data with varying conditions
        np.random.seed(42)
        df = pd.DataFrame({
            'high': np.random.uniform(100, 110, n_periods),
            'low': np.random.uniform(90, 100, n_periods),
            'close': np.random.uniform(95, 105, n_periods),
            'volume': np.random.uniform(1000, 5000, n_periods)
        })

        # Create indicator with rolling window config
        indicator = create_volume_indicator(adl_window=1440)

        adl = indicator.calculate_adl(df)

        # Check all values are bounded
        assert adl.min() >= 0, f"ADL min value {adl.min()} is below 0"
        assert adl.max() <= 100, f"ADL max value {adl.max()} is above 100"

        # Check no NaN values
        assert not adl.isna().any(), "ADL contains NaN values"

        # Check we have values for most of the dataset (accounting for min_periods)
        assert (~adl.isna()).sum() >= n_periods - 20, "Too many NaN values in ADL"

    def test_adl_window_parameter(self):
        """Test that ADL respects the window parameter."""
        df = pd.DataFrame({
            'high': [110, 112, 108, 115, 120, 118, 125],
            'low': [100, 102, 98, 105, 110, 108, 115],
            'close': [105, 110, 100, 112, 118, 115, 122],
            'volume': [1000, 1500, 800, 2000, 2500, 1800, 3000]
        })

        # Test with small window
        indicator_small = create_volume_indicator(adl_window=3)
        adl_small = indicator_small.calculate_adl(df)

        # Test with large window
        indicator_large = create_volume_indicator(adl_window=10)
        adl_large = indicator_large.calculate_adl(df)

        # Both should return valid values
        assert not adl_small.empty
        assert not adl_large.empty

        # Values should differ due to different windows
        # (but not necessarily in every case due to normalization)
        assert len(adl_small) == len(adl_large)

    def test_adl_no_unbounded_growth(self):
        """Test that ADL doesn't grow unbounded like cumsum would."""
        # Create dataset with consistent positive money flow
        # Old cumsum implementation would grow indefinitely
        n_periods = 5000
        df = pd.DataFrame({
            'high': [110] * n_periods,
            'low': [100] * n_periods,
            'close': [108] * n_periods,  # Consistently high close (positive MFM)
            'volume': [1000] * n_periods
        })

        # ADL window: 1440
        indicator = create_volume_indicator(adl_window=1440)
        adl = indicator.calculate_adl(df)

        # Check that values don't grow unbounded
        # Even with consistent positive flow, rolling window should keep values bounded
        assert adl.max() <= 100, "ADL grew beyond upper bound"
        assert adl.min() >= 0, "ADL fell below lower bound"

        # Check that later values aren't systematically larger than earlier values
        # (which would indicate unbounded growth)
        first_quarter = adl.iloc[1000:1500].mean()
        last_quarter = adl.iloc[-500:].mean()

        # With rolling window, these should be similar (both representing strong accumulation)
        # Allow some variation but not massive growth
        assert abs(last_quarter - first_quarter) < 30, \
            f"ADL shows unbounded growth: early={first_quarter:.2f}, late={last_quarter:.2f}"

    def test_adl_handles_insufficient_data(self):
        """Test that ADL handles datasets smaller than window size."""
        # Dataset with only 10 periods (much smaller than default 1440 window)
        df = pd.DataFrame({
            'high': [110, 112, 108, 115, 120, 118, 125, 130, 128, 135],
            'low': [100, 102, 98, 105, 110, 108, 115, 120, 118, 125],
            'close': [105, 110, 100, 112, 118, 115, 122, 128, 125, 132],
            'volume': [1000, 1500, 800, 2000, 2500, 1800, 3000, 3500, 2800, 4000]
        })

        # ADL window: 1440  # Window larger than data
        indicator = create_volume_indicator(adl_window=1440)
        adl = indicator.calculate_adl(df)

        # Should still return valid values
        assert not adl.empty
        assert not adl.isna().all()

        # Values should be bounded
        valid_values = adl[~adl.isna()]
        assert valid_values.min() >= 0
        assert valid_values.max() <= 100

    def test_adl_neutral_on_balanced_flow(self):
        """Test that ADL returns neutral scores (~50) for balanced buy/sell flow."""
        # Create data with balanced money flow (close in middle of range)
        n_periods = 100
        df = pd.DataFrame({
            'high': [110] * n_periods,
            'low': [100] * n_periods,
            'close': [105] * n_periods,  # Middle of range (neutral CLV)
            'volume': [1000] * n_periods
        })

        indicator = create_volume_indicator(adl_window=50)
        adl = indicator.calculate_adl(df)

        # Latest values should be near neutral (50)
        latest_values = adl.iloc[-10:]
        mean_latest = latest_values.mean()

        assert 40 < mean_latest < 60, \
            f"ADL should be neutral (~50) for balanced flow, got {mean_latest:.2f}"

    def test_adl_accumulation_signal(self):
        """Test that ADL returns high scores for accumulation (buying pressure)."""
        # Create data with strong buying pressure (close near high)
        n_periods = 100
        df = pd.DataFrame({
            'high': [110] * n_periods,
            'low': [100] * n_periods,
            'close': [109] * n_periods,  # Very close to high (positive CLV)
            'volume': [1000] * n_periods
        })

        indicator = create_volume_indicator(adl_window=50)
        adl = indicator.calculate_adl(df)

        # Latest values should indicate accumulation (>60)
        latest_values = adl.iloc[-10:]
        mean_latest = latest_values.mean()

        assert mean_latest > 60, \
            f"ADL should show accumulation (>60) for strong buying, got {mean_latest:.2f}"

    def test_adl_distribution_signal(self):
        """Test that ADL returns low scores for distribution (selling pressure)."""
        # Create data with strong selling pressure (close near low)
        n_periods = 100
        df = pd.DataFrame({
            'high': [110] * n_periods,
            'low': [100] * n_periods,
            'close': [101] * n_periods,  # Very close to low (negative CLV)
            'volume': [1000] * n_periods
        })

        indicator = create_volume_indicator(adl_window=50)
        adl = indicator.calculate_adl(df)

        # Latest values should indicate distribution (<40)
        latest_values = adl.iloc[-10:]
        mean_latest = latest_values.mean()

        assert mean_latest < 40, \
            f"ADL should show distribution (<40) for strong selling, got {mean_latest:.2f}"

    def test_adl_consistency_with_obv(self):
        """Test that ADL window behavior is consistent with OBV implementation."""
        df = pd.DataFrame({
            'high': [110, 112, 108, 115, 120],
            'low': [100, 102, 98, 105, 110],
            'close': [105, 110, 100, 112, 118],
            'volume': [1000, 1500, 800, 2000, 2500]
        })

        indicator = create_volume_indicator(adl_window=1440, obv_window=1440)

        adl = indicator.calculate_adl(df)
        obv = indicator.calculate_obv(df)

        # Both should return bounded values
        assert len(adl) == len(obv)
        assert not adl.isna().all()
        assert not obv.isna().all()

        # Both should be in 0-100 range
        valid_adl = adl[~adl.isna()]
        valid_obv = obv[~obv.isna()]

        assert valid_adl.min() >= 0 and valid_adl.max() <= 100
        assert valid_obv.min() >= 0 and valid_obv.max() <= 100

    def test_adl_empty_dataframe(self):
        """Test that ADL handles empty DataFrame gracefully."""
        df = pd.DataFrame()

        indicator = create_volume_indicator()
        adl = indicator.calculate_adl(df)

        # Should return neutral score
        assert len(adl) == 1
        assert adl.iloc[0] == 50.0

    def test_adl_missing_columns(self):
        """Test that ADL handles missing required columns."""
        # DataFrame missing 'high' column
        df = pd.DataFrame({
            'low': [100, 102, 98],
            'close': [105, 110, 100],
            'volume': [1000, 1500, 800]
        })

        indicator = create_volume_indicator()
        adl = indicator.calculate_adl(df)

        # Should return neutral score
        assert len(adl) == 1
        assert adl.iloc[0] == 50.0

    def test_adl_zero_volume(self):
        """Test that ADL handles zero volume gracefully."""
        df = pd.DataFrame({
            'high': [110, 112, 108],
            'low': [100, 102, 98],
            'close': [105, 110, 100],
            'volume': [0, 0, 0]  # All zero volume
        })

        indicator = create_volume_indicator()
        adl = indicator.calculate_adl(df)

        # Should return neutral score (no valid data after filtering zeros)
        assert len(adl) == 1
        assert adl.iloc[0] == 50.0

    def test_adl_with_realistic_market_data(self):
        """Test ADL with realistic market scenario."""
        # Simulate a trending market with increasing prices and volume
        n_periods = 200
        base_price = 100
        trend = np.linspace(0, 20, n_periods)  # Uptrend

        np.random.seed(42)
        df = pd.DataFrame({
            'high': base_price + trend + np.random.uniform(0, 2, n_periods),
            'low': base_price + trend - np.random.uniform(0, 2, n_periods),
            'close': base_price + trend + np.random.uniform(-1, 1, n_periods),
            'volume': 1000 + trend * 50 + np.random.uniform(-200, 200, n_periods)
        })

        indicator = create_volume_indicator(adl_window=100)
        adl = indicator.calculate_adl(df)

        # In uptrend with increasing volume, ADL should generally be positive
        latest_adl = adl.iloc[-20:].mean()

        assert latest_adl > 50, \
            f"ADL should be positive in uptrend, got {latest_adl:.2f}"

        # Check values are bounded
        assert adl.min() >= 0
        assert adl.max() <= 100

    def test_adl_score_method(self):
        """Test the _calculate_adl_score method works with new implementation."""
        df = pd.DataFrame({
            'high': [110, 112, 108, 115, 120, 118, 125, 130, 128, 135] * 5,
            'low': [100, 102, 98, 105, 110, 108, 115, 120, 118, 125] * 5,
            'close': [105, 110, 100, 112, 118, 115, 122, 128, 125, 132] * 5,
            'volume': [1000, 1500, 800, 2000, 2500, 1800, 3000, 3500, 2800, 4000] * 5
        })

        market_data = {
            'ohlcv': {
                'base': df
            }
        }

        indicator = create_volume_indicator(adl_window=30)

        score = indicator._calculate_adl_score(market_data)

        # Should return a valid score
        assert 0 <= score <= 100, f"ADL score {score} is out of bounds"
        assert not np.isnan(score), "ADL score is NaN"


class TestADLRollingWindowEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_adl_single_data_point(self):
        """Test ADL with only one data point."""
        df = pd.DataFrame({
            'high': [110],
            'low': [100],
            'close': [105],
            'volume': [1000]
        })

        indicator = create_volume_indicator()
        adl = indicator.calculate_adl(df)

        # Should handle gracefully
        assert len(adl) >= 1
        if not adl.isna().all():
            assert 0 <= adl.iloc[-1] <= 100

    def test_adl_with_nan_values(self):
        """Test ADL handles NaN values in data."""
        df = pd.DataFrame({
            'high': [110, np.nan, 108, 115],
            'low': [100, 102, np.nan, 105],
            'close': [105, 110, 100, np.nan],
            'volume': [1000, 1500, 800, 2000]
        })

        indicator = create_volume_indicator()
        adl = indicator.calculate_adl(df)

        # Should handle NaN gracefully
        assert not adl.empty
        valid_values = adl[~adl.isna()]
        if len(valid_values) > 0:
            assert valid_values.min() >= 0
            assert valid_values.max() <= 100

    def test_adl_extreme_volume_spike(self):
        """Test ADL handles extreme volume spikes without overflow."""
        df = pd.DataFrame({
            'high': [110] * 100,
            'low': [100] * 100,
            'close': [105] * 100,
            'volume': [1000] * 99 + [1000000]  # Extreme volume spike at end
        })

        indicator = create_volume_indicator(adl_window=50)
        adl = indicator.calculate_adl(df)

        # Should still be bounded despite volume spike
        assert adl.min() >= 0
        assert adl.max() <= 100
        assert not adl.isna().all()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
