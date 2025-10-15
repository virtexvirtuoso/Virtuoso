#!/usr/bin/env python3
"""
Quick service status checker
"""
import asyncio
import sys
import os
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

async def check_services():
    """Check if services are running"""
    try:
        # Try to connect to the running application
        import aiohttp

        print("=== Service Status Check ===")

        # Check if main app is running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8002/api/dashboard/overview', timeout=5) as resp:
                    data = await resp.json()
                    print("✅ Main dashboard API: RUNNING")
                    print(f"   Data source: {data.get('data_source', 'unknown')}")
                    print(f"   Total symbols: {data.get('summary', {}).get('total_symbols', 0)}")
        except Exception as e:
            print(f"❌ Main dashboard API: NOT RESPONDING - {e}")

        # Check cache health
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8002/api/cache/health', timeout=5) as resp:
                    data = await resp.json()
                    print(f"✅ Cache health: {data.get('status', 'unknown')}")
                    print(f"   L1: {data.get('layers', {}).get('l1_memory', 'unknown')}")
                    print(f"   L2: {data.get('layers', {}).get('l2_memcached', 'unknown')}")
                    print(f"   L3: {data.get('layers', {}).get('l3_redis', 'unknown')}")
        except Exception as e:
            print(f"❌ Cache health check: NOT RESPONDING - {e}")

        # Check monitoring API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8001/api/monitoring/status', timeout=5) as resp:
                    data = await resp.json()
                    print("✅ Monitoring API: RUNNING")
                    components = data.get('components', {})
                    print(f"   Market monitor: {components.get('market_monitor', {}).get('status', 'unknown')}")
                    print(f"   Health monitor: active" if data.get('health', False) else "   Health monitor: inactive")
        except Exception as e:
            print(f"❌ Monitoring API: NOT RESPONDING - {e}")

    except Exception as e:
        print(f"Error checking services: {e}")

if __name__ == "__main__":
    asyncio.run(check_services())