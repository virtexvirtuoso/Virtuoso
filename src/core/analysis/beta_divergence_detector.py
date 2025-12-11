"""
Beta Divergence Detection Module

Identifies when altcoins diverge from expected beta relationship for mean-reversion
trading opportunities using Z-score analysis.

Example:
    detector = BetaDivergenceDetector(lookback_window=120, z_threshold=2.5)
    signal = detector.detect_divergence_signal(
        btc_returns=btc_rets,
        alt_returns=alt_rets,
        beta=1.2,
        stability_score=72.0
    )

    if signal['signal_active'] and signal['direction'] == 'long':
        print(f"Alt underperforming (Z={signal['z_score']}) → LONG signal")
"""

import numpy as np
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BetaDivergenceDetector:
    """
    Detect when altcoins diverge from expected beta relationship.

    Uses Z-score of divergence (actual - expected returns) to identify
    mean-reversion opportunities.
    """

    def __init__(self, lookback_window: int = 120, z_threshold: float = 2.5):
        """
        Initialize Beta Divergence Detector.

        Args:
            lookback_window: Window for Z-score calculation (minutes)
            z_threshold: Minimum |Z| to trigger signal (default: 2.5 for crypto)
        """
        self.window = lookback_window
        self.z_threshold = z_threshold

    def calculate_divergence_zscore(
        self,
        btc_returns: pd.Series,
        alt_returns: pd.Series,
        beta: float
    ) -> pd.Series:
        """
        Calculate rolling Z-score of divergence from beta relationship.

        Args:
            btc_returns: BTC log returns
            alt_returns: Altcoin log returns
            beta: Current beta estimate

        Returns:
            Series of Z-scores
        """
        # Expected returns based on beta
        expected_returns = beta * btc_returns

        # Divergence (residuals)
        divergence = alt_returns - expected_returns

        # Rolling Z-score
        rolling_mean = divergence.rolling(self.window).mean()
        rolling_std = divergence.rolling(self.window).std()

        # Avoid division by zero
        rolling_std = rolling_std.replace(0, 1e-8)

        z_score = (divergence - rolling_mean) / rolling_std
        return z_score.fillna(0)

    def detect_divergence_signal(
        self,
        btc_returns: pd.Series,
        alt_returns: pd.Series,
        beta: float,
        stability_score: float,
        min_stability: float = 60.0
    ) -> Dict:
        """
        Generate mean-reversion trading signal based on divergence.

        Signal Logic:
        - Only fire when stability_score > min_stability (avoid regime changes)
        - Z > +2.5: Altcoin outperforming → SHORT (fade the divergence)
        - Z < -2.5: Altcoin underperforming → LONG (fade the divergence)

        Args:
            btc_returns: BTC log returns
            alt_returns: Altcoin log returns
            beta: Current beta estimate
            stability_score: Beta stability score (0-100)
            min_stability: Minimum stability to trade (default: 60)

        Returns:
            Dict with signal information
        """
        z_scores = self.calculate_divergence_zscore(btc_returns, alt_returns, beta)
        current_z = z_scores.iloc[-1]

        # Calculate recent divergence magnitude
        expected_returns = beta * btc_returns
        recent_divergence = (alt_returns - expected_returns).iloc[-5:].sum()

        signal = {
            'z_score': round(float(current_z), 2),
            'divergence_magnitude_pct': round(float(recent_divergence) * 100, 2),
            'stability_score': stability_score,
            'signal_active': False,
            'signal_type': None,
            'direction': None,
            'confidence': None
        }

        # Only trade divergences in stable regimes
        if stability_score < min_stability:
            signal['signal_type'] = 'no_signal'
            signal['confidence'] = 'low_stability'
            return signal

        # Check for significant divergence
        if abs(current_z) > self.z_threshold:
            signal['signal_active'] = True
            signal['signal_type'] = 'mean_reversion'

            if current_z > self.z_threshold:
                # Altcoin outperforming → Expect reversion down
                signal['direction'] = 'short'
                signal['confidence'] = 'extreme' if current_z > 3.5 else 'strong'
            elif current_z < -self.z_threshold:
                # Altcoin underperforming → Expect reversion up
                signal['direction'] = 'long'
                signal['confidence'] = 'extreme' if current_z < -3.5 else 'strong'

        return signal

    def get_historical_divergences(
        self,
        btc_returns: pd.Series,
        alt_returns: pd.Series,
        beta: float,
        threshold: float = 2.5
    ) -> pd.DataFrame:
        """
        Get historical divergence events for backtesting.

        Args:
            btc_returns: BTC log returns
            alt_returns: Altcoin log returns
            beta: Beta estimate
            threshold: Z-score threshold

        Returns:
            DataFrame with divergence events (timestamp, z_score, direction)
        """
        z_scores = self.calculate_divergence_zscore(btc_returns, alt_returns, beta)

        # Find events where |Z| > threshold
        events = []
        for i in range(len(z_scores)):
            z = z_scores.iloc[i]
            if abs(z) > threshold:
                events.append({
                    'index': i,
                    'timestamp': z_scores.index[i] if hasattr(z_scores, 'index') else i,
                    'z_score': float(z),
                    'direction': 'long' if z < -threshold else 'short',
                    'magnitude': abs(float(z))
                })

        return pd.DataFrame(events) if events else pd.DataFrame()
