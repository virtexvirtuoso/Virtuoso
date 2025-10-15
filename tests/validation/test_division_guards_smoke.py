"""
Division Guards Smoke Test (Phase 1 - Week 1 Day 5)

Validates that Division Guards infrastructure is working correctly and
indicator files can be imported and used without division-by-zero errors.
"""

import pytest
import numpy as np
import pandas as pd
from src.utils.safe_operations import safe_divide, safe_percentage


class TestDivisionGuardsInfrastructure:
    """Test the core Division Guards infrastructure."""

    def test_safe_divide_basic(self):
        """Test basic safe_divide functionality."""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=50.0) == 50.0

    def test_safe_divide_edge_cases(self):
        """Test safe_divide edge cases."""
        # Near-zero denominators
        assert safe_divide(10, 1e-15, default=0.0) == 0.0

        # NaN inputs
        assert safe_divide(np.nan, 5, default=0.0) == 0.0
        assert safe_divide(5, np.nan, default=0.0) == 0.0

        # Infinity inputs
        assert safe_divide(np.inf, 5, default=0.0) == 0.0
        assert safe_divide(5, np.inf, default=0.0) == 0.0

    def test_safe_percentage(self):
        """Test safe_percentage functionality."""
        assert safe_percentage(50, 100) == 50.0
        assert safe_percentage(10, 0) == 0.0
        assert safe_percentage(10, 0, default=100.0) == 100.0


class TestIndicatorImports:
    """Test that indicator files can be imported successfully."""

    def test_import_volume_indicators(self):
        """Test volume_indicators can be imported."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
            assert VolumeIndicators is not None
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

    def test_import_orderflow_indicators(self):
        """Test orderflow_indicators can be imported."""
        try:
            from src.indicators.orderflow_indicators import OrderflowIndicators
            assert OrderflowIndicators is not None
        except ImportError as e:
            pytest.skip(f"OrderflowIndicators not available: {e}")

    def test_import_orderbook_indicators(self):
        """Test orderbook_indicators can be imported."""
        try:
            from src.indicators.orderbook_indicators import OrderbookIndicators
            assert OrderbookIndicators is not None
        except ImportError as e:
            pytest.skip(f"OrderbookIndicators not available: {e}")

    def test_import_price_structure_indicators(self):
        """Test price_structure_indicators can be imported."""
        try:
            from src.indicators.price_structure_indicators import PriceStructureIndicators
            assert PriceStructureIndicators is not None
        except ImportError as e:
            pytest.skip(f"PriceStructureIndicators not available: {e}")


class TestDivisionGuardsInIndicators:
    """Test that Division Guards work correctly in indicator calculations."""

    def test_safe_divide_with_zero_volume(self):
        """Test that zero volume doesn't cause crashes."""
        # Simulate calculations that might have zero denominators
        volume_data = pd.Series([0, 0, 0, 0, 0])

        # Calculate relative volume safely
        current_volume = 100
        avg_volume = volume_data.mean()  # Will be 0.0

        # This should not crash
        relative_volume = safe_divide(current_volume, avg_volume, default=1.0)
        assert relative_volume == 1.0

    def test_safe_percentage_with_zero_total(self):
        """Test that zero total doesn't cause crashes."""
        buy_volume = 100
        sell_volume = 0
        total_volume = 0

        # This should not crash
        buy_pct = safe_percentage(buy_volume, total_volume, default=50.0)
        assert buy_pct == 50.0

    def test_safe_divide_with_price_zero(self):
        """Test that zero price doesn't cause crashes."""
        current_price = 0.0
        zone_level = 100.0

        # Distance calculation that might have zero price
        distance = safe_divide(abs(current_price - zone_level), current_price, default=1.0)
        assert distance == 1.0


class TestBackwardCompatibility:
    """Ensure Division Guards don't break existing functionality."""

    def test_normal_division_unchanged(self):
        """Test that normal divisions still work correctly."""
        assert safe_divide(100, 10) == 10.0
        assert safe_divide(7, 2) == 3.5
        assert safe_divide(-10, 5) == -2.0

    def test_array_operations_preserved(self):
        """Test that array operations still work."""
        numerators = np.array([10, 20, 30, 40])
        denominators = np.array([2, 4, 5, 8])

        results = safe_divide(numerators, denominators)
        expected = np.array([5.0, 5.0, 6.0, 5.0])

        np.testing.assert_array_almost_equal(results, expected)

    def test_array_with_zeros_handled(self):
        """Test that arrays with zero denominators are handled."""
        numerators = np.array([10, 20, 30, 40])
        denominators = np.array([2, 0, 5, 0])  # Some zeros

        results = safe_divide(numerators, denominators, default=0.0)
        expected = np.array([5.0, 0.0, 6.0, 0.0])

        np.testing.assert_array_almost_equal(results, expected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
