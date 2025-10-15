#!/usr/bin/env python3
"""
Unit tests for rolling window CVD/OBV implementations
Tests bounded values, sensitivity, and overflow prevention
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators


class TestRollingWindowOBV:
    """Test suite for OBV rolling window implementation"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = {
            'analysis': {
                'indicators': {
                    'volume': {
                        'parameters': {
                            'obv_window': 100  # Small window for testing
                        }
                    }
                }
            }
        }
        self.indicator = VolumeIndicators(self.config)

    def test_obv_bounded_values(self):
        """Test that OBV stays within 0-100 range"""
        # Create test data with strong trend
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1min'),
            'close': np.arange(200) + 100,  # Strong uptrend
            'volume': np.random.rand(200) * 1000 + 100
        })

        obv_series = self.indicator.calculate_obv(df)

        assert not obv_series.empty, "OBV series should not be empty"
        assert obv_series.min() >= 0, f"OBV min {obv_series.min()} should be >= 0"
        assert obv_series.max() <= 100, f"OBV max {obv_series.max()} should be <= 100"

    def test_obv_no_overflow_large_dataset(self):
        """Test OBV with large dataset to ensure no overflow"""
        # Create very large dataset
        large_size = 100000
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=large_size, freq='1min'),
            'close': np.random.randn(large_size).cumsum() + 1000,
            'volume': np.random.rand(large_size) * 10000 + 1000
        })

        obv_series = self.indicator.calculate_obv(df)

        # Check no NaN or inf values
        assert not pd.isna(obv_series.iloc[-1]), "OBV should not be NaN"
        assert not np.isinf(obv_series.iloc[-1]), "OBV should not be inf (overflow)"
        assert 0 <= obv_series.iloc[-1] <= 100, f"OBV {obv_series.iloc[-1]} out of bounds"

    def test_obv_sensitivity_to_recent_changes(self):
        """Test that OBV responds to recent price changes"""
        # Create data with flat start, then strong buying
        df_flat = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=150, freq='1min'),
            'close': [100.0] * 100 + list(np.arange(100, 150)),  # Flat then rising
            'volume': [1000.0] * 150
        })

        obv_series = self.indicator.calculate_obv(df_flat)

        # OBV at start should be near neutral
        obv_start = obv_series.iloc[110]  # After flat period

        # OBV at end should be higher (responding to buying)
        obv_end = obv_series.iloc[-1]

        assert obv_end > obv_start, f"OBV should increase with buying pressure (start={obv_start:.2f}, end={obv_end:.2f})"

    def test_obv_flat_price_neutral(self):
        """Test OBV with completely flat price"""
        df_flat = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1min'),
            'close': [100.0] * 200,  # Completely flat
            'volume': [1000.0] * 200
        })

        obv_series = self.indicator.calculate_obv(df_flat)

        # With flat price, OBV should be near neutral (50)
        obv_value = obv_series.iloc[-1]
        assert 45 <= obv_value <= 55, f"OBV with flat price should be near neutral (50), got {obv_value:.2f}"

    def test_obv_zero_volume_handling(self):
        """Test OBV handles zero volume gracefully"""
        df_zero_vol = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1min'),
            'close': np.random.randn(200).cumsum() + 100,
            'volume': [0.0] * 200  # Zero volume
        })

        obv_series = self.indicator.calculate_obv(df_zero_vol)

        # Should return neutral score
        assert not obv_series.empty
        obv_value = obv_series.iloc[-1]
        assert pd.isna(obv_value) or obv_value == 50.0, f"OBV with zero volume should be NaN or neutral, got {obv_value}"


