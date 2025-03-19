#!/usr/bin/env python3
"""Test script to verify Bybit ticker fetching methods"""

import asyncio
import logging
import sys
import os
from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set environment variables for API keys
os.environ['BYBIT_API_KEY'] = "your_test_api_key"
os.environ['BYBIT_API_SECRET'] = "your_test_api_secret"

async def test_bybit_ticker():
    """Test Bybit ticker fetching methods"""
    
    # Create a Bybit exchange instance with the correct config structure
    config = {
        "exchanges": {
            "bybit": {
                "api_key": "",  # Will be loaded from environment
                "api_secret": "",  # Will be loaded from environment
                "testnet": False,
                "rest_endpoint": "https://api.bybit.com",
                "websocket": {
                    "mainnet_endpoint": "wss://stream.bybit.com/v5/public",
                    "testnet_endpoint": "wss://stream-testnet.bybit.com/v5/public",
                    "channels": ["ticker", "orderbook", "trade"],
                    "symbols": ["BTCUSDT"]
                }
            }
        }
    }
    
    try:
        exchange = BybitExchange(config)
        # No need to initialize for this test
        
        symbol = "BTCUSDT"
        
        logger.info(f"Testing get_ticker for {symbol}...")
        ticker1 = await exchange.get_ticker(symbol)
        logger.info(f"get_ticker result: {ticker1['last'] if ticker1 and 'last' in ticker1 else ticker1}")
        
        logger.info(f"Testing fetch_ticker for {symbol}...")
        ticker2 = await exchange.fetch_ticker(symbol)
        logger.info(f"fetch_ticker result: {ticker2['last'] if ticker2 and 'last' in ticker2 else ticker2}")
        
        logger.info(f"Testing _fetch_ticker for {symbol}...")
        ticker3 = await exchange._fetch_ticker(symbol)
        logger.info(f"_fetch_ticker result: {ticker3['last'] if ticker3 and 'last' in ticker3 else ticker3}")
        
        logger.info("All ticker tests completed successfully")
    except Exception as e:
        logger.error(f"Error testing ticker methods: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_bybit_ticker()) 