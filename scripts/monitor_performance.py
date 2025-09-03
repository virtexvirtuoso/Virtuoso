#!/usr/bin/env python3
"""
Performance Monitoring Tool
Compares response times across different endpoint implementations
"""
import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
from typing import List, Tuple

BASE_URL = "http://VPS_HOST_REDACTED:8001"

async def test_endpoint(session: aiohttp.ClientSession, url: str, name: str) -> Tuple[str, float, int]:
    """Test an endpoint and return metrics"""
    try:
        start = time.perf_counter()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            elapsed = (time.perf_counter() - start) * 1000  # ms
            await response.text()  # Consume response
            return name, elapsed, response.status
    except Exception as e:
        return name, -1, 0

async def benchmark_endpoints():
    """Benchmark all endpoint implementations"""
    
    # Endpoint groups to test
    endpoint_groups = {
        "PHASE 1 - Direct": [
            ("/api/dashboard/overview", "Dashboard Overview"),
            ("/api/dashboard/signals", "Signals"),
            ("/api/market/overview", "Market Overview"),
        ],
        "PHASE 2 - Cached (Adapter)": [
            ("/api/dashboard-cached/overview", "Dashboard Overview"),
            ("/api/dashboard-cached/signals", "Signals"),
            ("/api/dashboard-cached/market-overview", "Market Overview"),
        ],
        "PHASE 3 - Fast (Direct Cache)": [
            ("/api/fast/overview", "Dashboard Overview"),
            ("/api/fast/signals", "Signals"),
            ("/api/fast/market", "Market Overview"),
            ("/api/fast/mobile", "Mobile Data"),
        ]
    }
    
    print("=" * 80)
    print("PERFORMANCE BENCHMARK REPORT")
    print("=" * 80)
    print(f"Time: {datetime.now()}")
    print(f"Target: {BASE_URL}")
    print("-" * 80)
    
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for group_name, endpoints in endpoint_groups.items():
            print(f"\n{group_name}")
            print("-" * 40)
            
            group_times = []
            
            # Test each endpoint 3 times
            for endpoint, name in endpoints:
                times = []
                for _ in range(3):
                    _, elapsed, status = await test_endpoint(
                        session, f"{BASE_URL}{endpoint}", name
                    )
                    if elapsed > 0:
                        times.append(elapsed)
                    await asyncio.sleep(0.1)  # Small delay between tests
                
                if times:
                    avg_time = statistics.mean(times)
                    min_time = min(times)
                    max_time = max(times)
                    group_times.append(avg_time)
                    
                    # Color coding
                    if avg_time < 50:
                        color = "🟢"  # Excellent
                    elif avg_time < 200:
                        color = "🟡"  # Good
                    elif avg_time < 1000:
                        color = "🟠"  # OK
                    else:
                        color = "🔴"  # Slow
                    
                    print(f"{color} {name:20} | Avg: {avg_time:6.1f}ms | Min: {min_time:6.1f}ms | Max: {max_time:6.1f}ms")
                else:
                    print(f"❌ {name:20} | FAILED")
            
            if group_times:
                group_avg = statistics.mean(group_times)
                results[group_name] = group_avg
                print(f"\n   GROUP AVERAGE: {group_avg:.1f}ms")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    
    if results:
        baseline = results.get("PHASE 1 - Direct", 1000)
        for name, avg_time in results.items():
            if baseline > 0:
                ratio = avg_time / baseline
                if ratio < 1:
                    comparison = f"{1/ratio:.1f}x faster"
                else:
                    comparison = f"{ratio:.1f}x slower"
            else:
                comparison = "N/A"
            
            print(f"{name:30} | {avg_time:6.1f}ms | {comparison}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if "PHASE 3 - Fast (Direct Cache)" in results:
        fast_time = results["PHASE 3 - Fast (Direct Cache)"]
        if fast_time < 100:
            print("✅ Phase 3 implementation achieving target <100ms response times!")
            print("   Ready for production use.")
        elif fast_time < 500:
            print("⚠️  Phase 3 showing improvement but not yet optimal.")
            print("   Check cache connection and network latency.")
        else:
            print("❌ Phase 3 not performing as expected.")
            print("   Debug cache implementation and check Memcached status.")
    
    print("\n" + "=" * 80)

async def monitor_cache_status():
    """Monitor cache health and hit rates"""
    print("\nCACHE STATUS CHECK")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Check cache health
        try:
            async with session.get(f"{BASE_URL}/api/fast/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Cache Status: {data.get('status', 'unknown')}")
                    print(f"Cache Connected: {data.get('cache_connected', False)}")
                    print(f"Health Check Time: {data.get('response_ms', 0):.1f}ms")
                else:
                    print(f"Cache health check failed: HTTP {response.status}")
        except Exception as e:
            print(f"Could not check cache health: {e}")

async def main():
    """Run performance monitoring"""
    await benchmark_endpoints()
    await monitor_cache_status()
    
    print("\n✅ Performance monitoring complete!")

if __name__ == "__main__":
    print("\n🔍 Starting Performance Benchmark...")
    print("This will test all endpoint implementations and compare response times.\n")
    asyncio.run(main())