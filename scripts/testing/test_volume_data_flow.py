#!/usr/bin/env python3
"""Test volume data flow from manager to market reporter"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.exchanges.manager import ExchangeManager
from core.config.config_manager import ConfigManager

async def test_volume_data_flow():
    """Test the volume data flow"""
    
    # Initialize config and manager
    config = ConfigManager()
    await config.initialize()
    
    manager = ExchangeManager(config)
    await manager.initialize()
    
    try:
        print("=== Testing Exchange Manager Volume Data ===")
        
        # Test direct market data fetch
        market_data = await manager.get_market_data('BTCUSDT')
        
        print(f"Market data keys: {list(market_data.keys())}")
        
        if 'ticker' in market_data:
            ticker = market_data['ticker']
            print(f"Ticker baseVolume: {ticker.get('baseVolume')}")
            print(f"Ticker quoteVolume: {ticker.get('quoteVolume')}")
            print(f"Ticker volume: {ticker.get('volume')}")
        
        if 'price' in market_data:
            price = market_data['price']
            print(f"Price structure volume: {price.get('volume')}")
            print(f"Price structure turnover: {price.get('turnover')}")
            
        print("\n=== Testing Market Reporter Data Extraction ===")
        
        # Import and test market reporter extraction
        from monitoring.market_reporter import MarketReporter
        
        reporter = MarketReporter()
        extracted = reporter._extract_market_data(market_data)
        
        print(f"Extracted volume: {extracted.get('volume')}")
        print(f"Extracted turnover: {extracted.get('turnover')}")
        
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_volume_data_flow()) 