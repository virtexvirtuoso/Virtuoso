#!/usr/bin/env python3
"""
Route Cleanup Verification Script
Tests that all routes are properly registered without conflicts.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_route_registration():
    """Test that all routes can be registered without conflicts."""
    print("🧪 Testing Route Registration After Cleanup...")
    
    try:
        from fastapi import FastAPI
        from src.api import init_api_routes
        
        # Create test FastAPI app
        app = FastAPI(title="Route Test App")
        
        # Try to initialize all routes
        print("📋 Initializing API routes...")
        init_api_routes(app)
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append({
                    'path': route.path,
                    'methods': list(route.methods),
                    'name': getattr(route, 'name', 'unknown')
                })
        
        # Sort routes by path for easy reading
        routes.sort(key=lambda x: x['path'])
        
        print(f"\n✅ Successfully registered {len(routes)} routes!")
        print("\n📊 Route Summary:")
        
        # Group by prefix for analysis
        prefixes = {}
        for route in routes:
            path_parts = route['path'].split('/')
            prefix = '/'.join(path_parts[:3]) if len(path_parts) >= 3 else route['path']
            
            if prefix not in prefixes:
                prefixes[prefix] = []
            prefixes[prefix].append(route)
        
        # Print grouped routes
        for prefix, prefix_routes in sorted(prefixes.items()):
            print(f"\n🔗 {prefix} ({len(prefix_routes)} routes)")
            for route in prefix_routes[:5]:  # Show first 5 routes per group
                methods_str = ','.join(route['methods'])
                print(f"   {methods_str:<8} {route['path']}")
            if len(prefix_routes) > 5:
                print(f"   ... and {len(prefix_routes) - 5} more routes")
        
        # Check for potential conflicts
        print("\n🔍 Checking for Route Conflicts...")
        path_conflicts = {}
        method_conflicts = []
        
        for route in routes:
            path = route['path']
            methods = route['methods']
            
            if path in path_conflicts:
                # Check if methods overlap
                existing_methods = path_conflicts[path]['methods']
                overlapping = set(methods) & set(existing_methods)
                if overlapping:
                    method_conflicts.append({
                        'path': path,
                        'conflicting_methods': list(overlapping),
                        'route1': path_conflicts[path],
                        'route2': route
                    })
                else:
                    # Different methods, this is okay
                    path_conflicts[path]['methods'].extend(methods)
            else:
                path_conflicts[path] = {
                    'methods': methods.copy(),
                    'route': route
                }
        
        if method_conflicts:
            print("❌ Found route conflicts:")
            for conflict in method_conflicts:
                print(f"   Path: {conflict['path']}")
                print(f"   Conflicting methods: {conflict['conflicting_methods']}")
                print(f"   Route 1: {conflict['route1']['route']['name']}")
                print(f"   Route 2: {conflict['route2']['name']}")
        else:
            print("✅ No route conflicts detected!")
        
        # Summary statistics
        total_endpoints = len(routes)
        unique_paths = len(path_conflicts)
        api_routes = len([r for r in routes if r['path'].startswith('/api/')])
        admin_routes = len([r for r in routes if r['path'].startswith('/admin')])
        
        print(f"\n📈 Route Statistics:")
        print(f"   Total Endpoints: {total_endpoints}")
        print(f"   Unique Paths: {unique_paths}")
        print(f"   API Routes: {api_routes}")
        print(f"   Admin Routes: {admin_routes}")
        
        return len(method_conflicts) == 0
        
    except Exception as e:
        print(f"❌ Error during route registration test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_critical_endpoints():
    """Test that critical endpoints are accessible."""
    print("\n🎯 Testing Critical Endpoints...")
    
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api import init_api_routes
        
        # Create test app
        app = FastAPI(title="Endpoint Test")
        init_api_routes(app)
        
        # Create test client
        client = TestClient(app)
        
        # Define critical endpoints to test
        critical_endpoints = [
            ("/api/dashboard/overview", "GET"),
            ("/api/dashboard/signals", "GET"),
            ("/api/dashboard/mobile-data", "GET"),
            ("/api/dashboard/health", "GET"),
            ("/api/confluence/stats", "GET"),
            ("/api/system/status", "GET"),
            ("/admin/dashboard", "GET"),
        ]
        
        results = []
        for endpoint, method in critical_endpoints:
            try:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json={})
                else:
                    continue
                
                status = "✅ PASS" if response.status_code < 500 else "❌ FAIL"
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'status': status
                })
                
                print(f"   {status} {method} {endpoint} → {response.status_code}")
                
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': 'ERROR',
                    'status': "❌ ERROR",
                    'error': str(e)
                })
                print(f"   ❌ ERROR {method} {endpoint} → {str(e)[:50]}...")
        
        # Summary
        passed = len([r for r in results if r['status'] == "✅ PASS"])
        total = len(results)
        print(f"\n📊 Critical Endpoint Test Results: {passed}/{total} passed")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ Error testing critical endpoints: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Route Cleanup Verification")
    print("=" * 50)
    
    # Test route registration
    registration_success = await test_route_registration()
    
    # Test critical endpoints
    endpoint_success = await test_critical_endpoints()
    
    # Final result
    print("\n" + "=" * 50)
    if registration_success and endpoint_success:
        print("✅ ALL TESTS PASSED - Route cleanup successful!")
        return True
    else:
        print("❌ SOME TESTS FAILED - Route conflicts may still exist")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)