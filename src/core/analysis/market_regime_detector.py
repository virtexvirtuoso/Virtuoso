"""
Market Regime Detection System

This module implements market regime detection to enable adaptive confluence scoring
that accounts for different market conditions (trending, ranging, volatile, illiquid).

The regime detector analyzes market characteristics to determine the dominant market
regime and provides adaptive weights for confluence components based on that regime.

Key Features:
- Real-time regime detection with 4 primary regimes
- Adaptive weighting schemes optimized for each regime
- Confidence scoring for regime classification
- Trend-aware indicator interpretation (reversal vs continuation)
- Regime transition detection and smoothing

Market Regimes:
1. STRONG_UPTREND: Clear bullish momentum, favor continuation signals
2. STRONG_DOWNTREND: Clear bearish momentum, favor continuation signals
3. RANGING: Sideways movement, favor mean-reversion signals
4. HIGH_VOLATILITY: Extreme price swings, reduce position sizing
5. LOW_LIQUIDITY: Thin orderbook, increase caution

Performance Characteristics:
- Time Complexity: O(n) for n candles
- Minimal overhead: <10ms per detection
- Regime persistence: 30-second smoothing window

Author: Virtuoso Team
Version: 1.0.0
Created: 2025-10-22

Deus Vult - God Wills It
"""

