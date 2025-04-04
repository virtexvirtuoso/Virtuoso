import logging
import sys
from typing import Dict, Any
import json

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Import the SentimentIndicator class
from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger

# Create a minimal config with timeframes to satisfy BaseIndicator
minimal_config = {
    'timeframes': {
        '1m': {'interval': 1, 'validation': {'min_candles': 10}},
        '5m': {'interval': 5, 'validation': {'min_candles': 10}}
    }
}

# Create a logger
logger = Logger('TEST', 'INFO')

# Create the SentimentIndicators instance
sentiment = SentimentIndicators(minimal_config, logger)

# Create sample component scores
component_scores = {
    'funding_rate': 60.5,
    'long_short_ratio': 55.2,
    'liquidations': 48.1,
    'volume_sentiment': 62.7,
    'market_mood': 58.3,
    'risk_score': 42.9,
    'funding_rate_volatility': 51.4
}

# Test the _log_component_breakdown method
print("\nTesting sentiment component breakdown formatting:")
sentiment._log_component_breakdown(component_scores)

print("\nComponent breakdown test completed successfully!") 