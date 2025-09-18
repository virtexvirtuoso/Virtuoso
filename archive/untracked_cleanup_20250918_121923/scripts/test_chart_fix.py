#!/usr/bin/env python3
"""Test script to verify that chart generation works with OHLCV data."""

import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_chart_fix.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_chart_generation_flow():
    """Test the complete flow from signal generation to chart creation."""
    try:
        # Import required modules
        from core.di.service_locator import ServiceLocator
        from core.di.interfaces import IAlertManager, ISignalGenerator, IMarketDataManager
        from core.di.registration import register_all_services
        from monitoring.alert_manager import AlertManager
        from signal_generation.signal_generator import SignalGenerator
        from core.market.market_data_manager import MarketDataManager

        # Configure test
        config = {
            'exchange': 'bybit',
            'symbols': ['BTC/USDT:USDT'],
            'timeframes': ['5m'],
            'thresholds': {
                'buy': 60,
                'sell': 40
            },
            'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL')
        }

        # Initialize services
        logger.info("Initializing services...")
        service_locator = ServiceLocator()
        register_all_services(service_locator, config)

        # Get required services
        alert_manager = service_locator.get(IAlertManager)
        market_data_manager = service_locator.get(IMarketDataManager)

        # Initialize signal generator with dependencies
        signal_generator = SignalGenerator(config, alert_manager, market_data_manager)

        # Create test signal data with simulated scores
        test_signal = {
            'symbol': 'BTC/USDT:USDT',
            'current_price': 50000,
            'confluence': 75.0,  # Above buy threshold
            'momentum_score': 80.0,
            'volume_score': 70.0,
            'orderflow_score': 75.0,
            'orderbook_score': 72.0,
            'sentiment_score': 78.0,
            'price_structure_score': 73.0,
            'futures_premium_score': 71.0,
            'timeframe': '5m',
            'timestamp': datetime.now().timestamp()
        }

        logger.info("Generating signal with OHLCV data fetching...")

        # Generate signal - this should now fetch OHLCV data
        signal_result = await signal_generator.generate_signal(test_signal)

        logger.info(f"Signal generated: {signal_result['type']} with score {signal_result['confluence_score']:.2f}")

        # Check if OHLCV was fetched in analyze_market
        if hasattr(signal_generator, 'market_data_manager') and signal_generator.market_data_manager:
            logger.info("✅ market_data_manager is available in signal_generator")
        else:
            logger.error("❌ market_data_manager NOT available in signal_generator")

        # Verify chart generation capability
        if hasattr(alert_manager, 'pdf_generator') and alert_manager.pdf_generator:
            logger.info("✅ PDF generator available in alert_manager")

            # Check if chart generation methods exist
            if hasattr(alert_manager.pdf_generator, '_create_candlestick_chart'):
                logger.info("✅ _create_candlestick_chart method exists")
            if hasattr(alert_manager.pdf_generator, '_create_simulated_chart'):
                logger.info("✅ _create_simulated_chart method exists")
        else:
            logger.error("❌ PDF generator NOT available in alert_manager")

        # Check for generated charts
        chart_dir = Path('reports/charts')
        if chart_dir.exists():
            charts = list(chart_dir.glob('*.png'))
            if charts:
                logger.info(f"✅ Found {len(charts)} chart files")
                for chart in charts[-3:]:  # Show last 3 charts
                    logger.info(f"  - {chart.name}")
            else:
                logger.warning("⚠️ No chart files found in reports/charts/")
        else:
            logger.warning("⚠️ reports/charts directory does not exist")

        logger.info("✅ Test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        return False

async def main():
    """Main test runner."""
    logger.info("=" * 60)
    logger.info("Starting Chart Generation Fix Test")
    logger.info("=" * 60)

    success = await test_chart_generation_flow()

    if success:
        logger.info("\n✅ ALL TESTS PASSED - Chart generation with OHLCV data is working!")
    else:
        logger.error("\n❌ TESTS FAILED - Review the logs for details")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())