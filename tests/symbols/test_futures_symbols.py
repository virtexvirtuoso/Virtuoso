#!/usr/bin/env python3
"""
Test script to check quarterly futures symbol formats on Bybit
"""
import asyncio
import logging
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.monitoring.market_reporter import MarketReporter
from src.core.exchanges.bybit import BybitExchange
from src.core.config.config_manager import ConfigManager

async def test_quarterly_futures():
    """Test quarterly futures symbol formats against Bybit API"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Initialize exchange
    config_mgr = ConfigManager()
    exchange = BybitExchange(config_mgr)
    await exchange.initialize()
    
    # Initialize reporter with exchange
    reporter = MarketReporter(exchange=exchange, logger=logger)
    
    # Run the test
    print("====== TESTING QUARTERLY FUTURES SYMBOL FORMATS ======")
    await reporter._check_quarterly_futures()
    print("====== TEST COMPLETED ======")

if __name__ == "__main__":
    asyncio.run(test_quarterly_futures()) 