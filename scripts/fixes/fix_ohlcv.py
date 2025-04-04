import asyncio
import aiohttp
import json
import pandas as pd
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                   stream=sys.stdout)
logger = logging.getLogger("fix_ohlcv")

class BybitFix:
    """Class to demonstrate the fix for the OHLCV data fetching issue"""
    
    async def fetch_ohlcv(self, symbol, interval, limit=200):
        """Fixed fetch_ohlcv method that properly processes the API response"""
        async with aiohttp.ClientSession() as session:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            logger.info(f"Fetching OHLCV data for {symbol} @ {interval}")
            async with session.get('https://api.bybit.com/v5/market/kline', params=params) as response:
                result = await response.json()
                
                # Process the response to extract candles
                processed_candles = await self.parse_ohlcv(result)
                logger.info(f"Processed {len(processed_candles)} candles")
                
                return processed_candles
    
    async def parse_ohlcv(self, response):
        """Parse OHLCV data from Bybit API response"""
        ohlcv = []
        
        # Check if we have a valid response
        if not response or not isinstance(response, dict):
            logger.error(f"Invalid OHLCV response format: {type(response)}")
            return ohlcv
            
        # Get result from response
        result = response.get('result', {})
        if not isinstance(result, dict):
            logger.error(f"Invalid result format in OHLCV response: {type(result)}")
            return ohlcv
            
        # Get candle list from result
        candles = result.get('list', [])
        if not candles:
            logger.warning("No candles returned in OHLCV response")
            return ohlcv
            
        logger.debug(f"Processing {len(candles)} raw candles from API")
        
        # Process each candle with enhanced error handling
        for candle in candles:
            try:
                # Verify we have at least 6 elements (required fields)
                if len(candle) < 6:
                    logger.warning(f"Skipping candle with insufficient elements: {candle}")
                    continue
                
                # Bybit returns candles as: [timestamp, open, high, low, close, volume, turnover]
                # Apply explicit conversion and validation
                timestamp = int(candle[0])
                open_price = float(candle[1])
                high_price = float(candle[2])
                low_price = float(candle[3])
                close_price = float(candle[4])
                volume = float(candle[5])
                
                # Basic validation
                if timestamp <= 0:
                    logger.warning(f"Skipping candle with invalid timestamp: {candle}")
                    continue
                    
                # Price validation (optional - adjust thresholds as needed)
                if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                    logger.warning(f"Skipping candle with invalid price values: {candle}")
                    continue
                    
                if high_price < low_price:
                    logger.warning(f"Skipping candle with high < low: {candle}")
                    continue
                
                # Add the processed candle
                ohlcv.append([
                    timestamp,      # timestamp
                    open_price,     # open
                    high_price,     # high
                    low_price,      # low
                    close_price,    # close
                    volume          # volume
                ])
                
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing candle: {e}, candle: {candle}")
                continue
        
        # Final validation and logging        
        if not ohlcv:
            logger.error("No valid candles after processing OHLCV data")
        else:
            logger.debug(f"Successfully processed {len(ohlcv)} valid candles out of {len(candles)} raw candles")
                
        return ohlcv

async def test_fix():
    """Test the fix for the OHLCV data fetching issue"""
    bybit_fix = BybitFix()
    
    # Test with different timeframes
    timeframes = {
        'base': '1',
        'ltf': '5',
        'mtf': '30',
        'htf': '240'
    }
    
    ohlcv_data = {}
    
    # Create tasks for each timeframe
    tasks = [
        bybit_fix.fetch_ohlcv('BTCUSDT', interval, limit=200)
        for interval in timeframes.values()
    ]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.debug("\n=== Raw OHLCV DataFrames Before Wrapping ===")
    
    for i, tf in enumerate(timeframes.keys()):
        result = results[i]
        if isinstance(result, Exception):
            logger.error(f"Error fetching {tf} timeframe: {str(result)}")
            # Create empty DataFrame as fallback
            ohlcv_data[tf] = pd.DataFrame(
                columns=['open', 'high', 'low', 'close', 'volume']
            )
        else:
            try:
                # Convert list of candles to DataFrame
                df = pd.DataFrame(result, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Log sample data for debugging
                logger.debug(f"{tf} DataFrame: shape={df.shape}, cols={list(df.columns)}")
                logger.debug("Sample data:\n" + str(df.head()))
                
                ohlcv_data[tf] = df
            except Exception as e:
                logger.error(f"Error processing {tf} timeframe data: {str(e)}")
                logger.debug(f"Raw result: {result}")
                # Create empty DataFrame as fallback
                ohlcv_data[tf] = pd.DataFrame(
                    columns=['open', 'high', 'low', 'close', 'volume']
                )
    
    # Print summary
    print("\n=== OHLCV Data Summary ===")
    for tf, df in ohlcv_data.items():
        print(f"{tf}: shape={df.shape}")
    
    # Print sample data for base timeframe
    if 'base' in ohlcv_data and not ohlcv_data['base'].empty:
        print("\nBase timeframe sample data:")
        print(ohlcv_data['base'].head())

async def main():
    await test_fix()
    
    print("\n=== Fix Explanation ===")
    print("The issue is in how the OHLCV data is processed from the Bybit API response.")
    print("The fetch_ohlcv method in the BybitExchange class returns the raw API response,")
    print("but the test script expects it to return processed candles.")
    print("\nTo fix this issue, you need to:")
    print("1. Modify the fetch_ohlcv method to process the API response and extract the candles")
    print("2. Or modify the fetch_ohlcv_data function in the test script to handle the raw API response")
    print("\nThe fix implemented in this script demonstrates the first approach.")

if __name__ == "__main__":
    asyncio.run(main()) 