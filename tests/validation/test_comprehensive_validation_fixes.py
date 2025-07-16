#!/usr/bin/env python3
"""
Comprehensive test to verify all validation fixes work correctly.
"""
import sys
import os
import logging
import asyncio
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise, only show warnings and errors
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationFixTester:
    """Tests all validation systems to ensure consistent behavior."""
    
    def __init__(self):
        self.logger = logger
        self.test_results = []
        
    def create_test_scenarios(self):
        """Create test scenarios that previously failed validation."""
        
        return [
            {
                'name': 'Empty Ticker Data (API Fetch Failed)',
                'data': {
                    'symbol': 'BTCUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {},  # ← Empty ticker when fetch fails
                    'orderbook': {'bids': [], 'asks': []},
                    'trades': [],
                    'sentiment': {'long_short_ratio': {'long': 50, 'short': 50}},
                    'ohlcv': {},
                    'metadata': {'ticker_success': False}
                },
                'expected_result': True,
                'description': 'Should pass with warnings when ticker is empty'
            },
            {
                'name': 'Partial Ticker Data (Missing Price)',
                'data': {
                    'symbol': 'ETHUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {
                        'volume': 1000000,
                        'high24h': 3100,
                        'low24h': 2900
                        # ← Missing 'lastPrice', 'last', 'price' fields
                    },
                    'orderbook': {'bids': [], 'asks': []},
                    'trades': [],
                    'sentiment': {'long_short_ratio': {'long': 60, 'short': 40}},
                    'ohlcv': {},
                    'metadata': {'ticker_success': True}
                },
                'expected_result': True,
                'description': 'Should pass with warnings when price field is missing'
            },
            {
                'name': 'Alternative Price Field Names',
                'data': {
                    'symbol': 'ADAUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {
                        'close': 0.45,  # ← Uses 'close' instead of 'lastPrice'
                        'volume': 500000
                    },
                    'orderbook': {'bids': [], 'asks': []},
                    'trades': [],
                    'sentiment': {'long_short_ratio': {'long': 55, 'short': 45}},
                    'ohlcv': {},
                    'metadata': {'ticker_success': True}
                },
                'expected_result': True,
                'description': 'Should pass when using alternative price field names'
            },
            {
                'name': 'Minimal Valid Data',
                'data': {
                    'symbol': 'SOLUSDT',  # Only symbol is truly required
                    'exchange': 'bybit'
                },
                'expected_result': True,
                'description': 'Should pass with minimal required data'
            },
            {
                'name': 'Complete Valid Data',
                'data': {
                    'symbol': 'DOGEUSDT',
                    'exchange': 'bybit',
                    'timestamp': 1700000000000,
                    'ticker': {
                        'lastPrice': 0.08,
                        'bid': 0.079,
                        'ask': 0.081,
                        'volume': 2000000
                    },
                    'orderbook': {
                        'bids': [[0.079, 1000]],
                        'asks': [[0.081, 1000]]
                    },
                    'trades': [
                        {'price': 0.08, 'size': 100, 'side': 'buy', 'timestamp': 1700000000000}
                    ],
                    'sentiment': {'long_short_ratio': {'long': 65, 'short': 35}},
                    'ohlcv': {'base': 'mock_dataframe'},
                    'metadata': {'ticker_success': True}
                },
                'expected_result': True,
                'description': 'Should pass with complete valid data'
            }
        ]
    
    def test_bybit_exchange_validation(self, test_data):
        """Test BybitExchange.validate_market_data method."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            
            # Create minimal config for testing
            config = {
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api.bybit.com',
                        'api_key': 'test_key',
                        'secret': 'test_secret',
                        'websocket': {
                            'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                            'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                        },
                        'sandbox': False,
                        'timeout': 30000,
                        'rateLimit': 100
                    }
                }
            }
            
            exchange = BybitExchange(config)
            result = exchange.validate_market_data(test_data)
            return result, None
            
        except Exception as e:
            return False, str(e)
    
    def test_monitor_validator(self, test_data):
        """Test MarketDataValidator._validate_ticker method."""
        try:
            from src.monitoring.monitor import MarketDataValidator
            
            validator = MarketDataValidator()
            
            # Test ticker validation specifically
            if 'ticker' in test_data:
                result = validator._validate_ticker(test_data['ticker'])
                return result, None
            else:
                # If no ticker data, should pass
                return True, None
                
        except Exception as e:
            return False, str(e)
    
    def test_base_exchange_validation(self, test_data):
        """Test BaseExchange.validate_market_data method."""
        try:
            from src.core.exchanges.base import BaseExchange
            
            # Create a mock implementation since BaseExchange is abstract
            class MockExchange(BaseExchange):
                async def initialize(self): return True
                async def health_check(self): return True
                def sign(self, *args, **kwargs): return ('', {}, {}, {})
                def parse_trades(self, response): return {}
                def parse_orderbook(self, response): return {}
                def parse_ticker(self, response): return {}
                def parse_ohlcv(self, response): return {}
                def parse_balance(self, response): return {}
                def parse_order(self, response): return {}
                async def connect_ws(self): return True
                async def subscribe_ws(self, *args, **kwargs): return True
                async def get_markets(self): return []
                async def fetch_market_data(self, symbol): return {}
            
            exchange = MockExchange({})
            exchange.validate_market_data(test_data)  # This raises exception on failure
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def test_data_validator(self, test_data):
        """Test DataValidator.validate_market_data method."""
        try:
            from src.utils.validation import DataValidator
            
            result = DataValidator.validate_market_data(test_data)
            return result, None
            
        except Exception as e:
            return False, str(e)
    
    async def run_comprehensive_tests(self):
        """Run comprehensive tests on all validation systems."""
        
        print("🧪 **COMPREHENSIVE VALIDATION FIXES TEST**\n")
        
        test_scenarios = self.create_test_scenarios()
        
        validation_systems = [
            ('BybitExchange.validate_market_data', self.test_bybit_exchange_validation),
            ('MarketDataValidator._validate_ticker', self.test_monitor_validator),
            ('BaseExchange.validate_market_data', self.test_base_exchange_validation),
            ('DataValidator.validate_market_data', self.test_data_validator)
        ]
        
        overall_success = True
        
        for scenario in test_scenarios:
            print(f"**Testing Scenario: {scenario['name']}**")
            print(f"Description: {scenario['description']}")
            
            scenario_success = True
            
            for system_name, test_func in validation_systems:
                try:
                    result, error = test_func(scenario['data'])
                    
                    if result == scenario['expected_result']:
                        print(f"  ✅ {system_name}: PASS")
                    else:
                        print(f"  ❌ {system_name}: FAIL (expected {scenario['expected_result']}, got {result})")
                        if error:
                            print(f"     Error: {error}")
                        scenario_success = False
                        overall_success = False
                        
                except Exception as e:
                    print(f"  ❌ {system_name}: ERROR - {str(e)}")
                    scenario_success = False
                    overall_success = False
            
            if scenario_success:
                print(f"  🎯 Scenario Result: ✅ ALL SYSTEMS CONSISTENT\n")
            else:
                print(f"  🎯 Scenario Result: ❌ INCONSISTENT BEHAVIOR\n")
        
        return overall_success
    
    def demonstrate_before_after(self):
        """Demonstrate the before/after behavior of validation fixes."""
        
        print("=== Before/After Validation Behavior ===\n")
        
        print("**BEFORE (Strict Validation):**")
        print("❌ Empty ticker data → ValidationError: Missing required field: price")
        print("❌ Alternative price fields → ValidationError: Missing required field: lastPrice")
        print("❌ Partial data → ValidationError: Missing required fields")
        print("❌ API failures → System stops processing")
        print()
        
        print("**AFTER (Flexible Validation):**")
        print("✅ Empty ticker data → Warning logged, processing continues")
        print("✅ Alternative price fields → Detected and used (close, mark, etc.)")
        print("✅ Partial data → Warnings for missing recommended fields")
        print("✅ API failures → Graceful degradation with default values")
        print()

async def main():
    """Run the comprehensive validation test."""
    
    tester = ValidationFixTester()
    
    tester.demonstrate_before_after()
    
    success = await tester.run_comprehensive_tests()
    
    if success:
        print("🎉 **ALL VALIDATION SYSTEMS NOW CONSISTENT!**")
        print("\n📋 **Summary of Fixes Applied:**")
        print("1. ✅ MarketDataValidator._validate_ticker - Now uses flexible price field detection")
        print("2. ✅ BaseExchange.validate_market_data - Now separates core vs recommended fields")
        print("3. ✅ DataValidator.validate_market_data - Now warns instead of failing")
        print("4. ✅ BybitExchange.validate_market_data - Already had flexible validation")
        print("\n🚀 **Expected Improvements:**")
        print("• No more 'Missing required field: price' errors")
        print("• System continues processing with partial data")
        print("• Better error messages with actionable context")
        print("• Consistent behavior across all validation systems")
    else:
        print("❌ **VALIDATION INCONSISTENCIES STILL EXIST**")
        print("Some validation systems are still using different logic.")
        print("Review the test results above for specific issues.")

if __name__ == "__main__":
    asyncio.run(main()) 