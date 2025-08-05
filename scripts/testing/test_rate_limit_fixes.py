#!/usr/bin/env python3
"""Test the Bybit rate limit fixes."""

import asyncio
import sys
import time
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.exchanges.bybit import BybitExchange

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_rate_limits():
    """Test the rate limit implementation."""
    # Create test config
    config = {
        'exchanges': {
            'bybit': {
                'api_key': 'test_key',
                'api_secret': 'test_secret',
                'testnet': True,
                'rest_endpoint': 'https://api-testnet.bybit.com',
                'ws_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear'
            }
        }
    }
    
    try:
        # Initialize exchange
        logger.info("Initializing Bybit exchange with new rate limits...")
        exchange = BybitExchange(config)
        
        # Check the rate limit configuration
        logger.info(f"Global rate limit: {exchange.RATE_LIMITS['global']}")
        logger.info(f"Rate limit status: {exchange.rate_limit_status}")
        
        # Test 1: Verify sliding window implementation
        logger.info("\n=== Test 1: Sliding Window Rate Limiting ===")
        start_time = time.time()
        request_count = 0
        
        # Simulate rapid requests
        async def make_request():
            nonlocal request_count
            await exchange._check_rate_limit('ticker')
            request_count += 1
            
        # Try to make 10 rapid requests
        tasks = []
        for i in range(10):
            tasks.append(make_request())
        
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        logger.info(f"Made {request_count} requests in {elapsed:.2f}s")
        logger.info(f"Requests per second: {request_count/elapsed:.2f}")
        
        # Test 2: Check rate limit status monitoring
        logger.info("\n=== Test 2: Rate Limit Status Monitoring ===")
        if hasattr(exchange, 'get_rate_limit_status'):
            status = exchange.get_rate_limit_status()
            logger.info(f"Rate limit status: {status}")
        else:
            logger.warning("get_rate_limit_status method not found")
        
        # Test 3: Connection pool configuration
        logger.info("\n=== Test 3: Connection Pool Configuration ===")
        if hasattr(exchange, 'connector') and exchange.connector:
            logger.info(f"Connection limit: {exchange.connector.limit}")
            logger.info(f"Connection limit per host: {exchange.connector.limit_per_host}")
        else:
            logger.info("Connector not yet initialized")
        
        # Test 4: Timeout configuration
        logger.info("\n=== Test 4: Timeout Configuration ===")
        if hasattr(exchange, 'timeout') and exchange.timeout:
            logger.info(f"Total timeout: {exchange.timeout.total}s")
            logger.info(f"Connect timeout: {exchange.timeout.connect}s")
            logger.info(f"Socket read timeout: {exchange.timeout.sock_read}s")
        else:
            logger.info("Timeout not yet configured")
        
        # Test 5: Make a real API call to check header tracking
        logger.info("\n=== Test 5: Rate Limit Header Tracking ===")
        await exchange.initialize()
        
        # Make a test API call
        result = await exchange._make_request('GET', '/v5/market/time', {})
        if result.get('retCode') == 0:
            logger.info("API call successful")
            logger.info(f"Rate limit after call: {exchange.rate_limit_status}")
        else:
            logger.warning(f"API call failed: {result}")
        
        logger.info("\n✅ All tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'exchange' in locals() and hasattr(exchange, 'close'):
            await exchange.close()

async def stress_test_rate_limits():
    """Stress test to verify we don't exceed Bybit's limits."""
    logger.info("\n=== Stress Test: 600 requests in 5 seconds ===")
    
    config = {
        'exchanges': {
            'bybit': {
                'api_key': 'test_key',
                'api_secret': 'test_secret',
                'testnet': True,
                'rest_endpoint': 'https://api-testnet.bybit.com',
                'ws_endpoint': 'wss://stream-testnet.bybit.com/v5/public/linear'
            }
        }
    }
    
    exchange = BybitExchange(config)
    
    try:
        # Track requests
        request_times = []
        
        async def timed_request(i):
            start = time.time()
            await exchange._check_rate_limit('ticker')
            end = time.time()
            request_times.append((start, end))
            if i % 100 == 0:
                logger.info(f"Completed {i} requests")
        
        # Try to make 650 requests (should hit limit)
        start_time = time.time()
        tasks = [timed_request(i) for i in range(650)]
        
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        logger.info(f"\nCompleted 650 requests in {total_time:.2f}s")
        
        # Check 5-second windows
        for window_start in range(0, int(total_time), 5):
            window_end = window_start + 5
            window_requests = sum(1 for start, _ in request_times 
                                if window_start <= start - start_time < window_end)
            logger.info(f"Requests in {window_start}-{window_end}s window: {window_requests}")
            
            if window_requests > 600:
                logger.error(f"❌ EXCEEDED LIMIT: {window_requests} > 600!")
            else:
                logger.info(f"✅ Within limit: {window_requests} <= 600")
        
    finally:
        if hasattr(exchange, 'close'):
            await exchange.close()

async def main():
    """Run all tests."""
    await test_rate_limits()
    await stress_test_rate_limits()

if __name__ == "__main__":
    asyncio.run(main())