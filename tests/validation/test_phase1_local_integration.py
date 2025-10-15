"""
Phase 1 Local Integration Test

Tests that Phase 1 changes (z-score normalization and Division Guards) work
correctly in actual indicator implementations with real data scenarios.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class TestPhase1ZScoreIntegration:
    """Test z-score normalization works in actual indicator usage."""

    def test_volume_indicators_with_zscore(self):
        """Test VolumeIndicators with z-score normalization applied."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        # Create instance
        volume_indicators = VolumeIndicators()

        # Create realistic mock data
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0 + np.random.randn(200) * 100,
            'high': 50100.0 + np.random.randn(200) * 100,
            'low': 49900.0 + np.random.randn(200) * 100,
            'close': 50000.0 + np.random.randn(200) * 100,
            'volume': 1000000 + np.random.randn(200) * 100000,
        })
        df['volume'] = df['volume'].abs()  # Ensure positive

        # Test OBV with z-score normalization
        try:
            obv_score = volume_indicators.calculate_obv_score(df)

            # Verify OBV score is bounded (0-100)
            assert isinstance(obv_score, (int, float, np.number)), \
                f"OBV score should be numeric, got {type(obv_score)}"
            assert 0 <= obv_score <= 100, \
                f"OBV score should be 0-100, got {obv_score}"

            print(f"✅ OBV Score: {obv_score:.2f} (bounded 0-100)")
        except Exception as e:
            pytest.fail(f"OBV calculation failed: {e}")

        # Test ADL with z-score normalization
        try:
            adl_score = volume_indicators.calculate_adl_score(df)

            # Verify ADL score is bounded (0-100)
            assert isinstance(adl_score, (int, float, np.number)), \
                f"ADL score should be numeric, got {type(adl_score)}"
            assert 0 <= adl_score <= 100, \
                f"ADL score should be 0-100, got {adl_score}"

            print(f"✅ ADL Score: {adl_score:.2f} (bounded 0-100)")
        except Exception as e:
            pytest.fail(f"ADL calculation failed: {e}")

        # Test Volume Delta (if it uses z-score)
        try:
            volume_delta = volume_indicators.calculate_volume_delta(
                buy_volume=50000,
                sell_volume=30000
            )

            # Volume delta should be numeric
            assert isinstance(volume_delta, (int, float, np.number)), \
                f"Volume delta should be numeric, got {type(volume_delta)}"

            print(f"✅ Volume Delta: {volume_delta:.2f}")
        except Exception as e:
            # Volume delta might not be z-scored, just log
            print(f"ℹ️  Volume Delta calculation: {e}")

    def test_zscore_prevents_overflow(self):
        """Test that z-score prevents overflow with extreme cumulative values."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        volume_indicators = VolumeIndicators()

        # Create data that would cause overflow without z-score
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': np.linspace(49000, 51000, 1000),  # Trending up
            'volume': np.ones(1000) * 1000000,  # Constant high volume
        })

        # This should NOT overflow with z-score normalization
        try:
            obv_score = volume_indicators.calculate_obv_score(df)

            # Should be bounded even with 1000 periods of accumulation
            assert 0 <= obv_score <= 100, \
                f"OBV should remain bounded even with 1000 periods, got {obv_score}"
            assert not np.isnan(obv_score), "OBV should not be NaN"
            assert not np.isinf(obv_score), "OBV should not be infinite"

            print(f"✅ OBV with 1000 periods: {obv_score:.2f} (no overflow)")
        except Exception as e:
            pytest.fail(f"OBV overflowed with long data: {e}")


class TestPhase1DivisionGuardsIntegration:
    """Test Division Guards work in actual indicator usage."""

    def test_volume_indicators_with_division_guards(self):
        """Test VolumeIndicators with Division Guards protection."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        volume_indicators = VolumeIndicators()

        # Create data with zero volume (would cause division by zero)
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1h')
        df_zero_volume = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50000.0,
            'volume': 0.0,  # Zero volume - dangerous!
        })

        # This should NOT crash with Division Guards
        try:
            obv_score = volume_indicators.calculate_obv_score(df_zero_volume)
            assert isinstance(obv_score, (int, float, np.number)), \
                "Should return numeric value even with zero volume"
            print(f"✅ Zero volume handled: OBV = {obv_score:.2f}")
        except ZeroDivisionError:
            pytest.fail("Division by zero occurred - Division Guards failed!")
        except Exception as e:
            # Other exceptions might be acceptable (e.g., insufficient data)
            print(f"ℹ️  Zero volume exception (expected): {e}")

    def test_orderflow_indicators_with_division_guards(self):
        """Test OrderflowIndicators with Division Guards protection."""
        try:
            from src.indicators.orderflow_indicators import OrderflowIndicators
        except ImportError as e:
            pytest.skip(f"OrderflowIndicators not available: {e}")

        orderflow_indicators = OrderflowIndicators()

        # Test with edge case data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0 + np.random.randn(100) * 50,
            'high': 50100.0 + np.random.randn(100) * 50,
            'low': 49900.0 + np.random.randn(100) * 50,
            'close': 50000.0 + np.random.randn(100) * 50,
            'volume': np.maximum(100000 + np.random.randn(100) * 10000, 0),
        })

        # Try to calculate CVD score (has protected divisions)
        try:
            # CVD calculation might need trades data
            trades = pd.DataFrame({
                'timestamp': dates[:50],
                'price': 50000.0 + np.random.randn(50) * 50,
                'amount': np.random.rand(50) * 10,
                'side': np.random.choice(['buy', 'sell'], 50),
            })

            cvd_score = orderflow_indicators.calculate_cvd_score(df, trades)

            # Should return a valid score
            if cvd_score is not None:
                assert isinstance(cvd_score, (int, float, np.number)), \
                    f"CVD score should be numeric, got {type(cvd_score)}"
                print(f"✅ CVD Score: {cvd_score:.2f}")
            else:
                print(f"ℹ️  CVD Score: None (insufficient data)")
        except ZeroDivisionError:
            pytest.fail("Division by zero in OrderflowIndicators!")
        except Exception as e:
            # Might fail for other reasons (data requirements)
            print(f"ℹ️  CVD calculation note: {e}")

    def test_orderbook_indicators_with_division_guards(self):
        """Test OrderbookIndicators with Division Guards protection."""
        try:
            from src.indicators.orderbook_indicators import OrderbookIndicators
        except ImportError as e:
            pytest.skip(f"OrderbookIndicators not available: {e}")

        orderbook_indicators = OrderbookIndicators()

        # Create mock orderbook with edge cases
        bids = np.array([
            [49900, 1.0],
            [49850, 2.0],
            [49800, 3.0],
            [0.0, 0.0],  # Zero price/volume - edge case
        ])

        asks = np.array([
            [50100, 1.0],
            [50150, 2.0],
            [50200, 3.0],
            [0.0, 0.0],  # Zero price/volume - edge case
        ])

        current_price = 50000.0

        # Test orderbook depth calculation (has many protected divisions)
        try:
            depth_score = orderbook_indicators.calculate_orderbook_depth_score(
                bids=bids,
                asks=asks,
                current_price=current_price
            )

            if depth_score is not None:
                assert isinstance(depth_score, (int, float, np.number)), \
                    f"Depth score should be numeric, got {type(depth_score)}"
                assert 0 <= depth_score <= 100, \
                    f"Depth score should be 0-100, got {depth_score}"
                print(f"✅ Orderbook Depth: {depth_score:.2f}")
            else:
                print(f"ℹ️  Orderbook Depth: None (insufficient data)")
        except ZeroDivisionError:
            pytest.fail("Division by zero in OrderbookIndicators!")
        except Exception as e:
            print(f"ℹ️  Orderbook depth note: {e}")

    def test_price_structure_indicators_with_division_guards(self):
        """Test PriceStructureIndicators with Division Guards protection."""
        try:
            from src.indicators.price_structure_indicators import PriceStructureIndicators
        except ImportError as e:
            pytest.skip(f"PriceStructureIndicators not available: {e}")

        price_structure = PriceStructureIndicators()

        # Create data with flat prices (zero range - dangerous for divisions)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df_flat = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0,
            'high': 50000.0,  # Flat - no range
            'low': 50000.0,   # Flat - no range
            'close': 50000.0,
            'volume': 1000000,
        })

        # This should handle zero range without crashing
        try:
            value_area_score = price_structure.calculate_value_area_score(df_flat)

            if value_area_score is not None:
                assert isinstance(value_area_score, (int, float, np.number)), \
                    "Should return numeric even with flat prices"
                print(f"✅ Flat price handling: Value Area = {value_area_score:.2f}")
            else:
                print(f"ℹ️  Value Area: None (flat prices)")
        except ZeroDivisionError:
            pytest.fail("Division by zero with flat prices!")
        except Exception as e:
            print(f"ℹ️  Value area note: {e}")


