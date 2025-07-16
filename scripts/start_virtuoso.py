#!/usr/bin/env python3
"""
Smart startup script for Virtuoso Trading System.
Checks port availability and handles conflicts automatically.
"""

import os
import sys
import subprocess
import socket
from pathlib import Path

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_port_available(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('localhost', port))
        return result != 0

def main():
    """Main startup function."""
    print("🚀 Virtuoso Trading System - Smart Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("config/config.yaml").exists():
        print("❌ Error: config/config.yaml not found")
        print("   Please run this script from the Virtuoso root directory")
        sys.exit(1)
    
    # Check current port configuration
    try:
        result = subprocess.run(
            [sys.executable, "scripts/port_manager.py", "--show-config"],
            capture_output=True,
            text=True,
            check=True
        )
        print("📋 Current Configuration:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error reading configuration: {e}")
        sys.exit(1)
    
    # Check if auto-fix is needed
    try:
        result = subprocess.run(
            [sys.executable, "scripts/port_manager.py", "--auto-fix"],
            capture_output=True,
            text=True,
            check=True
        )
        print("🔧 Port Check:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during port check: {e}")
        sys.exit(1)
    
    # Start the main application
    print("\n🎯 Starting Virtuoso Trading System...")
    print("   Dashboard will be available at: http://localhost:<port>/dashboard")
    print("   API documentation at: http://localhost:<port>/docs")
    print("   Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Run the main application
        subprocess.run([sys.executable, "-m", "src.main"], check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown signal received")
        print("✅ Virtuoso Trading System stopped")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 