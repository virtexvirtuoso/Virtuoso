#!/usr/bin/env python3
"""
Test whale detection system directly on VPS
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.monitoring.monitor import MarketMonitor
from src.core.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

async def test_whale_detection():
    """Test whale detection functionality"""
    try:
        # Initialize config
        config = load_config()

        # Initialize monitor
        monitor = MarketMonitor(config)
        logger.info("Monitor initialized")

        # Test whale detection with sample data
        test_symbol = 'BTCUSDT'
        test_market_data = {
            'bids': [[45000, 1.0], [44999, 2.0], [44998, 5.0]],
            'asks': [[45001, 1.5], [45002, 3.0], [45003, 4.0]],
            'timestamp': 1695427200000,
            'symbol': test_symbol
        }

        logger.info(f"Testing whale detection for {test_symbol}")

        # Call whale detection directly
        await monitor._analyze_and_alert_whale_activity(test_symbol, test_market_data)

        logger.info("✅ Whale detection test completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Whale detection test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_whale_detection())
    sys.exit(0 if success else 1)