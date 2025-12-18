"""
API routes for signal performance tracking and validation
"""
from fastapi import APIRouter, Query
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/performance/summary")
async def get_performance_summary(
    days: int = Query(7, description="Number of days to look back"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (LONG/SHORT)")
):
    """Get signal performance summary for validation dashboard"""
    try:
        from src.database.signal_performance import get_tracker
        
        tracker = get_tracker()
        summary = tracker.get_performance_summary(
            days=days,
            signal_type=signal_type
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error fetching performance summary: {e}")
        return {
            "error": str(e),
            "win_rate": 0.0,
            "closed_signals": 0,
            "total_signals": 0,
            "avg_pnl_pct": 0.0
        }

@router.get("/performance/by-pattern")
async def get_performance_by_pattern(
    days: int = Query(30, description="Number of days to look back")
):
    """Get performance breakdown by signal pattern"""
    try:
        from src.database.signal_performance import get_tracker
        
        tracker = get_tracker()
        
        # Get performance for each pattern type
        divergence_perf = tracker.get_performance_summary(
            days=days,
            signal_pattern="divergence"
        )
        
        confirmation_perf = tracker.get_performance_summary(
            days=days,
            signal_pattern="confirmation"
        )
        
        return {
            "by_pattern": {
                "divergence": divergence_perf,
                "confirmation": confirmation_perf
            },
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Error fetching pattern performance: {e}")
        return {
            "error": str(e),
            "by_pattern": {}
        }

@router.get("/active")
async def get_active_signals():
    """Get currently active (open) signals"""
    try:
        from src.database.signal_performance import get_tracker
        
        tracker = get_tracker()
        conn = tracker._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                signal_id,
                symbol,
                signal_type,
                confluence_score,
                entry_price,
                stop_loss,
                timestamp as signal_time,
                signal_pattern,
                mfe,
                mae
            FROM trading_signals
            WHERE status = 'open' OR status IS NULL
            ORDER BY timestamp DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        conn.close()
        
        signals = [dict(zip(columns, row)) for row in results]
        
        return {
            "signals": signals,
            "count": len(signals),
            "timestamp": int(time.time() * 1000),
            "source": "database"
        }
        
    except Exception as e:
        logger.error(f"Error fetching active signals: {e}")
        return {
            "signals": [],
            "count": 0,
            "timestamp": int(time.time() * 1000),
            "source": "disabled",
            "message": str(e)
        }

@router.get("/latest")
async def get_latest_signals(
    limit: int = Query(10, description="Number of recent signals to return")
):
    """Get most recent signals (both open and closed)"""
    try:
        from src.database.signal_performance import get_tracker
        import time
        
        tracker = get_tracker()
        conn = tracker._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                signal_id,
                symbol,
                signal_type,
                status,
                confluence_score,
                entry_price,
                exit_price,
                stop_loss,
                timestamp as signal_time,
                exit_time,
                signal_pattern,
                pnl_pct,
                outcome,
                mfe,
                mae
            FROM trading_signals
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        conn.close()
        
        signals = [dict(zip(columns, row)) for row in results]
        
        return {
            "signals": signals,
            "count": len(signals),
            "timestamp": int(time.time() * 1000)
        }
        
    except Exception as e:
        logger.error(f"Error fetching latest signals: {e}")
        return {
            "signals": [],
            "count": 0,
            "timestamp": int(time.time() * 1000),
            "error": str(e)
        }

@router.post("/close")
async def close_signal(
    signal_id: int,
    exit_price: float,
    exit_reason: str = "manual",
    performance_notes: Optional[str] = None
):
    """Manually close a signal with exit data"""
    try:
        from src.database.signal_performance import get_tracker
        
        tracker = get_tracker()
        success = tracker.close_signal(
            signal_id=signal_id,
            exit_price=exit_price,
            exit_reason=exit_reason,
            performance_notes=performance_notes
        )
        
        if success:
            return {
                "success": True,
                "message": f"Signal {signal_id} closed successfully",
                "signal_id": signal_id
            }
        else:
            return {
                "success": False,
                "error": "Failed to close signal",
                "signal_id": signal_id
            }
            
    except Exception as e:
        logger.error(f"Error closing signal: {e}")
        return {
            "success": False,
            "error": str(e),
            "signal_id": signal_id
        }
