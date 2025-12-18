"""
Signal Performance Tracking Module

Provides functions to update trading signal performance metrics including:
- Signal outcomes (win/loss/stopped_out)
- P&L calculations
- Excursion tracking (MFE/MAE)
- Pattern classification
- Validation cohort tagging
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, Literal
import json
import logging

logger = logging.getLogger(__name__)


class SignalPerformanceTracker:
    """
    Tracks and updates trading signal performance metrics.
    """

    def __init__(self, db_path: str):
        """
        Initialize tracker with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def open_signal(
        self,
        signal_id: str,
        confirmed_price: Optional[float] = None,
        signal_pattern: Optional[str] = None,
        divergence_type: Optional[str] = None,
        orderflow_tags: Optional[list] = None,
        is_validation_cohort: bool = False,
        orderflow_config: Optional[str] = None,
        trigger_component: Optional[str] = None,
    ) -> bool:
        """
        Mark signal as opened/active and set initial tracking metadata.

        Args:
            signal_id: Unique signal identifier
            confirmed_price: Price at which signal was confirmed
            signal_pattern: Pattern type ('divergence', 'confirmation', etc.)
            divergence_type: Specific divergence if applicable
            orderflow_tags: List of orderflow pattern tags
            is_validation_cohort: Whether signal is part of validation cohort
            orderflow_config: Orderflow multiplier config (e.g., '50_45')
            trigger_component: Component that triggered signal

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            updates = {
                "opened_at": datetime.utcnow().isoformat(),
                "status": "active",
            }

            if confirmed_price is not None:
                updates["confirmed_price"] = confirmed_price
            if signal_pattern:
                updates["signal_pattern"] = signal_pattern
            if divergence_type:
                updates["divergence_type"] = divergence_type
            if orderflow_tags:
                updates["orderflow_tags"] = json.dumps(orderflow_tags)
            if is_validation_cohort:
                updates["is_validation_cohort"] = 1
            if orderflow_config:
                updates["orderflow_config"] = orderflow_config
            if trigger_component:
                updates["trigger_component"] = trigger_component

            # Build UPDATE query
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [signal_id]

            cursor.execute(
                f"UPDATE trading_signals SET {set_clause} WHERE signal_id = ?",
                values,
            )

            conn.commit()
            conn.close()

            logger.info(f"Opened signal {signal_id} with pattern {signal_pattern}")
            return True

        except Exception as e:
            logger.error(f"Error opening signal {signal_id}: {e}")
            return False

    def close_signal(
        self,
        signal_id: str,
        exit_price: float,
        exit_reason: str,
        performance_notes: Optional[str] = None,
    ) -> bool:
        """
        Close signal and calculate final performance metrics.

        Args:
            signal_id: Unique signal identifier
            exit_price: Price at which signal was exited
            exit_reason: Reason for exit ('target_hit', 'stop_loss', etc.)
            performance_notes: Optional notes about performance

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get signal data
            cursor.execute(
                """
                SELECT signal_type, entry_price, stop_loss, opened_at, current_price
                FROM trading_signals
                WHERE signal_id = ?
                """,
                (signal_id,),
            )
            row = cursor.fetchone()

            if not row:
                logger.error(f"Signal {signal_id} not found")
                return False

            signal_type = row["signal_type"]
            entry_price = row["entry_price"] or row["current_price"]
            stop_loss = row["stop_loss"]
            opened_at = row["opened_at"]

            if not entry_price:
                logger.error(f"Signal {signal_id} has no entry price")
                return False

            # Calculate P&L
            pnl_pct = self._calculate_pnl_pct(signal_type, entry_price, exit_price)

            # Determine outcome
            outcome = self._determine_outcome(pnl_pct, exit_reason)

            # Calculate R-multiple if stop loss exists
            r_multiple = None
            if stop_loss:
                risk_pct = abs((stop_loss - entry_price) / entry_price * 100)
                if risk_pct > 0:
                    r_multiple = pnl_pct / risk_pct

            # Calculate duration
            closed_at = datetime.utcnow()
            duration_hours = None
            if opened_at:
                opened_dt = datetime.fromisoformat(opened_at)
                duration_hours = (closed_at - opened_dt).total_seconds() / 3600

            # Update signal
            cursor.execute(
                """
                UPDATE trading_signals
                SET
                    exit_price = ?,
                    closed_at = ?,
                    status = 'closed',
                    outcome = ?,
                    pnl_pct = ?,
                    r_multiple = ?,
                    duration_hours = ?,
                    exit_reason = ?,
                    performance_notes = ?
                WHERE signal_id = ?
                """,
                (
                    exit_price,
                    closed_at.isoformat(),
                    outcome,
                    pnl_pct,
                    r_multiple,
                    duration_hours,
                    exit_reason,
                    performance_notes,
                    signal_id,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(
                f"Closed signal {signal_id}: {outcome} with {pnl_pct:.2f}% P&L"
            )
            return True

        except Exception as e:
            logger.error(f"Error closing signal {signal_id}: {e}")
            return False

    def update_excursion(
        self,
        signal_id: str,
        current_price: float,
    ) -> bool:
        """
        Update maximum favorable/adverse excursion for active signal.

        Args:
            signal_id: Unique signal identifier
            current_price: Current market price

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get signal data
            cursor.execute(
                """
                SELECT signal_type, entry_price, mfe_pct, mae_pct, current_price
                FROM trading_signals
                WHERE signal_id = ? AND status = 'active'
                """,
                (signal_id,),
            )
            row = cursor.fetchone()

            if not row:
                return False

            signal_type = row["signal_type"]
            entry_price = row["entry_price"] or row["current_price"]
            current_mfe = row["mfe_pct"] or 0
            current_mae = row["mae_pct"] or 0

            if not entry_price:
                return False

            # Calculate current excursion
            if signal_type == "LONG":
                excursion_pct = (current_price - entry_price) / entry_price * 100
            else:  # SHORT
                excursion_pct = (entry_price - current_price) / entry_price * 100

            # Update if new extreme reached
            updates = {}
            now = datetime.utcnow().isoformat()

            if excursion_pct > current_mfe:
                updates["mfe_pct"] = excursion_pct
                updates["mfe_price"] = current_price
                updates["mfe_at"] = now

            if excursion_pct < current_mae:
                updates["mae_pct"] = excursion_pct
                updates["mae_price"] = current_price
                updates["mae_at"] = now

            if updates:
                set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                values = list(updates.values()) + [signal_id]
                cursor.execute(
                    f"UPDATE trading_signals SET {set_clause} WHERE signal_id = ?",
                    values,
                )
                conn.commit()

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error updating excursion for {signal_id}: {e}")
            return False

    @staticmethod
    def _calculate_pnl_pct(signal_type: str, entry_price: float, exit_price: float) -> float:
        """
        Calculate P&L percentage based on signal direction.

        Args:
            signal_type: 'LONG' or 'SHORT'
            entry_price: Entry price
            exit_price: Exit price

        Returns:
            P&L percentage
        """
        if signal_type == "LONG":
            return ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            return ((entry_price - exit_price) / entry_price) * 100

    @staticmethod
    def _determine_outcome(
        pnl_pct: float,
        exit_reason: str,
    ) -> Literal["win", "loss", "stopped_out", "expired"]:
        """
        Determine signal outcome based on P&L and exit reason.

        Args:
            pnl_pct: P&L percentage
            exit_reason: Reason for exit

        Returns:
            Outcome string
        """
        if exit_reason == "stop_loss":
            return "stopped_out"
        elif exit_reason in ["time_exit", "expired"]:
            return "expired"
        elif pnl_pct > 0:
            return "win"
        else:
            return "loss"

    def classify_signal_pattern(
        self,
        signal_id: str,
        components: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        """
        Classify signal pattern based on component scores.

        Args:
            signal_id: Signal identifier
            components: Component scores dictionary

        Returns:
            Dictionary with pattern classification or None
        """
        try:
            # Extract orderflow metrics
            orderflow_score = components.get("orderflow", {}).get("score", 50)
            technical_score = components.get("technical", {}).get("score", 50)
            volume_score = components.get("volume", {}).get("score", 50)

            pattern_info = {}

            # Detect divergence patterns
            # Divergence: orderflow contradicts price/technical
            if abs(orderflow_score - technical_score) > 20:
                if orderflow_score > 60 and technical_score < 40:
                    pattern_info["signal_pattern"] = "divergence"
                    pattern_info["divergence_type"] = "bullish_divergence"
                elif orderflow_score < 40 and technical_score > 60:
                    pattern_info["signal_pattern"] = "divergence"
                    pattern_info["divergence_type"] = "bearish_divergence"
            # Confirmation: all components aligned
            elif all(
                abs(score - orderflow_score) < 15
                for score in [technical_score, volume_score]
                if score is not None
            ):
                pattern_info["signal_pattern"] = "confirmation"
            # Momentum: strong directional scores
            elif orderflow_score > 70 or orderflow_score < 30:
                pattern_info["signal_pattern"] = "momentum"
            else:
                pattern_info["signal_pattern"] = "other"

            # Extract orderflow tags
            orderflow_tags = []
            orderflow_data = components.get("orderflow", {})

            if orderflow_data.get("buyer_aggression", 0) > 0.7:
                orderflow_tags.append("high_buyer_aggression")
            if orderflow_data.get("seller_aggression", 0) > 0.7:
                orderflow_tags.append("high_seller_aggression")
            if orderflow_data.get("absorption_detected", False):
                orderflow_tags.append("absorption")
            if orderflow_data.get("large_orders", False):
                orderflow_tags.append("large_orders")

            if orderflow_tags:
                pattern_info["orderflow_tags"] = orderflow_tags

            return pattern_info

        except Exception as e:
            logger.error(f"Error classifying pattern for {signal_id}: {e}")
            return None

    def get_performance_summary(
        self,
        signal_type: Optional[str] = None,
        signal_pattern: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get performance summary statistics.

        Args:
            signal_type: Filter by LONG/SHORT (optional)
            signal_pattern: Filter by pattern type (optional)
            days: Number of days to look back

        Returns:
            Dictionary with performance metrics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Build query
            where_clauses = [
                "status = 'closed'",
                "outcome IN ('win', 'loss', 'stopped_out')",
                f"created_at > datetime('now', '-{days} days')",
            ]

            if signal_type:
                where_clauses.append(f"signal_type = '{signal_type}'")
            if signal_pattern:
                where_clauses.append(f"signal_pattern = '{signal_pattern}'")

            where_sql = " AND ".join(where_clauses)

            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_signals,
                    COUNT(*) FILTER (WHERE outcome = 'win') as wins,
                    COUNT(*) FILTER (WHERE outcome = 'loss') as losses,
                    COUNT(*) FILTER (WHERE outcome = 'stopped_out') as stopped_out,
                    AVG(pnl_pct) as avg_pnl,
                    AVG(CASE WHEN outcome = 'win' THEN pnl_pct END) as avg_win,
                    AVG(CASE WHEN outcome = 'loss' THEN pnl_pct END) as avg_loss,
                    AVG(r_multiple) as avg_r_multiple,
                    AVG(duration_hours) as avg_duration_hours,
                    MAX(pnl_pct) as max_win,
                    MIN(pnl_pct) as min_loss,
                    AVG(mfe_pct) as avg_mfe,
                    AVG(mae_pct) as avg_mae
                FROM trading_signals
                WHERE {where_sql}
                """
            )

            row = cursor.fetchone()
            conn.close()

            if row["total_signals"] == 0:
                return {"message": "No closed signals found"}

            win_rate = (row["wins"] / row["total_signals"]) * 100 if row["wins"] else 0
            profit_factor = (
                abs(row["avg_win"] * row["wins"] / (row["avg_loss"] * row["losses"]))
                if row["losses"] and row["avg_loss"]
                else None
            )

            return {
                "total_signals": row["total_signals"],
                "wins": row["wins"],
                "losses": row["losses"],
                "stopped_out": row["stopped_out"],
                "win_rate": round(win_rate, 2),
                "avg_pnl_pct": round(row["avg_pnl"], 2) if row["avg_pnl"] else None,
                "avg_win_pct": round(row["avg_win"], 2) if row["avg_win"] else None,
                "avg_loss_pct": round(row["avg_loss"], 2) if row["avg_loss"] else None,
                "profit_factor": round(profit_factor, 2) if profit_factor else None,
                "avg_r_multiple": round(row["avg_r_multiple"], 2)
                if row["avg_r_multiple"]
                else None,
                "avg_duration_hours": round(row["avg_duration_hours"], 2)
                if row["avg_duration_hours"]
                else None,
                "max_win_pct": round(row["max_win"], 2) if row["max_win"] else None,
                "min_loss_pct": round(row["min_loss"], 2) if row["min_loss"] else None,
                "avg_mfe_pct": round(row["avg_mfe"], 2) if row["avg_mfe"] else None,
                "avg_mae_pct": round(row["avg_mae"], 2) if row["avg_mae"] else None,
            }

        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def get_tracker(db_path: str = "data/virtuoso.db") -> SignalPerformanceTracker:
    """
    Get a SignalPerformanceTracker instance.

    Args:
        db_path: Path to database file

    Returns:
        SignalPerformanceTracker instance
    """
    return SignalPerformanceTracker(db_path)


def tag_validation_cohort(
    db_path: str,
    orderflow_config: str = "50_45",
    start_date: str = "2025-12-09",
) -> int:
    """
    Tag signals as part of validation cohort.

    Args:
        db_path: Path to database file
        orderflow_config: Orderflow multiplier config
        start_date: Start date for cohort (YYYY-MM-DD)

    Returns:
        Number of signals tagged
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE trading_signals
            SET
                is_validation_cohort = 1,
                orderflow_config = ?
            WHERE created_at >= ?
            """,
            (orderflow_config, start_date),
        )

        count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Tagged {count} signals as validation cohort")
        return count

    except Exception as e:
        logger.error(f"Error tagging validation cohort: {e}")
        return 0
