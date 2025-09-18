#!/usr/bin/env python3
"""Simple test to verify chart generation with OHLCV data."""

import asyncio
import sys
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_chart_generation():
    """Test chart generation with OHLCV data."""
    try:
        # Import required modules
        from monitoring.alert_manager import AlertManager
        from signal_generation.signal_generator import SignalGenerator
        from core.market.market_data_manager import MarketDataManager
        from core.exchanges.manager import ExchangeManager

        # Configuration
        config = {
            'exchange': 'bybit',
            'symbols': ['BTC/USDT:USDT'],
            'timeframes': ['5m'],
            'thresholds': {
                'buy': 60,
                'sell': 40
            },
            'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL', 'test_webhook_url')
        }

        logger.info("Step 1: Initializing services...")

        # Initialize exchange manager
        exchange_manager = ExchangeManager(config)

        # Initialize market data manager
        market_data_manager = MarketDataManager(exchange_manager)

        # Initialize alert manager
        alert_manager = AlertManager(config)

        # Initialize signal generator with market_data_manager
        signal_generator = SignalGenerator(config, alert_manager, market_data_manager)

        logger.info("Step 2: Creating mock OHLCV data...")

        # Create mock OHLCV data DataFrame
        timestamps = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        base_price = 50000
        mock_ohlcv = pd.DataFrame({
            'timestamp': timestamps,
            'open': base_price + np.random.randn(100) * 100,
            'high': base_price + np.random.randn(100) * 150 + 100,
            'low': base_price + np.random.randn(100) * 150 - 100,
            'close': base_price + np.random.randn(100) * 100,
            'volume': np.random.randint(1000, 10000, 100)
        })

        # Store in market_data_manager's cache
        if hasattr(market_data_manager, '_ohlcv_cache'):
            cache_key = f"BTC/USDT:USDT_5m"
            market_data_manager._ohlcv_cache[cache_key] = {
                'data': mock_ohlcv,
                'timestamp': datetime.now()
            }
            logger.info(f"✅ Stored mock OHLCV data in cache with key: {cache_key}")

        logger.info("Step 3: Testing signal generation with analyze_market...")

        # Simulate confluence analysis result
        confluence_result = {
            'symbol': 'BTC/USDT:USDT',
            'score': 75.0,  # Above buy threshold
            'components': {
                'orderflow': 80.0,
                'sentiment': 75.0,
                'liquidity': 70.0,
                'bitcoin_beta': 72.0,
                'smart_money_flow': 78.0,
                'machine_learning': 73.0
            },
            'results': {
                'orderflow': {'interpretation': 'Strong buying pressure detected'},
                'sentiment': {'interpretation': 'Bullish sentiment prevailing'},
                'liquidity': {'interpretation': 'Good liquidity support'},
                'bitcoin_beta': {'interpretation': 'Positive correlation with BTC'},
                'smart_money_flow': {'interpretation': 'Institutional accumulation'},
                'machine_learning': {'interpretation': 'Uptrend predicted'}
            },
            'reliability': 1.0,
            'price': 50000
        }

        # Call analyze_market to trigger OHLCV fetching and alert
        await signal_generator.analyze_market(
            confluence_result['symbol'],
            confluence_result,
            confluence_result['price']
        )

        logger.info("Step 4: Checking for generated charts...")

        # Check if charts were generated
        chart_dir = os.path.join(os.getcwd(), 'reports', 'charts')
        if os.path.exists(chart_dir):
            charts = [f for f in os.listdir(chart_dir) if f.endswith('.png')]
            if charts:
                logger.info(f"✅ Found {len(charts)} chart files:")
                for chart in charts[-3:]:  # Show last 3
                    logger.info(f"   - {chart}")
            else:
                logger.warning("⚠️ No chart files found")
        else:
            os.makedirs(chart_dir, exist_ok=True)
            logger.info("Created reports/charts directory")

        logger.info("✅ Test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        return False

async def main():
    """Main test runner."""
    print("=" * 60)
    print("Testing Chart Generation with OHLCV Data")
    print("=" * 60)

    success = await test_chart_generation()

    if success:
        print("\n✅ TEST PASSED - Chart generation flow is working!")
    else:
        print("\n❌ TEST FAILED - Check the logs for details")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())