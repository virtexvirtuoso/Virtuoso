import asyncio
import logging
import pandas as pd
from src.core.exchanges.bybit import BybitExchange

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                  format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                  handlers=[logging.StreamHandler()])

logger = logging.getLogger('debug_ohlcv')

async def debug_ohlcv():
    # Sample config
    config = {
        'exchanges': {
            'bybit': {
                'name': 'bybit',
                'enabled': True,
                'testnet': False,
                'rest_endpoint': 'https://api.bybit.com',
                'websocket': {
                    'enabled': False,
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                },
                'api_credentials': {
                    'api_key': 'dummy_key',
                    'api_secret': 'dummy_secret'
                }
            }
        }
    }
    
    # Create exchange
    bybit = BybitExchange(config)
    
    # Initialize exchange (required)
    success = await bybit.initialize()
    if not success:
        logger.error("Failed to initialize Bybit exchange")
        return
    
    # Test OHLCV fetching for BTCUSDT
    try:
        logger.info("Fetching OHLCV data for BTCUSDT...")
        ohlcv_data = await bybit._fetch_all_timeframes('BTCUSDT')
        
        # Debug detailed information about each timeframe
        for tf_name, df in ohlcv_data.items():
            logger.info(f"{tf_name} Timeframe:")
            logger.info(f"Shape: {df.shape}")
            logger.info(f"Columns: {list(df.columns)}")
            logger.info(f"Index type: {type(df.index).__name__}")
            logger.info(f"Column dtypes: {df.dtypes}")
            logger.info(f"Is empty: {df.empty}")
            logger.info(f"Has null values: {df.isnull().values.any()}")
            
            # Print first few rows
            if not df.empty:
                logger.info(f"First 2 rows:\n{df.head(2)}")
                
            # Check if index is DatetimeIndex and is timezone naive
            if isinstance(df.index, pd.DatetimeIndex):
                logger.info(f"Index timezone info: {df.index.tzinfo}")
            
            # Output the raw DataFrame representation for further analysis
            logger.info(f"Raw DataFrame info:")
            logger.info(f"{df.info()}")
            
            logger.info("-" * 50)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    
    # Cleanup
    await bybit.close()

# Run the test
if __name__ == "__main__":
    asyncio.run(debug_ohlcv()) 