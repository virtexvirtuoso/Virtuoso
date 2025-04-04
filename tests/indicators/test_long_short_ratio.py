#!/usr/bin/env python3
"""
Long-Short Ratio Test

This script tests the processing of mock long-short ratio data in the sentiment indicator
to verify that it's being correctly used in sentiment calculation.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
import numpy as np
from pprint import pprint
import time

from src.indicators.sentiment_indicators import SentimentIndicators

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TEST_LSR")

async def test_sentiment_with_mock_lsr_data():
    """Test the sentiment indicator with mock long-short ratio data."""
    print("\n=== Testing Sentiment Indicator with Mock Long-Short Ratio Data ===")
    
    # Create sentiment indicator config
    sentiment_config = {
        # Required timeframes config
        "timeframes": {
            "base": {
                "interval": "5",
                "weight": 0.4,
                "validation": {
                    "min_candles": 50
                }
            },
            "ltf": {
                "interval": "1",
                "weight": 0.2,
                "validation": {
                    "min_candles": 50
                }
            },
            "mtf": {
                "interval": "15",
                "weight": 0.3,
                "validation": {
                    "min_candles": 50
                }
            },
            "htf": {
                "interval": "60",
                "weight": 0.1,
                "validation": {
                    "min_candles": 50
                }
            }
        },
        # Validation requirements
        "validation_requirements": {
            "trades": {
                "min_trades": 50,
                "max_age": 3600
            },
            "orderbook": {
                "min_levels": 10
            }
        },
        # Sentiment-specific configuration
        "analysis": {
            "indicators": {
                "sentiment": {
                    "funding_threshold": 0.01,
                    "liquidation_threshold": 1000000,
                    "window": 20
                }
            }
        },
        # Confluence configuration with high weight on long_short_ratio for testing
        "confluence": {
            "weights": {
                "sub_components": {
                    "sentiment": {
                        "funding_rate": 0.1,
                        "long_short_ratio": 0.4,  # High weight for testing
                        "liquidations": 0.1,
                        "volume": 0.1,
                        "market_mood": 0.1,
                        "risk": 0.2
                    }
                }
            }
        }
    }
    
    sentiment = SentimentIndicators(sentiment_config)
    
    # Create test cases with different long-short ratios
    test_cases = [
        {
            "name": "Neutral LSR (50/50)",
            "symbol": "BTCUSDT",
            "long": 50.0,
            "short": 50.0,
            "expected_score_range": (45, 55)
        },
        {
            "name": "Bullish LSR (70/30)",
            "symbol": "BTCUSDT", 
            "long": 70.0,
            "short": 30.0,
            "expected_score_range": (60, 100)
        },
        {
            "name": "Bearish LSR (30/70)",
            "symbol": "BTCUSDT",
            "long": 30.0,
            "short": 70.0,
            "expected_score_range": (0, 40)
        },
        {
            "name": "Extremely Bullish LSR (90/10)",
            "symbol": "BTCUSDT",
            "long": 90.0,
            "short": 10.0,
            "expected_score_range": (75, 100)
        },
        {
            "name": "Extremely Bearish LSR (10/90)",
            "symbol": "BTCUSDT",
            "long": 10.0,
            "short": 90.0,
            "expected_score_range": (0, 25)
        }
    ]
    
    print("Testing sentiment indicator with different long-short ratio scenarios...")
    
    for test_case in test_cases:
        print(f"\n--- Test Case: {test_case['name']} ---")
        
        # Create mock market data
        market_data = {
            "symbol": test_case["symbol"],
            "ticker": {
                "last": 40000.0,  # Mock BTC price
                "timestamp": int(time.time() * 1000)
            },
            "sentiment": {
                "long_short_ratio": {
                    "symbol": test_case["symbol"],
                    "long": test_case["long"],
                    "short": test_case["short"],
                    "timestamp": int(time.time() * 1000)
                }
            }
        }
        
        print(f"Symbol: {test_case['symbol']}")
        print(f"Long Value: {test_case['long']}")
        print(f"Short Value: {test_case['short']}")
        print(f"Expected Score Range: {test_case['expected_score_range']}")
        
        # Test LSR component calculation directly
        print("\nTesting _calculate_lsr_score method directly:")
        try:
            # Create sentiment data structure with the right format
            # First, let's log the exact data structure being created for the full calculation
            print("\nDEBUG - Original market_data structure:")
            print(f"Keys: {list(market_data.keys())}")
            for key in market_data:
                print(f"  {key}: {type(market_data[key])}")
                if isinstance(market_data[key], dict):
                    print(f"    Sub-keys: {list(market_data[key].keys())}")
            
            # Process market data the same way that calculate would
            processed_data = sentiment._process_sentiment_data(market_data)
            print("\nDEBUG - Processed data structure:")
            print(f"Keys: {list(processed_data.keys())}")
            if 'long_short_ratio' in processed_data:
                print(f"LSR data in processed_data: {processed_data['long_short_ratio']}")
            
            # Now use the processed data for direct calculation - this should match what happens in the full calculation
            print("\nDEBUG - Calling _calculate_lsr_score with processed data")
            lsr_score = sentiment._calculate_lsr_score(processed_data)
            print(f"Long-Short Ratio Score: {lsr_score:.2f}")
            
            # For comparison, also call with the original direct approach
            direct_sentiment_data = {"long_short_ratio": market_data["sentiment"]["long_short_ratio"]}
            print("\nDEBUG - Calling _calculate_lsr_score with direct data")
            direct_lsr_score = sentiment._calculate_lsr_score(direct_sentiment_data)
            print(f"Direct Long-Short Ratio Score: {direct_lsr_score:.2f}")
            
            # Interpret score
            if lsr_score > 60:
                interpretation = "Bullish (more longs than shorts)"
            elif lsr_score < 40:
                interpretation = "Bearish (more shorts than longs)"
            else:
                interpretation = "Neutral positioning"
                
            print(f"Interpretation: {interpretation}")
            
            # Check if score is within expected range
            min_expected, max_expected = test_case["expected_score_range"]
            if min_expected <= lsr_score <= max_expected:
                print("✅ Score is within expected range")
            else:
                print(f"❌ Score {lsr_score:.2f} is outside expected range {test_case['expected_score_range']}")
                
        except Exception as e:
            print(f"Error calculating LSR score: {str(e)}")
        
        # Calculate full sentiment with high weight on LSR
        print("\nCalculating full sentiment with high weight on long_short_ratio:")
        try:
            result = await sentiment.calculate(market_data)
            
            if isinstance(result, dict):
                print(f"Overall Sentiment Score: {result.get('score', 0):.2f}")
                
                # Check if long_short_ratio component is in the result
                components = result.get('components', {})
                if 'long_short_ratio' in components:
                    lsr_component = components['long_short_ratio']
                    print(f"LSR Component Score in Result: {lsr_component:.2f}")
                    
                    # Verify it matches the direct calculation
                    if np.isclose(lsr_component, lsr_score, atol=0.01):
                        print("✅ LSR component score matches direct calculation")
                    else:
                        print(f"❌ LSR component score ({lsr_component:.2f}) doesn't match direct calculation ({lsr_score:.2f})")
                else:
                    print("❌ LSR component not found in result components")
                
                # Print all component scores
                if 'components' in result:
                    print("\nAll Component Scores:")
                    for component, score in result['components'].items():
                        print(f"  {component}: {score:.2f}")
            else:
                print(f"Overall Sentiment Score: {result:.2f}")
                
            # Debug: print the raw data structure to verify LSR is correctly passed
            print("\nDebug - Raw market data being passed:")
            if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:
                print(f"LSR data found in market_data['sentiment']")
            else:
                print("LSR data not found in expected location")
                
        except Exception as e:
            print(f"Error processing sentiment: {str(e)}")
    
    return True

async def main():
    print("=== LONG-SHORT RATIO TEST ===")
    
    # Test sentiment with mock LSR data
    await test_sentiment_with_mock_lsr_data()
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main()) 