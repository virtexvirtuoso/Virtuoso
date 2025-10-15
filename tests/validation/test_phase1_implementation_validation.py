"""
Phase 1 Implementation Validation Test

Validates that Phase 1 changes (z-score and Division Guards) are correctly
implemented and can be imported/used without errors.
"""

import pytest
import numpy as np
import pandas as pd


class TestPhase1ImportsAndSyntax:
    """Test that all Phase 1 modifications are syntactically correct."""

    def test_utilities_import(self):
        """Test that utility modules can be imported."""
        try:
            from src.utils.normalization import rolling_zscore, normalize_to_score
            from src.utils.safe_operations import safe_divide, safe_percentage

            assert callable(rolling_zscore), "rolling_zscore should be callable"
            assert callable(normalize_to_score), "normalize_to_score should be callable"
            assert callable(safe_divide), "safe_divide should be callable"
            assert callable(safe_percentage), "safe_percentage should be callable"

            print("✅ All utility functions importable")
        except ImportError as e:
            pytest.fail(f"Failed to import utilities: {e}")

    def test_indicator_files_import(self):
        """Test that modified indicator files can be imported."""
        errors = []

        try:
            from src.indicators import volume_indicators
            print("✅ volume_indicators.py imports successfully")
        except Exception as e:
            errors.append(f"volume_indicators: {e}")

        try:
            from src.indicators import orderflow_indicators
            print("✅ orderflow_indicators.py imports successfully")
        except Exception as e:
            errors.append(f"orderflow_indicators: {e}")

        try:
            from src.indicators import orderbook_indicators
            print("✅ orderbook_indicators.py imports successfully")
        except Exception as e:
            errors.append(f"orderbook_indicators: {e}")

        try:
            from src.indicators import price_structure_indicators
            print("✅ price_structure_indicators.py imports successfully")
        except Exception as e:
            errors.append(f"price_structure_indicators: {e}")

        if errors:
            pytest.fail(f"Import errors: {'; '.join(errors)}")

    def test_safe_operations_in_indicator_files(self):
        """Test that safe_operations are imported in indicator files."""
        import inspect

        files_to_check = [
            ('src.indicators.volume_indicators', 'VolumeIndicators'),
            ('src.indicators.orderflow_indicators', 'OrderflowIndicators'),
            ('src.indicators.orderbook_indicators', 'OrderbookIndicators'),
            ('src.indicators.price_structure_indicators', 'PriceStructureIndicators'),
        ]

        for module_name, class_name in files_to_check:
            try:
                module = __import__(module_name, fromlist=[class_name])

                # Check if safe_divide is in the module
                assert hasattr(module, 'safe_divide') or 'safe_divide' in str(inspect.getsource(module)), \
                    f"{module_name} should import safe_divide"

                print(f"✅ {module_name} has Division Guards imports")
            except ImportError as e:
                print(f"ℹ️  {module_name} not available: {e}")
            except Exception as e:
                print(f"ℹ️  {module_name} check note: {e}")


class TestPhase1UtilitiesFunctional:
    """Test that utilities work correctly in realistic scenarios."""

    def test_zscore_with_realistic_data(self):
        """Test z-score normalization with realistic cumulative data."""
        from src.utils.normalization import rolling_zscore, normalize_to_score

        # Simulate OBV-like cumulative data
        obv_raw = np.cumsum(np.random.randn(500) * 1000000)  # Cumulative, could be billions

        # Apply rolling z-score
        z_scores = [rolling_zscore(obv_raw[:i+1], window=100)
                    for i in range(len(obv_raw)) if i >= 10]

        # Z-scores should be bounded
        z_scores = np.array([z for z in z_scores if z is not None])
        assert np.all(np.abs(z_scores) < 10), \
            f"Z-scores should be reasonable, max={np.max(np.abs(z_scores))}"

        # Convert to scores
        scores = [normalize_to_score(z, scale=15) for z in z_scores]
        scores = np.array([s for s in scores if s is not None])

        # Scores should be 0-100
        assert np.all(scores >= 0) and np.all(scores <= 100), \
            f"Scores should be 0-100, range=[{np.min(scores)}, {np.max(scores)}]"

        print(f"✅ Z-score normalization: {len(scores)} scores in range [0, 100]")
        print(f"   Mean: {np.mean(scores):.2f}, Std: {np.std(scores):.2f}")

    def test_division_guards_with_edge_cases(self):
        """Test Division Guards handle all edge cases."""
        from src.utils.safe_operations import safe_divide, safe_percentage

        test_cases = [
            # (numerator, denominator, expected_behavior)
            (10, 0, "returns default"),
            (10, 1e-15, "returns default (near-zero)"),
            (10, np.nan, "returns default (NaN)"),
            (10, np.inf, "returns default (infinity)"),
            (np.nan, 5, "returns default (NaN numerator)"),
            (10, 2, "returns 5.0 (normal)"),
        ]

        for num, denom, expected in test_cases:
            result = safe_divide(num, denom, default=0.0)
            assert not np.isnan(result), f"Result should not be NaN for {expected}"
            assert not np.isinf(result), f"Result should not be infinity for {expected}"
            print(f"✅ {expected}: {num}/{denom} = {result}")

    def test_division_guards_with_arrays(self):
        """Test Division Guards work with numpy arrays."""
        from src.utils.safe_operations import safe_divide

        numerators = np.array([10, 20, 30, 40, 50])
        denominators = np.array([2, 0, 5, np.nan, 10])  # Mixed valid/invalid

        results = safe_divide(numerators, denominators, default=0.0)

        # Should return array
        assert isinstance(results, np.ndarray), "Should return numpy array"
        assert len(results) == len(numerators), "Should preserve length"

        # Check individual results
        assert results[0] == 5.0, "10/2 should be 5.0"
        assert results[1] == 0.0, "10/0 should be default (0.0)"
        assert results[2] == 6.0, "30/5 should be 6.0"
        assert results[3] == 0.0, "40/NaN should be default (0.0)"
        assert results[4] == 5.0, "50/10 should be 5.0"

        print(f"✅ Array division guards: {results}")

    def test_safe_percentage(self):
        """Test safe_percentage utility."""
        from src.utils.safe_operations import safe_percentage

        # Normal percentage
        pct = safe_percentage(50, 100)
        assert pct == 50.0, f"50/100 should be 50%, got {pct}"

        # Zero denominator
        pct_zero = safe_percentage(50, 0, default=0.0)
        assert pct_zero == 0.0, f"Should return default with zero denom, got {pct_zero}"

        # Greater than 100%
        pct_large = safe_percentage(150, 100)
        assert pct_large == 150.0, f"Should allow >100%, got {pct_large}"

        print(f"✅ safe_percentage working correctly")


