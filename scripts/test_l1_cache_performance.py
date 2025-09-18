#!/usr/bin/env python3
"""
L1 Cache Performance Testing Script

Tests the high-performance LRU cache implementation for:
- 1500 items capacity
- <1ms access time
- LRU eviction correctness
- Thread safety
- Memory efficiency
"""

import asyncio
import time
import sys
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.cache.lru_cache import HighPerformanceLRUCache


class L1CachePerformanceTester:
    """Comprehensive L1 cache performance tester"""

    def __init__(self):
        self.results = {}

    def test_basic_functionality(self) -> Dict[str, Any]:
        """Test basic cache operations"""
        print("=== Testing Basic Functionality ===")

        cache = HighPerformanceLRUCache(max_size=10, default_ttl=60)
        results = {
            "basic_set_get": False,
            "ttl_expiration": False,
            "key_deletion": False,
            "cache_clear": False
        }

        # Test set/get
        cache.set("test1", "value1")
        result = cache.get("test1")
        results["basic_set_get"] = result == "value1"
        print(f"  Set/Get: {'✅' if results['basic_set_get'] else '❌'}")

        # Test TTL expiration
        cache.set("test_expire", "temp_value", ttl=1)
        time.sleep(1.1)
        expired_result = cache.get("test_expire")
        results["ttl_expiration"] = expired_result is None
        print(f"  TTL Expiration: {'✅' if results['ttl_expiration'] else '❌'}")

        # Test deletion
        cache.set("test_delete", "delete_me")
        delete_success = cache.delete("test_delete")
        deleted_result = cache.get("test_delete")
        results["key_deletion"] = delete_success and deleted_result is None
        print(f"  Key Deletion: {'✅' if results['key_deletion'] else '❌'}")

        # Test clear
        cache.set("test2", "value2")
        cache.clear()
        results["cache_clear"] = cache.size() == 0
        print(f"  Cache Clear: {'✅' if results['cache_clear'] else '❌'}")

        return results

    def test_lru_eviction(self) -> Dict[str, Any]:
        """Test LRU eviction behavior"""
        print("\n=== Testing LRU Eviction ===")

        cache = HighPerformanceLRUCache(max_size=3, default_ttl=60)
        results = {
            "capacity_limit": False,
            "lru_order": False,
            "access_updates_order": False
        }

        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        results["capacity_limit"] = cache.size() == 3
        print(f"  Capacity Limit: {'✅' if results['capacity_limit'] else '❌'}")

        # Add one more item - should evict LRU (key1)
        cache.set("key4", "value4")
        key1_evicted = cache.get("key1") is None
        key4_exists = cache.get("key4") == "value4"
        results["lru_order"] = key1_evicted and key4_exists
        print(f"  LRU Eviction Order: {'✅' if results['lru_order'] else '❌'}")

        # Access key2 to make it recently used
        cache.get("key2")
        # Add key5 - should evict key3 (not key2)
        cache.set("key5", "value5")
        key2_exists = cache.get("key2") == "value2"
        key3_evicted = cache.get("key3") is None
        results["access_updates_order"] = key2_exists and key3_evicted
        print(f"  Access Updates Order: {'✅' if results['access_updates_order'] else '❌'}")

        return results

    def test_performance_requirements(self) -> Dict[str, Any]:
        """Test performance requirements: 1500 items, <1ms access"""
        print("\n=== Testing Performance Requirements ===")

        cache = HighPerformanceLRUCache(max_size=1500, default_ttl=30)
        results = {
            "capacity_1500": False,
            "get_under_1ms": False,
            "set_under_1ms": False,
            "bulk_operations": False
        }

        # Test 1500 item capacity
        for i in range(1500):
            cache.set(f"perf_key_{i}", f"value_{i}")

        results["capacity_1500"] = cache.size() == 1500
        print(f"  1500 Items Capacity: {'✅' if results['capacity_1500'] else '❌'}")

        # Test access time
        test_key = "perf_key_750"  # Middle item

        # Measure get performance
        get_times = []
        for _ in range(1000):
            start = time.perf_counter()
            cache.get(test_key)
            elapsed = (time.perf_counter() - start) * 1000
            get_times.append(elapsed)

        avg_get_time = sum(get_times) / len(get_times)
        max_get_time = max(get_times)
        results["get_under_1ms"] = avg_get_time < 1.0
        print(f"  Get Time: avg={avg_get_time:.3f}ms, max={max_get_time:.3f}ms {'✅' if results['get_under_1ms'] else '❌'}")

        # Measure set performance
        set_times = []
        for i in range(100):
            start = time.perf_counter()
            cache.set(f"perf_set_{i}", f"new_value_{i}")
            elapsed = (time.perf_counter() - start) * 1000
            set_times.append(elapsed)

        avg_set_time = sum(set_times) / len(set_times)
        max_set_time = max(set_times)
        results["set_under_1ms"] = avg_set_time < 1.0
        print(f"  Set Time: avg={avg_set_time:.3f}ms, max={max_set_time:.3f}ms {'✅' if results['set_under_1ms'] else '❌'}")

        # Test bulk operations
        start = time.perf_counter()
        for i in range(1000):
            cache.get(f"perf_key_{i % 1500}")
        bulk_time = (time.perf_counter() - start) * 1000
        results["bulk_operations"] = bulk_time < 100  # 1000 operations in < 100ms
        print(f"  1000 Gets in {bulk_time:.1f}ms: {'✅' if results['bulk_operations'] else '❌'}")

        return results

    def test_thread_safety(self) -> Dict[str, Any]:
        """Test thread safety"""
        print("\n=== Testing Thread Safety ===")

        cache = HighPerformanceLRUCache(max_size=1000, default_ttl=60)
        results = {
            "concurrent_access": False,
            "data_integrity": False
        }

        # Concurrent access test
        def worker(worker_id: int, operations: int):
            for i in range(operations):
                key = f"thread_{worker_id}_key_{i}"
                value = f"thread_{worker_id}_value_{i}"
                cache.set(key, value)
                retrieved = cache.get(key)
                assert retrieved == value, f"Data corruption detected: {retrieved} != {value}"

        try:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker, i, 50) for i in range(10)]
                for future in futures:
                    future.result()  # Will raise exception if assertion fails

            results["concurrent_access"] = True
            print(f"  Concurrent Access: ✅")
        except Exception as e:
            print(f"  Concurrent Access: ❌ ({e})")

        # Data integrity check
        test_data = {}
        for i in range(100):
            key = f"integrity_key_{i}"
            value = f"integrity_value_{i}"
            cache.set(key, value)
            test_data[key] = value

        integrity_check = True
        for key, expected_value in test_data.items():
            actual_value = cache.get(key)
            if actual_value != expected_value:
                integrity_check = False
                break

        results["data_integrity"] = integrity_check
        print(f"  Data Integrity: {'✅' if results['data_integrity'] else '❌'}")

        return results

    def test_memory_efficiency(self) -> Dict[str, Any]:
        """Test memory efficiency and cleanup"""
        print("\n=== Testing Memory Efficiency ===")

        cache = HighPerformanceLRUCache(max_size=1000, default_ttl=2)
        results = {
            "expired_cleanup": False,
            "statistics_accuracy": False,
            "memory_usage": False
        }

        # Fill cache with short TTL items
        for i in range(500):
            cache.set(f"expire_key_{i}", f"expire_value_{i}", ttl=1)

        # Wait for expiration
        time.sleep(1.1)

        # Test cleanup
        expired_count = cache.cleanup_expired()
        results["expired_cleanup"] = expired_count == 500
        print(f"  Expired Cleanup: {expired_count} items {'✅' if results['expired_cleanup'] else '❌'}")

        # Test statistics
        cache.clear()
        cache.set("stat_test", "value")
        cache.get("stat_test")  # Hit
        cache.get("non_existent")  # Miss

        stats = cache.get_statistics()
        expected_hit_rate = 50.0  # 1 hit, 1 miss
        actual_hit_rate = stats["hit_rate"]
        results["statistics_accuracy"] = abs(actual_hit_rate - expected_hit_rate) < 1.0
        print(f"  Statistics Accuracy: {actual_hit_rate:.1f}% hit rate {'✅' if results['statistics_accuracy'] else '❌'}")

        # Memory usage test (basic check)
        cache.clear()
        initial_size = cache.size()
        for i in range(100):
            cache.set(f"memory_key_{i}", f"memory_value_{i}")

        final_size = cache.size()
        results["memory_usage"] = initial_size == 0 and final_size == 100
        print(f"  Memory Usage: {initial_size} -> {final_size} {'✅' if results['memory_usage'] else '❌'}")

        return results

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        print("L1 Cache Comprehensive Performance Test")
        print("=" * 50)

        all_results = {}

        # Run all test suites
        all_results["basic_functionality"] = self.test_basic_functionality()
        all_results["lru_eviction"] = self.test_lru_eviction()
        all_results["performance_requirements"] = self.test_performance_requirements()
        all_results["thread_safety"] = self.test_thread_safety()
        all_results["memory_efficiency"] = self.test_memory_efficiency()

        # Calculate overall success
        total_tests = 0
        passed_tests = 0

        for category, tests in all_results.items():
            for test_name, result in tests.items():
                total_tests += 1
                if result:
                    passed_tests += 1

        success_rate = (passed_tests / total_tests) * 100

        print(f"\n=== Overall Results ===")
        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        # Requirements check
        perf_tests = all_results["performance_requirements"]
        requirements_met = (
            perf_tests["capacity_1500"] and
            perf_tests["get_under_1ms"] and
            perf_tests["set_under_1ms"]
        )

        print(f"L1 Cache Requirements Met: {'✅' if requirements_met else '❌'}")
        print(f"  - 1500 items capacity: {'✅' if perf_tests['capacity_1500'] else '❌'}")
        print(f"  - <1ms access time: {'✅' if perf_tests['get_under_1ms'] else '❌'}")
        print(f"  - <1ms set time: {'✅' if perf_tests['set_under_1ms'] else '❌'}")

        all_results["overall"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "requirements_met": requirements_met
        }

        return all_results


def main():
    """Main test execution"""
    tester = L1CachePerformanceTester()
    results = tester.run_comprehensive_test()

    # Exit with error code if requirements not met
    if not results["overall"]["requirements_met"]:
        print("\n❌ L1 Cache requirements not met!")
        sys.exit(1)
    else:
        print("\n✅ L1 Cache meets all performance requirements!")
        sys.exit(0)


if __name__ == "__main__":
    main()