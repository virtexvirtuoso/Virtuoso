import ccxt
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_open_interest():
    """Debug open interest data fetching from exchanges"""
    try:
        # Initialize exchange
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'  # For futures markets with open interest
            }
        })
        
        # Try different symbols
        symbols = ['BTC/USDT', 'ETH/USDT', 'LTC/USDT']
        
        for symbol in symbols:
            logger.info(f"\nDebug open interest for {symbol}")
            
            # Check if fetchOpenInterest exists
            if 'fetchOpenInterest' in dir(exchange) and callable(getattr(exchange, 'fetchOpenInterest')):
                try:
                    logger.info(f"Attempting fetchOpenInterest for {symbol}...")
                    oi_data = exchange.fetchOpenInterest(symbol)
                    logger.info(f"Raw open interest data: {json.dumps(oi_data, indent=2)}")
                    
                    if 'openInterestAmount' in oi_data:
                        logger.info(f"Open interest amount: {oi_data['openInterestAmount']}")
                    else:
                        logger.warning(f"No openInterestAmount field found in data")
                        
                except Exception as e:
                    logger.error(f"Error fetching open interest for {symbol}: {str(e)}")
            else:
                logger.warning("fetchOpenInterest method not available")
            
            # Try alternative methods
            try:
                logger.info(f"\nFetching ticker for {symbol}")
                ticker = exchange.fetch_ticker(symbol)
                logger.info(f"Ticker fields: {list(ticker.keys())}")
                
                if 'openInterest' in ticker:
                    logger.info(f"Open interest from ticker: {ticker['openInterest']}")
                else:
                    logger.warning("No open interest field in ticker")
            except Exception as e:
                logger.error(f"Error fetching ticker: {str(e)}")
            
            # Try futures methods if available
            if hasattr(exchange, 'fapiPublicGetOpenInterest'):
                try:
                    logger.info(f"\nTrying futures API for {symbol}")
                    # Convert symbol to format required by futures API
                    futures_symbol = symbol.replace('/', '')
                    futures_oi = exchange.fapiPublicGetOpenInterest({'symbol': futures_symbol})
                    logger.info(f"Futures API open interest: {json.dumps(futures_oi, indent=2)}")
                except Exception as e:
                    logger.error(f"Error with futures API: {str(e)}")
    
    except Exception as e:
        logger.error(f"General error: {str(e)}")

if __name__ == "__main__":
    debug_open_interest() 