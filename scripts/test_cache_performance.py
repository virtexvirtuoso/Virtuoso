#!/usr/bin/env python3
"""Test cache performance improvements"""

import asyncio
import aiohttp
import time
import json
from statistics import mean, median

async def test_cache_performance():
    """Test cache hit ratios and response times"""
    
    endpoints = [
        "http://45.77.40.77:8001/api/dashboard/overview",
        "http://45.77.40.77:8001/api/market/overview", 
        "http://45.77.40.77:8001/api/dashboard/signals",
        "http://45.77.40.77:8001/api/dashboard/market-overview"
    ]
    
    async with aiohttp.ClientSession() as session:
        print("🚀 Testing Cache Performance Improvements")
        print("=" * 60)
        
        for endpoint in endpoints:
            response_times = []
            
            # Make 10 requests to test caching
            for i in range(10):
                start_time = time.time()
                try:
                    async with session.get(endpoint, timeout=5) as response:
                        await response.text()
                        response_time = (time.time() - start_time) * 1000  # ms
                        response_times.append(response_time)
                except Exception as e:
                    print(f"❌ Error on {endpoint}: {e}")
                    continue
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            if response_times:
                avg_time = mean(response_times)
                med_time = median(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                
                print(f"📊 {endpoint.split('/')[-1]}:")
                print(f"   Average: {avg_time:.2f}ms")
                print(f"   Median:  {med_time:.2f}ms") 
                print(f"   Min:     {min_time:.2f}ms")
                print(f"   Max:     {max_time:.2f}ms")
                
                # Analyze cache effectiveness
                if len(response_times) >= 5:
                    first_half = response_times[:5]
                    second_half = response_times[5:]
                    
                    if mean(second_half) < mean(first_half):
                        improvement = ((mean(first_half) - mean(second_half)) / mean(first_half)) * 100
                        print(f"   🎯 Cache improvement: {improvement:.1f}% faster")
                    else:
                        print(f"   ⚠️  No significant cache improvement detected")
                print()
        
        # Test cache health endpoint
        print("🏥 Cache Health Check:")
        try:
            async with session.get("http://45.77.40.77:8003/api/dashboard/cache/health") as response:
                health_data = await response.json()
                
                performance = health_data.get('performance', {})
                hit_rate = performance.get('hit_rate', 0)
                hits = performance.get('hits', 0)
                misses = performance.get('misses', 0)
                circuit_state = performance.get('circuit_breaker_state', 'UNKNOWN')
                
                print(f"   Hit Rate: {hit_rate:.2f}%")
                print(f"   Hits: {hits}")
                print(f"   Misses: {misses}")
                print(f"   Circuit Breaker: {circuit_state}")
                
                if hit_rate >= 30:
                    print("   ✅ Cache performance: GOOD")
                elif hit_rate >= 20:
                    print("   ⚠️  Cache performance: ACCEPTABLE") 
                else:
                    print("   ❌ Cache performance: NEEDS IMPROVEMENT")
                    
        except Exception as e:
            print(f"   ❌ Could not get cache health: {e}")

if __name__ == "__main__":
    asyncio.run(test_cache_performance())