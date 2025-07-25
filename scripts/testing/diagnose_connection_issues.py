#!/usr/bin/env python3
"""
Diagnose the root cause of connection timeout issues with Bybit API.
"""

import asyncio
import aiohttp
import time
import statistics
import traceback
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

async def test_direct_connection():
    """Test direct connection to Bybit without our wrapper."""
    print("\n🔍 1. Testing Direct Connection to Bybit API...")
    
    urls = [
        "https://api.bybit.com/v5/market/time",
        "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT",
        "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=1"
    ]
    
    for url in urls:
        latencies = []
        errors = 0
        
        print(f"\n  Testing: {url.split('?')[0]}...")
        
        for i in range(5):
            try:
                start = time.time()
                timeout = aiohttp.ClientTimeout(total=10)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        data = await response.json()
                        latency = (time.time() - start) * 1000
                        latencies.append(latency)
                        
                        if data.get('retCode') == 0:
                            print(f"    Attempt {i+1}: ✅ {latency:.0f}ms")
                        else:
                            print(f"    Attempt {i+1}: ⚠️  API Error: {data.get('retMsg')}")
                            
            except asyncio.TimeoutError:
                errors += 1
                print(f"    Attempt {i+1}: ❌ TIMEOUT after 10s")
            except Exception as e:
                errors += 1
                print(f"    Attempt {i+1}: ❌ ERROR: {str(e)}")
            
            await asyncio.sleep(0.5)
        
        if latencies:
            avg = statistics.mean(latencies)
            print(f"  📊 Stats: Avg: {avg:.0f}ms, Min: {min(latencies):.0f}ms, Max: {max(latencies):.0f}ms, Errors: {errors}/5")

async def test_concurrent_connections():
    """Test how many concurrent connections cause issues."""
    print("\n🔍 2. Testing Concurrent Connection Limits...")
    
    async def make_request(session, semaphore, index):
        async with semaphore:
            try:
                start = time.time()
                url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
                
                async with session.get(url) as response:
                    data = await response.json()
                    latency = (time.time() - start) * 1000
                    
                    if data.get('retCode') == 0:
                        return ('success', latency, index)
                    else:
                        return ('api_error', latency, index)
                        
            except asyncio.TimeoutError:
                return ('timeout', None, index)
            except Exception as e:
                return ('error', None, index)
    
    for concurrent_limit in [1, 5, 10, 20, 50]:
        print(f"\n  Testing with {concurrent_limit} concurrent requests...")
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            semaphore = asyncio.Semaphore(concurrent_limit)
            
            start = time.time()
            tasks = [make_request(session, semaphore, i) for i in range(concurrent_limit)]
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start
            
            successes = sum(1 for r in results if r[0] == 'success')
            timeouts = sum(1 for r in results if r[0] == 'timeout')
            errors = sum(1 for r in results if r[0] in ['error', 'api_error'])
            
            success_latencies = [r[1] for r in results if r[0] == 'success' and r[1]]
            avg_latency = statistics.mean(success_latencies) if success_latencies else 0
            
            print(f"    Results: {successes}/{concurrent_limit} successful, {timeouts} timeouts, {errors} errors")
            print(f"    Total time: {total_time:.2f}s, Avg latency: {avg_latency:.0f}ms")

async def test_session_reuse():
    """Test if session reuse improves performance."""
    print("\n🔍 3. Testing Session Reuse vs New Sessions...")
    
    url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
    
    # Test 1: New session each time
    print("\n  Testing with new session for each request...")
    latencies_new = []
    errors_new = 0
    
    for i in range(10):
        try:
            start = time.time()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    await response.json()
                    latency = (time.time() - start) * 1000
                    latencies_new.append(latency)
                    
        except Exception:
            errors_new += 1
            
        await asyncio.sleep(0.1)
    
    # Test 2: Reuse session
    print("\n  Testing with reused session...")
    latencies_reuse = []
    errors_reuse = 0
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for i in range(10):
            try:
                start = time.time()
                async with session.get(url) as response:
                    await response.json()
                    latency = (time.time() - start) * 1000
                    latencies_reuse.append(latency)
                    
            except Exception:
                errors_reuse += 1
                
            await asyncio.sleep(0.1)
    
    if latencies_new:
        avg_new = statistics.mean(latencies_new)
        print(f"\n  📊 New Sessions: Avg: {avg_new:.0f}ms, Errors: {errors_new}/10")
        
    if latencies_reuse:
        avg_reuse = statistics.mean(latencies_reuse)
        print(f"  📊 Reused Session: Avg: {avg_reuse:.0f}ms, Errors: {errors_reuse}/10")
        
        if latencies_new and latencies_reuse:
            improvement = ((avg_new - avg_reuse) / avg_new) * 100
            print(f"  📊 Improvement: {improvement:.1f}%")

async def check_system_limits():
    """Check system resource limits."""
    print("\n🔍 4. Checking System Resource Limits...")
    
    import resource
    import socket
    
    # Get file descriptor limits
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print(f"  File descriptor limits: soft={soft}, hard={hard}")
    
    # Check open connections
    try:
        import psutil
        process = psutil.Process()
        connections = process.connections()
        print(f"  Current open connections: {len(connections)}")
        
        # Count by status
        status_counts = {}
        for conn in connections:
            status = conn.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"    {status}: {count}")
            
    except ImportError:
        print("  (psutil not installed - can't check connection details)")

async def test_dns_resolution():
    """Test DNS resolution time."""
    print("\n🔍 5. Testing DNS Resolution...")
    
    import socket
    
    hostnames = ['api.bybit.com', 'stream.bybit.com']
    
    for hostname in hostnames:
        try:
            start = time.time()
            ip = socket.gethostbyname(hostname)
            dns_time = (time.time() - start) * 1000
            print(f"  {hostname} → {ip} ({dns_time:.0f}ms)")
        except Exception as e:
            print(f"  {hostname} → ERROR: {str(e)}")

async def main():
    """Run all diagnostic tests."""
    print("🚀 Starting Connection Diagnostics for Bybit API...")
    print("=" * 60)
    
    await test_direct_connection()
    await test_concurrent_connections()
    await test_session_reuse()
    await check_system_limits()
    await test_dns_resolution()
    
    print("\n" + "=" * 60)
    print("📋 RECOMMENDATIONS:")
    print("\n1. If latencies > 1000ms: Network/routing issue")
    print("2. If concurrent requests fail: Rate limiting or connection pool exhaustion")
    print("3. If session reuse shows improvement: Implement connection pooling")
    print("4. If file descriptors low: Increase system limits")
    print("5. If DNS slow: Consider DNS caching or direct IP usage")

if __name__ == "__main__":
    asyncio.run(main())