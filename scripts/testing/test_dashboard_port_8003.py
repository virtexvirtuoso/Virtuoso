#!/usr/bin/env python3
"""
Dashboard audit for application running on port 8003
"""

import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8003"

def test_dashboard():
    """Test dashboard on port 8003"""
    print("\n" + "="*70)
    print(f"DASHBOARD AUDIT - RUN-WXPXYR-4986")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("="*70 + "\n")
    
    # Test endpoints
    endpoints = [
        ("Root Status", "/", "GET"),
        ("Health Check", "/health", "GET"),
        ("Version Info", "/version", "GET"),
        ("Dashboard HTML", "/dashboard", "GET"),
        ("Dashboard Overview API", "/api/dashboard/overview", "GET"),
        ("System Status", "/api/system/status", "GET"),
        ("Top Symbols", "/api/top-symbols", "GET"),
        ("Market Overview", "/api/market/overview", "GET"),
        ("Alpha Opportunities", "/api/alpha/opportunities", "GET"),
        ("Liquidation Alerts", "/api/liquidation/alerts", "GET"),
        ("WebSocket Status", "/api/websocket/status", "GET"),
    ]
    
    passed = 0
    failed = 0
    
    for name, endpoint, method in endpoints:
        try:
            response = requests.request(method, f"{BASE_URL}{endpoint}", timeout=5)
            status = response.status_code
            
            if status == 200:
                print(f"✅ {name:<30} Status: {status}")
                passed += 1
                
                # Show run info if available
                if endpoint in ["/", "/version"]:
                    try:
                        data = response.json()
                        if "run_id" in data:
                            print(f"   Run ID: {data.get('run_id')}")
                            print(f"   Started: {data.get('run_started', 'N/A')}")
                    except:
                        pass
                        
                # Show data preview for key endpoints
                if endpoint == "/api/dashboard/overview":
                    try:
                        data = response.json()
                        print(f"   System Status: {data.get('system_status', {})}")
                    except:
                        pass
                        
            else:
                print(f"❌ {name:<30} Status: {status}")
                failed += 1
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {name:<30} Error: {type(e).__name__}")
            failed += 1
        except Exception as e:
            print(f"❌ {name:<30} Error: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "-"*70)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    
    # Dashboard accessibility
    print("\n" + "-"*70)
    print("DASHBOARD ACCESS:")
    print(f"  Main Dashboard: {BASE_URL}/dashboard")
    print(f"  API Documentation: {BASE_URL}/docs")
    print(f"  Health Check: {BASE_URL}/health")
    
    # Test WebSocket endpoint
    print("\n" + "-"*70)
    print("WEBSOCKET ENDPOINTS:")
    print(f"  Dashboard WS: ws://localhost:8003/ws/dashboard")
    print(f"  API Dashboard WS: ws://localhost:8003/api/dashboard/ws")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    test_dashboard()