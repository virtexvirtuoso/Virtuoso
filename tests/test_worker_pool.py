#!/usr/bin/env python3
"""
Test script for Worker Pool Manager
"""
import asyncio
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.worker_pool_manager import WorkerPoolManager, calculate_confluence_indicators
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_worker_pool():
    """Test the worker pool functionality."""
    logger.info("Starting Worker Pool test...")
    
    # Initialize worker pool
    manager = WorkerPoolManager(num_workers=2)
    
    # Register functions
    manager.register_function('calculate_confluence', calculate_confluence_indicators)
    
    # Start the pool
    await manager.start()
    logger.info("Worker pool started")
    
    # Test data
    test_market_data = {
        'candles': [
            {'close': 100 + i * 0.5} for i in range(50)
        ],
        'volume': {
            'current': 1500000,
            'average': 1000000,
            'trend': [900000, 1000000, 1200000, 1500000]
        },
        'orderbook': {
            'bids': [[99.5, 100], [99.4, 200], [99.3, 150], [99.2, 300], [99.1, 250]],
            'asks': [[100.5, 120], [100.6, 180], [100.7, 200], [100.8, 250], [100.9, 300]]
        }
    }
    
    # Test single task
    logger.info("Testing single task...")
    start_time = time.time()
    result = await manager.submit_task('calculate_confluence', test_market_data)
    single_time = time.time() - start_time
    logger.info(f"Single task completed in {single_time:.3f}s")
    logger.info(f"Result: {result}")
    
    # Test multiple tasks
    logger.info("\nTesting multiple tasks...")
    test_data_list = [test_market_data for _ in range(10)]
    
    start_time = time.time()
    results = await manager.map_tasks('calculate_confluence', test_data_list)
    multi_time = time.time() - start_time
    
    logger.info(f"Processed {len(results)} tasks in {multi_time:.3f}s")
    logger.info(f"Average time per task: {multi_time/len(results):.3f}s")
    
    # Count successful results
    successful = sum(1 for r in results if not isinstance(r, Exception))
    logger.info(f"Successful: {successful}/{len(results)}")
    
    # Test error handling
    logger.info("\nTesting error handling...")
    try:
        await manager.submit_task('non_existent_function', {})
    except ValueError as e:
        logger.info(f"Correctly caught error: {e}")
    
    # Stop the pool
    await manager.stop()
    logger.info("Worker pool stopped")
    
    return True


async def test_indicator_calculations():
    """Test individual indicator calculations."""
    from src.core.worker_pool_manager import calculate_rsi, calculate_macd, analyze_volume_profile, analyze_orderbook_depth
    
    logger.info("\nTesting indicator calculations...")
    
    # Test RSI
    prices = [100, 102, 101, 103, 104, 102, 105, 106, 104, 107, 108, 106, 109, 110, 108]
    rsi = calculate_rsi(prices)
    logger.info(f"RSI: {rsi:.2f}")
    
    # Test MACD
    prices_long = prices * 3  # Need more data for MACD
    macd_line, signal_line = calculate_macd(prices_long)
    logger.info(f"MACD: {macd_line:.4f}, Signal: {signal_line:.4f}")
    
    # Test Volume Profile
    volume_data = {
        'current': 1500000,
        'average': 1000000,
        'trend': [900000, 1000000, 1200000, 1500000]
    }
    volume_score = analyze_volume_profile(volume_data)
    logger.info(f"Volume Score: {volume_score:.2f}")
    
    # Test Orderbook Analysis
    orderbook = {
        'bids': [[99.5, 100], [99.4, 200], [99.3, 150]],
        'asks': [[100.5, 120], [100.6, 180], [100.7, 200]]
    }
    orderbook_score = analyze_orderbook_depth(orderbook)
    logger.info(f"Orderbook Score: {orderbook_score:.2f}")


if __name__ == "__main__":
    try:
        # Run tests
        asyncio.run(test_worker_pool())
        asyncio.run(test_indicator_calculations())
        
        logger.info("\n✅ All tests passed!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)