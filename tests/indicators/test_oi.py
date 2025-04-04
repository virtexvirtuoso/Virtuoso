#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import logging
import sys
import os

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger('test_oi')

# Add the current directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our exchange implementation
from src.core.exchanges.bybit import BybitExchange

async def test_direct_api():
    """Test the Bybit API endpoint directly using aiohttp"""
    try:
        symbols = ["BTCUSDT"]
        intervals = ["5min", "15min", "30min"]
        
        for symbol in symbols:
            for interval in intervals:
                logger.info(f"Testing direct API call to Bybit open interest endpoint for {symbol} with interval {interval}")
                params = {
                    'category': 'linear',
                    'symbol': symbol,
                    'intervalTime': interval,
                    'limit': 5
                }
                
                logger.debug(f"API params: {params}")
                
                async with aiohttp.ClientSession() as session:
                    url = 'https://api.bybit.com/v5/market/open-interest'
                    logger.debug(f"Making request to {url}")
                    
                    async with session.get(url, params=params) as resp:
                        status = resp.status
                        logger.debug(f"Response status: {status}")
                        
                        if status != 200:
                            text = await resp.text()
                            logger.error(f"API error: {status} - {text}")
                            continue
                        
                        result = await resp.json()
                        logger.info(f"API response for {symbol} with interval {interval}:")
                        if 'result' in result and 'list' in result['result']:
                            items = result['result']['list']
                            logger.info(f"Found {len(items)} open interest entries")
                            
                            # Show sample entry
                            if items:
                                logger.info(f"Sample entry: {items[0]}")
                        else:
                            logger.error(f"Response missing expected structure")
    
    except Exception as e:
        logger.error(f"Error in direct API test: {e}", exc_info=True)

async def test_exchange_implementation():
    """Test our BybitExchange implementation"""
    try:
        logger.info("Testing our BybitExchange implementation with fixed interval format")
        
        # Create exchange instance with proper config structure
        config = {
            'exchanges': {
                'bybit': {
                    'api_key': '',
                    'api_secret': '',
                    'rate_limits': {
                        'default': {'max_requests': 10, 'timeframe': 1},
                        'market_data': {'max_requests': 10, 'timeframe': 1}
                    },
                    'websocket': {
                        'enabled': False,
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                    }
                }
            }
        }
        exchange = BybitExchange(config, logger)
        
        # Test with different intervals
        intervals = ["5min", "15min", "30min"]
        symbol = "BTCUSDT"
        
        for interval in intervals:
            # Call the method with the current interval
            logger.info(f"Calling fetch_open_interest_history with interval {interval}")
            result = await exchange.fetch_open_interest_history(symbol, interval=interval)
            
            logger.info(f"Result from fetch_open_interest_history with interval {interval}:")
            
            # Check if we got history
            if 'history' in result and result['history']:
                logger.info(f"✅ Success! Got {len(result['history'])} history entries")
                logger.info(f"Sample history entry: {result['history'][0]}")
            else:
                logger.warning(f"❌ No history entries in result for interval {interval}")
    
    except Exception as e:
        logger.error(f"Error in exchange implementation test: {e}", exc_info=True)

async def test_market_data_integration():
    """Test that open interest data is correctly integrated into market data structure"""
    try:
        logger.info("Testing market data integration of open interest data")
        
        # Import necessary modules
        from src.core.exchanges.bybit import BybitExchange
        
        # Create Bybit-specific config that includes the required structure
        bybit_config = {
            'exchanges': {
                'bybit': {
                    'name': 'Bybit',
                    'enabled': True,
                    'api_key': '',
                    'api_secret': '',
                    'api_credentials': {
                        'api_key': os.getenv('BYBIT_API_KEY', ''),
                        'api_secret': os.getenv('BYBIT_API_SECRET', '')
                    },
                    'testnet': False,
                    'rest_endpoint': 'https://api.bybit.com',
                    'websocket': {
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                    }
                }
            }
        }
        
        # Initialize Bybit exchange directly
        bybit = BybitExchange(bybit_config)
        
        # Fetch open interest data directly from exchange
        logger.info("Fetching open interest data directly from exchange")
        oi_data = await bybit.fetch_open_interest_history('BTCUSDT', '15min')
        
        if 'history' in oi_data and oi_data['history']:
            logger.info(f"✅ Got {len(oi_data['history'])} OI history entries from exchange")
            
            # Create a market data structure manually for testing
            market_data = {
                'symbol': 'BTCUSDT',
                'open_interest': {
                    'current': 50000.0,
                    'history': oi_data['history']
                }
            }
            
            # Add direct reference to open interest history for easier access
            market_data['open_interest_history'] = oi_data['history']
            
            logger.info("Manually created market_data structure with open interest")
            
            # Check if we have open interest data
            if 'open_interest' in market_data:
                logger.info("✅ Found open_interest in market data")
                oi_data = market_data['open_interest']
                if isinstance(oi_data, dict):
                    logger.info(f"Open interest data keys: {list(oi_data.keys())}")
                    
                    # Check for history
                    if 'history' in oi_data and oi_data['history']:
                        logger.info(f"✅ Found history in open_interest with {len(oi_data['history'])} entries")
                        logger.info(f"Sample entry: {oi_data['history'][0]}")
                    else:
                        logger.warning("❌ No history found in open_interest")
                else:
                    logger.warning(f"❌ Open interest data is not a dictionary: {type(oi_data)}")
            else:
                logger.warning("❌ No open_interest found in market data")
                
            # Check for direct reference
            if 'open_interest_history' in market_data:
                logger.info("✅ Found direct open_interest_history reference in market data")
                oi_history = market_data['open_interest_history']
                if isinstance(oi_history, list) and oi_history:
                    logger.info(f"✅ Direct reference contains {len(oi_history)} entries")
                    logger.info(f"Sample entry from direct reference: {oi_history[0]}")
                else:
                    logger.warning(f"❌ Direct reference is empty or not a list: {type(oi_history)}")
            else:
                logger.warning("❌ No open_interest_history direct reference found in market data")
        else:
            logger.warning("❌ No open interest history returned from exchange")
            
    except Exception as e:
        logger.error(f"Error in market data integration test: {e}", exc_info=True)

async def main():
    # First test direct API
    await test_direct_api()
    
    print("\n" + "-"*50 + "\n")
    
    # Then test our implementation
    await test_exchange_implementation()
    
    print("\n" + "-"*50 + "\n")
    
    # Finally test market data integration
    await test_market_data_integration()

if __name__ == "__main__":
    asyncio.run(main())