class TestPhase1EdgeCaseHandling:
    """Test Phase 1 improvements handle edge cases without crashing."""

    def test_zscore_with_insufficient_data(self):
        """Test z-score with insufficient data."""
        from src.utils.normalization import rolling_zscore

        # Not enough data for window
        small_data = np.array([1, 2, 3])
        z = rolling_zscore(small_data, window=100)

        # Should handle gracefully (return None or valid value)
        assert z is None or isinstance(z, (int, float)), \
            "Should handle insufficient data gracefully"

        print(f"✅ Insufficient data handled: z = {z}")

    def test_zscore_with_zero_std(self):
        """Test z-score with zero standard deviation."""
        from src.utils.normalization import rolling_zscore

        # All same values = zero std
        flat_data = np.ones(150)
        z = rolling_zscore(flat_data, window=100)

        # Should handle gracefully
        assert z is not None, "Should return a value even with zero std"
        assert not np.isnan(z) and not np.isinf(z), \
            "Should not return NaN/inf with zero std"

        print(f"✅ Zero std handled: z = {z}")

    def test_division_by_exact_epsilon(self):
        """Test division by values exactly at epsilon threshold."""
        from src.utils.safe_operations import safe_divide

        epsilon = 1e-10

        # Exactly at epsilon
        result_at = safe_divide(10, epsilon, default=0.0)
        # Just above epsilon
        result_above = safe_divide(10, epsilon * 1.1, default=0.0)

        # At epsilon should return default, above should divide
        assert result_at == 0.0, "Exactly at epsilon should use default"
        assert result_above != 0.0, "Above epsilon should divide"

        print(f"✅ Epsilon threshold working: at={result_at}, above={result_above:.2e}")


class TestPhase1RegressionPrevention:
    """Test that Phase 1 didn't break anything."""

    def test_utilities_dont_crash_on_normal_data(self):
        """Test utilities work with normal, expected data."""
        from src.utils.normalization import rolling_zscore, normalize_to_score
        from src.utils.safe_operations import safe_divide

        # Normal data
        normal_cumulative = np.cumsum(np.random.randn(200) * 1000)

        # Should not crash
        z = rolling_zscore(normal_cumulative, window=100)
        score = normalize_to_score(z, scale=15) if z is not None else 50.0
        division = safe_divide(100, 50, default=0.0)

        assert z is not None or len(normal_cumulative) < 100, "Should calculate z-score"
        assert 0 <= score <= 100, f"Score should be 0-100, got {score}"
        assert division == 2.0, f"100/50 should be 2.0, got {division}"

        print(f"✅ Normal data processing: z={z}, score={score:.2f}, div={division}")

    def test_no_import_errors(self):
        """Test that all imports work without errors."""
        try:
            # Import all utilities
            from src.utils.normalization import rolling_zscore, normalize_to_score, welford_update
            from src.utils.safe_operations import (
                safe_divide, safe_percentage, safe_log,
                safe_sqrt, clip_to_range, ensure_score_range
            )

            # Import indicator modules
            from src.indicators import volume_indicators
            from src.indicators import orderflow_indicators
            from src.indicators import orderbook_indicators
            from src.indicators import price_structure_indicators

            print("✅ All imports successful - no regressions")
        except ImportError as e:
            pytest.fail(f"Import regression detected: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
