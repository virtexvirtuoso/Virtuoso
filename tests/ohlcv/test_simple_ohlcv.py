#!/usr/bin/env python
"""Simple test script to verify OHLCV data availability in market data."""

import asyncio
import ccxt.async_support as ccxt
import logging
import json
import os
import pandas as pd
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger('test_simple_ohlcv')

TEST_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

async def fetch_ohlcv(exchange, symbol, timeframe='1m', limit=100):
    """Fetch OHLCV data from exchange."""
    try:
        logger.info(f"Fetching OHLCV data for {symbol} ({timeframe})")
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if ohlcv:
            logger.info(f"Successfully fetched {len(ohlcv)} candles for {symbol} ({timeframe})")
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Log some basic info
            logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
            logger.info(f"Sample candle:\n{df.iloc[0]}")
            
            return df
        else:
            logger.error(f"No OHLCV data returned for {symbol} ({timeframe})")
            return None
    except Exception as e:
        logger.error(f"Error fetching OHLCV for {symbol} ({timeframe}): {str(e)}")
        return None

async def build_market_data(exchange, symbol):
    """Build a market data structure similar to what MarketDataManager would provide."""
    market_data = {
        'symbol': symbol,
        'timestamp': int(time.time() * 1000),
        'ohlcv': {}
    }
    
    # Define timeframes to fetch
    timeframes = {
        'base': '1m',
        'ltf': '5m',
        'mtf': '30m',
        'htf': '4h'
    }
    
    # Fetch OHLCV data for each timeframe
    for tf_name, tf in timeframes.items():
        df = await fetch_ohlcv(exchange, symbol, tf)
        if df is not None:
            market_data['ohlcv'][tf_name] = df
    
    # Check if we got OHLCV data
    if market_data['ohlcv']:
        logger.info(f"Successfully built market data for {symbol} with {len(market_data['ohlcv'])} timeframes")
    else:
        logger.error(f"Failed to build market data for {symbol}: No OHLCV data")
    
    return market_data

async def generate_report_data(market_data_by_symbol):
    """Generate report data structure from market data."""
    report_data = {}
    
    for symbol, market_data in market_data_by_symbol.items():
        if 'ohlcv' in market_data and market_data['ohlcv']:
            report_data[symbol] = {
                'ohlcv': market_data['ohlcv'],
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'exchange': 'bybit'
                }
            }
            logger.info(f"Added {symbol} to report data with {len(market_data['ohlcv'])} timeframes")
    
    # Save report data to file
    if report_data:
        output_dir = 'test_report_output'
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert DataFrames to lists for JSON serialization
        json_data = {}
        for symbol, data in report_data.items():
            json_data[symbol] = {
                'metadata': data['metadata']
            }
            
            # Convert DataFrames to lists
            json_data[symbol]['ohlcv'] = {}
            for tf, df in data['ohlcv'].items():
                # Convert index to string and reset index to make it serializable
                json_data[symbol]['ohlcv'][tf] = df.reset_index().to_dict(orient='records')
        
        # Save to file
        output_file = os.path.join(output_dir, f"market_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
            
        logger.info(f"Report data saved to {output_file}")
    
    return report_data

async def main():
    """Main test function."""
    exchange = None
    
    try:
        logger.info("Starting OHLCV test")
        
        # Create exchange
        exchange = ccxt.bybit({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'linear',  # Use linear futures
                'adjustForTimeDifference': True,
            }
        })
        
        # Load markets
        await exchange.load_markets()
        
        # Get market data for each symbol
        market_data_by_symbol = {}
        for symbol in TEST_SYMBOLS:
            market_data = await build_market_data(exchange, symbol)
            market_data_by_symbol[symbol] = market_data
        
        # Generate report data
        report_data = await generate_report_data(market_data_by_symbol)
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Close exchange
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(main()) 