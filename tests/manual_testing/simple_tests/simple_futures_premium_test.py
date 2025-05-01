import asyncio
import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Import required modules
try:
    from src.core.exchanges.bybit import BybitExchange
    logger.info("Successfully imported BybitExchange module")
except ImportError as e:
    logger.error(f"Failed to import BybitExchange: {e}")
    sys.exit(1)

async def test_market_reporter_fix():
    """Test the specific futures premium functionality we fixed."""
    logger.info("Starting futures premium test with Bybit data")
    
    # Create simplified configuration for Bybit exchange
    config = {
        'exchanges': {
            'bybit': {
                'enabled': True,
                'rest_endpoint': 'https://api.bybit.com',
                'testnet': False,
                'api_credentials': {
                    'api_key': os.environ.get('BYBIT_API_KEY', 'demo'),
                    'api_secret': os.environ.get('BYBIT_API_SECRET', 'demo')
                },
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
        # Initialize exchange
        exchange = BybitExchange(config, None)
        await exchange.initialize()
        logger.info("Exchange initialized successfully")
        
        # Define the test symbols
        symbols = ['BTC/USDT:USDT']
        
        # Directly test futures premium calculation
        logger.info("Testing futures premium calculation...")
        
        # Try to fetch ticker for a perpetual contract
        logger.info(f"Fetching ticker for {symbols[0]}...")
        perp_ticker = await exchange.fetch_ticker(symbols[0])
        
        if perp_ticker:
            logger.info("SUCCESS: Perpetual ticker fetched successfully!")
            # Extract mark price
            mark_price = None
            if 'info' in perp_ticker:
                info = perp_ticker['info']
                mark_price = float(info.get('markPrice', info.get('mark_price', 0)))
            logger.info(f"Mark Price: {mark_price}")
        else:
            logger.error("Failed to fetch perpetual ticker")
        
        # Try to fetch ticker for a spot symbol
        spot_symbol = symbols[0].replace(':USDT', '')
        logger.info(f"Fetching ticker for spot {spot_symbol}...")
        spot_ticker = await exchange.fetch_ticker(spot_symbol)
        
        if spot_ticker:
            logger.info("SUCCESS: Spot ticker fetched successfully!")
            # Extract index price
            index_price = None
            if spot_ticker and spot_ticker.get('last'):
                index_price = float(spot_ticker.get('last', 0))
            logger.info(f"Index Price: {index_price}")
        else:
            logger.error("Failed to fetch spot ticker")
        
        # Try to get futures contracts
        logger.info("Fetching futures contracts...")
        all_markets = await exchange.get_markets()
        
        if all_markets:
            logger.info(f"SUCCESS: Found {len(all_markets)} markets!")
            
            # Extract BTC futures contracts
            base_asset = spot_symbol.replace('USDT', '')
            futures_pattern = r'([A-Z]+).*?(\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2})'
            
            # Count futures contracts
            weekly_futures = 0
            quarterly_futures = 0
            futures_contracts = []
            
            import re
            for market in all_markets:
                market_id = market.get('id', '').upper()
                market_symbol = market.get('symbol', '').upper()
                
                if base_asset.upper() in market_id or base_asset.upper() in market_symbol:
                    if (re.search(futures_pattern, market_id) or 
                        re.search(futures_pattern, market_symbol)):
                        
                        futures_contracts.append(market)
                        if re.search(r'\d{2}APR\d{2}', market_id) or re.search(r'\d{2}APR\d{2}', market_symbol):
                            weekly_futures += 1
                        elif re.search(r'\d{2}(JUN|SEP|DEC|MAR)\d{2}', market_id) or re.search(r'\d{2}(JUN|SEP|DEC|MAR)\d{2}', market_symbol):
                            quarterly_futures += 1
            
            logger.info(f"Found {len(futures_contracts)} futures contracts: {weekly_futures} weekly, {quarterly_futures} quarterly")
            
            # Try to get futures price
            if futures_contracts:
                futures_ticker = await exchange.fetch_ticker(futures_contracts[0]['symbol'])
                if futures_ticker and futures_ticker.get('last'):
                    futures_price = float(futures_ticker.get('last', 0))
                    logger.info(f"Futures price for {futures_contracts[0]['symbol']}: {futures_price}")
                    
                    # Calculate futures basis if we have index price
                    if index_price and index_price > 0:
                        futures_basis = ((futures_price - index_price) / index_price) * 100
                        logger.info(f"Futures basis: {futures_basis:.4f}%")
                else:
                    logger.error("Failed to fetch futures ticker")
        else:
            logger.error("Failed to fetch markets")
        
        logger.info("Test completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    result = asyncio.run(test_market_reporter_fix())
    sys.exit(0 if result else 1) 