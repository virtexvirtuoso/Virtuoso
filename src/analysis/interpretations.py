from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class IndicatorInterpreter:
    """Centralized indicator interpretation logic."""
    
    @staticmethod
    def interpret_score(score: float, indicator_type: str) -> Dict[str, str]:
        """Interpret a normalized indicator score."""
        try:
            if indicator_type == "volume":
                return IndicatorInterpreter._interpret_volume_score(score)
            elif indicator_type == "momentum":
                return IndicatorInterpreter._interpret_momentum_score(score)
            elif indicator_type == "trend":
                return IndicatorInterpreter._interpret_trend_score(score)
            elif indicator_type in ["volume_delta", "adl", "force_index", "cmf", "emv", "relative_volume"]:
                return IndicatorInterpreter._interpret_volume_score(score)  # Use volume interpretation for volume-related indicators
            elif indicator_type in ["rsi", "ao", "williams_r", "cci", "uo", "divergence_rsi", "divergence_ao"]:
                return IndicatorInterpreter._interpret_momentum_score(score)  # Use momentum interpretation for momentum-related indicators
            else:
                logger.warning(f"Unknown indicator type: {indicator_type}")
                return {"signal": "unknown", "strength": "unknown"}
        except Exception as e:
            logger.error(f"Error interpreting score: {str(e)}")
            return {"signal": "error", "strength": "unknown"}
    
    @staticmethod
    def _interpret_volume_score(score: float) -> Dict[str, str]:
        """Interpret volume-based indicator score."""
        if score >= 80:
            return {
                "signal": "extremely_high_volume",
                "strength": "very_strong",
                "interpretation": "Extremely high volume indicating strong market interest"
            }
        elif score >= 60:
            return {
                "signal": "above_average_volume",
                "strength": "strong",
                "interpretation": "Above average volume showing increased market activity"
            }
        elif score >= 40:
            return {
                "signal": "average_volume",
                "strength": "moderate",
                "interpretation": "Normal volume levels with balanced trading activity"
            }
        elif score >= 20:
            return {
                "signal": "below_average_volume",
                "strength": "weak",
                "interpretation": "Below average volume indicating reduced market interest"
            }
        else:
            return {
                "signal": "very_low_volume",
                "strength": "very_weak",
                "interpretation": "Very low volume suggesting potential lack of market interest"
            }
    
    @staticmethod
    def _interpret_momentum_score(score: float) -> Dict[str, str]:
        """Interpret momentum-based indicator score."""
        if score >= 80:
            return {
                "signal": "strong_bullish",
                "strength": "very_strong",
                "interpretation": "Strong bullish momentum indicating potential upward continuation"
            }
        elif score >= 60:
            return {
                "signal": "moderate_bullish",
                "strength": "strong",
                "interpretation": "Moderate bullish momentum showing buying pressure"
            }
        elif score >= 40:
            return {
                "signal": "neutral",
                "strength": "moderate",
                "interpretation": "Neutral momentum with balanced buying and selling pressure"
            }
        elif score >= 20:
            return {
                "signal": "moderate_bearish",
                "strength": "weak",
                "interpretation": "Moderate bearish momentum showing selling pressure"
            }
        else:
            return {
                "signal": "strong_bearish",
                "strength": "very_weak",
                "interpretation": "Strong bearish momentum indicating potential downward continuation"
            }
    
    @staticmethod
    def _interpret_trend_score(score: float) -> Dict[str, str]:
        """Interpret trend-based indicator score."""
        if score >= 80:
            return {
                "signal": "strong_uptrend",
                "strength": "very_strong",
                "interpretation": "Strong uptrend with consistent higher highs and higher lows"
            }
        elif score >= 60:
            return {
                "signal": "moderate_uptrend",
                "strength": "strong",
                "interpretation": "Moderate uptrend showing bullish price action"
            }
        elif score >= 40:
            return {
                "signal": "sideways",
                "strength": "moderate",
                "interpretation": "Sideways trend with no clear directional bias"
            }
        elif score >= 20:
            return {
                "signal": "moderate_downtrend",
                "strength": "weak",
                "interpretation": "Moderate downtrend showing bearish price action"
            }
        else:
            return {
                "signal": "strong_downtrend",
                "strength": "very_weak",
                "interpretation": "Strong downtrend with consistent lower highs and lower lows"
            }
    
    @staticmethod
    def get_composite_interpretation(
        scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate composite interpretation from multiple indicator scores."""
        try:
            # Calculate weighted average score
            total_weight = sum(weights.values())
            if total_weight == 0:
                logger.warning("Total weight is 0, using default score")
                return {
                    "signal": "neutral",
                    "interpretation": "Neutral conditions due to invalid weights",
                    "composite_score": 50.0
                }
                
            weighted_score = 0.0
            valid_indicators = 0
            
            # Calculate weighted score for each indicator
            for indicator, weight in weights.items():
                if indicator in scores:
                    score = scores[indicator]
                    weighted_score += score * weight
                    valid_indicators += 1
                else:
                    logger.debug(f"Missing score for indicator: {indicator}")
            
            if valid_indicators == 0:
                logger.warning("No valid indicators found")
                return {
                    "signal": "neutral",
                    "interpretation": "Neutral conditions due to missing indicators",
                    "composite_score": 50.0
                }
            
            # Calculate final composite score
            composite_score = weighted_score / total_weight
            
            # Ensure score is within bounds
            composite_score = max(1.0, min(100.0, composite_score))
            
            # Get interpretation based on composite score
            interpretation = IndicatorInterpreter._interpret_momentum_score(composite_score)
            interpretation["composite_score"] = composite_score
            
            # Add individual scores for reference
            interpretation["individual_scores"] = scores
            
            logger.debug(f"Composite score: {composite_score:.2f}")
            logger.debug(f"Individual scores: {scores}")
            
            return interpretation
            
        except Exception as e:
            logger.error(f"Error generating composite interpretation: {str(e)}")
            return {
                "signal": "error",
                "interpretation": "Error generating composite interpretation",
                "composite_score": 50.0,
                "error": str(e)
            } 