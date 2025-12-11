"""
Beta Stability Analysis Module

Quantifies beta reliability to adjust position sizing and risk tolerance using
a composite score combining R², beta variance, and forecast error ratio.

Example:
    analyzer = BetaStabilityAnalyzer(stability_window=60)
    stability = analyzer.calculate_stability_score(
        r_squared=0.75,
        beta_series=beta_values,
        actual_returns=alt_returns,
        predicted_returns=predictions
    )

    if stability['stability_score'] > 80:
        print("High confidence - Trade full size")
"""

import numpy as np
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BetaStabilityAnalyzer:
    """
    Assess stability and reliability of beta relationships.

    Composite score (0-100) combining:
    - R² (50% weight): Goodness of fit
    - Beta variance (30% weight): Stability over time
    - Forecast error ratio (20% weight): Recent vs historical error
    """

    def __init__(self, stability_window: int = 60):
        """
        Initialize Beta Stability Analyzer.

        Args:
            stability_window: Rolling window for variance calculation (minutes)
        """
        self.window = stability_window

    def compute_beta_variance(self, beta_series: pd.Series) -> float:
        """
        Calculate rolling variance of beta estimates.

        High variance indicates regime instability.

        Args:
            beta_series: Series of beta values over time

        Returns:
            Variance of recent beta estimates
        """
        if len(beta_series) < self.window:
            # Not enough data - return high variance (conservative)
            return 0.5

        recent_variance = beta_series.iloc[-self.window:].var()
        return float(recent_variance)

    def compute_forecast_error_ratio(
        self,
        actual_returns: pd.Series,
        predicted_returns: pd.Series,
        historical_window: int = 120
    ) -> float:
        """
        Compare recent forecast errors to historical baseline.

        FER > 1.5 indicates model breakdown.

        Args:
            actual_returns: Actual altcoin returns
            predicted_returns: Predicted returns from beta model
            historical_window: Window for historical baseline

        Returns:
            Forecast Error Ratio (recent RMSE / historical RMSE)
        """
        # Recent errors (last 30 minutes)
        recent_errors = (actual_returns - predicted_returns).iloc[-30:]
        recent_rmse = np.sqrt((recent_errors ** 2).mean())

        # Historical errors
        hist_errors = (actual_returns - predicted_returns).iloc[-historical_window:-30]

        if len(hist_errors) < 10:
            # Not enough history - return neutral ratio
            return 1.0

        hist_rmse = np.sqrt((hist_errors ** 2).mean())

        # Avoid division by zero
        if hist_rmse < 1e-8:
            return 999.0  # Undefined - very poor baseline

        fer = recent_rmse / hist_rmse
        return float(fer)

    def calculate_stability_score(
        self,
        r_squared: float,
        beta_series: pd.Series,
        actual_returns: pd.Series,
        predicted_returns: pd.Series
    ) -> Dict:
        """
        Calculate composite stability score (0-100).

        Interpretation:
        - 80-100: Excellent stability, high confidence trading
        - 60-80: Good stability, trade with normal risk
        - 40-60: Fair stability, reduce position sizes
        - 0-40: Poor stability, avoid trading

        Args:
            r_squared: Coefficient of determination
            beta_series: Historical beta values
            actual_returns: Actual altcoin returns
            predicted_returns: Predicted returns from beta

        Returns:
            Dict with stability score and components
        """
        # Component 1: R-squared (50% weight)
        r2_component = 50 * r_squared

        # Component 2: Beta variance (30% weight)
        beta_var = self.compute_beta_variance(beta_series)
        # Normalize: assume variance >0.5 is very high
        beta_var_normalized = min(beta_var / 0.5, 1.0)
        variance_component = 30 * (1 - beta_var_normalized)

        # Component 3: Forecast error ratio (20% weight)
        fer = self.compute_forecast_error_ratio(actual_returns, predicted_returns)
        # Normalize: FER=1.0 is perfect, >2.0 is poor
        fer_normalized = max(0, 1 - (fer - 1.0))
        fer_component = 20 * fer_normalized

        # Composite score
        stability_score = r2_component + variance_component + fer_component
        stability_score = np.clip(stability_score, 0, 100)

        return {
            'stability_score': round(float(stability_score), 1),
            'r_squared': round(float(r_squared), 3),
            'beta_variance': round(float(beta_var), 4),
            'forecast_error_ratio': round(float(fer), 2),
            'rating': self._get_rating(stability_score),
            'recommendation': self._get_recommendation(stability_score)
        }

    @staticmethod
    def _get_rating(score: float) -> str:
        """Convert score to rating."""
        if score >= 80:
            return 'Excellent'
        elif score >= 60:
            return 'Good'
        elif score >= 40:
            return 'Fair'
        else:
            return 'Poor'

    @staticmethod
    def _get_recommendation(score: float) -> str:
        """Convert score to trading recommendation."""
        if score >= 80:
            return 'High confidence - Trade full size'
        elif score >= 60:
            return 'Good confidence - Trade normal size'
        elif score >= 40:
            return 'Low confidence - Reduce position size 50%'
        else:
            return 'No confidence - Avoid trading this pair'
