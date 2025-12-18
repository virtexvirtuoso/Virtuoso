"""Debug timestamp issue in get_recent_alerts."""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta, timezone
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.manipulation_detector import ManipulationDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_timestamps():
    """Debug timestamp comparison issue."""

    config = {
        'monitoring': {
            'manipulation_detection': {
                'enabled': True,
                'cooldown': 0,
                'oi_change_15m_threshold': 0.015,
                'alert_confidence_threshold': 0.4,
                'min_data_points': 5,
            }
        }
    }

    detector = ManipulationDetector(config, logger)
    symbol = "BTCUSDT"

    # Build baseline
    for i in range(8):
        data = {
            'ticker': {'last': 50000, 'baseVolume': 1000000},
            'funding': {'openInterest': 100000000}
        }
        await detector.analyze_market_data(symbol, data)

    # Trigger alert
    alert_data = {
        'ticker': {'last': 50000, 'baseVolume': 1000000},
        'funding': {'openInterest': 104000000}
    }

    current_time_before = int(time.time())
    logger.info(f"Current timestamp BEFORE alert: {current_time_before}")

    alert = await detector.analyze_market_data(symbol, alert_data)

    current_time_after = int(time.time())
    logger.info(f"Current timestamp AFTER alert: {current_time_after}")

    if alert:
        logger.info(f"Alert created: {alert.description}")
        logger.info(f"Alert timestamp: {alert.timestamp}")
        logger.info(f"Alert timestamp type: {type(alert.timestamp)}")

        # Check history
        if symbol in detector._manipulation_history:
            history = detector._manipulation_history[symbol]
            logger.info(f"\nHistory length: {len(history)}")

            for i, hist in enumerate(history):
                logger.info(f"\nHistory entry {i}:")
                logger.info(f"  Type: {type(hist)}")
                logger.info(f"  Timestamp: {hist.get('timestamp', 'N/A')}")
                logger.info(f"  Timestamp type: {type(hist.get('timestamp', 0))}")

            # Now test get_recent_alerts
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            logger.info(f"\nCalling get_recent_alerts with since: {since}")
            logger.info(f"Since timestamp (int): {int(since.timestamp())}")

            recent = await detector.get_recent_alerts(since, limit=10)
            logger.info(f"get_recent_alerts returned {len(recent)} alerts")

            if len(recent) > 0:
                logger.info(f"\nFirst alert:")
                logger.info(f"  {recent[0]}")
            else:
                logger.info("\n❌ No alerts returned - investigating why...")

                # Manual check
                since_timestamp = int(since.timestamp())
                logger.info(f"\nManual check:")
                logger.info(f"  since_timestamp: {since_timestamp}")

                for hist in history:
                    hist_ts = hist.get('timestamp', 0)
                    logger.info(f"  hist timestamp: {hist_ts}")
                    logger.info(f"  Comparison: {hist_ts} >= {since_timestamp} = {hist_ts >= since_timestamp}")

        else:
            logger.error("❌ Symbol not in _manipulation_history")

    else:
        logger.error("❌ No alert created")


if __name__ == "__main__":
    asyncio.run(debug_timestamps())
