import asyncio
import logging
import sys
import os

# Configure logging to console only
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Mock minimal environment for testing
class MockExchange:
    def __init__(self):
        self.rest_endpoint = "https://api.bybit.com"
    
    async def fetch_ticker(self, *args, **kwargs):
        # Return minimal mock data to avoid real API calls
        return {"last": 50000, "info": {"price24hPcnt": 0.01}}
    
    async def fetch_order_book(self, *args, **kwargs):
        # Return minimal mock data
        return {"bids": [[50000, 1], [49900, 2]], "asks": [[50100, 1], [50200, 2]]}
        
    async def get_markets(self):
        return {}

# Create a simple function to test the market reporter
async def test_market_reporter():
    # Import here to avoid logging configuration issues
    from src.monitoring.market_reporter import MarketReporter
    
    # Create a market reporter with mock exchange
    print("Creating MarketReporter with mock exchange...")
    reporter = MarketReporter(exchange=MockExchange(), logger=logging.getLogger("test"))
    
    # Test generate_market_report with empty input to test the fix
    print("\nTesting generate_market_report with empty input...")
    print("This should use generate_market_summary internally to fill in missing sections")
    try:
        result = await reporter.generate_market_report({})
        print(f"\nResult: {'Success' if result else 'Failed'}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_market_reporter()) 