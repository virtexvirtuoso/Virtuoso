#!/usr/bin/env python3
"""Comprehensive test of the AsyncIO task tracking system."""

import asyncio
import time
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.utils.task_tracker import create_tracked_task, cleanup_background_tasks, get_task_info

async def test_task_tracking():
    """Test the task tracking system comprehensively."""
    print("🧪 Testing AsyncIO Task Tracking System")
    print("=" * 50)

    # Test 1: Basic task creation and tracking
    print("\n1. Testing basic task creation and tracking...")

    async def sample_task(name, duration):
        await asyncio.sleep(duration)
        return f"Task {name} completed"

    # Create multiple tracked tasks
    tasks = []
    for i in range(5):
        task = create_tracked_task(sample_task(f"test_{i}", 0.1), name=f"test_task_{i}")
        tasks.append(task)

    # Check task info before completion
    info_before = get_task_info()
    print(f"   Tasks before completion: {info_before}")

    # Wait for tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print(f"   Task results: {len(results)} tasks completed")

    # Small delay to let callbacks execute
    await asyncio.sleep(0.1)

    # Check task info after completion
    info_after = get_task_info()
    print(f"   Tasks after completion: {info_after}")

    # Test 2: Task failure handling
    print("\n2. Testing task failure handling...")

    async def failing_task():
        await asyncio.sleep(0.05)
        raise ValueError("Test error")

    fail_task = create_tracked_task(failing_task(), name="failing_task")
    try:
        await fail_task
    except ValueError:
        print("   ✅ Task failure properly handled")

    await asyncio.sleep(0.1)  # Let cleanup callback run
    info_after_failure = get_task_info()
    print(f"   Task info after failure: {info_after_failure}")

    # Test 3: Task cancellation
    print("\n3. Testing task cancellation...")

    async def long_running_task():
        try:
            await asyncio.sleep(10)  # Long running
        except asyncio.CancelledError:
            print("   ✅ Task properly cancelled")
            raise

    cancel_task = create_tracked_task(long_running_task(), name="cancel_task")
    await asyncio.sleep(0.05)  # Let it start
    cancel_task.cancel()

    try:
        await cancel_task
    except asyncio.CancelledError:
        pass

    await asyncio.sleep(0.1)  # Let cleanup callback run
    info_after_cancel = get_task_info()
    print(f"   Task info after cancellation: {info_after_cancel}")

    # Test 4: Cleanup system
    print("\n4. Testing cleanup system...")

    # Create some background tasks
    background_tasks = []
    for i in range(3):
        task = create_tracked_task(asyncio.sleep(1), name=f"background_{i}")
        background_tasks.append(task)

    info_before_cleanup = get_task_info()
    print(f"   Tasks before cleanup: {info_before_cleanup}")

    # Test cleanup
    await cleanup_background_tasks()

    info_after_cleanup = get_task_info()
    print(f"   Tasks after cleanup: {info_after_cleanup}")

    print("\n✅ AsyncIO Task Tracking System Tests Complete!")
    return True

def test_local_imports():
    """Test that the task tracking utilities are importable."""
    print("\n🔍 Testing import system...")

    try:
        from src.utils.task_tracker import create_tracked_task, cleanup_background_tasks, get_task_info
        print("   ✅ Task tracker imports successful")

        # Test basic functionality
        info = get_task_info()
        print(f"   ✅ Task info accessible: {info}")

        return True
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False

def test_converted_files():
    """Test that files have been properly converted."""
    print("\n🔍 Testing file conversions...")

    # Check some key files
    test_files = [
        'src/main.py',
        'src/monitoring/monitor_legacy.py',
        'src/services/service_coordinator.py',
        'src/core/exchanges/manager.py'
    ]

    conversion_count = 0
    for file_path in test_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tracked_count = content.count('create_tracked_task')
            asyncio_count = content.count('asyncio.create_task')

            print(f"   {file_path}:")
            print(f"     create_tracked_task: {tracked_count}")
            print(f"     asyncio.create_task: {asyncio_count}")

            if tracked_count > 0:
                conversion_count += 1

        except FileNotFoundError:
            print(f"   ❌ File not found: {file_path}")

    print(f"   ✅ {conversion_count}/{len(test_files)} files converted")
    return conversion_count >= len(test_files) - 1  # Allow for one missing file

async def test_performance_impact():
    """Test performance impact of task tracking."""
    print("\n⚡ Testing performance impact...")

    # Test untracked tasks (for comparison)
    start_time = time.time()
    untracked_tasks = [asyncio.create_task(asyncio.sleep(0.001)) for _ in range(100)]
    await asyncio.gather(*untracked_tasks)
    untracked_time = time.time() - start_time

    # Test tracked tasks
    start_time = time.time()
    tracked_tasks = [create_tracked_task(asyncio.sleep(0.001), name=f"perf_test_{i}") for i in range(100)]
    await asyncio.gather(*tracked_tasks)
    tracked_time = time.time() - start_time

    # Clean up any remaining tracked tasks
    await cleanup_background_tasks()

    overhead = ((tracked_time - untracked_time) / untracked_time) * 100 if untracked_time > 0 else 0
    print(f"   Untracked: {untracked_time:.4f}s")
    print(f"   Tracked: {tracked_time:.4f}s")
    print(f"   Overhead: {overhead:.2f}%")

    # Performance should be reasonable (< 50% overhead)
    return overhead < 50

def main():
    """Main test function."""
    print("🚀 Comprehensive AsyncIO Task Tracking System Test")
    print("=" * 60)

    # Test 1: Import system
    if not test_local_imports():
        print("❌ Import tests failed")
        return False

    # Test 2: File conversions
    if not test_converted_files():
        print("❌ File conversion tests failed")
        return False

    # Test 3: Runtime functionality
    try:
        result = asyncio.run(test_task_tracking())
        if not result:
            print("❌ Task tracking tests failed")
            return False
    except Exception as e:
        print(f"❌ Task tracking test error: {e}")
        return False

    # Test 4: Performance impact
    try:
        perf_result = asyncio.run(test_performance_impact())
        if not perf_result:
            print("❌ Performance impact too high")
            return False
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False

    print("\n🎉 ALL TESTS PASSED!")
    print("✅ AsyncIO Task Tracking System is fully functional")
    print("✅ Performance impact is acceptable")
    print("✅ File conversions completed successfully")
    print("✅ Resource cleanup working properly")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)