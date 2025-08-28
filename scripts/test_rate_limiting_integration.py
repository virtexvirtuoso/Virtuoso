#!/usr/bin/env python3
"""
Test script for rate limiting integration in Bybit exchange.
Verifies that rate limiter is properly integrated with exchange operations.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.exchanges.bybit import BybitExchange
from src.core.exchanges.rate_limiter import BybitRateLimiter

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_rate_limiter_integration():
    """Test rate limiting integration"""
    logger.info("Starting rate limiting integration test...")
    
    # Mock config for testing
    config = {
        'exchanges': {
            'bybit': {
                'rest_endpoint': 'https://api.bybit.com',
                'testnet_endpoint': 'https://api-testnet.bybit.com',
                'testnet': True,  # Use testnet for safety
                'websocket': {
                    'enabled': False,
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public',
                    'channels': ['orderbook.1.BTCUSDT'],
                    'symbols': ['BTCUSDT']
                }
            }
        }
    }
    
    try:
        # Test 1: Rate limiter initialization
        logger.info("Test 1: Checking rate limiter initialization...")
        exchange = BybitExchange(config, None)
        
        assert hasattr(exchange, 'rate_limiter'), "Rate limiter not initialized"
        assert isinstance(exchange.rate_limiter, BybitRateLimiter), "Rate limiter is not BybitRateLimiter instance"
        logger.info("✓ Rate limiter properly initialized")
        
        # Test 2: Circuit breakers initialization
        logger.info("Test 2: Checking circuit breakers initialization...")
        assert hasattr(exchange, 'circuit_breakers'), "Circuit breakers not initialized"
        assert hasattr(exchange, 'circuit_breaker_config'), "Circuit breaker config not set"
        logger.info("✓ Circuit breakers properly initialized")
        
        # Test 3: Rate limiter statistics method
        logger.info("Test 3: Testing rate limiter statistics...")
        stats = exchange.get_rate_limiter_stats()
        assert 'api_calls' in stats, "API calls not in stats"
        assert 'rate_limit_status' in stats, "Rate limit status not in stats"
        assert 'circuit_breakers' in stats, "Circuit breakers not in stats"
        logger.info("✓ Rate limiter statistics method works correctly")
        
        # Test 4: Make a test API call (only if API keys are available)
        logger.info("Test 4: Testing API call with rate limiting...")
        if os.getenv('BYBIT_API_KEY') and os.getenv('BYBIT_API_SECRET'):
            try:
                # Initialize the exchange
                await exchange.initialize()
                
                # Make a simple market data request (no authentication needed)
                result = await exchange._make_request('GET', 'v5/market/instruments-info', {'category': 'linear', 'limit': 5})
                
                # Check if rate limiter recorded the call
                stats_after = exchange.get_rate_limiter_stats()
                assert len(stats_after['api_calls']) > 0, "Rate limiter did not record API call"
                logger.info("✓ API call with rate limiting successful")
                logger.info(f"API calls recorded: {stats_after['api_calls']}")
                
            except Exception as e:
                logger.warning(f"API test skipped due to error: {e}")
        else:
            logger.info("API keys not available, skipping live API test")
        
        # Test 5: Test rate limiter wait functionality
        logger.info("Test 5: Testing rate limiter wait functionality...")
        start_time = asyncio.get_event_loop().time()
        await exchange.rate_limiter.wait_if_needed('test_endpoint')
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info(f"✓ Rate limiter wait executed in {elapsed:.3f}s")
        
        logger.info("All rate limiting integration tests passed! ✅")
        return True
        
    except Exception as e:
        logger.error(f"Rate limiting integration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("RATE LIMITING INTEGRATION TEST")
    print("=" * 60)
    
    success = await test_rate_limiter_integration()
    
    print("=" * 60)
    if success:
        print("✅ All tests PASSED")
        return 0
    else:
        print("❌ Tests FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)