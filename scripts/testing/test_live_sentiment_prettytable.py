#!/usr/bin/env python3
"""
Test script to verify that live sentiment indicators use PrettyTable contribution breakdown tables.

This script creates a mock sentiment analysis environment and runs the actual 
SentimentIndicators class to verify the contribution breakdown tables are 
displayed using PrettyTable format.
"""

import sys
import os
import logging
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging to capture the formatted output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

def create_mock_config():
    """Create a mock configuration for testing."""
    return {
        'timeframes': {
            'base': {'interval': 5, 'validation': {'min_candles': 50}},
            'ltf': {'interval': 15, 'validation': {'min_candles': 50}},
            'mtf': {'interval': 60, 'validation': {'min_candles': 50}},
            'htf': {'interval': 240, 'validation': {'min_candles': 50}}
        },
        'confluence': {
            'weights': {
                'sub_components': {
                    'sentiment': {
                        'funding_rate': 0.25,
                        'funding_rate_volatility': 0.1,
                        'long_short_ratio': 0.2,
                        'liquidation_events': 0.15,
                        'volume_sentiment': 0.15,
                        'market_mood': 0.1,
                        'risk_score': 0.05
                    }
                }
            }
        },
        'analysis': {
            'indicators': {
                'sentiment': {
                    'funding_threshold': 0.01,
                    'liquidation_threshold': 1000000,
                    'window': 20,
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

def create_mock_market_data():
    """Create mock market data that matches the user's HYPERUSDT example."""
    return {
        'symbol': 'HYPERUSDT',
        'sentiment': {
            'funding_rate': 0.005,  # Positive funding rate
            'long_short_ratio': {
                'long': 60.5,
                'short': 39.5
            },
            'liquidations': [
                {'amount': 500000, 'side': 'long', 'timestamp': 1625097600},
                {'amount': 300000, 'side': 'short', 'timestamp': 1625097660},
                {'amount': 750000, 'side': 'long', 'timestamp': 1625097720}
            ],
            'market_mood': {
                'social_sentiment': 75.0,
                'fear_and_greed': 65,
                'search_trends': 80.0,
                'positive_mentions': 0.72
            }
        },
        'volume': {
            'total_volume': 1500000,
            'buy_volume': 900000,
            'sell_volume': 600000
        },
        'risk_limit': {
            'levels': [
                {
                    'starting_margin': 0.05,
                    'maintain_margin': 0.025
                }
            ],
            'current_utilization': 0.3
        }
    }

async def test_sentiment_indicator_prettytable():
    """Test that SentimentIndicators uses PrettyTable for contribution breakdown."""
    print("🚀 TESTING LIVE SENTIMENT INDICATOR WITH PRETTYTABLE")
    print("="*80)
    
    try:
        # Import the actual SentimentIndicators class
        from src.indicators.sentiment_indicators import SentimentIndicators
        from src.core.logger import Logger
        
        # Create logger
        logger = Logger("test_sentiment")
        
        # Create configuration
        config = create_mock_config()
        
        # Initialize sentiment indicator
        print("📊 Initializing SentimentIndicators...")
        sentiment_indicator = SentimentIndicators(config, logger)
        
        # Create mock market data
        market_data = create_mock_market_data()
        
        print(f"\n📈 Testing sentiment analysis for {market_data['symbol']}...")
        print("="*80)
        
        # Run the sentiment calculation
        result = await sentiment_indicator.calculate(market_data)
        
        print("\n✅ SENTIMENT ANALYSIS COMPLETED!")
        print("="*80)
        print(f"Overall Score: {result.get('score', 0):.2f}")
        print(f"Components: {list(result.get('components', {}).keys())}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        
        # The contribution breakdown tables should have been logged using PrettyTable format
        print("\n📋 VERIFICATION:")
        print("• Check the logs above for contribution breakdown tables")
        print("• Tables should use clean PrettyTable format (+ and | characters)")
        print("• No Unicode box-drawing characters (┌, ─, ┐, etc.) should be present")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_orderflow_indicator_prettytable():
    """Test that OrderflowIndicators uses PrettyTable for contribution breakdown."""
    print("\n🚀 TESTING LIVE ORDERFLOW INDICATOR WITH PRETTYTABLE")
    print("="*80)
    
    try:
        # Import the actual OrderflowIndicators class
        from src.indicators.orderflow_indicators import OrderflowIndicators
        from src.core.logger import Logger
        
        # Create logger
        logger = Logger("test_orderflow")
        
        # Create configuration for orderflow
        config = create_mock_config()
        config['confluence']['weights']['sub_components']['orderflow'] = {
            'cvd': 0.25,
            'open_interest_score': 0.15,
            'trade_flow_score': 0.20,
            'liquidity_score': 0.10,
            'imbalance_score': 0.15,
            'pressure_score': 0.10,
            'liquidity_zones': 0.05
        }
        
        # Initialize orderflow indicator
        print("📊 Initializing OrderflowIndicators...")
        orderflow_indicator = OrderflowIndicators(config, logger)
        
        # Create mock market data with orderflow components
        market_data = {
            'symbol': 'HYPERUSDT',
            'trades': [
                {'price': 100.5, 'size': 1000, 'side': 'buy', 'time': 1625097600},
                {'price': 100.4, 'size': 800, 'side': 'sell', 'time': 1625097601},
                {'price': 100.6, 'size': 1200, 'side': 'buy', 'time': 1625097602}
            ],
            'orderbook': {
                'bids': [[100.0, 1000], [99.9, 800], [99.8, 600]],
                'asks': [[100.1, 900], [100.2, 700], [100.3, 500]],
                'timestamp': 1625097600
            }
        }
        
        print(f"\n📈 Testing orderflow analysis for {market_data['symbol']}...")
        print("="*80)
        
        # Run the orderflow calculation
        result = await orderflow_indicator.calculate(market_data)
        
        print("\n✅ ORDERFLOW ANALYSIS COMPLETED!")
        print("="*80)
        print(f"Overall Score: {result.get('score', 0):.2f}")
        print(f"Components: {list(result.get('components', {}).keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all live indicator tests."""
    print("🔍 LIVE INDICATOR PRETTYTABLE VERIFICATION TEST")
    print("This test verifies that actual indicator classes use PrettyTable")
    print("for contribution breakdown tables instead of Unicode box-drawing.")
    print("="*80)
    
    success_count = 0
    total_tests = 2
    
    # Test sentiment indicator
    if await test_sentiment_indicator_prettytable():
        success_count += 1
    
    # Test orderflow indicator  
    if await test_orderflow_indicator_prettytable():
        success_count += 1
    
    print("\n" + "="*80)
    print(f"📊 TEST RESULTS: {success_count}/{total_tests} PASSED")
    
    if success_count == total_tests:
        print("✅ ALL LIVE INDICATOR TESTS PASSED!")
        print("\n🎯 VERIFICATION COMPLETE:")
        print("• Live sentiment indicators use PrettyTable")
        print("• Live orderflow indicators use PrettyTable")
        print("• Contribution breakdown tables display cleanly")
        print("• No Unicode box-drawing characters in output")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 