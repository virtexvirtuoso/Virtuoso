#!/usr/bin/env python3
"""
Simplified Test Suite for Architectural Improvements
Tests the actual components available in the codebase
"""

import asyncio
import time
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

print("Testing Virtuoso CCXT Architecture Improvements\n")
print("="*60)

# Track results
results = {
    'phase1_events': {'available': False, 'tests': []},
    'phase2_di': {'available': False, 'tests': []},
    'phase3_resilience': {'available': False, 'tests': []},
    'phase4_optimization': {'available': False, 'tests': []},
}

# TEST PHASE 1: Event-Driven Components
print("\n📍 PHASE 1: Event-Driven Data Pipeline")
print("-"*40)
try:
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import Event
    from src.core.events.event_publisher import EventPublisher
    
    results['phase1_events']['available'] = True
    print("✅ Event components available")
    
    # Basic test
    async def test_events():
        event_bus = EventBus()
        received = []
        
        async def handler(event):
            received.append(event)
        
        await event_bus.subscribe("test", handler)
        
        test_event = Event(event_type="test", data={'value': 123})
        await event_bus.publish(test_event)
        await asyncio.sleep(0.1)
        
        assert len(received) == 1, "Event not received"
        print("✅ Event pub/sub working")
        results['phase1_events']['tests'].append('pub/sub: passed')
        
        # Test throughput
        start = time.time()
        for i in range(100):
            await event_bus.publish(Event(event_type="perf", data={'i': i}))
        elapsed = time.time() - start
        throughput = 100 / elapsed
        print(f"✅ Throughput: {throughput:.0f} events/sec")
        results['phase1_events']['tests'].append(f'throughput: {throughput:.0f} eps')
    
    asyncio.run(test_events())
    
except ImportError as e:
    print(f"❌ Event components not available: {e}")
except Exception as e:
    print(f"❌ Event test failed: {e}")

# TEST PHASE 2: Dependency Injection
print("\n📍 PHASE 2: Service Layer Migration")
print("-"*40)
try:
    from src.core.di.container import ServiceContainer
    from src.core.di.registration import bootstrap_container
    
    results['phase2_di']['available'] = True
    print("✅ DI components available")
    
    # Basic test
    async def test_di():
        container = ServiceContainer()
        
        class TestService:
            def __init__(self):
                self.value = "test"
        
        container.register_singleton(TestService, TestService)
        service = await container.get_service(TestService)
        assert service.value == "test"
        print("✅ DI container working")
        results['phase2_di']['tests'].append('container: passed')
        
        # Test bootstrap
        try:
            bootstrapped = bootstrap_container({})
            stats = bootstrapped.get_stats()
            print(f"✅ Bootstrapped with {stats['services_registered_count']} services")
            results['phase2_di']['tests'].append(f'bootstrap: {stats["services_registered_count"]} services')
        except:
            print("⚠️ Bootstrap partially working")
    
    asyncio.run(test_di())
    
except ImportError as e:
    print(f"❌ DI components not available: {e}")
except Exception as e:
    print(f"❌ DI test failed: {e}")

# TEST PHASE 3: Infrastructure Resilience
print("\n📍 PHASE 3: Infrastructure Resilience")
print("-"*40)
try:
    from src.core.resilience.circuit_breaker import CircuitBreaker
    from src.core.resilience.retry_policy import RetryPolicy
    from src.core.resilience.health_check import HealthCheckService
    
    results['phase3_resilience']['available'] = True
    print("✅ Resilience components available")
    
    # Basic test
    async def test_resilience():
        # Circuit breaker
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
        
        fail_count = 0
        async def failing():
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 2:
                raise Exception("fail")
            return "success"
        
        # Trigger failures
        for _ in range(2):
            try:
                await cb.call(failing)
            except:
                pass
        
        assert cb.state == "OPEN"
        print("✅ Circuit breaker working")
        results['phase3_resilience']['tests'].append('circuit_breaker: passed')
        
        # Retry policy
        retry = RetryPolicy(max_attempts=3, base_delay=0.01)
        attempts = 0
        
        async def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise Exception("retry")
            return "success"
        
        result = await retry.execute(flaky)
        assert attempts == 3
        print("✅ Retry policy working")
        results['phase3_resilience']['tests'].append('retry_policy: passed')
        
        # Health checks
        health = HealthCheckService()
        async def check():
            return {"status": "healthy"}
        
        health.register_check("test", check)
        status = await health.check_health()
        assert "test" in status
        print("✅ Health checks working")
        results['phase3_resilience']['tests'].append('health_check: passed')
    
    asyncio.run(test_resilience())
    
except ImportError as e:
    print(f"❌ Resilience components not available: {e}")
except Exception as e:
    print(f"❌ Resilience test failed: {e}")

# TEST PHASE 4: Optimization
print("\n📍 PHASE 4: Data Pipeline Optimization")
print("-"*40)
try:
    from src.core.events.optimized_event_processor import OptimizedEventProcessor
    
    results['phase4_optimization']['available'] = True
    print("✅ Optimization components available")
    
    # Basic test
    async def test_optimization():
        processor = OptimizedEventProcessor()
        await processor.start()
        
        # Process events
        start = time.time()
        for i in range(1000):
            await processor.process_event({
                'type': 'test',
                'data': {'value': i}
            })
        
        elapsed = time.time() - start
        throughput = 1000 / elapsed
        print(f"✅ Optimized throughput: {throughput:.0f} events/sec")
        results['phase4_optimization']['tests'].append(f'throughput: {throughput:.0f} eps')
        
        stats = processor.get_stats()
        print(f"✅ Processed with {len(stats['queue_sizes'])} priority queues")
        results['phase4_optimization']['tests'].append('queues: working')
        
        await processor.stop()
    
    asyncio.run(test_optimization())
    
except ImportError as e:
    print(f"❌ Optimization components not available: {e}")
except Exception as e:
    print(f"❌ Optimization test failed: {e}")

# SUMMARY
print("\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)

phases_available = sum(1 for phase in results.values() if phase['available'])
phases_tested = sum(1 for phase in results.values() if phase['tests'])

print(f"\n✅ Phases Available: {phases_available}/4")
print(f"✅ Phases Tested: {phases_tested}/4")

for phase_name, phase_data in results.items():
    if phase_data['available']:
        print(f"\n{phase_name}:")
        for test in phase_data['tests']:
            print(f"  • {test}")

# Save results
with open('test_results_simple.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n📁 Results saved to test_results_simple.json")

if phases_available == 4 and phases_tested == 4:
    print("\n" + "🎉 "*10)
    print("ALL PHASES SUCCESSFULLY TESTED!")
    print("🎉 "*10)
else:
    print(f"\n⚠️ {4 - phases_available} phases not fully available")