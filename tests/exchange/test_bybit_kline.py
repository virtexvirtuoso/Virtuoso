#!/usr/bin/env python
"""Test script to directly query Bybit API for OHLCV data."""

import asyncio
import aiohttp
import logging
import json
import pandas as pd
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger('test_bybit_kline')

# Set to DEBUG for more verbose output
logger.setLevel(logging.DEBUG)

async def fetch_kline(session, symbol, interval, limit=200):
    """Fetch kline (OHLCV) data from Bybit API.
    
    Args:
        session: aiohttp ClientSession
        symbol: Trading pair (e.g., BTCUSDT)
        interval: Time interval (e.g., 1, 5, 15, 30, 60, 240, D)
        limit: Number of candles to retrieve
        
    Returns:
        OHLCV data as a DataFrame
    """
    url = f"https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    try:
        logger.debug(f"Fetching {symbol} kline data for interval {interval}")
        async with session.get(url, params=params) as response:
            # Get response text
            response_text = await response.text()
            
            # Log raw response for debugging
            logger.debug(f"Raw response: {response_text[:500]}...")
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Check for successful response
            if data.get('retCode') == 0 and data.get('retMsg') == 'OK':
                result = data.get('result', {})
                candles = result.get('list', [])
                
                if not candles:
                    logger.warning(f"No candles returned for {symbol} {interval}")
                    return None
                
                logger.info(f"Received {len(candles)} candles for {symbol} {interval}")
                
                # Create DataFrame with proper column names
                # Bybit V5 API returns: timestamp, open, high, low, close, volume, turnover
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                
                # Convert timestamp to datetime and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Convert numeric columns to float
                for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                    df[col] = df[col].astype(float)
                
                # Sort by timestamp (ascending)
                df.sort_index(inplace=True)
                
                return df
            else:
                logger.error(f"API error: {data.get('retMsg', 'Unknown error')}")
                return None
    except Exception as e:
        logger.error(f"Error fetching kline data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def test_timeframes():
    """Test fetching different timeframes."""
    # Define symbols and intervals to test
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = {
        'base': '1',    # 1 minute (base timeframe)
        'ltf': '5',     # 5 minutes (low timeframe)
        'mtf': '30',    # 30 minutes (medium timeframe)
        'htf': '240'    # 4 hours (high timeframe)
    }
    
    async with aiohttp.ClientSession() as session:
        # Test each symbol and interval
        for symbol in symbols:
            logger.info(f"Testing {symbol} kline data")
            
            for tf_name, interval in intervals.items():
                df = await fetch_kline(session, symbol, interval)
                
                if df is not None and not df.empty:
                    # Log summary of data
                    logger.info(f"{symbol} {tf_name} ({interval}): {len(df)} candles")
                    logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
                    
                    # Display first 2 candles
                    logger.info(f"First 2 candles: \n{df.head(2)}")
                else:
                    logger.error(f"Failed to get {tf_name} data for {symbol}")

async def main():
    """Main test function."""
    try:
        logger.info("Starting Bybit OHLCV data test")
        await test_timeframes()
        logger.info("Test completed")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 