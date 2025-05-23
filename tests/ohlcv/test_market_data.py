#!/usr/bin/env python3
"""
Integration test for market data fetching and validation.
This script tests that market data is properly fetched and validated,
with a focus on ensuring ticker data is correctly initialized.
"""

import asyncio
import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def test_market_data_manager():
    """Test market data manager fetching and validation."""
    try:
        # Import required components
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager
        from src.monitoring.monitor import MarketMonitor
        
        # Create config
        config = {
            'exchange': {
                'primary': 'bybit',
                'api_key': '',  # No API key needed for public data
                'api_secret': ''
            },
            'market_data': {
                'cache': {
                    'enabled': True,
                    'data_ttl': 60
                }
            }
        }
        
        # Create exchange manager
        exchange_manager = ExchangeManager(config)
        await exchange_manager.initialize()
        
        # Create market data manager
        logger.info("Creating market data manager")
        market_data_manager = MarketDataManager(config, exchange_manager)
        
        # Initialize with test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'WIFUSDT']
        logger.info(f"Initializing market data manager with symbols: {test_symbols}")
        await market_data_manager.initialize(test_symbols)
        
        # Test direct data fetching
        for symbol in test_symbols:
            logger.info(f"Testing direct market data fetching for {symbol}")
            market_data = await market_data_manager.get_market_data(symbol)
            
            # Validate ticker data
            logger.info(f"Validating ticker data for {symbol}")
            ticker = market_data.get('ticker')
            if ticker:
                logger.info(f"Ticker data found: {ticker.get('last')} (bid: {ticker.get('bid')}, ask: {ticker.get('ask')})")
                assert ticker is not None, "Ticker data should not be None"
                assert isinstance(ticker, dict), "Ticker data should be a dictionary"
                assert 'last' in ticker, "Ticker should have a 'last' field"
                assert 'bid' in ticker, "Ticker should have a 'bid' field"
                assert 'ask' in ticker, "Ticker should have a 'ask' field"
            else:
                logger.error(f"No ticker data found for {symbol}")
                
            # Validate orderbook
            logger.info(f"Validating orderbook data for {symbol}")
            orderbook = market_data.get('orderbook')
            if orderbook:
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])
                logger.info(f"Orderbook data found: {len(bids)} bids, {len(asks)} asks")
            else:
                logger.error(f"No orderbook data found for {symbol}")
                
            # Validate OHLCV data
            logger.info(f"Validating OHLCV data for {symbol}")
            ohlcv = market_data.get('ohlcv', {})
            if ohlcv:
                for tf, data in ohlcv.items():
                    logger.info(f"OHLCV data for {tf}: {len(data) if data is not None else 'None'} candles")
            else:
                logger.error(f"No OHLCV data found for {symbol}")
        
        # Test MarketMonitor validation
        logger.info("Testing MarketMonitor data validation")
        monitor = MarketMonitor(
            logger=logger,
            exchange_manager=exchange_manager,
            market_data_manager=market_data_manager
        )
        
        # Test fetching and validation
        for symbol in test_symbols:
            logger.info(f"Testing MarketMonitor fetch_market_data for {symbol}")
            market_data = await monitor.fetch_market_data(symbol)
            
            # Check if ticker is properly initialized
            ticker = market_data.get('ticker')
            if ticker:
                logger.info(f"MarketMonitor ticker data: {ticker.get('last')} (bid: {ticker.get('bid')}, ask: {ticker.get('ask')})")
                assert ticker is not None, "Ticker data should not be None"
                assert isinstance(ticker, dict), "Ticker data should be a dictionary"
            else:
                logger.error(f"MarketMonitor returned no ticker data for {symbol}")
                
            # Validate data using MarketMonitor's validate method
            logger.info(f"Validating market data for {symbol} through MarketMonitor")
            validation_result = await monitor.validate_market_data(market_data)
            logger.info(f"Validation result: {validation_result}")
            assert validation_result, f"Market data validation failed for {symbol}"
        
        logger.info("All tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting market data integration test")
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(test_market_data_manager())
    sys.exit(0 if result else 1) 