#!/usr/bin/env python3
"""
Binance API Test Runner

Alternative to the bash script for systems where bash isn't available.
This script installs dependencies and runs the Binance API test.

Usage:
    python scripts/run_binance_test.py
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11+"""
    print("🐍 Checking Python version...")
    
    version_info = sys.version_info
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 11):
        print(f"❌ Python 3.11+ required, found {version_info.major}.{version_info.minor}")
        return False
    
    print(f"✅ Python {version_info.major}.{version_info.minor}.{version_info.micro} found")
    return True

def install_dependencies():
    """Install required packages"""
    print("\n📦 Installing required packages...")
    print("Installing: ccxt pandas tabulate")
    
    packages = ['ccxt', 'pandas', 'tabulate']
    
    try:
        for package in packages:
            print(f"   Installing {package}...")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("Try running manually: pip install ccxt pandas tabulate")
        return False

def check_test_script():
    """Check if test script exists"""
    print("\n📋 Checking test script...")
    
    script_path = Path("scripts/test_binance_api_calls.py")
    if not script_path.exists():
        print("❌ Test script not found at scripts/test_binance_api_calls.py")
        print("Please make sure you're in the Virtuoso_ccxt directory")
        return False
    
    print("✅ Test script found")
    return True

def run_test():
    """Run the Binance API test"""
    print("\n🔥 Running Binance API tests...")
    print("=" * 60)
    print()
    
    try:
        # Import and run the test directly
        import asyncio
        
        # Add the scripts directory to path so we can import
        scripts_dir = Path("scripts")
        sys.path.insert(0, str(scripts_dir))
        
        # Import the test module
        from test_binance_api_calls import main
        
        # Run the async test
        asyncio.run(main())
        
        return True
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print("Try running manually: python scripts/test_binance_api_calls.py")
        return False

def main():
    """Main function"""
    print("🚀 Binance API Integration Test Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Check test script
    if not check_test_script():
        sys.exit(1)
    
    # Run the test
    if not run_test():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Test execution completed!")
    print()
    print("💡 Next steps:")
    print("1. Review the test output above")
    print("2. Check for any API endpoints that failed")
    print("3. If tests passed, proceed with BinanceExchange implementation")
    print("4. Use the response structures shown to build the integration")

if __name__ == "__main__":
    main() 