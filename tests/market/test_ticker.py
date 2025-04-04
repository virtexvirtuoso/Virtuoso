import json
import sys
import logging
import time

# Path to our implementation
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.core.market.market_data_manager import MarketDataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Create a simple mock for testing
class MockConfig:
    def __init__(self):
        self.config = {
            'market_data': {
                'cache': {
                    'enabled': True,
                    'data_ttl': 60
                },
                'websocket_update_throttle': 5
            }
        }
    def get(self, key, default=None):
        parts = key.split('.')
        current = self.config
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return default
        return current

# Mock exchange manager
class MockExchangeManager:
    async def get_primary_exchange(self):
        return None

# Create test cases
def run_test():
    # Create mock objects
    config = MockConfig()
    exchange_manager = MockExchangeManager()
    
    # Initialize the MarketDataManager
    data_manager = MarketDataManager(config, exchange_manager)
    
    # Initialize a symbol in the cache
    symbol = 'BTCUSDT'
    data_manager.data_cache[symbol] = {}
    
    # Test case 1: Partial update with just symbol and tickDirection
    print('\nTest Case 1: Partial update with symbol and tickDirection')
    test_data1 = {'symbol': 'BTCUSDT', 'tickDirection': 'ZeroMinusTick'}
    data_manager._update_ticker_from_ws(symbol, test_data1)
    print(f'Ticker after update 1: {json.dumps(data_manager.data_cache[symbol].get("ticker", {}))}')
    
    # Test case 2: Update with symbol and indexPrice
    print('\nTest Case 2: Update with symbol and indexPrice')
    test_data2 = {'symbol': 'BTCUSDT', 'indexPrice': '86988.98'}
    data_manager._update_ticker_from_ws(symbol, test_data2)
    print(f'Ticker after update 2: {json.dumps(data_manager.data_cache[symbol].get("ticker", {}))}')
    
    # Test case 3: Update with markPrice, openInterestValue, etc.
    print('\nTest Case 3: Update with multiple fields')
    test_data3 = {'symbol': 'BTCUSDT', 'markPrice': '86946.67', 'openInterestValue': '4597351953.56'}
    data_manager._update_ticker_from_ws(symbol, test_data3)
    print(f'Ticker after update 3: {json.dumps(data_manager.data_cache[symbol].get("ticker", {}))}')
    
    # Test case 4 - test from logs
    print('\nTest Case 4: Actual messages from logs')
    test_cases = [
        {'symbol': 'SUIUSDT', 'tickDirection': 'ZeroMinusTick'},
        {'symbol': 'SUIUSDT', 'indexPrice': '2.48842'},
        {'symbol': 'BTCUSDT', 'markPrice': '86946.67', 'indexPrice': '86988.98', 'openInterestValue': '4597351953.56'},
        {'symbol': 'WALUSDT', 'markPrice': '0.5857', 'openInterestValue': '20896980.03'},
        {'symbol': 'WALUSDT', 'tickDirection': 'ZeroMinusTick'},
        {'symbol': 'WALUSDT', 'markPrice': '0.5857', 'indexPrice': '0.5864', 'openInterestValue': '20896980.03'},
        {'symbol': 'ADAUSDT', 'markPrice': '0.6933', 'indexPrice': '0.6937', 'openInterest': '153288559', 'openInterestValue': '106274957.95'},
        {'symbol': 'ACTUSDT', 'tickDirection': 'ZeroPlusTick'},
        {'symbol': 'ACTUSDT', 'indexPrice': '0.0561'}
    ]
    
    for i, test_case in enumerate(test_cases):
        test_symbol = test_case['symbol']
        if test_symbol not in data_manager.data_cache:
            data_manager.data_cache[test_symbol] = {}
        
        print(f"\nProcessing test case 4.{i+1}: {test_case}")
        data_manager._update_ticker_from_ws(test_symbol, test_case)
        print(f'Ticker: {json.dumps(data_manager.data_cache[test_symbol].get("ticker", {}))}')
    
    print("\nAll tests completed successfully")
    return "Tests completed"

if __name__ == '__main__':
    run_test()
