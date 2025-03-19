import asyncio
import logging
import sys
from pprint import pprint
import pandas as pd

from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("ohlcv_structure_test")

# Sample config
CONFIG = {
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

async def test_ohlcv_structure():
    try:
        # Initialize exchange
        exchange = BybitExchange(CONFIG)
        success = await exchange.initialize()
        if not success:
            logger.error("Failed to initialize exchange")
            return
            
        # Test symbol
        symbol = "BTCUSDT"
        
        # Fetch market data directly from exchange
        logger.info(f"\n=== Fetching market data for {symbol} ===")
        market_data = await exchange.fetch_market_data(symbol)
        
        # Check OHLCV structure
        logger.info("\n=== OHLCV Structure ===")
        if 'ohlcv' in market_data:
            ohlcv = market_data['ohlcv']
            logger.info(f"OHLCV keys: {list(ohlcv.keys())}")
            
            # Check each timeframe
            for tf in ['base', 'ltf', 'mtf', 'htf']:
                if tf in ohlcv:
                    tf_data = ohlcv[tf]
                    logger.info(f"\nTimeframe: {tf}")
                    logger.info(f"  Type: {type(tf_data)}")
                    logger.info(f"  Keys: {list(tf_data.keys()) if isinstance(tf_data, dict) else 'N/A'}")
                    
                    # Check data
                    data = tf_data.get('data') if isinstance(tf_data, dict) else None
                    if data is not None:
                        logger.info(f"  Data type: {type(data)}")
                        if hasattr(data, 'empty'):
                            logger.info(f"  Empty: {data.empty}")
                            if not data.empty:
                                logger.info(f"  Shape: {data.shape}")
                                logger.info(f"  Columns: {list(data.columns)}")
                                logger.info(f"  Index type: {type(data.index)}")
                                logger.info(f"  First row: {data.iloc[0]}")
                            else:
                                logger.info(f"  Columns: {list(data.columns)}")
                                logger.info(f"  Column dtypes: {data.dtypes.to_dict()}")
                    else:
                        logger.error(f"  No 'data' key found in {tf} timeframe")
                else:
                    logger.error(f"Missing {tf} timeframe in OHLCV data")
        
        # Perform validation similar to what the monitor would do
        logger.info("\n=== Manual Validation ===")
        valid = validate_market_data(market_data)
        logger.info(f"Manual validation result: {valid}")
            
        # Clean up
        await exchange.close()
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}", exc_info=True)

def validate_market_data(market_data):
    """Simplified validation logic similar to what the monitor would do"""
    if not market_data or not isinstance(market_data, dict):
        logger.error("Market data is not a valid dictionary")
        return False
        
    # Check OHLCV structure
    ohlcv = market_data.get('ohlcv', {})
    logger.debug("\n=== OHLCV Structure ===")
    logger.debug(f"OHLCV keys: {list(ohlcv.keys())}")
    
    # Check required timeframes
    required_timeframes = {'base', 'ltf', 'mtf', 'htf'}
    missing_timeframes = required_timeframes - set(ohlcv.keys())
    if missing_timeframes:
        logger.error(f"Missing timeframes: {missing_timeframes}")
        return False

    # Validate each timeframe's data
    for tf in required_timeframes:
        tf_data = ohlcv[tf]
        if not isinstance(tf_data, dict) or 'data' not in tf_data:
            logger.error(f"Invalid {tf} timeframe structure")
            return False
            
        df = tf_data['data']
        if not isinstance(df, pd.DataFrame) or df.empty:
            logger.error(f"Invalid DataFrame for {tf} timeframe")
            return False
            
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            logger.error(f"Missing columns in {tf}: {missing_columns}")
            return False

    logger.debug("Market data validation successful")
    return True

if __name__ == "__main__":
    asyncio.run(test_ohlcv_structure()) 