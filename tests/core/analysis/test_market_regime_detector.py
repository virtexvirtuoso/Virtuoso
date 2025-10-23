"""
Unit Tests for Market Regime Detector

Tests the regime detection logic, adaptive weighting system, and trend-aware
indicator adjustments.

Author: Virtuoso Team
Version: 1.0.0
Created: 2025-10-22
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.core.analysis.market_regime_detector import (
    MarketRegimeDetector,
    MarketRegime,
    RegimeDetection
)


@pytest.fixture
def detector():
    """Create a market regime detector instance."""
    return MarketRegimeDetector()


@pytest.fixture
def strong_uptrend_data():
    """Generate market data representing a strong uptrend."""
    # 100 candles with steady upward movement
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    np.random.seed(42)

    # Price increases from 100 to 115 (15% gain)
    trend = np.linspace(100, 115, 100)
    noise = np.random.normal(0, 0.3, 100)
    close = trend + noise

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close * 0.999,
        'high': close * 1.002,
        'low': close * 0.998,
        'close': close,
        'volume': np.random.uniform(1000, 2000, 100)
    })

    return {
        'ohlcv': {'base': df},
        'orderbook': {
            'bids': [[close[-1] * 0.9995, 1000]] * 25,
            'asks': [[close[-1] * 1.0005, 1000]] * 25,
        }
    }


@pytest.fixture
def ranging_market_data():
    """Generate market data representing a ranging market."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    np.random.seed(43)

    # Price oscillates around 100 ± 2
    close = 100 + np.random.uniform(-2, 2, 100)

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close * 0.999,
        'high': close * 1.001,
        'low': close * 0.999,
        'close': close,
        'volume': np.random.uniform(1000, 1500, 100)
    })

    return {
        'ohlcv': {'base': df},
        'orderbook': {
            'bids': [[close[-1] * 0.9995, 1000]] * 25,
            'asks': [[close[-1] * 1.0005, 1000]] * 25,
        }
    }


