#!/usr/bin/env python3
"""
Virtuoso Trading System Startup Script
Starts the integrated Virtuoso Trading System with full dashboard functionality.
Includes: Trading System + Market Monitoring + Dashboard Web Interface
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the integrated Virtuoso Trading System with Dashboard."""
    
    print("🚀 Starting Virtuoso Trading System with Integrated Dashboard...")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("src/web_server.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        print("   Current directory:", os.getcwd())
        print("   Expected: /path/to/Virtuoso_ccxt")
        return 1
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("   Consider activating your virtual environment first:")
        print("   source venv311/bin/activate")
        print()
    
    print("✅ Starting integrated trading system...")
    print("📊 Dashboard and Trading System will be available at:")
    print("   Main Dashboard: http://localhost:8000/dashboard")
    print("   Market Analysis: http://localhost:8000/market-analysis") 
    print("   Beta Analysis: http://localhost:8000/beta-analysis")
    print("   System Status: http://localhost:8000/")
    print("   API Health: http://localhost:8000/health")
    print("   WebSocket Analysis: ws://localhost:8000/ws/analysis/{symbol}")
    print()
    print("🎯 Features:")
    print("   ✅ Live Trading System + Market Monitoring")
    print("   ✅ Real-time Signal Confluence Analysis")
    print("   ✅ Integrated Dashboard with Live Data")
    print("   ✅ Alpha Opportunity Detection")
    print("   ✅ Discord Alerts & Notifications")
    print()
    print("Press Ctrl+C to stop the system")
    print("=" * 60)
    
    try:
        # Change to src directory and start the integrated main application
        os.chdir("src")
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 