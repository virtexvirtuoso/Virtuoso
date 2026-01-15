"""
Unit tests for the Statistical OI Divergence module.

Tests the adaptive statistical methods, confidence scoring, and partial data utilization.
See: docs/07-technical/investigations/OI_DIVERGENCE_COMPREHENSIVE_STATISTICAL_FRAMEWORK.md
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.core.analysis.oi_divergence_stats import (
    OIDivergenceStatsCalculator,
    sample_confidence,
    recency_confidence,
    completeness_confidence,
    significance_confidence,
    calculate_combined_confidence,
    calculate_direction_only,
    calculate_kendall_correlation,
    calculate_rolling_zscore,
    calculate_statistical_divergence,
    DEFAULT_CONFIG,
)


class TestConfidenceScoring:
    """Test confidence scoring functions."""

    def test_sample_confidence_minimal(self):
        """Test confidence for minimal samples."""
        assert sample_confidence(0) == 0.15
        assert sample_confidence(1) == 0.15
        assert sample_confidence(2) == 0.15

    def test_sample_confidence_small(self):
        """Test confidence for small samples (3-5)."""
        assert sample_confidence(3) == 0.25
        assert sample_confidence(4) == pytest.approx(0.28, abs=0.01)
        assert sample_confidence(5) == pytest.approx(0.31, abs=0.01)

    def test_sample_confidence_medium(self):
        """Test confidence for medium samples (6-15)."""
        assert sample_confidence(6) == 0.40
        assert sample_confidence(10) == pytest.approx(0.52, abs=0.01)
        assert sample_confidence(15) == pytest.approx(0.67, abs=0.01)

    def test_sample_confidence_large(self):
        """Test confidence for large samples (16-30)."""
        assert sample_confidence(16) == 0.70
        assert sample_confidence(20) == pytest.approx(0.74, abs=0.01)
        assert sample_confidence(30) == pytest.approx(0.84, abs=0.01)

    def test_sample_confidence_very_large(self):
        """Test confidence approaches 0.95 asymptote."""
        assert sample_confidence(31) == pytest.approx(0.85, abs=0.01)
        assert sample_confidence(50) == pytest.approx(0.907, abs=0.01)
        assert sample_confidence(100) <= 0.95

    def test_recency_confidence_fresh(self):
        """Test confidence for fresh data."""
        assert recency_confidence(0) == 1.0
        assert recency_confidence(0.0) == 1.0

    def test_recency_confidence_decay(self):
        """Test exponential decay of recency confidence."""
        # At half-life (30 min), confidence should be 0.5
        assert recency_confidence(30) == pytest.approx(0.5, abs=0.01)
        # At 15 min, should be ~0.71
        assert recency_confidence(15) == pytest.approx(0.71, abs=0.02)

    def test_recency_confidence_floor(self):
        """Test that recency confidence has a floor at 0.3."""
        assert recency_confidence(60) == pytest.approx(0.3, abs=0.05)
        assert recency_confidence(120) == 0.3
        assert recency_confidence(1000) == 0.3

    def test_completeness_confidence_full(self):
        """Test confidence for complete data."""
        assert completeness_confidence(50, 50) == 1.0
        assert completeness_confidence(100, 100) == 1.0

    def test_completeness_confidence_partial(self):
        """Test confidence for partial data."""
        # 90% complete -> sqrt(0.9) ≈ 0.95
        assert completeness_confidence(50, 45) == pytest.approx(0.95, abs=0.01)
        # 50% complete -> sqrt(0.5) ≈ 0.71
        assert completeness_confidence(50, 25) == pytest.approx(0.71, abs=0.01)

    def test_completeness_confidence_zero_expected(self):
        """Test default for unknown expectation."""
        assert completeness_confidence(0, 10) == 0.5

    def test_significance_confidence_unknown(self):
        """Test confidence for unknown significance."""
        assert significance_confidence(None) == 0.5

    def test_significance_confidence_not_significant(self):
        """Test confidence for non-significant results."""
        assert significance_confidence(0.15) == 0.30
        assert significance_confidence(0.50) == 0.30

    def test_significance_confidence_marginal(self):
        """Test confidence for marginally significant results."""
        assert significance_confidence(0.09) == 0.60
        assert significance_confidence(0.051) == 0.60

    def test_significance_confidence_significant(self):
        """Test confidence for significant results."""
        assert significance_confidence(0.04) == 0.85
        assert significance_confidence(0.02) == 0.85

    def test_significance_confidence_highly_significant(self):
        """Test confidence for highly significant results."""
        assert significance_confidence(0.009) == 0.95
        assert significance_confidence(0.001) == 0.95

    def test_combined_confidence(self):
        """Test combined confidence uses minimum."""
        result = calculate_combined_confidence(
            n=20,
            oldest_age_min=10,
            expected_points=20,
            actual_points=18,
            p_value=0.03
        )
        assert 'overall' in result
        assert 'sample' in result
        assert 'recency' in result
        assert 'completeness' in result
        assert 'significance' in result
        # Overall should be min of components
        assert result['overall'] == min(
            result['sample'],
            result['recency'],
            result['completeness'],
            result['significance']
        )


class TestDirectionOnly:
    """Test direction-only analysis for n < 3."""

    def test_bullish_divergence_direction(self):
        """Test bullish divergence detection (price down, OI up)."""
        price = np.array([-1.0, -2.0])
        oi = np.array([1.0, 2.0])
        result = calculate_direction_only(price, oi)
        assert result['divergence_detected'] == True
        assert result['correlation'] == -1.0
        assert result['method'] == 'direction_only'
        assert result['max_confidence'] == 0.15

    def test_bearish_divergence_direction(self):
        """Test bearish divergence detection (price up, OI down)."""
        price = np.array([1.0, 2.0])
        oi = np.array([-1.0, -2.0])
        result = calculate_direction_only(price, oi)
        assert result['divergence_detected'] == True
        assert result['correlation'] == -1.0

    def test_no_divergence_both_up(self):
        """Test no divergence when both trending up."""
        price = np.array([1.0, 2.0])
        oi = np.array([1.0, 2.0])
        result = calculate_direction_only(price, oi)
        assert result['divergence_detected'] == False
        assert result['correlation'] == 1.0

    def test_no_divergence_both_down(self):
        """Test no divergence when both trending down."""
        price = np.array([-1.0, -2.0])
        oi = np.array([-1.0, -2.0])
        result = calculate_direction_only(price, oi)
        assert result['divergence_detected'] == False


class TestKendallCorrelation:
    """Test Kendall's Tau correlation for small samples."""

    def test_negative_correlation(self):
        """Test detection of negative correlation."""
        price = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        oi = np.array([-1.0, -2.0, -3.0, -4.0, -5.0])
        result = calculate_kendall_correlation(price, oi, divergence_threshold=-0.3)
        assert result['correlation'] < -0.3
        assert result['divergence_detected'] == True
        assert result['method'] == 'kendall_tau'
        assert result['max_confidence'] == 0.40

    def test_positive_correlation(self):
        """Test positive correlation (no divergence)."""
        price = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        oi = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = calculate_kendall_correlation(price, oi, divergence_threshold=-0.3)
        assert result['correlation'] > 0
        assert result['divergence_detected'] == False


