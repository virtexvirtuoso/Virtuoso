#!/usr/bin/env python3
"""
Test to verify liquidation cache expiry logic consistency.
"""

import asyncio
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_expiry_logic_consistency():
    """Test that load() and append() handle expiry consistently."""
    from src.utils.liquidation_cache import LiquidationCache
    
    # Create test cache with very short expiry (2 seconds)
    test_cache_dir = tempfile.mkdtemp(prefix="expiry_test_")
    cache = LiquidationCache(cache_dir=test_cache_dir, cache_expiry=2)
    
    logger.info("Testing cache expiry logic consistency...")
    
    try:
        # Add old liquidation that should expire
        old_time = int((datetime.now() - timedelta(seconds=5)).timestamp() * 1000)
        old_liquidation = {
            'symbol': 'TESTUSDT',
            'timestamp': old_time,
            'price': 1000.0,
            'size': 0.1,
            'side': 'long',
            'source': 'test'
        }
        
        cache.append(old_liquidation, 'testusdt')
        logger.info("✅ Added old liquidation to cache")
        
        # Verify it's filtered out when loaded
        liquidations = cache.load('testusdt')
        
        if liquidations is None or len(liquidations) == 0:
            logger.info("✅ load() correctly filtered expired liquidation")
        else:
            logger.error("❌ load() failed to filter expired liquidation")
            return False
        
        # Add fresh liquidation
        fresh_time = int(datetime.now().timestamp() * 1000)
        fresh_liquidation = {
            'symbol': 'TESTUSDT',
            'timestamp': fresh_time,
            'price': 1100.0,
            'size': 0.2,
            'side': 'short',
            'source': 'test'
        }
        
        cache.append(fresh_liquidation, 'testusdt')
        logger.info("✅ Added fresh liquidation to cache")
        
        # Verify fresh liquidation is returned
        liquidations = cache.load('testusdt')
        
        if liquidations and len(liquidations) == 1 and liquidations[0]['side'] == 'short':
            logger.info("✅ load() correctly returned fresh liquidation")
            logger.info(f"   Liquidation: {liquidations[0]}")
            
            # Test mixed scenario - add both old and new liquidations manually
            mixed_data = [
                {
                    'symbol': 'TESTUSDT',
                    'timestamp': int((datetime.now() - timedelta(seconds=10)).timestamp() * 1000),
                    'price': 900.0,
                    'size': 0.05,
                    'side': 'long',
                    'source': 'old'
                },
                {
                    'symbol': 'TESTUSDT',
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'price': 1200.0,
                    'size': 0.3,
                    'side': 'short',
                    'source': 'new'
                }
            ]
            
            # Manually create cache file with mixed data
            cache_file = os.path.join(test_cache_dir, "mixedusdt_liquidations.json")
            cache_structure = {
                "timestamp": int(datetime.now().timestamp()),
                "symbol": "mixedusdt",
                "data": mixed_data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_structure, f)
            
            # Test load() with mixed data
            mixed_liquidations = cache.load('mixedusdt')
            
            if mixed_liquidations and len(mixed_liquidations) == 1 and mixed_liquidations[0]['source'] == 'new':
                logger.info("✅ load() correctly filtered mixed expired/fresh liquidations")
                logger.info(f"   Remaining: {len(mixed_liquidations)} liquidations")
                return True
            else:
                logger.error("❌ load() failed to properly filter mixed liquidations")
                if mixed_liquidations:
                    logger.error(f"   Got {len(mixed_liquidations)} liquidations: {mixed_liquidations}")
                return False
        else:
            logger.error("❌ load() failed to return fresh liquidation")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # Cleanup
        if os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
            logger.info("Cleaned up test directory")

async def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Cache Expiry Logic Consistency Test")
    logger.info("=" * 60)
    
    success = await test_expiry_logic_consistency()
    
    if success:
        logger.info("\n🎉 Cache expiry logic consistency test PASSED!")
        logger.info("Both load() and append() methods handle expiry consistently.")
    else:
        logger.info("\n❌ Cache expiry logic consistency test FAILED!")
        logger.info("There are still inconsistencies in expiry handling.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)