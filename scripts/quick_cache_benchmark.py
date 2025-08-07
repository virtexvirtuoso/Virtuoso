#!/usr/bin/env python3
"""
Quick Redis vs Memcached Benchmark
Simplified version for fast comparison
"""

import time
import json
import statistics

TEST_ITERATIONS = 100
TEST_DATA = {
    'symbol': 'BTCUSDT',
    'price': 43250.50,
    'volume': 1234567890,
    'timestamp': time.time(),
    'orderbook': {
        'bids': [[43250, 100], [43249, 200], [43248, 300]],
        'asks': [[43251, 100], [43252, 200], [43253, 300]]
    }
}

def test_memcached():
    """Test Memcached performance"""
    try:
        from pymemcache.client.base import Client
        mc = Client(('127.0.0.1', 11211))
        
        data = json.dumps(TEST_DATA).encode('utf-8')
        times = []
        
        # Warmup
        mc.set(b'test', data, expire=10)
        mc.get(b'test')
        
        # Test
        for i in range(TEST_ITERATIONS):
            key = f'bench:{i}'.encode()
            
            # Write
            start = time.perf_counter()
            mc.set(key, data, expire=60)
            write_time = time.perf_counter() - start
            
            # Read
            start = time.perf_counter()
            result = mc.get(key)
            read_time = time.perf_counter() - start
            
            times.append((write_time * 1000, read_time * 1000))
            mc.delete(key)
        
        mc.close()
        
        write_times = [t[0] for t in times]
        read_times = [t[1] for t in times]
        
        return {
            'write_avg': statistics.mean(write_times),
            'write_p99': sorted(write_times)[int(len(write_times) * 0.99)],
            'read_avg': statistics.mean(read_times),
            'read_p99': sorted(read_times)[int(len(read_times) * 0.99)]
        }
    except Exception as e:
        return {'error': str(e)}

def test_redis():
    """Test Redis performance"""
    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=False)
        r.ping()
        
        data = json.dumps(TEST_DATA).encode('utf-8')
        times = []
        
        # Warmup
        r.setex('test', 10, data)
        r.get('test')
        
        # Test
        for i in range(TEST_ITERATIONS):
            key = f'bench:{i}'
            
            # Write
            start = time.perf_counter()
            r.setex(key, 60, data)
            write_time = time.perf_counter() - start
            
            # Read
            start = time.perf_counter()
            result = r.get(key)
            read_time = time.perf_counter() - start
            
            times.append((write_time * 1000, read_time * 1000))
            r.delete(key)
        
        r.close()
        
        write_times = [t[0] for t in times]
        read_times = [t[1] for t in times]
        
        return {
            'write_avg': statistics.mean(write_times),
            'write_p99': sorted(write_times)[int(len(write_times) * 0.99)],
            'read_avg': statistics.mean(read_times),
            'read_p99': sorted(read_times)[int(len(read_times) * 0.99)]
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == "__main__":
    print("=" * 50)
    print("REDIS vs MEMCACHED - QUICK BENCHMARK")
    print("=" * 50)
    print(f"Test: {TEST_ITERATIONS} iterations")
    print(f"Data size: ~500 bytes (typical ticker+orderbook)")
    print()
    
    # Test Memcached
    print("Testing Memcached...")
    mc_results = test_memcached()
    
    # Test Redis
    print("Testing Redis...")
    rd_results = test_redis()
    
    print()
    print("RESULTS:")
    print("-" * 50)
    
    if 'error' not in mc_results and 'error' not in rd_results:
        print(f"{'Metric':<20} {'Memcached':<15} {'Redis':<15}")
        print(f"{'='*50}")
        print(f"{'Write Avg (ms)':<20} {mc_results['write_avg']:>10.3f}     {rd_results['write_avg']:>10.3f}")
        print(f"{'Write P99 (ms)':<20} {mc_results['write_p99']:>10.3f}     {rd_results['write_p99']:>10.3f}")
        print(f"{'Read Avg (ms)':<20} {mc_results['read_avg']:>10.3f}     {rd_results['read_avg']:>10.3f}")
        print(f"{'Read P99 (ms)':<20} {mc_results['read_p99']:>10.3f}     {rd_results['read_p99']:>10.3f}")
        
        print()
        print("WINNER BY OPERATION:")
        print("-" * 50)
        
        # Compare writes
        if mc_results['write_avg'] < rd_results['write_avg']:
            diff = (rd_results['write_avg'] / mc_results['write_avg'] - 1) * 100
            print(f"Write: Memcached ({diff:.1f}% faster)")
        else:
            diff = (mc_results['write_avg'] / rd_results['write_avg'] - 1) * 100
            print(f"Write: Redis ({diff:.1f}% faster)")
        
        # Compare reads
        if mc_results['read_avg'] < rd_results['read_avg']:
            diff = (rd_results['read_avg'] / mc_results['read_avg'] - 1) * 100
            print(f"Read:  Memcached ({diff:.1f}% faster)")
        else:
            diff = (mc_results['read_avg'] / rd_results['read_avg'] - 1) * 100
            print(f"Read:  Redis ({diff:.1f}% faster)")
        
        print()
        print("RECOMMENDATION:")
        print("-" * 50)
        
        mc_score = 0
        rd_score = 0
        
        if mc_results['write_avg'] < rd_results['write_avg']: mc_score += 1
        else: rd_score += 1
        
        if mc_results['read_avg'] < rd_results['read_avg']: mc_score += 1
        else: rd_score += 1
        
        if mc_score > rd_score:
            print("✅ KEEP MEMCACHED - Better performance for caching")
        elif rd_score > mc_score:
            print("🔄 CONSIDER REDIS - Better performance + more features")
        else:
            print("🤝 EITHER WORKS - Choose based on features needed")
            
    else:
        if 'error' in mc_results:
            print(f"Memcached error: {mc_results['error']}")
        if 'error' in rd_results:
            print(f"Redis error: {rd_results['error']}")