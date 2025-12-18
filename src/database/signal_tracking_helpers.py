"""
Signal Tracking Helper Functions

Provides utility functions for classifying and managing trading signal patterns
for performance tracking integration.
"""

import logging
from typing import Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)


def determine_signal_pattern(
    components: Dict[str, Any],
    signal_type: str
) -> Literal["divergence", "confirmation", "momentum", "other"]:
    """
    Classify signal pattern based on component scores.

    This function analyzes the relationship between price action (technical)
    and orderflow to determine if we have:
    - Divergence: Price moving one way, orderflow contradicting
    - Confirmation: All components aligned in same direction
    - Momentum: Strong directional movement
    - Other: Mixed or unclear signals

    Args:
        components: Dictionary of component scores (0-100 scale)
        signal_type: 'LONG' or 'SHORT'

    Returns:
        Pattern classification string

    Examples:
        >>> # LONG divergence: Price weak but orderflow bullish
        >>> determine_signal_pattern({'technical': 35, 'orderflow': 75}, 'LONG')
        'divergence'

        >>> # LONG confirmation: All aligned bullish
        >>> determine_signal_pattern({'technical': 70, 'orderflow': 72, 'volume': 68}, 'LONG')
        'confirmation'
    """
    try:
        # Extract key scores - handle both direct values and nested dicts
        def get_score(component_data):
            if isinstance(component_data, dict):
                return component_data.get('score', 50)
            return component_data or 50

        technical_score = get_score(components.get('technical', 50))
        orderflow_score = get_score(components.get('orderflow', 50))
        volume_score = get_score(components.get('volume', 50))

        # Calculate score spread
        scores = [technical_score, orderflow_score, volume_score]
        score_spread = max(scores) - min(scores)

        # Detect divergence patterns
        # Divergence: orderflow contradicts price/technical
        if abs(orderflow_score - technical_score) > 20:
            if signal_type == 'LONG':
                # LONG divergence: Low technical but high orderflow (accumulation)
                if orderflow_score > 60 and technical_score < 40:
                    logger.debug(f"LONG divergence detected: orderflow={orderflow_score}, technical={technical_score}")
                    return "divergence"
            else:  # SHORT
                # SHORT divergence: High technical but low orderflow (distribution)
                if orderflow_score < 40 and technical_score > 60:
                    logger.debug(f"SHORT divergence detected: orderflow={orderflow_score}, technical={technical_score}")
                    return "divergence"

        # Confirmation: all components aligned (spread < 15 points)
        if score_spread < 15:
            logger.debug(f"Confirmation pattern: scores tightly aligned (spread={score_spread:.1f})")
            return "confirmation"

        # Momentum: strong directional scores
        if signal_type == 'LONG' and min(scores) > 65:
            logger.debug(f"LONG momentum: all scores above 65")
            return "momentum"
        elif signal_type == 'SHORT' and max(scores) < 35:
            logger.debug(f"SHORT momentum: all scores below 35")
            return "momentum"

        # Default to other
        logger.debug(f"Pattern classified as 'other': technical={technical_score}, orderflow={orderflow_score}")
        return "other"

    except Exception as e:
        logger.error(f"Error determining signal pattern: {e}")
        return "other"


def extract_orderflow_tags(components: Dict[str, Any]) -> list:
    """
    Extract orderflow pattern tags from component data.

    Args:
        components: Dictionary of component data

    Returns:
        List of orderflow tags (e.g., ['high_buyer_aggression', 'absorption'])
    """
    tags = []

    try:
        orderflow_data = components.get('orderflow', {})

        if isinstance(orderflow_data, dict):
            # Check for buyer/seller aggression
            buyer_aggression = orderflow_data.get('buyer_aggression', 0)
            seller_aggression = orderflow_data.get('seller_aggression', 0)

            if buyer_aggression > 0.7:
                tags.append('high_buyer_aggression')
            if seller_aggression > 0.7:
                tags.append('high_seller_aggression')

            # Check for special patterns
            if orderflow_data.get('absorption_detected', False):
                tags.append('absorption')
            if orderflow_data.get('large_orders', False):
                tags.append('large_orders')
            if orderflow_data.get('iceberg_detected', False):
                tags.append('iceberg')

    except Exception as e:
        logger.error(f"Error extracting orderflow tags: {e}")

    return tags


def get_divergence_type(
    components: Dict[str, Any],
    signal_type: str,
    pattern: str
) -> Optional[str]:
    """
    Get specific divergence type if pattern is divergence.

    Args:
        components: Dictionary of component scores
        signal_type: 'LONG' or 'SHORT'
        pattern: Pattern classification

    Returns:
        Divergence type or None if not a divergence pattern
    """
    if pattern != "divergence":
        return None

    try:
        def get_score(component_data):
            if isinstance(component_data, dict):
                return component_data.get('score', 50)
            return component_data or 50

        technical_score = get_score(components.get('technical', 50))
        orderflow_score = get_score(components.get('orderflow', 50))

        if signal_type == 'LONG':
            if orderflow_score > 60 and technical_score < 40:
                return 'bullish_divergence'
        else:  # SHORT
            if orderflow_score < 40 and technical_score > 60:
                return 'bearish_divergence'

        return 'hidden_divergence'

    except Exception as e:
        logger.error(f"Error determining divergence type: {e}")
        return None


def get_validation_cohort() -> str:
    """
    Get current validation cohort identifier.

    Returns:
        Cohort identifier (e.g., '50_45' for orderflow multipliers)
    """
    # This would ideally read from config, but for now hardcode current values
    return '50_45'


def get_trigger_component(components: Dict[str, Any]) -> Optional[str]:
    """
    Identify which component triggered the signal (highest score).

    Args:
        components: Dictionary of component scores

    Returns:
        Name of component with highest score
    """
    try:
        def get_score(component_data):
            if isinstance(component_data, dict):
                return component_data.get('score', 0)
            return component_data or 0

        # Get all component scores
        component_scores = {
            name: get_score(data)
            for name, data in components.items()
        }

        if not component_scores:
            return None

        # Find component with highest score
        trigger = max(component_scores.items(), key=lambda x: x[1])
        return trigger[0]

    except Exception as e:
        logger.error(f"Error identifying trigger component: {e}")
        return None
