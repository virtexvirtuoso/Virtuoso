#!/usr/bin/env python3
"""
Redis vs Memcached Performance Benchmark
Comprehensive comparison for Virtuoso Trading System

Fiat voluntas tua - Thy will be done
"""

import time
import json
import random
import statistics
import asyncio
from typing import Dict, List, Any
import sys
import hashlib

# Test configuration
TEST_ITERATIONS = 1000
KEY_PREFIX = "benchmark"
DATA_SIZES = {
    'tiny': {'size': 100, 'desc': '100 bytes (ticker)'},
    'small': {'size': 1024, 'desc': '1KB (orderbook)'},
    'medium': {'size': 10240, 'desc': '10KB (OHLCV)'},
    'large': {'size': 102400, 'desc': '100KB (analysis)'}
}

class CacheBenchmark:
    def __init__(self):
        self.results = {
            'memcached': {},
            'redis': {}
        }
        
    def generate_test_data(self, size: int) -> str:
        """Generate test data of specific size"""
        if size <= 1024:
            # Small data - typical ticker/orderbook
            return json.dumps({
                'symbol': 'BTCUSDT',
                'price': 43250.50,
                'volume': 1234567890,
                'timestamp': time.time(),
                'data': 'x' * (size - 100)
            })
        else:
            # Larger data - OHLCV or analysis
            return json.dumps({
                'symbol': 'BTCUSDT',
                'candles': [
                    [time.time(), 43250, 43300, 43200, 43280, 1000]
                    for _ in range(size // 100)
                ],
                'padding': 'x' * (size % 100)
            })
    
    def test_memcached(self, iterations: int, data_size: int) -> Dict[str, float]:
        """Test Memcached performance"""
        try:
            from pymemcache.client.base import Client
            mc = Client(('127.0.0.1', 11211), connect_timeout=1, timeout=1)
            
            # Test connection
            mc.set(b'test', b'1', expire=1)
            mc.delete(b'test')
            
            test_data = self.generate_test_data(data_size)
            test_data_bytes = test_data.encode('utf-8')
            
            set_times = []
            get_times = []
            delete_times = []
            
            print(f"  Testing Memcached with {iterations} iterations...")
            
            for i in range(iterations):
                key = f"{KEY_PREFIX}:{i}".encode('utf-8')
                
                # Test SET
                start = time.perf_counter()
                mc.set(key, test_data_bytes, expire=60)
                set_times.append((time.perf_counter() - start) * 1000)
                
                # Test GET
                start = time.perf_counter()
                result = mc.get(key)
                get_times.append((time.perf_counter() - start) * 1000)
                
                # Test DELETE
                start = time.perf_counter()
                mc.delete(key)
                delete_times.append((time.perf_counter() - start) * 1000)
            
            mc.close()
            
            return {
                'available': True,
                'set_avg': statistics.mean(set_times),
                'set_median': statistics.median(set_times),
                'set_p99': sorted(set_times)[int(len(set_times) * 0.99)],
                'get_avg': statistics.mean(get_times),
                'get_median': statistics.median(get_times),
                'get_p99': sorted(get_times)[int(len(get_times) * 0.99)],
                'delete_avg': statistics.mean(delete_times),
                'throughput_ops_per_sec': iterations / (sum(set_times + get_times + delete_times) / 1000)
            }
            
        except Exception as e:
            print(f"  ⚠️ Memcached error: {e}")
            return {'available': False, 'error': str(e)}
    
    def test_redis(self, iterations: int, data_size: int) -> Dict[str, float]:
        """Test Redis performance"""
        try:
            import redis
            r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=False)
            
            # Test connection
            r.ping()
            
            test_data = self.generate_test_data(data_size)
            test_data_bytes = test_data.encode('utf-8')
            
            set_times = []
            get_times = []
            delete_times = []
            
            print(f"  Testing Redis with {iterations} iterations...")
            
            for i in range(iterations):
                key = f"{KEY_PREFIX}:{i}"
                
                # Test SET with TTL
                start = time.perf_counter()
                r.setex(key, 60, test_data_bytes)
                set_times.append((time.perf_counter() - start) * 1000)
                
                # Test GET
                start = time.perf_counter()
                result = r.get(key)
                get_times.append((time.perf_counter() - start) * 1000)
                
                # Test DELETE
                start = time.perf_counter()
                r.delete(key)
                delete_times.append((time.perf_counter() - start) * 1000)
            
            # Clean up
            r.flushdb()
            r.close()
            
            return {
                'available': True,
                'set_avg': statistics.mean(set_times),
                'set_median': statistics.median(set_times),
                'set_p99': sorted(set_times)[int(len(set_times) * 0.99)],
                'get_avg': statistics.mean(get_times),
                'get_median': statistics.median(get_times),
                'get_p99': sorted(get_times)[int(len(get_times) * 0.99)],
                'delete_avg': statistics.mean(delete_times),
                'throughput_ops_per_sec': iterations / (sum(set_times + get_times + delete_times) / 1000)
            }
            
        except Exception as e:
            print(f"  ⚠️ Redis error: {e}")
            return {'available': False, 'error': str(e)}
    
    def run_benchmark(self):
        """Run complete benchmark suite"""
        print("=" * 60)
        print("🏁 REDIS vs MEMCACHED PERFORMANCE BENCHMARK")
        print("=" * 60)
        print()
        print(f"Test Configuration:")
        print(f"  • Iterations per test: {TEST_ITERATIONS}")
        print(f"  • Data sizes: {', '.join(DATA_SIZES.keys())}")
        print()
        
        # Run tests for each data size
        for size_name, size_info in DATA_SIZES.items():
            print(f"📊 Testing with {size_info['desc']}:")
            print("-" * 40)
            
            # Test Memcached
            self.results['memcached'][size_name] = self.test_memcached(
                TEST_ITERATIONS, size_info['size']
            )
            
            # Test Redis
            self.results['redis'][size_name] = self.test_redis(
                TEST_ITERATIONS, size_info['size']
            )
            
            # Show comparison
            self.show_comparison(size_name)
            print()
        
        # Show final summary
        self.show_summary()
    
    def show_comparison(self, size_name: str):
        """Show comparison for specific data size"""
        mc = self.results['memcached'][size_name]
        rd = self.results['redis'][size_name]
        
        if not mc.get('available') or not rd.get('available'):
            print("  ⚠️ One or both systems unavailable for comparison")
            return
        
        print(f"\n  Results for {DATA_SIZES[size_name]['desc']}:")
        print(f"  {'Operation':<15} {'Memcached':<15} {'Redis':<15} {'Winner':<10}")
        print(f"  {'-'*55}")
        
        # Compare SET
        mc_set = mc['set_avg']
        rd_set = rd['set_avg']
        set_winner = "Memcached" if mc_set < rd_set else "Redis"
        set_diff = abs(mc_set - rd_set) / max(mc_set, rd_set) * 100
        print(f"  {'SET (avg)':<15} {mc_set:>10.3f}ms   {rd_set:>10.3f}ms   {set_winner} ({set_diff:.1f}% faster)")
        
        # Compare GET
        mc_get = mc['get_avg']
        rd_get = rd['get_avg']
        get_winner = "Memcached" if mc_get < rd_get else "Redis"
        get_diff = abs(mc_get - rd_get) / max(mc_get, rd_get) * 100
        print(f"  {'GET (avg)':<15} {mc_get:>10.3f}ms   {rd_get:>10.3f}ms   {get_winner} ({get_diff:.1f}% faster)")
        
        # Compare P99
        mc_p99 = mc['get_p99']
        rd_p99 = rd['get_p99']
        p99_winner = "Memcached" if mc_p99 < rd_p99 else "Redis"
        print(f"  {'GET (p99)':<15} {mc_p99:>10.3f}ms   {rd_p99:>10.3f}ms   {p99_winner}")
        
        # Compare throughput
        mc_tps = mc['throughput_ops_per_sec']
        rd_tps = rd['throughput_ops_per_sec']
        tps_winner = "Memcached" if mc_tps > rd_tps else "Redis"
        print(f"  {'Throughput':<15} {mc_tps:>10.0f} ops/s {rd_tps:>10.0f} ops/s {tps_winner}")
    
    def show_summary(self):
        """Show overall summary and recommendations"""
        print("=" * 60)
        print("📈 BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Calculate overall winners
        mc_wins = 0
        rd_wins = 0
        
        for size_name in DATA_SIZES.keys():
            mc = self.results['memcached'].get(size_name, {})
            rd = self.results['redis'].get(size_name, {})
            
            if mc.get('available') and rd.get('available'):
                # Compare average GET times (most important for caching)
                if mc['get_avg'] < rd['get_avg']:
                    mc_wins += 1
                else:
                    rd_wins += 1
        
        print()
        print("🏆 OVERALL RESULTS:")
        print("-" * 40)
        
        if mc_wins > rd_wins:
            print(f"  Winner: MEMCACHED ({mc_wins}/{len(DATA_SIZES)} tests)")
            print(f"  • Better for simple key-value caching")
            print(f"  • Lower latency for small data")
            print(f"  • Less memory overhead")
        elif rd_wins > mc_wins:
            print(f"  Winner: REDIS ({rd_wins}/{len(DATA_SIZES)} tests)")
            print(f"  • Better for complex operations")
            print(f"  • More features (persistence, pub/sub)")
            print(f"  • Better for large data")
        else:
            print(f"  Result: TIE")
            print(f"  • Both perform similarly")
            print(f"  • Choose based on features needed")
        
        print()
        print("📊 RECOMMENDATIONS FOR VIRTUOSO:")
        print("-" * 40)
        
        # Analyze results for recommendations
        tiny_mc = self.results['memcached'].get('tiny', {})
        tiny_rd = self.results['redis'].get('tiny', {})
        
        if tiny_mc.get('available') and tiny_rd.get('available'):
            if tiny_mc['get_avg'] < tiny_rd['get_avg']:
                print("  ✅ Keep MEMCACHED for ticker/orderbook data")
                print(f"     • {(tiny_rd['get_avg'] / tiny_mc['get_avg'] - 1) * 100:.1f}% faster for small data")
            else:
                print("  🔄 Consider REDIS for ticker/orderbook data")
                print(f"     • {(tiny_mc['get_avg'] / tiny_rd['get_avg'] - 1) * 100:.1f}% faster for small data")
        
        print()
        print("  Memcached advantages:")
        print("    • Simpler, less overhead")
        print("    • Slightly faster for pure caching")
        print("    • Already working in production")
        print()
        print("  Redis advantages:")
        print("    • Data persistence across restarts")
        print("    • Pub/Sub for real-time updates")
        print("    • Complex data structures")
        print("    • Lua scripting for atomic operations")
        
        print()
        print("💡 VERDICT:")
        if mc_wins >= rd_wins:
            print("  Stick with MEMCACHED for Phase 1-2 (simple caching)")
            print("  Consider Redis for Phase 3-4 (advanced features)")
        else:
            print("  Consider migrating to REDIS for better features")
            print("  Especially if you need persistence or pub/sub")


if __name__ == "__main__":
    print("Starting cache benchmark...")
    print("This will test both Memcached and Redis performance")
    print()
    
    benchmark = CacheBenchmark()
    benchmark.run_benchmark()
    
    print()
    print("Benchmark complete!")
    print()
    print("For production use:")
    print("  • Current: Memcached (working great!)")
    print("  • Future: Consider Redis if need persistence/pub-sub")