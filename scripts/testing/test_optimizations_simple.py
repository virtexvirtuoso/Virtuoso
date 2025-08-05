#!/usr/bin/env python3
"""
Simple test for API optimization components.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_imports():
    """Test if all components can be imported."""
    print("Testing imports...")
    
    try:
        from src.core.api_request_queue import APIRequestQueue, RequestPriority
        print("✅ APIRequestQueue imported successfully")
    except Exception as e:
        print(f"❌ Failed to import APIRequestQueue: {e}")
        return False
    
    try:
        from src.core.api_cache_manager import APICacheManager, CacheStrategy
        print("✅ APICacheManager imported successfully")
    except Exception as e:
        print(f"❌ Failed to import APICacheManager: {e}")
        return False
    
    try:
        from src.core.exchanges.bybit_optimized import OptimizedBybitExchange
        print("✅ OptimizedBybitExchange imported successfully")
    except Exception as e:
        print(f"❌ Failed to import OptimizedBybitExchange: {e}")
        return False
    
    return True


async def test_basic_functionality():
    """Test basic functionality of components."""
    print("\nTesting basic functionality...")
    
    # Test Request Queue
    try:
        from src.core.api_request_queue import APIRequestQueue
        queue = APIRequestQueue(max_concurrent=2, rate_limit=5)
        await queue.start()
        print("✅ Request queue started")
        await queue.stop()
        print("✅ Request queue stopped")
    except Exception as e:
        print(f"❌ Request queue test failed: {e}")
        return False
    
    # Test Cache Manager
    try:
        from src.core.api_cache_manager import APICacheManager
        cache = APICacheManager()
        await cache.start()
        print("✅ Cache manager started")
        
        # Test basic cache operation
        await cache.set(
            endpoint="/test",
            method="GET",
            params={},
            headers=None,
            response={'retCode': 0, 'data': 'test'}
        )
        
        result = await cache.get(
            endpoint="/test",
            method="GET",
            params={},
            headers=None
        )
        
        if result and result['data'] == 'test':
            print("✅ Cache operations work")
        else:
            print("❌ Cache operations failed")
            
        await cache.stop()
        print("✅ Cache manager stopped")
    except Exception as e:
        print(f"❌ Cache manager test failed: {e}")
        return False
    
    return True


async def main():
    """Run simple tests."""
    print("🚀 Running Simple Optimization Tests\n")
    
    # Test imports
    if not await test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test basic functionality
    if not await test_basic_functionality():
        print("\n❌ Functionality tests failed")
        return False
    
    print("\n✅ All simple tests passed!")
    print("\nThe optimization components are ready to use.")
    print("\nTo deploy to VPS, run: ./scripts/deploy_api_optimizations.sh")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)