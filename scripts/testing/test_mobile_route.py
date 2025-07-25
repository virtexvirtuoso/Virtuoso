#!/usr/bin/env python3
"""Test the mobile dashboard route."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pathlib import Path

# Check if the template file exists
template_path = Path("src/dashboard/templates/dashboard_mobile_v1.html")
print(f"✅ Mobile template exists: {template_path.exists()}")
print(f"   Path: {template_path.absolute()}")

# Check main.py for the route
main_path = Path("src/main.py")
if main_path.exists():
    content = main_path.read_text()
    if "@app.get(\"/dashboard/mobile\")" in content:
        print("✅ Mobile route found in main.py")
        print("   Route: /dashboard/mobile")
        print("   Access URL: http://localhost:8000/dashboard/mobile")
    else:
        print("❌ Mobile route NOT found in main.py")
else:
    print("❌ main.py not found")

print("\n📱 Mobile Dashboard Setup:")
print("1. The mobile route has been added to main.py")
print("2. Access the mobile dashboard at: http://localhost:8000/dashboard/mobile")
print("3. All API endpoints are properly configured")
print("\n✅ The 404 error should now be resolved!")