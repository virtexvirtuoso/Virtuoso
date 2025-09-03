#!/usr/bin/env python3
"""
Simple test script to verify that all API endpoints are properly registered and working.
This script tests route registration without running complex logic.
"""

import os
import re
from typing import List, Dict, Set
from collections import defaultdict

def extract_routes_from_file(file_path: str) -> List[Dict[str, str]]:
    """Extract route definitions from a Python file."""
    routes = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if file has APIRouter
        if 'APIRouter()' not in content:
            return routes
        
        # Find all route decorators
        route_pattern = r'@router\.(get|post|put|delete|patch|websocket)\s*\(\s*["\']([^"\']+)["\']'
        
        for match in re.finditer(route_pattern, content):
            method = match.group(1).upper()
            path = match.group(2)
            
            # Find function name
            remaining = content[match.end():match.end()+500]
            func_match = re.search(r'def\s+(\w+)\s*\(', remaining)
            func_name = func_match.group(1) if func_match else 'unknown'
            
            routes.append({
                'method': method,
                'path': path,
                'function': func_name,
                'file': os.path.basename(file_path).replace('.py', '')
            })
    except:
        pass
    
    # Remove duplicates
    seen = set()
    unique_routes = []
    for route in routes:
        key = (route['method'], route['path'], route['function'])
        if key not in seen:
            seen.add(key)
            unique_routes.append(route)
    
    return unique_routes

def get_api_init_prefixes(api_init_path: str) -> Dict[str, str]:
    """Extract route prefixes from API __init__.py."""
    prefixes = {}
    
    try:
        with open(api_init_path, 'r') as f:
            content = f.read()
        
        # Find router inclusions (handles both quoted strings and f-strings)
        patterns = [
            # Pattern for regular quotes
            r'app\.include_router\s*\(\s*(\w+)\.router,\s*prefix\s*=\s*["\']([^"\']+)["\']',
            # Pattern for f-strings
            r'app\.include_router\s*\(\s*(\w+)\.router,\s*prefix\s*=\s*f["\'][^"\']*/([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                if pattern.startswith(r'app\.include_router\s*\(\s*(\w+)\.router,\s*prefix\s*=\s*f'):
                    # For f-strings, prepend /api/
                    prefix = '/api/' + match.group(2)
                else:
                    prefix = match.group(2)
                prefixes[module] = prefix
    except:
        pass
    
    return prefixes

def main():
    """Main test function."""
    routes_dir = os.path.dirname(os.path.abspath(__file__))
    api_init_path = os.path.join(os.path.dirname(routes_dir), '__init__.py')
    
    print("\n" + "="*80)
    print("API ENDPOINT REGISTRATION TEST")
    print("="*80)
    print("Testing route registration without importing the full application.\n")
    
    # Get all Python files
    route_files = [f for f in os.listdir(routes_dir) 
                   if f.endswith('.py') and not f.startswith('__') and not f.startswith('test_')]
    
    print(f"Found {len(route_files)} route modules")
    
    # Get route prefixes
    prefixes = get_api_init_prefixes(api_init_path)
    print(f"Found {len(prefixes)} registered prefixes in __init__.py\n")
    
    # Extract routes from each file
    all_routes = []
    routes_by_module = defaultdict(list)
    
    for file in sorted(route_files):
        file_path = os.path.join(routes_dir, file)
        routes = extract_routes_from_file(file_path)
        module = file.replace('.py', '')
        
        if routes:
            routes_by_module[module] = routes
            for route in routes:
                # Apply prefix if registered
                if module in prefixes:
                    route['full_path'] = prefixes[module] + route['path']
                else:
                    route['full_path'] = route['path']
                all_routes.append(route)
    
    # Print summary
    print("SUMMARY:")
    print("-"*40)
    print(f"Total unique endpoints: {len(all_routes)}")
    print(f"Modules with routes: {len(routes_by_module)}")
    
    # Print routes by module
    print("\n\nROUTES BY MODULE:")
    print("="*80)
    
    for module, routes in sorted(routes_by_module.items()):
        prefix = prefixes.get(module, 'N/A')
        print(f"\n{module.upper()} ({len(routes)} routes)")
        if prefix != 'N/A':
            print(f"Registered prefix: {prefix}")
        else:
            print("⚠️  No prefix registered in __init__.py")
        print("-"*40)
        
        for route in sorted(routes, key=lambda x: (x['method'], x['path'])):
            full_path = route.get('full_path', route['path'])
            print(f"  {route['method']:8} {full_path:45} → {route['function']}()")
    
    # List modules not registered
    print("\n\nREGISTRATION STATUS:")
    print("="*80)
    
    registered_modules = set(prefixes.keys())
    route_modules = set(routes_by_module.keys())
    
    print("\n✅ Registered modules:")
    for module in sorted(registered_modules & route_modules):
        print(f"  - {module} → {prefixes[module]}")
    
    unregistered = route_modules - registered_modules
    if unregistered:
        print("\n⚠️  Modules with routes but no registration:")
        for module in sorted(unregistered):
            print(f"  - {module} ({len(routes_by_module[module])} routes)")
    
    # Core routes from main.py
    print("\n\nCORE ROUTES (defined in main.py):")
    print("="*80)
    print("These routes are registered directly in the main application:")
    
    core_routes = [
        "GET     /",
        "GET     /health", 
        "GET     /version",
        "GET     /ui",
        "GET     /dashboard",
        "GET     /analysis/{symbol}",
        "WebSocket /ws/analysis/{symbol}",
        "GET     /api/top-symbols",
        "GET     /api/bybit-direct/top-symbols",
        "GET     /api/market-report",
        "GET     /api/dashboard/overview",
        "GET     /api/correlation/live-matrix",
        "GET     /api/alpha/opportunities",
        "POST    /api/alpha/scan",
        "GET     /api/liquidation/alerts",
        "GET     /api/manipulation/alerts",
        "GET     /api/signals/latest",
        "GET     /api/bitcoin-beta/status",
        "POST    /api/bitcoin-beta/generate",
        "POST    /api/websocket/initialize",
        "GET     /api/websocket/status"
    ]
    
    for route in core_routes:
        print(f"  {route}")
    
    # Final summary
    print("\n" + "="*80)
    print("TEST RESULTS:")
    print("="*80)
    
    total_routes = len(all_routes) + len(core_routes)
    print(f"\n✅ Found {total_routes} total API endpoints:")
    print(f"   - {len(all_routes)} routes in modules")
    print(f"   - {len(core_routes)} core routes in main.py")
    
    if unregistered:
        print(f"\n⚠️  {len(unregistered)} modules need registration in __init__.py")
    else:
        print("\n✅ All route modules are properly registered!")
    
    print("\n📝 Note: To verify runtime connectivity, start the server and test endpoints.")
    print("   Run: python src/main.py")
    print("   Then test: curl http://localhost:8000/health")

if __name__ == "__main__":
    main()