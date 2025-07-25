#!/usr/bin/env python3
"""Verify that all dashboard_v10.html API endpoints are properly defined in the code."""

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

def check_multiple_files(files, route_pattern):
    """Check if route exists in any of the given files."""
    for file_path in files:
        if check_route_exists(file_path, route_pattern):
            return True, file_path
    return False, None

def main():
    print("🔍 Dashboard v10 API Route Verification")
    print("=" * 60)
    
    # All API endpoints found in dashboard_v10.html
    v10_endpoints = [
        # Core dashboard endpoints
        ("/api/dashboard/overview", '@router.get("/overview")'),
        ("/api/liquidation/alerts", '@router.get("/api/liquidation/alerts")'),
        ("/api/liquidation/stress-indicators", '@router.get("/api/liquidation/stress-indicators")'),
        ("/api/liquidation/cascade-risk", '@router.get("/api/liquidation/cascade-risk")'),
        ("/api/alpha/opportunities", '@router.get("/api/alpha/opportunities")'),
        ("/api/alpha/scan", '@router.post("/api/alpha/scan")'),
        ("/api/system/status", '@router.get("/api/system/status")'),
        ("/api/system/performance", '@router.get("/api/system/performance")'),
        
        # Trading endpoints
        ("/api/trading/portfolio/summary", '/portfolio/summary'),
        ("/api/trading/orders", '@router.get("/orders")'),
        ("/api/trading/positions", '@router.get("/positions")'),
        
        # Market endpoints
        ("/api/market/overview", '@router.get("/overview")'),
        ("/api/bitcoin-beta/status", '@router.get("/status")'),
        
        # Signal endpoints
        ("/api/signals/signals/latest", '/signals/latest'),
        ("/api/dashboard/alerts/recent", '@router.get("/alerts/recent")'),
        
        # Manipulation detection
        ("/api/manipulation/alerts", '@router.get("/alerts")'),
        ("/api/manipulation/stats", '@router.get("/stats")'),
        
        # Symbol endpoints
        ("/api/top-symbols/", '@router.get("/")'),
        
        # Correlation endpoints
        ("/api/correlation/live-matrix", '@router.get("/live-matrix")'),
        
        # WebSocket endpoint
        ("/api/dashboard/ws", '@router.websocket("/ws")'),
        
        # Additional endpoints
        ("/api/active", '@router.get("/active")'),
        ("/api/market/ticker/", '@router.get("/ticker/{symbol}")'),
        ("/api/signal-tracking/tracked/", '@router.get("/tracked/{signal_id}")'),
    ]
    
    # Route files to check
    route_files = [
        Path("src/api/routes/dashboard.py"),
        Path("src/api/routes/signals.py"),
        Path("src/api/routes/alpha.py"),
        Path("src/api/routes/liquidation.py"),
        Path("src/api/routes/correlation.py"),
        Path("src/api/routes/signal_tracking.py"),
        Path("src/api/routes/trading.py"),
        Path("src/api/routes/market.py"),
        Path("src/api/routes/manipulation.py"),
        Path("src/api/routes/bitcoin_beta.py"),
        Path("src/api/routes/top_symbols.py"),
    ]
    
    # Check which route files exist
    existing_files = []
    missing_files = []
    
    for file_path in route_files:
        if file_path.exists():
            existing_files.append(file_path)
            print(f"✅ Found: {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ Missing: {file_path}")
    
    print("-" * 60)
    print(f"Route files found: {len(existing_files)}")
    print(f"Route files missing: {len(missing_files)}")
    print("-" * 60)
    
    # Check each endpoint
    all_routes_found = True
    routes_status = []
    
    for endpoint, route_pattern in v10_endpoints:
        found, found_file = check_multiple_files(existing_files, route_pattern)
        
        if found:
            status = f"✅ {endpoint:<35} - Found in {found_file.name}"
            routes_status.append((endpoint, True, found_file.name))
        else:
            status = f"❌ {endpoint:<35} - NOT FOUND"
            routes_status.append((endpoint, False, None))
            all_routes_found = False
        
        print(status)
    
    print("-" * 60)
    
    # Summary
    found_count = sum(1 for _, found, _ in routes_status if found)
    total_count = len(routes_status)
    
    print(f"Endpoints found: {found_count}/{total_count}")
    
    if not all_routes_found:
        print(f"\n❌ Missing endpoints:")
        for endpoint, found, _ in routes_status:
            if not found:
                print(f"   - {endpoint}")
    
    print("=" * 60)
    
    if all_routes_found:
        print("✅ All dashboard v10 API endpoints are properly defined!")
        print("\n📊 To test connectivity, start the server with:")
        print("   python src/main.py")
        print("\n🧪 Then run the live endpoint test:")
        print("   python scripts/testing/test_v10_dashboard_endpoints.py")
        return True
    else:
        print("❌ Some routes are missing or not properly configured!")
        print(f"\n📝 {len(missing_files)} route files are missing:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)