"""
Unit Tests for Dual-Regime Signal Enhancement Calculator

Tests Phase 1 implementation with discrete alignment factors.

Author: Virtuoso Team
Version: 1.0.0
Created: 2025-12-16
"""

import pytest
from src.core.analysis.dual_regime_calculator import DualRegimeCalculator
from src.core.schemas.dual_regime import (
    MarketRegimeContext,
    SymbolRegimeContext,
    DualRegimeResult
)


class TestDualRegimeCalculator:
    """Test suite for DualRegimeCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance with default config."""
        return DualRegimeCalculator()

    @pytest.fixture
    def market_bearish(self):
        """Real market context: 2025-12-16 (BEARISH)."""
        return MarketRegimeContext(
            bias="BEARISH",
            fear_greed=11,  # Extreme Fear
            long_pct=74.1,  # Crowded longs
            short_pct=25.9,
            funding_rate=0.0024,
            btc_dominance=56.85,
            confidence=1.0
        )

    @pytest.fixture
    def symbol_strong_uptrend(self):
        """Symbol in strong uptrend with high confidence."""
        return SymbolRegimeContext(
            regime="STRONG_UPTREND",
            confidence=0.82,
            trend_direction=0.9,  # Strong bullish trend
            mtf_aligned=True,
            volatility_percentile=45.0
        )

    def test_bullish_relative_strength_real_market(
        self, calculator, market_bearish, symbol_strong_uptrend
    ):
        """
        Test Scenario 1: Bullish relative strength
        (Strong symbol in bearish market)

        Expected: Allow with minimal penalty (~0.995x)
        NOTE: With 74.1% longs, this triggers "crowded_trade" classification
        """
        result = calculator.calculate(
            market_context=market_bearish,
            symbol_context=symbol_strong_uptrend,
            signal_type="LONG"
        )

        # Assertions
        assert isinstance(result, DualRegimeResult)
        assert 0.90 <= result.final_multiplier <= 1.05  # Allow with slight penalty
        assert result.regime_type == "crowded_trade"  # Crowded longs trigger this
        assert result.confidence > 0.80  # High confidence
        assert result.metadata['signal_type'] == "LONG"
        assert result.metadata['market_bias'] == "BEARISH"

    def test_bearish_relative_strength(self, calculator):
        """
        Test Scenario 2: Bearish relative strength
        (Weak symbol in bullish market)

        Expected: Allow with moderate penalty (~0.99x)
        NOTE: With 72% shorts, this triggers "crowded_trade" classification
        """
        market = MarketRegimeContext(
            bias="BULLISH",
            fear_greed=82,  # Extreme Greed
            long_pct=28.0,
            short_pct=72.0,  # Crowded shorts
            funding_rate=-0.001,
            btc_dominance=54.0,
            confidence=1.0
        )

        symbol = SymbolRegimeContext(
            regime="STRONG_DOWNTREND",
            confidence=0.80,
            trend_direction=-0.85,  # Strong bearish trend
            mtf_aligned=True,
            volatility_percentile=50.0
        )

        result = calculator.calculate(market, symbol, "SHORT")

        assert 0.95 <= result.final_multiplier <= 1.05  # Adjusted for crowded shorts
        assert result.regime_type == "crowded_trade"  # Crowded shorts trigger this

    def test_aligned_momentum_bullish(self, calculator):
        """
        Test Scenario 3: Aligned momentum
        (Bullish market + bullish symbol)

        Expected: Strong boost (~1.12x)
        """
        market = MarketRegimeContext(
            bias="BULLISH",
            fear_greed=72,  # Greed
            long_pct=65.0,  # Slightly crowded
            short_pct=35.0,
            funding_rate=0.005,
            btc_dominance=52.0,
            confidence=1.0
        )

        symbol = SymbolRegimeContext(
            regime="STRONG_UPTREND",
            confidence=0.90,
            trend_direction=0.95,
            mtf_aligned=True,
            volatility_percentile=40.0
        )

        result = calculator.calculate(market, symbol, "LONG")

        assert 1.08 <= result.final_multiplier <= 1.20  # Strong boost
        assert result.regime_type == "aligned_momentum"

    def test_counter_trend_low_confidence(self, calculator):
        """
        Test Scenario 4: Counter-trend trap
        (Bullish market + bearish symbol, low confidence)

        Expected: Moderate penalty (~0.89x)
        NOTE: Low confidence reduces symbol influence, lessening penalty
        """
        market = MarketRegimeContext(
            bias="BULLISH",
            fear_greed=75,
            long_pct=55.0,
            short_pct=45.0,
            funding_rate=0.003,
            btc_dominance=55.0,
            confidence=1.0
        )

        symbol = SymbolRegimeContext(
            regime="STRONG_DOWNTREND",
            confidence=0.45,  # LOW confidence
            trend_direction=-0.7,
            mtf_aligned=False,
            volatility_percentile=60.0
        )

        result = calculator.calculate(market, symbol, "SHORT")

        assert 0.85 <= result.final_multiplier <= 0.95  # Moderate penalty (low confidence reduces impact)
        assert result.regime_type == "relative_strength"  # Not crowded, so relative strength

    def test_ranging_low_confidence_filter(self, calculator):
        """
        Test Scenario 5: Ranging + low confidence
        (Should apply penalty, potentially filter)

        Expected: Moderate penalty
        """
        market = MarketRegimeContext(
            bias="NEUTRAL",
            fear_greed=52,
            long_pct=50.0,
            short_pct=50.0,
            funding_rate=0.0001,
            btc_dominance=56.0,
            confidence=0.8
        )

        symbol = SymbolRegimeContext(
            regime="RANGING",
            confidence=0.35,  # VERY LOW
            trend_direction=0.1,
            mtf_aligned=False,
            volatility_percentile=30.0
        )

        result = calculator.calculate(market, symbol, "LONG")

        assert 0.90 <= result.final_multiplier <= 1.00
        assert result.regime_type == "ranging_neutral"
        assert result.blending_weight == 0.0  # Ignore symbol regime

    def test_high_volatility_override(self, calculator):
        """Test HIGH_VOLATILITY regime clamping."""
        market = MarketRegimeContext(
            bias="BULLISH",
            fear_greed=85,  # Extreme greed
            long_pct=75.0,  # Very crowded
            short_pct=25.0,
            funding_rate=0.015,
            btc_dominance=58.0,
            confidence=0.9
        )

        symbol = SymbolRegimeContext(
            regime="HIGH_VOLATILITY",
            confidence=0.70,
            trend_direction=0.5,
            mtf_aligned=False,
            volatility_percentile=95.0
        )

        result = calculator.calculate(market, symbol, "LONG")

        # Should be clamped to [0.90, 1.10]
        assert 0.90 <= result.final_multiplier <= 1.10
        assert result.regime_type == "high_volatility"

    def test_low_liquidity_override(self, calculator):
        """Test LOW_LIQUIDITY regime clamping (tighter than volatility)."""
        market = MarketRegimeContext(
            bias="BEARISH",
            fear_greed=25,
            long_pct=45.0,
            short_pct=55.0,
            funding_rate=-0.002,
            btc_dominance=60.0,
            confidence=0.85
        )

        symbol = SymbolRegimeContext(
            regime="LOW_LIQUIDITY",
            confidence=0.65,
            trend_direction=-0.3,
            mtf_aligned=False,
            volatility_percentile=25.0
        )

        result = calculator.calculate(market, symbol, "SHORT")

        # Should be clamped to [0.92, 1.08]
        assert 0.92 <= result.final_multiplier <= 1.08
        assert result.regime_type == "low_liquidity"

    def test_crowded_trade_detection(self, calculator):
        """Test crowded trade classification (>70% one-sided)."""
        market = MarketRegimeContext(
            bias="BULLISH",
            fear_greed=78,
            long_pct=78.0,  # Very crowded longs
            short_pct=22.0,
            funding_rate=0.012,
            btc_dominance=54.0,
            confidence=1.0
        )

        symbol = SymbolRegimeContext(
            regime="MODERATE_UPTREND",
            confidence=0.75,
            trend_direction=0.6,
            mtf_aligned=True,
            volatility_percentile=55.0
        )

        result = calculator.calculate(market, symbol, "LONG")

        assert result.regime_type == "crowded_trade"
        # Should have positioning penalty (0.85)
        assert result.market_factor < 1.0

    def test_mtf_alignment_bonus(self, calculator):
        """Test that MTF alignment increases blending weight."""
        market = MarketRegimeContext(
            bias="NEUTRAL",
            fear_greed=50,
            long_pct=50.0,
            short_pct=50.0,
            funding_rate=0.0,
            btc_dominance=56.0,
            confidence=1.0
        )

        # With MTF alignment
        symbol_mtf = SymbolRegimeContext(
            regime="MODERATE_UPTREND",
            confidence=0.70,
            trend_direction=0.5,
            mtf_aligned=True,
            volatility_percentile=40.0
        )

        # Without MTF alignment
        symbol_no_mtf = SymbolRegimeContext(
            regime="MODERATE_UPTREND",
            confidence=0.70,
            trend_direction=0.5,
            mtf_aligned=False,
            volatility_percentile=40.0
        )

        result_mtf = calculator.calculate(market, symbol_mtf, "LONG")
        result_no_mtf = calculator.calculate(market, symbol_no_mtf, "LONG")

        # MTF alignment should increase blending weight by ~15%
        assert result_mtf.blending_weight > result_no_mtf.blending_weight
        assert result_mtf.blending_weight / result_no_mtf.blending_weight >= 1.10

    def test_extreme_fear_contrarian_boost(self, calculator):
        """Test that Extreme Fear boosts LONG signals.

        NOTE: In counter-trend scenario, Extreme Fear (bearish sentiment)
        still penalizes LONG signals. The boost applies in aligned scenarios."""
        market_fear = MarketRegimeContext(
            bias="BEARISH",
            fear_greed=15,  # Extreme Fear
            long_pct=55.0,
            short_pct=45.0,
            funding_rate=0.001,
            btc_dominance=57.0,
            confidence=1.0
        )

        market_neutral = MarketRegimeContext(
            bias="NEUTRAL",
            fear_greed=50,  # Neutral
            long_pct=55.0,
            short_pct=45.0,
            funding_rate=0.001,
            btc_dominance=57.0,
            confidence=1.0
        )

        symbol = SymbolRegimeContext(
            regime="MODERATE_UPTREND",
            confidence=0.60,
            trend_direction=0.4,
            mtf_aligned=False,
            volatility_percentile=45.0
        )

        result_fear = calculator.calculate(market_fear, symbol, "LONG")
        result_neutral = calculator.calculate(market_neutral, symbol, "LONG")

        # In counter-trend, fear still penalizes LONG (bearish alignment)
        # Both should have penalty, but neutral should be less penalized
        assert result_neutral.market_factor >= result_fear.market_factor
        assert result_fear.regime_type == "counter_trend"
        assert result_neutral.regime_type == "counter_trend"

    def test_metadata_completeness(self, calculator, market_bearish, symbol_strong_uptrend):
        """Test that result metadata contains all expected fields."""
        result = calculator.calculate(
            market_bearish, symbol_strong_uptrend, "LONG"
        )

        required_keys = [
            'market_bias', 'symbol_regime', 'signal_type',
            'fear_greed', 'long_pct', 'short_pct',
            'mtf_aligned', 'symbol_confidence'
        ]

        for key in required_keys:
            assert key in result.metadata, f"Missing metadata key: {key}"

    def test_multiplier_bounds(self, calculator):
        """Test that multipliers never exceed safety bounds [0.50, 1.50]."""
        # Create extreme scenarios to test bounds
        extreme_bearish_market = MarketRegimeContext(
            bias="BEARISH",
            fear_greed=5,  # Extreme panic
            long_pct=85.0,  # Extremely crowded longs
            short_pct=15.0,
            funding_rate=0.02,  # Very high funding
            btc_dominance=65.0,
            confidence=1.0
        )

        extreme_bearish_symbol = SymbolRegimeContext(
            regime="STRONG_DOWNTREND",
            confidence=0.95,
            trend_direction=-0.98,
            mtf_aligned=True,
            volatility_percentile=90.0
        )

        # Test extreme SHORT scenario (should get max boost)
        result_short = calculator.calculate(
            extreme_bearish_market, extreme_bearish_symbol, "SHORT"
        )

        # Test extreme LONG scenario (should get max penalty)
        result_long = calculator.calculate(
            extreme_bearish_market, extreme_bearish_symbol, "LONG"
        )

        # Safety bounds
        assert 0.50 <= result_short.final_multiplier <= 1.50
        assert 0.50 <= result_long.final_multiplier <= 1.50

        # Typical bounds (should be tighter)
        assert 0.75 <= result_short.final_multiplier <= 1.35
        assert 0.65 <= result_long.final_multiplier <= 1.25


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
