"""
Kill Switch Module for Orderflow Multiplier Reversion

This module monitors SHORT signal performance and automatically reverts
orderflow multipliers to legacy values if performance falls below thresholds.

CRITICAL SAFETY MECHANISM:
- Monitors SHORT signal win rate over 7-day rolling window
- Triggers if win_rate < 35% AND closed_count >= 20
- Reverts CVD multiplier: 50 → 35
- Reverts OI multiplier: 45 → 30
- Sends critical alerts to Discord/email
- Logs all state changes for audit trail
- Idempotent: safe to activate multiple times

Author: Claude (Backend Architect)
Date: 2025-12-11
"""

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import json
import os
import yaml

logger = logging.getLogger(__name__)


class KillSwitchState:
    """Kill switch activation states."""
    ACTIVE = "active"          # Legacy multipliers in use
    INACTIVE = "inactive"      # New multipliers in use
    MONITORING = "monitoring"  # Checking performance


class OrderflowKillSwitch:
    """
    Monitors SHORT signal performance and reverts orderflow multipliers
    if performance degrades below acceptable thresholds.

    Design Principles:
    - Fail-safe: Errors don't crash the system
    - Idempotent: Can activate multiple times safely
    - Auditable: Logs every check and activation
    - Reversible: Manual override to re-enable new multipliers
    - Testable: Easy to unit test without database dependencies
    """

    # Thresholds
    MIN_WIN_RATE = 0.35  # 35%
    MIN_CLOSED_SIGNALS = 20
    LOOKBACK_DAYS = 7

    # Legacy multipliers (safe values)
    LEGACY_CVD_MULTIPLIER = 35.0
    LEGACY_OI_MULTIPLIER = 30.0

    # New multipliers (experimental values)
    NEW_CVD_MULTIPLIER = 50.0
    NEW_OI_MULTIPLIER = 45.0

    def __init__(self, config: Dict[str, Any], db_path: Optional[str] = None):
        """
        Initialize kill switch.

        Args:
            config: System configuration dictionary
            db_path: Path to virtuoso.db (defaults to data/virtuoso.db)
        """
        self.config = config
        self.db_path = db_path or self._get_default_db_path()
        self.logger = logging.getLogger(__name__)

        # Initialize state from config or database
        self._state = self._load_state()

        # Track last check time to avoid spamming checks
        self._last_check_time: Optional[datetime] = None
        self._check_interval_seconds = 300  # Check every 5 minutes max

    def _get_default_db_path(self) -> str:
        """Get default database path."""
        return os.path.join(os.getcwd(), 'data', 'virtuoso.db')

    def _load_state(self) -> str:
        """
        Load kill switch state from database.

        Returns:
            Current kill switch state (active/inactive/monitoring)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kill_switch_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    state TEXT NOT NULL,
                    activated_at TEXT,
                    reason TEXT,
                    win_rate REAL,
                    closed_count INTEGER,
                    updated_at TEXT NOT NULL
                )
            ''')

            # Get current state
            cursor.execute('SELECT state FROM kill_switch_state WHERE id = 1')
            row = cursor.fetchone()

            if row:
                state = row[0]
            else:
                # Initialize to monitoring state
                state = KillSwitchState.MONITORING
                cursor.execute('''
                    INSERT INTO kill_switch_state (id, state, updated_at)
                    VALUES (1, ?, ?)
                ''', (state, datetime.now(timezone.utc).isoformat()))
                conn.commit()

            conn.close()
            self.logger.info(f"Kill switch state loaded: {state}")
            return state

        except Exception as e:
            self.logger.error(f"Error loading kill switch state: {e}")
            # Default to monitoring if we can't load state
            return KillSwitchState.MONITORING

    def _save_state(
        self,
        state: str,
        reason: Optional[str] = None,
        win_rate: Optional[float] = None,
        closed_count: Optional[int] = None
    ) -> None:
        """
        Save kill switch state to database.

        Args:
            state: New state to save
            reason: Reason for state change
            win_rate: Current win rate (if applicable)
            closed_count: Number of closed signals (if applicable)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc).isoformat()
            activated_at = now if state == KillSwitchState.ACTIVE else None

            cursor.execute('''
                UPDATE kill_switch_state
                SET state = ?, activated_at = ?, reason = ?,
                    win_rate = ?, closed_count = ?, updated_at = ?
                WHERE id = 1
            ''', (state, activated_at, reason, win_rate, closed_count, now))

            conn.commit()
            conn.close()

            self.logger.info(
                f"Kill switch state saved: {state} | "
                f"Reason: {reason} | Win Rate: {win_rate} | Closed: {closed_count}"
            )

        except Exception as e:
            self.logger.error(f"Error saving kill switch state: {e}")

    def get_short_performance(self) -> Tuple[float, int, int]:
        """
        Query SHORT signal performance from database.

        Returns:
            Tuple of (win_rate, closed_count, total_count)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate timestamp for 7 days ago
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.LOOKBACK_DAYS)
            cutoff_timestamp_ms = int(cutoff_time.timestamp() * 1000)

            # Query SHORT signals from last 7 days that are closed
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) as closed,
                    SUM(CASE
                        WHEN closed_at IS NOT NULL AND outcome = 'win' THEN 1
                        ELSE 0
                    END) as wins
                FROM trading_signals
                WHERE signal_type = 'SHORT'
                  AND timestamp >= ?
            ''', (cutoff_timestamp_ms,))

            row = cursor.fetchone()
            conn.close()

            if row:
                total, closed, wins = row
                closed = closed or 0
                wins = wins or 0

                win_rate = (wins / closed) if closed > 0 else 0.0

                self.logger.debug(
                    f"SHORT performance: win_rate={win_rate:.2%}, "
                    f"closed={closed}, total={total}"
                )

                return win_rate, closed, total
            else:
                self.logger.warning("No SHORT signals found in database")
                return 0.0, 0, 0

        except Exception as e:
            self.logger.error(f"Error querying SHORT performance: {e}")
            # Return safe defaults on error
            return 0.0, 0, 0

    def should_trigger(self) -> Tuple[bool, Optional[str]]:
        """
        Check if kill switch should trigger based on performance.

        Returns:
            Tuple of (should_trigger, reason)
        """
        # Don't check if already active
        if self._state == KillSwitchState.ACTIVE:
            return False, "Kill switch already active"

        # Rate limit checks to avoid database spam
        if self._last_check_time:
            time_since_check = (datetime.now(timezone.utc) - self._last_check_time).total_seconds()
            if time_since_check < self._check_interval_seconds:
                return False, f"Check throttled (last check {time_since_check:.0f}s ago)"

        self._last_check_time = datetime.now(timezone.utc)

        # Get SHORT signal performance
        win_rate, closed_count, total_count = self.get_short_performance()

        # Check thresholds
        if closed_count < self.MIN_CLOSED_SIGNALS:
            reason = (
                f"Insufficient data: {closed_count} closed signals "
                f"(need {self.MIN_CLOSED_SIGNALS})"
            )
            self.logger.debug(reason)
            return False, reason

        if win_rate < self.MIN_WIN_RATE:
            reason = (
                f"Poor performance: {win_rate:.2%} win rate "
                f"(threshold: {self.MIN_WIN_RATE:.0%}), "
                f"{closed_count} closed signals over {self.LOOKBACK_DAYS} days"
            )
            self.logger.warning(f"KILL SWITCH TRIGGER: {reason}")
            return True, reason

        # Performance is acceptable
        reason = f"Performance OK: {win_rate:.2%} win rate, {closed_count} closed signals"
        self.logger.debug(reason)
        return False, reason

    def activate(self) -> bool:
        """
        Activate kill switch: revert to legacy multipliers.

        This method is idempotent - safe to call multiple times.

        Returns:
            True if activation successful, False otherwise
        """
        try:
            # Check if we should trigger
            should_activate, reason = self.should_trigger()

            if not should_activate:
                self.logger.debug(f"Kill switch activation skipped: {reason}")
                return False

            # Update state
            self._state = KillSwitchState.ACTIVE

            # Get performance metrics for logging
            win_rate, closed_count, _ = self.get_short_performance()

            # Save state to database
            self._save_state(
                state=KillSwitchState.ACTIVE,
                reason=reason,
                win_rate=win_rate,
                closed_count=closed_count
            )

            # Update configuration file
            self._update_config_file(use_new_multipliers=False)

            # Send critical alert
            self._send_alert(
                title="KILL SWITCH ACTIVATED",
                message=reason,
                win_rate=win_rate,
                closed_count=closed_count
            )

            self.logger.critical(
                f"KILL SWITCH ACTIVATED: Reverted to legacy multipliers. {reason}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error activating kill switch: {e}", exc_info=True)
            return False

    def deactivate(self, manual_override: bool = True) -> bool:
        """
        Deactivate kill switch: re-enable new multipliers.

        This should only be called manually after investigating the issue.

        Args:
            manual_override: Set to True to bypass safety checks

        Returns:
            True if deactivation successful, False otherwise
        """
        try:
            if not manual_override:
                self.logger.error(
                    "Kill switch deactivation requires manual_override=True "
                    "to prevent accidental re-enabling"
                )
                return False

            # Update state
            self._state = KillSwitchState.MONITORING

            # Save state to database
            self._save_state(
                state=KillSwitchState.MONITORING,
                reason="Manual override - re-enabled new multipliers"
            )

            # Update configuration file
            self._update_config_file(use_new_multipliers=True)

            # Send alert
            self._send_alert(
                title="Kill Switch Deactivated (Manual Override)",
                message="New orderflow multipliers re-enabled by manual override",
                win_rate=None,
                closed_count=None
            )

            self.logger.warning(
                "Kill switch deactivated by manual override - "
                "new multipliers re-enabled"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error deactivating kill switch: {e}", exc_info=True)
            return False

    def _update_config_file(self, use_new_multipliers: bool) -> None:
        """
        Update config.yaml with appropriate multiplier values.

        Args:
            use_new_multipliers: If True, use new multipliers; else use legacy
        """
        try:
            config_path = Path(os.getcwd()) / 'config' / 'config.yaml'

            if not config_path.exists():
                self.logger.error(f"Config file not found: {config_path}")
                return

            # Load current config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Update multipliers in config
            if 'analysis' not in config:
                config['analysis'] = {}
            if 'indicators' not in config['analysis']:
                config['analysis']['indicators'] = {}
            if 'orderflow' not in config['analysis']['indicators']:
                config['analysis']['indicators']['orderflow'] = {}

            orderflow_config = config['analysis']['indicators']['orderflow']

            if use_new_multipliers:
                orderflow_config['use_symmetric_divergence'] = True
                cvd_multiplier = self.NEW_CVD_MULTIPLIER
                oi_multiplier = self.NEW_OI_MULTIPLIER
            else:
                orderflow_config['use_symmetric_divergence'] = False
                cvd_multiplier = self.LEGACY_CVD_MULTIPLIER
                oi_multiplier = self.LEGACY_OI_MULTIPLIER

            # Add comment to config
            orderflow_config['_kill_switch_note'] = (
                f"Multipliers managed by kill switch. "
                f"Current: CVD={cvd_multiplier}, OI={oi_multiplier}"
            )

            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            self.logger.info(
                f"Config updated: use_new_multipliers={use_new_multipliers}, "
                f"CVD={cvd_multiplier}, OI={oi_multiplier}"
            )

        except Exception as e:
            self.logger.error(f"Error updating config file: {e}", exc_info=True)

    def _send_alert(
        self,
        title: str,
        message: str,
        win_rate: Optional[float] = None,
        closed_count: Optional[int] = None
    ) -> None:
        """
        Send alert notification via Discord/email.

        Args:
            title: Alert title
            message: Alert message
            win_rate: Current win rate (optional)
            closed_count: Number of closed signals (optional)
        """
        try:
            # Import alert manager
            from src.monitoring.alert_manager import alert_manager

            # Build details
            details = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'kill_switch_state': self._state,
                'message': message
            }

            if win_rate is not None:
                details['win_rate'] = f"{win_rate:.2%}"
            if closed_count is not None:
                details['closed_signals'] = closed_count

            # Send critical alert
            alert_manager.send_critical_alert(
                title=title,
                message=message,
                details=details
            )

            self.logger.info(f"Kill switch alert sent: {title}")

        except Exception as e:
            self.logger.error(f"Error sending kill switch alert: {e}", exc_info=True)
            # Don't fail if alert fails - just log it

    def get_status(self) -> Dict[str, Any]:
        """
        Get current kill switch status.

        Returns:
            Dictionary with current status information
        """
        try:
            win_rate, closed_count, total_count = self.get_short_performance()

            return {
                'state': self._state,
                'is_active': self._state == KillSwitchState.ACTIVE,
                'last_check_time': self._last_check_time.isoformat() if self._last_check_time else None,
                'performance': {
                    'win_rate': win_rate,
                    'closed_count': closed_count,
                    'total_count': total_count,
                    'lookback_days': self.LOOKBACK_DAYS
                },
                'thresholds': {
                    'min_win_rate': self.MIN_WIN_RATE,
                    'min_closed_signals': self.MIN_CLOSED_SIGNALS
                },
                'multipliers': {
                    'legacy': {
                        'cvd': self.LEGACY_CVD_MULTIPLIER,
                        'oi': self.LEGACY_OI_MULTIPLIER
                    },
                    'new': {
                        'cvd': self.NEW_CVD_MULTIPLIER,
                        'oi': self.NEW_OI_MULTIPLIER
                    },
                    'current_mode': 'legacy' if self._state == KillSwitchState.ACTIVE else 'new'
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting kill switch status: {e}")
            return {
                'state': 'error',
                'error': str(e)
            }

    def check_and_activate_if_needed(self) -> bool:
        """
        Main entry point: check performance and activate if needed.

        This is the method that should be called from the main loop.

        Returns:
            True if kill switch was activated, False otherwise
        """
        try:
            should_activate, reason = self.should_trigger()

            if should_activate:
                return self.activate()
            else:
                self.logger.debug(f"Kill switch check passed: {reason}")
                return False

        except Exception as e:
            self.logger.error(f"Error in kill switch check: {e}", exc_info=True)
            # Fail-safe: don't crash the system on kill switch errors
            return False


# Singleton instance for easy access
_kill_switch_instance: Optional[OrderflowKillSwitch] = None


def get_kill_switch(config: Optional[Dict[str, Any]] = None) -> OrderflowKillSwitch:
    """
    Get or create kill switch singleton instance.

    Args:
        config: System configuration (only used on first call)

    Returns:
        OrderflowKillSwitch instance
    """
    global _kill_switch_instance

    if _kill_switch_instance is None:
        if config is None:
            raise ValueError("Config required for first kill switch initialization")
        _kill_switch_instance = OrderflowKillSwitch(config)

    return _kill_switch_instance