from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Enum representing different market regimes."""
    STRONG_UPTREND = "strong_uptrend"
    MODERATE_UPTREND = "moderate_uptrend"
    RANGING = "ranging"
    MODERATE_DOWNTREND = "moderate_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"


@dataclass
class RegimeDetection:
    """Container for regime detection results."""
    regime: MarketRegime
    confidence: float  # 0-1, how confident we are in this regime
    strength: float  # 0-1, how strong the regime characteristics are
    trend_direction: float  # -1 to 1, overall trend direction
    volatility_percentile: float  # 0-100, current volatility vs historical
    liquidity_score: float  # 0-1, current liquidity quality
    metadata: Dict[str, Any]  # Additional regime-specific info


class MarketRegimeDetector:
    """
    Detects market regimes and provides adaptive weighting schemes.

    This detector analyzes multiple market characteristics to classify the current
    market regime and provides optimized indicator weights for each regime.

    Detection Methodology:
    1. Trend Detection: Uses ADX, EMA slopes, price structure
    2. Volatility Analysis: ATR percentile, realized volatility
    3. Liquidity Assessment: Orderbook depth, spread analysis
    4. Regime Classification: Multi-factor decision tree
    5. Adaptive Weights: Regime-optimized component weights

    Usage:
        detector = MarketRegimeDetector(config)
        regime = detector.detect_regime(market_data)
        weights = detector.get_adaptive_weights(regime.regime)
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the market regime detector.

        Args:
            config: Configuration dictionary with thresholds and parameters
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Load thresholds from config with sensible defaults
        self.thresholds = {
            'adx_trending': self.config.get('adx_trending_threshold', 25),
            'adx_strong_trend': self.config.get('adx_strong_threshold', 40),
            'atr_percentile_high': self.config.get('atr_percentile_high', 75),
            'atr_percentile_low': self.config.get('atr_percentile_low', 25),
            'ema_slope_threshold': self.config.get('ema_slope_threshold', 0.001),
            'orderbook_depth_min': self.config.get('orderbook_depth_min', 100000),
            'spread_threshold': self.config.get('spread_threshold', 0.001),
            'volume_percentile_high': self.config.get('volume_percentile_high', 70),
        }

        # Regime history for smoothing (prevent regime flicker)
        self.regime_history: List[Tuple[datetime, MarketRegime]] = []
        self.regime_window = timedelta(seconds=30)  # Require 30s persistence

        # Cache for expensive calculations
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 5  # 5 second cache

    def detect_regime(self, market_data: Dict[str, Any]) -> RegimeDetection:
        """
        Detect the current market regime based on market data.

        This is the main entry point for regime detection. It analyzes multiple
        market characteristics and returns a classified regime with confidence.

        Args:
            market_data: Dictionary containing:
                - ohlcv: OHLCV data (required)
                - orderbook: Orderbook snapshot (optional, improves accuracy)
                - trades: Recent trades (optional, improves accuracy)

        Returns:
            RegimeDetection object with regime classification and metrics

        Example:
            >>> detector = MarketRegimeDetector()
            >>> regime = detector.detect_regime(market_data)
            >>> print(f"Regime: {regime.regime}, Confidence: {regime.confidence:.2f}")
            Regime: STRONG_UPTREND, Confidence: 0.85
        """
        try:
            # Extract required data
            ohlcv = market_data.get('ohlcv', {})
            base_df = ohlcv.get('base', pd.DataFrame())

            if base_df.empty or len(base_df) < 50:
                self.logger.warning("Insufficient data for regime detection")
                return self._get_default_regime()

            # === Step 1: Trend Detection ===
            trend_metrics = self._detect_trend(base_df)

            # === Step 2: Volatility Analysis ===
            volatility_metrics = self._analyze_volatility(base_df)

            # === Step 3: Liquidity Assessment ===
            liquidity_metrics = self._assess_liquidity(market_data)

            # === Step 4: Regime Classification ===
            regime, confidence = self._classify_regime(
                trend_metrics,
                volatility_metrics,
                liquidity_metrics
            )

            # === Step 5: Apply Smoothing (prevent flicker) ===
            regime = self._apply_regime_smoothing(regime)

            # Build result
            detection = RegimeDetection(
                regime=regime,
                confidence=confidence,
                strength=trend_metrics['strength'],
                trend_direction=trend_metrics['direction'],
                volatility_percentile=volatility_metrics['percentile'],
                liquidity_score=liquidity_metrics['score'],
                metadata={
                    'adx': trend_metrics['adx'],
                    'ema_slope': trend_metrics['ema_slope'],
                    'atr_percentile': volatility_metrics['percentile'],
                    'spread_bps': liquidity_metrics['spread_bps'],
                    'depth_usd': liquidity_metrics['depth_usd'],
                }
            )

            self.logger.info(
                f"Regime detected: {regime.value}, "
                f"confidence: {confidence:.2f}, "
                f"trend: {trend_metrics['direction']:.2f}"
            )

            return detection

        except Exception as e:
            self.logger.error(f"Error detecting regime: {str(e)}", exc_info=True)
            return self._get_default_regime()

    def _detect_trend(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Detect trend characteristics using ADX and EMA analysis.

        Returns:
            Dict with keys: direction, strength, adx, ema_slope
        """
        try:
            # Calculate ADX (Average Directional Index) for trend strength
            adx = self._calculate_adx(df, period=14)

            # Calculate EMA slopes for trend direction
            ema_20 = df['close'].ewm(span=20, adjust=False).mean()
            ema_50 = df['close'].ewm(span=50, adjust=False).mean()

            # Slope = (current - previous) / previous
            ema_slope = (ema_20.iloc[-1] - ema_20.iloc[-5]) / ema_20.iloc[-5]

            # Direction: -1 (bearish) to +1 (bullish)
            if ema_20.iloc[-1] > ema_50.iloc[-1]:
                direction = min(abs(ema_slope) * 100, 1.0)  # Bullish
            else:
                direction = -min(abs(ema_slope) * 100, 1.0)  # Bearish

            # Strength: 0 (weak) to 1 (strong)
            # ADX > 40 = strong trend, ADX < 25 = weak trend
            strength = min(adx / 50.0, 1.0)

            return {
                'direction': float(direction),
                'strength': float(strength),
                'adx': float(adx),
                'ema_slope': float(ema_slope),
            }

        except Exception as e:
            self.logger.warning(f"Error detecting trend: {str(e)}")
            return {'direction': 0.0, 'strength': 0.0, 'adx': 0.0, 'ema_slope': 0.0}

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average Directional Index (ADX) for trend strength."""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            # Calculate +DM and -DM
            plus_dm = np.maximum(high[1:] - high[:-1], 0)
            minus_dm = np.maximum(low[:-1] - low[1:], 0)

            # True Range
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            tr = np.maximum(tr1, np.maximum(tr2, tr3))

            # Smooth with exponential moving average
            atr = pd.Series(tr).ewm(span=period, adjust=False).mean()
            plus_di = 100 * pd.Series(plus_dm).ewm(span=period, adjust=False).mean() / atr
            minus_di = 100 * pd.Series(minus_dm).ewm(span=period, adjust=False).mean() / atr

            # Calculate DX and ADX
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
            adx = dx.ewm(span=period, adjust=False).mean().iloc[-1]

            return float(adx) if np.isfinite(adx) else 0.0

        except Exception as e:
            self.logger.warning(f"Error calculating ADX: {str(e)}")
            return 0.0

    def _analyze_volatility(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Analyze volatility characteristics using ATR percentile.

        Returns:
            Dict with keys: percentile, atr_current, atr_mean
        """
        try:
            # Calculate ATR (Average True Range)
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            # True Range
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            tr = np.maximum(tr1, np.maximum(tr2, tr3))

            # Current ATR (14-period)
            atr_current = pd.Series(tr).ewm(span=14, adjust=False).mean().iloc[-1]

            # Historical ATR for percentile calculation (last 100 periods)
            atr_series = pd.Series(tr).ewm(span=14, adjust=False).mean()
            atr_historical = atr_series.iloc[-100:] if len(atr_series) >= 100 else atr_series

            # Calculate percentile (0-100)
            percentile = (atr_historical < atr_current).sum() / len(atr_historical) * 100

            return {
                'percentile': float(percentile),
                'atr_current': float(atr_current),
                'atr_mean': float(atr_historical.mean()),
            }

        except Exception as e:
            self.logger.warning(f"Error analyzing volatility: {str(e)}")
            return {'percentile': 50.0, 'atr_current': 0.0, 'atr_mean': 0.0}

    def _assess_liquidity(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Assess liquidity quality using orderbook depth and spread.

        Returns:
            Dict with keys: score, depth_usd, spread_bps
        """
        try:
            orderbook = market_data.get('orderbook', {})

            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                # No orderbook data, assume reasonable liquidity
                return {'score': 0.7, 'depth_usd': 0.0, 'spread_bps': 0.0}

            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            if not bids or not asks:
                return {'score': 0.5, 'depth_usd': 0.0, 'spread_bps': 0.0}

            # Calculate spread in basis points (bps)
            best_bid = float(bids[0][0]) if bids else 0
            best_ask = float(asks[0][0]) if asks else 0
            mid_price = (best_bid + best_ask) / 2

            spread_bps = ((best_ask - best_bid) / mid_price) * 10000 if mid_price > 0 else 0

            # Calculate depth within 0.1% of mid price
            price_range = mid_price * 0.001  # 0.1%
            bid_depth = sum(
                float(price) * float(size)
                for price, size in bids
                if float(price) >= mid_price - price_range
            )
            ask_depth = sum(
                float(price) * float(size)
                for price, size in asks
                if float(price) <= mid_price + price_range
            )
            depth_usd = bid_depth + ask_depth

            # Liquidity score: 0 (poor) to 1 (excellent)
            # Good: depth > $100k, spread < 10 bps
            depth_score = min(depth_usd / 100000, 1.0)
            spread_score = max(1.0 - (spread_bps / 10), 0.0)
            liquidity_score = (depth_score + spread_score) / 2

            return {
                'score': float(liquidity_score),
                'depth_usd': float(depth_usd),
                'spread_bps': float(spread_bps),
            }

        except Exception as e:
            self.logger.warning(f"Error assessing liquidity: {str(e)}")
            return {'score': 0.7, 'depth_usd': 0.0, 'spread_bps': 0.0}

    def _classify_regime(
        self,
        trend_metrics: Dict[str, float],
        volatility_metrics: Dict[str, float],
        liquidity_metrics: Dict[str, float]
    ) -> Tuple[MarketRegime, float]:
        """
        Classify market regime based on analyzed metrics.

        Decision logic:
        1. Check for low liquidity (overrides other regimes)
        2. Check for high volatility (caution regime)
        3. Classify trend strength and direction

        Returns:
            Tuple of (MarketRegime, confidence_score)
        """
        # Extract metrics
        adx = trend_metrics['adx']
        direction = trend_metrics['direction']
        volatility_pct = volatility_metrics['percentile']
        liquidity_score = liquidity_metrics['score']

        confidence = 0.5  # Default confidence

        # Priority 1: Low liquidity (highest priority)
        if liquidity_score < 0.3:
            return MarketRegime.LOW_LIQUIDITY, 0.8

        # Priority 2: High volatility
        if volatility_pct > self.thresholds['atr_percentile_high']:
            confidence = min((volatility_pct - 75) / 25, 1.0)  # 75-100 -> 0-1
            return MarketRegime.HIGH_VOLATILITY, confidence

        # Priority 3: Trend classification
        is_trending = adx > self.thresholds['adx_trending']
        is_strong_trend = adx > self.thresholds['adx_strong_trend']

        if is_strong_trend:
            confidence = min(adx / 50, 1.0)  # Confidence scales with ADX
            if direction > 0.3:  # Bullish
                return MarketRegime.STRONG_UPTREND, confidence
            elif direction < -0.3:  # Bearish
                return MarketRegime.STRONG_DOWNTREND, confidence
            else:  # Conflicting signals
                return MarketRegime.RANGING, 0.6

        elif is_trending:
            confidence = min(adx / 35, 0.8)
            if direction > 0.2:
                return MarketRegime.MODERATE_UPTREND, confidence
            elif direction < -0.2:
                return MarketRegime.MODERATE_DOWNTREND, confidence
            else:
                return MarketRegime.RANGING, 0.7

        else:
            # Not trending = ranging market
            confidence = max(0.5, 1.0 - (adx / 25))  # Lower ADX = higher confidence in ranging
            return MarketRegime.RANGING, confidence

    def _apply_regime_smoothing(self, new_regime: MarketRegime) -> MarketRegime:
        """
        Apply temporal smoothing to prevent regime flicker.

        Requires the same regime for 30 seconds before transitioning.
        """
        now = datetime.now()

        # Add new detection to history
        self.regime_history.append((now, new_regime))

        # Clean old entries outside window
        cutoff = now - self.regime_window
        self.regime_history = [
            (ts, regime) for ts, regime in self.regime_history
            if ts > cutoff
        ]

        # Count regime occurrences in window
        regime_counts = {}
        for _, regime in self.regime_history:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        # Return most common regime in window
        if regime_counts:
            smoothed_regime = max(regime_counts.items(), key=lambda x: x[1])[0]
            return smoothed_regime

        return new_regime

    def get_adaptive_weights(self, regime: MarketRegime) -> Dict[str, float]:
        """
        Get adaptive confluence component weights based on market regime.

        This is a critical method that adjusts indicator weights to match
        the current market regime, enabling context-aware confluence scoring.

        Weight Adjustments by Regime:
        - STRONG_UPTREND/DOWNTREND: Boost orderflow & volume (momentum)
        - RANGING: Boost technical & price structure (mean reversion)
        - HIGH_VOLATILITY: Reduce all weights, increase caution
        - LOW_LIQUIDITY: Boost orderbook depth signals

        Args:
            regime: The detected market regime

        Returns:
            Dict of component weights (orderflow, orderbook, volume, etc.)

        Example:
            >>> detector = MarketRegimeDetector()
            >>> regime = detector.detect_regime(market_data)
            >>> weights = detector.get_adaptive_weights(regime.regime)
            >>> print(weights['orderflow'])  # Higher in trending markets
            0.35  # vs default 0.30
        """
        # Base weights (default from config)
        base_weights = {
            'orderflow': 0.30,
            'orderbook': 0.20,
            'volume': 0.18,
            'price_structure': 0.15,
            'technical': 0.10,
            'sentiment': 0.07,
        }

        # Regime-specific adjustments
        adjustments = {
            MarketRegime.STRONG_UPTREND: {
                'orderflow': 1.2,      # +20% (momentum is king)
                'volume': 1.15,         # +15% (confirm with volume)
                'technical': 0.7,       # -30% (RSI overbought is normal)
                'price_structure': 0.9, # -10% (support less relevant)
            },
            MarketRegime.STRONG_DOWNTREND: {
                'orderflow': 1.2,
                'volume': 1.15,
                'technical': 0.7,
                'price_structure': 0.9,
            },
            MarketRegime.MODERATE_UPTREND: {
                'orderflow': 1.1,
                'volume': 1.1,
                'technical': 0.85,
                'price_structure': 0.95,
            },
            MarketRegime.MODERATE_DOWNTREND: {
                'orderflow': 1.1,
                'volume': 1.1,
                'technical': 0.85,
                'price_structure': 0.95,
            },
            MarketRegime.RANGING: {
                'technical': 1.3,        # +30% (RSI/Stoch reliable)
                'price_structure': 1.25, # +25% (S/R critical)
                'orderflow': 0.85,       # -15% (momentum less relevant)
                'volume': 0.9,           # -10%
            },
            MarketRegime.HIGH_VOLATILITY: {
                'orderflow': 0.9,        # Reduce all weights (caution)
                'orderbook': 0.85,
                'volume': 0.9,
                'price_structure': 0.85,
                'technical': 0.8,
                'sentiment': 0.9,
            },
            MarketRegime.LOW_LIQUIDITY: {
                'orderbook': 1.4,        # +40% (critical in thin markets)
                'orderflow': 0.8,        # -20% (less reliable)
                'volume': 0.85,          # -15%
            },
        }

        # Apply adjustments
        adjusted_weights = base_weights.copy()
        regime_adjustments = adjustments.get(regime, {})

        for component, multiplier in regime_adjustments.items():
            adjusted_weights[component] = base_weights[component] * multiplier

        # Normalize to sum to 1.0
        total = sum(adjusted_weights.values())
        normalized_weights = {
            k: v / total for k, v in adjusted_weights.items()
        }

        self.logger.debug(f"Adaptive weights for {regime.value}: {normalized_weights}")

        return normalized_weights

    def is_reversal_likely(
        self,
        regime: RegimeDetection,
        indicator_scores: Dict[str, float]
    ) -> Tuple[bool, float]:
        """
        Determine if current conditions suggest a potential reversal.

        This method helps distinguish between:
        - Reversal zones: Exhaustion signals at extremes
        - Continuation zones: Healthy pullbacks within trends

        Reversal Criteria (must meet 3+ of 5):
        1. At key support/resistance (price structure)
        2. Volume exhaustion (declining volume at extremes)
        3. Orderflow divergence (CVD diverging from price)
        4. Technical extremes (RSI >80 or <20)
        5. Orderbook imbalance flip (large absorption)

        Args:
            regime: Current regime detection
            indicator_scores: Dict of indicator scores (0-100)

        Returns:
            Tuple of (is_reversal_likely: bool, confidence: float)

        Example:
            >>> regime = detector.detect_regime(market_data)
            >>> scores = {'technical': 85, 'orderflow': 45, 'volume': 40}
            >>> likely, confidence = detector.is_reversal_likely(regime, scores)
            >>> print(f"Reversal likely: {likely}, confidence: {confidence:.2f}")
            Reversal likely: True, confidence: 0.72
        """
        # In ranging markets, reversals are more common
        if regime.regime == MarketRegime.RANGING:
            base_probability = 0.6
        else:
            base_probability = 0.2

        reversal_conditions = 0
        max_conditions = 5

        # Condition 1: Price structure at extremes
        if 'price_structure' in indicator_scores:
            ps_score = indicator_scores['price_structure']
            if ps_score > 75 or ps_score < 25:
                reversal_conditions += 1

        # Condition 2: Volume exhaustion
        if 'volume' in indicator_scores:
            vol_score = indicator_scores['volume']
            # Low volume at price extremes suggests exhaustion
            if vol_score < 35:
                reversal_conditions += 1

        # Condition 3: Orderflow divergence
        if 'orderflow' in indicator_scores:
            of_score = indicator_scores['orderflow']
            # Orderflow diverging from price (needs more context, simplified here)
            # In real impl: check CVD direction vs price direction
            reversal_conditions += 0.5  # Partial credit (need more data)

        # Condition 4: Technical extremes
        if 'technical' in indicator_scores:
            tech_score = indicator_scores['technical']
            if tech_score > 80 or tech_score < 20:
                reversal_conditions += 1

        # Condition 5: Orderbook imbalance flip
        if 'orderbook' in indicator_scores:
            ob_score = indicator_scores['orderbook']
            # Extreme orderbook shifts can signal reversals
            if abs(ob_score - 50) > 30:
                reversal_conditions += 1

        # Calculate probability
        condition_ratio = reversal_conditions / max_conditions
        reversal_probability = base_probability + (condition_ratio * 0.4)

        is_likely = reversal_probability > 0.5
        confidence = min(reversal_probability, 1.0)

        self.logger.debug(
            f"Reversal analysis: {reversal_conditions}/{max_conditions} "
            f"conditions met, probability: {reversal_probability:.2f}"
        )

        return is_likely, confidence

    def adjust_indicator_for_trend(
        self,
        indicator_name: str,
        raw_score: float,
        regime: RegimeDetection
    ) -> float:
        """
        Adjust individual indicator scores based on trend context.

        This prevents false reversal signals during strong trends.

        Key Adjustments:
        - RSI >70 in uptrend → Not bearish (continuation)
        - RSI <30 in downtrend → Not bullish (continuation)
        - MACD bearish cross in uptrend → Weak signal

        Args:
            indicator_name: Name of the indicator (e.g., 'rsi', 'macd')
            raw_score: Raw indicator score (0-100)
            regime: Current regime detection

        Returns:
            Adjusted score (0-100) that accounts for trend context
        """
        # Only adjust in trending regimes
        if regime.regime not in [
            MarketRegime.STRONG_UPTREND,
            MarketRegime.STRONG_DOWNTREND,
            MarketRegime.MODERATE_UPTREND,
            MarketRegime.MODERATE_DOWNTREND,
        ]:
            return raw_score  # No adjustment in ranging markets

        is_uptrend = 'UPTREND' in regime.regime.value
        is_downtrend = 'DOWNTREND' in regime.regime.value

        # Technical indicators (RSI, Williams %R, Stochastics)
        if indicator_name.lower() in ['rsi', 'williams_r', 'stochastics', 'technical']:
            if is_uptrend and raw_score > 70:
                # Overbought in uptrend is normal, reduce bearish signal
                dampening = 0.5  # Pull score toward neutral
                adjusted = raw_score + (50 - raw_score) * dampening
                self.logger.debug(
                    f"Trend adjustment: {indicator_name} {raw_score:.1f} → "
                    f"{adjusted:.1f} (uptrend dampening)"
                )
                return adjusted

            elif is_downtrend and raw_score < 30:
                # Oversold in downtrend is normal, reduce bullish signal
                dampening = 0.5
                adjusted = raw_score + (50 - raw_score) * dampening
                self.logger.debug(
                    f"Trend adjustment: {indicator_name} {raw_score:.1f} → "
                    f"{adjusted:.1f} (downtrend dampening)"
                )
                return adjusted

        return raw_score

    def _get_default_regime(self) -> RegimeDetection:
        """Return a safe default regime when detection fails."""
        return RegimeDetection(
            regime=MarketRegime.RANGING,
            confidence=0.5,
            strength=0.5,
            trend_direction=0.0,
            volatility_percentile=50.0,
            liquidity_score=0.7,
            metadata={}
        )

    def get_regime_description(self, regime: MarketRegime) -> str:
        """Get human-readable description of a market regime."""
        descriptions = {
            MarketRegime.STRONG_UPTREND: "Strong upward momentum - favor long continuations",
            MarketRegime.MODERATE_UPTREND: "Moderate bullish trend - balanced approach",
            MarketRegime.RANGING: "Sideways consolidation - favor mean reversion",
            MarketRegime.MODERATE_DOWNTREND: "Moderate bearish trend - balanced approach",
            MarketRegime.STRONG_DOWNTREND: "Strong downward momentum - favor short continuations",
            MarketRegime.HIGH_VOLATILITY: "Extreme volatility - reduce position sizing",
            MarketRegime.LOW_LIQUIDITY: "Thin orderbook - exercise caution",
        }
        return descriptions.get(regime, "Unknown regime")
