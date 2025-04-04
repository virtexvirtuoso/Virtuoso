import logging
import asyncio
from src.indicators.sentiment_indicators import SentimentIndicators

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Test data
test_data = {
    'sentiment': {
        'liquidations': [
            {'side': 'long', 'size': 1000, 'timestamp': 1648000000000},
            {'side': 'short', 'size': 500, 'timestamp': 1648000100000}
        ],
        'market_mood': {
            'social_sentiment': 65.0,
            'fear_and_greed': 45.0,
            'search_trends': 55.0,
            'positive_mentions': 0.6
        },
        'funding_rate': {'rate': -0.001}
    },
    'volume': {'buy_volume_percent': 0.55},
    'trades': [
        {'side': 'buy', 'size': 1.5},
        {'side': 'sell', 'size': 1.0}
    ],
    'risk_limit': {
        'levels': [
            {'starting_margin': 0.02, 'maintain_margin': 0.01, 'limit': 100000},
            {'starting_margin': 0.05, 'maintain_margin': 0.025, 'limit': 1000000}
        ],
        'current_utilization': 0.4
    }
}

# Configuration
config = {
    'timeframes': {
        '1m': {
            'name': '1m',
            'minutes': 1,
            'interval': 1,
            'validation': {'min_candles': 30}
        },
        '5m': {
            'name': '5m',
            'minutes': 5,
            'interval': 5,
            'validation': {'min_candles': 30}
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
                        'liquidation_sensitivity': 0.10
                    }
                }
            }
        }
    }
}

async def run_test():
    # Initialize indicator
    indicator = SentimentIndicators(config)
    
    # Calculate sentiment
    result = await indicator.calculate(test_data)
    print('\nFinal Result:', result)

if __name__ == '__main__':
    asyncio.run(run_test()) 