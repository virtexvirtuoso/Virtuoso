#!/usr/bin/env python3
"""
Phase 2 Cache Performance Test
Compares Memcached vs Phase 1 in-memory cache
"""

import sys
import time
import json
import statistics
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

def test_cache_performance():
    """Test and compare cache performance"""
    
    print("=" * 60)
    print("🚀 Phase 2 Cache Performance Test")
    print("=" * 60)
    print()
    
    # Initialize cache router
    from src.core.cache.cache_router import cache_router
    
    # Test data
    test_data = {
        'small': {'key': 'test_small', 'value': 'x' * 100},  # 100 bytes
        'medium': {'key': 'test_medium', 'value': {'data': 'x' * 1000, 'list': list(range(100))}},  # ~1KB
        'large': {'key': 'test_large', 'value': {'symbols': ['BTC'] * 100, 'data': 'x' * 10000}},  # ~10KB
    }
    
    results = {}
    
    for size_name, test_case in test_data.items():
        print(f"\n📊 Testing {size_name} data ({len(str(test_case['value']))} bytes)")
        print("-" * 40)
        
        key = test_case['key']
        value = test_case['value']
        
        # Test Memcached
        memcached_times = []
        for i in range(100):
            # Set
            start = time.perf_counter()
            cache_router.set(key + f'_mc_{i}', value, use_memcached=True, use_fallback=False)
            set_time = (time.perf_counter() - start) * 1000
            
            # Get
            start = time.perf_counter()
            retrieved = cache_router.get(key + f'_mc_{i}', use_memcached=True)
            get_time = (time.perf_counter() - start) * 1000
            
            if retrieved:
                memcached_times.append({'set': set_time, 'get': get_time})
        
        # Test Phase 1 Memory Cache
        memory_times = []
        for i in range(100):
            # Set
            start = time.perf_counter()
            cache_router.set(key + f'_mem_{i}', value, use_memcached=False, use_fallback=True)
            set_time = (time.perf_counter() - start) * 1000
            
            # Get
            start = time.perf_counter()
            retrieved = cache_router.get(key + f'_mem_{i}', use_memcached=False)
            get_time = (time.perf_counter() - start) * 1000
            
            if retrieved:
                memory_times.append({'set': set_time, 'get': get_time})
        
        # Calculate statistics
        if memcached_times:
            mc_get_times = [t['get'] for t in memcached_times]
            mc_set_times = [t['set'] for t in memcached_times]
            mc_stats = {
                'avg_get': statistics.mean(mc_get_times),
                'min_get': min(mc_get_times),
                'max_get': max(mc_get_times),
                'p95_get': statistics.quantiles(mc_get_times, n=20)[18],  # 95th percentile
                'avg_set': statistics.mean(mc_set_times),
            }
        else:
            mc_stats = None
        
        if memory_times:
            mem_get_times = [t['get'] for t in memory_times]
            mem_set_times = [t['set'] for t in memory_times]
            mem_stats = {
                'avg_get': statistics.mean(mem_get_times),
                'min_get': min(mem_get_times),
                'max_get': max(mem_get_times),
                'p95_get': statistics.quantiles(mem_get_times, n=20)[18],
                'avg_set': statistics.mean(mem_set_times),
            }
        else:
            mem_stats = None
        
        # Print results
        if mc_stats and mem_stats:
            improvement = ((mem_stats['avg_get'] - mc_stats['avg_get']) / mem_stats['avg_get']) * 100
            
            print(f"\n✅ Memcached (Phase 2):")
            print(f"  GET: avg={mc_stats['avg_get']:.2f}ms, min={mc_stats['min_get']:.2f}ms, p95={mc_stats['p95_get']:.2f}ms")
            print(f"  SET: avg={mc_stats['avg_set']:.2f}ms")
            
            print(f"\n📦 Memory Cache (Phase 1):")
            print(f"  GET: avg={mem_stats['avg_get']:.2f}ms, min={mem_stats['min_get']:.2f}ms, p95={mem_stats['p95_get']:.2f}ms")
            print(f"  SET: avg={mem_stats['avg_set']:.2f}ms")
            
            print(f"\n🎯 Improvement: {improvement:.1f}% faster with Memcached")
            
            results[size_name] = {
                'memcached': mc_stats,
                'memory': mem_stats,
                'improvement_percent': improvement
            }
    
    # Print router statistics
    print("\n" + "=" * 60)
    print("📈 Cache Router Statistics")
    print("=" * 60)
    router_stats = cache_router.get_stats()
    for key, value in router_stats.items():
        print(f"  {key}: {value}")
    
    # Health check
    print("\n" + "=" * 60)
    print("🏥 Health Check")
    print("=" * 60)
    health = cache_router.health_check()
    print(f"  Memcached: {health['caches'].get('memcached', 'unknown')}")
    print(f"  Memory Cache: {health['caches'].get('memory', 'unknown')}")
    
    return results

if __name__ == "__main__":
    try:
        results = test_cache_performance()
        
        # Summary
        print("\n" + "=" * 60)
        print("✨ PHASE 2 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        avg_improvements = []
        for size, data in results.items():
            if 'improvement_percent' in data:
                avg_improvements.append(data['improvement_percent'])
                print(f"  {size.upper()}: {data['improvement_percent']:.1f}% faster")
        
        if avg_improvements:
            overall = statistics.mean(avg_improvements)
            print(f"\n🏆 Overall: Memcached is {overall:.1f}% faster than Phase 1")
            
            if overall > 50:
                print("🎉 EXCELLENT! Phase 2 achieving target performance!")
            elif overall > 20:
                print("✅ Good improvement with Phase 2")
            else:
                print("⚠️ Modest improvement, may need tuning")
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()