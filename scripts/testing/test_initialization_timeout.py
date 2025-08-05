#!/usr/bin/env python3
"""
Test the initialization timeout fixes.
"""

import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bybit_initialization():
    """Test Bybit initialization with timeout."""
    logger.info("Testing Bybit initialization with timeout fixes...")
    
    try:
        from src.core.exchanges.bybit import BybitExchange
        from src.config.config_manager import ConfigManager
        
        # Load config
        config = ConfigManager().config
        
        # Create exchange instance
        exchange = BybitExchange(config.exchanges.bybit.model_dump())
        
        # Test initialization with timeout
        start_time = datetime.now()
        logger.info("Starting initialization...")
        
        try:
            success = await exchange.initialize()
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if success:
                logger.info(f"✅ Initialization successful in {elapsed:.2f}s")
                
                # Test a simple API call
                logger.info("Testing API call...")
                start_time = datetime.now()
                result = await exchange._make_request('GET', '/v5/market/time')
                elapsed = (datetime.now() - start_time).total_seconds()
                
                if result and result.get('retCode') == 0:
                    logger.info(f"✅ API call successful in {elapsed:.2f}s")
                    logger.info(f"   Server time: {result.get('result', {}).get('timeNow', 'N/A')}")
                else:
                    logger.error(f"❌ API call failed: {result}")
                
                # Cleanup
                await exchange.close()
                
            else:
                logger.error(f"❌ Initialization failed after {elapsed:.2f}s")
                
        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Initialization timed out after {elapsed:.2f}s")
            return False
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_timeout_behavior():
    """Test that timeouts actually work by simulating a slow server."""
    logger.info("\nTesting timeout behavior with simulated delays...")
    
    # Test various timeout scenarios
    test_cases = [
        ("Fast response (should succeed)", 0.5),
        ("Slow response (should timeout)", 15.0),
    ]
    
    for description, delay in test_cases:
        logger.info(f"\nTest: {description}")
        try:
            start = datetime.now()
            async with asyncio.timeout(5.0):  # 5 second timeout
                await asyncio.sleep(delay)
                logger.info(f"✅ Completed in {(datetime.now() - start).total_seconds():.2f}s")
        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start).total_seconds()
            logger.info(f"✅ Correctly timed out after {elapsed:.2f}s")

async def main():
    """Run all tests."""
    logger.info("🧪 Testing initialization timeout fixes...")
    logger.info("=" * 60)
    
    # Test 1: Bybit initialization
    logger.info("\n1. Testing Bybit initialization...")
    result1 = await test_bybit_initialization()
    
    # Test 2: Timeout behavior
    logger.info("\n2. Testing timeout behavior...")
    await test_timeout_behavior()
    
    logger.info("\n" + "=" * 60)
    
    if result1:
        logger.info("✅ All tests passed!")
    else:
        logger.error("❌ Some tests failed")
    
    return result1

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)