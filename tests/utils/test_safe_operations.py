"""
Unit Tests for Safe Mathematical Operations (Phase 1 - Week 1 Day 3-4)

Tests cover:
- safe_divide: Division-by-zero protection
- safe_percentage: Percentage calculations
- safe_log: Logarithm protection
- safe_sqrt: Square root protection
- clip_to_range: Value clipping
- ensure_score_range: Score validation

Test categories:
- Basic functionality
- Edge cases (zero, NaN, infinity)
- Array operations
- Custom defaults and epsilon
- Warning logging
"""

import pytest
import numpy as np
from src.utils.safe_operations import (
    safe_divide,
    safe_percentage,
    safe_log,
    safe_sqrt,
    clip_to_range,
    ensure_score_range,
    DEFAULT_EPSILON
)


class TestSafeDivide:
    """Test suite for safe_divide function."""

    def test_normal_division(self):
        """Test normal division operations."""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(100, 4) == 25.0
        assert safe_divide(7, 3) == pytest.approx(2.333, rel=0.01)

    def test_division_by_zero(self):
        """Test division by exact zero returns default."""
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=50.0) == 50.0
        assert np.isnan(safe_divide(10, 0, default=np.nan))

    def test_division_by_near_zero(self):
        """Test division by near-zero values."""
        # Default epsilon is 1e-10
        assert safe_divide(10, 1e-11) == 0.0  # 1e-11 < 1e-10, treated as zero
        assert safe_divide(10, 1e-12) == 0.0  # 1e-12 < 1e-10, treated as zero

        # Custom epsilon
        assert safe_divide(10, 1e-5, epsilon=1e-6) != 0.0  # 1e-5 > 1e-6, safe to divide
        assert safe_divide(10, 1e-7, epsilon=1e-6) == 0.0  # 1e-7 < 1e-6, treated as zero

    def test_nan_inputs(self):
        """Test NaN inputs return default."""
        assert safe_divide(np.nan, 5) == 0.0
        assert safe_divide(10, np.nan) == 0.0
        assert safe_divide(np.nan, np.nan) == 0.0

        # Custom default
        assert safe_divide(np.nan, 5, default=100.0) == 100.0

    def test_infinity_inputs(self):
        """Test infinity inputs return default."""
        assert safe_divide(np.inf, 5) == 0.0
        assert safe_divide(10, np.inf) == 0.0
        assert safe_divide(-np.inf, 5) == 0.0
        assert safe_divide(10, -np.inf) == 0.0

    def test_negative_numbers(self):
        """Test division with negative numbers."""
        assert safe_divide(-10, 2) == -5.0
        assert safe_divide(10, -2) == -5.0
        assert safe_divide(-10, -2) == 5.0

    def test_array_operations(self):
        """Test element-wise array division."""
        numerator = np.array([10, 20, 30])
        denominator = np.array([2, 4, 5])
        result = safe_divide(numerator, denominator)

        np.testing.assert_array_almost_equal(result, [5.0, 5.0, 6.0])

    def test_array_with_zeros(self):
        """Test array division with some zero denominators."""
        numerator = np.array([10, 20, 30])
        denominator = np.array([2, 0, 5])
        result = safe_divide(numerator, denominator, default=99.0)

        assert result[0] == 5.0
        assert result[1] == 99.0  # Division by zero
        assert result[2] == 6.0

    def test_array_with_nan(self):
        """Test array division with NaN values."""
        numerator = np.array([10, np.nan, 30])
        denominator = np.array([2, 4, np.nan])
        result = safe_divide(numerator, denominator, default=-1.0)

        assert result[0] == 5.0
        assert result[1] == -1.0  # NaN numerator
        assert result[2] == -1.0  # NaN denominator


class TestSafePercentage:
    """Test suite for safe_percentage function."""

    def test_normal_percentage(self):
        """Test normal percentage calculations."""
        assert safe_percentage(25, 100) == 25.0
        assert safe_percentage(1, 4) == 25.0
        assert safe_percentage(3, 4) == 75.0

    def test_percentage_of_zero(self):
        """Test percentage when whole is zero."""
        assert safe_percentage(10, 0) == 0.0
        assert safe_percentage(10, 0, default=50.0) == 50.0

    def test_percentage_greater_than_100(self):
        """Test percentage can exceed 100%."""
        assert safe_percentage(150, 100) == 150.0
        assert safe_percentage(200, 100) == 200.0

    def test_percentage_array(self):
        """Test percentage with arrays."""
        parts = np.array([25, 50, 75])
        wholes = np.array([100, 100, 100])
        result = safe_percentage(parts, wholes)

        np.testing.assert_array_almost_equal(result, [25.0, 50.0, 75.0])


