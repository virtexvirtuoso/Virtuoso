#!/usr/bin/env python3
"""
Quick Dashboard Connectivity Test
Checks if the dashboard and its APIs are accessible
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"

def test_connectivity():
    """Quick connectivity test for dashboard"""
    print(f"\nDashboard Connectivity Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("Dashboard HTML", f"{BASE_URL}/", "GET"),
        ("System Status API", f"{BASE_URL}/api/system/status", "GET"),
        ("Dashboard Overview API", f"{BASE_URL}/api/dashboard/overview", "GET"),
    ]
    
    for name, url, method in tests:
        try:
            response = requests.request(method, url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: OK (Status: {response.status_code})")
                if "api" in url:
                    try:
                        data = response.json()
                        print(f"  Response keys: {list(data.keys())[:5]}...")
                    except:
                        pass
            else:
                print(f"✗ {name}: Failed (Status: {response.status_code})")
        except requests.ConnectionError:
            print(f"✗ {name}: Connection Failed - Server not running?")
        except requests.Timeout:
            print(f"✗ {name}: Timeout")
        except Exception as e:
            print(f"✗ {name}: Error - {str(e)}")
    
    print("\nNote: If tests fail, ensure the application is running with:")
    print("  python src/main.py")

if __name__ == "__main__":
    test_connectivity()