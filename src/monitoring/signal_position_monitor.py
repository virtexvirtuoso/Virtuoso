"""
Signal Position Monitor

Monitors active trading signals and tracks price excursions (MFE/MAE) for performance analysis.
This service runs periodically to update excursion metrics for all open signals.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback

from src.database.signal_performance import SignalPerformanceTracker

logger = logging.getLogger(__name__)


class SignalPositionMonitor:
    """
    Monitors active signals and updates excursion metrics.

    This class:
    - Fetches active signals from database
    - Gets current prices for each symbol
    - Updates MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse Excursion)
    - Optionally triggers auto-close on stop loss or take profit hits
    """

    def __init__(
        self,
        db_path: str = "data/virtuoso.db",
        market_data_manager=None,
        auto_close_enabled: bool = False,
        update_interval: int = 60
    ):
        """
        Initialize position monitor.

        Args:
            db_path: Path to database
            market_data_manager: Manager for fetching current prices
            auto_close_enabled: Whether to automatically close signals on TP/SL hits
            update_interval: How often to update excursions (seconds)
        """
        self.db_path = db_path
        self.market_data_manager = market_data_manager
        self.auto_close_enabled = auto_close_enabled
        self.update_interval = update_interval
        self.tracker = SignalPerformanceTracker(db_path)
        self.running = False
        self.monitor_task = None

    async def start(self):
        """Start the position monitoring loop."""
        if self.running:
            logger.warning("Position monitor already running")
            return

        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Signal position monitor started (update interval: {self.update_interval}s)")

    async def stop(self):
        """Stop the position monitoring loop."""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Signal position monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop that runs continuously."""
        while self.running:
            try:
                await self.update_all_positions()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in position monitor loop: {e}")
                logger.debug(traceback.format_exc())
                await asyncio.sleep(self.update_interval)

    async def update_all_positions(self):
        """Update excursions for all active signals."""
        try:
            # Get all active signals from database
            active_signals = self._get_active_signals()

            if not active_signals:
                logger.debug("No active signals to monitor")
                return

            logger.info(f"Monitoring {len(active_signals)} active signals")

            # Update each signal
            for signal in active_signals:
                try:
                    await self._update_signal_position(signal)
                except Exception as e:
                    logger.error(f"Error updating signal {signal['signal_id']}: {e}")

        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            logger.debug(traceback.format_exc())

    async def _update_signal_position(self, signal: Dict[str, Any]):
        """
        Update excursion for a single signal.

        Args:
            signal: Signal data from database
        """
        signal_id = signal['signal_id']
        symbol = signal['symbol']

        try:
            # Get current price
            current_price = await self._get_current_price(symbol)

            if current_price is None:
                logger.warning(f"Could not get price for {symbol}, skipping excursion update")
                return

            # Update excursion in database
            success = self.tracker.update_excursion(signal_id, current_price)

            if success:
                logger.debug(f"Updated excursion for {signal_id}: price={current_price}")
            else:
                logger.warning(f"Failed to update excursion for {signal_id}")

            # Check for auto-close conditions if enabled
            if self.auto_close_enabled:
                await self._check_auto_close(signal, current_price)

        except Exception as e:
            logger.error(f"Error updating signal {signal_id}: {e}")
            logger.debug(traceback.format_exc())

    async def _check_auto_close(self, signal: Dict[str, Any], current_price: float):
        """
        Check if signal should be auto-closed (hit stop loss or take profit).

        Args:
            signal: Signal data
            current_price: Current market price
        """
        signal_id = signal['signal_id']
        signal_type = signal['signal_type']
        entry_price = signal.get('entry_price') or signal.get('current_price')
        stop_loss = signal.get('stop_loss')

        # Parse targets JSON if available
        targets = signal.get('targets')
        if isinstance(targets, str):
            import json
            try:
                targets = json.loads(targets)
            except:
                targets = None

        # Check stop loss
        if stop_loss:
            if signal_type == 'LONG' and current_price <= stop_loss:
                logger.info(f"LONG signal {signal_id} hit stop loss at {current_price}")
                self.tracker.close_signal(
                    signal_id=signal_id,
                    exit_price=current_price,
                    exit_reason='stop_loss',
                    performance_notes='Auto-closed on stop loss hit'
                )
                return

            elif signal_type == 'SHORT' and current_price >= stop_loss:
                logger.info(f"SHORT signal {signal_id} hit stop loss at {current_price}")
                self.tracker.close_signal(
                    signal_id=signal_id,
                    exit_price=current_price,
                    exit_reason='stop_loss',
                    performance_notes='Auto-closed on stop loss hit'
                )
                return

        # Check take profit targets (use first target as TP)
        if targets and isinstance(targets, list) and len(targets) > 0:
            first_target = targets[0]
            if isinstance(first_target, dict):
                target_price = first_target.get('price')

                if target_price:
                    if signal_type == 'LONG' and current_price >= target_price:
                        logger.info(f"LONG signal {signal_id} hit take profit at {current_price}")
                        self.tracker.close_signal(
                            signal_id=signal_id,
                            exit_price=current_price,
                            exit_reason='target_hit',
                            performance_notes=f'Auto-closed on {first_target.get("name", "Target 1")} hit'
                        )
                        return

                    elif signal_type == 'SHORT' and current_price <= target_price:
                        logger.info(f"SHORT signal {signal_id} hit take profit at {current_price}")
                        self.tracker.close_signal(
                            signal_id=signal_id,
                            exit_price=current_price,
                            exit_reason='target_hit',
                            performance_notes=f'Auto-closed on {first_target.get("name", "Target 1")} hit'
                        )
                        return

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current price or None if unavailable
        """
        try:
            if self.market_data_manager:
                # Try to get from market data manager
                market_data = await self.market_data_manager.get_market_data(symbol)
                if market_data and 'ticker' in market_data:
                    ticker = market_data['ticker']
                    price = ticker.get('last') or ticker.get('close')
                    if price:
                        return float(price)

            # Fallback: could add direct exchange API call here
            logger.warning(f"No market data manager available for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def _get_active_signals(self) -> List[Dict[str, Any]]:
        """
        Get all active signals from database.

        Returns:
            List of active signal dictionaries
        """
        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM trading_signals
                WHERE status = 'active'
                ORDER BY created_at DESC
                """
            )

            rows = cursor.fetchall()
            signals = [dict(row) for row in rows]
            conn.close()

            return signals

        except Exception as e:
            logger.error(f"Error fetching active signals: {e}")
            return []

    def close_signal_manually(
        self,
        signal_id: str,
        exit_price: float,
        exit_reason: str = 'manual',
        notes: Optional[str] = None
    ) -> bool:
        """
        Manually close a signal.

        Args:
            signal_id: Signal to close
            exit_price: Exit price
            exit_reason: Reason for exit
            notes: Optional performance notes

        Returns:
            True if successful
        """
        try:
            success = self.tracker.close_signal(
                signal_id=signal_id,
                exit_price=exit_price,
                exit_reason=exit_reason,
                performance_notes=notes
            )

            if success:
                logger.info(f"Manually closed signal {signal_id} at {exit_price}")
            return success

        except Exception as e:
            logger.error(f"Error manually closing signal {signal_id}: {e}")
            return False

    async def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get current monitoring statistics.

        Returns:
            Dictionary with monitoring stats
        """
        try:
            active_signals = self._get_active_signals()

            return {
                'active_signals': len(active_signals),
                'monitoring_enabled': self.running,
                'auto_close_enabled': self.auto_close_enabled,
                'update_interval': self.update_interval,
                'signals': [
                    {
                        'signal_id': s['signal_id'],
                        'symbol': s['symbol'],
                        'type': s['signal_type'],
                        'entry_price': s.get('entry_price'),
                        'mfe_pct': s.get('mfe_pct'),
                        'mae_pct': s.get('mae_pct'),
                        'opened_at': s.get('opened_at')
                    }
                    for s in active_signals
                ]
            }

        except Exception as e:
            logger.error(f"Error getting monitoring stats: {e}")
            return {
                'error': str(e),
                'active_signals': 0,
                'monitoring_enabled': self.running
            }