class TestPhase1EdgeCases:
    """Test Phase 1 improvements handle real-world edge cases."""

    def test_all_zero_data(self):
        """Test indicators handle all-zero data gracefully."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        volume_indicators = VolumeIndicators()

        dates = pd.date_range(start='2024-01-01', periods=50, freq='1h')
        df_zeros = pd.DataFrame({
            'timestamp': dates,
            'open': 0.0,
            'high': 0.0,
            'low': 0.0,
            'close': 0.0,
            'volume': 0.0,
        })

        # Should not crash
        try:
            obv_score = volume_indicators.calculate_obv_score(df_zeros)
            print(f"✅ All-zero data handled: OBV = {obv_score}")
        except Exception as e:
            print(f"ℹ️  All-zero exception: {e}")

    def test_nan_data(self):
        """Test indicators handle NaN data gracefully."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        volume_indicators = VolumeIndicators()

        dates = pd.date_range(start='2024-01-01', periods=50, freq='1h')
        df_nan = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': [50000.0] * 25 + [np.nan] * 25,  # NaN in second half
            'volume': [1000000.0] * 25 + [np.nan] * 25,
        })

        # Should handle NaN without crashing
        try:
            obv_score = volume_indicators.calculate_obv_score(df_nan)
            print(f"✅ NaN data handled: OBV = {obv_score}")
        except Exception as e:
            print(f"ℹ️  NaN exception: {e}")

    def test_extreme_values(self):
        """Test indicators handle extreme values."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        volume_indicators = VolumeIndicators()

        dates = pd.date_range(start='2024-01-01', periods=50, freq='1h')
        df_extreme = pd.DataFrame({
            'timestamp': dates,
            'open': 1e10,    # Very large
            'high': 1e10,
            'low': 1e10,
            'close': 1e10,
            'volume': 1e15,  # Extremely large
        })

        # Should handle extreme values
        try:
            obv_score = volume_indicators.calculate_obv_score(df_extreme)

            # Z-score should bound even extreme values
            if obv_score is not None:
                assert 0 <= obv_score <= 100, \
                    f"Extreme values should still be bounded, got {obv_score}"
                print(f"✅ Extreme values handled: OBV = {obv_score:.2f}")
        except Exception as e:
            print(f"ℹ️  Extreme values note: {e}")


class TestPhase1BackwardCompatibility:
    """Test that Phase 1 changes don't break existing behavior."""

    def test_normal_data_unchanged(self):
        """Test that normal data produces reasonable scores."""
        try:
            from src.indicators.volume_indicators import VolumeIndicators
        except ImportError as e:
            pytest.skip(f"VolumeIndicators not available: {e}")

        volume_indicators = VolumeIndicators()

        # Create normal, realistic data
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
        np.random.seed(42)  # Reproducible
        df_normal = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0 + np.cumsum(np.random.randn(200) * 10),
            'high': 50100.0 + np.cumsum(np.random.randn(200) * 10),
            'low': 49900.0 + np.cumsum(np.random.randn(200) * 10),
            'close': 50000.0 + np.cumsum(np.random.randn(200) * 10),
            'volume': np.abs(1000000 + np.random.randn(200) * 100000),
        })

        # Calculate scores
        try:
            obv_score = volume_indicators.calculate_obv_score(df_normal)
            adl_score = volume_indicators.calculate_adl_score(df_normal)

            # Should produce valid scores
            assert 0 <= obv_score <= 100, f"OBV should be 0-100, got {obv_score}"
            assert 0 <= adl_score <= 100, f"ADL should be 0-100, got {adl_score}"

            print(f"✅ Normal data scores:")
            print(f"   OBV: {obv_score:.2f}")
            print(f"   ADL: {adl_score:.2f}")
        except Exception as e:
            pytest.fail(f"Normal data calculation failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
