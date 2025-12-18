"""
Perpetuals Pulse Charts API Routes

Provides chart generation endpoints for the perpetuals pulse dashboard card.

Author: Virtuoso Team
Version: 1.0.0
Created: 2025-12-11
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime, timezone, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

# Import chart generation functions
try:
    from src.core.chart.perpetuals_pulse_charts import (
        create_funding_rate_microtrend,
        create_long_short_gauge,
        create_signal_strength_dashboard,
        create_market_state_composite,
        create_all_charts,
        charts_to_html
    )
    CHARTS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Chart library not available: {e}")
    CHARTS_AVAILABLE = False

# Import database for funding history
try:
    from src.data_storage.database import get_db_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.warning("Database not available for funding history")


async def fetch_funding_history(hours: int = 4) -> list:
    """
    Fetch funding rate history from database.

    Args:
        hours: Number of hours of history to fetch

    Returns:
        List of {timestamp, funding_rate, exchange} dicts
    """
    if not DB_AVAILABLE:
        return []

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Query database (adapt to your schema)
        # This is a placeholder - adjust to match your actual database schema
        query = """
            SELECT timestamp, funding_rate, exchange
            FROM funding_history
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """

        # Execute query (adapt to your connection method)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (cutoff.isoformat(),))
        rows = cursor.fetchall()
        conn.close()

        # Convert to list of dicts
        history = []
        for row in rows:
            history.append({
                'timestamp': row[0],
                'funding_rate': float(row[1]),
                'exchange': row[2]
            })

        logger.info(f"Fetched {len(history)} funding rate records")
        return history

    except Exception as e:
        logger.error(f"Error fetching funding history: {e}")
        return []


@router.get("/perpetuals-charts/all")
async def get_all_charts(lookback_hours: int = 4) -> Dict[str, Any]:
    """
    Generate all perpetuals pulse charts.

    Args:
        lookback_hours: Hours of funding history to display

    Returns:
        JSON with chart HTML for each visualization
    """
    if not CHARTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Chart generation service unavailable"
        )

    try:
        # Fetch current data from perpetuals-pulse endpoint
        # In production, you'd call the actual endpoint or service
        from src.api.routes.dashboard import get_perpetuals_pulse

        current_data = await get_perpetuals_pulse()

        if current_data.get('status') == 'error':
            logger.warning("Perpetuals pulse data unavailable")
            return {
                "status": "error",
                "error": "Current data unavailable",
                "charts": {}
            }

        # Fetch funding history
        funding_history = await fetch_funding_history(lookback_hours)

        # Generate all charts
        charts = create_all_charts(current_data, funding_history)

        # Convert to HTML
        html_charts = charts_to_html(charts)

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "charts": html_charts,
            "data_summary": {
                "funding_rate": current_data.get('funding_rate', 0),
                "long_pct": current_data.get('long_pct', 50),
                "signal_count": current_data.get('signal_count', 0),
                "data_quality": current_data.get('data_quality_score', 0)
            }
        }

    except Exception as e:
        logger.error(f"Error generating charts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chart generation error: {str(e)}"
        )


@router.get("/perpetuals-charts/funding-microtrend")
async def get_funding_microtrend(lookback_hours: int = 4) -> Dict[str, Any]:
    """Generate funding rate micro-trend chart only."""
    if not CHARTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chart service unavailable")

    try:
        from src.api.routes.dashboard import get_perpetuals_pulse

        current_data = await get_perpetuals_pulse()
        if current_data.get('status') == 'error':
            raise HTTPException(status_code=503, detail="Data unavailable")

        funding_history = await fetch_funding_history(lookback_hours)

        fig = create_funding_rate_microtrend(funding_history, current_data, lookback_hours)

        return {
            "status": "success",
            "html": fig.to_html(include_plotlyjs=False, div_id="funding-microtrend"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating funding microtrend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/perpetuals-charts/long-short-gauge")
async def get_long_short_gauge() -> Dict[str, Any]:
    """Generate long/short positioning gauge chart only."""
    if not CHARTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chart service unavailable")

    try:
        from src.api.routes.dashboard import get_perpetuals_pulse

        current_data = await get_perpetuals_pulse()
        if current_data.get('status') == 'error':
            raise HTTPException(status_code=503, detail="Data unavailable")

        fig = create_long_short_gauge(current_data)

        return {
            "status": "success",
            "html": fig.to_html(include_plotlyjs=False, div_id="long-short-gauge"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating long/short gauge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/perpetuals-charts/signal-strength")
async def get_signal_strength() -> Dict[str, Any]:
    """Generate signal strength dashboard chart only."""
    if not CHARTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chart service unavailable")

    try:
        from src.api.routes.dashboard import get_perpetuals_pulse

        current_data = await get_perpetuals_pulse()
        if current_data.get('status') == 'error':
            raise HTTPException(status_code=503, detail="Data unavailable")

        fig = create_signal_strength_dashboard(current_data)

        return {
            "status": "success",
            "html": fig.to_html(include_plotlyjs=False, div_id="signal-strength"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating signal strength: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/perpetuals-charts/market-state")
async def get_market_state() -> Dict[str, Any]:
    """Generate market state composite chart only."""
    if not CHARTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chart service unavailable")

    try:
        from src.api.routes.dashboard import get_perpetuals_pulse

        current_data = await get_perpetuals_pulse()
        if current_data.get('status') == 'error':
            raise HTTPException(status_code=503, detail="Data unavailable")

        fig = create_market_state_composite(current_data)

        return {
            "status": "success",
            "html": fig.to_html(include_plotlyjs=False, div_id="market-state"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating market state: {e}")
        raise HTTPException(status_code=500, detail=str(e))
