"""
Unit Tests for Signal Normalization Utilities

Tests cover:
- Rolling z-score normalization
- Batch normalization
- Multi-indicator management
- Edge cases and error handling
- Numerical stability
"""

import pytest
import numpy as np
from src.utils.normalization import (
    RollingNormalizer,
    BatchNormalizer,
    MultiIndicatorNormalizer,
    NormalizationConfig,
    NormalizationMethod,
    normalize_signal,
    normalize_array,
    create_default_normalizers
)


class TestRollingNormalizer:
    """Test suite for RollingNormalizer class."""

    def test_initialization(self):
        """Test normalizer initialization with valid parameters."""
        normalizer = RollingNormalizer(lookback=100, min_samples=20)
        assert normalizer.lookback == 100
        assert normalizer.min_samples == 20
        assert normalizer.sample_count == 0
        assert not normalizer.is_ready

    def test_initialization_invalid_params(self):
        """Test that invalid parameters raise ValueError."""
        with pytest.raises(ValueError):
            RollingNormalizer(lookback=10, min_samples=20)  # lookback < min_samples

    def test_single_update(self):
        """Test updating with single value."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)
        normalizer.update(10.0)
        assert normalizer.sample_count == 1
        assert normalizer.mean == 10.0

    def test_multiple_updates(self):
        """Test updating with multiple values."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)
        values = [10.0, 20.0, 30.0, 40.0, 50.0]

        for val in values:
            normalizer.update(val)

        assert normalizer.sample_count == 5
        assert normalizer.is_ready
        np.testing.assert_almost_equal(normalizer.mean, 30.0)

    def test_normalize_insufficient_samples(self):
        """Test normalization returns 0 with insufficient samples."""
        normalizer = RollingNormalizer(lookback=100, min_samples=20)

        # Add only 10 samples (less than min_samples=20)
        for i in range(10):
            normalizer.update(float(i))

        result = normalizer.normalize(5.0)
        assert result == 0.0

    def test_normalize_zero_variance(self):
        """Test normalization with zero variance data."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)

        # All same values
        for _ in range(10):
            normalizer.update(42.0)

        result = normalizer.normalize(42.0)
        assert result == 0.0

    def test_normalize_known_distribution(self):
        """Test normalization with known normal distribution."""
        normalizer = RollingNormalizer(lookback=100, min_samples=20)

        # Generate standard normal distribution
        np.random.seed(42)
        values = np.random.normal(0, 1, 100)

        for val in values:
            normalizer.update(val)

        # Mean should be close to 0, std close to 1
        assert abs(normalizer.mean) < 0.3
        assert abs(normalizer.std - 1.0) < 0.3

        # Normalize a value 2 std above mean
        z_score = normalizer.normalize(normalizer.mean + 2 * normalizer.std)
        np.testing.assert_almost_equal(z_score, 2.0, decimal=1)

    def test_winsorization(self):
        """Test that extreme values are winsorized."""
        normalizer = RollingNormalizer(
            lookback=100,
            min_samples=20,
            winsorize_threshold=3.0
        )

        # Normal distribution
        np.random.seed(42)
        values = np.random.normal(0, 1, 50)
        for val in values:
            normalizer.update(val)

        # Extreme outlier (10 standard deviations)
        extreme_value = normalizer.mean + 10 * normalizer.std
        z_score = normalizer.normalize(extreme_value)

        # Should be clipped to +3.0
        assert z_score == 3.0

    def test_rolling_window_overflow(self):
        """Test that rolling window correctly handles overflow."""
        normalizer = RollingNormalizer(lookback=10, min_samples=5)

        # Add 20 values (2x the window size)
        for i in range(20):
            normalizer.update(float(i))

        # Window should only contain last 10 values
        assert len(normalizer.values) == 10
        assert normalizer.values[-1] == 19.0
        assert normalizer.values[0] == 10.0

        # Mean should be around 14.5 (average of 10-19)
        np.testing.assert_almost_equal(normalizer.mean, 14.5, decimal=1)

    def test_reset(self):
        """Test normalizer reset functionality."""
        normalizer = RollingNormalizer(lookback=100, min_samples=20)

        # Add data
        for i in range(30):
            normalizer.update(float(i))

        assert normalizer.sample_count == 30
        assert normalizer.is_ready

        # Reset
        normalizer.reset()

        assert normalizer.sample_count == 0
        assert not normalizer.is_ready
        assert normalizer.mean == 0.0
        assert normalizer.std == 0.0

    def test_welford_algorithm_stability(self):
        """Test numerical stability of Welford's algorithm."""
        normalizer = RollingNormalizer(lookback=1000, min_samples=20)

        # Large values that could cause numerical instability
        large_values = [1e10 + i for i in range(100)]

        for val in large_values:
            normalizer.update(val)

        # Should still compute reasonable statistics
        assert np.isfinite(normalizer.mean)
        assert np.isfinite(normalizer.std)
        assert normalizer.std > 0


