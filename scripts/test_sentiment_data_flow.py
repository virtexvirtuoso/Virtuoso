#!/usr/bin/env python3
"""
Test script to verify sentiment data flow is working correctly.
This script checks that all sentiment data sources are properly connected.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.market.market_data_manager import MarketDataManager
from src.core.exchanges.manager import ExchangeManager
from src.utils.logging_config import configure_logging
import logging

async def test_sentiment_data_flow():
    """Test that sentiment data is properly populated."""
    
    # Setup logging
    configure_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize components
    logger.info("Initializing Exchange Manager and Market Data Manager...")
    exchange_manager = ExchangeManager()
    market_data_manager = MarketDataManager(exchange_manager)
    
    # Test symbol
    symbol = 'BTCUSDT'
    
    try:
        # Initialize exchange
        await exchange_manager.initialize()
        logger.info("Exchange manager initialized")
        
        # Refresh all components including sentiment data
        logger.info(f"Refreshing market data for {symbol}...")
        await market_data_manager.refresh_components(
            symbol, 
            components=['ticker', 'long_short_ratio', 'risk_limits']
        )
        
        # Get market data including sentiment
        logger.info(f"Getting market data for {symbol}...")
        market_data = await market_data_manager.get_market_data(symbol)
        
        # Check sentiment dict
        sentiment = market_data.get('sentiment', {})
        
        print("\n" + "="*60)
        print("SENTIMENT DATA FLOW TEST RESULTS")
        print("="*60)
        
        # Check each sentiment component
        checks = {
            'long_short_ratio': 'Long/Short Ratio',
            'risk': 'Risk Limits',
            'funding_rate': 'Funding Rate',
            'liquidations': 'Liquidations',
            'open_interest': 'Open Interest'
        }
        
        for key, name in checks.items():
            if key in sentiment:
                status = "✅ FOUND"
                data = sentiment[key]
                # Show some data details
                if isinstance(data, dict):
                    details = f"Keys: {list(data.keys())[:3]}"
                elif isinstance(data, list):
                    details = f"Count: {len(data)}"
                else:
                    details = f"Value: {data}"
                print(f"{name:20} {status:10} - {details}")
            else:
                print(f"{name:20} ❌ MISSING")
        
        print("\n" + "="*60)
        print("RAW SENTIMENT DICT:")
        print("="*60)
        
        # Print full sentiment dict for debugging
        import json
        print(json.dumps(sentiment, indent=2, default=str))
        
        # Check data_cache to see what's available
        print("\n" + "="*60)
        print("DATA CACHE KEYS FOR SYMBOL:")
        print("="*60)
        
        if symbol in market_data_manager.data_cache:
            cache_keys = list(market_data_manager.data_cache[symbol].keys())
            for key in cache_keys:
                data = market_data_manager.data_cache[symbol][key]
                if data:
                    if isinstance(data, dict):
                        info = f"Dict with {len(data)} keys"
                    elif isinstance(data, list):
                        info = f"List with {len(data)} items"
                    else:
                        info = f"Type: {type(data).__name__}"
                    print(f"  - {key}: {info}")
                else:
                    print(f"  - {key}: Empty/None")
        
    except Exception as e:
        logger.error(f"Error testing sentiment data flow: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await exchange_manager.cleanup()
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_sentiment_data_flow())