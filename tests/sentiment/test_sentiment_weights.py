import logging
import sys
import yaml
import json
from typing import Dict, Any

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Import the SentimentIndicator class
from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger

def load_config():
    """Load the main configuration file."""
    try:
        with open('config/config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

# Load the actual config
config = load_config()

# Create a logger
logger = Logger('TEST', 'INFO')

# Create the SentimentIndicators instance with the actual config
sentiment = SentimentIndicators(config, logger)

# Get the config-defined weights
config_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('sentiment', {})

# Print the sentiment component weights from config.yaml
print("\n=== Sentiment Weights from config.yaml ===")
for component, weight in sorted(config_weights.items()):
    print(f"{component}: {weight}")

# Print the weights used by the SentimentIndicators class
print("\n=== Sentiment Weights in SentimentIndicators ===")
for component, weight in sorted(sentiment.component_weights.items()):
    print(f"{component}: {weight:.4f}")

# Create market data with funding rate history for testing volatility
market_data = {
    'sentiment': {
        'funding_rate': 0.0025,  # Current funding rate
        'long_short_ratio': {'long': 0.55, 'short': 0.45},
        'funding_history': [
            {'fundingRate': 0.0020},
            {'fundingRate': 0.0025},
            {'fundingRate': 0.0022},
            {'fundingRate': 0.0018},
            {'fundingRate': 0.0021}
        ]
    }
}

# Calculate the funding rate score (now includes volatility)
print("\n=== Testing Combined Funding Rate Score ===")
funding_score = sentiment._calculate_funding_score(market_data)
print(f"Combined funding rate score: {funding_score:.2f}")
print(f"Internal volatility weight: {sentiment.funding_volatility_weight:.2f}")

# Create sample component scores for overall calculation
component_scores = {
    'funding_rate': funding_score,
    'long_short_ratio': 55.2,
    'liquidations': 48.1,
    'volume_sentiment': 62.7,
    'market_mood': 58.3,
    'risk': 42.9,
}

# Test the _log_component_breakdown method
print("\n=== Testing sentiment component breakdown ===")
sentiment._log_component_breakdown(component_scores)

# Test weighted score calculation
weighted_score = sentiment._compute_weighted_score(component_scores)
print(f"\nFinal weighted score: {weighted_score:.2f}")

# Test the full calculation
print("\n=== Testing full sentiment calculation ===")
result = sentiment._calculate_sync(market_data)
print(f"Overall sentiment score: {result['score']:.2f}")
print("\nComponent scores:")
for component, score in result['components'].items():
    if component != 'sentiment':  # Skip the overall sentiment score
        print(f"  {component}: {score:.2f}")

print("\nWeight mapping test completed successfully!") 