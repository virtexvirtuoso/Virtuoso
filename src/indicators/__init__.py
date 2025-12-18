# src/indicators/__init__.py

"""
Indicator modules for market analysis.

This module provides a variety of indicators for analyzing market data,
including technical, volume, price structure, orderflow, and sentiment indicators.
"""

import logging

# Add TRACE level to logging if it doesn't exist
TRACE_LEVEL = 5  # Lower than DEBUG (10)
logging.addLevelName(TRACE_LEVEL, 'TRACE')

# Define trace method if it doesn't exist
if not hasattr(logging.Logger, 'trace'):
    def trace(self, message, *args, **kwargs):
        """
        Log 'msg % args' with severity 'TRACE'.
        """
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, message, args, **kwargs)
    
    # Add trace method to Logger class
    logging.Logger.trace = trace

# Initialize package logger
logger = logging.getLogger(__name__)

logger.debug("=== Loading indicators package ===")

# Log before importing BaseIndicator
logger.debug("About to import BaseIndicator")
from .base_indicator import BaseIndicator, IndicatorMetrics
logger.debug(f"BaseIndicator loaded. Attributes: {dir(BaseIndicator)}")
logger.debug(f"BaseIndicator dict: {BaseIndicator.__dict__}")

# Log before importing each indicator
logger.debug("About to import indicator classes")

# Import indicators with safe fallbacks (some modules are gitignored/proprietary)
try:
    from .volume_indicators import VolumeIndicators
except ImportError as e:
    logger.warning(f"VolumeIndicators not available: {e}")
    VolumeIndicators = None

try:
    from .orderflow_indicators import OrderflowIndicators
except ImportError as e:
    logger.warning(f"OrderflowIndicators not available: {e}")
    OrderflowIndicators = None

try:
    from .orderbook_indicators import OrderbookIndicators
except ImportError as e:
    logger.warning(f"OrderbookIndicators not available: {e}")
    OrderbookIndicators = None

try:
    from .technical_indicators import TechnicalIndicators
except ImportError as e:
    logger.warning(f"TechnicalIndicators not available: {e}")
    TechnicalIndicators = None

try:
    from .sentiment_indicators import SentimentIndicators
except ImportError as e:
    logger.warning(f"SentimentIndicators not available: {e}")
    SentimentIndicators = None

try:
    from .price_structure_indicators import PriceStructureIndicators
except ImportError as e:
    logger.warning(f"PriceStructureIndicators not available: {e}")
    PriceStructureIndicators = None

logger.debug("All indicator modules loaded")

__all__ = [
    'BaseIndicator',
    'IndicatorMetrics',
    'VolumeIndicators',
    'OrderflowIndicators',
    'OrderbookIndicators',
    'TechnicalIndicators',
    'SentimentIndicators',
    'PriceStructureIndicators'
]

# Extend indicator classes with enhanced divergence visualization
# This will add divergence visualization to all indicator classes that use 
# timeframe divergence analysis
from typing import Dict, Any
import numpy as np


