#!/usr/bin/env python3
"""
Simple RPI Integration Test Script

This script validates the RPI integration components directly.
"""

import asyncio
import sys
import os
import logging
import time
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def test_imports():
    """Test that all RPI-related components can be imported."""
    logger.info("🔍 Testing RPI component imports...")

    try:
        from src.core.exchanges.bybit import BybitExchange
        logger.info("✅ BybitExchange imported successfully")
    except ImportError as e:
        logger.error(f"❌ BybitExchange import failed: {e}")
        return False

    try:
        from src.core.market.market_data_manager import MarketDataManager
        logger.info("✅ MarketDataManager imported successfully")
    except ImportError as e:
        logger.error(f"❌ MarketDataManager import failed: {e}")
        return False

    try:
        from src.data_processing.data_processor import DataProcessor
        logger.info("✅ DataProcessor imported successfully")
    except ImportError as e:
        logger.error(f"❌ DataProcessor import failed: {e}")
        return False

    try:
        from src.indicators.orderbook_indicators import OrderbookIndicators
        logger.info("✅ OrderbookIndicators imported successfully")
    except ImportError as e:
        logger.error(f"❌ OrderbookIndicators import failed: {e}")
        return False

    try:
        from src.monitoring.alert_manager import AlertManager
        logger.info("✅ AlertManager imported successfully")
    except ImportError as e:
        logger.error(f"❌ AlertManager import failed: {e}")
        return False

    return True

async def test_rpi_data_processing():
    """Test RPI data processing functionality."""
    logger.info("🔍 Testing RPI data processing...")

    try:
        from src.data_processing.data_processor import DataProcessor

        # Create test RPI data
        test_rpi_data = {
            'b': [  # bids
                [50000.0, 1.2, 0.3],  # [price, non_rpi, rpi]
                [49999.5, 0.8, 0.2],
                [49999.0, 1.0, 0.1]
            ],
            'a': [  # asks
                [50001.0, 1.1, 0.4],
                [50001.5, 0.9, 0.2],
                [50002.0, 1.3, 0.1]
            ],
            'ts': int(time.time() * 1000),
            'u': 12345,
            'seq': 67890
        }

        # Create test config for DataProcessor
        test_config = {
            'data_processing': {
                'validation': {'enabled': True},
                'caching': {'enabled': False}
            }
        }

        processor = DataProcessor(test_config)
        processed_rpi = await processor.process_rpi_orderbook(test_rpi_data)

        # Validate processed data
        assert isinstance(processed_rpi, dict), "Processed RPI should be a dict"
        assert 'b' in processed_rpi, "Processed RPI should contain bids"
        assert 'a' in processed_rpi, "Processed RPI should contain asks"

        bids = processed_rpi.get('b', [])
        asks = processed_rpi.get('a', [])

        logger.info(f"✅ RPI data processed: {len(bids)} bids, {len(asks)} asks")

        # Test sorting
        if len(bids) > 1:
            for i in range(len(bids) - 1):
                assert bids[i][0] >= bids[i+1][0], "Bids should be sorted descending"

        if len(asks) > 1:
            for i in range(len(asks) - 1):
                assert asks[i][0] <= asks[i+1][0], "Asks should be sorted ascending"

        logger.info("✅ RPI data sorting validation passed")
        return True

    except Exception as e:
        logger.error(f"❌ RPI data processing test failed: {e}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        return False

async def test_retail_component_calculation():
    """Test retail component calculation."""
    logger.info("🔍 Testing retail component calculation...")

    try:
        from src.indicators.orderbook_indicators import OrderbookIndicators

        # Create test config
        test_config = {
            'orderbook': {
                'depth_levels': 10,
                'imbalance_threshold': 1.5,
                'liquidity_threshold': 1.5
            }
        }

        indicators = OrderbookIndicators(test_config)

        # Create test market data with RPI
        test_market_data = {
            'symbol': 'BTCUSDT',
            'orderbook': {
                'bids': [[50000.0, 1.5], [49999.0, 2.0]],
                'asks': [[50001.0, 1.3], [50002.0, 1.8]],
                'timestamp': int(time.time() * 1000)
            },
            'rpi_orderbook': {
                'b': [
                    [50000.0, 1.2, 0.3],  # total = 1.5 (matches standard)
                    [49999.0, 1.8, 0.2]   # total = 2.0 (matches standard)
                ],
                'a': [
                    [50001.0, 1.0, 0.3],  # total = 1.3 (matches standard)
                    [50002.0, 1.6, 0.2]   # total = 1.8 (matches standard)
                ],
                'ts': int(time.time() * 1000)
            },
            'rpi_enabled': True,
            'trades': []
        }

        # Test retail component calculation
        retail_score = indicators._calculate_retail_component(test_market_data)

        assert isinstance(retail_score, (int, float)), "Retail score should be numeric"
        assert 0 <= retail_score <= 100, f"Retail score should be 0-100, got {retail_score}"

        logger.info(f"✅ Retail component calculation successful: score = {retail_score:.2f}")

        # Test with no RPI data
        test_market_data_no_rpi = test_market_data.copy()
        test_market_data_no_rpi['rpi_enabled'] = False
        test_market_data_no_rpi.pop('rpi_orderbook', None)

        retail_score_no_rpi = indicators._calculate_retail_component(test_market_data_no_rpi)

        logger.info(f"✅ No RPI data test: score = {retail_score_no_rpi:.2f}")

        return True

    except Exception as e:
        logger.error(f"❌ Retail component calculation test failed: {e}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        return False

async def test_alert_generation():
    """Test retail alert generation."""
    logger.info("🔍 Testing retail alert generation...")

    try:
        from src.monitoring.alert_manager import AlertManager

        # Create test config
        test_config = {
            'alerts': {
                'discord_webhook_url': None,  # No actual alerts
                'retail_pressure': {
                    'enabled': True,
                    'threshold': 70
                }
            }
        }

        alert_manager = AlertManager(test_config)

        # Test scenarios
        test_scenarios = [
            {'retail': 85.0, 'expected': 'extreme_buying'},
            {'retail': 15.0, 'expected': 'extreme_selling'},
            {'retail': 75.0, 'expected': 'strong_buying'},
            {'retail': 25.0, 'expected': 'strong_selling'},
            {'retail': 50.0, 'expected': 'neutral'}
        ]

        for scenario in test_scenarios:
            test_analysis = {'components': {'retail': scenario['retail']}}
            alerts = alert_manager._generate_retail_alerts(test_analysis, 'BTCUSDT')

            logger.info(f"✅ Scenario {scenario['expected']} (score={scenario['retail']:.1f}): {len(alerts)} alerts")
            if alerts:
                logger.debug(f"   Alerts: {alerts}")

        return True

    except Exception as e:
        logger.error(f"❌ Alert generation test failed: {e}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        return False

async def main():
    """Main test runner."""
    logger.info("🚀 Starting Simple RPI Integration Tests")
    logger.info("=" * 60)

    tests = [
        ("Component Imports", test_imports),
        ("RPI Data Processing", test_rpi_data_processing),
        ("Retail Component Calculation", test_retail_component_calculation),
        ("Alert Generation", test_alert_generation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: FAILED - {str(e)}")

    logger.info("\n" + "=" * 60)
    logger.info(f"🎯 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        logger.info("✅ All tests passed! RPI integration is working correctly.")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed. Please review the RPI integration.")
        return 1

if __name__ == '__main__':
    import traceback
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except Exception as e:
        logger.error(f"🚨 Test runner crashed: {str(e)}")
        logger.debug(traceback.format_exc())
        sys.exit(1)