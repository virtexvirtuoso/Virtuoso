#!/usr/bin/env python3
"""Test script to verify all mobile dashboard endpoints are working."""

import asyncio
import aiohttp
import json
from typing import Dict, List, Tuple
import sys

# Mobile dashboard endpoints
ENDPOINTS = [
    ("/api/dashboard/overview", "GET", "Dashboard Overview"),
    ("/api/dashboard/symbols", "GET", "Dashboard Symbols"),
    ("/api/signals/active", "GET", "Active Signals"),
    ("/api/alpha/opportunities", "GET", "Alpha Opportunities"),
    ("/api/dashboard/alerts", "GET", "Dashboard Alerts"),
    ("/dashboard/mobile", "GET", "Mobile Dashboard HTML"),
    ("/dashboard/ws", "GET", "WebSocket Endpoint"),
]

BASE_URLS = [
    "http://localhost:8003",
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8080"
]

async def test_endpoint(session: aiohttp.ClientSession, base_url: str, endpoint: str, method: str) -> Tuple[bool, Dict]:
    """Test a single endpoint."""
    url = f"{base_url}{endpoint}"
    try:
        async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if endpoint.endswith('.html') or endpoint.endswith('/mobile'):
                # For HTML endpoints, just check status
                return response.status == 200, {"status": response.status, "type": "html"}
            else:
                # For API endpoints, parse JSON
                data = await response.json()
                return response.status == 200, {"status": response.status, "data": data}
    except aiohttp.ClientError as e:
        return False, {"error": str(e)}
    except json.JSONDecodeError:
        return False, {"error": "Invalid JSON response"}
    except Exception as e:
        return False, {"error": f"Unexpected error: {str(e)}"}

async def find_working_server() -> str:
    """Find which port the server is running on."""
    async with aiohttp.ClientSession() as session:
        for base_url in BASE_URLS:
            try:
                async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        return base_url
            except:
                continue
    return None

async def main():
    """Run all endpoint tests."""
    print("🔍 Mobile Dashboard Endpoint Test")
    print("=" * 50)
    
    # Find working server
    base_url = await find_working_server()
    if not base_url:
        print("❌ ERROR: No server found running on expected ports!")
        print("Please start the Virtuoso server with: python src/main.py")
        sys.exit(1)
    
    print(f"✅ Found server at: {base_url}")
    print("-" * 50)
    
    # Test all endpoints
    async with aiohttp.ClientSession() as session:
        all_passed = True
        
        for endpoint, method, description in ENDPOINTS:
            success, result = await test_endpoint(session, base_url, endpoint, method)
            
            if success:
                print(f"✅ {description:<25} [{endpoint}]")
                if "data" in result:
                    # Show sample data
                    data = result["data"]
                    if isinstance(data, dict):
                        keys = list(data.keys())[:3]  # Show first 3 keys
                        print(f"   └─ Response keys: {', '.join(keys)}")
            else:
                print(f"❌ {description:<25} [{endpoint}]")
                print(f"   └─ Error: {result.get('error', 'Unknown error')}")
                all_passed = False
        
        print("-" * 50)
        
        # Test WebSocket endpoint
        print("🔌 Testing WebSocket connection...")
        ws_url = base_url.replace("http://", "ws://") + "/dashboard/ws"
        try:
            async with session.ws_connect(ws_url, timeout=aiohttp.ClientTimeout(total=5)) as ws:
                print(f"✅ WebSocket connected at: {ws_url}")
                await ws.close()
        except Exception as e:
            print(f"❌ WebSocket connection failed: {str(e)}")
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("✅ All mobile dashboard endpoints are working!")
        print(f"\n📱 Access mobile dashboard at: {base_url}/dashboard/mobile")
    else:
        print("❌ Some endpoints failed. Please check the server logs.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)