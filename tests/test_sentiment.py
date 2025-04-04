import sys
import os
import time
import json
import logging
import asyncio
from typing import Dict, Any

# Add src to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger

# Use explicit INFO level
logger = Logger(__name__, level=logging.INFO)

async def main():
    """Test the sentiment indicators with sample market data."""
    logger.info("Testing sentiment indicators...")
    
    # Create a basic configuration
    config = {
        'analysis': {
            'indicators': {
                'sentiment': {
                    'parameters': {
                        'sigmoid_transformation': {
                            'default_sensitivity': 0.12,
                            'long_short_sensitivity': 0.12,
                            'funding_sensitivity': 0.15,
                            'liquidation_sensitivity': 0.10
                        }
                    }
                }
            }
        },
        'timeframes': {
            'base': {'interval': '1', 'validation': {'min_candles': 100}, 'weight': 0.4},
            'ltf': {'interval': '5', 'validation': {'min_candles': 100}, 'weight': 0.3},
            'mtf': {'interval': '30', 'validation': {'min_candles': 100}, 'weight': 0.2},
            'htf': {'interval': '240', 'validation': {'min_candles': 100}, 'weight': 0.1}
        }
    }
    
    current_time = int(time.time() * 1000)
    
    # Create sample market data with properly formatted liquidations
    market_data = {
        'symbol': 'BTCUSDT',
        'exchange': 'bybit',
        'timestamp': current_time,
        'ticker': {
            'symbol': 'BTCUSDT',
            'timestamp': current_time,
            'datetime': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'high': 40000.0,
            'low': 39000.0,
            'bid': 39500.0,
            'ask': 39510.0,
            'last': 39500.0,
            'volume': 1000.0,
            'turnover': 39500000.0,
            'mark': 39500.0,
            'index': 39500.0,
            'percentage': 1.5,
            'bid_size': 10.0,
            'ask_size': 10.0,
            'open_interest': 5000.0,
            'open_interest_value': 197500000.0,
            'fundingRate': 0.0001,
            'nextFundingTime': current_time + 8 * 3600 * 1000
        },
        'sentiment': {
            'long_short_ratio': {
                'symbol': 'BTCUSDT',
                'long': 0.6,
                'short': 0.4,
                'timestamp': current_time
            },
            'funding_rate': {
                'rate': 0.0001,
                'next_funding_time': current_time + 8 * 3600 * 1000
            },
            'liquidations': [
                {
                    'side': 'long',
                    'size': 10.0,
                    'price': 39000.0,
                    'timestamp': current_time - 3600 * 1000
                },
                {
                    'side': 'short',
                    'size': 15.0,
                    'price': 40000.0,
                    'timestamp': current_time - 2 * 3600 * 1000
                }
            ],
            'market_mood': {
                'risk_level': 1,
                'max_leverage': 100.0,
                'timestamp': current_time
            },
            'volatility': {
                'value': 0.02,
                'window': 24,
                'timeframe': '5min',
                'timestamp': current_time,
                'trend': 'increasing',
                'period_minutes': 5
            },
            'volume_sentiment': {
                'buy_volume': 600.0,
                'sell_volume': 400.0,
                'timestamp': current_time
            }
        },
        'risk_limit': {
            'symbol': 'BTCUSDT',
            'initialMargin': 0.01,
            'maintenanceMargin': 0.005,
            'currentTier': 1,
            'maxLeverage': 100.0
        }
    }
    
    # Initialize sentiment indicators
    logger.info("Initializing SentimentIndicators...")
    sentiment_indicators = SentimentIndicators(config, logger)
    
    # Run synchronous calculation
    logger.info("Running synchronous calculation...")
    sync_result = sentiment_indicators._calculate_sync(market_data)
    logger.info(f"Sync result score: {sync_result.get('score', 'N/A')}")
    
    component_scores = sync_result.get('components', {})
    if component_scores:
        for component, score in component_scores.items():
            logger.info(f"Component {component}: {score:.2f}")
    
    # Run asynchronous calculation
    logger.info("Running asynchronous calculation...")
    async_result = await sentiment_indicators.calculate(market_data)
    logger.info(f"Async result score: {async_result.get('score', 'N/A')}")
    
    async_component_scores = async_result.get('components', {})
    if async_component_scores:
        for component, score in async_component_scores.items():
            logger.info(f"Async component {component}: {score:.2f}")
    
    # Calculate score directly
    logger.info("Running calculate_score...")
    score = await sentiment_indicators.calculate_score(market_data)
    logger.info(f"Calculate score result: {score:.2f}")
    
    # Get signals
    logger.info("Getting signals...")
    signals = await sentiment_indicators.get_signals(market_data)
    if signals:
        for signal in signals:
            logger.info(f"Signal type: {signal.get('type')}, direction: {signal.get('direction')}, strength: {signal.get('strength'):.2f}")
    else:
        logger.info("No signals generated")
    
    logger.info("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 