class TestSafeLog:
    """Test suite for safe_log function."""

    def test_natural_log(self):
        """Test natural logarithm."""
        assert safe_log(np.e) == pytest.approx(1.0)
        assert safe_log(1) == 0.0
        assert safe_log(np.e ** 2) == pytest.approx(2.0)

    def test_log_base_10(self):
        """Test base-10 logarithm."""
        assert safe_log(10, base=10) == 1.0
        assert safe_log(100, base=10) == 2.0
        assert safe_log(1000, base=10) == 3.0

    def test_log_base_2(self):
        """Test base-2 logarithm."""
        assert safe_log(2, base=2) == 1.0
        assert safe_log(8, base=2) == 3.0
        assert safe_log(16, base=2) == 4.0

    def test_log_of_zero(self):
        """Test log of zero returns default."""
        assert safe_log(0) == 0.0
        assert safe_log(0, default=-np.inf) == -np.inf

    def test_log_of_negative(self):
        """Test log of negative returns default."""
        assert safe_log(-5) == 0.0
        assert safe_log(-100, default=np.nan) != safe_log(-100, default=np.nan)  # NaN != NaN

    def test_log_of_near_zero(self):
        """Test log of near-zero value."""
        assert safe_log(1e-11) == 0.0
        assert safe_log(1e-11, default=100.0) == 100.0

    def test_log_array(self):
        """Test log with arrays."""
        values = np.array([1, 10, 100])
        result = safe_log(values, base=10)

        np.testing.assert_array_almost_equal(result, [0.0, 1.0, 2.0])

    def test_log_array_with_invalid(self):
        """Test log array with invalid values."""
        values = np.array([10, 0, -5, 100])
        result = safe_log(values, base=10, default=-1.0)

        assert result[0] == 1.0
        assert result[1] == -1.0  # Zero
        assert result[2] == -1.0  # Negative
        assert result[3] == 2.0


class TestSafeSqrt:
    """Test suite for safe_sqrt function."""

    def test_normal_sqrt(self):
        """Test normal square root."""
        assert safe_sqrt(4) == 2.0
        assert safe_sqrt(9) == 3.0
        assert safe_sqrt(16) == 4.0
        assert safe_sqrt(0) == 0.0

    def test_sqrt_of_negative(self):
        """Test sqrt of negative returns default."""
        assert safe_sqrt(-4) == 0.0
        assert safe_sqrt(-100, default=np.nan) != safe_sqrt(-100, default=np.nan)

    def test_sqrt_of_near_zero_negative(self):
        """Test sqrt of near-zero negative is clamped to zero."""
        # Very small negative (within epsilon) should be treated as zero
        result = safe_sqrt(-1e-12)
        assert result == 0.0

    def test_sqrt_array(self):
        """Test sqrt with arrays."""
        values = np.array([0, 1, 4, 9, 16])
        result = safe_sqrt(values)

        np.testing.assert_array_almost_equal(result, [0.0, 1.0, 2.0, 3.0, 4.0])

    def test_sqrt_array_with_negative(self):
        """Test sqrt array with negative values."""
        values = np.array([4, -1, 9, -100])
        result = safe_sqrt(values, default=-999.0)

        assert result[0] == 2.0
        assert result[1] == -999.0  # Negative
        assert result[2] == 3.0
        assert result[3] == -999.0  # Negative


class TestClipToRange:
    """Test suite for clip_to_range function."""

    def test_value_within_range(self):
        """Test value already within range."""
        assert clip_to_range(50, 0, 100) == 50
        assert clip_to_range(25.5, 0, 100) == 25.5

    def test_value_below_range(self):
        """Test value below minimum."""
        assert clip_to_range(-10, 0, 100) == 0
        assert clip_to_range(-999, 0, 100) == 0

    def test_value_above_range(self):
        """Test value above maximum."""
        assert clip_to_range(150, 0, 100) == 100
        assert clip_to_range(999, 0, 100) == 100

    def test_nan_clipped_to_min(self):
        """Test NaN is clipped to minimum."""
        assert clip_to_range(np.nan, 0, 100) == 0

    def test_infinity_clipped(self):
        """Test infinity values are clipped."""
        assert clip_to_range(np.inf, 0, 100) == 100
        assert clip_to_range(-np.inf, 0, 100) == 0

    def test_array_clipping(self):
        """Test clipping arrays."""
        values = np.array([-10, 25, 50, 75, 150])
        result = clip_to_range(values, 0, 100)

        np.testing.assert_array_equal(result, [0, 25, 50, 75, 100])

    def test_array_with_invalid_values(self):
        """Test array with NaN and infinity."""
        values = np.array([50, np.nan, 150, -np.inf, np.inf])
        result = clip_to_range(values, 0, 100)

        assert result[0] == 50
        assert result[1] == 0  # NaN -> min
        assert result[2] == 100  # Over max
        assert result[3] == 0  # -inf -> min
        assert result[4] == 100  # +inf -> max


