#!/usr/bin/env python3
"""Test script to verify all dashboard_v10.html endpoints are working."""

import asyncio
import aiohttp
import json
from typing import Dict, List, Tuple
import sys

# Dashboard v10 endpoints (corrected)
ENDPOINTS = [
    # Core dashboard
    ("/api/dashboard/overview", "GET", "Dashboard Overview"),
    ("/api/liquidation/alerts", "GET", "Liquidation Alerts"),
    ("/api/liquidation/stress-indicators", "GET", "Stress Indicators"),
    ("/api/liquidation/cascade-risk", "GET", "Cascade Risk"),
    ("/api/alpha/opportunities", "GET", "Alpha Opportunities"),
    ("/api/alpha/scan", "POST", "Alpha Scan"),
    ("/api/system/status", "GET", "System Status"),
    ("/api/system/performance", "GET", "System Performance"),
    
    # Trading
    ("/api/trading/portfolio/summary", "GET", "Portfolio Summary"),
    ("/api/trading/orders", "GET", "Trading Orders"),
    ("/api/trading/positions", "GET", "Trading Positions"),
    
    # Market
    ("/api/market/overview", "GET", "Market Overview"),
    ("/api/bitcoin-beta/status", "GET", "Bitcoin Beta Status"),
    
    # Signals
    ("/api/signals/signals/latest", "GET", "Latest Signals"),
    ("/api/dashboard/alerts/recent", "GET", "Recent Alerts"),
    
    # Manipulation
    ("/api/manipulation/alerts", "GET", "Manipulation Alerts"),
    ("/api/manipulation/stats", "GET", "Manipulation Stats"),
    
    # Symbols
    ("/api/top-symbols/", "GET", "Top Symbols"),
    
    # Correlation
    ("/api/correlation/live-matrix", "GET", "Live Correlation Matrix"),
    
    # Additional
    ("/api/active", "GET", "Active Signals"),
    ("/api/market/ticker/BTCUSDT", "GET", "Market Ticker"),
    ("/api/signal-tracking/tracked/test123", "GET", "Tracked Signal"),
    
    # HTML pages
    ("/dashboard/", "GET", "V10 Dashboard HTML"),
    ("/dashboard/mobile", "GET", "Mobile Dashboard HTML"),
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
    
    # Prepare request data for POST requests
    data = None
    if method == "POST" and "/alpha/scan" in endpoint:
        data = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h", "4h"],
            "min_confluence_score": 0.5
        }
    
    try:
        kwargs = {"timeout": aiohttp.ClientTimeout(total=10)}
        if data:
            kwargs["json"] = data
            
        async with session.request(method, url, **kwargs) as response:
            if endpoint.endswith('.html') or '/dashboard/' in endpoint:
                # For HTML endpoints, just check status
                return response.status == 200, {"status": response.status, "type": "html"}
            else:
                # For API endpoints, try to parse JSON
                try:
                    response_data = await response.json()
                    return response.status in [200, 201], {
                        "status": response.status, 
                        "data": response_data
                    }
                except json.JSONDecodeError:
                    # Some endpoints might return text
                    text = await response.text()
                    return response.status in [200, 201], {
                        "status": response.status,
                        "text": text[:100] + "..." if len(text) > 100 else text
                    }
                    
    except aiohttp.ClientError as e:
        return False, {"error": f"Connection error: {str(e)}"}
    except Exception as e:
        return False, {"error": f"Unexpected error: {str(e)}"}

async def find_working_server() -> str:
    """Find which port the server is running on."""
    async with aiohttp.ClientSession() as session:
        for base_url in BASE_URLS:
            try:
                async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        return base_url
            except:
                continue
    return None

async def test_websocket(base_url: str) -> bool:
    """Test WebSocket connection."""
    ws_url = base_url.replace("http://", "ws://") + "/dashboard/ws"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=aiohttp.ClientTimeout(total=5)) as ws:
                print(f"✅ WebSocket connected: /dashboard/ws")
                await ws.close()
                return True
    except Exception as e:
        print(f"❌ WebSocket failed: {str(e)}")
        return False

async def main():
    """Run all endpoint tests."""
    print("🔍 Dashboard v10 Endpoint Live Test")
    print("=" * 60)
    
    # Find working server
    base_url = await find_working_server()
    if not base_url:
        print("❌ ERROR: No server found running on expected ports!")
        print("Please start the Virtuoso server with: python src/main.py")
        sys.exit(1)
    
    print(f"✅ Found server at: {base_url}")
    print("-" * 60)
    
    # Test all endpoints
    async with aiohttp.ClientSession() as session:
        all_passed = True
        results = []
        
        for endpoint, method, description in ENDPOINTS:
            success, result = await test_endpoint(session, base_url, endpoint, method)
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {description:<25} [{method} {endpoint}]")
            
            if success and "data" in result:
                # Show sample data for successful API calls
                data = result["data"]
                if isinstance(data, dict):
                    if "status" in data:
                        print(f"   └─ Status: {data['status']}")
                    elif len(data) > 0:
                        keys = list(data.keys())[:3]
                        print(f"   └─ Keys: {', '.join(keys)}")
            elif not success:
                print(f"   └─ Error: {result.get('error', 'Unknown error')}")
                all_passed = False
            
            results.append((endpoint, method, success, result))
        
        print("-" * 60)
        
        # Test WebSocket
        print("🔌 Testing WebSocket connection...")
        ws_success = await test_websocket(base_url)
        if not ws_success:
            all_passed = False
    
    print("=" * 60)
    
    # Summary
    successful = sum(1 for _, _, success, _ in results if success)
    total = len(results)
    
    print(f"Endpoints tested: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    
    if all_passed and ws_success:
        print("\n✅ All dashboard v10 endpoints are working!")
        print(f"\n📊 Access v10 dashboard at: {base_url}/dashboard/")
        print(f"📱 Access mobile dashboard at: {base_url}/dashboard/mobile")
    else:
        print("\n❌ Some endpoints failed. Check server logs for details.")
        print("\nFailed endpoints:")
        for endpoint, method, success, result in results:
            if not success:
                print(f"   - {method} {endpoint}: {result.get('error', 'Failed')}")
    
    return all_passed and ws_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)