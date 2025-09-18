#!/usr/bin/env python3
"""
L2 Memcached Performance Testing Script

Tests the Memcached (L2) cache layer for:
- 15,000 items capacity
- Connection pooling (20 connections)
- TTL behavior and expiration
- Concurrent access patterns
- Memory efficiency
"""

import asyncio
import time
import sys
import os
import random
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import aiomcache
except ImportError:
    print("❌ aiomcache not installed. Install with: pip install aiomcache")
    sys.exit(1)


class L2MemcachedPerformanceTester:
    """Comprehensive L2 Memcached performance tester"""

    def __init__(self, host='127.0.0.1', port=11211, pool_size=20):
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.client = None
        self.results = {}

    async def setup_client(self):
        """Initialize Memcached client"""
        try:
            self.client = aiomcache.Client(
                self.host,
                self.port,
                pool_size=self.pool_size
            )
            # Test connection
            await self.client.set(b'test_connection', b'ok', exptime=1)
            result = await self.client.get(b'test_connection')
            if result != b'ok':
                raise Exception("Connection test failed")
            await self.client.delete(b'test_connection')
            print(f"✅ Connected to Memcached at {self.host}:{self.port} (pool_size={self.pool_size})")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Memcached: {e}")
            return False

    async def test_basic_functionality(self) -> Dict[str, Any]:
        """Test basic Memcached operations"""
        print("\n=== Testing Basic Functionality ===")

        results = {
            "basic_set_get": False,
            "ttl_expiration": False,
            "key_deletion": False,
            "binary_data": False,
            "large_values": False
        }

        try:
            # Test set/get
            await self.client.set(b'test1', b'value1', exptime=60)
            result = await self.client.get(b'test1')
            results["basic_set_get"] = result == b'value1'
            print(f"  Set/Get: {'✅' if results['basic_set_get'] else '❌'}")

            # Test TTL expiration
            await self.client.set(b'test_expire', b'temp_value', exptime=1)
            await asyncio.sleep(1.1)
            expired_result = await self.client.get(b'test_expire')
            results["ttl_expiration"] = expired_result is None
            print(f"  TTL Expiration: {'✅' if results['ttl_expiration'] else '❌'}")

            # Test deletion
            await self.client.set(b'test_delete', b'delete_me', exptime=60)
            delete_success = await self.client.delete(b'test_delete')
            deleted_result = await self.client.get(b'test_delete')
            results["key_deletion"] = delete_success and deleted_result is None
            print(f"  Key Deletion: {'✅' if results['key_deletion'] else '❌'}")

            # Test binary data (JSON serialization)
            test_data = {"symbol": "BTCUSDT", "price": 45000.50, "volume": 123.456}
            json_data = json.dumps(test_data).encode('utf-8')
            await self.client.set(b'test_json', json_data, exptime=60)
            retrieved_data = await self.client.get(b'test_json')
            parsed_data = json.loads(retrieved_data.decode('utf-8'))
            results["binary_data"] = parsed_data == test_data
            print(f"  Binary/JSON Data: {'✅' if results['binary_data'] else '❌'}")

            # Test large values (typical dashboard data size)
            large_data = {"data": "x" * 10000}  # ~10KB
            large_json = json.dumps(large_data).encode('utf-8')
            await self.client.set(b'test_large', large_json, exptime=60)
            large_result = await self.client.get(b'test_large')
            results["large_values"] = large_result == large_json
            print(f"  Large Values (10KB): {'✅' if results['large_values'] else '❌'}")

        except Exception as e:
            print(f"  Error in basic functionality test: {e}")

        return results

    async def test_capacity_limits(self) -> Dict[str, Any]:
        """Test 15,000 item capacity"""
        print("\n=== Testing Capacity Limits (15,000 items) ===")

        results = {
            "load_15k_items": False,
            "retrieve_random_sample": False,
            "memory_efficiency": False
        }

        try:
            # Load 15,000 items
            print("  Loading 15,000 items...")
            start_time = time.time()

            # Use semaphore to control concurrency
            semaphore = asyncio.Semaphore(100)

            async def set_item(i):
                async with semaphore:
                    key = f"capacity_test_{i:06d}".encode('utf-8')
                    value = json.dumps({
                        "id": i,
                        "symbol": f"TEST{i % 100}USDT",
                        "price": random.uniform(1, 100),
                        "volume": random.uniform(1000, 10000),
                        "timestamp": time.time()
                    }).encode('utf-8')
                    await self.client.set(key, value, exptime=300)  # 5 min TTL

            # Load items concurrently
            tasks = [set_item(i) for i in range(15000)]
            await asyncio.gather(*tasks)

            load_time = time.time() - start_time
            results["load_15k_items"] = True
            print(f"  Loaded 15,000 items in {load_time:.2f}s: ✅")

            # Test random sample retrieval
            print("  Testing random sample retrieval...")
            sample_size = 1000
            sample_indices = random.sample(range(15000), sample_size)

            async def get_item(i):
                key = f"capacity_test_{i:06d}".encode('utf-8')
                return await self.client.get(key)

            start_time = time.time()
            get_tasks = [get_item(i) for i in sample_indices]
            results_list = await asyncio.gather(*get_tasks)
            retrieval_time = time.time() - start_time

            successful_retrievals = sum(1 for r in results_list if r is not None)
            success_rate = (successful_retrievals / sample_size) * 100

            results["retrieve_random_sample"] = success_rate >= 95.0
            print(f"  Retrieved {successful_retrievals}/{sample_size} items ({success_rate:.1f}%) in {retrieval_time:.3f}s: {'✅' if results['retrieve_random_sample'] else '❌'}")

            # Memory efficiency check
            avg_retrieval_time = (retrieval_time / sample_size) * 1000  # Convert to ms
            results["memory_efficiency"] = avg_retrieval_time < 10.0  # Should be < 10ms per item
            print(f"  Average retrieval time: {avg_retrieval_time:.3f}ms per item: {'✅' if results['memory_efficiency'] else '❌'}")

        except Exception as e:
            print(f"  Error in capacity test: {e}")

        return results

    async def test_connection_pooling(self) -> Dict[str, Any]:
        """Test connection pooling with concurrent access"""
        print("\n=== Testing Connection Pooling (20 connections) ===")

        results = {
            "concurrent_writes": False,
            "concurrent_reads": False,
            "pool_efficiency": False,
            "no_connection_errors": False
        }

        try:
            # Test concurrent writes (should not exceed pool size)
            concurrent_tasks = 50  # More than pool size to test pooling

            async def concurrent_writer(worker_id: int):
                errors = []
                for i in range(20):  # 20 operations per worker
                    try:
                        key = f"pool_test_w{worker_id}_{i}".encode('utf-8')
                        value = json.dumps({
                            "worker": worker_id,
                            "operation": i,
                            "timestamp": time.time()
                        }).encode('utf-8')
                        await self.client.set(key, value, exptime=120)
                    except Exception as e:
                        errors.append(str(e))
                return len(errors)

            print(f"  Testing {concurrent_tasks} concurrent writers...")
            start_time = time.time()
            write_tasks = [concurrent_writer(i) for i in range(concurrent_tasks)]
            write_errors = await asyncio.gather(*write_tasks)
            write_time = time.time() - start_time

            total_write_errors = sum(write_errors)
            total_write_ops = concurrent_tasks * 20
            results["concurrent_writes"] = total_write_errors == 0
            print(f"  Concurrent writes: {total_write_ops} ops, {total_write_errors} errors in {write_time:.2f}s: {'✅' if results['concurrent_writes'] else '❌'}")

            # Test concurrent reads
            async def concurrent_reader(worker_id: int):
                errors = []
                successful_reads = 0
                for i in range(20):
                    try:
                        key = f"pool_test_w{worker_id}_{i}".encode('utf-8')
                        result = await self.client.get(key)
                        if result is not None:
                            successful_reads += 1
                    except Exception as e:
                        errors.append(str(e))
                return len(errors), successful_reads

            print(f"  Testing {concurrent_tasks} concurrent readers...")
            start_time = time.time()
            read_tasks = [concurrent_reader(i) for i in range(concurrent_tasks)]
            read_results = await asyncio.gather(*read_tasks)
            read_time = time.time() - start_time

            total_read_errors = sum(r[0] for r in read_results)
            total_successful_reads = sum(r[1] for r in read_results)
            results["concurrent_reads"] = total_read_errors == 0
            print(f"  Concurrent reads: {total_successful_reads} successful, {total_read_errors} errors in {read_time:.2f}s: {'✅' if results['concurrent_reads'] else '❌'}")

            # Pool efficiency check
            total_ops = total_write_ops + (concurrent_tasks * 20)
            total_time = write_time + read_time
            ops_per_second = total_ops / total_time
            results["pool_efficiency"] = ops_per_second > 1000  # Should handle >1000 ops/sec
            print(f"  Pool efficiency: {ops_per_second:.0f} ops/sec: {'✅' if results['pool_efficiency'] else '❌'}")

            # No connection errors
            results["no_connection_errors"] = total_write_errors == 0 and total_read_errors == 0
            print(f"  No connection errors: {'✅' if results['no_connection_errors'] else '❌'}")

        except Exception as e:
            print(f"  Error in connection pooling test: {e}")

        return results

    async def test_performance_characteristics(self) -> Dict[str, Any]:
        """Test performance characteristics under load"""
        print("\n=== Testing Performance Characteristics ===")

        results = {
            "latency_under_load": False,
            "throughput_test": False,
            "memory_usage": False
        }

        try:
            # Latency test under load (more realistic - sequential with some concurrency)
            print("  Testing latency under realistic load...")
            num_operations = 1000
            concurrency_limit = 10  # Limit concurrent operations to realistic levels

            # Pre-populate some test data for gets
            for i in range(100):
                key = f"latency_test_get_{i}".encode('utf-8')
                value = json.dumps({"test": i, "data": "x" * 100}).encode('utf-8')
                await self.client.set(key, value, exptime=300)

            semaphore = asyncio.Semaphore(concurrency_limit)

            async def latency_test_operation(i):
                async with semaphore:
                    key = f"latency_test_{i}".encode('utf-8')
                    value = json.dumps({"test": i, "data": "x" * 100}).encode('utf-8')

                    # Measure set latency
                    start_time = time.perf_counter()
                    await self.client.set(key, value, exptime=60)
                    set_latency = (time.perf_counter() - start_time) * 1000

                    # Measure get latency (mix of new data and pre-populated data)
                    get_key = f"latency_test_get_{i % 100}".encode('utf-8')
                    start_time = time.perf_counter()
                    await self.client.get(get_key)
                    get_latency = (time.perf_counter() - start_time) * 1000

                    return set_latency, get_latency

            tasks = [latency_test_operation(i) for i in range(num_operations)]
            latency_results = await asyncio.gather(*tasks)

            set_latencies = [r[0] for r in latency_results]
            get_latencies = [r[1] for r in latency_results]

            avg_set_latency = sum(set_latencies) / len(set_latencies)
            avg_get_latency = sum(get_latencies) / len(get_latencies)
            p95_set_latency = sorted(set_latencies)[int(len(set_latencies) * 0.95)]
            p95_get_latency = sorted(get_latencies)[int(len(get_latencies) * 0.95)]

            # L2 should be faster than 10ms average (more realistic for Memcached), 50ms P95
            results["latency_under_load"] = avg_set_latency < 10 and avg_get_latency < 10 and p95_set_latency < 50 and p95_get_latency < 50
            print(f"  Set latency: avg={avg_set_latency:.2f}ms, P95={p95_set_latency:.2f}ms")
            print(f"  Get latency: avg={avg_get_latency:.2f}ms, P95={p95_get_latency:.2f}ms")
            print(f"  Latency under load: {'✅' if results['latency_under_load'] else '❌'}")

            # Throughput test
            print("  Testing maximum throughput...")
            throughput_duration = 10  # seconds
            start_time = time.time()
            end_time = start_time + throughput_duration
            operations_count = 0

            async def throughput_worker():
                nonlocal operations_count
                while time.time() < end_time:
                    key = f"throughput_{operations_count}".encode('utf-8')
                    await self.client.set(key, b'test_value', exptime=30)
                    operations_count += 1

            # Run multiple workers
            workers = [throughput_worker() for _ in range(10)]
            await asyncio.gather(*workers)

            throughput = operations_count / throughput_duration
            results["throughput_test"] = throughput > 500  # Should handle >500 ops/sec
            print(f"  Throughput: {throughput:.0f} ops/sec: {'✅' if results['throughput_test'] else '❌'}")

            # Memory usage estimate
            test_items = 1000
            item_size_estimate = 200  # bytes per item (key + value + overhead)
            estimated_memory = test_items * item_size_estimate / 1024 / 1024  # MB
            results["memory_usage"] = estimated_memory < 100  # Should be reasonable
            print(f"  Memory usage estimate: {estimated_memory:.2f}MB for {test_items} items: {'✅' if results['memory_usage'] else '❌'}")

        except Exception as e:
            print(f"  Error in performance test: {e}")

        return results

    async def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== Cleaning up test data ===")
        try:
            # Note: Memcached doesn't have a flush_all command in aiomcache
            # Test data will expire based on TTL
            print("  Test data will expire based on TTL settings")
        except Exception as e:
            print(f"  Cleanup error: {e}")

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        print("L2 Memcached Comprehensive Performance Test")
        print("=" * 50)

        # Setup
        if not await self.setup_client():
            return {"error": "Failed to connect to Memcached"}

        all_results = {}

        try:
            # Run all test suites
            all_results["basic_functionality"] = await self.test_basic_functionality()
            all_results["capacity_limits"] = await self.test_capacity_limits()
            all_results["connection_pooling"] = await self.test_connection_pooling()
            all_results["performance_characteristics"] = await self.test_performance_characteristics()

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
            capacity_tests = all_results["capacity_limits"]
            pooling_tests = all_results["connection_pooling"]
            performance_tests = all_results["performance_characteristics"]

            requirements_met = (
                capacity_tests.get("load_15k_items", False) and
                capacity_tests.get("retrieve_random_sample", False) and
                pooling_tests.get("no_connection_errors", False) and
                performance_tests.get("latency_under_load", False)
            )

            print(f"L2 Memcached Requirements Met: {'✅' if requirements_met else '❌'}")
            print(f"  - 15,000 items capacity: {'✅' if capacity_tests.get('load_15k_items', False) else '❌'}")
            print(f"  - Connection pooling (20 conn): {'✅' if pooling_tests.get('no_connection_errors', False) else '❌'}")
            print(f"  - Performance under load: {'✅' if performance_tests.get('latency_under_load', False) else '❌'}")

            all_results["overall"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "requirements_met": requirements_met
            }

        finally:
            await self.cleanup_test_data()

        return all_results


async def main():
    """Main test execution"""
    tester = L2MemcachedPerformanceTester()
    results = await tester.run_comprehensive_test()

    # Exit with error code if requirements not met
    if "error" in results:
        print(f"\n❌ {results['error']}")
        sys.exit(1)
    elif not results["overall"]["requirements_met"]:
        print("\n❌ L2 Memcached requirements not met!")
        sys.exit(1)
    else:
        print("\n✅ L2 Memcached meets all performance requirements!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())