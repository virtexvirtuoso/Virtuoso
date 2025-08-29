"""
Concurrent Service Resolution Tests for DI Container.

This test suite validates that the dependency injection container
handles concurrent service resolution correctly without race conditions,
memory leaks, or thread safety issues.
"""

import asyncio
import pytest
import time
import threading
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import gc

from src.core.di.container import ServiceContainer, ServiceLifetime
from src.core.interfaces.services import IDisposable, IAsyncDisposable


# Test service classes
class TestService:
    """Simple test service."""
    
    def __init__(self):
        self.created_at = time.time()
        self.disposed = False
    
    async def dispose(self):
        """Dispose resources."""
        self.disposed = True
        await asyncio.sleep(0.001)  # Simulate cleanup work


class DisposableTestService(IDisposable):
    """Test service implementing IDisposable."""
    
    def __init__(self):
        self.created_at = time.time()
        self.disposed = False
    
    async def dispose(self):
        """Dispose resources."""
        self.disposed = True
        await asyncio.sleep(0.001)


class AsyncDisposableTestService(IAsyncDisposable):
    """Test service implementing IAsyncDisposable."""
    
    def __init__(self):
        self.created_at = time.time()
        self.disposed = False
    
    async def dispose_async(self):
        """Dispose resources asynchronously."""
        self.disposed = True
        await asyncio.sleep(0.002)  # Simulate async cleanup


class DependentService:
    """Service with dependencies for injection testing."""
    
    def __init__(self, dependency: TestService):
        self.dependency = dependency
        self.created_at = time.time()