class TestBatchNormalizer:
    """Test suite for BatchNormalizer class."""

    def test_normalize_short_array(self):
        """Test batch normalization with insufficient data."""
        values = np.array([1.0, 2.0, 3.0])
        result = BatchNormalizer.normalize(values, min_samples=20)

        # Should return zeros for insufficient data
        np.testing.assert_array_equal(result, np.zeros(3))

    def test_normalize_standard_distribution(self):
        """Test batch normalization with known distribution."""
        np.random.seed(42)
        values = np.random.normal(100, 15, 200)

        result = BatchNormalizer.normalize(
            values,
            lookback=100,
            min_samples=20
        )

        # Most z-scores should be within [-3, 3]
        assert np.abs(result).max() <= 3.0

        # Mean of z-scores should be close to 0
        assert abs(np.mean(result[50:])) < 0.3  # Exclude initial values

    def test_normalize_with_lookback(self):
        """Test rolling behavior with specified lookback."""
        # Trend: 0-99, then sudden jump to 200-299
        values = np.concatenate([
            np.arange(100),
            np.arange(200, 300)
        ])

        result = BatchNormalizer.normalize(
            values,
            lookback=50,
            min_samples=20
        )

        # After the jump, z-scores should be high (outliers)
        # Then normalize as the new range becomes the window
        assert result[100] > 2.0  # First value after jump
        assert abs(result[-1]) < 2.0  # Later values normalized to new range


class TestMultiIndicatorNormalizer:
    """Test suite for MultiIndicatorNormalizer class."""

    def test_register_indicator(self):
        """Test indicator registration."""
        normalizer = MultiIndicatorNormalizer()
        config = NormalizationConfig(lookback=100)

        normalizer.register_indicator('test_indicator', config)

        assert 'test_indicator' in normalizer.configs
        assert 'test_indicator' in normalizer.normalizers

    def test_update_and_normalize(self):
        """Test update and normalization workflow."""
        normalizer = MultiIndicatorNormalizer()
        config = NormalizationConfig(lookback=100, min_samples=5)
        normalizer.register_indicator('cvd', config)

        # Add samples
        for i in range(10):
            normalizer.update('cvd', float(i * 10))

        # Normalize
        result = normalizer.normalize('cvd', 50.0)

        # Should return a valid z-score
        assert isinstance(result, float)
        assert -3.0 <= result <= 3.0

    def test_unregistered_indicator_raises_error(self):
        """Test that normalizing unregistered indicator raises error."""
        normalizer = MultiIndicatorNormalizer()

        with pytest.raises(ValueError, match="not registered"):
            normalizer.normalize('unknown_indicator', 42.0)

    def test_different_normalization_methods(self):
        """Test different normalization methods."""
        normalizer = MultiIndicatorNormalizer()

        # Z-score
        normalizer.register_indicator(
            'zscore_indicator',
            NormalizationConfig(method=NormalizationMethod.ZSCORE, min_samples=5)
        )

        # Tanh
        normalizer.register_indicator(
            'tanh_indicator',
            NormalizationConfig(method=NormalizationMethod.TANH)
        )

        # MinMax
        normalizer.register_indicator(
            'minmax_indicator',
            NormalizationConfig(method=NormalizationMethod.MINMAX)
        )

        # None
        normalizer.register_indicator(
            'none_indicator',
            NormalizationConfig(method=NormalizationMethod.NONE)
        )

        # Add data for z-score indicator
        for i in range(10):
            normalizer.update('zscore_indicator', float(i))

        # Test each method
        zscore_result = normalizer.normalize('zscore_indicator', 5.0)
        tanh_result = normalizer.normalize('tanh_indicator', 1000.0)
        minmax_result = normalizer.normalize('minmax_indicator', 50.0)
        none_result = normalizer.normalize('none_indicator', 42.0)

        assert isinstance(zscore_result, float)
        assert -1.0 <= tanh_result <= 1.0  # Tanh bounds
        assert -1.0 <= minmax_result <= 1.0  # MinMax bounds
        assert none_result == 42.0  # No normalization

    def test_is_ready(self):
        """Test ready status checking."""
        normalizer = MultiIndicatorNormalizer()
        config = NormalizationConfig(lookback=100, min_samples=20)
        normalizer.register_indicator('test', config)

        # Not ready initially
        assert not normalizer.is_ready('test')

        # Add samples
        for i in range(25):
            normalizer.update('test', float(i))

        # Should be ready now
        assert normalizer.is_ready('test')

    def test_get_stats(self):
        """Test statistics retrieval."""
        normalizer = MultiIndicatorNormalizer()
        config = NormalizationConfig(lookback=100, min_samples=5)
        normalizer.register_indicator('test', config)

        # Add data
        for i in range(10):
            normalizer.update('test', float(i))

        stats = normalizer.get_stats('test')

        assert 'mean' in stats
        assert 'std' in stats
        assert 'samples' in stats
        assert 'ready' in stats
        assert stats['samples'] == 10
        assert stats['ready'] is True


