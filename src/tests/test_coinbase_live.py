import asyncio
import logging
from datetime import datetime
import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.exchanges.coinbase import CoinbaseExchange

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_coinbase_market_data():
    """Test fetching live market data from Coinbase Exchange"""
    try:
        # Initialize exchange with configuration
        config = {
            'api_credentials': {
                'api_key': os.getenv('COINBASE_API_KEY', ''),
                'api_secret': os.getenv('COINBASE_API_SECRET', '')
            },
            'rate_limits': {
                'requests_per_second': 10
            }
        }
        
        exchange = CoinbaseExchange(config)
        await exchange.initialize()
        
        # Test symbols for spot trading
        symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
        
        for symbol in symbols:
            logger.info(f"\nFetching market data for {symbol}...")
            
            try:
                # Fetch market data
                market_data = await exchange.fetch_market_data(symbol)
                
                # Log ticker data
                ticker = market_data['ticker']
                logger.info(f"\n=== {symbol} Ticker ===")
                logger.info(f"Last Price: {ticker['last']}")
                logger.info(f"24h High: {ticker['high']}")
                logger.info(f"24h Low: {ticker['low']}")
                logger.info(f"24h Volume: {ticker['volume']}")
                logger.info(f"24h Change %: {ticker['percentage']}%")
                logger.info(f"Bid/Ask: {ticker['bid']}/{ticker['ask']}")
                
                # Log orderbook data
                orderbook = market_data['orderbook']
                logger.info(f"\n=== {symbol} Orderbook ===")
                if orderbook['bids']:
                    logger.info(f"Top 5 Bids:")
                    for i, bid in enumerate(orderbook['bids'][:5]):
                        logger.info(f"{i+1}. Price: {bid[0]}, Size: {bid[1]}")
                else:
                    logger.info("No bids available")
                    
                if orderbook['asks']:
                    logger.info(f"\nTop 5 Asks:")
                    for i, ask in enumerate(orderbook['asks'][:5]):
                        logger.info(f"{i+1}. Price: {ask[0]}, Size: {ask[1]}")
                else:
                    logger.info("No asks available")
                
                # Calculate orderbook metrics
                if orderbook['bids'] and orderbook['asks']:
                    bid_volume = sum(bid[1] for bid in orderbook['bids'][:5])
                    ask_volume = sum(ask[1] for ask in orderbook['asks'][:5])
                    spread = orderbook['asks'][0][0] - orderbook['bids'][0][0]
                    spread_percentage = (spread / orderbook['asks'][0][0]) * 100
                    
                    logger.info(f"\nOrderbook Analysis:")
                    logger.info(f"Top 5 Levels Bid Volume: {bid_volume:.3f}")
                    logger.info(f"Top 5 Levels Ask Volume: {ask_volume:.3f}")
                    logger.info(f"Spread: {spread:.8f}")
                    logger.info(f"Spread Percentage: {spread_percentage:.4f}%")
                
                # Log recent trades
                trades = market_data['recent_trades']
                logger.info(f"\n=== {symbol} Recent Trades ===")
                if trades:
                    logger.info(f"Last 3 trades:")
                    for i, trade in enumerate(trades[:3]):
                        logger.info(f"{i+1}. Price: {trade['price']}, Size: {trade['amount']}, Side: {trade['side']}")
                    
                    # Calculate trade metrics
                    buy_volume = sum(trade['amount'] for trade in trades if trade['side'] == 'buy')
                    sell_volume = sum(trade['amount'] for trade in trades if trade['side'] == 'sell')
                    total_volume = buy_volume + sell_volume
                    if total_volume > 0:
                        buy_percentage = (buy_volume / total_volume) * 100
                        logger.info(f"\nTrade Analysis:")
                        logger.info(f"Buy Volume: {buy_volume:.3f}")
                        logger.info(f"Sell Volume: {sell_volume:.3f}")
                        logger.info(f"Buy Percentage: {buy_percentage:.2f}%")
                else:
                    logger.info("No recent trades available")
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                continue
                
            logger.info("\n" + "="*50)
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_coinbase_market_data()) 