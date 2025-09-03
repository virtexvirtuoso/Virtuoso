#!/usr/bin/env python3
"""Test dashboard data flow on VPS"""

import asyncio
import aiohttp
import json
from datetime import datetime

VPS_URL = "http://VPS_HOST_REDACTED:8001"

async def test_endpoints():
    """Test all dashboard endpoints"""
    
    endpoints = [
        "/api/market/overview",
        "/api/dashboard/overview", 
        "/api/dashboard/signals",
        "/api/dashboard/market-overview",
        "/mobile"
    ]
    
    async with aiohttp.ClientSession() as session:
        print(f"Testing dashboard data flow at {datetime.now()}")
        print("=" * 60)
        
        for endpoint in endpoints:
            url = f"{VPS_URL}{endpoint}"
            try:
                async with session.get(url, timeout=5) as response:
                    status = response.status
                    
                    if endpoint == "/mobile":
                        # Check if HTML page loads
                        content = await response.text()
                        has_charts = "canvas" in content
                        has_api_calls = "/api/" in content
                        print(f"✅ {endpoint}: Status {status}, Has charts: {has_charts}, Has API calls: {has_api_calls}")
                    else:
                        # Check JSON data
                        data = await response.json()
                        
                        if endpoint == "/api/dashboard/signals":
                            signal_count = len(data) if isinstance(data, list) else 0
                            print(f"✅ {endpoint}: Status {status}, Signals: {signal_count}")
                        elif endpoint == "/api/dashboard/overview":
                            has_signals = len(data.get('signals', [])) if 'signals' in data else 0
                            print(f"✅ {endpoint}: Status {status}, Has signals: {has_signals}")
                        else:
                            print(f"✅ {endpoint}: Status {status}, Data keys: {list(data.keys())[:5]}")
                            
            except asyncio.TimeoutError:
                print(f"❌ {endpoint}: Timeout")
            except Exception as e:
                print(f"❌ {endpoint}: Error - {str(e)}")
        
        print("\n" + "=" * 60)
        print("Dashboard Data Flow Summary:")
        
        # Test actual data fetching from dashboard perspective
        try:
            # Get market overview
            async with session.get(f"{VPS_URL}/api/market/overview") as resp:
                market_data = await resp.json()
                print(f"Market Overview: {market_data.get('status', 'unknown')} - Volume: ${market_data.get('total_volume', 0):,.0f}")
            
            # Get dashboard overview
            async with session.get(f"{VPS_URL}/api/dashboard/overview") as resp:
                dashboard_data = await resp.json()
                signals = dashboard_data.get('signals', [])
                if signals:
                    top_signal = signals[0]
                    print(f"Top Signal: {top_signal.get('symbol')} - Score: {top_signal.get('score', 0):.2f} - Action: {top_signal.get('action', 'unknown')}")
                else:
                    print("No signals available")
                    
        except Exception as e:
            print(f"Error getting summary: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())