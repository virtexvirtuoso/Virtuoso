#!/usr/bin/env python3
"""
Simple test to verify cache dashboards are working
"""
import asyncio
import aiohttp
import json
from datetime import datetime

async def test_endpoints():
    """Test both regular and cached endpoints"""
    
    base_url = "http://VPS_HOST_REDACTED:8001"
    
    # Endpoints to test
    endpoints = [
        # Regular endpoints
        ("/api/dashboard/overview", "Regular Dashboard"),
        ("/api/cache/health", "Cache Health"),
        ("/api/cache/cache/overview", "Phase 2 Cache"),
        # New cached endpoints
        ("/api/dashboard-cached/overview", "Cached Dashboard"),
        ("/api/dashboard-cached/market-overview", "Cached Market"),
        ("/api/dashboard-cached/signals", "Cached Signals"),
    ]
    
    print("=" * 60)
    print("CACHE DASHBOARD TEST")
    print("=" * 60)
    print(f"Testing at: {datetime.now()}")
    print(f"Target: {base_url}")
    print()
    
    async with aiohttp.ClientSession() as session:
        for endpoint, name in endpoints:
            try:
                start = asyncio.get_event_loop().time()
                async with session.get(f"{base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    elapsed = (asyncio.get_event_loop().time() - start) * 1000
                    
                    if response.status == 200:
                        data = await response.text()
                        try:
                            json_data = json.loads(data)
                            print(f"✅ {name:20} - {elapsed:.1f}ms - {len(data)} bytes")
                        except:
                            print(f"⚠️  {name:20} - {elapsed:.1f}ms - Invalid JSON")
                    else:
                        print(f"❌ {name:20} - HTTP {response.status}")
            except asyncio.TimeoutError:
                print(f"⏱️  {name:20} - TIMEOUT (>5s)")
            except Exception as e:
                print(f"❌ {name:20} - ERROR: {str(e)[:30]}")
    
    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_endpoints())