"""
Utility functions for indicators to use enhanced log formatting.

This module provides helper functions for indicators to easily use the enhanced 
LogFormatter class for better visualization of analysis results.
"""

from typing import Dict, Any, List, Tuple
import logging
from src.core.formatting import LogFormatter, AnalysisFormatter

def log_score_contributions(logger: logging.Logger, title: str, component_scores: Dict[str, float], weights: Dict[str, float], symbol: str = "", final_score: float = None) -> None:
    """
    Log component score contributions with enhanced formatting.
    
    Args:
        logger: Logger to use for output
        title: Title for the score contribution section
        component_scores: Dictionary of component scores
        weights: Dictionary of component weights
        symbol: Optional symbol to include in the title
        final_score: Optional final score to override the calculated sum
    """
    # Create list of (component, score, weight, contribution) tuples
    contributions = []
    for component, score in component_scores.items():
        weight = weights.get(component, 0)
        contribution = score * weight
        contributions.append((component, score, weight, contribution))
    
    # Sort by contribution (highest first)
    contributions.sort(key=lambda x: x[3], reverse=True)
    
    # Use enhanced formatter
    formatted_section = LogFormatter.format_score_contribution_section(title, contributions, symbol, final_score=final_score)
    logger.info(formatted_section)

def log_component_analysis(logger: logging.Logger, title: str, components: Dict[str, float]) -> None:
    """
    Log component analysis with enhanced formatting.
    
    Args:
        logger: Logger to use for output
        title: Title for the component analysis
        components: Dictionary of component scores
    """
    formatted_analysis = LogFormatter.format_component_analysis(title, components)
    logger.info(formatted_analysis)

def log_calculation_details(logger: logging.Logger, name: str, value: float = None, extra_info: str = "", metrics: Dict[str, Any] = None) -> None:
    """
    Log calculation details with enhanced formatting.
    
    This function supports two modes:
    1. Single value mode: Logs a single calculation with name, value, and optional extra info
    2. Multiple metrics mode: Logs a dictionary of metrics with a title
    
    Args:
        logger: Logger to use for output
        name: Name of the calculation or title for metrics section
        value: Calculated value (for single value mode)
        extra_info: Optional extra information (for single value mode)
        metrics: Dictionary of metric name -> value (for multiple metrics mode)
    """
    if metrics is not None:
        # Multiple metrics mode
        formatted_details = LogFormatter.format_detailed_calculation(name, metrics)
        logger.info(formatted_details)
    else:
        # Single value mode
        formatted_detail = LogFormatter.format_calculation_detail(name, value, extra_info)
        logger.info(formatted_detail)

def log_final_score(logger: logging.Logger, name: str, score: float, symbol: str = "") -> None:
    """
    Log final score with enhanced formatting.
    
    Args:
        logger: Logger to use for output
        name: Name of the indicator/component
        score: Final score value
        symbol: Optional symbol to include in the title
    """
    formatted_score = LogFormatter.format_final_score(name, score, symbol)
    logger.info(formatted_score)

def log_indicator_results(logger: logging.Logger, indicator_name: str, final_score: float, 
                         component_scores: Dict[str, float], weights: Dict[str, float], 
                         symbol: str = "") -> None:
    """
    Log complete indicator results with consistent formatting.
    
    This is a convenience function that logs both the component breakdown and final score
    with proper formatting. All indicators should use this function to ensure consistent
    output formatting.
    
    Args:
        logger: Logger to use for output
        indicator_name: Name of the indicator (e.g., "Technical", "Volume")
        final_score: Final calculated score
        component_scores: Dictionary of component scores
        weights: Dictionary of component weights
        symbol: Optional symbol to include in the title
    """
    # First log the component breakdown
    breakdown_title = f"{indicator_name} Score Contribution Breakdown"
    log_score_contributions(logger, breakdown_title, component_scores, weights, symbol)
    
    # Then log the final score
    log_final_score(logger, indicator_name, final_score, symbol)

def log_multi_timeframe_analysis(logger: logging.Logger, indicator_name: str, 
                                timeframe_scores: Dict[str, Dict[str, float]], 
                                divergences: Dict[str, Any] = None,
                                timeframe_weights: Dict[str, float] = None,
                                component_weights: Dict[str, float] = None,
                                symbol: str = "") -> None:
    """
    Log multi-timeframe analysis and divergence information.
    
    This function provides detailed logging of scores across different timeframes
    and any divergence bonuses that were applied.
    
    Args:
        logger: Logger to use for output
        indicator_name: Name of the indicator (e.g., "Technical", "Volume")
        timeframe_scores: Dictionary mapping timeframes to component scores
        divergences: Optional dictionary of divergence information
        timeframe_weights: Optional dictionary of timeframe weights
        component_weights: Optional dictionary of component weights
        symbol: Optional symbol to include in the title
    """
    if not timeframe_scores:
        logger.debug("No multi-timeframe data available for logging")
        return
        
    # Log header
    header = f"\n=== {symbol} {indicator_name} Multi-Timeframe Analysis ==="
    logger.info(header)
    
    # Log timeframe scores
    for tf, scores in timeframe_scores.items():
        if not scores:
            continue
            
        # Log timeframe header
        tf_header = f"\n{tf.upper()} Timeframe:"
        logger.info(tf_header)
        
        # Log component scores for this timeframe
        for component, score in scores.items():
            weight = component_weights.get(component, 0) if component_weights else 0
            contribution = score * weight if weight else 0
            
            if weight:
                logger.info(f"- {component}: {score:.2f} × {weight:.2f} = {contribution:.2f}")
            else:
                logger.info(f"- {component}: {score:.2f}")
                
        # Calculate and log weighted score for this timeframe if weights are provided
        if component_weights:
            weighted_sum = sum(scores.get(comp, 0) * component_weights.get(comp, 0) 
                              for comp in scores if comp in component_weights)
            weight_sum = sum(component_weights.get(comp, 0) for comp in scores if comp in component_weights)
            
            if weight_sum > 0:
                tf_score = weighted_sum / weight_sum
                tf_weight = timeframe_weights.get(tf, 0) if timeframe_weights else 0
                logger.info(f"Timeframe Score: {tf_score:.2f}" + 
                           (f" (Weight: {tf_weight:.2f})" if tf_weight else ""))
    
    # Log divergence information if available
    if divergences:
        logger.info("\n=== Divergence Analysis ===")
        
        for key, div_info in divergences.items():
            div_type = div_info.get('type', 'unknown')
            strength = div_info.get('strength', 0)
            tf = div_info.get('timeframe', '')
            component = div_info.get('component', '')
            
            # Format divergence type with emphasis
            if div_type == 'bullish':
                type_str = "BULLISH"
            elif div_type == 'bearish':
                type_str = "BEARISH"
            else:
                type_str = div_type.upper()
            
            logger.info(f"- {tf.upper()} {component}: {type_str} divergence (Strength: {strength:.2f})")
            
            # Log any bonus applied
            if 'bonus' in div_info:
                bonus = div_info['bonus']
                logger.info(f"  Applied bonus: {bonus:.2f}") 