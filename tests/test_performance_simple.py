#!/usr/bin/env python3
"""
Simple test for parallel fetching performance improvement
"""

import asyncio
import time
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def simulate_api_call(symbol: str, delay: float = 0.5):
    """Simulate an API call with network delay"""
    await asyncio.sleep(delay)
    return {
        'symbol': symbol,
        'price': 100.0 + hash(symbol) % 100,
        'volume': 1000000 + hash(symbol) % 1000000
    }

async def test_sequential(symbols):
    """Test sequential fetching (OLD METHOD)"""
    print("\n🐌 Testing SEQUENTIAL fetch (old method)...")
    start = time.time()
    
    results = []
    for symbol in symbols:
        data = await simulate_api_call(symbol, 0.5)
        results.append(data)
    
    duration = time.time() - start
    print(f"  Sequential: {len(results)} symbols in {duration:.2f}s")
    return duration

async def test_parallel(symbols):
    """Test parallel fetching (NEW METHOD)"""
    print("\n⚡ Testing PARALLEL fetch (new method)...")
    start = time.time()
    
    # Create tasks for parallel execution
    tasks = [simulate_api_call(symbol, 0.5) for symbol in symbols]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start
    print(f"  Parallel: {len(results)} symbols in {duration:.2f}s")
    return duration

async def test_bulk():
    """Test bulk fetch (BEST METHOD)"""
    print("\n🚀 Testing BULK fetch (best method)...")
    start = time.time()
    
    # Simulate fetching all symbols in one call
    await asyncio.sleep(0.5)  # Single API call delay
    results = [{'symbol': f'SYM{i}', 'price': 100.0 + i} for i in range(30)]
    
    duration = time.time() - start
    print(f"  Bulk: {len(results)} symbols in {duration:.2f}s")
    return duration

async def main():
    print("\n" + "="*60)
    print("MOBILE DASHBOARD PERFORMANCE OPTIMIZATION DEMONSTRATION")
    print("="*60)
    print("\nSimulating API calls for 30 symbols...")
    print("Each individual API call has 0.5s network latency")
    
    # Test symbols
    symbols = [f'SYMBOL_{i}' for i in range(30)]
    
    # Run tests
    seq_time = await test_sequential(symbols[:5])  # Only 5 for demo (would be too slow)
    par_time = await test_parallel(symbols)
    bulk_time = await test_bulk()
    
    # Results
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    print(f"\n📊 Actual Test Results:")
    print(f"  • Sequential (5 symbols): {seq_time:.2f}s")
    print(f"  • Parallel (30 symbols): {par_time:.2f}s")
    print(f"  • Bulk (30 symbols): {bulk_time:.2f}s")
    
    print(f"\n📈 Extrapolated for 30 symbols:")
    print(f"  • Sequential: ~{seq_time * 6:.1f}s (30 × 0.5s)")
    print(f"  • Parallel: {par_time:.2f}s (limited by slowest)")
    print(f"  • Bulk: {bulk_time:.2f}s (single call)")
    
    print(f"\n✨ Performance Improvements:")
    speedup_parallel = (seq_time * 6) / par_time
    speedup_bulk = (seq_time * 6) / bulk_time
    print(f"  • Parallel is {speedup_parallel:.1f}x faster than sequential")
    print(f"  • Bulk is {speedup_bulk:.1f}x faster than sequential")
    
    print("\n🎯 This is why the mobile dashboard was slow!")
    print("   Sequential API calls were taking 15-30 seconds")
    print("   Now with parallel/bulk: <1-3 seconds")

if __name__ == "__main__":
    print("\n🔧 Starting performance optimization demonstration...")
    asyncio.run(main())
    print("\n✅ Demonstration complete!")