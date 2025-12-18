"""
Market Regime API Routes

Provides endpoints for:
- Current regime state for all symbols
- Regime state for specific symbol
- Recent regime changes
- Regime history for a symbol

Supports cross-service data flow:
- When running standalone (web_server.py), reads from shared cache
- When running integrated (main.py), reads from local RegimeMonitor
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel, Field

# Shared cache import is done lazily inside functions to avoid circular imports
SHARED_CACHE_AVAILABLE = True  # Will be checked at runtime

logger = logging.getLogger(__name__)
router = APIRouter()


# ========================================
# Pydantic Models
# ========================================

class RegimeState(BaseModel):
    """Current regime state for a symbol."""
    regime: str
    confidence: float
    trend_direction: float
    volatility_percentile: float
    liquidity_score: float
    mtf_aligned: bool
    conflict_type: str
    timestamp: float
    timestamp_iso: str
    emoji: Optional[str] = None


class RegimeChange(BaseModel):
    """A regime change event."""
    symbol: str
    previous_regime: str
    new_regime: str
    previous_confidence: float
    new_confidence: float
    trigger: str
    conflict_type: Optional[str] = None
    timestamp: float
    timestamp_iso: str


class RegimeSummary(BaseModel):
    """Summary of all current regimes."""
    total_symbols: int
    regime_distribution: Dict[str, int]
    average_confidence: float
    high_volatility_count: int
    low_liquidity_count: int
    last_update: Optional[float] = None


class RegimeStats(BaseModel):
    """Monitor statistics."""
    regimes_tracked: int
    changes_detected: int
    alerts_sent: int
    symbols_tracked: List[str]
    changes_in_memory: int
    last_update: Optional[float] = None


# ========================================
# Shared Cache Helpers
# ========================================

async def get_regimes_from_shared_cache() -> Optional[Dict[str, Any]]:
    """Try to read regime data from shared cache (cross-service fallback)."""
    try:
        # Lazy import to avoid circular imports
        from src.core.cache.shared_cache_bridge import get_shared_cache_bridge
        bridge = get_shared_cache_bridge()
        data, is_cross_service = await bridge.get_shared_data('regime:current')
        if data and is_cross_service:
            logger.debug(f"Read regime data from shared cache: {len(data)} symbols")
        return data
    except ImportError:
        logger.debug("Shared cache bridge not available")
        return None
    except Exception as e:
        logger.debug(f"Could not read from shared cache: {e}")
        return None


async def get_changes_from_shared_cache() -> Optional[List[Dict[str, Any]]]:
    """Try to read regime changes from shared cache."""
    try:
        from src.core.cache.shared_cache_bridge import get_shared_cache_bridge
        bridge = get_shared_cache_bridge()
        data, _ = await bridge.get_shared_data('regime:changes')
        return data
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"Could not read changes from shared cache: {e}")
        return None


async def get_stats_from_shared_cache() -> Optional[Dict[str, Any]]:
    """Try to read regime stats from shared cache."""
    try:
        from src.core.cache.shared_cache_bridge import get_shared_cache_bridge
        bridge = get_shared_cache_bridge()
        data, _ = await bridge.get_shared_data('regime:stats')
        return data
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"Could not read stats from shared cache: {e}")
        return None


def compute_summary_from_regimes(regimes: Dict[str, Any], last_update: Optional[float] = None) -> Dict[str, Any]:
    """Compute regime summary from raw regimes data."""
    if not regimes:
        return {
            'total_symbols': 0,
            'regime_distribution': {},
            'average_confidence': 0.0,
            'high_volatility_count': 0,
            'low_liquidity_count': 0,
            'last_update': last_update
        }

    distribution = {}
    confidences = []
    high_vol = 0
    low_liq = 0

    for symbol, state in regimes.items():
        regime = state.get('regime', 'unknown')
        distribution[regime] = distribution.get(regime, 0) + 1
        confidences.append(state.get('confidence', 0))

        if regime == 'high_volatility':
            high_vol += 1
        elif regime == 'low_liquidity':
            low_liq += 1

    return {
        'total_symbols': len(regimes),
        'regime_distribution': distribution,
        'average_confidence': sum(confidences) / len(confidences) if confidences else 0,
        'high_volatility_count': high_vol,
        'low_liquidity_count': low_liq,
        'last_update': last_update
    }


def compute_trading_bias_from_regimes(regimes: Dict[str, Any], last_update: Optional[float] = None) -> Dict[str, Any]:
    """Compute trading bias from raw regimes data."""
    if not regimes:
        return {
            'overall_bias': 'NEUTRAL',
            'confidence': 0.0,
            'bullish_count': 0,
            'bearish_count': 0,
            'neutral_count': 0,
            'caution_count': 0,
            'recommendation': 'Insufficient data',
            'last_update': last_update
        }

    bullish = 0
    bearish = 0
    neutral = 0
    caution = 0
    total_conf = 0.0

    for symbol, state in regimes.items():
        regime = state.get('regime', 'unknown')
        conf = state.get('confidence', 0)
        total_conf += conf

        if regime in ['strong_uptrend', 'moderate_uptrend']:
            bullish += 1
        elif regime in ['strong_downtrend', 'moderate_downtrend']:
            bearish += 1
        elif regime == 'ranging':
            neutral += 1
        else:  # high_volatility, low_liquidity, unknown
            caution += 1

    total = len(regimes)
    avg_conf = total_conf / total if total > 0 else 0

    # Determine overall bias
    if bullish > bearish * 1.5:
        bias = 'BULLISH'
        rec = 'Favor LONG positions'
    elif bearish > bullish * 1.5:
        bias = 'BEARISH'
        rec = 'Favor SHORT positions'
    elif caution > total * 0.3:
        bias = 'CAUTION'
        rec = 'Reduce exposure, high volatility detected'
    else:
        bias = 'NEUTRAL'
        rec = 'Mixed signals, wait for clarity'

    return {
        'overall_bias': bias,
        'confidence': round(avg_conf, 3),
        'bullish_count': bullish,
        'bearish_count': bearish,
        'neutral_count': neutral,
        'caution_count': caution,
        'recommendation': rec,
        'last_update': last_update
    }


# ========================================
# Dependency
# ========================================

async def get_regime_monitor(request: Request):
    """Dependency to get regime monitor from app state."""
    if hasattr(request.app.state, "regime_monitor"):
        return request.app.state.regime_monitor

    # Try to get from signal_processor
    if hasattr(request.app.state, "signal_processor"):
        sp = request.app.state.signal_processor
        if hasattr(sp, 'regime_monitor'):
            return sp.regime_monitor

    # Return None instead of raising - allows graceful degradation
    return None


# ========================================
# Endpoints
# ========================================

@router.get("/", response_model=Dict[str, RegimeState])
async def get_all_regimes(
    regime_monitor=Depends(get_regime_monitor)
) -> Dict[str, RegimeState]:
    """
    Get current regime state for all tracked symbols.

    Returns a dictionary mapping symbol to its current regime state.

    Data flow:
    - First tries local RegimeMonitor (when running in main.py)
    - Falls back to shared cache (when running standalone in web_server.py)
    """
    try:
        # Try local regime monitor first
        if regime_monitor:
            regimes = regime_monitor.get_current_regimes()
            if regimes:  # Has data
                return regimes

        # Fallback to shared cache (cross-service data from main.py)
        cached_regimes = await get_regimes_from_shared_cache()
        if cached_regimes:
            logger.debug("Serving regime data from shared cache")
            return cached_regimes

        # No data available - return empty dict (not an error)
        return {}

    except Exception as e:
        logger.error(f"Error getting regimes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=RegimeSummary)
async def get_regime_summary(
    regime_monitor=Depends(get_regime_monitor)
) -> RegimeSummary:
    """
    Get summary of current market regimes across all symbols.

    Useful for dashboard overview showing regime distribution.

    Data flow:
    - First tries local RegimeMonitor
    - Falls back to shared cache for cross-service data
    """
    try:
        regimes = None
        last_update = None

        # Try local regime monitor first
        if regime_monitor:
            regimes = regime_monitor.get_current_regimes()
            if regimes:
                stats = regime_monitor.get_stats()
                last_update = stats.get('last_update')

        # Fallback to shared cache if no local data
        if not regimes:
            cached_regimes = await get_regimes_from_shared_cache()
            if cached_regimes:
                regimes = cached_regimes
                # Try to get last_update from stats cache
                cached_stats = await get_stats_from_shared_cache()
                if cached_stats:
                    last_update = cached_stats.get('last_update')

        # Compute summary using helper function
        summary_data = compute_summary_from_regimes(regimes or {}, last_update)
        return RegimeSummary(**summary_data)

    except Exception as e:
        logger.error(f"Error getting regime summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes", response_model=List[RegimeChange])
async def get_recent_changes(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of changes"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    regime_monitor=Depends(get_regime_monitor)
) -> List[RegimeChange]:
    """
    Get recent regime changes.

    Returns a list of regime changes, most recent first.
    Used for the alerts dashboard.

    Data flow:
    - First tries local RegimeMonitor
    - Falls back to shared cache for cross-service data
    """
    try:
        changes = []

        # Try local regime monitor first
        if regime_monitor:
            changes = regime_monitor.get_recent_changes(limit=limit)

        # Fallback to shared cache if no local data
        if not changes:
            cached_changes = await get_changes_from_shared_cache()
            if cached_changes:
                changes = cached_changes[:limit]

        # Filter by symbol if specified
        if symbol and changes:
            changes = [c for c in changes if c['symbol'] == symbol.upper()]

        return changes

    except Exception as e:
        logger.error(f"Error getting regime changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol/{symbol}", response_model=RegimeState)
async def get_symbol_regime(
    symbol: str,
    regime_monitor=Depends(get_regime_monitor)
) -> RegimeState:
    """
    Get current regime for a specific symbol.

    Args:
        symbol: Trading symbol (e.g., BTCUSDT)

    Data flow:
    - First tries local RegimeMonitor
    - Falls back to shared cache for cross-service data
    """
    try:
        symbol = symbol.upper()
        regime = None

        # Try local regime monitor first
        if regime_monitor:
            regime = regime_monitor.get_regime_for_symbol(symbol)

        # Fallback to shared cache if no local data
        if not regime:
            cached_regimes = await get_regimes_from_shared_cache()
            if cached_regimes and symbol in cached_regimes:
                regime = cached_regimes[symbol]

        if not regime:
            raise HTTPException(status_code=404, detail=f"No regime data for {symbol}")

        return regime

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting regime for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol/{symbol}/history", response_model=List[Dict[str, Any]])
async def get_symbol_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum history entries"),
    regime_monitor=Depends(get_regime_monitor)
) -> List[Dict[str, Any]]:
    """
    Get regime history for a specific symbol.

    Returns historical regime states, most recent first.
    """
    if not regime_monitor:
        raise HTTPException(status_code=503, detail="Regime monitor not initialized")

    try:
        symbol = symbol.upper()
        history = regime_monitor.get_symbol_history(symbol, limit=limit)
        return history

    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=RegimeStats)
async def get_regime_stats(
    regime_monitor=Depends(get_regime_monitor)
) -> RegimeStats:
    """
    Get regime monitor statistics.

    Returns operational stats about the regime monitor.

    Data flow:
    - First tries local RegimeMonitor
    - Falls back to shared cache for cross-service data
    """
    try:
        stats = None

        # Try local regime monitor first
        if regime_monitor:
            stats = regime_monitor.get_stats()
            if stats.get('regimes_tracked', 0) > 0:
                return RegimeStats(**stats)

        # Fallback to shared cache
        cached_stats = await get_stats_from_shared_cache()
        if cached_stats:
            return RegimeStats(**cached_stats)

        # Return empty stats if nothing available
        return RegimeStats(
            regimes_tracked=0,
            changes_detected=0,
            alerts_sent=0,
            symbols_tracked=[],
            changes_in_memory=0,
            last_update=None
        )

    except Exception as e:
        logger.error(f"Error getting regime stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading-bias")
async def get_trading_bias(
    regime_monitor=Depends(get_regime_monitor)
) -> Dict[str, Any]:
    """
    Get aggregated trading bias based on current regimes.

    Returns overall market sentiment and recommended bias.
    Useful for dashboard market overview.

    Data flow:
    - First tries local RegimeMonitor
    - Falls back to shared cache for cross-service data
    """
    try:
        regimes = None
        last_update = None

        # Try local regime monitor first
        if regime_monitor:
            regimes = regime_monitor.get_current_regimes()
            if regimes:
                stats = regime_monitor.get_stats()
                last_update = stats.get('last_update')

        # Fallback to shared cache if no local data
        if not regimes:
            cached_regimes = await get_regimes_from_shared_cache()
            if cached_regimes:
                regimes = cached_regimes
                cached_stats = await get_stats_from_shared_cache()
                if cached_stats:
                    last_update = cached_stats.get('last_update')

        # Compute trading bias using helper function
        return compute_trading_bias_from_regimes(regimes or {}, last_update)

    except Exception as e:
        logger.error(f"Error calculating trading bias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/external-signals")
async def get_external_signals(
    regime_monitor=Depends(get_regime_monitor)
) -> Dict[str, Any]:
    """
    Get external market data signals used for regime enhancement.

    Returns aggregated data from:
    - crypto-perps-tracker: Derivatives sentiment (funding, basis, L/S ratio)
    - CoinGecko: Global market structure (dominance, market cap)
    - Alternative.me: Fear & Greed Index

    These signals are used to enhance regime detection accuracy by
    incorporating external market sentiment and structure data.
    """
    if not regime_monitor:
        raise HTTPException(status_code=503, detail="Regime monitor not initialized")

    try:
        # Trigger a fresh fetch if available
        if hasattr(regime_monitor, 'fetch_external_signals'):
            await regime_monitor.fetch_external_signals()

        # Get the summary
        if hasattr(regime_monitor, 'get_external_signals_summary'):
            return regime_monitor.get_external_signals_summary()

        return {
            'available': False,
            'message': 'External signals not available'
        }

    except Exception as e:
        logger.error(f"Error getting external signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