class TestRollingZScore:
    """Test rolling z-score calculation."""

    def test_zscore_normal(self):
        """Test z-score for normal data."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        z, mean, std = calculate_rolling_zscore(values)
        assert mean == 3.0
        # Latest value (5) should have positive z-score
        assert z > 0

    def test_zscore_insufficient_data(self):
        """Test z-score with insufficient data."""
        values = np.array([1.0])
        z, mean, std = calculate_rolling_zscore(values)
        assert z == 0.0

    def test_zscore_constant_values(self):
        """Test z-score with constant values (zero std)."""
        values = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        z, mean, std = calculate_rolling_zscore(values)
        assert z == 0.0  # No deviation possible


class TestOIDivergenceStatsCalculator:
    """Test the main calculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator instance."""
        return OIDivergenceStatsCalculator()

    def test_initialization(self, calculator):
        """Test calculator initialization with defaults."""
        assert calculator.config['min_samples'] == 3
        assert calculator.config['zscore_threshold'] == 2.0

    def test_empty_input(self, calculator):
        """Test handling of empty input."""
        result = calculator.calculate([], [])
        assert result['type'] == 'neutral'
        assert result['strength'] == 0.0
        assert 'reason' in result

    def test_length_mismatch(self, calculator):
        """Test handling of length mismatch."""
        result = calculator.calculate([1, 2, 3], [1, 2])
        assert result['type'] == 'neutral'
        assert 'Length mismatch' in result.get('reason', '')

    def test_insufficient_samples(self, calculator):
        """Test handling of insufficient samples."""
        result = calculator.calculate([1, 2], [1, 2])
        assert result['type'] == 'neutral'
        assert 'Insufficient' in result.get('reason', '')

    def test_bullish_divergence(self, calculator):
        """Test bullish divergence detection."""
        # Price trending down, OI trending up
        price_changes = [-1.0, -2.0, -1.5, -2.5, -1.0, -2.0, -1.5]
        oi_changes = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5]
        result = calculator.calculate(price_changes, oi_changes)
        assert result['type'] == 'bullish'
        assert result['strength'] > 0
        assert result['correlation'] < 0

    def test_bearish_divergence(self, calculator):
        """Test bearish divergence detection."""
        # Price trending up, OI trending down
        price_changes = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5]
        oi_changes = [-1.0, -2.0, -1.5, -2.5, -1.0, -2.0, -1.5]
        result = calculator.calculate(price_changes, oi_changes)
        assert result['type'] == 'bearish'
        assert result['strength'] > 0

    def test_no_divergence(self, calculator):
        """Test no divergence when correlated."""
        # Both trending same direction
        price_changes = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5]
        oi_changes = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5]
        result = calculator.calculate(price_changes, oi_changes)
        # Correlation should be positive, so no divergence
        assert result['correlation'] > 0
        assert result['divergence_detected'] == False

    def test_method_selection_small(self, calculator):
        """Test method selection for small samples."""
        price_changes = [1.0, -2.0, 1.5]  # 3 samples
        oi_changes = [-1.0, 2.0, -1.5]
        result = calculator.calculate(price_changes, oi_changes)
        assert result['method'] in ['kendall_tau', 'direction_only']

    def test_method_selection_medium(self, calculator):
        """Test method selection for medium samples."""
        price_changes = [1.0, -2.0, 1.5, -2.0, 1.0, -1.5, 1.0, -2.0]  # 8 samples
        oi_changes = [-1.0, 2.0, -1.5, 2.0, -1.0, 1.5, -1.0, 2.0]
        result = calculator.calculate(price_changes, oi_changes)
        assert result['method'] in ['spearman_bootstrap', 'kendall_tau']

    def test_method_selection_large(self, calculator):
        """Test method selection for large samples."""
        np.random.seed(42)
        # Generate 25 samples with negative correlation
        price_changes = np.cumsum(np.random.randn(25) * 0.1 + 0.05).tolist()
        oi_changes = np.cumsum(np.random.randn(25) * 0.1 - 0.05).tolist()
        result = calculator.calculate(price_changes, oi_changes)
        assert result['method'] in ['spearman_pearson', 'spearman_bootstrap']

    def test_confidence_in_result(self, calculator):
        """Test that confidence is included in result."""
        price_changes = [1.0, -2.0, 1.5, -2.0, 1.0, -1.5, 1.0]
        oi_changes = [-1.0, 2.0, -1.5, 2.0, -1.0, 1.5, -1.0]
        result = calculator.calculate(price_changes, oi_changes)
        assert 'confidence' in result
        assert 'confidence_components' in result
        assert 0 <= result['confidence'] <= 1

    def test_handles_nan_values(self, calculator):
        """Test handling of NaN values in input."""
        price_changes = [1.0, float('nan'), 1.5, 2.0, 1.0, 1.5, 1.0]
        oi_changes = [-1.0, 2.0, -1.5, float('nan'), -1.0, 1.5, -1.0]
        result = calculator.calculate(price_changes, oi_changes)
        # Should still work after filtering NaNs
        assert result['sample_size'] < 7  # Some filtered out

    def test_handles_inf_values(self, calculator):
        """Test handling of Inf values in input."""
        price_changes = [1.0, float('inf'), 1.5, 2.0, 1.0, 1.5, 1.0]
        oi_changes = [-1.0, 2.0, float('-inf'), 2.0, -1.0, 1.5, -1.0]
        result = calculator.calculate(price_changes, oi_changes)
        assert result['sample_size'] < 7

    def test_z_score_in_result(self, calculator):
        """Test that z-score is included in result."""
        price_changes = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5]
        oi_changes = [-1.0, -2.0, -1.5, -2.5, -1.0, -2.0, -1.5]
        result = calculator.calculate(price_changes, oi_changes)
        assert 'z_score' in result
        assert 'z_mean' in result
        assert 'z_std' in result


class TestConvenienceFunction:
    """Test the module-level convenience function."""

    def test_calculate_statistical_divergence(self):
        """Test the convenience function."""
        price_changes = [1.0, -2.0, 1.5, -2.0, 1.0, -1.5]
        oi_changes = [-1.0, 2.0, -1.5, 2.0, -1.0, 1.5]
        result = calculate_statistical_divergence(price_changes, oi_changes)
        assert 'type' in result
        assert 'strength' in result
        assert 'confidence' in result


class TestMinSamplesConfig:
    """Test minimum samples configuration."""

    def test_min_samples_3(self):
        """Test with min_samples=3 (default)."""
        calc = OIDivergenceStatsCalculator({'min_samples': 3})
        result = calc.calculate([1, 2, 3], [1, 2, 3])
        assert result['sample_size'] == 3

    def test_min_samples_5(self):
        """Test with min_samples=5."""
        calc = OIDivergenceStatsCalculator({'min_samples': 5})
        # 3 samples should be rejected
        result = calc.calculate([1, 2, 3], [1, 2, 3])
        assert result['type'] == 'neutral'
        assert 'Insufficient' in result.get('reason', '')
        # 5 samples should work
        result = calc.calculate([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert result['sample_size'] == 5


class TestConfidenceScaling:
    """Test that strength is scaled by confidence."""

    def test_strength_scales_with_confidence(self):
        """Test that effective strength accounts for confidence."""
        calc = OIDivergenceStatsCalculator()
        # Create data with clear divergence
        price_changes = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5]
        oi_changes = [-1.0, -2.0, -1.5, -2.5, -1.0, -2.0, -1.5]
        result = calc.calculate(price_changes, oi_changes)

        # Raw strength should be >= effective strength
        # (effective = raw * confidence, and confidence <= 1)
        assert result['raw_strength'] >= result['strength']
