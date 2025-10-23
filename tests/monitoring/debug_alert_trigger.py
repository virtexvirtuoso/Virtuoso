"""Debug why alerts aren't triggering."""

import asyncio
import logging
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.manipulation_detector import ManipulationDetector

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def debug_alert_trigger():
    """Debug alert triggering."""

    config = {
        'monitoring': {
            'manipulation_detection': {
                'enabled': True,
                'cooldown': 0,
                'oi_change_15m_threshold': 0.015,
                'oi_change_1h_threshold': 0.02,
                'volume_spike_threshold': 2.5,
                'price_change_15m_threshold': 0.0075,
                'alert_confidence_threshold': 0.4,
                'min_data_points': 5,
            }
        }
    }

    detector = ManipulationDetector(config, logger)
    symbol = "BTCUSDT"

    logger.info("="*80)
    logger.info("Building baseline data (8 points)...")
    logger.info("="*80)

    base_time = int(time.time()) - 600  # Start 10 minutes ago

    for i in range(8):
        # Manually update historical data with timestamps
        detector._historical_data.setdefault(symbol, []).append({
            'timestamp': base_time + (i * 60),  # 1 minute intervals
            'price': 50000,
            'volume': 1000000,
            'open_interest': 100000000
        })

    logger.info(f"Historical data points: {len(detector._historical_data.get(symbol, []))}")

    # Now analyze with OI spike
    logger.info("\n" + "="*80)
    logger.info("Analyzing with 4% OI spike...")
    logger.info("="*80)

    alert_data = {
        'ticker': {'last': 50000, 'baseVolume': 1000000},
        'funding': {'openInterest': 104000000}  # 4% increase
    }

    alert = await detector.analyze_market_data(symbol, alert_data)

    if alert:
        logger.info(f"\n✅ Alert created!")
        logger.info(f"   Description: {alert.description}")
        logger.info(f"   Confidence: {alert.confidence_score}")
        logger.info(f"   Timestamp: {alert.timestamp}")

        # Check persistence
        if symbol in detector._manipulation_history:
            logger.info(f"\n✅ Alert persisted to history")
            logger.info(f"   History length: {len(detector._manipulation_history[symbol])}")
        else:
            logger.error(f"\n❌ Alert NOT persisted to history")

    else:
        logger.error("\n❌ NO ALERT CREATED")

        # Check why
        logger.info("\nDiagnostics:")
        logger.info(f"  Has sufficient data: {detector._has_sufficient_data(symbol)}")
        logger.info(f"  Is in cooldown: {detector._is_in_cooldown(symbol)}")

        # Check historical data
        hist_data = detector._historical_data.get(symbol, [])
        logger.info(f"  Historical data points: {len(hist_data)}")

        if hist_data:
            logger.info(f"  Latest OI: {hist_data[-1].get('open_interest', 0)}")
            logger.info(f"  Oldest OI: {hist_data[0].get('open_interest', 0)}")

            # Calculate what the OI change would be
            if len(hist_data) >= 2:
                current_oi = 104000000
                oldest_oi = hist_data[0].get('open_interest', 0)
                if oldest_oi > 0:
                    pct_change = (current_oi - oldest_oi) / oldest_oi
                    logger.info(f"  OI change: {pct_change*100:.2f}%")
                    logger.info(f"  Threshold: {config['monitoring']['manipulation_detection']['oi_change_15m_threshold']*100:.2f}%")

        # Check stats
        stats = detector.get_stats()
        logger.info(f"\nStats:")
        logger.info(f"  Total analyses: {stats['total_analyses']}")
        logger.info(f"  Alerts generated: {stats['alerts_generated']}")


if __name__ == "__main__":
    asyncio.run(debug_alert_trigger())
