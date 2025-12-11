"""
Lead-Lag Analysis Module

Detects time delays between BTC price movements and altcoin responses using
cross-correlation functions (CCF) with FFT optimization.

Example:
    analyzer = LeadLagAnalyzer(max_lag_minutes=60)
    signal = analyzer.generate_lead_lag_signal(btc_prices, alt_prices)

    if signal['signal_active']:
        print(f"BTC leads {symbol} by {signal['optimal_lag_minutes']} minutes")
"""

import numpy as np
import pandas as pd
from scipy.signal import correlate
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class LeadLagAnalyzer:
    """
    Detect lead-lag relationships between Bitcoin and altcoins.

    Uses cross-correlation function (CCF) to identify optimal time delay
    where altcoin returns show maximum correlation with BTC returns.
    """

    def __init__(self, max_lag_minutes: int = 60):
        """
        Initialize Lead-Lag Analyzer.

        Args:
            max_lag_minutes: Maximum lag to test (default: 60 minutes)
        """
        self.max_lag = max_lag_minutes

    def compute_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate log returns from price series."""
        return np.log(prices / prices.shift(1)).fillna(0)

    def find_optimal_lag(
        self,
        btc_returns: pd.Series,
        alt_returns: pd.Series
    ) -> Tuple[int, float, float]:
        """
        Find optimal lag using cross-correlation.

        Args:
            btc_returns: BTC log returns
            alt_returns: Altcoin log returns

        Returns:
            (optimal_lag_minutes, max_correlation, confidence_interval)
        """
        # Normalize returns for correlation
        btc_norm = (btc_returns - btc_returns.mean()) / btc_returns.std()
        alt_norm = (alt_returns - alt_returns.mean()) / alt_returns.std()

        # Compute cross-correlation using FFT (fast)
        correlation = correlate(alt_norm, btc_norm, mode='same', method='fft')
        correlation = correlation / len(btc_norm)

        # Find peak in positive lag region (BTC leads)
        center = len(correlation) // 2
        positive_lags = correlation[center:center + self.max_lag]

        optimal_lag = np.argmax(positive_lags)
        max_corr = positive_lags[optimal_lag]

        # Confidence interval (statistical significance)
        se = 1.0 / np.sqrt(len(btc_returns) - optimal_lag)
        ci_95 = 1.96 * se

        return optimal_lag, max_corr, ci_95

    def generate_lead_lag_signal(
        self,
        btc_prices: pd.Series,
        alt_prices: pd.Series,
        btc_move_threshold: float = 0.005  # 0.5%
    ) -> Dict:
        """
        Generate trading signal based on lead-lag relationship.

        Signal Logic:
        - If BTC moves >threshold in last 5 minutes
        - Predict alt will follow with lag k* minutes
        - Return entry signal with expected timing

        Args:
            btc_prices: BTC price series
            alt_prices: Altcoin price series
            btc_move_threshold: Minimum BTC move to trigger signal (default: 0.5%)

        Returns:
            Dict with signal information
        """
        btc_returns = self.compute_returns(btc_prices)
        alt_returns = self.compute_returns(alt_prices)

        # Find optimal lag (recompute every 15 minutes to track regime)
        optimal_lag, correlation, ci = self.find_optimal_lag(btc_returns, alt_returns)

        # Check recent BTC move (last 5 minutes)
        recent_btc_move = btc_returns.iloc[-5:].sum()

        # Generate signal
        signal = {
            'optimal_lag_minutes': int(optimal_lag),
            'correlation': round(float(correlation), 3),
            'confidence_interval': round(float(ci), 3),
            'significant': bool(abs(correlation) > 2 * ci),  # 95% confidence
            'recent_btc_move_pct': round(float(recent_btc_move) * 100, 2),
            'signal_active': False,
            'direction': None,
            'expected_alt_move_pct': 0.0,
            'entry_window_minutes': int(optimal_lag)
        }

        # Activate signal if BTC moved significantly
        if abs(recent_btc_move) > btc_move_threshold and signal['significant']:
            signal['signal_active'] = True
            signal['direction'] = 'long' if recent_btc_move > 0 else 'short'

            # Estimate expected alt move (simple beta approximation)
            beta_estimate = np.cov(alt_returns, btc_returns)[0, 1] / np.var(btc_returns)
            signal['expected_alt_move_pct'] = round(float(beta_estimate * recent_btc_move) * 100, 2)

        return signal
