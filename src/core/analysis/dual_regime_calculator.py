"""
Dual-Regime Signal Enhancement Calculator

Combines market-wide regime (Fear & Greed, funding rates, BTC dominance) with
symbol-specific regime (trend strength, volatility, MTF alignment) through
confidence-weighted blending to adjust confluence signal scores.

Key Innovation:
- Bidirectional relative strength detection (buy strong in weak markets, short weak in strong markets)
- Adaptive confidence weighting (0-75% symbol influence, market always retains 25% minimum)
- Conservative multiplier ranges (0.75-1.25x market factor, 0.85-1.15x symbol factor)

Author: Virtuoso Team + Claude + Quant Agent
Version: 1.0.0 (Phase 1 - Discrete Alignment)
Created: 2025-12-16
Documentation: docs/08-features/trading/DUAL_REGIME_SIGNAL_ENHANCEMENT.md
"""

import logging
from typing import Dict, Any, Optional

# Import dataclasses from schema file
from src.core.schemas.dual_regime import (
    MarketRegimeContext,
    SymbolRegimeContext,
    DualRegimeResult
)

logger = logging.getLogger(__name__)


class DualRegimeCalculator:
    """
    Calculates regime-adjusted multiplier for confluence scores.

    Phase 1 Implementation:
    - Uses discrete alignment factors (0.80, 0.95, 1.15)
    - 3-level market bias (BULLISH=+1, NEUTRAL=0, BEARISH=-1)
    - Proven, conservative approach

    Usage:
        calculator = DualRegimeCalculator(config)
        result = calculator.calculate(
            market_context=market_regime,
            symbol_context=symbol_regime,
            signal_type="LONG"
        )
        adjusted_score = base_score * result.final_multiplier
    """

    # Fear & Greed Index thresholds
    FEAR_GREED_EXTREME_LOW = 20       # <20 = Extreme Fear
    FEAR_GREED_FEAR = 40              # <40 = Fear
    FEAR_GREED_GREED = 60             # >60 = Greed
    FEAR_GREED_EXTREME_HIGH = 80      # >80 = Extreme Greed

    # Position crowding thresholds
    LONG_RATIO_THRESHOLD = 60.0       # >60% longs = crowded
    SHORT_RATIO_THRESHOLD = 60.0      # >60% shorts = crowded

    # Sentiment factor multipliers
    SENTIMENT_EXTREME_CONTRARIAN = 1.15   # Extreme Fear + LONG (or Extreme Greed + SHORT)
    SENTIMENT_MODERATE_CONTRARIAN = 1.08
    SENTIMENT_NEUTRAL = 1.00
    SENTIMENT_MODERATE_PENALTY = 0.92
    SENTIMENT_EXTREME_PENALTY = 0.85

    # Positioning factor multipliers
    POSITIONING_CONTRARIAN_BOOST = 1.15   # Crowded opposite side
    POSITIONING_CROWDED_PENALTY = 0.85    # Crowded same side
    POSITIONING_NEUTRAL = 1.00

    # Alignment factor multipliers (Phase 1: discrete)
    ALIGNMENT_ALIGNED = 1.15          # Market bias matches signal direction
    ALIGNMENT_NEUTRAL = 0.95          # Neutral market or mixed signals
    ALIGNMENT_MISALIGNED = 0.80       # Relative strength play (signal against market)

    # Symbol regime base multipliers
    REGIME_BASE_MULTIPLIERS = {
        'STRONG_UPTREND': 1.15,
        'MODERATE_UPTREND': 1.08,
        'RANGING': 1.00,
        'MODERATE_DOWNTREND': 0.92,
        'STRONG_DOWNTREND': 0.85,
        'HIGH_VOLATILITY': 1.00,      # Special case (handled separately)
        'LOW_LIQUIDITY': 1.00,        # Special case
    }

    # Confidence weighting thresholds
    CONFIDENCE_MIN_THRESHOLD = 0.40   # Below this, ignore symbol regime
    MTF_ALIGNMENT_BONUS = 1.15        # +15% bonus for MTF agreement

    # Blending weight caps
    MAX_SYMBOL_INFLUENCE = 0.75       # Market always retains 25% minimum
    MIN_MARKET_INFLUENCE = 0.25

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize calculator with optional configuration overrides.

        Args:
            config: Dictionary of parameter overrides (from regime_parameters.yaml)
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.DualRegimeCalculator")

        # Allow config overrides for thresholds (useful for backtesting)
        if config:
            self._apply_config_overrides(config)

    def _apply_config_overrides(self, config: Dict[str, Any]):
        """Apply configuration overrides to class constants."""
        fear_greed_cfg = config.get('fear_greed', {})
        if 'extreme_fear' in fear_greed_cfg:
            self.FEAR_GREED_EXTREME_LOW = fear_greed_cfg['extreme_fear']
        if 'extreme_greed' in fear_greed_cfg:
            self.FEAR_GREED_EXTREME_HIGH = fear_greed_cfg['extreme_greed']

        positioning_cfg = config.get('positioning', {})
        if 'long_crowded_threshold' in positioning_cfg:
            self.LONG_RATIO_THRESHOLD = positioning_cfg['long_crowded_threshold']
        if 'short_crowded_threshold' in positioning_cfg:
            self.SHORT_RATIO_THRESHOLD = positioning_cfg['short_crowded_threshold']

    def calculate(
        self,
        market_context: MarketRegimeContext,
        symbol_context: SymbolRegimeContext,
        signal_type: str,  # "LONG" or "SHORT"
    ) -> DualRegimeResult:
        """
        Calculate dual-regime multiplier for a signal.

        Args:
            market_context: Market-wide regime data
            symbol_context: Symbol-specific regime data
            signal_type: "LONG" or "SHORT"

        Returns:
            DualRegimeResult with final_multiplier and detailed breakdown

        Example:
            >>> result = calculator.calculate(market, symbol, "LONG")
            >>> adjusted_score = 72 * result.final_multiplier  # 72 → 71.6
        """
        # Step 1: Calculate market factor (3 components: sentiment × positioning × alignment)
        market_factor = self._calculate_market_factor(market_context, signal_type)

        # Step 2: Calculate symbol factor (regime × direction interaction)
        symbol_factor = self._calculate_symbol_factor(symbol_context, signal_type)

        # Step 3: Calculate blending weight (confidence-driven, 0-75% symbol influence)
        blending_weight = self._calculate_blending_weight(
            symbol_context, market_context, signal_type
        )

        # Step 4: Blend factors with special regime overrides
        final_multiplier = self._blend_factors(
            market_factor, symbol_factor, blending_weight, symbol_context.regime
        )

        # Step 5: Classify regime type for monitoring
        regime_type = self._classify_regime_type(
            market_context, symbol_context, signal_type
        )

        # Step 6: Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            market_context, symbol_context, blending_weight
        )

        return DualRegimeResult(
            final_multiplier=final_multiplier,
            market_factor=market_factor,
            symbol_factor=symbol_factor,
            blending_weight=blending_weight,
            regime_type=regime_type,
            confidence=confidence,
            metadata={
                'market_bias': market_context.bias,
                'symbol_regime': symbol_context.regime,
                'signal_type': signal_type,
                'fear_greed': market_context.fear_greed,
                'long_pct': market_context.long_pct,
                'short_pct': market_context.short_pct,
                'mtf_aligned': symbol_context.mtf_aligned,
                'symbol_confidence': symbol_context.confidence,
            }
        )

    def _calculate_market_factor(
        self, context: MarketRegimeContext, signal_type: str
    ) -> float:
        """
        Calculate market-wide regime factor.

        Combines 3 components:
        1. Sentiment (Fear & Greed contrarian logic)
        2. Positioning (Long/Short ratio crowding detection)
        3. Alignment (market bias × signal direction)

        Returns:
            Market factor ∈ [0.75, 1.25]
        """
        # Component 1: Sentiment factor (contrarian logic)
        sentiment_factor = self._calculate_sentiment_factor(
            context.fear_greed, signal_type
        )

        # Component 2: Positioning factor (crowding detection)
        positioning_factor = self._calculate_positioning_factor(
            context.long_pct, context.short_pct, signal_type
        )

        # Component 3: Alignment factor (discrete Phase 1)
        alignment_factor = self._calculate_alignment_factor(
            context.bias, signal_type
        )

        # Combined market factor
        market_factor = sentiment_factor * positioning_factor * alignment_factor

        # Clamp to [0.75, 1.25] for safety
        return max(0.75, min(1.25, market_factor))

    def _calculate_sentiment_factor(self, fear_greed: int, signal_type: str) -> float:
        """
        Calculate sentiment factor from Fear & Greed Index.

        Contrarian logic:
        - Extreme Fear + LONG signal = bullish opportunity (boost)
        - Extreme Greed + SHORT signal = bearish opportunity (boost)
        - Extreme Fear + SHORT signal = fight the bottom (penalize)
        - Extreme Greed + LONG signal = chase the top (penalize)
        """
        if signal_type == 'LONG':
            if fear_greed < self.FEAR_GREED_EXTREME_LOW:
                return self.SENTIMENT_EXTREME_CONTRARIAN  # Extreme Fear = buy
            elif fear_greed < self.FEAR_GREED_FEAR:
                return self.SENTIMENT_MODERATE_CONTRARIAN  # Fear = moderate buy
            elif fear_greed > self.FEAR_GREED_EXTREME_HIGH:
                return self.SENTIMENT_EXTREME_PENALTY  # Extreme Greed = avoid longs
            elif fear_greed > self.FEAR_GREED_GREED:
                return self.SENTIMENT_MODERATE_PENALTY  # Greed = caution
            else:
                return self.SENTIMENT_NEUTRAL

        else:  # SHORT
            if fear_greed > self.FEAR_GREED_EXTREME_HIGH:
                return self.SENTIMENT_EXTREME_CONTRARIAN  # Extreme Greed = sell
            elif fear_greed > self.FEAR_GREED_GREED:
                return self.SENTIMENT_MODERATE_CONTRARIAN  # Greed = moderate sell
            elif fear_greed < self.FEAR_GREED_EXTREME_LOW:
                return self.SENTIMENT_EXTREME_PENALTY  # Extreme Fear = avoid shorts
            elif fear_greed < self.FEAR_GREED_FEAR:
                return self.SENTIMENT_MODERATE_PENALTY  # Fear = caution
            else:
                return self.SENTIMENT_NEUTRAL

    def _calculate_positioning_factor(
        self, long_pct: float, short_pct: float, signal_type: str
    ) -> float:
        """
        Calculate positioning factor from Long/Short ratio.

        Contrarian crowding logic:
        - If longs crowded (>60%), penalize LONG signals (liquidation risk)
        - If shorts crowded (>60%), penalize SHORT signals (squeeze risk)
        - If longs crowded, boost SHORT signals (distribution opportunity)
        - If shorts crowded, boost LONG signals (cover/squeeze opportunity)
        """
        if signal_type == 'LONG':
            if long_pct > self.LONG_RATIO_THRESHOLD:
                return self.POSITIONING_CROWDED_PENALTY  # Crowded longs = bearish
            elif short_pct > self.SHORT_RATIO_THRESHOLD:
                return self.POSITIONING_CONTRARIAN_BOOST  # Crowded shorts = bullish
            else:
                return self.POSITIONING_NEUTRAL

        else:  # SHORT
            if short_pct > self.SHORT_RATIO_THRESHOLD:
                return self.POSITIONING_CROWDED_PENALTY  # Crowded shorts = bullish
            elif long_pct > self.LONG_RATIO_THRESHOLD:
                return self.POSITIONING_CONTRARIAN_BOOST  # Crowded longs = bearish
            else:
                return self.POSITIONING_NEUTRAL

    def _calculate_alignment_factor(self, market_bias: str, signal_type: str) -> float:
        """
        Calculate alignment factor (Phase 1: discrete).

        Maps market bias (BULLISH/NEUTRAL/BEARISH) to numeric value,
        compares to signal direction, returns discrete alignment factor.

        Phase 1 mapping:
        - BULLISH × LONG = +1 (aligned) → 1.15x
        - BEARISH × SHORT = +1 (aligned) → 1.15x
        - BULLISH × SHORT = -1 (misaligned) → 0.80x (relative weakness play)
        - BEARISH × LONG = -1 (misaligned) → 0.80x (relative strength play)
        - NEUTRAL × any = 0 → 0.95x
        """
        # Map market bias to numeric value
        bias_map = {
            "BULLISH": 1,
            "NEUTRAL": 0,
            "BEARISH": -1
        }
        market_bias_value = bias_map.get(market_bias, 0)

        # Map signal type to direction
        signal_direction = 1 if signal_type == 'LONG' else -1

        # Calculate alignment score
        alignment_score = market_bias_value * signal_direction

        # Map to discrete factor (Phase 1)
        if alignment_score == 1:
            return self.ALIGNMENT_ALIGNED  # Aligned momentum
        elif alignment_score == 0:
            return self.ALIGNMENT_NEUTRAL  # Neutral/mixed
        else:  # alignment_score == -1
            return self.ALIGNMENT_MISALIGNED  # Relative strength play

    def _calculate_symbol_factor(
        self, context: SymbolRegimeContext, signal_type: str
    ) -> float:
        """
        Calculate symbol-specific regime factor.

        Uses symmetric formula:
            factor = 1.0 + (base_multiplier - 1.0) × trend_direction

        Where:
        - base_multiplier from REGIME_BASE_MULTIPLIERS (e.g., STRONG_UPTREND = 1.15)
        - trend_direction = +1 for LONG, -1 for SHORT

        This creates automatic symmetry:
        - LONG in STRONG_UPTREND: 1.0 + (1.15-1.0)×1 = 1.15 (boost)
        - SHORT in STRONG_DOWNTREND: 1.0 + (0.85-1.0)×(-1) = 1.15 (boost)
        - LONG in STRONG_DOWNTREND: 1.0 + (0.85-1.0)×1 = 0.85 (penalty)
        - SHORT in STRONG_UPTREND: 1.0 + (1.15-1.0)×(-1) = 0.85 (penalty)

        Returns:
            Symbol factor ∈ [0.85, 1.15]
        """
        base_multiplier = self.REGIME_BASE_MULTIPLIERS.get(context.regime, 1.00)
        trend_direction = 1.0 if signal_type == 'LONG' else -1.0

        # Symmetric deviation calculation
        deviation = (base_multiplier - 1.00) * trend_direction

        return 1.00 + deviation

    def _calculate_blending_weight(
        self,
        symbol_ctx: SymbolRegimeContext,
        market_ctx: MarketRegimeContext,
        signal_type: str
    ) -> float:
        """
        Calculate confidence-weighted blending weight.

        Determines how much to trust symbol regime vs market regime.

        Logic:
        - Low symbol confidence (<0.40) → ignore symbol regime (weight=0)
        - High confidence + MTF alignment → high symbol influence (weight→0.75)
        - Misalignment penalty reduces weight (relative strength needs high confidence)

        Returns:
            Blending weight ∈ [0, 0.75] (market always retains 25% minimum)
        """
        confidence = symbol_ctx.confidence

        # Base weight from confidence tiers
        if confidence < self.CONFIDENCE_MIN_THRESHOLD:
            base_weight = 0.0  # Ignore unreliable symbol regime
        elif confidence < 0.60:
            # Linear interpolation: 0.40→0.05, 0.60→0.30
            base_weight = 0.05 + (confidence - 0.40) * 1.25
        elif confidence < 0.75:
            # Linear interpolation: 0.60→0.30, 0.75→0.50
            base_weight = 0.30 + (confidence - 0.60) * 1.33
        elif confidence < 0.85:
            # Linear interpolation: 0.75→0.50, 0.85→0.65
            base_weight = 0.50 + (confidence - 0.75) * 1.50
        else:
            # High confidence: 0.85→0.65, 1.00→0.75
            base_weight = 0.65 + (confidence - 0.85) * 0.67

        # MTF alignment bonus (+15%)
        if symbol_ctx.mtf_aligned:
            base_weight = min(self.MAX_SYMBOL_INFLUENCE, base_weight * self.MTF_ALIGNMENT_BONUS)

        # Directional alignment adjustment
        # If symbol trend opposes market bias (relative strength), require higher confidence
        bias_map = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
        market_bias_value = bias_map.get(market_ctx.bias, 0)
        directional_alignment = symbol_ctx.trend_direction * market_bias_value

        if directional_alignment < -0.5:
            # Strong misalignment (relative strength play)
            base_weight *= 0.85  # Reduce symbol influence slightly
        elif directional_alignment > 0.5:
            # Strong alignment (momentum play)
            base_weight = min(self.MAX_SYMBOL_INFLUENCE, base_weight * 1.10)

        return max(0.0, min(self.MAX_SYMBOL_INFLUENCE, base_weight))

    def _blend_factors(
        self, market: float, symbol: float, weight: float, regime: str
    ) -> float:
        """
        Blend market and symbol factors with special regime overrides.

        Formula:
            final = market × (1 - weight) + symbol × weight

        Special overrides for risk management:
        - HIGH_VOLATILITY: Clamp to [0.90, 1.10] (conservative)
        - LOW_LIQUIDITY: Clamp to [0.92, 1.08] (very conservative)

        Returns:
            Final multiplier (typically [0.75, 1.25])
        """
        # Standard blending
        final = market * (1.0 - weight) + symbol * weight

        # Special regime overrides
        if regime == 'HIGH_VOLATILITY':
            final = max(0.90, min(1.10, final))
            self.logger.debug(f"HIGH_VOLATILITY override: clamped to {final:.3f}")
        elif regime == 'LOW_LIQUIDITY':
            final = max(0.92, min(1.08, final))
            self.logger.debug(f"LOW_LIQUIDITY override: clamped to {final:.3f}")

        return final

    def _classify_regime_type(
        self,
        market: MarketRegimeContext,
        symbol: SymbolRegimeContext,
        signal: str
    ) -> str:
        """
        Classify regime combination for monitoring/analysis.

        Categories:
        - aligned_momentum: Market and symbol both trending same direction
        - relative_strength: Symbol strong while market weak (or inverse)
        - counter_trend: Signal against both market and symbol trend
        - ranging_neutral: Both regimes neutral/ranging
        - high_volatility: Volatility override active
        - low_liquidity: Liquidity override active
        - crowded_trade: Positioning >70% one-sided
        """
        # Special regime overrides first
        if symbol.regime == 'HIGH_VOLATILITY':
            return 'high_volatility'
        if symbol.regime == 'LOW_LIQUIDITY':
            return 'low_liquidity'

        # Crowded trade detection
        if market.long_pct > 70 or market.short_pct > 70:
            return 'crowded_trade'

        # Alignment classification
        bias_map = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
        market_bias_value = bias_map.get(market.bias, 0)
        signal_direction = 1 if signal == 'LONG' else -1

        market_signal_alignment = market_bias_value * signal_direction
        symbol_signal_alignment = symbol.trend_direction * signal_direction

        if market_signal_alignment == 1 and symbol_signal_alignment > 0.5:
            return 'aligned_momentum'
        elif market_signal_alignment == -1 and symbol_signal_alignment > 0.5:
            return 'relative_strength'
        elif abs(market_bias_value) < 0.1 and abs(symbol.trend_direction) < 0.3:
            return 'ranging_neutral'
        else:
            return 'counter_trend'

    def _calculate_overall_confidence(
        self,
        market: MarketRegimeContext,
        symbol: SymbolRegimeContext,
        weight: float
    ) -> float:
        """
        Calculate overall confidence in the adjustment.

        Weighted average of market and symbol confidence.

        Returns:
            Overall confidence ∈ [0, 1]
        """
        return market.confidence * (1.0 - weight) + symbol.confidence * weight
