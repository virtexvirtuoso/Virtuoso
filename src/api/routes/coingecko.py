"""
CoinGecko Extended API Routes
=============================

Provides API endpoints for extended CoinGecko data:
- Trending coins and NFTs
- Derivatives (funding rates, open interest)
- Category/sector performance
- Exchange volume distribution

See: docs/08-features/COINGECKO_INTEGRATION_ROADMAP.md
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coingecko", tags=["coingecko"])


async def _get_from_cache(request: Request, key: str) -> Optional[Dict[str, Any]]:
    """Helper to get data from cache via shared cache bridge.

    Uses the same shared_cache pattern that other web server routes use,
    ensuring we can read data written by the trading service.
    """
    try:
        # Use shared cache bridge (same pattern as other web server routes)
        if hasattr(request.app.state, 'shared_cache') and request.app.state.shared_cache:
            data, is_cross_service = await request.app.state.shared_cache.get_shared_data(key)
            if data:
                if isinstance(data, str):
                    return json.loads(data)
                return data

        return None
    except Exception as e:
        logger.warning(f"Cache read error for {key}: {e}")
        return None


@router.get("/trending")
async def get_trending_coins(request: Request) -> Dict[str, Any]:
    """
    Get trending coins from CoinGecko.

    Returns top 7 trending coins and top 3 trending NFTs.
    Data updates every ~15 minutes.

    Trading Value: Early signal detection for momentum plays.
    Coins appearing on trending often see 10-30% pumps within 24-48 hours.
    """
    data = await _get_from_cache(request, "coingecko:trending")

    if not data:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Data not available",
                "message": "Trending data not yet cached. Please try again in a few minutes.",
                "cache_key": "coingecko:trending"
            }
        )

    return {
        "status": "success",
        "data": data,
        "cache_key": "coingecko:trending"
    }


@router.get("/derivatives")
async def get_derivatives_data(request: Request) -> Dict[str, Any]:
    """
    Get derivatives (perpetual futures) data from CoinGecko.

    Returns:
    - Top contracts by open interest
    - Cross-exchange funding rate comparisons
    - Funding rate spreads for arbitrage detection
    - Total open interest

    Trading Value: Cross-exchange funding rate arbitrage detection.
    """
    data = await _get_from_cache(request, "coingecko:derivatives")

    if not data:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Data not available",
                "message": "Derivatives data not yet cached. Please try again in a few minutes.",
                "cache_key": "coingecko:derivatives"
            }
        )

    return {
        "status": "success",
        "data": data,
        "cache_key": "coingecko:derivatives"
    }


@router.get("/derivatives/funding-spreads")
async def get_funding_spreads(request: Request) -> Dict[str, Any]:
    """
    Get funding rate spreads for arbitrage opportunities.

    Returns symbols with the highest cross-exchange funding rate spreads.
    Higher spreads indicate potential arbitrage opportunities.
    """
    data = await _get_from_cache(request, "coingecko:derivatives")

    if not data or not data.get('funding_spreads'):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Data not available",
                "message": "Funding spread data not yet cached."
            }
        )

    # Sort by spread magnitude
    spreads = data.get('funding_spreads', {})
    sorted_spreads = dict(sorted(
        spreads.items(),
        key=lambda x: x[1].get('spread_bps', 0),
        reverse=True
    ))

    return {
        "status": "success",
        "data": {
            "spreads": sorted_spreads,
            "total_open_interest": data.get('total_open_interest', 0),
            "updated_at": data.get('updated_at')
        },
        "description": "Funding rate spreads in basis points. Higher = more arbitrage opportunity."
    }


@router.get("/categories")
async def get_category_performance(request: Request) -> Dict[str, Any]:
    """
    Get category (sector) performance from CoinGecko.

    Returns:
    - All tracked categories with market cap and 24h change
    - Top 3 and bottom 3 performing sectors
    - Sector rotation signal

    Trading Value: Sector rotation signals for identifying capital flow.
    """
    data = await _get_from_cache(request, "coingecko:categories")

    if not data:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Data not available",
                "message": "Category data not yet cached. Please try again in a few minutes.",
                "cache_key": "coingecko:categories"
            }
        )

    return {
        "status": "success",
        "data": data,
        "cache_key": "coingecko:categories"
    }


@router.get("/categories/rotation-signal")
async def get_rotation_signal(request: Request) -> Dict[str, Any]:
    """
    Get current sector rotation signal.

    Signals:
    - RISK_ON: Meme coins leading - high risk appetite
    - DEFI_ROTATION: Capital flowing to DeFi
    - AI_NARRATIVE: AI tokens outperforming
    - RISK_OFF: L1s declining - defensive positioning
    - NEUTRAL: No clear rotation signal
    """
    data = await _get_from_cache(request, "coingecko:categories")

    if not data:
        raise HTTPException(
            status_code=503,
            detail={"error": "Data not available"}
        )

    return {
        "status": "success",
        "data": {
            "signal": data.get('rotation_signal', 'NEUTRAL: No data'),
            "top_performers": data.get('top_performers', []),
            "bottom_performers": data.get('bottom_performers', []),
            "updated_at": data.get('updated_at')
        }
    }


@router.get("/exchanges")
async def get_exchange_distribution(request: Request) -> Dict[str, Any]:
    """
    Get exchange volume distribution from CoinGecko.

    Returns:
    - Top 20 exchanges by volume with trust scores
    - Total 24h volume in BTC
    - Market concentration metrics (Top 3/5 share, Herfindahl index)

    Trading Value: Liquidity concentration analysis for execution optimization.
    """
    data = await _get_from_cache(request, "coingecko:exchanges")

    if not data:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Data not available",
                "message": "Exchange data not yet cached. Please try again in a few minutes.",
                "cache_key": "coingecko:exchanges"
            }
        )

    return {
        "status": "success",
        "data": data,
        "cache_key": "coingecko:exchanges"
    }


@router.get("/exchanges/concentration")
async def get_exchange_concentration(request: Request) -> Dict[str, Any]:
    """
    Get exchange market concentration metrics.

    Returns:
    - Top 3 exchange market share %
    - Top 5 exchange market share %
    - Herfindahl-Hirschman Index (HHI) for concentration

    Higher HHI = more concentrated market (less decentralized).
    """
    data = await _get_from_cache(request, "coingecko:exchanges")

    if not data or not data.get('concentration'):
        raise HTTPException(
            status_code=503,
            detail={"error": "Data not available"}
        )

    return {
        "status": "success",
        "data": {
            "concentration": data.get('concentration', {}),
            "total_volume_btc": data.get('total_volume_btc', 0),
            "top_exchanges": data.get('exchanges', [])[:5],
            "updated_at": data.get('updated_at')
        },
        "description": "HHI > 2500 indicates highly concentrated market"
    }


@router.get("/cycle-phase")
async def get_market_cycle_phase(request: Request) -> Dict[str, Any]:
    """
    Get market cycle phase derived from CoinGecko category performance.

    Phases (BTC Dom → Infra → Alt → Spec → Peak):
    - ACCUMULATION: Stablecoins leading, risk-off positioning
    - BTC_DOMINANCE: BTC/major L1s leading, early bull
    - INFRASTRUCTURE: DeFi/L2s leading, capital building
    - ALT_SEASON: Mid-caps outperforming, risk appetite rising
    - SPECULATION: Meme/GameFi leading, late cycle euphoria

    Trading Value: Identifies current market cycle position for risk management.
    """
    data = await _get_from_cache(request, "coingecko:categories")

    if not data:
        raise HTTPException(
            status_code=503,
            detail={"error": "Category data not available"}
        )

    top_performers = data.get('top_performers', [])
    bottom_performers = data.get('bottom_performers', [])
    rotation_signal = data.get('rotation_signal', '')

    # Derive market cycle phase from category performance
    phase = "UNKNOWN"
    phase_score = 50  # 0-100, where 0=BTC Dom, 100=Peak Speculation
    risk_level = "MODERATE"
    confidence = 0.5

    # Define category groups for phase detection
    stablecoin_keywords = ['stablecoin', 'usd', 'fiat']
    btc_keywords = ['bitcoin', 'layer 1', 'layer-1', 'smart contract']
    infra_keywords = ['defi', 'layer 2', 'layer-2', 'exchange', 'oracle', 'infrastructure']
    alt_keywords = ['gaming', 'metaverse', 'nft', 'social', 'storage']
    spec_keywords = ['meme', 'dog', 'cat', 'pepe', 'shib']

    def matches_keywords(performers: list, keywords: list) -> bool:
        """Check if any performer matches keywords."""
        for performer in performers[:3]:  # Check top 3
            performer_lower = performer.lower()
            for kw in keywords:
                if kw in performer_lower:
                    return True
        return False

    # Determine phase based on what's leading
    if matches_keywords(top_performers, stablecoin_keywords):
        phase = "ACCUMULATION"
        phase_score = 10
        risk_level = "LOW"
        confidence = 0.7
    elif matches_keywords(top_performers, spec_keywords):
        phase = "SPECULATION"
        phase_score = 90
        risk_level = "EXTREME"
        confidence = 0.8
    elif matches_keywords(top_performers, alt_keywords):
        phase = "ALT_SEASON"
        phase_score = 70
        risk_level = "HIGH"
        confidence = 0.6
    elif matches_keywords(top_performers, infra_keywords):
        phase = "INFRASTRUCTURE"
        phase_score = 50
        risk_level = "MODERATE"
        confidence = 0.6
    elif matches_keywords(top_performers, btc_keywords):
        phase = "BTC_DOMINANCE"
        phase_score = 30
        risk_level = "LOW"
        confidence = 0.7
    else:
        # Use rotation signal as fallback
        if 'RISK_OFF' in rotation_signal.upper():
            phase = "ACCUMULATION"
            phase_score = 15
            risk_level = "LOW"
            confidence = 0.5
        elif 'RISK_ON' in rotation_signal.upper():
            phase = "ALT_SEASON"
            phase_score = 65
            risk_level = "MODERATE"
            confidence = 0.5
        else:
            phase = "TRANSITION"
            phase_score = 50
            risk_level = "MODERATE"
            confidence = 0.4

    # Check bottom performers for confirmation
    if matches_keywords(bottom_performers, spec_keywords):
        # Meme coins at bottom = early cycle confirmation
        if phase in ["ACCUMULATION", "BTC_DOMINANCE"]:
            confidence = min(confidence + 0.15, 0.9)
    elif matches_keywords(bottom_performers, stablecoin_keywords):
        # Stablecoins at bottom = late cycle confirmation
        if phase in ["SPECULATION", "ALT_SEASON"]:
            confidence = min(confidence + 0.15, 0.9)

    return {
        "status": "success",
        "data": {
            "phase": {
                "name": phase,
                "risk_level": risk_level
            },
            "phase_score": phase_score,
            "confidence": confidence,
            "indicators": {
                "speculative_ratio": phase_score / 50,  # Normalized 0-2 scale
                "top_sectors": top_performers[:3],
                "bottom_sectors": bottom_performers[:3]
            },
            "rotation_signal": rotation_signal,
            "description": _get_phase_description(phase),
            "updated_at": data.get('updated_at')
        }
    }


def _get_phase_description(phase: str) -> str:
    """Get human-readable description for each market phase."""
    descriptions = {
        "ACCUMULATION": "Risk-off positioning. Capital parked in stablecoins. Smart money accumulating.",
        "BTC_DOMINANCE": "Bitcoin leading. Early bull market. Alts underperforming BTC.",
        "INFRASTRUCTURE": "Capital flowing to DeFi/L2s. Building phase before alt season.",
        "ALT_SEASON": "Mid-caps outperforming. Risk appetite increasing. Late-stage bull.",
        "SPECULATION": "Meme coins leading. Euphoric phase. High risk of reversal.",
        "TRANSITION": "No clear phase. Market in transition between cycles.",
        "UNKNOWN": "Insufficient data to determine phase."
    }
    return descriptions.get(phase, "Unknown phase")


@router.get("/summary")
async def get_coingecko_summary(request: Request) -> Dict[str, Any]:
    """
    Get summary of all CoinGecko extended data.

    Combines trending, derivatives, categories, and exchanges into a single response.
    Useful for dashboard widgets that need multiple data points.
    """
    # Fetch all data concurrently
    trending = await _get_from_cache(request, "coingecko:trending")
    derivatives = await _get_from_cache(request, "coingecko:derivatives")
    categories = await _get_from_cache(request, "coingecko:categories")
    exchanges = await _get_from_cache(request, "coingecko:exchanges")

    return {
        "status": "success",
        "data": {
            "trending": {
                "available": trending is not None,
                "top_coins": [c.get('symbol') for c in (trending or {}).get('coins', [])[:5]],
                "updated_at": (trending or {}).get('updated_at')
            },
            "derivatives": {
                "available": derivatives is not None,
                "total_open_interest": (derivatives or {}).get('total_open_interest', 0),
                "arb_opportunities": len((derivatives or {}).get('funding_spreads', {})),
                "updated_at": (derivatives or {}).get('updated_at')
            },
            "categories": {
                "available": categories is not None,
                "rotation_signal": (categories or {}).get('rotation_signal', 'N/A'),
                "top_performers": (categories or {}).get('top_performers', [])[:3],
                "updated_at": (categories or {}).get('updated_at')
            },
            "exchanges": {
                "available": exchanges is not None,
                "total_volume_btc": (exchanges or {}).get('total_volume_btc', 0),
                "top_3_share": (exchanges or {}).get('concentration', {}).get('top_3_share', 0),
                "updated_at": (exchanges or {}).get('updated_at')
            }
        }
    }
