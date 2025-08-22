#\!/usr/bin/env python3
"""Fix the port mismatch - dashboard trying to fetch from wrong port"""

def fix_dashboard_proxy_ports():
    """Fix the hardcoded port 8003 to use 8004"""
    
    files_to_fix = [
        "src/dashboard/dashboard_proxy.py",
        "src/dashboard/dashboard_proxy_phase2.py"
    ]
    
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace port 8003 with 8004
            original = content
            content = content.replace('"http://localhost:8003"', '"http://localhost:8004"')
            content = content.replace("'http://localhost:8003'", "'http://localhost:8004'")
            content = content.replace("http://localhost:8003", "http://localhost:8004")
            
            if content \!= original:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed port in {file_path}")
            else:
                print(f"ℹ️  No changes needed in {file_path}")
                
        except FileNotFoundError:
            print(f"⚠️  File not found: {file_path}")
    
    # Also fix any dashboard routes that might have hardcoded 8003
    dashboard_route = "src/api/routes/dashboard.py"
    try:
        with open(dashboard_route, 'r') as f:
            content = f.read()
        
        original = content
        content = content.replace('"http://localhost:8003', '"http://localhost:8004')
        content = content.replace("'http://localhost:8003", "'http://localhost:8004")
        
        if content \!= original:
            with open(dashboard_route, 'w') as f:
                f.write(content)
            print(f"✅ Fixed port in {dashboard_route}")
        else:
            print(f"ℹ️  No hardcoded port 8003 in {dashboard_route}")
            
    except FileNotFoundError:
        print(f"⚠️  File not found: {dashboard_route}")

if __name__ == "__main__":
    fix_dashboard_proxy_ports()
    print("\n✅ Port configuration fixed\!")
    print("The dashboard will now fetch from the correct port (8004)")