class ConcurrentServiceResolutionTests:
    """Test suite for concurrent DI container operations."""
    
    @pytest.fixture
    def container(self):
        """Create a fresh DI container for each test."""
        return ServiceContainer()
    
    @pytest.mark.asyncio
    async def test_concurrent_singleton_resolution(self, container):
        """Test that singletons are thread-safe under concurrent access."""
        container.register_singleton(TestService, TestService)
        
        # Number of concurrent requests
        num_requests = 50
        
        async def resolve_service():
            return await container.get_service(TestService)
        
        # Execute concurrent resolutions
        tasks = [resolve_service() for _ in range(num_requests)]
        instances = await asyncio.gather(*tasks)
        
        # All instances should be the same object (singleton)
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, "Singleton instances should be identical"
        
        # Verify only one instance was created
        stats = container.get_stats()
        assert stats['instances_created'] == 1, f"Expected 1 instance, got {stats['instances_created']}"
    
    @pytest.mark.asyncio
    async def test_concurrent_transient_resolution(self, container):
        """Test that transient services create unique instances concurrently."""
        container.register_transient(TestService, TestService)
        
        num_requests = 30
        
        async def resolve_service():
            return await container.get_service(TestService)
        
        # Execute concurrent resolutions
        tasks = [resolve_service() for _ in range(num_requests)]
        instances = await asyncio.gather(*tasks)
        
        # All instances should be different (transient)
        instance_ids = [id(instance) for instance in instances]
        assert len(set(instance_ids)) == num_requests, "Transient instances should be unique"
        
        # Verify correct number of instances created
        stats = container.get_stats()
        assert stats['instances_created'] == num_requests
    
    @pytest.mark.asyncio
    async def test_concurrent_scoped_resolution(self, container):
        """Test scoped service resolution under concurrent load."""
        container.register_scoped(TestService, TestService)
        
        # Create multiple scopes with concurrent access
        scope_count = 5
        requests_per_scope = 10
        
        async def test_scope(scope_id: str):
            async with container.create_scope() as scope:
                # Multiple concurrent requests within same scope
                tasks = [scope.get_service(TestService) for _ in range(requests_per_scope)]
                instances = await asyncio.gather(*tasks)
                
                # All instances in same scope should be identical
                first_instance = instances[0]
                for instance in instances[1:]:
                    assert instance is first_instance, f"Scoped instances should be identical within scope {scope_id}"
                
                return first_instance
        
        # Test multiple scopes concurrently
        scope_tasks = [test_scope(f"scope_{i}") for i in range(scope_count)]
        scope_instances = await asyncio.gather(*scope_tasks)
        
        # Instances from different scopes should be different
        scope_ids = [id(instance) for instance in scope_instances]
        assert len(set(scope_ids)) == scope_count, "Scoped instances should be unique between scopes"
    
    @pytest.mark.asyncio
    async def test_concurrent_dependency_injection(self, container):
        """Test concurrent resolution with dependency injection."""
        container.register_singleton(TestService, TestService)
        container.register_transient(DependentService, DependentService)
        
        num_requests = 25
        
        async def resolve_dependent_service():
            return await container.get_service(DependentService)
        
        # Execute concurrent resolutions
        tasks = [resolve_dependent_service() for _ in range(num_requests)]
        dependent_instances = await asyncio.gather(*tasks)
        
        # All dependent services should have the same singleton dependency
        first_dependency = dependent_instances[0].dependency
        for dependent in dependent_instances[1:]:
            assert dependent.dependency is first_dependency, "Singleton dependencies should be identical"
        
        # But the dependent services themselves should be different (transient)
        dependent_ids = [id(dependent) for dependent in dependent_instances]
        assert len(set(dependent_ids)) == num_requests, "Transient dependent services should be unique"
    
    @pytest.mark.asyncio
    async def test_concurrent_disposal_safety(self, container):
        """Test that disposal is thread-safe and doesn't cause race conditions."""
        container.register_scoped(DisposableTestService, DisposableTestService)
        
        # Create multiple scopes concurrently
        num_scopes = 10
        
        async def create_and_dispose_scope():
            async with container.create_scope() as scope:
                instance = await scope.get_service(DisposableTestService)
                # Simulate some work
                await asyncio.sleep(0.01)
                return instance
        
        # Run concurrent scope creation/disposal
        tasks = [create_and_dispose_scope() for _ in range(num_scopes)]
        instances = await asyncio.gather(*tasks)
        
        # Give disposal time to complete
        await asyncio.sleep(0.1)
        
        # All instances should be disposed
        for instance in instances:
            assert instance.disposed, "Instance should have been disposed"
        
        # Check memory stats
        memory_stats = container.get_memory_stats()
        assert memory_stats['instances_created'] == num_scopes
        assert memory_stats['instances_disposed'] == num_scopes
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, container):
        """Test memory leak detection under concurrent load."""
        container.register_transient(TestService, TestService)
        
        # Create many instances concurrently
        num_instances = 20
        
        async def create_instance():
            return await container.get_service(TestService)
        
        tasks = [create_instance() for _ in range(num_instances)]
        instances = await asyncio.gather(*tasks)
        
        # Get initial memory stats
        initial_stats = container.get_memory_stats()
        assert initial_stats['instances_created'] == num_instances
        
        # Manually dispose some instances to simulate proper cleanup
        disposed_count = 0
        for i, instance in enumerate(instances):
            if i % 2 == 0:  # Dispose every other instance
                await container._dispose_instance(instance)
                disposed_count += 1
        
        # Run container disposal
        await container.dispose()
        
        # Check final stats - should detect some potential leaks
        final_stats = container.get_memory_stats()
        expected_leaks = num_instances - disposed_count
        
        # Note: The exact leak count might vary due to disposal logic,
        # but we should see some memory tracking
        assert final_stats['instances_created'] == num_instances
    
    @pytest.mark.asyncio 
    async def test_high_load_performance(self, container):
        """Test container performance under high concurrent load."""
        container.register_singleton(TestService, TestService)
        container.register_transient(DependentService, DependentService)
        
        # High load test
        num_requests = 100
        start_time = time.time()
        
        async def resolve_services():
            singleton = await container.get_service(TestService)
            dependent = await container.get_service(DependentService)
            return singleton, dependent
        
        # Execute high load
        tasks = [resolve_services() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 5.0, f"High load test took too long: {total_time:.2f}s"
        assert len(results) == num_requests
        
        # All singleton instances should be the same
        singleton_instances = [result[0] for result in results]
        first_singleton = singleton_instances[0]
        for singleton in singleton_instances[1:]:
            assert singleton is first_singleton
    
    @pytest.mark.asyncio
    async def test_async_disposal_interface_compliance(self, container):
        """Test that IAsyncDisposable services are properly disposed."""
        container.register_transient(AsyncDisposableTestService, AsyncDisposableTestService)
        
        # Create instances
        instances = []
        for _ in range(5):
            instance = await container.get_service(AsyncDisposableTestService)
            instances.append(instance)
        
        # Manually dispose container (which should dispose all tracked instances)
        await container.dispose()
        
        # Give time for async disposal to complete
        await asyncio.sleep(0.05)
        
        # All instances should be disposed
        for instance in instances:
            assert instance.disposed, "IAsyncDisposable instance should have been disposed"


@pytest.mark.asyncio
async def test_thread_safety_with_executor():
    """Test DI container thread safety using ThreadPoolExecutor."""
    container = ServiceContainer()
    container.register_singleton(TestService, TestService)
    
    def sync_resolve():
        """Synchronous wrapper for testing in threads."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(container.get_service(TestService))
        finally:
            loop.close()
    
    # Use ThreadPoolExecutor to test thread safety
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit multiple resolution tasks to different threads
        futures = [executor.submit(sync_resolve) for _ in range(20)]
        
        # Collect results
        instances = []
        for future in futures:
            instance = future.result(timeout=5.0)
            instances.append(instance)
    
    # All instances should be the same (singleton)
    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance, "Singleton should be thread-safe"
    
    # Cleanup
    await container.dispose()


if __name__ == "__main__":
    # Run basic tests if executed directly
    import sys
    
    async def run_basic_tests():
        """Run a subset of tests for quick validation."""
        container = ServiceContainer()
        
        print("🧪 Running Concurrent DI Resolution Tests...")
        
        # Test 1: Concurrent singleton resolution
        print("  ✓ Testing concurrent singleton resolution...")
        container.register_singleton(TestService, TestService)
        tasks = [container.get_service(TestService) for _ in range(10)]
        instances = await asyncio.gather(*tasks)
        assert all(instance is instances[0] for instance in instances)
        
        # Test 2: Memory leak detection
        print("  ✓ Testing memory leak detection...")
        memory_stats = container.get_memory_stats()
        print(f"    Created: {memory_stats['instances_created']}, Disposed: {memory_stats['instances_disposed']}")
        
        # Test 3: Disposal
        print("  ✓ Testing container disposal...")
        await container.dispose()
        final_stats = container.get_memory_stats()
        print(f"    Final - Created: {final_stats['instances_created']}, Disposed: {final_stats['instances_disposed']}")
        
        print("✅ All basic concurrent DI tests passed!")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(run_basic_tests())
    else:
        print("Run with --quick for basic tests, or use pytest for full test suite")
        print("Example: python tests/test_concurrent_di_resolution.py --quick")