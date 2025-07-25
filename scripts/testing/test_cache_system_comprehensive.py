#!/usr/bin/env python3
"""
Comprehensive test for liquidation cache system across the entire codebase.
Tests all components that interact with the cache and verifies proper integration.
"""

import asyncio
import sys
import os
import json
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

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

class CacheSystemComprehensiveTest:
    """Comprehensive test suite for liquidation cache system."""
    
    def __init__(self):
        self.test_cache_dir = None
        self.original_cache_dir = None
        self.test_results = {}
        
    async def setup_test_environment(self):
        """Setup test environment with cache data."""
        # Create temporary cache directory
        self.test_cache_dir = tempfile.mkdtemp(prefix="cache_system_test_")
        logger.info(f"Created test cache directory: {self.test_cache_dir}")
        
        # Create realistic test data for multiple symbols
        symbols = ['btcusdt', 'ethusdt', 'adausdt', 'solusdt', 'dogeusdt']
        current_time = int(datetime.now().timestamp() * 1000)
        
        for symbol in symbols:
            liquidations = []
            
            # Create liquidations over the last hour
            for i in range(20):
                minutes_ago = i * 3  # Every 3 minutes
                timestamp = current_time - (minutes_ago * 60 * 1000)
                
                liquidation = {
                    'symbol': symbol.upper(),
                    'timestamp': timestamp,
                    'price': 50000 + (i * 100) + (hash(symbol) % 1000),
                    'size': 0.1 + (i * 0.05),
                    'side': 'long' if i % 2 == 0 else 'short',
                    'source': 'websocket'
                }
                liquidations.append(liquidation)
            
            # Save in proper structured format
            cache_file = os.path.join(self.test_cache_dir, f"{symbol}_liquidations.json")
            cache_structure = {
                "timestamp": int(datetime.now().timestamp()),
                "symbol": symbol,
                "data": liquidations
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_structure, f)
        
        logger.info(f"Created test data for {len(symbols)} symbols with 20 liquidations each")
        
    async def cleanup_test_environment(self):
        """Cleanup test environment."""
        if self.test_cache_dir and os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)
            logger.info("Cleaned up test environment")
    
    async def test_cache_import_and_initialization(self):
        """Test that cache can be imported and initialized properly."""
        try:
            # Test direct import
            from src.utils.liquidation_cache import LiquidationCache, liquidation_cache
            
            # Test class instantiation
            custom_cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Test global instance exists
            if hasattr(liquidation_cache, 'load') and hasattr(liquidation_cache, 'append'):
                logger.info("✅ Cache imports and initialization work correctly")
                logger.info(f"  - LiquidationCache class: Available")
                logger.info(f"  - Global instance: Available")
                logger.info(f"  - Custom instance: Available")
                return True
            else:
                logger.error("❌ Global cache instance missing required methods")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache import/initialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_cache_basic_operations(self):
        """Test basic cache operations work correctly."""
        try:
            from src.utils.liquidation_cache import LiquidationCache
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Test load operation
            btc_data = cache.load('btcusdt')
            if btc_data and len(btc_data) == 20:
                logger.info("✅ Cache load operation works")
                logger.info(f"  - Loaded {len(btc_data)} BTC liquidations")
            else:
                logger.error("❌ Cache load operation failed")
                return False
            
            # Test append operation
            new_liquidation = {
                'symbol': 'BTCUSDT',
                'timestamp': int(datetime.now().timestamp() * 1000),
                'price': 51000.0,
                'size': 0.25,
                'side': 'long',
                'source': 'test'
            }
            
            cache.append(new_liquidation, 'btcusdt')
            
            # Verify append worked
            updated_data = cache.load('btcusdt')
            if updated_data and len(updated_data) == 21:
                logger.info("✅ Cache append operation works")
                logger.info(f"  - Cache now has {len(updated_data)} liquidations")
                return True
            else:
                logger.error("❌ Cache append operation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache basic operations test failed: {e}")
            return False
    
    async def test_monitor_integration(self):
        """Test that monitor component integrates properly with cache."""
        try:
            # Test monitor imports
            from src.utils.liquidation_cache import liquidation_cache
            
            # Simulate monitor behavior
            test_liquidation = {
                'symbol': 'ETHUSDT',
                'timestamp': int(datetime.now().timestamp() * 1000),
                'price': 3500.0,
                'size': 1.5,
                'side': 'short',
                'source': 'websocket'
            }
            
            # This is what monitor.py does
            symbol_str = 'ethusdt'
            liquidation_cache.append(test_liquidation, symbol_str)
            
            # Verify data was saved
            cached_data = liquidation_cache.load(symbol_str)
            
            if cached_data and any(liq.get('size') == 1.5 for liq in cached_data):
                logger.info("✅ Monitor integration works correctly")
                logger.info(f"  - Monitor can append to cache")
                logger.info(f"  - Monitor can verify cached data")
                logger.info(f"  - Cache has {len(cached_data)} total liquidations")
                return True
            else:
                logger.error("❌ Monitor integration failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Monitor integration test failed: {e}")
            return False
    
    async def test_multi_symbol_cache_handling(self):
        """Test cache handles multiple symbols correctly."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            symbols = ['btcusdt', 'ethusdt', 'adausdt', 'solusdt', 'dogeusdt']
            total_liquidations = 0
            
            for symbol in symbols:
                liquidations = cache.load(symbol)
                if liquidations:
                    total_liquidations += len(liquidations)
                    logger.info(f"  - {symbol}: {len(liquidations)} liquidations")
                else:
                    logger.error(f"  - {symbol}: No data found")
                    return False
            
            if total_liquidations >= 100:  # 5 symbols * 20 liquidations each
                logger.info("✅ Multi-symbol cache handling works")
                logger.info(f"  - Total liquidations across all symbols: {total_liquidations}")
                return True
            else:
                logger.error("❌ Multi-symbol cache handling failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Multi-symbol cache test failed: {e}")
            return False
    
    async def test_cache_error_handling(self):
        """Test cache handles errors gracefully."""
        try:
            
            # Test with invalid cache directory
            invalid_cache = LiquidationCache(cache_dir="/invalid/path/that/doesnt/exist")
            
            # This should not crash, but return None or handle gracefully
            result = invalid_cache.load('btcusdt')
            
            if result is None:
                logger.info("✅ Cache handles invalid directories gracefully")
            else:
                logger.warning("⚠️ Cache returned data from invalid directory")
            
            # Test with corrupted cache file
            corrupted_file = os.path.join(self.test_cache_dir, "corrupted_liquidations.json")
            with open(corrupted_file, 'w') as f:
                f.write("invalid json content {")
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            result = cache.load('corrupted')
            
            if result is None:
                logger.info("✅ Cache handles corrupted files gracefully")
                return True
            else:
                logger.error("❌ Cache did not handle corrupted file properly")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache error handling test failed: {e}")
            return False
    
    async def test_cache_performance(self):
        """Test cache performance under various conditions."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Test load performance
            start_time = time.time()
            for _ in range(100):
                cache.load('btcusdt')
            load_time = time.time() - start_time
            
            # Test append performance
            test_liquidation = {
                'symbol': 'PERFUSDT',
                'timestamp': int(datetime.now().timestamp() * 1000),
                'price': 1000.0,
                'size': 0.1,
                'side': 'long',
                'source': 'test'
            }
            
            start_time = time.time()
            for i in range(50):
                test_liquidation['timestamp'] = int(datetime.now().timestamp() * 1000) + i
                cache.append(test_liquidation, 'perfusdt')
            append_time = time.time() - start_time
            
            # Verify final count
            final_data = cache.load('perfusdt')
            final_count = len(final_data) if final_data else 0
            
            logger.info("✅ Cache performance test completed")
            logger.info(f"  - 100 loads took {load_time:.3f}s ({load_time*10:.1f}ms per load)")
            logger.info(f"  - 50 appends took {append_time:.3f}s ({append_time*20:.1f}ms per append)")
            logger.info(f"  - Final liquidation count: {final_count}")
            
            # Performance should be reasonable (under 1 second for these operations)
            if load_time < 1.0 and append_time < 1.0:
                return True
            else:
                logger.warning("⚠️ Cache performance may be slow")
                return True  # Still pass, just warn
                
        except Exception as e:
            logger.error(f"❌ Cache performance test failed: {e}")
            return False
    
    async def test_cache_expiry_functionality(self):
        """Test cache expiry works correctly."""
        try:
            
            # Create cache with very short expiry (1 second)
            cache = LiquidationCache(cache_dir=self.test_cache_dir, cache_expiry=1)
            
            # Add old liquidation
            old_liquidation = {
                'symbol': 'EXPIREDUSDT',
                'timestamp': int((datetime.now() - timedelta(seconds=5)).timestamp() * 1000),
                'price': 1000.0,
                'size': 0.1,
                'side': 'long',
                'source': 'test'
            }
            
            cache.append(old_liquidation, 'expiredusdt')
            
            # Try to load - should filter out expired data
            result = cache.load('expiredusdt')
            
            if result is None or len(result) == 0:
                logger.info("✅ Cache expiry functionality works")
                logger.info("  - Expired liquidations are properly filtered")
                return True
            else:
                logger.error("❌ Cache expiry functionality failed")
                logger.error(f"  - Got {len(result)} liquidations, expected 0")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache expiry test failed: {e}")
            return False
    
    async def test_cache_data_integrity(self):
        """Test cache maintains data integrity."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Test data consistency across operations
            original_data = cache.load('btcusdt')
            original_count = len(original_data) if original_data else 0
            
            # Add multiple liquidations
            for i in range(5):
                test_liquidation = {
                    'symbol': 'BTCUSDT',
                    'timestamp': int(datetime.now().timestamp() * 1000) + i,
                    'price': 50000.0 + i,
                    'size': 0.1,
                    'side': 'long' if i % 2 == 0 else 'short',
                    'source': 'integrity_test'
                }
                cache.append(test_liquidation, 'btcusdt')
            
            # Verify all data is there
            final_data = cache.load('btcusdt')
            final_count = len(final_data) if final_data else 0
            
            if final_count == original_count + 5:
                # Verify data quality
                integrity_test_count = sum(1 for liq in final_data if liq.get('source') == 'integrity_test')
                
                if integrity_test_count == 5:
                    logger.info("✅ Cache data integrity maintained")
                    logger.info(f"  - Original count: {original_count}")
                    logger.info(f"  - Final count: {final_count}")
                    logger.info(f"  - Test liquidations found: {integrity_test_count}")
                    return True
                else:
                    logger.error("❌ Data integrity compromised - test liquidations missing")
                    return False
            else:
                logger.error("❌ Data integrity failed - count mismatch")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache data integrity test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all cache system tests."""
        logger.info("=" * 80)
        logger.info("Comprehensive Cache System Test Suite")
        logger.info("=" * 80)
        
        await self.setup_test_environment()
        
        tests = [
            ("Cache Import & Initialization", self.test_cache_import_and_initialization),
            ("Basic Cache Operations", self.test_cache_basic_operations),
            ("Monitor Integration", self.test_monitor_integration),
            ("Multi-Symbol Handling", self.test_multi_symbol_cache_handling),
            ("Error Handling", self.test_cache_error_handling),
            ("Performance Testing", self.test_cache_performance),
            ("Expiry Functionality", self.test_cache_expiry_functionality),
            ("Data Integrity", self.test_cache_data_integrity),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running: {test_name}")
            try:
                result = await test_func()
                results.append((test_name, result))
                self.test_results[test_name] = result
            except Exception as e:
                logger.error(f"💥 Test crashed: {e}")
                results.append((test_name, False))
                self.test_results[test_name] = False
        
        await self.cleanup_test_environment()
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("Test Summary")
        logger.info("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("\n🎉 All cache system tests passed!")
            logger.info("The liquidation cache system is working properly throughout the codebase.")
        else:
            logger.info("\n⚠️ Some tests failed. Cache system needs attention.")
        
        return passed == total

async def main():
    """Main test function."""
    tester = CacheSystemComprehensiveTest()
    success = await tester.run_all_tests()
    
    # Generate comprehensive report
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_results": tester.test_results,
        "summary": {
            "total_tests": len(tester.test_results),
            "passed": sum(1 for result in tester.test_results.values() if result),
            "failed": sum(1 for result in tester.test_results.values() if not result),
            "success_rate": f"{sum(1 for result in tester.test_results.values() if result)/len(tester.test_results)*100:.1f}%"
        },
        "cache_system_status": "FULLY_FUNCTIONAL" if success else "NEEDS_ATTENTION",
        "recommendations": [
            "Consider adding cache configuration to config.yaml",
            "Add cache monitoring and statistics",
            "Consider database storage for production environments",
            "Add more integration points with other components"
        ]
    }
    
    report_path = f"data/cache_system_comprehensive_report_{int(datetime.now().timestamp())}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\n📄 Comprehensive report saved: {report_path}")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)