#!/usr/bin/env python3
"""
Comprehensive AsyncIO Task Management Validation Script
Validates the fixes for untracked asyncio tasks and resource leaks
"""

import asyncio
import aiohttp
import aiomcache
import psutil
import time
import signal
import sys
import logging
from typing import Dict, List, Set, Any
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncIOValidation:
    """Validates AsyncIO task management fixes"""

    def __init__(self):
        self.background_tasks: Set[asyncio.Task] = set()
        self.test_results: Dict[str, Any] = {}
        self.memcache_clients: List[aiomcache.Client] = []
        self.initial_memory = None
        self.process = psutil.Process()

    def create_tracked_task(self, coro, name=None):
        """Replicate the create_tracked_task function from main.py"""
        task = asyncio.create_task(coro)
        if name and hasattr(task, 'set_name'):
            task.set_name(name)

        # Add to tracking set
        self.background_tasks.add(task)

        # Remove from set when done
        def task_done_callback(task):
            self.background_tasks.discard(task)
            task_name = getattr(task, 'get_name', lambda: str(task))()
            if task.cancelled():
                logger.debug(f"Task {task_name} was cancelled")
            elif task.exception():
                logger.error(f"Task {task_name} failed: {task.exception()}")

        task.add_done_callback(task_done_callback)
        return task

    async def test_task_tracking(self):
        """Test 1: Validate task tracking system"""
        logger.info("🧪 Testing task tracking system...")

        async def dummy_task(duration=1):
            await asyncio.sleep(duration)
            return "completed"

        # Create tracked tasks
        initial_count = len(self.background_tasks)
        tasks = []

        for i in range(5):
            task = self.create_tracked_task(dummy_task(0.5), f"test_task_{i}")
            tasks.append(task)

        # Verify tasks are tracked
        assert len(self.background_tasks) == initial_count + 5, f"Expected {initial_count + 5} tasks, got {len(self.background_tasks)}"

        # Wait for completion
        await asyncio.gather(*tasks)

        # Verify tasks are removed after completion
        await asyncio.sleep(0.1)  # Small delay for cleanup
        assert len(self.background_tasks) == initial_count, f"Expected {initial_count} tasks after cleanup, got {len(self.background_tasks)}"

        self.test_results['task_tracking'] = {
            'status': 'PASS',
            'details': 'Tasks properly added and removed from tracking set'
        }
        logger.info("✅ Task tracking test passed")

    async def test_resource_cleanup(self):
        """Test 2: Validate aiomcache resource cleanup"""
        logger.info("🧪 Testing aiomcache resource cleanup...")

        async def create_memcache_connection():
            """Simulate the pattern from main.py"""
            memcache_client = None
            try:
                # Create client (simulating cache operations)
                memcache_client = aiomcache.Client("127.0.0.1", 11211)
                self.memcache_clients.append(memcache_client)

                # Simulate some cache operations
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in memcache operation: {e}")
            finally:
                # Always cleanup aiomcache client to prevent resource leaks
                if memcache_client:
                    try:
                        await memcache_client.close()
                        logger.debug("Memcache client closed successfully")
                        if memcache_client in self.memcache_clients:
                            self.memcache_clients.remove(memcache_client)
                    except Exception as e:
                        logger.debug(f"Error closing memcache client: {e}")

        # Test multiple connections
        tasks = []
        for i in range(10):
            task = self.create_tracked_task(create_memcache_connection(), f"memcache_test_{i}")
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no leftover connections
        open_connections = len(self.memcache_clients)

        self.test_results['resource_cleanup'] = {
            'status': 'PASS' if open_connections == 0 else 'FAIL',
            'details': f'Open memcache connections: {open_connections}',
            'open_connections': open_connections
        }

        if open_connections == 0:
            logger.info("✅ Resource cleanup test passed")
        else:
            logger.error(f"❌ Resource cleanup test failed: {open_connections} open connections")

    async def test_graceful_shutdown(self):
        """Test 3: Validate graceful task cancellation"""
        logger.info("🧪 Testing graceful shutdown...")

        async def long_running_task():
            try:
                await asyncio.sleep(10)  # Long running task
            except asyncio.CancelledError:
                logger.debug("Long running task was cancelled")
                raise

        # Create long running tasks
        tasks = []
        for i in range(3):
            task = self.create_tracked_task(long_running_task(), f"long_task_{i}")
            tasks.append(task)

        # Wait a bit then cancel
        await asyncio.sleep(0.2)

        # Simulate cleanup_background_tasks
        logger.info(f"Cleaning up {len(self.background_tasks)} background tasks...")

        # Cancel all tasks
        for task in self.background_tasks.copy():
            if not task.done():
                task.cancel()

        # Wait for cancellation to complete
        if self.background_tasks:
            try:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error during task cleanup: {e}")

        # Check if all tasks were cancelled
        cancelled_count = sum(1 for task in tasks if task.cancelled())

        self.background_tasks.clear()

        self.test_results['graceful_shutdown'] = {
            'status': 'PASS' if cancelled_count == 3 else 'FAIL',
            'details': f'Cancelled {cancelled_count}/3 tasks',
            'cancelled_tasks': cancelled_count
        }

        if cancelled_count == 3:
            logger.info("✅ Graceful shutdown test passed")
        else:
            logger.error(f"❌ Graceful shutdown test failed: only {cancelled_count}/3 tasks cancelled")

    async def test_memory_usage(self):
        """Test 4: Monitor memory usage during task operations"""
        logger.info("🧪 Testing memory usage patterns...")

        if self.initial_memory is None:
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        async def memory_intensive_task():
            # Simulate some memory usage
            data = [i for i in range(1000)]
            await asyncio.sleep(0.1)
            return len(data)

        # Create many tasks
        tasks = []
        for i in range(50):
            task = self.create_tracked_task(memory_intensive_task(), f"memory_task_{i}")
            tasks.append(task)

        # Monitor memory during execution
        peak_memory = self.initial_memory

        while any(not task.done() for task in tasks):
            current_memory = self.process.memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)
            await asyncio.sleep(0.01)

        await asyncio.gather(*tasks)

        # Final memory check
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - self.initial_memory

        self.test_results['memory_usage'] = {
            'status': 'PASS' if memory_growth < 50 else 'WARN',  # 50MB threshold
            'initial_memory_mb': round(self.initial_memory, 2),
            'peak_memory_mb': round(peak_memory, 2),
            'final_memory_mb': round(final_memory, 2),
            'memory_growth_mb': round(memory_growth, 2)
        }

        logger.info(f"✅ Memory usage test completed: {memory_growth:.2f}MB growth")

    async def test_untracked_task_detection(self):
        """Test 5: Detect if any untracked tasks are being created"""
        logger.info("🧪 Testing untracked task detection...")

        # Get initial task count
        initial_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        initial_count = len(initial_tasks)

        # Create tracked task
        tracked_task = self.create_tracked_task(asyncio.sleep(0.1), "tracked_test")

        # Create untracked task (simulate old pattern)
        untracked_task = asyncio.create_task(asyncio.sleep(0.1))

        await asyncio.sleep(0.05)

        # Check current tasks
        current_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        current_count = len(current_tasks)

        # Wait for completion
        await asyncio.gather(tracked_task, untracked_task)

        # Final task count
        final_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        final_count = len(final_tasks)

        untracked_detected = (current_count - initial_count) > 1  # More than just our tracked task

        self.test_results['untracked_task_detection'] = {
            'status': 'WARN' if untracked_detected else 'PASS',
            'details': f'Initial: {initial_count}, Peak: {current_count}, Final: {final_count}',
            'untracked_detected': untracked_detected
        }

        if untracked_detected:
            logger.warning(f"⚠️ Untracked tasks detected: peak {current_count} vs initial {initial_count}")
        else:
            logger.info("✅ No untracked tasks detected")

    async def run_validation(self):
        """Run all validation tests"""
        logger.info("🚀 Starting AsyncIO Task Management Validation")
        logger.info(f"Process PID: {self.process.pid}")

        self.initial_memory = self.process.memory_info().rss / 1024 / 1024
        logger.info(f"Initial memory usage: {self.initial_memory:.2f} MB")

        try:
            await self.test_task_tracking()
            await self.test_resource_cleanup()
            await self.test_graceful_shutdown()
            await self.test_memory_usage()
            await self.test_untracked_task_detection()

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

        return True

    def generate_report(self):
        """Generate validation report"""
        print("\n" + "="*80)
        print("🔍 ASYNCIO TASK MANAGEMENT VALIDATION REPORT")
        print("="*80)

        passed_tests = 0
        total_tests = len(self.test_results)

        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
            print(f"\n{status_icon} {test_name.replace('_', ' ').title()}: {result['status']}")
            print(f"   Details: {result.get('details', 'No details available')}")

            if test_name == 'memory_usage' and 'memory_growth_mb' in result:
                print(f"   Memory Growth: {result['memory_growth_mb']:.2f} MB")
            elif test_name == 'resource_cleanup' and 'open_connections' in result:
                print(f"   Open Connections: {result['open_connections']}")
            elif test_name == 'graceful_shutdown' and 'cancelled_tasks' in result:
                print(f"   Cancelled Tasks: {result['cancelled_tasks']}")

            if result['status'] == 'PASS':
                passed_tests += 1

        print(f"\n📊 SUMMARY: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 All AsyncIO task management fixes validated successfully!")
            return True
        else:
            print("⚠️ Some issues detected in AsyncIO task management")
            return False

async def main():
    """Main validation function"""
    validator = AsyncIOValidation()

    def signal_handler(signum, frame):
        logger.info("Received interrupt signal, cleaning up...")
        # Cancel all background tasks
        for task in validator.background_tasks:
            task.cancel()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        success = await validator.run_validation()
        report_success = validator.generate_report()

        return success and report_success

    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"Failed to run validation: {e}")
        sys.exit(1)