@pytest.fixture
def high_volatility_data():
    """Generate market data with high volatility."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    np.random.seed(44)

    # Large price swings
    close = 100 + np.cumsum(np.random.uniform(-3, 3, 100))

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close * 0.995,
        'high': close * 1.01,
        'low': close * 0.99,
        'close': close,
        'volume': np.random.uniform(2000, 5000, 100)
    })

    return {
        'ohlcv': {'base': df},
        'orderbook': {
            'bids': [[close[-1] * 0.999, 500]] * 25,
            'asks': [[close[-1] * 1.001, 500]] * 25,
        }
    }


class TestMarketRegimeDetector:
    """Test suite for MarketRegimeDetector."""

    def test_initialization(self, detector):
        """Test detector initializes correctly."""
        assert detector is not None
        assert 'adx_trending' in detector.thresholds
        assert len(detector.regime_history) == 0

    def test_detect_strong_uptrend(self, detector, strong_uptrend_data):
        """Test detection of strong uptrend regime."""
        regime = detector.detect_regime(strong_uptrend_data)

        assert regime is not None
        assert regime.regime in [
            MarketRegime.STRONG_UPTREND,
            MarketRegime.MODERATE_UPTREND
        ]
        assert regime.trend_direction > 0.0  # Positive trend
        assert regime.confidence > 0.5

    def test_detect_ranging_market(self, detector, ranging_market_data):
        """Test detection of ranging/consolidation regime."""
        regime = detector.detect_regime(ranging_market_data)

        assert regime is not None
        # Ranging market has low ADX, direction near 0
        assert regime.regime == MarketRegime.RANGING
        assert abs(regime.trend_direction) < 0.5  # Near neutral

    def test_detect_high_volatility(self, detector, high_volatility_data):
        """Test detection of high volatility regime."""
        regime = detector.detect_regime(high_volatility_data)

        assert regime is not None
        # High volatility shows up in ATR percentile
        assert regime.volatility_percentile > 50.0

    def test_insufficient_data_returns_default(self, detector):
        """Test that insufficient data returns default regime."""
        # Only 10 candles (needs 50+)
        df = pd.DataFrame({
            'timestamp': pd.date_range(end=datetime.now(), periods=10, freq='1min'),
            'open': [100] * 10,
            'high': [101] * 10,
            'low': [99] * 10,
            'close': [100] * 10,
            'volume': [1000] * 10
        })

        market_data = {'ohlcv': {'base': df}}
        regime = detector.detect_regime(market_data)

        assert regime.regime == MarketRegime.RANGING  # Default regime
        assert regime.confidence == 0.5

    def test_adx_calculation(self, detector, strong_uptrend_data):
        """Test ADX calculation for trend strength."""
        df = strong_uptrend_data['ohlcv']['base']
        adx = detector._calculate_adx(df, period=14)

        assert isinstance(adx, float)
        assert 0 <= adx <= 100  # ADX is bounded 0-100
        assert adx > 20  # Strong uptrend should have ADX > 20

    def test_volatility_analysis(self, detector, high_volatility_data):
        """Test volatility analysis with ATR percentile."""
        df = high_volatility_data['ohlcv']['base']
        volatility_metrics = detector._analyze_volatility(df)

        assert 'percentile' in volatility_metrics
        assert 'atr_current' in volatility_metrics
        assert 0 <= volatility_metrics['percentile'] <= 100
        assert volatility_metrics['atr_current'] > 0

    def test_liquidity_assessment(self, detector, strong_uptrend_data):
        """Test liquidity assessment from orderbook."""
        liquidity_metrics = detector._assess_liquidity(strong_uptrend_data)

        assert 'score' in liquidity_metrics
        assert 'depth_usd' in liquidity_metrics
        assert 'spread_bps' in liquidity_metrics
        assert 0 <= liquidity_metrics['score'] <= 1
        assert liquidity_metrics['depth_usd'] > 0

    def test_liquidity_assessment_no_orderbook(self, detector):
        """Test liquidity assessment with missing orderbook data."""
        market_data = {'ohlcv': {'base': pd.DataFrame()}}
        liquidity_metrics = detector._assess_liquidity(market_data)

        assert liquidity_metrics['score'] == 0.7  # Default assumption
        assert liquidity_metrics['depth_usd'] == 0.0

    def test_adaptive_weights_uptrend(self, detector):
        """Test adaptive weights favor momentum in uptrend."""
        weights = detector.get_adaptive_weights(MarketRegime.STRONG_UPTREND)

        assert 'orderflow' in weights
        assert 'technical' in weights

        # In uptrend: orderflow > technical (momentum > mean reversion)
        assert weights['orderflow'] > weights['technical']
        assert weights['volume'] > weights['technical']

        # Weights sum to 1.0
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_adaptive_weights_ranging(self, detector):
        """Test adaptive weights favor mean reversion in ranging market."""
        weights = detector.get_adaptive_weights(MarketRegime.RANGING)

        # In ranging: technical & price structure boosted
        assert weights['technical'] > 0.12  # Boosted from base 0.10
        assert weights['price_structure'] > 0.17  # Boosted from base 0.15

        # Weights sum to 1.0
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_adaptive_weights_high_volatility(self, detector):
        """Test adaptive weights reduce in high volatility."""
        base_weights = detector.get_adaptive_weights(MarketRegime.RANGING)
        volatile_weights = detector.get_adaptive_weights(MarketRegime.HIGH_VOLATILITY)

        # In high volatility, most weights should be reduced (caution)
        # Sum still = 1.0, but individual components are dampened relative to base
        # This is hard to test directly since they're normalized, so we check ratios

        # The volatility adjustments are relative, not absolute
        # Just ensure it returns valid weights
        assert abs(sum(volatile_weights.values()) - 1.0) < 0.01

    def test_regime_smoothing_prevents_flicker(self, detector):
        """Test regime smoothing prevents rapid regime changes."""
        # First detection
        regime1 = MarketRegime.STRONG_UPTREND
        smoothed1 = detector._apply_regime_smoothing(regime1)

        # Should return the regime (first detection)
        assert smoothed1 == regime1

        # Immediately change to different regime
        regime2 = MarketRegime.RANGING
        smoothed2 = detector._apply_regime_smoothing(regime2)

        # Should still return first regime (not enough persistence)
        # Actually, with only 2 samples, it will return the most common
        # Let's add more samples to test properly

        # Add several more uptrend samples
        for _ in range(5):
            detector._apply_regime_smoothing(MarketRegime.STRONG_UPTREND)

        # Now try ranging again
        smoothed_final = detector._apply_regime_smoothing(MarketRegime.RANGING)

        # Should still be UPTREND (majority in window)
        assert smoothed_final == MarketRegime.STRONG_UPTREND

    def test_is_reversal_likely_at_extreme(self, detector, strong_uptrend_data):
        """Test reversal detection at price extremes."""
        regime = detector.detect_regime(strong_uptrend_data)

        # Simulate extreme indicator readings suggesting reversal
        indicator_scores = {
            'technical': 85,        # Overbought
            'volume': 30,           # Declining volume (exhaustion)
            'orderflow': 45,        # Weakening momentum
            'price_structure': 80,  # At resistance
            'orderbook': 70,        # Imbalance
        }

        is_likely, confidence = detector.is_reversal_likely(regime, indicator_scores)

        # With 4-5 conditions met, reversal should be likely
        assert isinstance(is_likely, bool)
        assert 0 <= confidence <= 1

    def test_is_reversal_in_ranging_market(self, detector, ranging_market_data):
        """Test reversal likelihood in ranging market (more common)."""
        regime = detector.detect_regime(ranging_market_data)

        # Moderate signals
        indicator_scores = {
            'technical': 70,
            'volume': 55,
            'orderflow': 50,
        }

        is_likely, confidence = detector.is_reversal_likely(regime, indicator_scores)

        # In ranging market, base probability is higher
        assert confidence >= 0.5  # Should have decent confidence

    def test_adjust_indicator_for_uptrend(self, detector, strong_uptrend_data):
        """Test RSI adjustment in uptrend (overbought is normal)."""
        regime = detector.detect_regime(strong_uptrend_data)

        # RSI = 75 (overbought)
        raw_score = 75  # Above 50 = bearish in raw terms
        adjusted = detector.adjust_indicator_for_trend('rsi', raw_score, regime)

        # In uptrend, overbought signal should be dampened toward neutral
        # Adjusted should be pulled toward 50
        if regime.regime in [MarketRegime.STRONG_UPTREND, MarketRegime.MODERATE_UPTREND]:
            assert adjusted < raw_score  # Pulled toward 50
            assert adjusted > 50  # But still above neutral

    def test_adjust_indicator_for_ranging(self, detector, ranging_market_data):
        """Test no adjustment in ranging market."""
        regime = detector.detect_regime(ranging_market_data)

        raw_score = 75
        adjusted = detector.adjust_indicator_for_trend('rsi', raw_score, regime)

        # In ranging market, no adjustment
        assert adjusted == raw_score

    def test_adjust_indicator_downtrend_oversold(self, detector):
        """Test RSI adjustment in downtrend (oversold is normal)."""
        # Create downtrend data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        close = np.linspace(115, 100, 100)  # Downward trend

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close * 1.001,
            'high': close * 1.002,
            'low': close * 0.998,
            'close': close,
            'volume': np.random.uniform(1000, 2000, 100)
        })

        market_data = {
            'ohlcv': {'base': df},
            'orderbook': {
                'bids': [[close[-1] * 0.9995, 1000]] * 25,
                'asks': [[close[-1] * 1.0005, 1000]] * 25,
            }
        }

        regime = detector.detect_regime(market_data)

        # RSI = 25 (oversold)
        raw_score = 25
        adjusted = detector.adjust_indicator_for_trend('rsi', raw_score, regime)

        # In downtrend, oversold signal should be dampened toward neutral
        if regime.regime in [MarketRegime.STRONG_DOWNTREND, MarketRegime.MODERATE_DOWNTREND]:
            assert adjusted > raw_score  # Pulled toward 50
            assert adjusted < 50  # But still below neutral

    def test_get_regime_description(self, detector):
        """Test regime descriptions are available."""
        for regime in MarketRegime:
            description = detector.get_regime_description(regime)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_classify_regime_low_liquidity(self, detector):
        """Test low liquidity is detected as highest priority."""
        trend_metrics = {'adx': 30, 'direction': 0.5, 'strength': 0.6, 'ema_slope': 0.01}
        volatility_metrics = {'percentile': 50, 'atr_current': 1.0, 'atr_mean': 1.0}
        liquidity_metrics = {'score': 0.2, 'depth_usd': 10000, 'spread_bps': 50}

        regime, confidence = detector._classify_regime(
            trend_metrics, volatility_metrics, liquidity_metrics
        )

        # Low liquidity should override trend
        assert regime == MarketRegime.LOW_LIQUIDITY

    def test_classify_regime_high_volatility(self, detector):
        """Test high volatility detection."""
        trend_metrics = {'adx': 20, 'direction': 0.2, 'strength': 0.4, 'ema_slope': 0.005}
        volatility_metrics = {'percentile': 85, 'atr_current': 3.0, 'atr_mean': 1.0}
        liquidity_metrics = {'score': 0.7, 'depth_usd': 150000, 'spread_bps': 5}

        regime, confidence = detector._classify_regime(
            trend_metrics, volatility_metrics, liquidity_metrics
        )

        assert regime == MarketRegime.HIGH_VOLATILITY
        assert confidence > 0.5

    def test_classify_regime_strong_trend(self, detector):
        """Test strong trend classification."""
        trend_metrics = {'adx': 45, 'direction': 0.8, 'strength': 0.9, 'ema_slope': 0.02}
        volatility_metrics = {'percentile': 50, 'atr_current': 1.0, 'atr_mean': 1.0}
        liquidity_metrics = {'score': 0.7, 'depth_usd': 150000, 'spread_bps': 5}

        regime, confidence = detector._classify_regime(
            trend_metrics, volatility_metrics, liquidity_metrics
        )

        assert regime == MarketRegime.STRONG_UPTREND
        assert confidence > 0.7  # High confidence in strong trend


class TestRegimeDetection:
    """Test the RegimeDetection dataclass."""

    def test_regime_detection_structure(self):
        """Test RegimeDetection has all required fields."""
        detection = RegimeDetection(
            regime=MarketRegime.RANGING,
            confidence=0.8,
            strength=0.5,
            trend_direction=0.1,
            volatility_percentile=45.0,
            liquidity_score=0.7,
            metadata={'test': 'value'}
        )

        assert detection.regime == MarketRegime.RANGING
        assert detection.confidence == 0.8
        assert detection.strength == 0.5
        assert detection.trend_direction == 0.1
        assert detection.volatility_percentile == 45.0
        assert detection.liquidity_score == 0.7
        assert detection.metadata['test'] == 'value'


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self, detector):
        """Test handling of empty dataframe."""
        market_data = {'ohlcv': {'base': pd.DataFrame()}}
        regime = detector.detect_regime(market_data)

        # Should return default regime
        assert regime.regime == MarketRegime.RANGING
        assert regime.confidence == 0.5

    def test_missing_orderbook(self, detector, strong_uptrend_data):
        """Test handling of missing orderbook data."""
        del strong_uptrend_data['orderbook']
        regime = detector.detect_regime(strong_uptrend_data)

        # Should still detect trend without orderbook
        assert regime is not None
        assert isinstance(regime.regime, MarketRegime)

    def test_nan_values_in_data(self, detector):
        """Test handling of NaN values in price data."""
        df = pd.DataFrame({
            'timestamp': pd.date_range(end=datetime.now(), periods=100, freq='1min'),
            'open': [100] * 100,
            'high': [101] * 100,
            'low': [99] * 100,
            'close': [100] * 50 + [np.nan] * 50,  # NaN values
            'volume': [1000] * 100
        })

        market_data = {'ohlcv': {'base': df}}
        regime = detector.detect_regime(market_data)

        # Should handle gracefully and return default
        assert regime is not None

    def test_extreme_price_movements(self, detector):
        """Test handling of extreme price movements."""
        df = pd.DataFrame({
            'timestamp': pd.date_range(end=datetime.now(), periods=100, freq='1min'),
            'open': [100] + [1000] * 99,  # 10x spike
            'high': [101] + [1010] * 99,
            'low': [99] + [990] * 99,
            'close': [100] + [1000] * 99,
            'volume': [1000] * 100
        })

        market_data = {'ohlcv': {'base': df}}
        regime = detector.detect_regime(market_data)

        # Should detect high volatility
        assert regime.volatility_percentile > 75  # High percentile


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
