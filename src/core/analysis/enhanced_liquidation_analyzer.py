"""
Enhanced Liquidation Analyzer - Phase 1 Implementation

This module provides advanced liquidation analysis combining base liquidation metrics
with technical analysis indicators including ADX, EMA crossovers, and support/resistance levels.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

@dataclass
class EnhancedLiquidationResult:
    """Result structure for enhanced liquidation analysis."""
    final_score: float
    reasoning: List[str]
    technical_indicators: Dict[str, float]
    confidence: float
    base_score: float
    enhancement_magnitude: float

class EnhancedLiquidationAnalyzer:
    """
    Enhanced liquidation analysis using technical indicators.

    Combines base liquidation scores with:
    - ADX (Average Directional Index) for trend strength
    - EMA crossovers for momentum detection
    - Support/Resistance levels for key price zones
    - Volume-price analysis for confirmation
    """

    def __init__(self,
                 adx_period: int = 14,
                 ema_short_period: int = 9,
                 ema_long_period: int = 21,
                 sr_lookback_periods: int = 50,
                 sr_distance_threshold: float = 0.02):
        """
        Initialize the enhanced liquidation analyzer.

        Args:
            adx_period: Period for ADX calculation
            ema_short_period: Period for short EMA
            ema_long_period: Period for long EMA
            sr_lookback_periods: Lookback periods for support/resistance
            sr_distance_threshold: Distance threshold for S/R levels (as percentage)
        """
        self.adx_period = adx_period
        self.ema_short_period = ema_short_period
        self.ema_long_period = ema_long_period
        self.sr_lookback_periods = sr_lookback_periods
        self.sr_distance_threshold = sr_distance_threshold

        self.logger = logging.getLogger(__name__)

        # Enhancement weights and thresholds
        self.enhancement_weights = {
            'adx_trend_strength': 0.25,
            'ema_momentum': 0.30,
            'support_resistance': 0.25,
            'volume_confirmation': 0.20
        }

        self.adx_strong_threshold = 25.0
        self.adx_weak_threshold = 15.0

    def analyze_enhanced_liquidation(self,
                                   base_liquidation_score: float,
                                   market_data: Dict[str, Any]) -> EnhancedLiquidationResult:
        """
        Perform enhanced liquidation analysis.

        Args:
            base_liquidation_score: Base liquidation score from sentiment indicators
            market_data: Market data containing OHLCV, volume, etc.

        Returns:
            EnhancedLiquidationResult with enhanced score and reasoning
        """
        try:
            # Extract OHLCV data
            ohlcv_df = self._extract_ohlcv_data(market_data)
            if ohlcv_df is None or len(ohlcv_df) < max(self.adx_period, self.ema_long_period):
                return self._fallback_result(base_liquidation_score, "Insufficient OHLCV data")

            # Calculate technical indicators
            technical_indicators = self._calculate_technical_indicators(ohlcv_df)

            # Analyze enhancement factors
            enhancement_factors = self._analyze_enhancement_factors(
                ohlcv_df, technical_indicators, market_data
            )

            # Calculate enhanced score
            enhanced_score = self._calculate_enhanced_score(
                base_liquidation_score, enhancement_factors
            )

            # Generate reasoning
            reasoning = self._generate_reasoning(enhancement_factors, technical_indicators)

            # Calculate confidence and enhancement magnitude
            confidence = self._calculate_confidence(enhancement_factors, technical_indicators)
            enhancement_magnitude = abs(enhanced_score - base_liquidation_score)

            return EnhancedLiquidationResult(
                final_score=float(np.clip(enhanced_score, 0, 100)),
                reasoning=reasoning,
                technical_indicators=technical_indicators,
                confidence=confidence,
                base_score=base_liquidation_score,
                enhancement_magnitude=enhancement_magnitude
            )

        except Exception as e:
            self.logger.error(f"Error in enhanced liquidation analysis: {str(e)}")
            return self._fallback_result(base_liquidation_score, f"Analysis error: {str(e)}")

    def _extract_ohlcv_data(self, market_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Extract and validate OHLCV data from market_data."""
        try:
            # Try different possible data sources
            ohlcv_sources = [
                market_data.get('ohlcv'),
                market_data.get('price_data'),
                market_data.get('candles'),
                market_data.get('klines')
            ]

            for source in ohlcv_sources:
                if source is not None:
                    if isinstance(source, pd.DataFrame):
                        df = source.copy()
                    elif isinstance(source, list):
                        # Convert list to DataFrame
                        df = pd.DataFrame(source, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    else:
                        continue

                    # Ensure required columns exist
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if all(col in df.columns for col in required_cols):
                        # Convert to numeric and handle missing values
                        for col in required_cols:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                        df = df.dropna(subset=required_cols)

                        if len(df) > 0:
                            return df.sort_index() if 'timestamp' not in df.columns else df.sort_values('timestamp')

            return None

        except Exception as e:
            self.logger.error(f"Error extracting OHLCV data: {str(e)}")
            return None

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical indicators from OHLCV data."""
        try:
            indicators = {}

            # Calculate EMAs
            indicators['ema_short'] = df['close'].ewm(span=self.ema_short_period).mean().iloc[-1]
            indicators['ema_long'] = df['close'].ewm(span=self.ema_long_period).mean().iloc[-1]

            # Calculate ADX
            indicators['adx'] = self._calculate_adx(df)

            # Calculate price position relative to EMAs
            current_price = df['close'].iloc[-1]
            indicators['price_vs_ema_short'] = (current_price / indicators['ema_short'] - 1) * 100
            indicators['price_vs_ema_long'] = (current_price / indicators['ema_long'] - 1) * 100

            # Calculate EMA crossover signal
            indicators['ema_crossover_signal'] = self._calculate_ema_crossover_signal(df)

            # Calculate volume trend
            indicators['volume_trend'] = self._calculate_volume_trend(df)

            # Calculate support/resistance levels
            sr_levels = self._calculate_support_resistance(df)
            indicators.update(sr_levels)

            return indicators

        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {str(e)}")
            return {}

    def _calculate_adx(self, df: pd.DataFrame) -> float:
        """Calculate Average Directional Index (ADX)."""
        try:
            high = df['high']
            low = df['low']
            close = df['close']

            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Calculate Directional Movement
            dm_plus = high - high.shift(1)
            dm_minus = low.shift(1) - low

            dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
            dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)

            # Calculate smoothed values
            atr = tr.rolling(window=self.adx_period).mean()
            di_plus = 100 * (dm_plus.rolling(window=self.adx_period).mean() / atr)
            di_minus = 100 * (dm_minus.rolling(window=self.adx_period).mean() / atr)

            # Calculate DX and ADX
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.rolling(window=self.adx_period).mean()

            return float(adx.iloc[-1]) if not np.isnan(adx.iloc[-1]) else 0.0

        except Exception as e:
            self.logger.error(f"Error calculating ADX: {str(e)}")
            return 0.0

    def _calculate_ema_crossover_signal(self, df: pd.DataFrame) -> float:
        """Calculate EMA crossover signal strength."""
        try:
            ema_short = df['close'].ewm(span=self.ema_short_period).mean()
            ema_long = df['close'].ewm(span=self.ema_long_period).mean()

            # Current crossover state
            current_cross = ema_short.iloc[-1] - ema_long.iloc[-1]
            previous_cross = ema_short.iloc[-2] - ema_long.iloc[-2]

            # Detect crossover and calculate signal strength
            if current_cross > 0 and previous_cross <= 0:
                # Bullish crossover
                return 1.0
            elif current_cross < 0 and previous_cross >= 0:
                # Bearish crossover
                return -1.0
            else:
                # No crossover, return current divergence strength
                return float(np.tanh(current_cross / ema_long.iloc[-1] * 100))

        except Exception as e:
            self.logger.error(f"Error calculating EMA crossover: {str(e)}")
            return 0.0

    def _calculate_volume_trend(self, df: pd.DataFrame) -> float:
        """Calculate volume trend indicator."""
        try:
            volume = df['volume']

            # Calculate volume moving averages
            vol_short = volume.rolling(window=5).mean()
            vol_long = volume.rolling(window=20).mean()

            # Current volume vs average
            current_vol_ratio = volume.iloc[-1] / vol_long.iloc[-1] if vol_long.iloc[-1] > 0 else 1.0

            # Volume trend
            vol_trend = (vol_short.iloc[-1] / vol_long.iloc[-1] - 1) * 100 if vol_long.iloc[-1] > 0 else 0.0

            return float(np.clip(vol_trend + (current_vol_ratio - 1) * 50, -100, 100))

        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {str(e)}")
            return 0.0

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate support and resistance levels."""
        try:
            lookback_df = df.tail(self.sr_lookback_periods)
            current_price = df['close'].iloc[-1]

            # Find local highs and lows
            highs = lookback_df['high']
            lows = lookback_df['low']

            # Calculate resistance (nearest high above current price)
            resistance_candidates = highs[highs > current_price * (1 + self.sr_distance_threshold)]
            resistance = resistance_candidates.min() if len(resistance_candidates) > 0 else current_price * 1.05

            # Calculate support (nearest low below current price)
            support_candidates = lows[lows < current_price * (1 - self.sr_distance_threshold)]
            support = support_candidates.max() if len(support_candidates) > 0 else current_price * 0.95

            # Calculate distance to S/R levels
            distance_to_resistance = (resistance / current_price - 1) * 100
            distance_to_support = (1 - support / current_price) * 100

            return {
                'resistance_level': float(resistance),
                'support_level': float(support),
                'distance_to_resistance': float(distance_to_resistance),
                'distance_to_support': float(distance_to_support),
                'near_resistance': bool(distance_to_resistance < self.sr_distance_threshold * 100),
                'near_support': bool(distance_to_support < self.sr_distance_threshold * 100)
            }

        except Exception as e:
            self.logger.error(f"Error calculating support/resistance: {str(e)}")
            return {
                'resistance_level': 0.0,
                'support_level': 0.0,
                'distance_to_resistance': 0.0,
                'distance_to_support': 0.0,
                'near_resistance': False,
                'near_support': False
            }

    def _analyze_enhancement_factors(self,
                                   df: pd.DataFrame,
                                   indicators: Dict[str, float],
                                   market_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze factors that enhance liquidation risk."""
        try:
            factors = {}

            # ADX trend strength factor
            adx = indicators.get('adx', 0)
            if adx > self.adx_strong_threshold:
                factors['adx_trend_strength'] = 1.0  # Strong trend increases liquidation risk
            elif adx < self.adx_weak_threshold:
                factors['adx_trend_strength'] = -0.5  # Weak trend reduces risk
            else:
                factors['adx_trend_strength'] = (adx - self.adx_weak_threshold) / (self.adx_strong_threshold - self.adx_weak_threshold)

            # EMA momentum factor
            ema_signal = indicators.get('ema_crossover_signal', 0)
            price_vs_ema_short = indicators.get('price_vs_ema_short', 0)

            # Strong momentum increases liquidation risk in opposite direction
            if abs(ema_signal) > 0.5:
                factors['ema_momentum'] = abs(ema_signal) * 0.8
            else:
                factors['ema_momentum'] = abs(price_vs_ema_short) / 10.0

            # Support/resistance factor
            near_support = indicators.get('near_support', False)
            near_resistance = indicators.get('near_resistance', False)

            if near_support or near_resistance:
                factors['support_resistance'] = 1.0  # Near key levels increases risk
            else:
                # Distance-based factor
                dist_support = indicators.get('distance_to_support', 0)
                dist_resistance = indicators.get('distance_to_resistance', 0)
                min_distance = min(dist_support, dist_resistance)
                factors['support_resistance'] = max(0, 1 - min_distance / 5.0)  # Within 5% of S/R

            # Volume confirmation factor
            volume_trend = indicators.get('volume_trend', 0)
            factors['volume_confirmation'] = abs(volume_trend) / 100.0

            # Normalize factors to [-1, 1] range
            for key in factors:
                factors[key] = float(np.clip(factors[key], -1.0, 1.0))

            return factors

        except Exception as e:
            self.logger.error(f"Error analyzing enhancement factors: {str(e)}")
            return {key: 0.0 for key in self.enhancement_weights.keys()}

    def _calculate_enhanced_score(self,
                                base_score: float,
                                enhancement_factors: Dict[str, float]) -> float:
        """Calculate the enhanced liquidation score."""
        try:
            # Calculate weighted enhancement
            total_enhancement = 0.0
            total_weight = 0.0

            for factor_name, factor_value in enhancement_factors.items():
                weight = self.enhancement_weights.get(factor_name, 0.0)
                total_enhancement += factor_value * weight
                total_weight += weight

            # Normalize enhancement
            if total_weight > 0:
                normalized_enhancement = total_enhancement / total_weight
            else:
                normalized_enhancement = 0.0

            # Apply enhancement to base score
            # Enhancement range: ±20 points maximum
            max_enhancement = 20.0
            enhancement_magnitude = normalized_enhancement * max_enhancement

            enhanced_score = base_score + enhancement_magnitude

            return float(np.clip(enhanced_score, 0, 100))

        except Exception as e:
            self.logger.error(f"Error calculating enhanced score: {str(e)}")
            return base_score

    def _generate_reasoning(self,
                          enhancement_factors: Dict[str, float],
                          indicators: Dict[str, float]) -> List[str]:
        """Generate human-readable reasoning for the enhancement."""
        reasoning = []

        try:
            # ADX reasoning
            adx = indicators.get('adx', 0)
            adx_factor = enhancement_factors.get('adx_trend_strength', 0)
            if abs(adx_factor) > 0.3:
                if adx > self.adx_strong_threshold:
                    reasoning.append(f"Strong trend (ADX: {adx:.1f}) increases liquidation risk")
                elif adx < self.adx_weak_threshold:
                    reasoning.append(f"Weak trend (ADX: {adx:.1f}) reduces liquidation pressure")

            # EMA momentum reasoning
            ema_factor = enhancement_factors.get('ema_momentum', 0)
            ema_signal = indicators.get('ema_crossover_signal', 0)
            if abs(ema_factor) > 0.3:
                if abs(ema_signal) > 0.5:
                    direction = "bullish" if ema_signal > 0 else "bearish"
                    reasoning.append(f"Strong {direction} momentum from EMA crossover")
                else:
                    reasoning.append("Price divergence from EMAs indicates momentum shift")

            # Support/resistance reasoning
            sr_factor = enhancement_factors.get('support_resistance', 0)
            if sr_factor > 0.3:
                if indicators.get('near_support', False):
                    reasoning.append("Price near key support level increases breakdown risk")
                elif indicators.get('near_resistance', False):
                    reasoning.append("Price near key resistance level increases rejection risk")
                else:
                    reasoning.append("Proximity to key price levels elevates liquidation risk")

            # Volume reasoning
            vol_factor = enhancement_factors.get('volume_confirmation', 0)
            if abs(vol_factor) > 0.3:
                vol_trend = indicators.get('volume_trend', 0)
                if vol_trend > 0:
                    reasoning.append("Increasing volume confirms price pressure")
                else:
                    reasoning.append("Declining volume suggests weakening momentum")

            # Default reasoning if no significant factors
            if not reasoning:
                reasoning.append("Technical analysis shows neutral liquidation risk")

            return reasoning

        except Exception as e:
            self.logger.error(f"Error generating reasoning: {str(e)}")
            return ["Enhanced analysis completed with limited data"]

    def _calculate_confidence(self,
                            enhancement_factors: Dict[str, float],
                            indicators: Dict[str, float]) -> float:
        """Calculate confidence in the enhanced analysis."""
        try:
            # Confidence based on data quality and indicator alignment
            confidence_factors = []

            # Data availability confidence
            data_availability = len([v for v in indicators.values() if v != 0.0]) / len(indicators)
            confidence_factors.append(data_availability)

            # Factor strength confidence
            factor_strength = np.mean([abs(f) for f in enhancement_factors.values()])
            confidence_factors.append(factor_strength)

            # ADX confidence (higher ADX = more confidence in trend)
            adx = indicators.get('adx', 0)
            adx_confidence = min(adx / 50.0, 1.0)  # Normalize to [0,1]
            confidence_factors.append(adx_confidence)

            # Volume confirmation confidence
            vol_trend = abs(indicators.get('volume_trend', 0))
            vol_confidence = min(vol_trend / 50.0, 1.0)  # Normalize to [0,1]
            confidence_factors.append(vol_confidence)

            return float(np.mean(confidence_factors))

        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    def _fallback_result(self, base_score: float, reason: str) -> EnhancedLiquidationResult:
        """Create a fallback result when enhanced analysis fails."""
        return EnhancedLiquidationResult(
            final_score=base_score,
            reasoning=[f"Enhanced analysis unavailable: {reason}"],
            technical_indicators={},
            confidence=0.0,
            base_score=base_score,
            enhancement_magnitude=0.0
        )

def create_enhanced_liquidation_analyzer(**kwargs) -> EnhancedLiquidationAnalyzer:
    """
    Factory function to create an enhanced liquidation analyzer.

    Args:
        **kwargs: Configuration parameters for the analyzer

    Returns:
        EnhancedLiquidationAnalyzer instance
    """
    return EnhancedLiquidationAnalyzer(**kwargs)