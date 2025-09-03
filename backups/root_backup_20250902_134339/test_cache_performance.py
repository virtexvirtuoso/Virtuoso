#!/usr/bin/env python3
"""
Comprehensive Performance Test for Cache Rationalization
Tests the performance of the consolidated DirectCacheAdapter
"""

import asyncio
import time
import statistics
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.cache_adapter_direct import DirectCacheAdapter, cache_adapter

async def performance_test():
    """Run comprehensive performance benchmarks"""
    
    print("🏃 Running Cache Performance Benchmarks")
    print("=" * 60)
    
    # Test each method multiple times (only existing methods)
    methods_to_test = [
        ('get_market_overview', cache_adapter.get_market_overview),
        ('get_dashboard_overview', cache_adapter.get_dashboard_overview),
        ('get_mobile_data', cache_adapter.get_mobile_data),
        ('get_signals', cache_adapter.get_signals),
        ('get_health_status', cache_adapter.get_health_status),
        ('get_alerts', cache_adapter.get_alerts),
        ('get_market_movers', cache_adapter.get_market_movers)
    ]
    
    results = {}
    iterations = 10
    
    for method_name, method in methods_to_test:
        times = []
        errors = 0
        
        print(f"\nTesting {method_name}...")
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                result = await method()
                end = time.perf_counter()
                
                elapsed = (end - start) * 1000  # Convert to milliseconds
                times.append(elapsed)
                
                # Validate result is not None
                if result is None:
                    errors += 1
                    print(f"  ⚠️ Iteration {i+1}: Returned None")
                
            except Exception as e:
                errors += 1
                print(f"  ❌ Iteration {i+1}: Error - {e}")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            
            results[method_name] = {
                'avg': avg_time,
                'min': min_time,
                'max': max_time,
                'median': median_time,
                'errors': errors
            }
            
            # Print results
            print(f"  ✅ Average: {avg_time:.2f}ms")
            print(f"  ✅ Median: {median_time:.2f}ms")
            print(f"  ✅ Min: {min_time:.2f}ms / Max: {max_time:.2f}ms")
            if errors > 0:
                print(f"  ⚠️ Errors: {errors}/{iterations}")
    
    # Overall summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    total_avg = sum(r['avg'] for r in results.values()) / len(results)
    total_errors = sum(r['errors'] for r in results.values())
    
    print(f"\n🎯 Overall Average Response Time: {total_avg:.2f}ms")
    
    if total_avg < 50:
        print("✅ EXCELLENT: <50ms average response time")
    elif total_avg < 100:
        print("✅ GOOD: <100ms average response time")
    elif total_avg < 200:
        print("⚠️ ACCEPTABLE: <200ms average response time")
    else:
        print("❌ NEEDS OPTIMIZATION: >200ms average response time")
    
    if total_errors == 0:
        print("✅ RELIABILITY: No errors detected")
    else:
        print(f"⚠️ RELIABILITY: {total_errors} errors detected")
    
    # Method-by-method breakdown
    print("\n📈 Method Performance Breakdown:")
    for method_name, stats in results.items():
        status = "✅" if stats['avg'] < 100 else "⚠️" if stats['avg'] < 200 else "❌"
        print(f"  {status} {method_name}: {stats['avg']:.2f}ms avg, {stats['median']:.2f}ms median")
    
    return results

async def stress_test():
    """Run concurrent stress test"""
    print("\n" + "=" * 60)
    print("💪 Running Concurrent Stress Test")
    print("=" * 60)
    
    concurrent_calls = 50
    print(f"\nMaking {concurrent_calls} concurrent calls...")
    
    start = time.perf_counter()
    
    # Create concurrent tasks
    tasks = []
    for _ in range(concurrent_calls):
        tasks.append(cache_adapter.get_dashboard_overview())
    
    # Execute all concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end = time.perf_counter()
    total_time = (end - start) * 1000
    
    # Count successes and failures
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = sum(1 for r in results if isinstance(r, Exception))
    
    print(f"\n✅ Completed {concurrent_calls} calls in {total_time:.2f}ms")
    print(f"✅ Average per call: {total_time/concurrent_calls:.2f}ms")
    print(f"✅ Successes: {successes}/{concurrent_calls}")
    if failures > 0:
        print(f"⚠️ Failures: {failures}/{concurrent_calls}")
    
    if failures == 0:
        print("\n🎉 STRESS TEST: PASSED - System handles concurrent load well")
    else:
        print(f"\n⚠️ STRESS TEST: {failures} failures under load")

async def main():
    """Run all performance tests"""
    print("\n🚀 CACHE RATIONALIZATION PERFORMANCE TEST SUITE")
    print("=" * 60)
    print("Testing the consolidated DirectCacheAdapter implementation")
    print("=" * 60)
    
    # Run performance benchmarks
    await performance_test()
    
    # Run stress test
    await stress_test()
    
    print("\n" + "=" * 60)
    print("✅ PERFORMANCE TEST SUITE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())