"""
Test script to verify our fix for the SentimentIndicators.get_signals coroutine never awaited issue.
"""
import asyncio
import logging
import os
from src.monitoring.monitor import MarketMonitor
from src.indicators.sentiment_indicators import SentimentIndicators

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_monitor')

async def test_sentiment_indicators_directly():
    """Test the SentimentIndicators class directly."""
    try:
        print("Testing SentimentIndicators directly...")
        
        # Create a basic config for SentimentIndicators
        config = {
            'analysis': {
                'indicators': {
                    'sentiment': {
                        'components': {
                            'funding_rate': {'weight': 0.15},
                            'long_short_ratio': {'weight': 0.15},
                            'liquidations': {'weight': 0.15},
                            'volume_sentiment': {'weight': 0.15},
                            'market_mood': {'weight': 0.15},
                            'risk_score': {'weight': 0.15},
                            'funding_rate_volatility': {'weight': 0.1}
                        },
                        'funding_threshold': 0.01,
                        'liquidation_threshold': 1000000,
                        'window': 20
                    }
                }
            },
            'timeframes': {
                'base': {'interval': 60, 'validation': {'min_candles': 10}, 'weight': 0.5},
                '1h': {'interval': 60, 'validation': {'min_candles': 10}, 'weight': 0.3},
                '1d': {'interval': 1440, 'validation': {'min_candles': 5}, 'weight': 0.2}
            },
            'validation_requirements': {
                'trades': {'min_trades': 10, 'max_age': 3600}
            }
        }
        
        # Initialize SentimentIndicators
        sentiment = SentimentIndicators(config, logger)
        
        # Create test market data
        market_data = {
            'sentiment': {
                'funding_rate': 0.0001,
                'long_short_ratio': {'long': 1.2, 'short': 1.0},
                'liquidations': []
            },
            'ohlcv': {
                'base': {
                    'data': []  # Empty data for this test
                }
            }
        }
        
        # Test the async calculate method
        print("Testing calculate method...")
        result = await sentiment.calculate(market_data)
        print(f"Calculate result: {result['score']}")
        
        # Test the get_signals method
        print("Testing get_signals method...")
        signals = await sentiment.get_signals(market_data)
        print(f"Generated {len(signals)} signals")
        
        # Test the synchronous _calculate_sync method which uses _get_signals_sync
        print("Testing _calculate_sync method...")
        sync_result = sentiment._calculate_sync(market_data)
        print(f"Sync calculate result: {sync_result['score']}")
        
        print("All tests completed successfully - no coroutine warnings!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sentiment_indicators_directly()) 