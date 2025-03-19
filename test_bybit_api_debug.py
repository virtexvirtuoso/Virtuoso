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
logger = logging.getLogger("bybit_debug")

async def fetch_ohlcv():
    """Fetch OHLCV data directly from Bybit API"""
    async with aiohttp.ClientSession() as session:
        params = {
            'category': 'linear',
            'symbol': 'BTCUSDT',
            'interval': '1',
            'limit': 200
        }
        
        logger.info("Fetching OHLCV data from Bybit API...")
        async with session.get('https://api.bybit.com/v5/market/kline', params=params) as response:
            result = await response.json()
            logger.debug(f"Raw API response: {json.dumps(result, indent=2)[:200]}...")
            
            # Check if we have candles
            if 'result' in result and 'list' in result['result']:
                candles = result['result']['list']
                logger.info(f"Received {len(candles)} candles from API")
                if candles:
                    logger.debug(f"First candle: {candles[0]}")
                    return result
            else:
                logger.error("No candles found in response")
                return None

def parse_ohlcv(response):
    """Parse OHLCV data from Bybit API response - similar to the exchange implementation"""
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

def convert_to_dataframe(ohlcv_data):
    """Convert OHLCV data to DataFrame - similar to the test script"""
    try:
        # Convert list of candles to DataFrame
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Log sample data for debugging
        logger.debug(f"DataFrame: shape={df.shape}, cols={list(df.columns)}")
        logger.debug("Sample data:\n" + str(df.head()))
        
        return df
    except Exception as e:
        logger.error(f"Error converting to DataFrame: {str(e)}")
        # Create empty DataFrame as fallback
        return pd.DataFrame(
            columns=['open', 'high', 'low', 'close', 'volume']
        )

async def main():
    # Step 1: Fetch OHLCV data
    response = await fetch_ohlcv()
    
    # Step 2: Parse OHLCV data
    ohlcv_data = parse_ohlcv(response)
    logger.info(f"Parsed {len(ohlcv_data)} candles")
    
    # Step 3: Convert to DataFrame
    df = convert_to_dataframe(ohlcv_data)
    logger.info(f"Final DataFrame shape: {df.shape}")
    
    # Print the first few rows
    print("\nFinal DataFrame:")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main()) 