import asyncio
import logging
import pandas as pd
import json
from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_bybit_ohlcv')

async def test_fetch_ohlcv():
    """Test fetching OHLCV data from Bybit API"""
    try:
        logger.info("Initializing Bybit exchange")
        exchange = BybitExchange({})
        await exchange.initialize()
        
        symbol = "BTCUSDT"
        interval = "1"  # 1 minute
        
        # Test direct API request
        logger.info(f"Making direct API request for {symbol} @ {interval}")
        response = await exchange._make_request('GET', '/v5/market/kline', {
            'category': 'linear',
            'symbol': symbol,
            'interval': interval,
            'limit': 200
        })
        
        logger.info(f"Response type: {type(response)}")
        if isinstance(response, dict):
            logger.info(f"Response keys: {list(response.keys())}")
            if 'result' in response:
                logger.info(f"Result keys: {list(response['result'].keys())}")
                if 'list' in response['result']:
                    logger.info(f"Got {len(response['result']['list'])} candles")
                    logger.info(f"First candle: {response['result']['list'][0]}")
                else:
                    logger.error("No 'list' key in result")
            else:
                logger.error("No 'result' key in response")
        else:
            logger.error(f"Response is not a dict: {response}")
        
        # Test _fetch_ohlcv method
        logger.info(f"Testing _fetch_ohlcv method for {symbol} @ {interval}")
        candles = await exchange._fetch_ohlcv(symbol, interval)
        logger.info(f"Got {len(candles)} candles from _fetch_ohlcv")
        if candles:
            logger.info(f"First candle: {candles[0]}")
        
        # Test fetch_ohlcv method if it exists
        if hasattr(exchange, 'fetch_ohlcv'):
            logger.info(f"Testing fetch_ohlcv method for {symbol} @ {interval}")
            ohlcv_data = await exchange.fetch_ohlcv(symbol, interval, limit=200)
            logger.info(f"Response type from fetch_ohlcv: {type(ohlcv_data)}")
            if isinstance(ohlcv_data, dict):
                logger.info(f"Response keys: {list(ohlcv_data.keys())}")
                if 'result' in ohlcv_data:
                    logger.info(f"Result keys: {list(ohlcv_data['result'].keys())}")
                    if 'list' in ohlcv_data['result']:
                        logger.info(f"Got {len(ohlcv_data['result']['list'])} candles")
                    else:
                        logger.error("No 'list' key in result")
                else:
                    logger.error("No 'result' key in response")
            else:
                logger.error(f"Response is not a dict: {ohlcv_data}")
        else:
            logger.error("Exchange does not have fetch_ohlcv method")
        
        # Test processing the response into a DataFrame
        logger.info("Testing DataFrame conversion")
        if candles:
            try:
                # Create DataFrame from candles
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                
                # Convert string values to numeric
                for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                # Convert timestamp to datetime and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Sort by timestamp (oldest first)
                df.sort_index(inplace=True)
                
                logger.info(f"Successfully created DataFrame with shape {df.shape}")
                logger.info(f"DataFrame head:\n{df.head()}")
                logger.info(f"DataFrame tail:\n{df.tail()}")
                
                # Check for NaN values
                nan_count = df.isna().sum().sum()
                if nan_count > 0:
                    logger.warning(f"DataFrame contains {nan_count} NaN values")
                    logger.warning(f"NaN counts by column:\n{df.isna().sum()}")
            except Exception as e:
                logger.error(f"Error creating DataFrame: {str(e)}")
        else:
            logger.error("No candles to create DataFrame")
        
        await exchange.close()
        logger.info("Test completed")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_fetch_ohlcv()) 