#!/usr/bin/env python
"""Test script to verify the MarketDataManager's handling of OHLCV data."""

import asyncio
import logging
import sys
import os
import json
from pprint import pprint

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger('test_ohlcv')

# Set to DEBUG for more verbose output
logger.setLevel(logging.DEBUG)

async def main():
    """Main test function."""
    from src.core.market.market_data_manager import MarketDataManager
    from src.core.exchanges.exchange_manager import ExchangeManager
    
    try:
        logger.info("Initializing exchange manager...")
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        
        logger.info("Initializing market data manager...")
        # Get config from exchange manager
        config = exchange_manager.config
        
        # Create market data manager
        market_data_manager = MarketDataManager(config=config, exchange_manager=exchange_manager)
        
        # Initialize with test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        logger.info(f"Initializing with test symbols: {test_symbols}")
        await market_data_manager.initialize(test_symbols)
        
        # Test fetching OHLCV data directly
        logger.info("Testing direct OHLCV fetching...")
        for symbol in test_symbols:
            logger.info(f"Fetching timeframes for {symbol}")
            timeframes = await market_data_manager._fetch_timeframes(symbol)
            if timeframes:
                for tf_name, df in timeframes.items():
                    logger.info(f"{symbol} {tf_name}: {len(df)} candles")
            else:
                logger.error(f"No timeframes returned for {symbol}")
        
        # Test getting complete market data
        logger.info("Testing get_market_data method...")
        for symbol in test_symbols:
            logger.info(f"Getting market data for {symbol}")
            market_data = await market_data_manager.get_market_data(symbol)
            
            # Check components in market data
            components = []
            if 'ticker' in market_data and market_data['ticker']:
                components.append(f"ticker")
            if 'orderbook' in market_data and market_data['orderbook']:
                components.append(f"orderbook")
            if 'trades' in market_data and market_data['trades']:
                components.append(f"trades ({len(market_data['trades'])})")
            if 'ohlcv' in market_data and market_data['ohlcv']:
                ohlcv_info = []
                for tf, df in market_data['ohlcv'].items():
                    ohlcv_info.append(f"{tf}: {len(df)}")
                components.append(f"ohlcv ({', '.join(ohlcv_info)})")
            
            logger.info(f"Market data for {symbol} contains: {', '.join(components)}")
            
            # Verify OHLCV data
            if 'ohlcv' in market_data and market_data['ohlcv']:
                logger.info(f"OHLCV data found for {symbol}")
                # Check each timeframe
                for tf, df in market_data['ohlcv'].items():
                    if len(df) > 0:
                        logger.info(f"{symbol} {tf} has {len(df)} candles")
                        if len(df) > 0:
                            # Display first candle
                            logger.info(f"First candle: {df.iloc[0].to_dict()}")
                    else:
                        logger.warning(f"{symbol} {tf} has no candles")
            else:
                logger.error(f"No OHLCV data for {symbol}")
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Clean up
        if 'exchange_manager' in locals():
            await exchange_manager.close()
        if 'market_data_manager' in locals():
            await market_data_manager.stop()
        
if __name__ == "__main__":
    asyncio.run(main()) 