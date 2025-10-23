"""Debug OI calculation in detail."""

import asyncio
import logging
import sys
import os
import time
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.manipulation_detector import ManipulationDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_oi():
    """Debug OI calculation."""

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

    # Inject historical data 15 minutes ago
    base_time = int(time.time()) - 900
    base_oi = 100000000

    for i in range(8):
        detector._historical_data.setdefault(symbol, []).append({
            'timestamp': base_time + (i * 60),
            'price': 50000,
            'volume': 1000000,
            'open_interest': base_oi
        })

    logger.info(f"Historical data:")
    for dp in detector._historical_data[symbol]:
        logger.info(f"  ts={dp['timestamp']}, oi={dp['open_interest']}")

    # Now call analyze_market_data with OI spike
    current_time_before = int(time.time())
    logger.info(f"\nCurrent time before analyze: {current_time_before}")

    spike_oi = base_oi * 1.04
    logger.info(f"Spike OI: {spike_oi} (4% increase from {base_oi})")

    alert_data = {
        'ticker': {'last': 50000, 'baseVolume': 1000000},
        'funding': {'openInterest': spike_oi}
    }

    # Manually call _analyze_manipulation_metrics to see what's calculated
    # First, update historical data as analyze_market_data would do
    detector._update_historical_data(symbol, alert_data)

    logger.info(f"\nHistorical data after update:")
    for dp in detector._historical_data[symbol]:
        logger.info(f"  ts={dp['timestamp']}, oi={dp['open_interest']}")

    # Now call _analyze_manipulation_metrics
    metrics = await detector._analyze_manipulation_metrics(symbol, alert_data)

    logger.info(f"\nMetrics calculated:")
    logger.info(f"  oi_change_15m: {metrics.get('oi_change_15m', 0)}")
    logger.info(f"  oi_change_15m_pct: {metrics.get('oi_change_15m_pct', 0)}")
    logger.info(f"  oi_change_1h: {metrics.get('oi_change_1h', 0)}")
    logger.info(f"  oi_change_1h_pct: {metrics.get('oi_change_1h_pct', 0)}")

    # Calculate confidence
    confidence = detector._calculate_confidence_score(metrics, symbol)
    logger.info(f"\nConfidence score: {confidence}")
    logger.info(f"Alert threshold: {config['monitoring']['manipulation_detection']['alert_confidence_threshold']}")

    if confidence >= config['monitoring']['manipulation_detection']['alert_confidence_threshold']:
        logger.info("✓ Confidence exceeds threshold - alert would be triggered")
    else:
        logger.error("❌ Confidence below threshold - alert would NOT be triggered")

    # Now actually call analyze_market_data to see if alert is created
    # Reset historical data first
    detector._historical_data[symbol] = []
    detector._last_alerts = {}

    # Re-inject historical data
    for i in range(8):
        detector._historical_data.setdefault(symbol, []).append({
            'timestamp': base_time + (i * 60),
            'price': 50000,
            'volume': 1000000,
            'open_interest': base_oi
        })

    alert = await detector.analyze_market_data(symbol, alert_data)

    if alert:
        logger.info(f"\n✅ Alert created: {alert.description}")
        logger.info(f"   Confidence: {alert.confidence_score}")
    else:
        logger.error("\n❌ No alert created")


if __name__ == "__main__":
    asyncio.run(debug_oi())
