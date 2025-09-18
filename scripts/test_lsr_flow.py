#!/usr/bin/env python3
"""Test script to verify LSR data flow through the system"""

import json
import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.sentiment_indicators import SentimentIndicators

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_lsr')

def test_lsr_calculation():
    """Test LSR calculation with various data formats"""
    
    # Create config with sentiment weights
    config = {
        'timeframes': {
            '1m': {'periods': 100, 'interval': 1},
            '5m': {'periods': 100, 'interval': 5},
            '30m': {'periods': 100, 'interval': 30},
            '4h': {'periods': 100, 'interval': 240}
        },
        'analysis': {
            'indicators': {
                'sentiment': {}
            }
        },
        'confluence': {
            'weights': {
                'sub_components': {
                    'sentiment': {
                        'long_short_ratio': 0.2,
                        'funding_rate': 0.15,
                        'funding_rate_volatility': 0.1,
                        'liquidation_events': 0.15,
                        'volume_sentiment': 0.2,
                        'market_mood': 0.1,
                        'risk_score': 0.1
                    }
                }
            }
        }
    }
    
    # Initialize sentiment processor
    sentiment_processor = SentimentIndicators(config, logger)
    
    print("\n" + "="*60)
    print("TESTING LSR DATA FLOW")
    print("="*60)
    
    # Test 1: LSR data in sentiment structure (as it comes from Bybit)
    test_data1 = {
        'sentiment': {
            'long_short_ratio': {
                'long': 65.0,
                'short': 35.0,
                'timestamp': 1234567890
            }
        }
    }
    
    print("\nTest 1: LSR in sentiment structure (65% long, 35% short)")
    print(f"Input data: {json.dumps(test_data1['sentiment']['long_short_ratio'], indent=2)}")
    lsr_score1 = sentiment_processor.calculate_long_short_ratio(test_data1)
    print(f"Result: LSR Score = {lsr_score1:.2f}% (Expected: 65.00%)")
    
    # Test 2: LSR data at top level
    test_data2 = {
        'long_short_ratio': {
            'long': 80.0,
            'short': 20.0
        }
    }
    
    print("\nTest 2: LSR at top level (80% long, 20% short)")
    print(f"Input data: {json.dumps(test_data2['long_short_ratio'], indent=2)}")
    lsr_score2 = sentiment_processor.calculate_long_short_ratio(test_data2)
    print(f"Result: LSR Score = {lsr_score2:.2f}% (Expected: 80.00%)")
    
    # Test 3: LSR as tuple/list format
    test_data3 = {
        'sentiment': {
            'long_short_ratio': [45.0, 55.0]  # [long, short]
        }
    }
    
    print("\nTest 3: LSR as list [45, 55]")
    print(f"Input data: {test_data3['sentiment']['long_short_ratio']}")
    lsr_score3 = sentiment_processor.calculate_long_short_ratio(test_data3)
    print(f"Result: LSR Score = {lsr_score3:.2f}% (Expected: 45.00%)")
    
    # Test 4: Missing LSR data (should default to 50/50)
    test_data4 = {
        'sentiment': {}
    }
    
    print("\nTest 4: Missing LSR data")
    print(f"Input data: {test_data4}")
    lsr_score4 = sentiment_processor.calculate_long_short_ratio(test_data4)
    print(f"Result: LSR Score = {lsr_score4:.2f}% (Expected: 50.00% - default)")
    
    # Test 5: Calculate full sentiment score with LSR data
    print("\n" + "="*60)
    print("TESTING FULL SENTIMENT CALCULATION WITH LSR")
    print("="*60)
    
    full_market_data = {
        'sentiment': {
            'long_short_ratio': {
                'long': 70.0,
                'short': 30.0,
                'timestamp': 1234567890
            },
            'funding_rate': {
                'rate': 0.001,
                'next_funding_time': 1234567890
            },
            'liquidations': []
        },
        'ticker': {
            'percentage': 2.5,
            'volume': 1000000
        }
    }
    
    print("\nFull market data with LSR (70/30):")
    print(f"LSR: {full_market_data['sentiment']['long_short_ratio']}")
    
    # Calculate sentiment score
    sentiment_result = sentiment_processor.calculate(full_market_data)
    
    print(f"\nSentiment calculation result:")
    print(f"- Overall score: {sentiment_result.get('score', 'N/A'):.2f}%")
    if 'components' in sentiment_result:
        print(f"- Components:")
        for comp, value in sentiment_result['components'].items():
            if isinstance(value, dict) and 'score' in value:
                print(f"  - {comp}: {value['score']:.2f}%")
            else:
                print(f"  - {comp}: {value}")
    
    # Check if LSR was properly used
    if 'components' in sentiment_result and 'long_short_ratio' in sentiment_result['components']:
        lsr_component = sentiment_result['components']['long_short_ratio']
        if isinstance(lsr_component, dict):
            lsr_score = lsr_component.get('score', lsr_component.get('value', 'N/A'))
        else:
            lsr_score = lsr_component
        print(f"\n✓ LSR component score in sentiment: {lsr_score}")
        if lsr_score != 50.0 and lsr_score != 'N/A':
            print("✓ LSR data is being properly processed!")
        else:
            print("✗ LSR data is defaulting to 50/50 - needs investigation")
    else:
        print("\n✗ LSR component not found in sentiment results")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_lsr_calculation()