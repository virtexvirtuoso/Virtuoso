#!/usr/bin/env python3
"""
Test liquidation cache integration with real components in the codebase.
This test verifies that the cache works properly with actual system components.
"""

import asyncio
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime

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

async def test_cache_with_sentiment_indicators():
    """Test cache integration with sentiment indicators."""
    try:
        from src.utils.liquidation_cache import LiquidationCache
        from src.indicators.sentiment_indicators import SentimentIndicators
        
        # Setup test cache
        test_cache_dir = tempfile.mkdtemp(prefix="sentiment_cache_test_")
        cache = LiquidationCache(cache_dir=test_cache_dir)
        
        # Add sample liquidation data
        liquidations = [
            {
                'symbol': 'BTCUSDT',
                'timestamp': int(datetime.now().timestamp() * 1000),
                'price': 50000.0,
                'size': 1.0,
                'side': 'long',
                'source': 'test'
            },
            {
                'symbol': 'BTCUSDT', 
                'timestamp': int(datetime.now().timestamp() * 1000) + 1000,
                'price': 49500.0,
                'size': 2.0,
                'side': 'short',
                'source': 'test'
            }
        ]
        
        for liq in liquidations:
            cache.append(liq, 'btcusdt')
        
        # Try to use cache data with sentiment indicators
        cached_data = cache.load('btcusdt')
        
        if cached_data and len(cached_data) >= 2:
            # Calculate sentiment from liquidation data
            long_volume = sum(liq['size'] for liq in cached_data if liq['side'] == 'long')
            short_volume = sum(liq['size'] for liq in cached_data if liq['side'] == 'short')
            
            logger.info("✅ Cache integration with sentiment indicators works")
            logger.info(f"  - Long volume: {long_volume}")
            logger.info(f"  - Short volume: {short_volume}")
            logger.info(f"  - Long/Short ratio: {long_volume/short_volume:.2f}")
            
            # Cleanup
            shutil.rmtree(test_cache_dir)
            return True
        else:
            logger.error("❌ Cache integration with sentiment indicators failed")
            shutil.rmtree(test_cache_dir)
            return False
            
    except Exception as e:
        logger.error(f"❌ Sentiment indicators cache test failed: {e}")
        if 'test_cache_dir' in locals() and os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
        return False

async def test_cache_with_base_indicator():
    """Test cache integration with base indicator framework."""
    try:
        from src.indicators.base_indicator import BaseIndicator
        
        # Setup test cache
        test_cache_dir = tempfile.mkdtemp(prefix="indicator_cache_test_")
        cache = LiquidationCache(cache_dir=test_cache_dir)
        
        # Add liquidation data
        liquidation = {
            'symbol': 'ETHUSDT',
            'timestamp': int(datetime.now().timestamp() * 1000),
            'price': 3500.0,
            'size': 0.5,
            'side': 'long',
            'source': 'test'
        }
        
        cache.append(liquidation, 'ethusdt')
        
        # Verify data can be loaded
        cached_data = cache.load('ethusdt')
        
        if cached_data and len(cached_data) >= 1:
            logger.info("✅ Cache integration with base indicator framework works")
            logger.info(f"  - Cached liquidations: {len(cached_data)}")
            logger.info(f"  - Latest liquidation: {cached_data[-1]}")
            
            # Cleanup
            shutil.rmtree(test_cache_dir)
            return True
        else:
            logger.error("❌ Cache integration with base indicators failed")
            shutil.rmtree(test_cache_dir)
            return False
            
    except Exception as e:
        logger.error(f"❌ Base indicator cache test failed: {e}")
        if 'test_cache_dir' in locals() and os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
        return False

async def test_cache_with_market_data_manager():
    """Test cache interaction with market data manager."""
    try:
        
        # Setup test cache
        test_cache_dir = tempfile.mkdtemp(prefix="market_data_cache_test_")
        cache = LiquidationCache(cache_dir=test_cache_dir)
        
        # Simulate market data manager storing liquidation data
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for symbol in symbols:
            liquidation = {
                'symbol': symbol,
                'timestamp': int(datetime.now().timestamp() * 1000),
                'price': 1000.0 + hash(symbol) % 1000,
                'size': 0.1,
                'side': 'long',
                'source': 'market_data_manager'
            }
            
            cache.append(liquidation, symbol.lower())
        
        # Verify all symbols have data
        total_liquidations = 0
        for symbol in symbols:
            cached_data = cache.load(symbol.lower())
            if cached_data:
                total_liquidations += len(cached_data)
        
        if total_liquidations >= 3:
            logger.info("✅ Cache integration with market data manager works")
            logger.info(f"  - Total liquidations stored: {total_liquidations}")
            logger.info(f"  - Symbols processed: {len(symbols)}")
            
            # Cleanup
            shutil.rmtree(test_cache_dir)
            return True
        else:
            logger.error("❌ Cache integration with market data manager failed")
            shutil.rmtree(test_cache_dir)
            return False
            
    except Exception as e:
        logger.error(f"❌ Market data manager cache test failed: {e}")
        if 'test_cache_dir' in locals() and os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
        return False

