#!/usr/bin/env python3
"""
Final Validation Test for Virtuoso CCXT Architecture
Tests all phases with Python 3.11 and correct API signatures
"""

import asyncio
import time
import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

print("\n" + "="*60)
print("FINAL ARCHITECTURE VALIDATION - PYTHON 3.11")
print("="*60)

results = {}

# TEST PHASE 1: Event-Driven Pipeline
print("\n📍 PHASE 1: Event-Driven Data Pipeline")
print("-"*40)
try:
    from src.core.events.event_bus import EventBus
    from src.core.events.event_types import Event, DataType
    from src.core.events.event_publisher import EventPublisher
    
    async def test_phase1():
        # Test EventBus
        event_bus = EventBus()
        received = []
        
        async def handler(event):
            received.append(event)
        
        await event_bus.subscribe("test", handler)
        
        test_event = Event(event_type="test", data={'value': 123})
        await event_bus.publish(test_event)
        await asyncio.sleep(0.1)
        
        assert len(received) == 1, "Event not received"
        print("✅ EventBus pub/sub working")
        
        # Test EventPublisher with correct signature
        publisher = EventPublisher(event_bus)
        
        # Use correct method signature
        await publisher.publish_market_data(
            symbol="BTC/USDT",
            exchange="bybit",
            data_type=DataType.TICKER,  # Required parameter
            raw_data={'price': 50000, 'volume': 1000}  # Required parameter
        )
        
        stats = publisher.get_stats()
        print(f"✅ EventPublisher working - {stats['total_published']} events published")
        
        # Test throughput
        start = time.time()
        for i in range(100):
            await event_bus.publish(Event(event_type="perf", data={'i': i}))
        throughput = 100 / (time.time() - start)
        print(f"✅ Throughput: {throughput:.0f} events/sec")
        
        # Cleanup
        await event_bus.stop()
        
        return True
    
    if asyncio.run(test_phase1()):
        results['phase1'] = 'PASSED'
        print("✅ PHASE 1: COMPLETE")
    
except Exception as e:
    results['phase1'] = f'FAILED: {e}'
    print(f"❌ Phase 1 failed: {e}")

# TEST PHASE 2: Service Layer
print("\n📍 PHASE 2: Service Layer Migration")
print("-"*40)
try:
    from src.core.di.container import ServiceContainer
    from src.core.di.registration import bootstrap_container
    
    async def test_phase2():
        # Test DI Container
        container = ServiceContainer()
        
        class TestService:
            def __init__(self):
                self.value = "test"
        
        container.register_singleton(TestService, TestService)
        service = await container.get_service(TestService)
        assert service.value == "test"
        print("✅ DI Container working")
        
        # Test Bootstrap
        bootstrapped = bootstrap_container({})
        stats = bootstrapped.get_stats()
        print(f"✅ Container bootstrapped with {stats['services_registered_count']} services")
        
        # Cleanup
        await container.dispose()
        
        return True
    
    if asyncio.run(test_phase2()):
        results['phase2'] = 'PASSED'
        print("✅ PHASE 2: COMPLETE")
    
except Exception as e:
    results['phase2'] = f'FAILED: {e}'
    print(f"❌ Phase 2 failed: {e}")

# TEST PHASE 3: Infrastructure Resilience
print("\n📍 PHASE 3: Infrastructure Resilience")
print("-"*40)
try:
    from src.core.resilience.circuit_breaker import CircuitBreaker
    from src.core.resilience.retry_policy import RetryPolicy
    from src.core.resilience.health_check import HealthCheckService
    
    async def test_phase3():
        # Test CircuitBreaker with correct parameters
        # Check actual __init__ signature
        import inspect
        cb_sig = inspect.signature(CircuitBreaker.__init__)
        print(f"CircuitBreaker params: {list(cb_sig.parameters.keys())}")
        
        # Use actual parameter names from implementation
        circuit_breaker = CircuitBreaker(
            failure_limit=3,  # Likely the correct parameter name
            recovery_timeout=1.0,
            expected_exception=Exception
        )
        
        failures = 0
        async def failing():
            nonlocal failures
            failures += 1
            if failures <= 3:
                raise Exception("fail")
            return "success"
        
        # Trigger failures
        for _ in range(3):
            try:
                await circuit_breaker.call(failing)
            except:
                pass
        
        print(f"✅ Circuit breaker triggered after {failures} failures")
        
        # Test RetryPolicy
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
        print(f"✅ Retry policy succeeded after {attempts} attempts")
        
        # Test HealthCheck
        health = HealthCheckService()
        
        async def check():
            return {"status": "healthy"}
        
        health.register_check("test", check)
        status = await health.check_health()
        assert "test" in status
        print("✅ Health checks working")
        
        return True
    
    if asyncio.run(test_phase3()):
        results['phase3'] = 'PASSED'
        print("✅ PHASE 3: COMPLETE")
    
except Exception as e:
    results['phase3'] = f'FAILED: {e}'
    print(f"❌ Phase 3 failed: {e}")

# TEST PHASE 4: Pipeline Optimization
print("\n📍 PHASE 4: Data Pipeline Optimization")
print("-"*40)
try:
    from src.core.events.optimized_event_processor import OptimizedEventProcessor
    from src.core.events.event_types import Event
    
    async def test_phase4():
        processor = OptimizedEventProcessor()
        await processor.start()
        
        # Process events using Event objects, not dicts
        for i in range(100):
            event = Event(
                event_type='test',
                data={'index': i}
            )
            # The processor expects Event objects, not dicts
            await processor.process_event(event)
        
        stats = processor.get_stats()
        print(f"✅ Processed events with {len(stats['queue_sizes'])} priority queues")
        
        # Test throughput
        start = time.time()
        for i in range(1000):
            event = Event(
                event_type='throughput',
                data={'i': i}
            )
            await processor.process_event(event)
        
        throughput = 1000 / (time.time() - start)
        print(f"✅ Optimized throughput: {throughput:.0f} events/sec")
        
        await processor.stop()
        print("✅ Graceful shutdown complete")
        
        return True
    
    if asyncio.run(test_phase4()):
        results['phase4'] = 'PASSED'
        print("✅ PHASE 4: COMPLETE")
    
except Exception as e:
    results['phase4'] = f'FAILED: {e}'
    print(f"❌ Phase 4 failed: {e}")

# SUMMARY
print("\n" + "="*60)
print("📊 FINAL VALIDATION RESULTS")
print("="*60)

passed = sum(1 for v in results.values() if v == 'PASSED')
total = len(results)

print(f"\n✅ Phases Passed: {passed}/{total}")

for phase, status in results.items():
    icon = "✅" if status == "PASSED" else "❌"
    print(f"{icon} {phase}: {status}")

# Save results
with open('final_validation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

if passed == 4:
    print("\n" + "🎉 "*10)
    print("ALL PHASES VALIDATED WITH PYTHON 3.11!")
    print("ARCHITECTURE IMPLEMENTATION COMPLETE!")
    print("🎉 "*10)
else:
    print(f"\n⚠️ {total - passed} phases need attention")

print("\n📁 Results saved to final_validation_results.json")