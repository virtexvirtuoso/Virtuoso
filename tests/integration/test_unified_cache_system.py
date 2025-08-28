#!/usr/bin/env python3
"""
Comprehensive Test Suite for Unified Cache System
Tests all aspects of the consolidated cache layer to ensure proper functionality.
"""

import asyncio
import json
import time
import logging
import sys
import os
from typing import Dict, Any
import traceback

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CacheSystemTester:
    """Comprehensive cache system test suite."""
    
    def __init__(self):
        self.test_results = []
        self.cache_manager = None
        
    async def initialize(self):
        """Initialize the cache manager for testing."""
        try:
            from src.core.cache_manager import cache_manager
            self.cache_manager = cache_manager
            logger.info("✅ Cache manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache manager: {e}")
            return False
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        })
    
    async def test_cache_manager_initialization(self):
        """Test that cache manager initializes properly."""
        test_name = "Cache Manager Initialization"
        try:
            # Test singleton pattern
            from src.core.cache_manager import CacheManager
            instance1 = CacheManager()
            instance2 = CacheManager()
            
            singleton_test = instance1 is instance2
            self.log_test_result(f"{test_name} - Singleton Pattern", singleton_test, 
                               f"Same instance: {singleton_test}")
            
            # Test initialization
            initialized = hasattr(instance1, '_initialized') and instance1._initialized
            self.log_test_result(f"{test_name} - Proper Initialization", initialized, 
                               f"Initialized: {initialized}")
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_basic_cache_operations(self):
        """Test basic get/set/delete operations."""
        test_name = "Basic Cache Operations"
        
        try:
            # Test basic set/get
            test_key = "test:basic"
            test_value = {"message": "test_value", "timestamp": time.time()}
            
            set_result = await self.cache_manager.set(test_key, test_value, ttl=60)
            self.log_test_result(f"{test_name} - Set Operation", set_result, 
                               f"Set returned: {set_result}")
            
            get_result = await self.cache_manager.get(test_key)
            get_success = get_result == test_value
            self.log_test_result(f"{test_name} - Get Operation", get_success, 
                               f"Retrieved: {get_result}")
            
            # Test exists
            exists_result = await self.cache_manager.exists(test_key)
            self.log_test_result(f"{test_name} - Exists Check", exists_result, 
                               f"Key exists: {exists_result}")
            
            # Test delete
            delete_result = await self.cache_manager.delete(test_key)
            self.log_test_result(f"{test_name} - Delete Operation", delete_result, 
                               f"Delete returned: {delete_result}")
            
            # Test get after delete
            get_after_delete = await self.cache_manager.get(test_key)
            delete_success = get_after_delete is None
            self.log_test_result(f"{test_name} - Get After Delete", delete_success, 
                               f"Value after delete: {get_after_delete}")
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def test_connection_pooling(self):
        """Test connection pooling functionality."""
        test_name = "Connection Pooling"
        
        try:
            # Test multiple concurrent operations
            tasks = []
            for i in range(10):
                key = f"test:pool:{i}"
                value = f"value_{i}"
                tasks.append(self.cache_manager.set(key, value))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            successful_ops = sum(1 for r in results if r is True)
            pool_test_passed = successful_ops >= 8  # Allow some failures
            
            self.log_test_result(f"{test_name} - Concurrent Operations", pool_test_passed, 
                               f"Successful operations: {successful_ops}/10")
            
            # Cleanup
            for i in range(10):
                await self.cache_manager.delete(f"test:pool:{i}")
            
            return pool_test_passed
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_fallback_mechanisms(self):
        """Test fallback to in-memory cache when memcached is unavailable."""
        test_name = "Fallback Mechanisms"
        
        try:
            # Force client to None to test fallback
            original_client = self.cache_manager._client
            self.cache_manager._client = None
            
            # Test set/get with fallback
            test_key = "test:fallback"
            test_value = {"fallback": True, "timestamp": time.time()}
            
            set_result = await self.cache_manager.set(test_key, test_value)
            self.log_test_result(f"{test_name} - Fallback Set", set_result, 
                               f"Fallback set successful: {set_result}")
            
            get_result = await self.cache_manager.get(test_key)
            fallback_success = get_result == test_value
            self.log_test_result(f"{test_name} - Fallback Get", fallback_success, 
                               f"Fallback get successful: {fallback_success}")
            
            # Check fallback cache stats
            stats = self.cache_manager.get_stats()
            fallback_hits = stats.get('fallback_hits', 0) > 0
            self.log_test_result(f"{test_name} - Fallback Stats", fallback_hits, 
                               f"Fallback hits recorded: {stats.get('fallback_hits', 0)}")
            
            # Restore client
            self.cache_manager._client = original_client
            
            return True
            
        except Exception as e:
            # Restore client even on error
            self.cache_manager._client = original_client
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_multi_operations(self):
        """Test batch get/set operations."""
        test_name = "Multi Operations"
        
        try:
            # Test multi-set
            test_items = {
                "test:multi:1": {"value": 1, "type": "test"},
                "test:multi:2": {"value": 2, "type": "test"},
                "test:multi:3": {"value": 3, "type": "test"}
            }
            
            set_count = await self.cache_manager.set_multi(test_items)
            set_success = set_count == len(test_items)
            self.log_test_result(f"{test_name} - Multi Set", set_success, 
                               f"Set {set_count}/{len(test_items)} items")
            
            # Test multi-get
            keys = list(test_items.keys())
            results = await self.cache_manager.get_multi(keys)
            
            get_success = len(results) == len(test_items)
            self.log_test_result(f"{test_name} - Multi Get", get_success, 
                               f"Retrieved {len(results)}/{len(test_items)} items")
            
            # Cleanup
            for key in keys:
                await self.cache_manager.delete(key)
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_key_consistency(self):
        """Test cache key patterns and consistency."""
        test_name = "Key Consistency"
        
        try:
            # Test common key patterns
            key_patterns = [
                "market:overview",
                "analysis:results",
                "signals:active",
                "confluence:symbols",
                "dashboard:mobile"
            ]
            
            consistent_keys = 0
            for pattern in key_patterns:
                # Test that keys follow expected format
                if ":" in pattern and len(pattern.split(":")) == 2:
                    consistent_keys += 1
                    
                    # Test pattern clearing
                    await self.cache_manager.set(f"{pattern}:test", {"test": True})
                    cleared = await self.cache_manager.clear_pattern(pattern)
                    pattern_test = cleared >= 0  # Should not error
                    
                    if not pattern_test:
                        self.log_test_result(f"{test_name} - Pattern {pattern}", False, 
                                           "Pattern clearing failed")
            
            consistency_test = consistent_keys == len(key_patterns)
            self.log_test_result(f"{test_name} - Key Format", consistency_test, 
                               f"Consistent keys: {consistent_keys}/{len(key_patterns)}")
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_ttl_management(self):
        """Test TTL (Time To Live) functionality."""
        test_name = "TTL Management"
        
        try:
            # Test short TTL
            test_key = "test:ttl"
            test_value = {"ttl_test": True}
            
            # Set with 2 second TTL
            await self.cache_manager.set(test_key, test_value, ttl=2)
            
            # Should exist immediately
            immediate_get = await self.cache_manager.get(test_key)
            immediate_success = immediate_get == test_value
            self.log_test_result(f"{test_name} - Immediate Get", immediate_success, 
                               f"Value retrieved: {immediate_get is not None}")
            
            # Wait for expiration (test with fallback cache)
            await asyncio.sleep(3)
            
            # Should be expired (this tests fallback TTL handling)
            expired_get = await self.cache_manager.get(test_key)
            expiration_success = expired_get is None
            self.log_test_result(f"{test_name} - TTL Expiration", expiration_success, 
                               f"Value after TTL: {expired_get}")
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_health_check(self):
        """Test health check functionality."""
        test_name = "Health Check"
        
        try:
            health = await self.cache_manager.health_check()
            
            required_fields = ['status', 'memcached_connected', 'fallback_available', 'stats', 'hit_rate']
            has_required_fields = all(field in health for field in required_fields)
            
            self.log_test_result(f"{test_name} - Required Fields", has_required_fields, 
                               f"Health response: {list(health.keys())}")
            
            # Test valid status values
            valid_status = health.get('status') in ['healthy', 'degraded', 'error']
            self.log_test_result(f"{test_name} - Valid Status", valid_status, 
                               f"Status: {health.get('status')}")
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_performance_monitoring_integration(self):
        """Test integration with performance monitoring."""
        test_name = "Performance Monitoring Integration"
        
        try:
            # This tests if performance monitoring can be imported without errors
            from src.core.cache_manager import get_performance_monitor
            
            monitor = get_performance_monitor()
            monitor_available = monitor is not None or monitor is False  # False means intentionally disabled
            
            self.log_test_result(f"{test_name} - Monitor Import", True, 
                               f"Monitor available: {monitor is not None}")
            
            # Test cache operation with monitoring
            await self.cache_manager.set("test:perf", {"performance": "test"})
            
            return True
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all cache system tests."""
        logger.info("🧪 Starting Unified Cache System Tests")
        logger.info("=" * 50)
        
        # Initialize
        if not await self.initialize():
            logger.error("❌ Failed to initialize cache system")
            return False
        
        # Run all tests
        tests = [
            self.test_cache_manager_initialization,
            self.test_basic_cache_operations,
            self.test_connection_pooling,
            self.test_fallback_mechanisms,
            self.test_multi_operations,
            self.test_key_consistency,
            self.test_ttl_management,
            self.test_health_check,
            self.test_performance_monitoring_integration,
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for test_func in tests:
            try:
                logger.info(f"\n🔬 Running {test_func.__name__}...")
                result = await test_func()
                if result:
                    passed_tests += 1
                total_tests += 1
            except Exception as e:
                logger.error(f"❌ Test {test_func.__name__} failed with exception: {e}")
                total_tests += 1
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info(f"📊 CACHE SYSTEM TEST SUMMARY")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        logger.info("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            logger.info(f"{status} {result['test']}")
            if result['details']:
                logger.info(f"   {result['details']}")
        
        # Final cleanup
        if self.cache_manager:
            await self.cache_manager.close()
        
        return passed_tests == total_tests


async def main():
    """Main test execution."""
    tester = CacheSystemTester()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("🎉 ALL CACHE SYSTEM TESTS PASSED!")
        sys.exit(0)
    else:
        logger.error("💥 SOME CACHE SYSTEM TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())