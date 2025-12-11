"""
Dynamic Beta Prediction Module

Forecasts expected altcoin movement magnitude given a BTC move using
exponentially weighted moving average (EWMA) beta with confidence intervals.

Example:
    predictor = DynamicBetaPredictor(alpha=0.94)

    # Update with each new data point
    for btc_ret, alt_ret in zip(btc_returns, alt_returns):
        predictor.update_beta(btc_ret, alt_ret)

    # Make prediction
    prediction = predictor.predict(btc_move_pct=1.5)
    print(f"Expected move: {prediction['expected_move_pct']}%")
"""

import numpy as np
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DynamicBetaPredictor:
    """
    Predict altcoin returns based on Bitcoin moves using dynamic beta.

    Uses EWMA for responsive beta estimation and tracks prediction errors
    for R² calculation and confidence intervals.
    """

    def __init__(self, alpha: float = 0.94):
        """
        Initialize Dynamic Beta Predictor.

        Args:
            alpha: EWMA decay factor (default: 0.94 for ~16-period half-life)
                   Use 0.94 for 1H timeframe, 0.98 for 4H timeframe
        """
        self.alpha = alpha
        self.ewma_cov = 0.0
        self.ewma_var = 0.0
        self.current_beta = 0.0  # Current beta estimate
        self.prediction_errors = []  # Track for R² calculation

    def update_beta(self, btc_return: float, alt_return: float) -> float:
        """
        Update EWMA beta with new return data.

        Args:
            btc_return: BTC log return
            alt_return: Altcoin log return

        Returns:
            Updated beta value
        """
        # Update EWMA covariance and variance
        self.ewma_cov = self.alpha * self.ewma_cov + (1 - self.alpha) * (btc_return * alt_return)
        self.ewma_var = self.alpha * self.ewma_var + (1 - self.alpha) * (btc_return ** 2)

        # Calculate and store beta (avoid division by zero)
        if self.ewma_var > 1e-8:
            self.current_beta = self.ewma_cov / self.ewma_var
        else:
            self.current_beta = 0.0

        return self.current_beta

    def predict(self, btc_move_pct: float) -> Dict:
        """
        Predict altcoin move given current Bitcoin move.

        Args:
            btc_move_pct: Bitcoin move in percentage (e.g., 1.5 for +1.5%)

        Returns:
            Dict with prediction, confidence interval, and R²
        """
        # Point prediction
        btc_move_decimal = btc_move_pct / 100
        expected_move = self.current_beta * btc_move_decimal

        # 95% confidence interval from recent prediction errors
        if len(self.prediction_errors) > 10:
            error_std = np.std(self.prediction_errors[-30:])  # Rolling 30-period
            ci_lower = expected_move - 1.96 * error_std
            ci_upper = expected_move + 1.96 * error_std
        else:
            # Not enough history yet - use point estimate
            ci_lower = ci_upper = expected_move

        # Calculate R²
        r_squared = self._calculate_r_squared()

        return {
            'beta': round(float(self.current_beta), 3),
            'r_squared': round(float(r_squared), 3),
            'btc_move_pct': btc_move_pct,
            'predicted_alt_move_pct': round(float(expected_move) * 100, 2),
            'confidence_95_lower_pct': round(float(ci_lower) * 100, 2),
            'confidence_95_upper_pct': round(float(ci_upper) * 100, 2),
            'prediction_quality': self._get_quality_rating(r_squared)
        }

    def update_error(self, actual_move: float, predicted_move: float):
        """
        Track prediction error for R² calculation.

        Args:
            actual_move: Actual altcoin move (decimal, not percent)
            predicted_move: Predicted altcoin move (decimal, not percent)
        """
        error = actual_move - predicted_move
        self.prediction_errors.append(error)

        # Keep only last 100 errors (memory management)
        if len(self.prediction_errors) > 100:
            self.prediction_errors.pop(0)

    def _calculate_r_squared(self) -> float:
        """
        Calculate R² from recent prediction errors.

        Returns:
            R² value between 0 and 1 (higher is better)
        """
        if len(self.prediction_errors) < 10:
            return 0.0

        errors = np.array(self.prediction_errors[-30:])
        ss_res = np.sum(errors ** 2)
        ss_tot = np.sum((errors - errors.mean()) ** 2)

        # Avoid division by zero
        if ss_tot < 1e-8:
            return 0.0

        r_squared = 1 - (ss_res / ss_tot)
        return float(np.clip(r_squared, 0, 1))

    @staticmethod
    def _get_quality_rating(r_squared: float) -> str:
        """Convert R² to quality rating."""
        if r_squared > 0.7:
            return 'excellent'
        elif r_squared > 0.5:
            return 'good'
        elif r_squared > 0.3:
            return 'fair'
        else:
            return 'poor'
