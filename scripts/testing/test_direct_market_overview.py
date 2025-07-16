#!/usr/bin/env python3
"""Test market overview calculation directly"""

import asyncio
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_market_overview():
    """Test market overview calculation directly"""
    
    # Import after path setup
    from monitoring.market_reporter import MarketReporter
    from core.exchanges.bybit import BybitExchange
    from core.config.config_manager import ConfigManager
    
    # Initialize config
    config = ConfigManager()
    await config.initialize()
    
    # Get exchange config
    exchanges_config = config.get_value('exchanges', {})
    bybit_config = exchanges_config.get('bybit', {})
    
    # Create exchange directly
    exchange = BybitExchange(bybit_config)
    await exchange.initialize()
    
    try:
        # Create market reporter with exchange but NO top_symbols_manager
        reporter = MarketReporter(exchange=exchange, top_symbols_manager=None)
        
        # Test symbols
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        print("=== Testing Market Overview Calculation ===")
        
        # Call the market overview calculation directly
        result = await reporter._calculate_market_overview(symbols)
        
        print(f"Total volume: {result.get('total_volume')}")
        print(f"Total turnover: {result.get('total_turnover')}")
        print(f"Volume by pair: {result.get('volume_by_pair')}")
        
        # Test individual ticker fetch
        print("\n=== Testing Individual Ticker Fetch ===")
        ticker = await reporter._fetch_with_retry('fetch_ticker', 'BTCUSDT', timeout=5)
        if ticker:
            print(f"Direct ticker baseVolume: {ticker.get('baseVolume')}")
            print(f"Direct ticker quoteVolume: {ticker.get('quoteVolume')}")
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_market_overview()) 