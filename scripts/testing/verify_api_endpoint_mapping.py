#!/usr/bin/env python3
"""Verify API endpoint mapping for mobile and regular dashboards."""

import sys
import os
import re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def extract_api_calls(file_path):
    """Extract all API calls from an HTML file."""
    api_calls = set()
    
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Find all fetch() calls
    fetch_pattern = r'fetch\([\'"`]([^\'"`]+)[\'"`]'
    matches = re.findall(fetch_pattern, content)
    
    for match in matches:
        # Skip WebSocket URLs
        if match.startswith('ws://') or match.startswith('wss://'):
            continue
        # Extract just the path part
        if match.startswith('${'):
            # Handle template strings like ${API_BASE_URL}/api/...
            api_match = re.search(r'/api/[^\'"`]+', match)
            if api_match:
                api_calls.add(api_match.group())
        elif match.startswith('/api/'):
            api_calls.add(match)
    
    return sorted(api_calls)

def find_route_definitions(src_path):
    """Find all route definitions in the source code."""
    routes = {}
    
    # Search patterns for different route definition styles
    patterns = [
        r'@router\.get\([\'"`]([^\'"`]+)[\'"`]',
        r'@router\.post\([\'"`]([^\'"`]+)[\'"`]',
        r'@router\.put\([\'"`]([^\'"`]+)[\'"`]',
        r'@router\.delete\([\'"`]([^\'"`]+)[\'"`]',
        r'@app\.get\([\'"`]([^\'"`]+)[\'"`]',
        r'@app\.post\([\'"`]([^\'"`]+)[\'"`]',
    ]
    
    # Search all Python files
    for py_file in Path(src_path).rglob('*.py'):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.startswith('/'):
                        # Get the router prefix if it's a router endpoint
                        if '@router.' in content:
                            # Try to find the router prefix
                            prefix_match = re.search(r'prefix=f?[\'"`]([^\'"`]+)[\'"`]', content)
                            if prefix_match and 'router' in py_file.name:
                                prefix = prefix_match.group(1)
                                if '{api_prefix}' in prefix:
                                    prefix = prefix.replace('{api_prefix}', '/api')
                                elif '$' in prefix:
                                    prefix = re.sub(r'\$\{[^}]+\}', '/api', prefix)
                                full_path = prefix + match
                            else:
                                # Check the file name to determine the prefix
                                file_name = py_file.stem
                                if file_name == 'main':
                                    full_path = match
                                elif file_name == 'dashboard':
                                    full_path = '/api/dashboard' + match
                                elif file_name == 'signals':
                                    full_path = '/api/signals' + match
                                elif file_name == 'alpha':
                                    full_path = '/api/alpha' + match
                                elif file_name == 'liquidation':
                                    full_path = '/api/liquidation' + match
                                else:
                                    full_path = '/api/' + file_name + match
                        else:
                            full_path = match
                            
                        routes[full_path] = str(py_file.relative_to(src_path))
                        
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return routes

def main():
    """Main verification function."""
    print("🔍 Verifying API Endpoint Mapping\n")
    
    # Paths
    mobile_path = Path("src/dashboard/templates/dashboard_mobile_v1.html")
    v10_path = Path("src/dashboard/templates/dashboard_v10.html")
    src_path = Path("src")
    
    # Extract API calls from both dashboards
    print("📱 Mobile Dashboard API Calls:")
    mobile_apis = extract_api_calls(mobile_path)
    for api in mobile_apis:
        print(f"  - {api}")
    
    print("\n💻 V10 Dashboard API Calls:")
    v10_apis = extract_api_calls(v10_path)
    for api in v10_apis:
        print(f"  - {api}")
    
    # Find all defined routes
    print("\n🔧 Finding Defined Routes...")
    defined_routes = find_route_definitions(src_path)
    
    # Check mobile dashboard endpoints
    print("\n✅ Mobile Dashboard Endpoint Verification:")
    mobile_missing = []
    for api in mobile_apis:
        # Handle dynamic parts in the path
        api_pattern = api.replace('{', '\\{').replace('}', '\\}')
        found = False
        for route in defined_routes:
            if route == api or re.match(api_pattern.replace('\\{[^}]+\\}', '[^/]+'), route):
                print(f"  ✓ {api} -> Found in {defined_routes.get(route, 'unknown')}")
                found = True
                break
        if not found:
            print(f"  ❌ {api} -> NOT FOUND")
            mobile_missing.append(api)
    
    # Check V10 dashboard endpoints
    print("\n✅ V10 Dashboard Endpoint Verification:")
    v10_missing = []
    for api in v10_apis:
        # Handle dynamic parts in the path
        api_pattern = api.replace('{', '\\{').replace('}', '\\}')
        found = False
        for route in defined_routes:
            if route == api or re.match(api_pattern.replace('\\{[^}]+\\}', '[^/]+'), route):
                print(f"  ✓ {api} -> Found in {defined_routes.get(route, 'unknown')}")
                found = True
                break
        if not found:
            print(f"  ❌ {api} -> NOT FOUND")
            v10_missing.append(api)
    
    # Summary
    print("\n📊 Summary:")
    print(f"Mobile Dashboard: {len(mobile_apis)} endpoints, {len(mobile_missing)} missing")
    print(f"V10 Dashboard: {len(v10_apis)} endpoints, {len(v10_missing)} missing")
    
    if mobile_missing:
        print("\n⚠️  Missing Mobile Endpoints:")
        for api in mobile_missing:
            print(f"  - {api}")
    
    if v10_missing:
        print("\n⚠️  Missing V10 Endpoints:")
        for api in v10_missing:
            print(f"  - {api}")
    
    # Check for common issues
    print("\n🔍 Common Issues Check:")
    
    # Check if API prefix is properly configured
    if any('/api/api/' in route for route in defined_routes):
        print("  ⚠️  Double '/api' prefix detected in some routes")
    
    # Check for duplicate routes
    route_counts = {}
    for route in defined_routes:
        route_counts[route] = route_counts.get(route, 0) + 1
    
    duplicates = {k: v for k, v in route_counts.items() if v > 1}
    if duplicates:
        print("  ⚠️  Duplicate routes found:")
        for route, count in duplicates.items():
            print(f"    - {route} (defined {count} times)")
    
    print("\n✅ Verification Complete!")

if __name__ == "__main__":
    main()