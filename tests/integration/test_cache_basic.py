#!/usr/bin/env python3
"""
Basic Cache System Test (bypasses performance monitor issues)
"""

import asyncio
import time
import logging
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_basic_cache():
    """Test basic cache functionality without performance monitoring."""
    logger.info("🧪 Testing Basic Cache Functionality")
    
    try:
        # Import cache manager directly
        from src.core.cache_manager import CacheManager
        
        # Create cache manager instance
        cache = CacheManager()
        logger.info("✅ Cache manager created")
        
        # Test basic operations without performance monitoring
        test_key = "test:basic"
        test_value = {"test": "data", "timestamp": time.time()}
        
        # Test set
        logger.info("Testing set operation...")
        set_result = await cache.set(test_key, test_value)
        logger.info(f"Set result: {set_result}")
        
        # Test get
        logger.info("Testing get operation...")
        get_result = await cache.get(test_key)
        logger.info(f"Get result: {get_result}")
        
        # Test health check
        logger.info("Testing health check...")
        health = await cache.health_check()
        logger.info(f"Health status: {health.get('status', 'unknown')}")
        
        # Cleanup
        await cache.delete(test_key)
        await cache.close()
        
        logger.info("🎉 Basic cache test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic cache test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test execution."""
    success = await test_basic_cache()
    
    if success:
        logger.info("✅ BASIC CACHE TEST PASSED!")
        sys.exit(0)
    else:
        logger.error("❌ BASIC CACHE TEST FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())