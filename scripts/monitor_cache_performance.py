#!/usr/bin/env python3
"""
Monitor cache dashboard performance and response times
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

BASE_URL = "http://45.77.40.77:8001"

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str, name: str) -> Tuple[str, float, int, bool]:
    """Test a single endpoint and return metrics"""
    try:
        start = time.perf_counter()
        async with session.get(f"{BASE_URL}{endpoint}", timeout=aiohttp.ClientTimeout(total=10)) as response:
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            data = await response.text()
            
            # Check if valid JSON
            try:
                json_data = json.loads(data)
                is_valid = True
                size = len(data)
            except:
                is_valid = False
                size = 0
            
            return name, elapsed, response.status, is_valid, size
    except asyncio.TimeoutError:
        return name, 10000, 0, False, 0  # Timeout after 10s
    except Exception as e:
        return name, 0, 0, False, 0

async def monitor_performance():
    """Monitor all endpoints continuously"""
    
    # Endpoints to monitor
    endpoints = [
        # Regular endpoints (baseline)
        ("/api/dashboard/overview", "Regular Dashboard"),
        ("/api/market/overview", "Regular Market"),
        ("/api/dashboard/signals", "Regular Signals"),
        
        # Phase 2 cache endpoints
        ("/api/cache/health", "Cache Health"),
        ("/api/cache/cache/overview", "Phase2 Cache"),
        
        # New cached dashboard endpoints
        ("/api/dashboard-cached/overview", "Cached Dashboard"),
        ("/api/dashboard-cached/market-overview", "Cached Market"),
        ("/api/dashboard-cached/signals", "Cached Signals"),
        ("/api/dashboard-cached/alerts", "Cached Alerts"),
    ]
    
    print("=" * 80)
    print("CACHE DASHBOARD PERFORMANCE MONITOR")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print(f"Target: {BASE_URL}")
    print("-" * 80)
    
    # Run continuous monitoring
    iteration = 0
    while True:
        iteration += 1
        print(f"\n[Iteration {iteration}] {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 80)
        print(f"{'Endpoint':<25} {'Status':<8} {'Time (ms)':<12} {'Size':<10} {'Type'}")
        print("-" * 80)
        
        async with aiohttp.ClientSession() as session:
            # Test all endpoints concurrently
            tasks = [test_endpoint(session, ep, name) for ep, name in endpoints]
            results = await asyncio.gather(*tasks)
            
            # Categorize results
            regular_times = []
            cached_times = []
            
            for name, elapsed, status, is_valid, size in results:
                # Determine type
                if "Cached" in name or "Phase2" in name:
                    endpoint_type = "CACHE"
                    if elapsed < 10000:  # Not a timeout
                        cached_times.append(elapsed)
                    color = "\033[92m"  # Green
                else:
                    endpoint_type = "REGULAR"
                    if elapsed < 10000:
                        regular_times.append(elapsed)
                    color = "\033[94m"  # Blue
                
                # Status display
                if status == 200:
                    status_str = f"✅ {status}"
                elif status == 0:
                    status_str = "❌ FAIL"
                else:
                    status_str = f"⚠️  {status}"
                
                # Time display with color coding
                if elapsed < 50:
                    time_color = "\033[92m"  # Green - excellent
                elif elapsed < 200:
                    time_color = "\033[93m"  # Yellow - good
                elif elapsed < 1000:
                    time_color = "\033[94m"  # Blue - ok
                else:
                    time_color = "\033[91m"  # Red - slow
                
                # Size display
                size_str = f"{size:,}" if size > 0 else "-"
                
                print(f"{color}{name:<25}\033[0m {status_str:<8} {time_color}{elapsed:>10.1f}ms\033[0m {size_str:<10} {endpoint_type}")
        
        # Calculate statistics
        print("-" * 80)
        if regular_times:
            avg_regular = sum(regular_times) / len(regular_times)
            print(f"Regular Endpoints: Avg {avg_regular:.1f}ms, Min {min(regular_times):.1f}ms, Max {max(regular_times):.1f}ms")
        
        if cached_times:
            avg_cached = sum(cached_times) / len(cached_times)
            print(f"Cached Endpoints:  Avg {avg_cached:.1f}ms, Min {min(cached_times):.1f}ms, Max {max(cached_times):.1f}ms")
            
            if regular_times and cached_times:
                speedup = avg_regular / avg_cached
                print(f"\n🚀 Cache Speedup: {speedup:.1f}x faster")
        
        # Wait before next iteration
        await asyncio.sleep(10)

async def main():
    """Main monitoring loop"""
    try:
        await monitor_performance()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("=" * 80)

if __name__ == "__main__":
    print("\n🔍 Starting Cache Dashboard Performance Monitor...")
    print("Press Ctrl+C to stop\n")
    asyncio.run(main())