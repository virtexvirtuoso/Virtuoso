#!/usr/bin/env python3
"""
Unified Stop Loss Calculator Service

This service provides consistent stop loss calculations across all components
of the Virtuoso trading system, ensuring that PDF reports, alerts, and
actual trade execution all use the same sophisticated confidence-based logic.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum


class StopLossMethod(Enum):
    """Stop loss calculation methods."""
    FIXED_PERCENTAGE = "fixed_percentage"
    CONFIDENCE_BASED = "confidence_based"
    VOLATILITY_BASED = "volatility_based"


class StopLossCalculator:
    """
    Unified stop loss calculation service that implements sophisticated
    confidence-based stop loss sizing for consistent risk management.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the stop loss calculator with configuration.

        Args:
            config: Configuration dictionary containing risk management settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Extract configuration values
        self.risk_config = config.get('risk', {})
        self.risk_mgmt_config = config.get('risk_management', {})
        self.trading_config = config.get('trading', {})

        # Base stop loss percentages
        self.base_stop_loss = self.risk_mgmt_config.get('default_stop_loss', 0.02)  # 2%
        self.long_stop_percentage = self.risk_config.get('long_stop_percentage', 3.0)
        self.short_stop_percentage = self.risk_config.get('short_stop_percentage', 3.5)

        # Confidence-based scaling factors
        self.min_stop_multiplier = self.risk_config.get('min_stop_multiplier', 0.8)  # 80% of base
        self.max_stop_multiplier = self.risk_config.get('max_stop_multiplier', 1.5)  # 150% of base

        # Trading thresholds from confluence configuration
        confluence_config = config.get('confluence', {})
        thresholds_config = confluence_config.get('thresholds', {})
        self.buy_threshold = thresholds_config.get('buy', 70)
        self.sell_threshold = thresholds_config.get('sell', 35)

        self.logger.info(f"StopLossCalculator initialized - Base: {self.base_stop_loss*100:.1f}%, "
                        f"Long: {self.long_stop_percentage:.1f}%, Short: {self.short_stop_percentage:.1f}%")

    def calculate_stop_loss_percentage(
        self,
        signal_type: str,
        confluence_score: float,
        method: StopLossMethod = StopLossMethod.CONFIDENCE_BASED
    ) -> float:
        """
        Calculate stop loss percentage based on signal type, confluence score, and method.

        Args:
            signal_type: 'BUY', 'SELL', or 'NEUTRAL'
            confluence_score: Confluence score (0-100)
            method: Calculation method to use

        Returns:
            Stop loss percentage as decimal (e.g., 0.025 for 2.5%)

        Raises:
            ValueError: If invalid signal type or confluence score
        """
        if signal_type not in ['BUY', 'SELL']:
            raise ValueError(f"Invalid signal_type: {signal_type}. Must be 'BUY' or 'SELL'")

        if not 0 <= confluence_score <= 100:
            raise ValueError(f"Invalid confluence_score: {confluence_score}. Must be 0-100")

        if method == StopLossMethod.FIXED_PERCENTAGE:
            return self._calculate_fixed_percentage(signal_type)
        elif method == StopLossMethod.CONFIDENCE_BASED:
            return self._calculate_confidence_based(signal_type, confluence_score)
        elif method == StopLossMethod.VOLATILITY_BASED:
            # Future implementation for volatility-based stops
            return self._calculate_confidence_based(signal_type, confluence_score)
        else:
            raise ValueError(f"Unsupported stop loss method: {method}")

    def _calculate_fixed_percentage(self, signal_type: str) -> float:
        """Calculate simple fixed percentage stop loss."""
        if signal_type == 'BUY':
            return self.long_stop_percentage / 100
        else:  # SELL
            return self.short_stop_percentage / 100

    def _calculate_confidence_based(self, signal_type: str, confluence_score: float) -> float:
        """
        Calculate confidence-based stop loss percentage.

        Higher confidence = tighter stops (precise exit if wrong - you should know immediately)
        Lower confidence = wider stops (give uncertain trades room to develop)
        """
        # Get base stop loss percentage for the signal type
        if signal_type == 'BUY':
            base_stop = self.long_stop_percentage / 100
            threshold = self.buy_threshold
        else:  # SELL
            base_stop = self.short_stop_percentage / 100
            threshold = self.sell_threshold

        # Calculate minimum and maximum stops
        min_stop = base_stop * self.min_stop_multiplier
        max_stop = base_stop * self.max_stop_multiplier

        # Calculate confidence-based scaling
        if signal_type == 'BUY':
            # For long trades: Higher score = higher confidence = TIGHTER stop
            if confluence_score <= threshold:
                return max_stop  # Low confidence = wide stop

            # Normalize score from threshold to 100
            normalized_score = (confluence_score - threshold) / (100 - threshold)

        else:  # SELL
            # For short trades: Lower score = higher confidence = TIGHTER stop
            if confluence_score >= threshold:
                return max_stop  # Low confidence = wide stop

            # Normalize score from threshold to 0
            normalized_score = (threshold - confluence_score) / threshold

        # INVERTED: Scale stop loss based on normalized confidence
        # Higher confidence (normalized_score closer to 1) = tighter stop (closer to min_stop)
        scaled_stop = max_stop - (normalized_score * (max_stop - min_stop))

        self.logger.debug(f"Confidence-based stop: {signal_type} score={confluence_score:.1f} "
                         f"→ {scaled_stop*100:.2f}% (base={base_stop*100:.1f}%)")

        return scaled_stop

    def calculate_stop_loss_price(
        self,
        entry_price: float,
        signal_type: str,
        confluence_score: float,
        method: StopLossMethod = StopLossMethod.CONFIDENCE_BASED
    ) -> float:
        """
        Calculate the actual stop loss price.

        Args:
            entry_price: Entry price for the trade
            signal_type: 'BUY' or 'SELL'
            confluence_score: Confluence score (0-100)
            method: Calculation method to use

        Returns:
            Stop loss price

        Raises:
            ValueError: If invalid inputs
        """
        if entry_price <= 0:
            raise ValueError(f"Invalid entry_price: {entry_price}. Must be positive")

        stop_loss_pct = self.calculate_stop_loss_percentage(signal_type, confluence_score, method)

        if signal_type == 'BUY':
            # Long position: stop below entry
            stop_price = entry_price * (1 - stop_loss_pct)
        else:  # SELL
            # Short position: stop above entry
            stop_price = entry_price * (1 + stop_loss_pct)

        self.logger.debug(f"Stop loss price: {signal_type} @{entry_price:.2f} "
                         f"→ stop @{stop_price:.2f} ({stop_loss_pct*100:.2f}%)")

        return stop_price

    def get_stop_loss_info(
        self,
        signal_data: Dict[str, Any],
        method: StopLossMethod = StopLossMethod.CONFIDENCE_BASED
    ) -> Dict[str, Any]:
        """
        Get comprehensive stop loss information from signal data.

        Args:
            signal_data: Signal data dictionary
            method: Calculation method to use

        Returns:
            Dictionary containing stop loss information:
            {
                'stop_loss_percentage': float,  # As decimal (0.025 = 2.5%)
                'stop_loss_price': float,       # Actual stop price
                'method': str,                  # Method used
                'confidence_score': float,      # Score used
                'signal_type': str             # Signal type
            }
        """
        # Extract required data
        signal_type = signal_data.get('signal_type', 'NEUTRAL')
        confluence_score = signal_data.get('confluence_score', 50)
        entry_price = signal_data.get('price') or signal_data.get('entry_price', 0)

        if signal_type == 'NEUTRAL' or entry_price <= 0:
            return {
                'stop_loss_percentage': 0,
                'stop_loss_price': 0,
                'method': method.value,
                'confidence_score': confluence_score,
                'signal_type': signal_type,
                'error': 'Invalid signal type or entry price'
            }

        try:
            stop_loss_pct = self.calculate_stop_loss_percentage(signal_type, confluence_score, method)
            stop_loss_price = self.calculate_stop_loss_price(entry_price, signal_type, confluence_score, method)

            return {
                'stop_loss_percentage': stop_loss_pct,
                'stop_loss_price': stop_loss_price,
                'method': method.value,
                'confidence_score': confluence_score,
                'signal_type': signal_type,
                'entry_price': entry_price
            }

        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return {
                'stop_loss_percentage': 0,
                'stop_loss_price': 0,
                'method': method.value,
                'confidence_score': confluence_score,
                'signal_type': signal_type,
                'error': str(e)
            }

    def validate_stop_loss(self, stop_loss_info: Dict[str, Any]) -> bool:
        """
        Validate stop loss information for reasonableness.

        Args:
            stop_loss_info: Stop loss info from get_stop_loss_info()

        Returns:
            True if valid, False otherwise
        """
        if 'error' in stop_loss_info:
            return False

        stop_loss_pct = stop_loss_info.get('stop_loss_percentage', 0)

        # Check if percentage is within reasonable bounds (0.1% to 10%)
        if not 0.001 <= stop_loss_pct <= 0.10:
            self.logger.warning(f"Stop loss percentage outside reasonable bounds: {stop_loss_pct*100:.2f}%")
            return False

        return True


# Global instance for easy access
_stop_loss_calculator = None


def get_stop_loss_calculator(config: Optional[Dict[str, Any]] = None) -> StopLossCalculator:
    """
    Get the global stop loss calculator instance.

    Args:
        config: Configuration dictionary (only used for first initialization)

    Returns:
        StopLossCalculator instance
    """
    global _stop_loss_calculator

    if _stop_loss_calculator is None:
        if config is None:
            raise ValueError("Config required for first initialization")
        _stop_loss_calculator = StopLossCalculator(config)

    return _stop_loss_calculator