#!/usr/bin/env python3
"""
Display current run information from the running application
"""

import requests
import json
from datetime import datetime

def get_run_info():
    """Get run information from the application"""
    base_url = "http://localhost:8000"
    
    print("\n" + "="*60)
    print("VIRTUOSO TRADING SYSTEM - RUN INFORMATION")
    print("="*60 + "\n")
    
    try:
        # Try to get root endpoint
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            print(f"📍 Status: {data.get('status', 'Unknown').upper()}")
            print(f"🏷️  Run ID: {data.get('run_id', 'N/A')}")
            print(f"🔢 Run Number: {data.get('run_number', 'N/A')}")
            print(f"🕰️  Started: {data.get('run_started', 'N/A')}")
            print(f"⏱️  Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate uptime if possible
            if data.get('run_started'):
                try:
                    start_time = datetime.strptime(data['run_started'], '%Y-%m-%d %H:%M:%S')
                    uptime = datetime.now() - start_time
                    hours, remainder = divmod(uptime.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    print(f"⏰ Uptime: {uptime.days}d {hours}h {minutes}m {seconds}s")
                except:
                    pass
            
            # Show component status
            print("\n📊 Component Status:")
            components = data.get('components', {})
            for comp_name, comp_data in components.items():
                status = comp_data.get('status', 'unknown')
                status_icon = "✅" if status in ['active', 'connected'] else "❌"
                print(f"  {status_icon} {comp_name}: {status}")
            
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            
        # Try to get version info
        try:
            version_response = requests.get(f"{base_url}/version", timeout=5)
            if version_response.status_code == 200:
                version_data = version_response.json()
                print(f"\n🚀 Version: {version_data.get('version', 'Unknown')}")
        except:
            pass
            
    except requests.ConnectionError:
        print("❌ Cannot connect to application - is it running?")
        print("\nTo start the application:")
        print("  1. source venv311/bin/activate")
        print("  2. python src/main.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    get_run_info()