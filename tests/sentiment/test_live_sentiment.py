#!/usr/bin/env python
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.exchanges.bybit import BybitExchange
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = Logger('live_sentiment_test')

async def fetch_live_sentiment(symbol='BTCUSDT', use_testnet=False):
    """Fetch and analyze live sentiment data from Bybit."""
    try:
        logger.info(f"Fetching live sentiment data for {symbol}...")
        
        # Initialize exchange configuration
        config = {
            'exchanges': {
                'bybit': {
                    'enabled': True,
                    'name': 'bybit',
                    'api_credentials': {
                        'api_key': os.getenv('BYBIT_API_KEY', ''),
                        'api_secret': os.getenv('BYBIT_API_SECRET', '')
                    },
                    'testnet': use_testnet,
                    'rest_endpoint': 'https://api-testnet.bybit.com' if use_testnet else 'https://api.bybit.com',
                    'websocket': {
                        'enabled': True,
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                        'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear',
                        'channels': ['trade', 'orderbook', 'kline', 'liquidation'],
                        'symbols': [symbol]
                    }
                }
            },
            'analysis': {
                'indicators': {
                    'sentiment': {
                        'parameters': {
                            'sigmoid_transformation': {
                                'default_sensitivity': 0.12,
                                'long_short_sensitivity': 0.12,
                                'funding_sensitivity': 0.15,
                                'liquidation_sensitivity': 0.1
                            }
                        }
                    }
                }
            },
            'timeframes': {
                '1m': {'name': '1m', 'minutes': 1, 'interval': 1, 'validation': {'min_candles': 30}},
                '5m': {'name': '5m', 'minutes': 5, 'interval': 5, 'validation': {'min_candles': 30}}
            }
        }
        
        # Initialize exchange
        exchange = BybitExchange(config, None)
        await exchange.initialize()
        
        # Fetch market data
        market_data = await exchange.fetch_market_data(symbol)
        
        if not market_data:
            logger.error("Failed to fetch market data")
            return None
            
        # Initialize sentiment indicators
        sentiment = SentimentIndicators(config)
        
        # Calculate sentiment
        result = await sentiment.calculate(market_data)
        
        # Log detailed results
        logger.info("\n=== Sentiment Analysis Results ===")
        logger.info(f"Overall Score: {result['score']:.2f}")
        logger.info("\nComponent Scores:")
        for component, score in result['components'].items():
            logger.info(f"{component}: {score:.2f}")
        
        if result['signals']:
            logger.info("\nTrading Signals:")
            for signal in result['signals']:
                logger.info(f"- {signal['signal']} ({signal['strength']}) from {signal['component']}")
                logger.info(f"  Reason: {signal['reason']}")
                logger.info(f"  Confidence: {signal['confidence']:.2f}")
        
        logger.info("\nInterpretation:")
        logger.info(f"Signal: {result['interpretation']['signal']}")
        logger.info(f"Bias: {result['interpretation']['bias']}")
        logger.info(f"Risk Level: {result['interpretation']['risk_level']}")
        logger.info(f"Summary: {result['interpretation']['summary']}")
        
        # Ensure proper cleanup
        await exchange.close()
        return result
        
    except Exception as e:
        logger.error(f"Error in live sentiment analysis: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def main():
    """Main function to run the live sentiment test."""
    # Test with both mainnet and testnet
    networks = [
        ('Mainnet', False, 'BTCUSDT'),
        ('Testnet', True, 'BTCUSDT')
    ]
    
    for network_name, is_testnet, symbol in networks:
        logger.info(f"\nTesting on {network_name} with {symbol}")
        result = await fetch_live_sentiment(symbol, is_testnet)
        if result:
            logger.info(f"{network_name} test completed successfully")
        else:
            logger.error(f"{network_name} test failed")
        
        # Wait between tests
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main()) 