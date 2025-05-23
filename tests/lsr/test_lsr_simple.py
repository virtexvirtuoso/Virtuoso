#!/usr/bin/env python3
"""
Simple script to test just the long/short ratio calculations in SentimentIndicators.
This bypasses the exchange implementation to focus on how the data is processed.
"""
import json
import logging
import numpy as np
from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LSR_Simple_Test")

# Sample configuration
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
        '1m': {'interval': '1m', 'limit': 100, 'validation': {'min_candles': 20}},
        '5m': {'interval': '5m', 'limit': 100, 'validation': {'min_candles': 20}},
        '15m': {'interval': '15m', 'limit': 100, 'validation': {'min_candles': 20}},
        '30m': {'interval': '30m', 'limit': 100, 'validation': {'min_candles': 20}},
        '1h': {'interval': '1h', 'limit': 100, 'validation': {'min_candles': 20}},
        '4h': {'interval': '4h', 'limit': 100, 'validation': {'min_candles': 20}},
        '1d': {'interval': '1d', 'limit': 100, 'validation': {'min_candles': 20}}
    }
}

def test_lsr_formats():
    """Test how SentimentIndicators processes different LSR data formats"""
    # Initialize sentiment indicators
    logger_instance = Logger("test_sentiment")
    sentiment = SentimentIndicators(config, logger_instance)
    
    # Test 1: Sample Bybit API format (decimal values)
    bybit_sample = {
        'sentiment': {
            'long_short_ratio': {
                'buyRatio': '0.5189',
                'sellRatio': '0.4811'
            }
        }
    }
    score1 = sentiment.calculate_long_short_ratio(bybit_sample)
    logger.info(f"Test 1 - Bybit Format (buyRatio/sellRatio as strings): Score: {score1}")
    
    # Test 2: Sample Bybit API format (numeric values)
    bybit_sample2 = {
        'sentiment': {
            'long_short_ratio': {
                'buyRatio': 0.5189,
                'sellRatio': 0.4811
            }
        }
    }
    score2 = sentiment.calculate_long_short_ratio(bybit_sample2)
    logger.info(f"Test 2 - Bybit Format (buyRatio/sellRatio as numbers): Score: {score2}")
    
    # Test 3: Sample processed format (0-100 scale)
    processed_sample = {
        'sentiment': {
            'long_short_ratio': {
                'long': 51.89,
                'short': 48.11
            }
        }
    }
    score3 = sentiment.calculate_long_short_ratio(processed_sample)
    logger.info(f"Test 3 - Processed Format (long/short as 0-100): Score: {score3}")
    
    # Test 4: Direct long percentage
    direct_sample = {
        'sentiment': {
            'long_short_ratio': 51.89
        }
    }
    score4 = sentiment.calculate_long_short_ratio(direct_sample)
    logger.info(f"Test 4 - Direct long percentage: Score: {score4}")
    
    # Test 5: Raw Bybit API response format
    raw_bybit_response = {
        'sentiment': {
            'long_short_ratio': {
                'list': [
                    {
                        'symbol': 'BTCUSDT',
                        'buyRatio': '0.5189',
                        'sellRatio': '0.4811',
                        'timestamp': '1746556200000'
                    }
                ]
            }
        }
    }
    score5 = sentiment.calculate_long_short_ratio(raw_bybit_response)
    logger.info(f"Test 5 - Raw Bybit response: Score: {score5}")
    
    # Test a range of values to check for proper handling
    logger.info("\nTesting a range of long-short ratios...")
    test_values = [
        (0.1, 0.9),   # Very bearish
        (0.3, 0.7),   # Moderately bearish
        (0.5, 0.5),   # Neutral
        (0.7, 0.3),   # Moderately bullish
        (0.9, 0.1)    # Very bullish
    ]
    
    for long_ratio, short_ratio in test_values:
        test_data = {
            'sentiment': {
                'long_short_ratio': {
                    'buyRatio': long_ratio,
                    'sellRatio': short_ratio
                }
            }
        }
        score = sentiment.calculate_long_short_ratio(test_data)
        logger.info(f"Long: {long_ratio:.1f}, Short: {short_ratio:.1f} → Score: {score:.1f}")

if __name__ == "__main__":
    test_lsr_formats() 