#!/usr/bin/env python3
"""
Test validation fixes with real Bybit API data.

This script:
1. Fetches real market data from Bybit
2. Tests timeframe mapping
3. Ensures trade data is collected
4. Runs confluence analysis to verify no validation errors
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import traceback
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.config.manager import ConfigManager
from src.core.exchanges.bybit import BybitExchange
from src.analysis.core.confluence import ConfluenceAnalyzer
from src.core.analysis.market_data_wrapper import MarketDataWrapper

async def test_bybit_data_collection():
    """Test data collection from Bybit API."""
    logger = Logger('test_bybit_data')
    
    logger.info("="*60)
    logger.info("Testing Bybit Data Collection and Validation Fixes")
    logger.info("="*60)
    
    try:
        # Initialize exchange
        config = ConfigManager().config
        exchange = BybitExchange(config, logger)
        
        # Test symbol
        symbol = 'BTCUSDT'
        logger.info(f"\nTesting with symbol: {symbol}")
        
        # 1. Fetch OHLCV data with different timeframes
        logger.info("\n1. Fetching OHLCV data...")
        ohlcv_data = {}
        
        timeframes = {
            '1m': 100,    # 1 minute
            '5m': 100,    # 5 minutes
            '15m': 100,   # 15 minutes
            '30m': 100,   # 30 minutes
            '1h': 100,    # 1 hour
            '4h': 100     # 4 hours
        }
        
        for interval, limit in timeframes.items():
            logger.info(f"   Fetching {interval} data...")
            try:
                candles = await exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
                if candles:
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Store with the same key
                    ohlcv_data[interval] = df
                    
                    logger.info(f"   ✓ Got {len(df)} candles for {interval}")
            except Exception as e:
                logger.error(f"   ✗ Failed to fetch {interval} data: {e}")
        
        logger.info(f"\nCollected OHLCV timeframes: {list(ohlcv_data.keys())}")
        
        # 2. Fetch orderbook
        logger.info("\n2. Fetching orderbook...")
        try:
            orderbook = await exchange.fetch_order_book(symbol, limit=25)
            logger.info(f"   ✓ Got orderbook with {len(orderbook['bids'])} bids and {len(orderbook['asks'])} asks")
        except Exception as e:
            logger.error(f"   ✗ Failed to fetch orderbook: {e}")
            orderbook = None
        
        # 3. Fetch trades (this is where the issue was)
        logger.info("\n3. Fetching trades...")
        try:
            trades = await exchange.fetch_trades(symbol, limit=1000)
            logger.info(f"   ✓ Got {len(trades)} trades")
        except Exception as e:
            logger.error(f"   ✗ Failed to fetch trades: {e}")
            trades = []
        
        # 4. Create market data structure
        market_data = {
            'symbol': symbol,
            'ohlcv': ohlcv_data,
            'orderbook': orderbook,
            'trades': trades,
            'sentiment': {
                'fear_greed_index': 50,
                'social_sentiment': 0.5
            }
        }
        
        # 5. Apply market data wrapper to ensure correct format
        logger.info("\n4. Applying market data wrapper...")
        logger.info(f"   Before wrapper - OHLCV keys: {list(market_data['ohlcv'].keys())}")
        logger.info(f"   Before wrapper - Has trades: {len(market_data.get('trades', []))} trades")
        
        wrapped_data = await MarketDataWrapper.ensure_complete_market_data(
            exchange, symbol, market_data
        )
        
        logger.info(f"   After wrapper - OHLCV keys: {list(wrapped_data['ohlcv'].keys())}")
        logger.info(f"   After wrapper - Has trades: {len(wrapped_data.get('trades', []))} trades")
        
        # 6. Validate the wrapped data
        logger.info("\n5. Validating market data...")
        validation = MarketDataWrapper.validate_market_data(wrapped_data)
        
        logger.info("   Validation results:")
        for key, value in validation.items():
            status = "✓" if value else "✗"
            logger.info(f"   {status} {key}: {value}")
        
        # 7. Run confluence analysis
        logger.info("\n6. Running confluence analysis...")
        analyzer = ConfluenceAnalyzer(config)
        
        try:
            result = await analyzer.analyze(wrapped_data)
            
            # Debug: print result structure
            logger.info(f"\n   Result type: {type(result)}")
            if isinstance(result, dict):
                logger.info(f"   Result keys: {list(result.keys())}")
                if 'metadata' in result:
                    logger.info(f"   Metadata keys: {list(result['metadata'].keys())}")
                    logger.info(f"   Metadata status: {result['metadata'].get('status', 'NOT_FOUND')}")
                    if 'errors' in result['metadata']:
                        logger.info(f"   Metadata errors: {result['metadata']['errors']}")
                    if 'error' in result['metadata']:
                        logger.info(f"   Metadata error: {result['metadata']['error']}")
                    if 'error_reason' in result['metadata']:
                        logger.info(f"   Metadata error_reason: {result['metadata']['error_reason']}")
            
            logger.info(f"\n   Confluence score: {result.get('confluence_score', 'N/A')}")
            status = result.get('metadata', {}).get('status', 'UNKNOWN')
            logger.info(f"   Status: {status}")
            
            if status == 'SUCCESS':
                logger.info("\n   ✅ Confluence analysis SUCCEEDED!")
                logger.info("\n   Component scores:")
                for component, score in result['components'].items():
                    logger.info(f"     {component}: {score:.2f}")
                    
                # Check if volume and orderflow succeeded
                if 'results' in result:
                    volume_result = result['results'].get('volume', {})
                    orderflow_result = result['results'].get('orderflow', {})
                    
                    logger.info("\n   Volume indicator:")
                    logger.info(f"     Score: {volume_result.get('score', 'N/A')}")
                    
                    logger.info("\n   Orderflow indicator:")
                    logger.info(f"     Score: {orderflow_result.get('score', 'N/A')}")
                    
            else:
                metadata = result.get('metadata', {})
                error_msg = metadata.get('error', metadata.get('error_reason', 'Unknown error'))
                logger.error(f"\n   ❌ Confluence analysis FAILED: {error_msg}")
                
                if 'failed_indicators' in metadata:
                    logger.error(f"   Failed indicators: {metadata['failed_indicators']}")
                    
                if 'errors' in metadata:
                    logger.error("   Errors:")
                    for error in metadata['errors']:
                        logger.error(f"     - {error}")
                        
        except Exception as e:
            logger.error(f"   Error in confluence analysis: {e}")
            logger.error(traceback.format_exc())
        
        # 8. Summary
        logger.info("\n" + "="*60)
        logger.info("Test Summary")
        logger.info("="*60)
        
        logger.info("\nData Collection Results:")
        logger.info(f"  OHLCV Timeframes: {list(ohlcv_data.keys())}")
        logger.info(f"  Orderbook: {'✓' if orderbook else '✗'}")
        logger.info(f"  Trades: {len(trades)} trades")
        
        logger.info("\nValidation Results:")
        all_valid = all(validation.values())
        if all_valid:
            logger.info("  ✅ All validation checks passed")
        else:
            logger.info("  ❌ Some validation checks failed")
            
        logger.info("\nKey Fixes Verified:")
        logger.info(f"  Base timeframe mapping: {'✓' if validation['has_base_timeframe'] else '✗'}")
        logger.info(f"  Trade data available: {'✓' if validation['has_trades'] else '✗'}")
        logger.info(f"  All timeframes present: {'✓' if validation['has_all_timeframes'] else '✗'}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

async def main():
    """Run the test."""
    return await test_bybit_data_collection()

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))