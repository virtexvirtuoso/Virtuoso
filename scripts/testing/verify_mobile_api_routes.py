#!/usr/bin/env python3
"""Verify that all mobile dashboard API routes are properly defined in the code."""

import os
import sys
from pathlib import Path

def check_route_exists(file_path, route_pattern):
    """Check if a route pattern exists in the file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            return route_pattern in content
    except FileNotFoundError:
        return False

def main():
    print("🔍 Mobile Dashboard API Route Verification")
    print("=" * 50)
    
    # Define the routes the mobile dashboard expects
    routes_to_check = [
        ("/api/dashboard/overview", '@router.get("/overview")'),  # Mounted under /api/dashboard/
        ("/api/dashboard/symbols", '@router.get("/symbols")'),  # Mounted under /api/dashboard/
        ("/api/signals/active", '@router.get("/active")'),  # In signals.py, mounted under /api/signals/
        ("/api/alpha/opportunities", '@router.get("/api/alpha/opportunities")'),
        ("/api/dashboard/alerts", '@router.get("/alerts")'),  # Mounted under /api/dashboard/
        ("/dashboard/ws", '@router.websocket("/ws")'),  # Mounted under /dashboard/
        ("/dashboard/mobile", '@router.get("/mobile")'),
    ]
    
    dashboard_routes_file = Path("src/api/routes/dashboard.py")
    signals_routes_file = Path("src/api/routes/signals.py")
    
    if not dashboard_routes_file.exists():
        print("❌ ERROR: Dashboard routes file not found!")
        return False
    
    if not signals_routes_file.exists():
        print("❌ ERROR: Signals routes file not found!")
        return False
    
    print(f"✅ Found dashboard routes file: {dashboard_routes_file}")
    print(f"✅ Found signals routes file: {signals_routes_file}")
    print("-" * 50)
    
    all_routes_found = True
    
    for endpoint, route_pattern in routes_to_check:
        # Check signals routes for active endpoint
        if "/signals/active" in endpoint:
            route_exists = check_route_exists(signals_routes_file, route_pattern)
        else:
            route_exists = check_route_exists(dashboard_routes_file, route_pattern)
        
        if route_exists:
            print(f"✅ {endpoint:<25} - Route defined")
        else:
            print(f"❌ {endpoint:<25} - Route NOT FOUND")
            all_routes_found = False
    
    print("-" * 50)
    
    # Check if the routes are properly registered in the main app
    api_init_file = Path("src/api/__init__.py")
    main_file = Path("src/main.py")
    
    if api_init_file.exists():
        api_registered = check_route_exists(api_init_file, "dashboard")
        if api_registered:
            print("✅ Dashboard routes registered in API init")
        else:
            print("❌ Dashboard routes NOT registered in API init")
            all_routes_found = False
    
    if main_file.exists():
        main_registered = check_route_exists(main_file, "init_api_routes")
        if main_registered:
            print("✅ API routes initialized in main app")
        else:
            print("❌ API routes NOT initialized in main app")
            all_routes_found = False
    
    print("=" * 50)
    
    if all_routes_found:
        print("✅ All mobile dashboard API routes are properly defined!")
        print("\n📱 To test connectivity, start the server with:")
        print("   python src/main.py")
        print("\n🧪 Then run the endpoint test:")
        print("   python scripts/testing/test_mobile_dashboard_endpoints.py")
        return True
    else:
        print("❌ Some routes are missing or not properly configured!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)