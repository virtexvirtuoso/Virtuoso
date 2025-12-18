"""
Multi-Timeframe (MTF) Altcoin Ranking API Routes

Provides endpoints for ranking altcoins based on their performance
vs Bitcoin across multiple timeframes.

Endpoints:
    GET /api/altcoins/mtf-ranking - Get ranked altcoins
    GET /api/altcoins/top-performers - High-consistency performers
    GET /api/altcoins/divergence-plays - Strongest divergence from BTC
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging

from ...core.analysis.mtf_beta_ranker import MTFBetaRanker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/altcoins", tags=["MTF Altcoin Ranking"])


@router.get("/mtf-ranking")
async def get_mtf_ranking(
    cluster: str = Query(
        "day_trading",
        description="Timeframe cluster preset",
        regex="^(scalping|day_trading|swing_trading|comprehensive)$"
    ),
    top_n: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of top-ranked altcoins to return"
    ),
    min_score: float = Query(
        0.0,
        ge=0.0,
        le=100.0,
        description="Minimum MTF score threshold (0-100)"
    ),
    exclude: Optional[str] = Query(
        None,
        description="Comma-separated list of symbols to exclude"
    )
):
    """
    Get ranked list of altcoins based on multi-timeframe beta performance.

    **Timeframe Clusters:**
    - `scalping`: 15m, 30m, 1h (3 timeframes)
    - `day_trading`: 1h, 4h, 8h (3 timeframes, recommended)
    - `swing_trading`: 8h, 12h, 24h (3 timeframes)
    - `comprehensive`: 15m, 30m, 1h, 4h, 8h, 12h, 24h (ALL 7 timeframes)

    **Response includes:**
    - MTF score (0-100)
    - Trading signal (STRONG_BUY, BUY, WEAK_BUY, etc.)
    - Total outperformance vs BTC (%)
    - Consistency ratio (% of timeframes aligned)
    - Volatility metric
    - Per-timeframe performance breakdown

    **Example:**
    ```
    GET /api/altcoins/mtf-ranking?cluster=day_trading&top_n=10&min_score=70
    ```
    """
    try:
        # Parse excluded symbols
        exclude_symbols = None
        if exclude:
            exclude_symbols = [s.strip().upper() for s in exclude.split(',')]

        # Initialize ranker with selected cluster
        ranker = MTFBetaRanker(cluster=cluster)

        # Get rankings
        results = await ranker.rank_altcoins(
            top_n=top_n,
            min_score=min_score,
            exclude_symbols=exclude_symbols
        )

        return {
            "status": "success",
            "data": results,
            "cluster": cluster,
            "filters": {
                "top_n": top_n,
                "min_score": min_score,
                "exclude": exclude_symbols
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in mtf_ranking endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/top-performers")
async def get_top_performers(
    cluster: str = Query(
        "day_trading",
        regex="^(scalping|day_trading|swing_trading|comprehensive)$"
    ),
    top_n: int = Query(5, ge=1, le=20),
    min_consistency: float = Query(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum consistency ratio (0-1)"
    )
):
    """
    Get top performing altcoins with high timeframe consistency.

    This endpoint filters for coins where most/all timeframes agree
    on direction, providing higher-confidence trade opportunities.

    **Parameters:**
    - `min_consistency`: Minimum % of timeframes that must align (default: 0.8 = 80%)

    **Example:**
    ```
    GET /api/altcoins/top-performers?cluster=day_trading&min_consistency=0.8
    ```

    Returns only coins where ≥80% of timeframes show the same direction.
    """
    try:
        ranker = MTFBetaRanker(cluster=cluster)

        top_performers = await ranker.get_top_performers(
            top_n=top_n,
            min_consistency=min_consistency
        )

        return {
            "status": "success",
            "data": top_performers,
            "cluster": cluster,
            "filters": {
                "top_n": top_n,
                "min_consistency": min_consistency
            }
        }

    except Exception as e:
        logger.error(f"Error in top_performers endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/divergence-plays")
async def get_divergence_plays(
    cluster: str = Query(
        "day_trading",
        regex="^(scalping|day_trading|swing_trading|comprehensive)$"
    ),
    top_n: int = Query(5, ge=1, le=20),
    min_divergence: float = Query(
        5.0,
        ge=0.0,
        description="Minimum total outperformance/underperformance (%)"
    )
):
    """
    Get altcoins with strongest performance divergence from Bitcoin.

    Useful for identifying relative strength/weakness trades where
    altcoins are significantly outperforming or underperforming BTC.

    **Parameters:**
    - `min_divergence`: Minimum cumulative divergence across timeframes (%)

    **Example:**
    ```
    GET /api/altcoins/divergence-plays?cluster=swing_trading&min_divergence=10
    ```

    Returns coins with ≥10% total divergence from BTC performance.
    """
    try:
        ranker = MTFBetaRanker(cluster=cluster)

        divergence_plays = await ranker.get_divergence_plays(
            min_divergence=min_divergence,
            top_n=top_n
        )

        return {
            "status": "success",
            "data": divergence_plays,
            "cluster": cluster,
            "filters": {
                "top_n": top_n,
                "min_divergence": min_divergence
            }
        }

    except Exception as e:
        logger.error(f"Error in divergence_plays endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeframe-clusters")
async def get_timeframe_clusters():
    """
    Get available timeframe cluster configurations.

    Returns all preset clusters with their timeframe compositions
    and recommended use cases.

    **Example:**
    ```
    GET /api/altcoins/timeframe-clusters
    ```
    """
    clusters = {
        "scalping": {
            "timeframes": [0.25, 0.5, 1],
            "timeframes_display": ["15m", "30m", "1h"],
            "description": "High-frequency trading, 1-30 minute holds",
            "typical_win_rate": "65-70%",
            "recommended_for": "Active traders with sub-minute execution"
        },
        "day_trading": {
            "timeframes": [1, 4, 8],
            "timeframes_display": ["1h", "4h", "8h"],
            "description": "Intraday momentum, 2-12 hour holds",
            "typical_win_rate": "60-65%",
            "recommended_for": "Most traders (default)"
        },
        "swing_trading": {
            "timeframes": [8, 12, 24],
            "timeframes_display": ["8h", "12h", "24h"],
            "description": "Multi-day trends, 3-14 day holds",
            "typical_win_rate": "55-60%",
            "recommended_for": "Position traders, less screen time"
        },
        "comprehensive": {
            "timeframes": [0.25, 0.5, 1, 4, 8, 12, 24],
            "timeframes_display": ["15m", "30m", "1h", "4h", "8h", "12h", "24h"],
            "description": "ALL 7 timeframes for maximum confluence",
            "typical_win_rate": "60-70%",
            "recommended_for": "High-conviction trades, maximum signal strength"
        }
    }

    return {
        "status": "success",
        "clusters": clusters
    }
