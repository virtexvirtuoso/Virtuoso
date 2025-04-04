import asyncio
import logging
from src.monitoring.market_reporter import MarketReporter
from src.core.exchanges.bybit import BybitExchange

async def test_market_reporter():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting market reporter test")
    
    # Initialize exchange
    config = {
        'exchanges': {
            'bybit': {
                'rest_endpoint': 'https://api.bybit.com',
                'testnet': False,
                'websocket': {
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                }
            }
        },
        'market_data': {
            'update_interval': 1.0,
            'validation': {
                'volume': {'min_value': 0},
                'turnover': {'min_value': 0}
            }
        }
    }
    
    try:
        # Create exchange instance
        exchange = BybitExchange(config, None)
        await exchange.initialize()
        logger.info("Exchange initialized successfully")
        
        # Initialize market reporter
        reporter = MarketReporter(exchange=exchange, logger=logger)
        logger.info("Market reporter initialized successfully")
        
        # Test the function that previously triggered the error
        symbols = ['BTC/USDT:USDT']
        logger.info(f"Testing _calculate_futures_premium with symbols: {symbols}")
        
        result = await reporter._calculate_futures_premium(symbols)
        logger.info("Test completed successfully!")
        logger.info(f"Result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_market_reporter()) 