class TestRollingWindowCVD:
    """Test suite for CVD rolling window implementation"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = {
            'cvd_window': 1000,  # Small window for testing
            'min_trades': 10  # Lower threshold for testing
        }
        self.indicator = OrderflowIndicators(self.config)

    def create_trade_data(self, n_trades, buy_ratio=0.5):
        """Helper to create trade data"""
        trades = []
        for i in range(n_trades):
            side = 'buy' if np.random.rand() < buy_ratio else 'sell'
            trades.append({
                'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(seconds=i),
                'side': side,
                'amount': np.random.rand() * 100 + 10,
                'price': 50000 + np.random.randn() * 100
            })
        return pd.DataFrame(trades)

    def test_cvd_bounded_values(self):
        """Test that CVD score stays within 0-100 range"""
        # Create market data with many trades
        trades_df = self.create_trade_data(5000, buy_ratio=0.7)  # 70% buys

        market_data = {
            'trades': trades_df,
            'ohlcv': pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
                'open': [50000] * 100,
                'high': [50100] * 100,
                'low': [49900] * 100,
                'close': list(np.arange(50000, 50100)),
                'volume': [1000] * 100
            })
        }

        cvd_score = self.indicator._calculate_cvd(market_data)

        assert 0 <= cvd_score <= 100, f"CVD score {cvd_score} should be in range [0, 100]"

    def test_cvd_no_overflow_large_dataset(self):
        """Test CVD with very large trade dataset"""
        # Create massive trade dataset
        trades_df = self.create_trade_data(100000, buy_ratio=0.6)

        market_data = {
            'trades': trades_df,
            'ohlcv': pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1min'),
                'open': np.random.randn(1000).cumsum() + 50000,
                'high': np.random.randn(1000).cumsum() + 50100,
                'low': np.random.randn(1000).cumsum() + 49900,
                'close': np.random.randn(1000).cumsum() + 50000,
                'volume': np.random.rand(1000) * 10000 + 1000
            })
        }

        cvd_score = self.indicator._calculate_cvd(market_data)

        # Check no overflow or invalid values
        assert not pd.isna(cvd_score), "CVD should not be NaN"
        assert not np.isinf(cvd_score), "CVD should not be inf (overflow)"
        assert 0 <= cvd_score <= 100, f"CVD {cvd_score} out of bounds"

    def test_cvd_responds_to_buy_selling(self):
        """Test CVD responds to buying/selling pressure"""
        # Strong buying pressure
        trades_buy = self.create_trade_data(2000, buy_ratio=0.9)  # 90% buys

        market_data_buy = {
            'trades': trades_buy,
            'ohlcv': pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
                'open': [50000] * 100,
                'high': [50100] * 100,
                'low': [49900] * 100,
                'close': list(np.arange(50000, 50100)),
                'volume': [1000] * 100
            })
        }

        cvd_buy_score = self.indicator._calculate_cvd(market_data_buy)

        # Strong selling pressure
        trades_sell = self.create_trade_data(2000, buy_ratio=0.1)  # 10% buys (90% sells)

        market_data_sell = {
            'trades': trades_sell,
            'ohlcv': pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
                'open': [50000] * 100,
                'high': [50100] * 100,
                'low': [49900] * 100,
                'close': list(np.arange(50000, 49900, -1)),
                'volume': [1000] * 100
            })
        }

        cvd_sell_score = self.indicator._calculate_cvd(market_data_sell)

        assert cvd_buy_score > cvd_sell_score, f"CVD with buying ({cvd_buy_score:.2f}) should be higher than selling ({cvd_sell_score:.2f})"
        assert cvd_buy_score > 55, f"Strong buying should give CVD > 55, got {cvd_buy_score:.2f}"
        assert cvd_sell_score < 45, f"Strong selling should give CVD < 45, got {cvd_sell_score:.2f}"

    def test_cvd_window_limits_accumulation(self):
        """Test that CVD window limits accumulation"""
        # Create data with window limit
        small_window_config = self.config.copy()
        small_window_config['cvd_window'] = 100
        indicator_small = OrderflowIndicators(small_window_config)

        # Large dataset but only last 100 trades should matter
        trades_df = self.create_trade_data(5000, buy_ratio=0.5)

        market_data = {
            'trades': trades_df,
            'ohlcv': pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
                'open': [50000] * 100,
                'high': [50100] * 100,
                'low': [49900] * 100,
                'close': [50000] * 100,
                'volume': [1000] * 100
            })
        }

        cvd_score = indicator_small._calculate_cvd(market_data)

        # CVD should be calculated only from last 100 trades
        # With balanced buying/selling (50%), should be near neutral
        assert 40 <= cvd_score <= 60, f"CVD with balanced flow should be near neutral (50), got {cvd_score:.2f}"


class TestCrossSymbolComparability:
    """Test that normalized CVD/OBV are comparable across different symbols"""

    def test_obv_cross_symbol_comparability(self):
        """Test OBV percentage is comparable across symbols"""
        config = {'analysis': {'indicators': {'volume': {'parameters': {'obv_window': 100}}}}}
        indicator = VolumeIndicators(config)

        # BTC-like: High price, high volume
        df_btc = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1min'),
            'close': np.arange(200) * 100 + 50000,  # $50k-$70k
            'volume': np.random.rand(200) * 1000 + 500
        })

        # ETH-like: Lower price, lower volume
        df_eth = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1min'),
            'close': np.arange(200) * 10 + 3000,  # $3k-$5k
            'volume': np.random.rand(200) * 100 + 50
        })

        obv_btc = indicator.calculate_obv(df_btc).iloc[-1]
        obv_eth = indicator.calculate_obv(df_eth).iloc[-1]

        # Both should be in similar range (both uptrending)
        assert 60 <= obv_btc <= 100, f"BTC OBV {obv_btc:.2f} should show uptrend"
        assert 60 <= obv_eth <= 100, f"ETH OBV {obv_eth:.2f} should show uptrend"

        # Difference should be reasonable (both show same pattern)
        diff = abs(obv_btc - obv_eth)
        assert diff < 30, f"OBV difference {diff:.2f} should be < 30 for similar patterns"


class TestBackwardCompatibility:
    """Test that the new implementation maintains backward compatibility"""

    def test_obv_method_exists(self):
        """Test OBV calculation method exists"""
        config = {}
        indicator = VolumeIndicators(config)
        assert hasattr(indicator, 'calculate_obv')

    def test_cvd_method_exists(self):
        """Test CVD calculation method exists"""
        config = {}
        indicator = OrderflowIndicators(config)
        assert hasattr(indicator, '_calculate_cvd')


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
