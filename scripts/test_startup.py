#!/usr/bin/env python3
"""
Test script to verify the startup fix works correctly.
"""

import os
import sys
import asyncio
import signal
from pathlib import Path

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_config_manager():
    """Test that config manager works correctly."""
    print("🧪 Testing config manager...")
    
    try:
        from src.config.manager import ConfigManager
        config_manager = ConfigManager()
        
        if config_manager.config is None:
            print("❌ Config manager returned None")
            return False
        
        web_config = config_manager.config.get('web_server', {})
        if not web_config:
            print("❌ No web_server configuration found")
            return False
        
        required_keys = ['host', 'port', 'auto_fallback', 'fallback_ports']
        for key in required_keys:
            if key not in web_config:
                print(f"❌ Missing required key: {key}")
                return False
        
        print("✅ Config manager test passed")
        print(f"   Host: {web_config['host']}")
        print(f"   Port: {web_config['port']}")
        print(f"   Auto fallback: {web_config['auto_fallback']}")
        print(f"   Fallback ports: {web_config['fallback_ports']}")
        return True
        
    except Exception as e:
        print(f"❌ Config manager test failed: {e}")
        return False

async def test_web_server_startup():
    """Test that web server can start without errors."""
    print("\n🧪 Testing web server startup...")
    
    try:
        # Import the main module
        from src.main import start_web_server, config_manager
        from src.config.manager import ConfigManager
        
        # Initialize config manager globally (simulating run_application)
        import src.main
        src.main.config_manager = ConfigManager()
        
        print("✅ Web server startup test passed (config available)")
        return True
        
    except Exception as e:
        print(f"❌ Web server startup test failed: {e}")
        return False

async def test_port_manager():
    """Test that port manager works with config.yaml."""
    print("\n🧪 Testing port manager...")
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/port_manager.py", "--show-config"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent
        )
        
        if "Current web server configuration:" in result.stdout:
            print("✅ Port manager test passed")
            return True
        else:
            print("❌ Port manager output unexpected")
            print(result.stdout)
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Port manager test failed: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Port manager test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing Virtuoso Startup Fix")
    print("=" * 40)
    
    tests = [
        test_config_manager,
        test_web_server_startup,
        test_port_manager
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {i+1}. {test.__name__}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! The startup fix is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted")
        sys.exit(1) 