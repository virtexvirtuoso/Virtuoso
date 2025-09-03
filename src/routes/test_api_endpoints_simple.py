#!/usr/bin/env python3
"""
Simplified API endpoint test that inspects route files directly without importing the full app.
This avoids dependency issues while still verifying route structure.
"""

import os
import re
from typing import List, Dict, Set, Tuple
from pathlib import Path

def find_route_files(routes_dir: str) -> List[str]:
    """Find all Python files in the routes directory."""
    route_files = []
    for file in os.listdir(routes_dir):
        if file.endswith('.py') and not file.startswith('__') and not file.startswith('test_'):
            route_files.append(file)
    return sorted(route_files)

def extract_routes_from_file(file_path: str) -> List[Dict[str, str]]:
    """Extract route definitions from a Python file."""
    routes = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find router variable
        router_match = re.search(r'router\s*=\s*APIRouter\(\)', content)
        if not router_match:
            return routes
        
        # Find all route decorators
        # Patterns: @router.get, @router.post, @router.put, @router.delete, @router.patch
        route_pattern = r'@router\.(get|post|put|delete|patch|websocket)\s*\(\s*["\']([^"\']+)["\']'
        
        for match in re.finditer(route_pattern, content):
            method = match.group(1).upper()
            path = match.group(2)
            
            # Try to find the function name
            # Look for the next function definition after the decorator
            remaining_content = content[match.end():match.end()+500]
            func_match = re.search(r'def\s+(\w+)\s*\(', remaining_content)
            func_name = func_match.group(1) if func_match else 'unknown'
            
            routes.append({
                'method': method,
                'path': path,
                'function': func_name,
                'file': os.path.basename(file_path)
            })
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return routes

def analyze_api_structure():
    """Analyze the API structure by inspecting route files."""
    # Get the routes directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    routes_dir = current_dir
    
    print("\n" + "="*80)
    print("API ENDPOINT STRUCTURE ANALYSIS")
    print("="*80)
    print(f"Routes Directory: {routes_dir}")
    
    # Find all route files
    route_files = find_route_files(routes_dir)
    print(f"\nFound {len(route_files)} route files:")
    for file in route_files:
        print(f"  - {file}")
    
    # Extract routes from each file
    all_routes = []
    routes_by_file = {}
    
    for file in route_files:
        file_path = os.path.join(routes_dir, file)
        routes = extract_routes_from_file(file_path)
        if routes:
            routes_by_file[file] = routes
            all_routes.extend(routes)
    
    # Print route analysis
    print(f"\n\nTotal Routes Found: {len(all_routes)}")
    
    print("\n" + "="*80)
    print("ROUTES BY FILE:")
    print("="*80)
    
    for file, routes in sorted(routes_by_file.items()):
        module_name = file.replace('.py', '')
        print(f"\n{module_name.upper()} ({len(routes)} routes):")
        
        for route in routes:
            print(f"  {route['method']:7} {route['path']:40} -> {route['function']}()")
    
    # Check main.py for route registration
    print("\n" + "="*80)
    print("ROUTE REGISTRATION IN API/__init__.py:")
    print("="*80)
    
    api_init_path = os.path.join(os.path.dirname(routes_dir), '__init__.py')
    if os.path.exists(api_init_path):
        with open(api_init_path, 'r') as f:
            content = f.read()
        
        # Find router inclusions
        include_pattern = r'app\.include_router\s*\(\s*(\w+)\.router,\s*prefix\s*=\s*["\']([^"\']+)["\']'
        
        print("\nRegistered Route Groups:")
        for match in re.finditer(include_pattern, content):
            module = match.group(1)
            prefix = match.group(2)
            print(f"  {module:20} -> {prefix}")
    
    # Expected vs Actual Analysis
    print("\n" + "="*80)
    print("EXPECTED ROUTE PATTERNS:")
    print("="*80)
    
    expected_patterns = {
        'signals': ['/latest', '/history', '/stats', '/symbol/{symbol}'],
        'market': ['/overview', '/symbols', '/data/{symbol}', '/analysis/{symbol}'],
        'alpha': ['/scan', '/opportunities', '/stats', '/history'],
        'dashboard': ['/overview', '/stats', '/alerts', '/alerts/recent'],
        'liquidation': ['/alerts', '/history', '/stats', '/risk-map'],
        'correlation': ['/matrix', '/live-matrix', '/analysis', '/pairs'],
        'manipulation': ['/alerts', '/stats', '/history', '/analyze'],
        'whale_activity': ['/alerts', '/transactions', '/stats', '/impact'],
        'sentiment': ['/analysis', '/indicators', '/social', '/trends']
    }
    
    # Match expected patterns with actual routes
    for module, expected_paths in expected_patterns.items():
        module_file = f"{module}.py"
        if module_file in routes_by_file:
            actual_paths = [r['path'] for r in routes_by_file[module_file]]
            print(f"\n{module.upper()}:")
            print(f"  Expected: {len(expected_paths)} routes")
            print(f"  Actual: {len(actual_paths)} routes")
            
            # Check which expected routes exist
            for path in expected_paths:
                if path in actual_paths:
                    print(f"  ✅ {path}")
                else:
                    print(f"  ❌ {path} (missing)")
            
            # Show extra routes not in expected list
            extra_routes = set(actual_paths) - set(expected_paths)
            if extra_routes:
                print(f"  Additional routes found:")
                for path in extra_routes:
                    print(f"    + {path}")

def main():
    """Main function."""
    print("API Endpoint Structure Analysis Tool")
    print("This tool analyzes route files without importing the full application.\n")
    
    analyze_api_structure()
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print("✅ Analysis complete!")
    print("\nNote: This analysis is based on static file inspection.")
    print("Some dynamic routes or middleware-added routes may not be detected.")
    print("\nTo verify actual runtime routes, the application must be running.")

if __name__ == "__main__":
    main()