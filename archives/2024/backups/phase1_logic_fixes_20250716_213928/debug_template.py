# src/indicators/debug_template.py
"""
Debug Logging Template for Indicators

This template provides standardized debug logging patterns based on OrderbookIndicators
that should be applied consistently across all indicator classes.

Key Debug Logging Patterns:
1. Component Calculation Debug Headers
2. Step-by-Step Calculation Logging
3. Data Quality Assessment
4. Performance Metrics
5. Trading Context Analysis
6. Component Influence Analysis
7. Threshold Alerts
8. Confidence Assessment
"""

import time
import numpy as np
from typing import Dict, Any, List, Tuple
import traceback


class DebugLoggingMixin:
    """
    Mixin class providing standardized debug logging methods for all indicators.
    
    This class should be inherited by all indicator classes to ensure consistent
    debug logging patterns across the entire indicator system.
    """
    
    def _log_component_calculation_header(self, component_name: str, data_summary: str = "") -> None:
        """Log standardized component calculation header."""
        self.logger.debug(f"\n=== {component_name.upper()} CALCULATION DEBUG ===")
        if data_summary:
            self.logger.debug(f"Input data summary: {data_summary}")
    
    def _log_calculation_step(self, step_name: str, values: Dict[str, Any]) -> None:
        """Log individual calculation steps with formatted values."""
        self.logger.debug(f"\n--- {step_name} ---")
        for key, value in values.items():
            if isinstance(value, float):
                self.logger.debug(f"  {key}: {value:.6f}")
            elif isinstance(value, (int, str)):
                self.logger.debug(f"  {key}: {value}")
            else:
                self.logger.debug(f"  {key}: {value}")
    
    def _log_formula_calculation(self, formula_name: str, formula: str, 
                               variables: Dict[str, float], result: float) -> None:
        """Log formula calculations with step-by-step breakdown."""
        self.logger.debug(f"\n{formula_name} formula:")
        self.logger.debug(f"  {formula}")
        
        # Log variable substitution
        substituted_formula = formula
        for var, val in variables.items():
            substituted_formula = substituted_formula.replace(var, f"{val:.6f}")
            self.logger.debug(f"  {var} = {val:.6f}")
        
        self.logger.debug(f"  {formula_name} = {substituted_formula}")
        self.logger.debug(f"  {formula_name} = {result:.6f}")
    
    def _log_score_transformation(self, raw_score: float, transformation_type: str,
                                parameters: Dict[str, Any], final_score: float) -> None:
        """Log score transformation steps."""
        self.logger.debug(f"\n{transformation_type} transformation:")
        for param, value in parameters.items():
            self.logger.debug(f"  {param}: {value}")
        self.logger.debug(f"  Input: {raw_score:.2f}")
        self.logger.debug(f"  Output: {final_score:.2f}")
    
    def _log_interpretation_analysis(self, score: float, interpretation: str,
                                   thresholds: Dict[str, Tuple[float, str]]) -> None:
        """Log score interpretation with threshold analysis."""
        self.logger.debug(f"\nInterpretation analysis:")
        self.logger.debug(f"  Score: {score:.2f}")
        self.logger.debug(f"  Interpretation: {interpretation}")
        
        self.logger.debug("  Threshold bands:")
        for band_name, (threshold, description) in thresholds.items():
            status = "✓" if score >= threshold else "✗"
            self.logger.debug(f"    {band_name} (≥{threshold:.1f}): {status} - {description}")
    
    def _log_significant_event(self, event_type: str, score: float, 
                             threshold: float, description: str) -> None:
        """Log significant events with emoji indicators."""
        if abs(score) > threshold:
            self.logger.info(f"Significant {event_type} detected: {score:.4f} - {description}")
    
    def _log_data_quality_metrics(self, market_data: Dict[str, Any]) -> None:
        """Log data quality assessment following OrderbookIndicators pattern."""
        try:
            self.logger.info("\n--- Data Quality Assessment ---")
            
            # Data completeness
            required_fields = getattr(self, 'required_data', [])
            available_fields = list(market_data.keys())
            missing_fields = [field for field in required_fields if field not in available_fields]
            
            completeness = (len(available_fields) - len(missing_fields)) / len(required_fields) * 100
            if completeness >= 90:
                completeness_quality = "Excellent"
            elif completeness >= 75:
                completeness_quality = "Good"
            elif completeness >= 50:
                completeness_quality = "Fair"
            else:
                completeness_quality = "Poor"
                
            self.logger.info(f"Data Completeness: {completeness:.1f}% ({completeness_quality})")
            if missing_fields:
                self.logger.warning(f"Missing fields: {missing_fields}")
            
            # Data freshness
            timestamp = market_data.get('timestamp', time.time() * 1000)
            age_seconds = (time.time() * 1000 - timestamp) / 1000
            
            if age_seconds <= 1:
                freshness = "Excellent"
            elif age_seconds <= 5:
                freshness = "Good"
            elif age_seconds <= 30:
                freshness = "Fair"
            else:
                freshness = "Stale"
                
            self.logger.info(f"Data Age: {age_seconds:.1f}s ({freshness})")
            
        except Exception as e:
            self.logger.error(f"Error logging data quality metrics: {str(e)}")
    
    def _log_performance_metrics(self, component_times: Dict[str, float], total_time: float) -> None:
        """Log performance timing metrics following OrderbookIndicators pattern."""
        try:
            self.logger.info("\n--- Performance Metrics ---")
            self.logger.info(f"Total Calculation Time: {total_time:.1f}ms")
            
            # Sort components by time taken
            sorted_times = sorted(component_times.items(), key=lambda x: x[1], reverse=True)
            
            self.logger.info("Component Timing (slowest first):")
            for component, time_ms in sorted_times:
                percentage = (time_ms / total_time) * 100
                self.logger.info(f"  {component}: {time_ms:.1f}ms ({percentage:.1f}%)")
                
            # Performance warnings
            if total_time > 100:
                self.logger.warning(f"⚠️  Slow calculation detected: {total_time:.1f}ms")
                
            slowest_component = max(component_times.items(), key=lambda x: x[1])
            if slowest_component[1] > 50:
                self.logger.warning(f"⚠️  Slow component '{slowest_component[0]}': {slowest_component[1]:.1f}ms")
                
        except Exception as e:
            self.logger.error(f"Error logging performance metrics: {str(e)}")
    
    def _log_trading_context(self, final_score: float, component_scores: Dict[str, float], 
                           symbol: str, indicator_name: str) -> None:
        """Log enhanced trading context and actionable insights."""
        try:
            self.logger.info(f"\n=== {symbol} {indicator_name} Trading Context ===")
            
            # 1. Score Interpretation Bands
            if final_score >= 70:
                strength = "STRONG BULLISH"
                action_bias = "Consider long positions"
                risk_level = "Moderate"
            elif final_score >= 55:
                strength = "MODERATE BULLISH" 
                action_bias = "Slight long bias"
                risk_level = "Low"
            elif final_score >= 45:
                strength = "NEUTRAL"
                action_bias = "Wait for clearer signals"
                risk_level = "High"
            elif final_score >= 30:
                strength = "MODERATE BEARISH"
                action_bias = "Slight short bias" 
                risk_level = "Low"
            else:
                strength = "STRONG BEARISH"
                action_bias = "Consider short positions"
                risk_level = "Moderate"
                
            self.logger.info(f"Signal Strength: {strength}")
            self.logger.info(f"Trading Bias: {action_bias}")
            self.logger.info(f"Risk Level: {risk_level}")
            
            # 2. Component Influence Analysis
            self._log_component_influence(component_scores)
            
            # 3. Threshold Alerts
            self._log_threshold_alerts(final_score, component_scores, symbol, indicator_name)
            
            # 4. Confidence Assessment
            confidence = self._calculate_confidence_level(component_scores)
            self.logger.info(f"Confidence Level: {confidence:.1f}% ({self._get_confidence_label(confidence)})")
            
        except Exception as e:
            self.logger.error(f"Error logging trading context: {str(e)}")
    
    def _log_component_influence(self, component_scores: Dict[str, float]) -> None:
        """Log which components are driving the overall score."""
        try:
            self.logger.info("\n--- Component Influence Analysis ---")
            
            # Calculate component contributions
            contributions = []
            for component, score in component_scores.items():
                weight = self.component_weights.get(component, 0)
                contribution = score * weight
                deviation = abs(score - 50.0)  # Distance from neutral
                influence = deviation * weight  # Influence on final score
                contributions.append((component, score, contribution, influence))
            
            # Sort by influence (highest impact first)
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Log top influencers
            self.logger.info("Top 3 Score Drivers:")
            for i, (component, score, contribution, influence) in enumerate(contributions[:3]):
                direction = "bullish" if score > 50 else "bearish" if score < 50 else "neutral"
                self.logger.info(f"{i+1}. {component}: {score:.1f} ({direction}) - Impact: {influence:.1f}")
                
            # Identify conflicting signals
            bullish_components = [c for c, s, _, _ in contributions if s > 60]
            bearish_components = [c for c, s, _, _ in contributions if s < 40]
            
            if bullish_components and bearish_components:
                self.logger.warning("⚠️  Mixed Signals Detected:")
                self.logger.warning(f"   Bullish: {', '.join(bullish_components)}")
                self.logger.warning(f"   Bearish: {', '.join(bearish_components)}")
                
        except Exception as e:
            self.logger.error(f"Error logging component influence: {str(e)}")
    
    def _log_threshold_alerts(self, final_score: float, component_scores: Dict[str, float], 
                            symbol: str, indicator_name: str) -> None:
        """Log alerts when scores cross significant thresholds."""
        try:
            alerts = []
            
            # Overall score threshold alerts
            if final_score >= 75:
                alerts.append(f"STRONG BULLISH {indicator_name} signal - Consider aggressive long positioning")
            elif final_score <= 25:
                alerts.append(f"STRONG BEARISH {indicator_name} signal - Consider aggressive short positioning")
            elif 48 <= final_score <= 52:
                alerts.append(f"NEUTRAL {indicator_name} zone - Wait for clearer directional bias")
            
            # Component-specific alerts (can be customized per indicator)
            self._log_component_specific_alerts(component_scores, alerts, indicator_name)
            
            # Log alerts
            if alerts:
                self.logger.info("\n--- Trading Alerts ---")
                for alert in alerts:
                    self.logger.info(alert)
                    
        except Exception as e:
            self.logger.error(f"Error logging threshold alerts: {str(e)}")
    
    def _log_component_specific_alerts(self, component_scores: Dict[str, float], 
                                     alerts: List[str], indicator_name: str) -> None:
        """Log component-specific alerts - to be overridden by each indicator."""
        # Default implementation - can be overridden by specific indicators
        pass
    
    def _calculate_confidence_level(self, component_scores: Dict[str, float]) -> float:
        """Calculate confidence level based on component consistency and data quality."""
        try:
            # Factor 1: Component consistency (lower variance = higher confidence)
            scores = list(component_scores.values())
            if len(scores) > 1:
                score_variance = np.var(scores)
                consistency_factor = max(0, 100 - (score_variance / 10))  # Normalize variance
            else:
                consistency_factor = 50
                
            # Factor 2: Data quality (based on successful calculations)
            data_quality_factor = (len(component_scores) / len(self.component_weights)) * 100
            
            # Factor 3: Score extremity (more extreme scores = higher confidence)
            extremity_factor = np.mean([abs(score - 50) for score in scores]) * 2
            
            # Weighted average
            confidence = (
                consistency_factor * 0.4 +
                data_quality_factor * 0.3 +
                extremity_factor * 0.3
            )
            
            return float(np.clip(confidence, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence level: {str(e)}")
            return 50.0
    
    def _get_confidence_label(self, confidence: float) -> str:
        """Get confidence level label."""
        if confidence >= 80:
            return "Very High"
        elif confidence >= 65:
            return "High"
        elif confidence >= 50:
            return "Moderate"
        elif confidence >= 35:
            return "Low"
        else:
            return "Very Low"
    
    def _log_calculation_error(self, component_name: str, error: Exception) -> None:
        """Log calculation errors with detailed context."""
        self.logger.error(f"Error calculating {component_name}: {str(error)}")
        self.logger.debug(f"{component_name} calculation error details: {traceback.format_exc()}")
    
    def _log_component_timing(self, component_name: str, start_time: float) -> float:
        """Log component calculation timing and return execution time."""
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        self.logger.debug(f"{component_name} calculation completed in {execution_time:.1f}ms")
        return execution_time


# Usage example for implementing in indicators:
"""
class ExampleIndicator(BaseIndicator, DebugLoggingMixin):
    
    def _calculate_example_component(self, data: Dict[str, Any]) -> float:
        start_time = time.time()
        
        # 1. Log calculation header
        self._log_component_calculation_header("Example Component", f"Data points: {len(data)}")
        
        # 2. Log calculation steps
        self._log_calculation_step("Data Processing", {
            "input_length": len(data),
            "processed_length": len(processed_data)
        })
        
        # 3. Log formula calculation
        self._log_formula_calculation(
            "Example Formula",
            "result = (a + b) / c",
            {"a": 10.5, "b": 5.2, "c": 2.0},
            7.85
        )
        
        # 4. Log score transformation
        self._log_score_transformation(
            raw_score=75.5,
            transformation_type="Sigmoid",
            parameters={"sensitivity": 0.12, "center": 50.0},
            final_score=78.2
        )
        
        # 5. Log interpretation
        self._log_interpretation_analysis(
            score=78.2,
            interpretation="Strong bullish signal",
            thresholds={
                "Strong": (70.0, "Strong signal threshold"),
                "Moderate": (55.0, "Moderate signal threshold")
            }
        )
        
        # 6. Log significant events
        self._log_significant_event("Example Event", 78.2, 70.0, "Strong bullish signal detected")
        
        # 7. Log timing
        execution_time = self._log_component_timing("Example Component", start_time)
        
        return 78.2
""" 