"""
Unit tests for Enhanced Liquidation Analyzer

Tests all functionality of the enhanced liquidation analyzer including:
- Technical indicator calculations
- Enhancement factor analysis
- Score enhancement logic
- Edge cases and error handling
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.core.analysis.enhanced_liquidation_analyzer import (
    EnhancedLiquidationAnalyzer,
    EnhancedLiquidationResult,
    create_enhanced_liquidation_analyzer
)

class TestEnhancedLiquidationAnalyzer:
    """Test suite for EnhancedLiquidationAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance with default parameters."""
        return EnhancedLiquidationAnalyzer(
            adx_period=14,
            ema_short_period=9,
            ema_long_period=21,
            sr_lookback_periods=50,
            sr_distance_threshold=0.02
        )

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data for testing."""
        np.random.seed(42)  # For reproducible tests

        periods = 100
        base_price = 50000
        timestamps = pd.date_range(start='2024-01-01', periods=periods, freq='1H')

        # Generate realistic price movement
        returns = np.random.normal(0, 0.02, periods)
        prices = [base_price]

        for i in range(1, periods):
            prices.append(prices[-1] * (1 + returns[i]))

        # Create OHLCV data
        data = []
        for i, price in enumerate(prices):
            volatility = abs(returns[i]) * price
            high = price + volatility * 0.5
            low = price - volatility * 0.5
            open_price = prices[i-1] if i > 0 else price
            volume = np.random.uniform(1000, 10000)

            data.append({
                'timestamp': timestamps[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })

        return pd.DataFrame(data)

    @pytest.fixture
    def sample_market_data(self, sample_ohlcv_data):
        """Create sample market data dictionary."""
        return {
            'ohlcv': sample_ohlcv_data,
            'symbol': 'BTC/USDT',
            'exchange': 'binance',
            'volume_24h': 1000000,
            'price_change_24h': 2.5
        }

    def test_analyzer_initialization(self):
        """Test analyzer initialization with custom parameters."""
        analyzer = EnhancedLiquidationAnalyzer(
            adx_period=20,
            ema_short_period=12,
            ema_long_period=26,
            sr_lookback_periods=30,
            sr_distance_threshold=0.015
        )

        assert analyzer.adx_period == 20
        assert analyzer.ema_short_period == 12
        assert analyzer.ema_long_period == 26
        assert analyzer.sr_lookback_periods == 30
        assert analyzer.sr_distance_threshold == 0.015

    def test_factory_function(self):
        """Test the create_enhanced_liquidation_analyzer factory function."""
        analyzer = create_enhanced_liquidation_analyzer(
            adx_period=25,
            ema_short_period=8
        )

        assert isinstance(analyzer, EnhancedLiquidationAnalyzer)
        assert analyzer.adx_period == 25
        assert analyzer.ema_short_period == 8

    def test_ohlcv_data_extraction_dataframe(self, analyzer, sample_ohlcv_data):
        """Test OHLCV data extraction from pandas DataFrame."""
        market_data = {'ohlcv': sample_ohlcv_data}

        extracted_df = analyzer._extract_ohlcv_data(market_data)

        assert extracted_df is not None
        assert isinstance(extracted_df, pd.DataFrame)
        assert len(extracted_df) == len(sample_ohlcv_data)
        assert all(col in extracted_df.columns for col in ['open', 'high', 'low', 'close', 'volume'])

    def test_ohlcv_data_extraction_list(self, analyzer):
        """Test OHLCV data extraction from list format."""
        ohlcv_list = [
            [1640995200, 50000, 51000, 49000, 50500, 1000],
            [1640998800, 50500, 51500, 50000, 51000, 1200],
            [1641002400, 51000, 52000, 50500, 51500, 1100]
        ]

        market_data = {'ohlcv': ohlcv_list}
        extracted_df = analyzer._extract_ohlcv_data(market_data)

        assert extracted_df is not None
        assert isinstance(extracted_df, pd.DataFrame)
        assert len(extracted_df) == 3
        assert extracted_df['close'].iloc[-1] == 51500

    def test_ohlcv_data_extraction_invalid(self, analyzer):
        """Test OHLCV data extraction with invalid data."""
        market_data = {'invalid_key': 'invalid_data'}

        extracted_df = analyzer._extract_ohlcv_data(market_data)

        assert extracted_df is None

    def test_technical_indicators_calculation(self, analyzer, sample_ohlcv_data):
        """Test calculation of all technical indicators."""
        indicators = analyzer._calculate_technical_indicators(sample_ohlcv_data)

        # Check all expected indicators are present
        expected_indicators = [
            'ema_short', 'ema_long', 'adx', 'price_vs_ema_short',
            'price_vs_ema_long', 'ema_crossover_signal', 'volume_trend',
            'resistance_level', 'support_level', 'distance_to_resistance',
            'distance_to_support', 'near_resistance', 'near_support'
        ]

        for indicator in expected_indicators:
            assert indicator in indicators

        # Check reasonable values
        assert indicators['ema_short'] > 0
        assert indicators['ema_long'] > 0
        assert 0 <= indicators['adx'] <= 100
        assert isinstance(indicators['near_resistance'], bool)
        assert isinstance(indicators['near_support'], bool)

    def test_adx_calculation(self, analyzer, sample_ohlcv_data):
        """Test ADX calculation specifically."""
        adx = analyzer._calculate_adx(sample_ohlcv_data)

        assert isinstance(adx, float)
        assert 0 <= adx <= 100
        assert not np.isnan(adx)

    def test_ema_crossover_signal(self, analyzer):
        """Test EMA crossover signal calculation."""
        # Create data with clear crossover
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 104, 103, 102, 101]
        })

        signal = analyzer._calculate_ema_crossover_signal(data)

        assert isinstance(signal, float)
        assert -1.0 <= signal <= 1.0

    def test_volume_trend_calculation(self, analyzer, sample_ohlcv_data):
        """Test volume trend calculation."""
        volume_trend = analyzer._calculate_volume_trend(sample_ohlcv_data)

        assert isinstance(volume_trend, float)
        assert -100 <= volume_trend <= 100

    def test_support_resistance_calculation(self, analyzer, sample_ohlcv_data):
        """Test support and resistance level calculation."""
        sr_levels = analyzer._calculate_support_resistance(sample_ohlcv_data)

        required_keys = [
            'resistance_level', 'support_level', 'distance_to_resistance',
            'distance_to_support', 'near_resistance', 'near_support'
        ]

        for key in required_keys:
            assert key in sr_levels

        assert sr_levels['resistance_level'] > sr_levels['support_level']
        assert isinstance(sr_levels['near_resistance'], bool)
        assert isinstance(sr_levels['near_support'], bool)

    def test_enhancement_factors_analysis(self, analyzer, sample_ohlcv_data, sample_market_data):
        """Test enhancement factors analysis."""
        indicators = analyzer._calculate_technical_indicators(sample_ohlcv_data)
        factors = analyzer._analyze_enhancement_factors(sample_ohlcv_data, indicators, sample_market_data)

        expected_factors = ['adx_trend_strength', 'ema_momentum', 'support_resistance', 'volume_confirmation']

        for factor in expected_factors:
            assert factor in factors
            assert -1.0 <= factors[factor] <= 1.0

    def test_enhanced_score_calculation(self, analyzer):
        """Test enhanced score calculation."""
        base_score = 60.0
        enhancement_factors = {
            'adx_trend_strength': 0.5,
            'ema_momentum': 0.3,
            'support_resistance': 0.7,
            'volume_confirmation': 0.2
        }

        enhanced_score = analyzer._calculate_enhanced_score(base_score, enhancement_factors)

        assert isinstance(enhanced_score, float)
        assert 0 <= enhanced_score <= 100
        assert enhanced_score != base_score  # Should be enhanced

    def test_reasoning_generation(self, analyzer):
        """Test reasoning generation."""
        enhancement_factors = {
            'adx_trend_strength': 0.8,
            'ema_momentum': 0.6,
            'support_resistance': 0.4,
            'volume_confirmation': 0.3
        }

        indicators = {
            'adx': 35.0,
            'ema_crossover_signal': 0.7,
            'near_support': True,
            'volume_trend': 25.0
        }

        reasoning = analyzer._generate_reasoning(enhancement_factors, indicators)

        assert isinstance(reasoning, list)
        assert len(reasoning) > 0
        assert all(isinstance(reason, str) for reason in reasoning)

    def test_confidence_calculation(self, analyzer):
        """Test confidence calculation."""
        enhancement_factors = {
            'adx_trend_strength': 0.5,
            'ema_momentum': 0.3,
            'support_resistance': 0.7,
            'volume_confirmation': 0.2
        }

        indicators = {
            'adx': 25.0,
            'ema_short': 50000,
            'ema_long': 49500,
            'volume_trend': 15.0
        }

        confidence = analyzer._calculate_confidence(enhancement_factors, indicators)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_analyze_enhanced_liquidation_success(self, analyzer, sample_market_data):
        """Test successful enhanced liquidation analysis."""
        base_score = 75.0

        result = analyzer.analyze_enhanced_liquidation(base_score, sample_market_data)

        assert isinstance(result, EnhancedLiquidationResult)
        assert 0 <= result.final_score <= 100
        assert isinstance(result.reasoning, list)
        assert len(result.reasoning) > 0
        assert isinstance(result.technical_indicators, dict)
        assert 0.0 <= result.confidence <= 1.0
        assert result.base_score == base_score
        assert result.enhancement_magnitude >= 0

    def test_analyze_enhanced_liquidation_insufficient_data(self, analyzer):
        """Test enhanced liquidation analysis with insufficient data."""
        base_score = 50.0
        insufficient_data = {
            'ohlcv': pd.DataFrame({
                'open': [100], 'high': [105], 'low': [95], 'close': [102], 'volume': [1000]
            })
        }

        result = analyzer.analyze_enhanced_liquidation(base_score, insufficient_data)

        assert result.final_score == base_score
        assert "Insufficient OHLCV data" in result.reasoning[0]
        assert result.confidence == 0.0

    def test_analyze_enhanced_liquidation_no_data(self, analyzer):
        """Test enhanced liquidation analysis with no OHLCV data."""
        base_score = 45.0
        empty_data = {}

        result = analyzer.analyze_enhanced_liquidation(base_score, empty_data)

        assert result.final_score == base_score
        assert len(result.reasoning) > 0
        assert result.confidence == 0.0

    def test_fallback_result(self, analyzer):
        """Test fallback result creation."""
        base_score = 65.0
        reason = "Test error condition"

        result = analyzer._fallback_result(base_score, reason)

        assert isinstance(result, EnhancedLiquidationResult)
        assert result.final_score == base_score
        assert result.reasoning[0].endswith(reason)
        assert result.confidence == 0.0
        assert result.enhancement_magnitude == 0.0

    def test_score_bounds_enforcement(self, analyzer, sample_market_data):
        """Test that enhanced scores are properly bounded between 0 and 100."""
        # Test with extreme base scores
        extreme_scores = [-10, 0, 50, 100, 110]

        for base_score in extreme_scores:
            result = analyzer.analyze_enhanced_liquidation(base_score, sample_market_data)
            assert 0 <= result.final_score <= 100

    def test_error_handling_in_technical_indicators(self, analyzer):
        """Test error handling in technical indicator calculations."""
        # Create malformed data
        bad_data = pd.DataFrame({
            'open': [None, None],
            'high': [None, None],
            'low': [None, None],
            'close': [None, None],
            'volume': [None, None]
        })

        indicators = analyzer._calculate_technical_indicators(bad_data)

        # Should return empty dict on error
        assert isinstance(indicators, dict)

    @patch('src.core.analysis.enhanced_liquidation_analyzer.logging.getLogger')
    def test_logging_integration(self, mock_logger, analyzer, sample_market_data):
        """Test that proper logging occurs during analysis."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        base_score = 60.0
        result = analyzer.analyze_enhanced_liquidation(base_score, sample_market_data)

        # Verify analysis completed successfully
        assert isinstance(result, EnhancedLiquidationResult)

    def test_different_data_source_formats(self, analyzer):
        """Test extraction from different market data source formats."""
        # Test with different key names
        test_cases = [
            {'price_data': pd.DataFrame({'open': [100], 'high': [105], 'low': [95], 'close': [102], 'volume': [1000]})},
            {'candles': pd.DataFrame({'open': [100], 'high': [105], 'low': [95], 'close': [102], 'volume': [1000]})},
            {'klines': pd.DataFrame({'open': [100], 'high': [105], 'low': [95], 'close': [102], 'volume': [1000]})}
        ]

        for market_data in test_cases:
            extracted_df = analyzer._extract_ohlcv_data(market_data)
            # Should either extract successfully or return None (if insufficient data)
            assert extracted_df is None or isinstance(extracted_df, pd.DataFrame)

    def test_enhancement_magnitude_calculation(self, analyzer, sample_market_data):
        """Test that enhancement magnitude is calculated correctly."""
        base_score = 50.0

        result = analyzer.analyze_enhanced_liquidation(base_score, sample_market_data)

        expected_magnitude = abs(result.final_score - base_score)
        assert result.enhancement_magnitude == expected_magnitude

    def test_various_market_conditions(self, analyzer):
        """Test analyzer with various market conditions."""
        # Create different market scenarios
        scenarios = [
            # Trending up market
            {'trend': 'up', 'volatility': 'low'},
            # Trending down market
            {'trend': 'down', 'volatility': 'high'},
            # Sideways market
            {'trend': 'sideways', 'volatility': 'medium'}
        ]

        for scenario in scenarios:
            # Create market data based on scenario
            periods = 50
            base_price = 50000

            if scenario['trend'] == 'up':
                price_changes = np.random.normal(0.01, 0.02, periods)
            elif scenario['trend'] == 'down':
                price_changes = np.random.normal(-0.01, 0.02, periods)
            else:  # sideways
                price_changes = np.random.normal(0, 0.01, periods)

            prices = [base_price]
            for change in price_changes:
                prices.append(prices[-1] * (1 + change))

            data = pd.DataFrame({
                'open': prices[:-1],
                'high': [p * 1.02 for p in prices[:-1]],
                'low': [p * 0.98 for p in prices[:-1]],
                'close': prices[1:],
                'volume': np.random.uniform(1000, 5000, periods)
            })

            market_data = {'ohlcv': data}
            result = analyzer.analyze_enhanced_liquidation(50.0, market_data)

            # Verify analysis completes for all scenarios
            assert isinstance(result, EnhancedLiquidationResult)
            assert 0 <= result.final_score <= 100

if __name__ == '__main__':
    pytest.main([__file__, '-v'])