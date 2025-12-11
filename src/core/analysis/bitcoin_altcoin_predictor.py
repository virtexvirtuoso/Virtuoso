"""
Bitcoin-Altcoin Predictive Analytics - Unified Service

Combines all 5 trading signals into a single comprehensive analysis:
1. Lead-Lag Analysis
2. Dynamic Beta Prediction
3. Beta Stability Scoring
4. Divergence Detection
5. Volatility Spillover

Example:
    predictor = BitcoinAltcoinPredictor()
    analysis = predictor.analyze_altcoin(
        symbol='ETH',
        btc_prices=btc_price_series,
        alt_prices=eth_price_series,
        btc_recent_move_pct=2.0
    )

    print(f"Stability: {analysis['stability']['stability_score']}/100")
    if analysis['divergence']['signal_active']:
        print(f"Divergence signal: {analysis['divergence']['direction']}")
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging

from .lead_lag_analyzer import LeadLagAnalyzer
from .dynamic_beta_predictor import DynamicBetaPredictor
from .beta_stability_analyzer import BetaStabilityAnalyzer
from .beta_divergence_detector import BetaDivergenceDetector
from .volatility_spillover_detector import VolatilitySpilloverDetector

logger = logging.getLogger(__name__)


class BitcoinAltcoinPredictor:
    """
    Unified service for Bitcoin-Altcoin predictive analytics.

    Computes all 5 trading signals efficiently and returns comprehensive
    analysis for position sizing, entry timing, and risk management.
    """

    def __init__(self):
        """Initialize all signal analyzers."""
        self.lead_lag = LeadLagAnalyzer(max_lag_minutes=60)
        self.beta_predictor = DynamicBetaPredictor(alpha=0.94)
        self.stability = BetaStabilityAnalyzer(stability_window=60)
        self.divergence = BetaDivergenceDetector(lookback_window=120, z_threshold=2.5)
        self.volatility = VolatilitySpilloverDetector(rv_window=5, baseline_window=60)

    def analyze_altcoin(
        self,
        symbol: str,
        btc_prices: pd.Series,
        alt_prices: pd.Series,
        btc_recent_move_pct: float = None
    ) -> Dict[str, Any]:
        """
        Run full predictive analysis for one altcoin.

        Args:
            symbol: Altcoin symbol (e.g., 'ETH')
            btc_prices: Series of BTC prices (60-240 minutes of 1-min data)
            alt_prices: Series of altcoin prices (same length as btc_prices)
            btc_recent_move_pct: Optional recent BTC move for prediction

        Returns:
            Dict with all signals and metrics:
            {
                'symbol': 'ETH',
                'beta': 1.30,
                'r_squared': 0.75,
                'stability': {...},
                'lead_lag': {...},
                'divergence': {...},
                'volatility': {...},
                'prediction': {...} or None
            }
        """
        try:
            # Calculate returns (log returns for stability)
            btc_returns = np.log(btc_prices / btc_prices.shift(1)).fillna(0)
            alt_returns = np.log(alt_prices / alt_prices.shift(1)).fillna(0)

            # 1. Update dynamic beta (process all data points)
            for btc_ret, alt_ret in zip(btc_returns, alt_returns):
                current_beta = self.beta_predictor.update_beta(btc_ret, alt_ret)

            # 2. Calculate R² (need predicted returns for stability)
            beta_series = pd.Series([self.beta_predictor.current_beta] * len(btc_returns))
            predicted_returns = beta_series * btc_returns
            r_squared = self.beta_predictor._calculate_r_squared()

            # Track errors for future predictions
            for actual, predicted in zip(alt_returns, predicted_returns):
                self.beta_predictor.update_error(actual, predicted)

            # 3. Stability assessment
            stability_metrics = self.stability.calculate_stability_score(
                r_squared=r_squared,
                beta_series=beta_series,
                actual_returns=alt_returns,
                predicted_returns=predicted_returns
            )

            # 4. Lead-lag analysis
            lead_lag_signal = self.lead_lag.generate_lead_lag_signal(
                btc_prices=btc_prices,
                alt_prices=alt_prices
            )

            # 5. Divergence detection
            divergence_signal = self.divergence.detect_divergence_signal(
                btc_returns=btc_returns,
                alt_returns=alt_returns,
                beta=self.beta_predictor.current_beta,
                stability_score=stability_metrics['stability_score']
            )

            # 6. Volatility spillover
            volatility_signal = self.volatility.detect_volatility_spike(
                btc_returns=btc_returns,
                alt_returns=alt_returns
            )

            # 7. Optional: Prediction if BTC moved
            prediction = None
            if btc_recent_move_pct is not None:
                prediction = self.beta_predictor.predict(btc_recent_move_pct)

            return {
                'symbol': symbol,
                'beta': round(float(self.beta_predictor.current_beta), 3),
                'r_squared': round(float(r_squared), 3),
                'stability': stability_metrics,
                'lead_lag': lead_lag_signal,
                'divergence': divergence_signal,
                'volatility': volatility_signal,
                'prediction': prediction,
                'timestamp': pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            return {
                'symbol': symbol,
                'error': str(e),
                'timestamp': pd.Timestamp.now().isoformat()
            }

    def analyze_all_altcoins(
        self,
        btc_prices: pd.Series,
        altcoin_prices: Dict[str, pd.Series]
    ) -> List[Dict]:
        """
        Analyze all altcoins in parallel.

        Args:
            btc_prices: BTC price series (60-240 minutes)
            altcoin_prices: Dict mapping symbol -> price series

        Returns:
            List of analysis results for each altcoin, sorted by stability
        """
        results = []

        for symbol, prices in altcoin_prices.items():
            if len(prices) < 60:  # Minimum data requirement
                logger.warning(f"Skipping {symbol}: insufficient data ({len(prices)} points)")
                continue

            # Ensure prices align with BTC (same length)
            if len(prices) != len(btc_prices):
                logger.warning(f"Skipping {symbol}: price series length mismatch")
                continue

            analysis = self.analyze_altcoin(symbol, btc_prices, prices)
            results.append(analysis)

        # Sort by stability score (most reliable first)
        results.sort(
            key=lambda x: x.get('stability', {}).get('stability_score', 0),
            reverse=True
        )

        return results

    def get_actionable_trades(
        self,
        btc_prices: pd.Series,
        altcoin_prices: Dict[str, pd.Series],
        min_stability: float = 60.0,
        min_z_score: float = 2.5
    ) -> List[Dict]:
        """
        Filter for actionable trading signals only.

        Returns only altcoins with:
        - Stability score >= min_stability
        - Active divergence signal with |Z| >= min_z_score

        Args:
            btc_prices: BTC price series
            altcoin_prices: Dict of altcoin price series
            min_stability: Minimum stability score (default: 60)
            min_z_score: Minimum |Z-score| for divergence (default: 2.5)

        Returns:
            List of actionable trade signals
        """
        all_analyses = self.analyze_all_altcoins(btc_prices, altcoin_prices)

        actionable = []
        for analysis in all_analyses:
            if 'error' in analysis:
                continue

            stability_score = analysis.get('stability', {}).get('stability_score', 0)
            divergence = analysis.get('divergence', {})

            # Check if signal meets criteria
            if (stability_score >= min_stability and
                divergence.get('signal_active') and
                abs(divergence.get('z_score', 0)) >= min_z_score):

                actionable.append({
                    'symbol': analysis['symbol'],
                    'direction': divergence['direction'],
                    'z_score': divergence['z_score'],
                    'stability_score': stability_score,
                    'beta': analysis['beta'],
                    'confidence': divergence['confidence'],
                    'recommendation': f"{divergence['direction'].upper()} {analysis['symbol']} "
                                    f"(Z={divergence['z_score']}, Stability={stability_score}/100)"
                })

        # Sort by |Z-score| (strongest signals first)
        actionable.sort(key=lambda x: abs(x['z_score']), reverse=True)

        return actionable