class TestEnsureScoreRange:
    """Test suite for ensure_score_range function."""

    def test_valid_scores(self):
        """Test scores already in 0-100 range."""
        assert ensure_score_range(0) == 0
        assert ensure_score_range(50) == 50
        assert ensure_score_range(100) == 100
        assert ensure_score_range(75.5) == 75.5

    def test_scores_below_zero(self):
        """Test negative scores clipped to 0."""
        assert ensure_score_range(-10) == 0
        assert ensure_score_range(-0.1) == 0

    def test_scores_above_100(self):
        """Test scores over 100 clipped."""
        assert ensure_score_range(150) == 100
        assert ensure_score_range(100.1) == 100

    def test_invalid_scores(self):
        """Test NaN and infinity scores."""
        assert ensure_score_range(np.nan) == 0
        assert ensure_score_range(np.inf) == 100
        assert ensure_score_range(-np.inf) == 0

    def test_score_array(self):
        """Test array of scores."""
        scores = np.array([-10, 0, 50, 100, 150])
        result = ensure_score_range(scores)

        np.testing.assert_array_equal(result, [0, 0, 50, 100, 100])


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_epsilon(self):
        """Test with very small epsilon threshold."""
        # With normal epsilon, 1e-5 / 1e-11 should return default
        assert safe_divide(1e-5, 1e-11) == 0.0

        # With tiny epsilon, it should divide
        result = safe_divide(1e-5, 1e-11, epsilon=1e-20)
        assert result > 0

    def test_very_large_numbers(self):
        """Test operations with very large numbers."""
        large = 1e15
        assert safe_divide(large, 2) == large / 2
        assert safe_divide(large, large) == 1.0

    def test_mixed_scalar_array(self):
        """Test that scalar and array modes return same results."""
        # Scalar mode
        scalar_result = safe_divide(10, 2)

        # Array mode with single element
        array_result = safe_divide(np.array([10]), np.array([2]))

        # Extract scalar from array using item()
        assert scalar_result == array_result.item()

    def test_zero_numerator(self):
        """Test zero numerator with non-zero denominator."""
        assert safe_divide(0, 10) == 0.0
        assert safe_divide(0, -5) == 0.0

    def test_both_near_zero(self):
        """Test when both numerator and denominator are near zero."""
        result = safe_divide(1e-12, 1e-11, default=999.0)
        assert result == 999.0  # Denominator too small

    def test_custom_epsilon_consistency(self):
        """Test epsilon works consistently across functions."""
        custom_eps = 1e-6

        # safe_divide
        assert safe_divide(1, 1e-7, epsilon=custom_eps) == 0.0
        assert safe_divide(1, 1e-5, epsilon=custom_eps) != 0.0

        # safe_log
        assert safe_log(1e-7, epsilon=custom_eps) == 0.0
        assert safe_log(1e-5, epsilon=custom_eps) != 0.0

        # safe_sqrt
        assert safe_sqrt(-1e-7, epsilon=custom_eps) == 0.0


class TestWarningLogging:
    """Test warning logging functionality."""

    def test_divide_warning(self, caplog):
        """Test division warning is logged."""
        with caplog.at_level("WARNING"):
            safe_divide(10, 0, warn=True)
            assert "Near-zero denominator" in caplog.text

    def test_log_warning(self, caplog):
        """Test log warning is logged."""
        with caplog.at_level("WARNING"):
            safe_log(0, warn=True)
            assert "Near-zero value" in caplog.text

    def test_sqrt_warning(self, caplog):
        """Test sqrt warning is logged."""
        with caplog.at_level("WARNING"):
            safe_sqrt(-5, warn=True)
            assert "Negative value" in caplog.text

    def test_clip_warning(self, caplog):
        """Test clip warning is logged."""
        with caplog.at_level("WARNING"):
            clip_to_range(150, 0, 100, warn=True)
            assert "clipped" in caplog.text

    def test_no_warning_when_disabled(self, caplog):
        """Test no warning when warn=False."""
        with caplog.at_level("WARNING"):
            safe_divide(10, 0, warn=False)
            assert len(caplog.records) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
