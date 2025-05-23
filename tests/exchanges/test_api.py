import os
import ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Initializing Bybit exchange...")
        exchange = ccxt.bybit({
            'apiKey': 'TjaG5KducWssxy9Z1m',
            'secret': 'test_api_secret_placeholder',
            'enableRateLimit': True
        })
        
        logger.info("Fetching markets...")
        markets = exchange.fetch_markets()
        logger.info(f"Successfully connected to Bybit. Found {len(markets)} markets.")
        
        try:
            logger.info("Fetching OHLCV data for BTC/USDT...")
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=5)
            logger.info(f"Successfully fetched OHLCV data: {ohlcv}")
        except Exception as e:
            logger.error(f"Error fetching OHLCV: {str(e)}")
    except Exception as e:
        logger.error(f"Error connecting to Bybit: {str(e)}")

if __name__ == "__main__":
    main() 