def patch_indicators_with_divergence_visualization():
    """
    Add divergence visualization features to all indicator classes.
    
    This function patches the indicator classes to include enhanced
    divergence visualization in the final score breakdown.
    """
    # Add _apply_divergence_bonuses method to indicator classes
    indicator_classes = [
        VolumeIndicators,
        OrderflowIndicators,
        OrderbookIndicators,
        PriceStructureIndicators,
        SentimentIndicators
    ]

    for indicator_class in indicator_classes:
        # Skip if class is None (import failed)
        if indicator_class is None:
            continue

        # Skip if the class already has the method (like TechnicalIndicators)
        if hasattr(indicator_class, '_apply_divergence_bonuses'):
            continue
            
        # Monkey-patch _apply_divergence_bonuses method
        def _apply_divergence_bonuses(self, component_scores, divergences):
            """Apply divergence bonuses with enhanced visualization."""
            if not divergences:
                return component_scores
                
            # Make a copy to avoid modifying the original
            adjusted_scores = component_scores.copy()
            
            indicator_name = self.__class__.__name__.replace('Indicators', '')
            self.logger.info(f"\n=== Applying {indicator_name} Indicator Divergence Bonuses ===")
            self.logger.info(f"Original component scores:")
            for component, score in component_scores.items():
                self.logger.info(f"  - {component}: {score:.2f}")
                
            # Track total adjustments per component
            adjustments = {component: 0.0 for component in component_scores}
            
            # Apply bonuses from divergences
            for key, div_info in divergences.items():
                component = div_info.get('component')
                
                if component not in adjusted_scores:
                    continue
                    
                # Get or calculate bonus
                bonus = div_info.get('bonus', 0.0)
                if 'bonus' not in div_info:
                    # Calculate bonus based on divergence strength and type
                    strength = div_info.get('strength', 0)
                    div_type = div_info.get('type', 'neutral')
                    
                    # Bullish divergence increases score, bearish decreases
                    bonus = strength * 0.1 * (1 if div_type == 'bullish' else -1)
                    
                    # Store bonus in divergence info for logging
                    div_info['bonus'] = bonus
                    
                if bonus == 0.0:
                    continue
                    
                # Get timeframe information if available
                tf1, tf2 = div_info.get('timeframes', ['', ''])
                if tf1 and tf2:
                    tf1_friendly = self.TIMEFRAME_CONFIG.get(tf1, {}).get('friendly_name', tf1.upper())
                    tf2_friendly = self.TIMEFRAME_CONFIG.get(tf2, {}).get('friendly_name', tf2.upper())
                    timeframe_info = f"between {tf1_friendly} and {tf2_friendly}"
                else:
                    timeframe_info = "in analysis"
                
                div_type = div_info.get('type', 'neutral')
                
                # Log the adjustment
                self.logger.info(f"  Adjusting {component} by {bonus:.2f} points ({div_type} divergence {timeframe_info})")
                
                # Update the score
                old_score = adjusted_scores[component]
                adjusted_scores[component] = np.clip(old_score + bonus, 0, 100)
                
                # Track total adjustment
                adjustments[component] += bonus
            
            # Store the adjustments for later use in the log_indicator_results method
            self._divergence_adjustments = adjustments
            
            # Log summary of adjustments
            self.logger.info("\nFinal adjusted scores:")
            for component, score in adjusted_scores.items():
                original = component_scores[component]
                adjustment = adjustments[component]
                
                if adjustment != 0:
                    direction = "+" if adjustment > 0 else ""
                    self.logger.info(f"  - {component}: {original:.2f} → {score:.2f} ({direction}{adjustment:.2f})")
                else:
                    self.logger.info(f"  - {component}: {score:.2f} (unchanged)")
                    
            return adjusted_scores
        
        # Monkey-patch log_indicator_results method
        def log_indicator_results(self, final_score, component_scores, symbol=""):
            """Log indicator results with divergence adjustment information."""
            # Handle component mapping for OrderflowIndicators
            if hasattr(self, 'component_mapping'):
                try:
                    # Map component names for consistent logging
                    mapped_scores = {}
                    for component, score in component_scores.items():
                        config_component = self.component_mapping.get(component, component)
                        mapped_scores[config_component] = score
                    component_scores = mapped_scores
                except Exception as e:
                    self.logger.error(f"Error mapping components: {str(e)}")
            
            # Get the indicator name
            indicator_name = self.__class__.__name__.replace('Indicators', '')
            
            # Get divergence adjustments if available
            divergence_adjustments = {}
            if hasattr(self, '_divergence_adjustments'):
                divergence_adjustments = self._divergence_adjustments
                
                # If using component mapping, map the adjustment keys too
                if hasattr(self, 'component_mapping'):
                    try:
                        mapped_adjustments = {}
                        for component, adjustment in divergence_adjustments.items():
                            config_component = self.component_mapping.get(component, component)
                            mapped_adjustments[config_component] = adjustment
                        divergence_adjustments = mapped_adjustments
                    except Exception as e:
                        self.logger.error(f"Error mapping divergence adjustments: {str(e)}")
            
            # Create contribution list
            breakdown_title = f"{indicator_name} Score Contribution Breakdown"
            contributions = []
            for component, score in component_scores.items():
                weight = self.component_weights.get(component, 0)
                contribution = score * weight
                contributions.append((component, score, weight, contribution))
            
            # Sort by contribution
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Use enhanced formatter
            from src.core.formatting.formatter import LogFormatter
            formatted_section = LogFormatter.format_score_contribution_section(
                breakdown_title, 
                contributions, 
                symbol,
                divergence_adjustments
            )
            self.logger.info(formatted_section)
            
            # Log final score
            from src.core.analysis.indicator_utils import log_final_score
            log_final_score(self.logger, indicator_name, final_score, symbol)
        
        # Add methods to the class
        setattr(indicator_class, '_apply_divergence_bonuses', _apply_divergence_bonuses)
        setattr(indicator_class, 'log_indicator_results', log_indicator_results)


# Apply the patches
patch_indicators_with_divergence_visualization()