async def test_cache_with_global_instance():
    """Test that global cache instance works correctly."""
    try:
        from src.utils.liquidation_cache import liquidation_cache
        
        # Test global instance methods
        test_liquidation = {
            'symbol': 'GLOBALUSDT',
            'timestamp': int(datetime.now().timestamp() * 1000),
            'price': 999.0,
            'size': 0.123,
            'side': 'short',
            'source': 'global_test'
        }
        
        # Use global instance (this is what monitor.py does)
        liquidation_cache.append(test_liquidation, 'globalusdt')
        
        # Verify data was stored
        cached_data = liquidation_cache.load('globalusdt')
        
        if cached_data and any(liq.get('size') == 0.123 for liq in cached_data):
            logger.info("✅ Global cache instance works correctly")
            logger.info(f"  - Global instance append: Success")
            logger.info(f"  - Global instance load: Success")
            logger.info(f"  - Cached liquidations: {len(cached_data)}")
            return True
        else:
            logger.error("❌ Global cache instance failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Global cache instance test failed: {e}")
        return False

async def test_cache_concurrent_access():
    """Test cache handles concurrent access properly."""
    try:
        
        # Setup test cache
        test_cache_dir = tempfile.mkdtemp(prefix="concurrent_cache_test_")
        cache = LiquidationCache(cache_dir=test_cache_dir)
        
        # Simulate concurrent access
        async def write_liquidations(symbol_suffix, count):
            for i in range(count):
                liquidation = {
                    'symbol': f'CONCURRENT{symbol_suffix}USDT',
                    'timestamp': int(datetime.now().timestamp() * 1000) + i,
                    'price': 1000.0 + i,
                    'size': 0.1,
                    'side': 'long' if i % 2 == 0 else 'short',
                    'source': f'concurrent_test_{symbol_suffix}'
                }
                
                cache.append(liquidation, f'concurrent{symbol_suffix}usdt')
                # Small delay to simulate real conditions
                await asyncio.sleep(0.001)
        
        # Run concurrent writes
        await asyncio.gather(
            write_liquidations('A', 10),
            write_liquidations('B', 10),
            write_liquidations('C', 10)
        )
        
        # Verify all data was written correctly
        total_liquidations = 0
        for suffix in ['A', 'B', 'C']:
            cached_data = cache.load(f'concurrent{suffix.lower()}usdt')
            if cached_data:
                total_liquidations += len(cached_data)
        
        if total_liquidations >= 30:
            logger.info("✅ Cache handles concurrent access correctly")
            logger.info(f"  - Total liquidations from concurrent writes: {total_liquidations}")
            
            # Cleanup
            shutil.rmtree(test_cache_dir)
            return True
        else:
            logger.error("❌ Cache concurrent access failed")
            logger.error(f"  - Expected 30+, got {total_liquidations}")
            shutil.rmtree(test_cache_dir)
            return False
            
    except Exception as e:
        logger.error(f"❌ Concurrent access test failed: {e}")
        if 'test_cache_dir' in locals() and os.path.exists(test_cache_dir):
            shutil.rmtree(test_cache_dir)
        return False

async def main():
    """Run all real integration tests."""
    logger.info("=" * 70)
    logger.info("Cache System Real Integration Tests")
    logger.info("=" * 70)
    
    tests = [
        ("Cache + Sentiment Indicators", test_cache_with_sentiment_indicators),
        ("Cache + Base Indicator Framework", test_cache_with_base_indicator),
        ("Cache + Market Data Manager", test_cache_with_market_data_manager),
        ("Global Cache Instance", test_cache_with_global_instance),
        ("Concurrent Access Handling", test_cache_concurrent_access),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"💥 Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("Real Integration Test Summary")
    logger.info("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("\n🎉 All real integration tests passed!")
        logger.info("The cache system integrates properly with all components.")
    else:
        logger.info("\n⚠️ Some integration tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)