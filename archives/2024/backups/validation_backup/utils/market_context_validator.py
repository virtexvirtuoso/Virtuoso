#!/usr/bin/env python3
"""
Market Context Validator
========================

Market context validation to prevent false bullish/bearish signals in indicator scoring.
This module provides validation methods to ensure indicators consider market context
when generating scores.
"""

import numpy as np
from typing import Optional


class MarketContextValidator:
    """
    Market context validation to prevent false bullish/bearish signals
    """
    
    @staticmethod
    def validate_oversold_bullish(score: float, rsi_value: float, price_trend: str = "unknown") -> float:
        """
        Validate oversold conditions - ensure they're truly bullish
        
        Args:
            score: Current indicator score
            rsi_value: RSI value (0-100) or Williams %R absolute value
            price_trend: Price trend context ("strong_downtrend", "downtrend", "sideways", "uptrend", "strong_uptrend", "unknown")
            
        Returns:
            Validated score adjusted for market context
        """
        try:
            if rsi_value < 30:  # Oversold
                # In strong downtrend, oversold might not be immediately bullish
                if price_trend == "strong_downtrend":
                    return min(score, 65)  # Cap bullish signal
                return max(score, 60)  # Ensure minimum bullish signal
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_overbought_bearish(score: float, rsi_value: float, price_trend: str = "unknown") -> float:
        """
        Validate overbought conditions - ensure they're truly bearish
        
        Args:
            score: Current indicator score
            rsi_value: RSI value (0-100) or Williams %R absolute value
            price_trend: Price trend context
            
        Returns:
            Validated score adjusted for market context
        """
        try:
            if rsi_value > 70:  # Overbought
                # In strong uptrend, overbought might not be immediately bearish
                if price_trend == "strong_uptrend":
                    return max(score, 35)  # Cap bearish signal
                return min(score, 40)  # Ensure maximum bearish signal
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_volume_context(score: float, volume_ratio: float, price_direction: str) -> float:
        """
        Validate volume signals with price direction context
        
        Args:
            score: Current indicator score
            volume_ratio: Volume ratio (current/average)
            price_direction: Price direction ("up", "down", "sideways")
            
        Returns:
            Validated score adjusted for volume context
        """
        try:
            if volume_ratio > 2.0:  # High volume
                if price_direction == "down":
                    # High volume on down move is bearish
                    return min(score, 30)
                elif price_direction == "up":
                    # High volume on up move is bullish
                    return max(score, 70)
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_funding_extremes(score: float, funding_rate: float) -> float:
        """
        Validate funding rate extremes to prevent false signals
        
        Args:
            score: Current indicator score
            funding_rate: Funding rate (as decimal, e.g., 0.01 = 1%)
            
        Returns:
            Validated score adjusted for funding extremes
        """
        try:
            if abs(funding_rate) > 0.01:  # 1% funding rate (extreme)
                # Extreme funding rates might indicate market manipulation
                return min(max(score, 40), 60)  # Force toward neutral
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_range_position(score: float, position_ratio: float, range_age: int) -> float:
        """
        Validate range position with range maturity context
        
        Args:
            score: Current indicator score
            position_ratio: Position in range (0.0 = bottom, 1.0 = top)
            range_age: Age of the range in periods
            
        Returns:
            Validated score adjusted for range context
        """
        try:
            if range_age < 10:  # Young range
                # Position in young range is less reliable
                return 50 + (score - 50) * 0.5  # Reduce signal strength
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_divergence_signal(score: float, divergence_strength: float, market_volatility: float = 1.0) -> float:
        """
        Validate divergence signals based on strength and market volatility
        
        Args:
            score: Current indicator score
            divergence_strength: Strength of divergence (0.0 to 1.0)
            market_volatility: Market volatility multiplier
            
        Returns:
            Validated score adjusted for divergence context
        """
        try:
            if divergence_strength > 0.7:  # Strong divergence
                # Strong divergence in high volatility might be noise
                if market_volatility > 1.5:
                    return 50 + (score - 50) * 0.7  # Reduce signal strength
                else:
                    return 50 + (score - 50) * 1.2  # Amplify signal in low volatility
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_trend_alignment(score: float, indicator_trend: str, price_trend: str) -> float:
        """
        Validate indicator signals against price trend alignment
        
        Args:
            score: Current indicator score
            indicator_trend: Indicator trend direction ("bullish", "bearish", "neutral")
            price_trend: Price trend direction ("uptrend", "downtrend", "sideways")
            
        Returns:
            Validated score adjusted for trend alignment
        """
        try:
            # Amplify signals when indicator and price trends align
            if indicator_trend == "bullish" and price_trend in ["uptrend", "strong_uptrend"]:
                return min(score * 1.1, 100)  # Amplify bullish signal
            elif indicator_trend == "bearish" and price_trend in ["downtrend", "strong_downtrend"]:
                return max(score * 1.1, 0)  # Amplify bearish signal
            
            # Reduce signals when they conflict
            elif indicator_trend == "bullish" and price_trend in ["downtrend", "strong_downtrend"]:
                return score * 0.8  # Reduce conflicting bullish signal
            elif indicator_trend == "bearish" and price_trend in ["uptrend", "strong_uptrend"]:
                return score * 0.8  # Reduce conflicting bearish signal
            
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_liquidity_context(score: float, liquidity_ratio: float, spread_ratio: float) -> float:
        """
        Validate signals based on liquidity and spread context
        
        Args:
            score: Current indicator score
            liquidity_ratio: Liquidity ratio (current/average)
            spread_ratio: Spread ratio (current/average)
            
        Returns:
            Validated score adjusted for liquidity context
        """
        try:
            # Low liquidity or high spreads reduce signal reliability
            if liquidity_ratio < 0.5 or spread_ratio > 2.0:
                return 50 + (score - 50) * 0.6  # Reduce signal strength
            
            # High liquidity and tight spreads increase signal reliability
            elif liquidity_ratio > 1.5 and spread_ratio < 0.8:
                return 50 + (score - 50) * 1.2  # Amplify signal strength
            
            return score
        except Exception:
            return score
    
    @staticmethod
    def validate_score_bounds(score: float, min_score: float = 0.0, max_score: float = 100.0) -> float:
        """
        Ensure score is within valid bounds
        
        Args:
            score: Score to validate
            min_score: Minimum allowed score
            max_score: Maximum allowed score
            
        Returns:
            Score clipped to valid bounds
        """
        try:
            return float(np.clip(score, min_score, max_score))
        except Exception:
            return 50.0  # Neutral fallback
    
    @staticmethod
    def apply_context_weighting(score: float, context_confidence: float) -> float:
        """
        Apply context confidence weighting to score
        
        Args:
            score: Current indicator score
            context_confidence: Confidence in context analysis (0.0 to 1.0)
            
        Returns:
            Score weighted by context confidence
        """
        try:
            # Higher confidence allows more extreme scores
            # Lower confidence pulls toward neutral
            confidence_factor = max(0.1, min(1.0, context_confidence))
            return 50 + (score - 50) * confidence_factor
        except Exception:
            return score 