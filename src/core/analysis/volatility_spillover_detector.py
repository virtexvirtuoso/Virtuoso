"""
Volatility Spillover Detection Module

Predicts altcoin volatility increases based on Bitcoin volatility spikes using
realized volatility and volatility beta.

Example:
    detector = VolatilitySpilloverDetector(rv_window=5, baseline_window=60)
    signal = detector.detect_volatility_spike(
        btc_returns=btc_rets,
        alt_returns=alt_rets
    )

    if signal['spike_detected']:
        print(f"BTC vol spiked {signal['btc_vol_ratio']}x → Widen stops")
"""

import numpy as np
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class VolatilitySpilloverDetector:
    """
    Detect Bitcoin volatility spikes and predict altcoin volatility response.

    Uses realized volatility (RV) calculated from high-frequency returns.
    """

    def __init__(self, rv_window: int = 5, baseline_window: int = 60):
        """
        Initialize Volatility Spillover Detector.

        Args:
            rv_window: Window for realized volatility calculation (minutes)
            baseline_window: Window for baseline volatility (minutes)
        """
        self.rv_window = rv_window
        self.baseline_window = baseline_window

    def calculate_realized_volatility(self, returns: pd.Series) -> pd.Series:
        """
        Calculate realized volatility in rolling windows.

        RV = sqrt(sum of squared returns)

        Args:
            returns: Log returns series

        Returns:
            Series of realized volatility values
        """
        squared_returns = returns ** 2
        rv = squared_returns.rolling(self.rv_window).sum().apply(np.sqrt)
        return rv

    def calculate_volatility_beta(
        self,
        btc_rv: pd.Series,
        alt_rv: pd.Series
    ) -> float:
        """
        Estimate how altcoin volatility responds to Bitcoin volatility.

        Args:
            btc_rv: BTC realized volatility series
            alt_rv: Altcoin realized volatility series

        Returns:
            Volatility beta (Cov(alt_rv, btc_rv) / Var(btc_rv))
        """
        # Use recent window for beta estimation
        recent_btc_rv = btc_rv.iloc[-self.baseline_window:]
        recent_alt_rv = alt_rv.iloc[-self.baseline_window:]

        # Remove NaN values
        mask = ~(recent_btc_rv.isna() | recent_alt_rv.isna())
        recent_btc_rv = recent_btc_rv[mask]
        recent_alt_rv = recent_alt_rv[mask]

        if len(recent_btc_rv) < 10:
            return 1.0  # Default to 1:1 relationship

        cov = np.cov(recent_btc_rv, recent_alt_rv)[0, 1]
        var = np.var(recent_btc_rv)

        if var < 1e-8:
            return 1.0

        vol_beta = cov / var
        return float(vol_beta)

    def detect_volatility_spike(
        self,
        btc_returns: pd.Series,
        alt_returns: pd.Series,
        spike_threshold: float = 1.5
    ) -> Dict:
        """
        Detect BTC volatility spike and predict alt volatility increase.

        Args:
            btc_returns: BTC log returns (1-minute)
            alt_returns: Altcoin log returns (1-minute)
            spike_threshold: Ratio to trigger spike (default: 1.5x baseline)

        Returns:
            Signal with predicted volatility expansion and recommendations
        """
        # Calculate realized volatilities
        btc_rv = self.calculate_realized_volatility(btc_returns)
        alt_rv = self.calculate_realized_volatility(alt_returns)

        # Current and baseline BTC volatility
        current_btc_rv = btc_rv.iloc[-1]
        baseline_btc_rv = btc_rv.iloc[-self.baseline_window:-self.rv_window].mean()

        # Handle NaN or zero baseline
        if pd.isna(baseline_btc_rv) or baseline_btc_rv < 1e-8:
            baseline_btc_rv = current_btc_rv

        # Volatility beta
        vol_beta = self.calculate_volatility_beta(btc_rv, alt_rv)

        # Check for spike
        vol_ratio = current_btc_rv / baseline_btc_rv if baseline_btc_rv > 0 else 1.0
        spike_detected = vol_ratio > spike_threshold

        # Predict alt volatility response
        current_alt_rv = alt_rv.iloc[-1]
        if spike_detected:
            vol_increase = vol_beta * (current_btc_rv - baseline_btc_rv)
            predicted_alt_rv = current_alt_rv + vol_increase
        else:
            predicted_alt_rv = current_alt_rv

        # Annualization factor for crypto (24/7 trading)
        # Annualized vol = RV * sqrt(minutes_per_year / window_size)
        annual_factor = np.sqrt((365 * 24 * 60) / self.rv_window)

        return {
            'spike_detected': bool(spike_detected),
            'btc_vol_current': round(float(current_btc_rv) * 100, 2),
            'btc_vol_baseline': round(float(baseline_btc_rv) * 100, 2),
            'btc_vol_ratio': round(float(vol_ratio), 2),
            'btc_vol_annualized_pct': round(float(current_btc_rv * annual_factor) * 100, 1),
            'volatility_beta': round(float(vol_beta), 2),
            'alt_vol_current': round(float(current_alt_rv) * 100, 2),
            'alt_vol_predicted': round(float(predicted_alt_rv) * 100, 2),
            'alt_vol_annualized_pct': round(float(predicted_alt_rv * annual_factor) * 100, 1),
            'expected_increase_pct': round((predicted_alt_rv / current_alt_rv - 1) * 100, 1) if current_alt_rv > 0 else 0,
            'recommendation': self._get_vol_recommendation(spike_detected, vol_ratio)
        }

    @staticmethod
    def _get_vol_recommendation(spike: bool, ratio: float) -> str:
        """Convert volatility spike to recommendation."""
        if not spike:
            return 'Normal volatility regime - No action needed'
        elif ratio > 2.0:
            return 'EXTREME vol spike - Reduce all positions, widen stops 2-3x'
        elif ratio > 1.5:
            return 'Significant vol spike - Widen stop-losses 1.5-2x'
        else:
            return 'Moderate vol increase - Monitor positions'
