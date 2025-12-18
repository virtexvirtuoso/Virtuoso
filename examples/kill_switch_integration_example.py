"""
Example: Kill Switch Integration

Demonstrates how to integrate the orderflow kill switch into
the main trading loop or monitoring system.

This is a reference implementation - adapt to your specific architecture.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from src.core.risk import get_kill_switch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingSystem:
    """Example trading system with kill switch integration."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trading system.

        Args:
            config: System configuration dictionary
        """
        self.config = config
        self.kill_switch = get_kill_switch(config)
        self.running = False

        logger.info("Trading system initialized with kill switch")

    async def generate_signals(self) -> list:
        """
        Generate trading signals.

        This is where your actual signal generation logic goes.
        The kill switch automatically adjusts multipliers in config.

        Returns:
            List of generated signals
        """
        # Placeholder for signal generation
        # Your actual implementation here
        logger.info("Generating trading signals...")
        await asyncio.sleep(1)  # Simulate work
        return []

    async def run(self):
        """Main trading loop with kill switch integration."""
        self.running = True
        logger.info("Starting trading system main loop")

        iteration = 0

        while self.running:
            try:
                iteration += 1
                logger.info(f"=== Iteration {iteration} ===")

                # CRITICAL: Check kill switch BEFORE generating signals
                kill_switch_triggered = self.kill_switch.check_and_activate_if_needed()

                if kill_switch_triggered:
                    logger.critical(
                        "⚠️  KILL SWITCH ACTIVATED - Reverted to legacy multipliers! ⚠️"
                    )
                    # Optionally: pause trading, send alerts, etc.
                    # The kill switch already sends alerts and updates config

                # Generate signals (uses current multipliers from config)
                signals = await self.generate_signals()

                logger.info(f"Generated {len(signals)} signals")

                # Process signals
                # ... your signal processing logic ...

                # Sleep before next iteration
                await asyncio.sleep(60)  # Check every 60 seconds

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt - shutting down")
                self.running = False
                break

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Brief pause on error

        logger.info("Trading system stopped")

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down trading system")
        self.running = False


class MonitoringSystem:
    """Example monitoring system with periodic kill switch checks."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize monitoring system.

        Args:
            config: System configuration dictionary
        """
        self.config = config
        self.kill_switch = get_kill_switch(config)
        self.running = False

        logger.info("Monitoring system initialized")

    async def check_kill_switch(self):
        """Periodic kill switch check."""
        while self.running:
            try:
                logger.info("Running kill switch check...")

                # Get current status
                status = self.kill_switch.get_status()

                logger.info(f"Kill switch state: {status['state']}")
                logger.info(
                    f"SHORT performance: {status['performance']['win_rate']:.1%} "
                    f"win rate, {status['performance']['closed_count']} closed signals"
                )

                # Check and activate if needed
                self.kill_switch.check_and_activate_if_needed()

                # Wait 5 minutes before next check
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in kill switch check: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def run(self):
        """Run monitoring system."""
        self.running = True
        logger.info("Starting monitoring system")

        # Run kill switch check as background task
        kill_switch_task = asyncio.create_task(self.check_kill_switch())

        # Wait for shutdown signal
        try:
            await kill_switch_task
        except asyncio.CancelledError:
            logger.info("Monitoring tasks cancelled")

        logger.info("Monitoring system stopped")

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down monitoring system")
        self.running = False


def example_manual_operations():
    """Example manual kill switch operations."""
    from src.core.risk import OrderflowKillSwitch

    config = {}  # Your config here
    kill_switch = OrderflowKillSwitch(config)

    # Check current status
    print("\n=== Kill Switch Status ===")
    status = kill_switch.get_status()
    print(f"State: {status['state']}")
    print(f"Active: {status['is_active']}")
    print(f"Win Rate: {status['performance']['win_rate']:.1%}")
    print(f"Closed Signals: {status['performance']['closed_count']}")
    print(f"Current Multipliers: {status['multipliers']['current_mode']}")

    # Check if should trigger
    print("\n=== Trigger Check ===")
    should_trigger, reason = kill_switch.should_trigger()
    print(f"Should Trigger: {should_trigger}")
    print(f"Reason: {reason}")

    # Manual activation (if needed)
    if input("\nManually activate kill switch? (y/n): ").lower() == 'y':
        success = kill_switch.activate()
        if success:
            print("✓ Kill switch activated")
        else:
            print("✗ Kill switch activation failed")

    # Manual deactivation (if needed)
    if input("\nManually deactivate kill switch? (y/n): ").lower() == 'y':
        success = kill_switch.deactivate(manual_override=True)
        if success:
            print("✓ Kill switch deactivated")
        else:
            print("✗ Kill switch deactivation failed")


def example_signal_closing():
    """Example of closing a signal and recording outcome."""
    import sqlite3
    from datetime import datetime, timezone

    def close_signal(signal_id: str, outcome: str, close_price: float):
        """
        Close a signal and record outcome for kill switch monitoring.

        Args:
            signal_id: Signal identifier
            outcome: 'win', 'loss', or 'breakeven'
            close_price: Price at which signal was closed
        """
        db_path = 'data/virtuoso.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get entry price
        cursor.execute(
            'SELECT entry_price, signal_type FROM trading_signals WHERE signal_id = ?',
            (signal_id,)
        )
        row = cursor.fetchone()

        if not row:
            logger.error(f"Signal {signal_id} not found")
            conn.close()
            return

        entry_price, signal_type = row

        # Calculate PnL
        if signal_type == 'SHORT':
            pnl_percentage = ((entry_price - close_price) / entry_price) * 100
        else:  # LONG
            pnl_percentage = ((close_price - entry_price) / entry_price) * 100

        # Update signal
        cursor.execute('''
            UPDATE trading_signals
            SET closed_at = ?, outcome = ?, close_price = ?, pnl_percentage = ?
            WHERE signal_id = ?
        ''', (
            datetime.now(timezone.utc).isoformat(),
            outcome,
            close_price,
            pnl_percentage,
            signal_id
        ))

        conn.commit()
        conn.close()

        logger.info(
            f"Closed signal {signal_id}: {outcome} "
            f"(PnL: {pnl_percentage:+.2f}%)"
        )

    # Example usage
    print("\n=== Example Signal Closing ===")
    print("close_signal('btcusdt_short_75p0_20251211_143000', 'win', 49500.0)")
    print("close_signal('ethusdt_short_68p5_20251211_150000', 'loss', 2150.0)")


async def main():
    """Main entry point for examples."""
    print("=== Kill Switch Integration Examples ===\n")
    print("Choose an example:")
    print("1. Trading System Integration (main loop)")
    print("2. Monitoring System Integration (periodic checks)")
    print("3. Manual Operations")
    print("4. Signal Closing Example")
    print()

    choice = input("Enter choice (1-4): ")

    config = {
        'database': {'url': 'sqlite:///data/virtuoso.db'},
        'analysis': {
            'indicators': {
                'orderflow': {
                    'use_symmetric_divergence': True
                }
            }
        }
    }

    if choice == '1':
        system = TradingSystem(config)
        await system.run()

    elif choice == '2':
        system = MonitoringSystem(config)
        await system.run()

    elif choice == '3':
        example_manual_operations()

    elif choice == '4':
        example_signal_closing()

    else:
        print("Invalid choice")


if __name__ == '__main__':
    asyncio.run(main())
