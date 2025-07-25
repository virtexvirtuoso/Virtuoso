#!/usr/bin/env python3
"""
Debug dashboard initialization error
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8003"

def debug_dashboard():
    """Debug dashboard initialization issues"""
    print("\n" + "="*70)
    print("DASHBOARD DEBUG - RUN-WXPXYR-4986")
    print("="*70 + "\n")
    
    # Check all critical endpoints that dashboard needs during initialization
    critical_endpoints = [
        ("/api/dashboard/overview", "Dashboard Overview"),
        ("/api/liquidation/alerts", "Liquidation Alerts"),
        ("/api/liquidation/stress-indicators", "Stress Indicators"),
        ("/api/liquidation/cascade-risk", "Cascade Risk"),
        ("/api/alpha/opportunities", "Alpha Opportunities"),
        ("/api/system/status", "System Status"),
        ("/api/system/performance", "System Performance"),
        ("/api/market/overview", "Market Overview"),
    ]
    
    print("Testing critical dashboard endpoints:\n")
    
    failed_endpoints = []
    
    for endpoint, name in critical_endpoints:
        try:
            start_time = datetime.now()
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {name:<30} OK ({elapsed:.2f}s)")
                
                # Check for error in response
                if isinstance(data, dict) and "error" in data:
                    print(f"   ⚠️  Contains error: {data['error']}")
                    failed_endpoints.append((endpoint, f"Error in response: {data['error']}"))
            else:
                print(f"❌ {name:<30} HTTP {response.status_code} ({elapsed:.2f}s)")
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        print(f"   Error: {error_data['detail']}")
                except:
                    pass
                failed_endpoints.append((endpoint, f"HTTP {response.status_code}"))
                
        except requests.exceptions.Timeout:
            print(f"❌ {name:<30} TIMEOUT (>10s)")
            failed_endpoints.append((endpoint, "Timeout"))
        except Exception as e:
            print(f"❌ {name:<30} ERROR: {type(e).__name__}")
            failed_endpoints.append((endpoint, str(e)))
    
    # Summary
    print("\n" + "-"*70)
    if failed_endpoints:
        print(f"FAILED ENDPOINTS ({len(failed_endpoints)}):\n")
        for endpoint, error in failed_endpoints:
            print(f"  {endpoint}: {error}")
        print("\n⚠️  Dashboard initialization will fail if any critical endpoint fails!")
    else:
        print("✅ All endpoints responding correctly!")
    
    # Check WebSocket configuration
    print("\n" + "-"*70)
    print("WebSocket Configuration:")
    try:
        ws_status = requests.get(f"{BASE_URL}/api/websocket/status", timeout=5).json()
        ws = ws_status.get('websocket', {})
        print(f"  Connected: {ws.get('connected', False)}")
        print(f"  Active Connections: {ws.get('active_connections', 0)}")
        print(f"  Messages Received: {ws.get('messages_received', 0)}")
    except:
        print("  ❌ Could not check WebSocket status")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    debug_dashboard()