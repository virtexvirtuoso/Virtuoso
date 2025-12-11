"""
Bitcoin-Altcoin Predictive Analytics

This module provides five statistical signals for predicting altcoin movement
based on Bitcoin price action:

1. LeadLagAnalyzer - Detect propagation delays
2. DynamicBetaPredictor - Forecast magnitude with confidence intervals
3. BetaStabilityAnalyzer - Score reliability
4. BetaDivergenceDetector - Identify mean-reversion opportunities
5. VolatilitySpilloverDetector - Predict volatility increases

Usage:
    from src.core.analysis.bitcoin_altcoin_predictor import BitcoinAltcoinPredictor

    predictor = BitcoinAltcoinPredictor()
    analysis = await predictor.analyze_altcoin('ETH', btc_prices, eth_prices)
"""

from .lead_lag_analyzer import LeadLagAnalyzer
from .dynamic_beta_predictor import DynamicBetaPredictor
from .beta_stability_analyzer import BetaStabilityAnalyzer
from .beta_divergence_detector import BetaDivergenceDetector
from .volatility_spillover_detector import VolatilitySpilloverDetector
from .bitcoin_altcoin_predictor import BitcoinAltcoinPredictor

__all__ = [
    'LeadLagAnalyzer',
    'DynamicBetaPredictor',
    'BetaStabilityAnalyzer',
    'BetaDivergenceDetector',
    'VolatilitySpilloverDetector',
    'BitcoinAltcoinPredictor',
]

__version__ = '1.0.0'
