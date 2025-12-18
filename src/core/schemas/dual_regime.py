"""
Dual-Regime Signal Enhancement Data Schemas

Dataclasses for dual-regime calculator inputs and outputs.
Separated from calculator for clean imports.

Author: Virtuoso Team
Version: 1.0.0
Created: 2025-12-16
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class MarketRegimeContext:
    """
    Market-wide regime data from external sources.

    Sourced from:
    - crypto-perps-tracker (port 8050): derivatives sentiment
    - CoinGecko: global market metrics
    - Alternative.me: Fear & Greed Index

    Fields:
        bias: Market directional bias ("BULLISH", "NEUTRAL", "BEARISH")
        fear_greed: Fear & Greed Index (0-100 scale)
        long_pct: Percentage of long positions (0-100)
        short_pct: Percentage of short positions (0-100)
        funding_rate: Perpetuals funding rate (decimal, e.g., 0.0024 = 0.24%)
        btc_dominance: Bitcoin market dominance percentage
        confidence: Data quality/freshness (0-1)
    """
    bias: str
    fear_greed: int
    long_pct: float
    short_pct: float
    funding_rate: float
    btc_dominance: float
    confidence: float


@dataclass
class SymbolRegimeContext:
    """
    Symbol-specific regime data from market_regime_detector.py

    Per-symbol analysis including trend strength, volatility state,
    and multi-timeframe alignment.

    Fields:
        regime: Regime classification (e.g., "STRONG_UPTREND", "RANGING")
        confidence: Regime classification confidence (0-1)
        trend_direction: Normalized trend strength × direction (-1 to +1)
        mtf_aligned: Multi-timeframe agreement boolean
        volatility_percentile: Current volatility vs historical (0-100)
    """
    regime: str
    confidence: float
    trend_direction: float
    mtf_aligned: bool
    volatility_percentile: float


@dataclass
class DualRegimeResult:
    """
    Output of dual-regime calculation.

    Contains the final multiplier to apply to confluence scores plus
    detailed breakdown for monitoring and debugging.

    Fields:
        final_multiplier: Multiplier to apply to confluence score (typically 0.75-1.25)
        market_factor: Market-wide adjustment factor (0.75-1.25)
        symbol_factor: Symbol-specific adjustment factor (0.85-1.15)
        blending_weight: Symbol influence weight (0-0.75, market retains 25% min)
        regime_type: Classification string (e.g., "aligned_momentum", "relative_strength")
        confidence: Overall confidence in adjustment (0-1)
        metadata: Dictionary with detailed breakdown for debugging

    Usage:
        adjusted_score = base_confluence_score * result.final_multiplier
    """
    final_multiplier: float
    market_factor: float
    symbol_factor: float
    blending_weight: float
    regime_type: str
    confidence: float
    metadata: Dict[str, Any]