class TestNormalizationConfig:
    """Test suite for NormalizationConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = NormalizationConfig()

        assert config.method == NormalizationMethod.ZSCORE
        assert config.lookback == 100
        assert config.min_samples == 20
        assert config.winsorize_threshold == 3.0
        assert config.outlier_removal is False

    def test_accumulative_indicator_config(self):
        """Test config for accumulative indicators."""
        config = NormalizationConfig.for_accumulative_indicator()

        assert config.method == NormalizationMethod.ZSCORE
        assert config.lookback == 200  # Longer for accumulative
        assert config.min_samples == 30

    def test_volatile_indicator_config(self):
        """Test config for volatile indicators."""
        config = NormalizationConfig.for_volatile_indicator()

        assert config.method == NormalizationMethod.ZSCORE
        assert config.lookback == 50  # Shorter for volatile
        assert config.outlier_removal is True


class TestConvenienceFunctions:
    """Test suite for convenience normalization functions."""

    def test_normalize_signal(self):
        """Test quick signal normalization."""
        lookback_data = [10.0, 20.0, 30.0, 40.0, 50.0]
        value = 35.0

        result = normalize_signal(value, lookback_data)

        # Should return a reasonable z-score
        assert isinstance(result, float)
        assert -3.0 <= result <= 3.0

    def test_normalize_signal_insufficient_data(self):
        """Test normalize_signal with insufficient data."""
        lookback_data = [10.0]  # Only 1 sample
        result = normalize_signal(42.0, lookback_data)

        assert result == 0.0

    def test_normalize_array(self):
        """Test array normalization."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = normalize_array(values)

        # Should be standardized (mean ~0, std ~1)
        assert isinstance(result, np.ndarray)
        assert len(result) == 5
        np.testing.assert_almost_equal(np.mean(result), 0.0, decimal=10)
        np.testing.assert_almost_equal(np.std(result, ddof=1), 1.0, decimal=10)

    def test_normalize_array_insufficient_data(self):
        """Test normalize_array with insufficient data."""
        values = [42.0]
        result = normalize_array(values)

        np.testing.assert_array_equal(result, np.zeros(1))


class TestCreateDefaultNormalizers:
    """Test suite for default normalizer factory."""

    def test_create_default_normalizers(self):
        """Test that default normalizers are created correctly."""
        normalizer = create_default_normalizers()

        # Check accumulative indicators
        assert 'cvd' in normalizer.configs
        assert 'obv' in normalizer.configs
        assert 'adl' in normalizer.configs

        # Check volatile indicators
        assert 'volume_delta' in normalizer.configs
        assert 'oi_change' in normalizer.configs

        # Check standard indicators
        assert 'rsi' in normalizer.configs
        assert 'macd' in normalizer.configs

        # Verify configs
        assert normalizer.configs['cvd'].lookback == 200  # Accumulative
        assert normalizer.configs['oi_change'].lookback == 50  # Volatile


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_nan_handling(self):
        """Test handling of NaN values."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)

        # Normal values
        for i in range(10):
            normalizer.update(float(i))

        # Try to normalize NaN
        # Note: This should handle gracefully or raise appropriate error
        result = normalizer.normalize(float('nan'))
        assert np.isnan(result) or result == 0.0

    def test_infinity_handling(self):
        """Test handling of infinite values."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)

        for i in range(10):
            normalizer.update(float(i))

        # Normalize infinity
        result_pos = normalizer.normalize(float('inf'))
        result_neg = normalizer.normalize(float('-inf'))

        # Should be clipped to threshold
        assert result_pos == 3.0
        assert result_neg == -3.0

    def test_very_large_values(self):
        """Test with very large values."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)

        large_values = [1e15 + i for i in range(20)]
        for val in large_values:
            normalizer.update(val)

        result = normalizer.normalize(1e15 + 10)
        assert np.isfinite(result)

    def test_alternating_signs(self):
        """Test with alternating positive/negative values."""
        normalizer = RollingNormalizer(lookback=100, min_samples=5)

        for i in range(20):
            val = 10.0 if i % 2 == 0 else -10.0
            normalizer.update(val)

        # Mean should be near 0
        assert abs(normalizer.mean) < 1.0

        # Normalize a typical value
        result = normalizer.normalize(10.0)
        assert -3.0 <= result <= 3.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
