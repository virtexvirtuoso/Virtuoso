import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('oi_test')

async def test_open_interest():
    """Test open interest data fetching from Bybit"""
    
    # Initialize exchange with proper configuration
    config = {
        'exchanges': {
            'bybit': {
                'enabled': True,
                'rest_endpoint': 'https://api.bybit.com',
                'ws_endpoint': 'wss://stream.bybit.com',
                'websocket': {
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                },
                'api_credentials': {
                    'key': '',
                    'secret': ''
                },
                'api_key': '',
                'api_secret': '',
                'rate_limits': {
                    'market_data': 10,
                    'order': 5
                },
                'testnet': False,
                'symbols': ['BTC/USDT'],
                'max_leverage': 100
            }
        },
        'logging': {
            'level': 'INFO'
        }
    }
    
    exchange = None
    try:
        # Create instance manually instead of using get_instance
        logger.info("Initializing Bybit exchange...")
        exchange = BybitExchange(config)
        
        # Initialize exchange
        logger.info("Initializing exchange...")
        initialized = await exchange.initialize()
        if not initialized:
            logger.error("Failed to initialize exchange")
            return
        
        # Fetch open interest history
        logger.info("Fetching open interest history...")
        oi_data = await exchange.fetch_open_interest_history('BTC/USDT')
        
        # Check structure
        logger.info(f"Open interest history entries: {len(oi_data.get('history', []))}")
        if oi_data.get('history'):
            logger.info(f"First entry: {oi_data['history'][0]}")
        else:
            logger.warning("No open interest history data available")
        
        # Fetch market data with the fix
        logger.info("Fetching full market data...")
        market_data = await exchange.fetch_market_data('BTC/USDT')
        
        # Check open interest in market data
        logger.info("Open interest in market data:")
        logger.info(f"Current: {market_data['open_interest']['current']}")
        logger.info(f"Previous: {market_data['open_interest']['previous']}")
        logger.info(f"History entries: {len(market_data['open_interest']['history'])}")
        
        if market_data['open_interest']['history']:
            logger.info(f"First history entry: {market_data['open_interest']['history'][0]}")
        else:
            logger.warning("No open interest history in market data")
            
        # Test the price-OI divergence calculation
        from src.indicators.orderflow_indicators import OrderflowIndicators
        
        logger.info("Initializing OrderflowIndicators...")
        indicators = OrderflowIndicators({})
        
        logger.info("Calculating price-OI divergence...")
        divergence = indicators._calculate_price_oi_divergence(market_data)
        
        logger.info(f"Divergence result: {divergence}")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)
    finally:
        logger.info("Test completed")
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_open_interest()) 