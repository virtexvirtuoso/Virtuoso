#!/usr/bin/env python3
"""
Test script to verify sentiment data validation fixes.

This script tests the fixes for the three warnings:
1. Missing recommended sentiment fields: ['funding_rate']
2. Missing liquidations data, setting defaults
3. Open interest dict missing 'value' field, setting default
"""

import asyncio
import sys
import os
import time
import pandas as pd
import numpy as np
from typing import Dict, Any

# Add the project root to the path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.logger import Logger

class SentimentValidationTester:
    """Test sentiment data validation fixes."""
    
    def __init__(self):
        self.logger = Logger(__name__)
        self.config = {
            'timeframes': {
                'base': {
                    'interval': '1', 
                    'weight': 0.4,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 60
                    }
                },
                'ltf': {
                    'interval': '5', 
                    'weight': 0.3,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 300
                    }
                },
                'mtf': {
                    'interval': '30', 
                    'weight': 0.2,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 1800
                    }
                },
                'htf': {
                    'interval': '240', 
                    'weight': 0.1,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 14400
                    }
                }
            },
            'analysis': {
                'indicators': {
                    'sentiment': {
                        'funding_threshold': 0.01,
                        'liquidation_threshold': 1000000,
                        'window': 20
                    }
                }
            },
            'confluence': {
                'weights': {
                    'components': {
                        'technical': 0.20,
                        'volume': 0.10,
                        'orderflow': 0.25,
                        'sentiment': 0.15,
                        'orderbook': 0.20,
                        'price_structure': 0.10
                    }
                }
            }
        }
        self.confluence_analyzer = ConfluenceAnalyzer(self.config)
    
    def create_test_market_data(self, test_case: str) -> Dict[str, Any]:
        """Create test market data for different scenarios."""
        base_data = {
            'symbol': 'ANIMEUSDT',
            'exchange': 'bybit',
            'timestamp': int(time.time() * 1000),
            'ohlcv': {
                'base': pd.DataFrame({
                    'timestamp': [1749510300000, 1749510360000, 1749510420000],
                    'open': [0.01, 0.0105, 0.0102],
                    'high': [0.011, 0.0108, 0.0105],
                    'low': [0.009, 0.0102, 0.0100],
                    'close': [0.0105, 0.0102, 0.0103],
                    'volume': [1000000, 950000, 1100000]
                })
            },
            'ticker': {
                'last': 0.0105,
                'fundingRate': 0.00005,
                'openInterest': 26904936,
                'nextFundingTime': 1749484800000
            }
        }
        
        if test_case == 'proper_structure':
            # Test case 1: Proper data structure (should pass without warnings)
            base_data['sentiment'] = {
                'funding_rate': {
                    'rate': 0.00005,
                    'next_funding_time': 1749484800000
                },
                'long_short_ratio': {
                    'symbol': 'ANIMEUSDT',
                    'long': 33.63,
                    'short': 66.37,
                    'timestamp': 1749510300000
                },
                'liquidations': {
                    'long': 0.0,
                    'short': 0.0,
                    'total': 0.0,
                    'timestamp': 1749510300000
                },
                'open_interest': {
                    'value': 26904936,
                    'change_24h': 2.5,
                    'timestamp': 1749510300000
                }
            }
        
        elif test_case == 'empty_liquidations':
            # Test case 2: Empty liquidations list (should not warn)
            base_data['sentiment'] = {
                'funding_rate': {
                    'rate': 0.00005,
                    'next_funding_time': 1749484800000
                },
                'long_short_ratio': {
                    'symbol': 'ANIMEUSDT',
                    'long': 33.63,
                    'short': 66.37,
                    'timestamp': 1749510300000
                },
                'liquidations': []  # Empty list - should be accepted
            }
        
        elif test_case == 'missing_oi_value':
            # Test case 3: Open interest without value field (should extract from ticker)
            base_data['sentiment'] = {
                'funding_rate': {
                    'rate': 0.00005,
                    'next_funding_time': 1749484800000
                },
                'long_short_ratio': {
                    'symbol': 'ANIMEUSDT',
                    'long': 33.63,
                    'short': 66.37,
                    'timestamp': 1749510300000
                },
                'liquidations': [],
                'open_interest': {
                    'change_24h': 2.5,
                    'timestamp': 1749510300000
                    # Missing 'value' field - should extract from ticker
                }
            }
        
        elif test_case == 'missing_funding_rate':
            # Test case 4: Actually missing funding rate (should warn)
            base_data['sentiment'] = {
                'long_short_ratio': {
                    'symbol': 'ANIMEUSDT',
                    'long': 33.63,
                    'short': 66.37,
                    'timestamp': 1749510300000
                },
                'liquidations': []
                # Missing funding_rate entirely
            }
        
        return base_data
    
    def test_validation_scenario(self, test_case: str, description: str) -> bool:
        """Test a specific validation scenario."""
        print(f"\n=== Testing: {description} ===")
        self.logger.info(f"\n=== Testing: {description} ===")
        
        # Create test data
        market_data = self.create_test_market_data(test_case)
        
        # Test validation
        try:
            result = self.confluence_analyzer._validate_sentiment_data(market_data)
            print(f"Validation result: {'PASSED' if result else 'FAILED'}")
            self.logger.info(f"Validation result: {'PASSED' if result else 'FAILED'}")
            
            # Check the final sentiment data structure
            sentiment_data = market_data.get('sentiment', {})
            print(f"Final sentiment structure keys: {list(sentiment_data.keys())}")
            self.logger.info(f"Final sentiment structure keys: {list(sentiment_data.keys())}")
            
            if 'funding_rate' in sentiment_data:
                print(f"Funding rate: {sentiment_data['funding_rate']}")
                self.logger.info(f"Funding rate: {sentiment_data['funding_rate']}")
            
            if 'long_short_ratio' in sentiment_data:
                lsr = sentiment_data['long_short_ratio']
                print(f"LSR: long={lsr.get('long')}, short={lsr.get('short')}")
                self.logger.info(f"LSR: long={lsr.get('long')}, short={lsr.get('short')}")
            
            if 'liquidations' in sentiment_data:
                liq = sentiment_data['liquidations']
                if isinstance(liq, list):
                    print(f"Liquidations: list with {len(liq)} entries")
                    self.logger.info(f"Liquidations: list with {len(liq)} entries")
                else:
                    print(f"Liquidations: {liq}")
                    self.logger.info(f"Liquidations: {liq}")
            
            if 'open_interest' in sentiment_data:
                oi = sentiment_data['open_interest']
                print(f"Open Interest: {oi}")
                self.logger.info(f"Open Interest: {oi}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during validation: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all validation tests."""
        self.logger.info("Starting sentiment data validation tests...")
        
        test_cases = [
            ('proper_structure', 'Proper data structure (should pass cleanly)'),
            ('empty_liquidations', 'Empty liquidations list (should not warn)'),
            ('missing_oi_value', 'Missing open interest value (should extract from ticker)'),
            ('missing_funding_rate', 'Actually missing funding rate (should warn)')
        ]
        
        results = {}
        
        for test_case, description in test_cases:
            results[test_case] = self.test_validation_scenario(test_case, description)
        
        # Summary
        self.logger.info("\n=== TEST SUMMARY ===")
        for test_case, result in results.items():
            status = "✓ PASSED" if result else "✗ FAILED"
            self.logger.info(f"{test_case}: {status}")
        
        passed = sum(results.values())
        total = len(results)
        self.logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        return passed == total

def main():
    """Main test function."""
    tester = SentimentValidationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Sentiment validation fixes are working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 