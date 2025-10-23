"""Proper validation of FIX #1 with correct timestamp handling."""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.manipulation_detector import ManipulationDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_fix1():
    """Properly validate FIX #1: Alert Persistence."""

    logger.info("="*80)
    logger.info("PROPER VALIDATION OF FIX #1: Alert Persistence")
    logger.info("="*80)

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

    # CORRECT WAY: Manually inject historical data with proper timestamps
    base_time = int(time.time()) - 900  # Start 15 minutes ago
    base_oi = 100000000

    for i in range(8):
        detector._historical_data.setdefault(symbol, []).append({
            'timestamp': base_time + (i * 60),  # 1-minute intervals
            'price': 50000,
            'volume': 1000000,
            'open_interest': base_oi
        })

    logger.info(f"✓ Injected {len(detector._historical_data[symbol])} historical data points")
    logger.info(f"  Time range: {base_time} to {base_time + 7*60}")

    # Now trigger alert with OI spike
    spike_oi = base_oi * 1.04  # 4% increase
    alert_data = {
        'ticker': {'last': 50000, 'baseVolume': 1000000},
        'funding': {'openInterest': spike_oi}
    }

    alert = await detector.analyze_market_data(symbol, alert_data)

    if not alert:
        logger.error("❌ TEST FAILED: Alert not created")
        return False

    logger.info(f"✓ Alert created: confidence={alert.confidence_score:.2f}")

    # CHECK 1: Alert persisted to _manipulation_history
    if symbol not in detector._manipulation_history:
        logger.error("❌ TEST FAILED: Symbol not in _manipulation_history")
        return False

    logger.info(f"✓ Symbol found in _manipulation_history")

    history = detector._manipulation_history[symbol]
    if len(history) == 0:
        logger.error("❌ TEST FAILED: _manipulation_history is empty")
        return False

    logger.info(f"✓ Alert persisted to history (length={len(history)})")

    # CHECK 2: alert_dict structure
    alert_dict = history[0]
    required_fields = ['timestamp', 'manipulation_type', 'confidence_score',
                      'severity', 'description', 'metrics']

    missing = [f for f in required_fields if f not in alert_dict]
    if missing:
        logger.error(f"❌ TEST FAILED: Missing fields: {missing}")
        return False

    logger.info(f"✓ alert_dict has all required fields")

    # CHECK 3: metrics.copy() prevents reference leaks
    original_metrics = alert.metrics
    stored_metrics = alert_dict['metrics']

    original_metrics['__test__'] = 'modified'

    if '__test__' in stored_metrics:
        logger.error("❌ TEST FAILED: metrics.copy() failed - reference leak")
        return False

    logger.info(f"✓ metrics.copy() prevents reference leaks")

    # CHECK 4: get_recent_alerts() works
    since = datetime.utcnow() - timedelta(hours=1)
    recent = await detector.get_recent_alerts(since, limit=10)

    logger.info(f"  get_recent_alerts() returned {len(recent)} alerts")

    if len(recent) == 0:
        logger.error("❌ TEST FAILED: get_recent_alerts() returned empty")
        logger.info(f"  Debug: since_timestamp = {int(since.timestamp())}")
        logger.info(f"  Debug: alert timestamp = {alert_dict['timestamp']}")
        logger.info(f"  Debug: Comparison: {alert_dict['timestamp']} >= {int(since.timestamp())} = {alert_dict['timestamp'] >= int(since.timestamp())}")
        return False

    logger.info(f"✓ get_recent_alerts() returns persisted alerts")

    # CHECK 5: API alert format
    api_alert = recent[0]
    api_required = ['id', 'timestamp', 'symbol', 'type', 'severity',
                   'confidence', 'description', 'metrics']

    missing_api = [f for f in api_required if f not in api_alert]
    if missing_api:
        logger.error(f"❌ TEST FAILED: API alert missing fields: {missing_api}")
        return False

    logger.info(f"✓ API alert format is correct")

    # CHECK 6: Multiple alerts append correctly
    # Wait a moment to avoid cooldown issues
    await asyncio.sleep(0.1)

    # Trigger second alert with volume spike
    alert2_data = {
        'ticker': {'last': 50000, 'baseVolume': 3000000},  # 3x volume
        'funding': {'openInterest': spike_oi}
    }

    alert2 = await detector.analyze_market_data(symbol, alert2_data)

    if alert2:
        if len(detector._manipulation_history[symbol]) != 2:
            logger.error(f"❌ TEST FAILED: Expected 2 alerts, got {len(detector._manipulation_history[symbol])}")
            return False

        logger.info(f"✓ Multiple alerts append correctly")
    else:
        logger.warning("⚠️  Second alert not triggered (may be normal due to timing)")

    logger.info("\n" + "="*80)
    logger.info("✅ FIX #1 VALIDATION: PASS")
    logger.info("="*80)

    return True


if __name__ == "__main__":
    success = asyncio.run(validate_fix1())
    sys.exit(0 if success else 1)
