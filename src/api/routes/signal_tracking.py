"""
Signal Tracking API Routes

Provides API endpoints for managing signal performance tracking including:
- Closing signals manually
- Viewing active signals
- Getting performance summaries
- Monitoring signal positions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging

from src.database.signal_performance import SignalPerformanceTracker, get_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signal_tracking"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CloseSignalRequest(BaseModel):
    """Request body for manually closing a signal."""
    signal_id: str = Field(..., description="Signal ID to close")
    exit_price: float = Field(..., description="Exit price")
    exit_reason: str = Field(
        default="manual",
        description="Reason for exit (manual, stop_loss, target_hit, timeout)"
    )
    notes: Optional[str] = Field(None, description="Optional performance notes")


class SignalCloseResponse(BaseModel):
    """Response after closing a signal."""
    success: bool
    signal_id: str
    message: str
    outcome: Optional[str] = None
    pnl_pct: Optional[float] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/close", response_model=SignalCloseResponse)
async def close_signal(request: CloseSignalRequest):
    """
    Manually close an active signal and calculate performance.

    This endpoint allows manual signal closure with P&L calculation.
    Use this when:
    - Manually exiting a position
    - Stopping out a signal
    - Taking profit on a signal
    - Timing out a signal

    Returns performance metrics including outcome and P&L percentage.
    """
    try:
        tracker = get_tracker()

        success = tracker.close_signal(
            signal_id=request.signal_id,
            exit_price=request.exit_price,
            exit_reason=request.exit_reason,
            performance_notes=request.notes
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Signal {request.signal_id} not found or already closed"
            )

        # Get the updated signal to return outcome/pnl
        import sqlite3
        conn = sqlite3.connect("data/virtuoso.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT outcome, pnl_pct FROM trading_signals WHERE signal_id = ?",
            (request.signal_id,)
        )
        row = cursor.fetchone()
        conn.close()

        outcome = row['outcome'] if row else None
        pnl_pct = row['pnl_pct'] if row else None

        return SignalCloseResponse(
            success=True,
            signal_id=request.signal_id,
            message=f"Signal closed successfully with {outcome}",
            outcome=outcome,
            pnl_pct=pnl_pct
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_signals():
    """
    Get all currently active signals being monitored.

    Returns:
        List of active signals with current excursion data
    """
    try:
        import sqlite3

        conn = sqlite3.connect("data/virtuoso.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                signal_id,
                symbol,
                signal_type,
                confluence_score,
                entry_price,
                stop_loss,
                current_price,
                opened_at,
                mfe_pct,
                mae_pct,
                signal_pattern,
                divergence_type
            FROM trading_signals
            WHERE status = 'active'
            ORDER BY opened_at DESC
            """
        )

        rows = cursor.fetchall()
        signals = [dict(row) for row in rows]
        conn.close()

        return {
            "active_signals": len(signals),
            "signals": signals
        }

    except Exception as e:
        logger.error(f"Error fetching active signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/summary")
async def get_performance_summary(
    signal_type: Optional[str] = Query(None, description="Filter by LONG/SHORT"),
    signal_pattern: Optional[str] = Query(None, description="Filter by pattern type"),
    days: int = Query(7, description="Number of days to analyze", ge=1, le=365)
):
    """
    Get performance summary statistics.

    Analyzes closed signals and returns:
    - Win rate
    - Average P&L
    - Average winner/loser
    - Profit factor
    - Average R-multiple
    - Average duration
    - Max win/loss
    - Average MFE/MAE

    Filters:
    - signal_type: LONG or SHORT
    - signal_pattern: divergence, confirmation, momentum, other
    - days: Lookback period
    """
    try:
        tracker = get_tracker()

        summary = tracker.get_performance_summary(
            signal_type=signal_type,
            signal_pattern=signal_pattern,
            days=days
        )

        return summary

    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/by-pattern")
async def get_performance_by_pattern(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """
    Get performance breakdown by signal pattern.

    Returns win rate, avg P&L, and other metrics grouped by:
    - divergence
    - confirmation
    - momentum
    - other
    """
    try:
        tracker = get_tracker()

        patterns = ['divergence', 'confirmation', 'momentum', 'other']
        results = {}

        for pattern in patterns:
            summary = tracker.get_performance_summary(
                signal_pattern=pattern,
                days=days
            )
            results[pattern] = summary

        return {
            "analysis_period_days": days,
            "by_pattern": results
        }

    except Exception as e:
        logger.error(f"Error getting performance by pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signal/{signal_id}")
async def get_signal_details(signal_id: str):
    """
    Get detailed information about a specific signal including performance data.
    """
    try:
        import sqlite3

        conn = sqlite3.connect("data/virtuoso.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM trading_signals WHERE signal_id = ?",
            (signal_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Signal {signal_id} not found"
            )

        signal = dict(row)

        # Parse JSON fields
        import json
        for field in ['targets', 'components', 'orderflow_tags']:
            if signal.get(field):
                try:
                    signal[field] = json.loads(signal[field])
                except:
                    pass

        return signal

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching signal details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/start")
async def start_position_monitor():
    """
    Start the automatic position monitoring service.

    This will periodically update excursions for all active signals.
    """
    try:
        # Import here to avoid circular imports
        from src.monitoring.signal_position_monitor import SignalPositionMonitor

        # This would need to be managed by the main application
        # For now, return instructions
        return {
            "message": "Position monitor should be started via main.py integration",
            "instructions": "Add SignalPositionMonitor to main.py startup sequence"
        }

    except Exception as e:
        logger.error(f"Error starting position monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/status")
async def get_monitor_status():
    """
    Get current status of the position monitoring service.
    """
    try:
        # This would check if monitor is running
        # For now, return placeholder
        return {
            "monitoring_enabled": False,
            "message": "Position monitoring not yet integrated into main loop",
            "integration_required": True
        }

    except Exception as e:
        logger.error(f"Error getting monitor status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
