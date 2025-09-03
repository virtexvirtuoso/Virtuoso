#!/usr/bin/env python3
"""
Quick startup test to identify critical issues
"""
import sys
import os
import asyncio
import traceback

# Add project to path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

async def test_startup():
    """Test system startup components step by step"""
    
    print("🔍 Testing Virtuoso System Startup")
    print("=" * 50)
    
    # Test 1: Basic imports
    print("\n1. Testing basic imports...")
    try:
        from src.main import app
        print("✅ FastAPI app imports successfully")
    except Exception as e:
        print(f"❌ FastAPI app import failed: {e}")
        traceback.print_exc()
        return
    
    # Test 2: Configuration
    print("\n2. Testing configuration...")
    try:
        from src.config.manager import ConfigManager
        config_manager = ConfigManager()
        api_config = config_manager.config.get('api', {})
        port = api_config.get('port', 8003)
        print(f"✅ Configuration loaded, API port: {port}")
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        traceback.print_exc()
        return
        
    # Test 3: Essential components
    print("\n3. Testing essential component imports...")
    try:
        from src.monitoring.monitor import MarketMonitor
        monitor = MarketMonitor()
        print("✅ MarketMonitor imports and instantiates successfully") 
        print(f"✅ Monitor has {len([m for m in dir(monitor) if not m.startswith('_')])} public methods")
    except Exception as e:
        print(f"❌ MarketMonitor import/instantiation failed: {e}")
        traceback.print_exc()
        return
    
    # Test 4: Cache system
    print("\n4. Testing cache system...")
    try:
        from src.api.cache_adapter_direct import DirectCacheAdapter
        cache = DirectCacheAdapter()
        print("✅ Cache adapter initialized")
    except Exception as e:
        print(f"❌ Cache initialization failed: {e}")
        traceback.print_exc()
    
    # Test 5: API routes
    print("\n5. Testing API routes...")
    try:
        from src.api import api
        print("✅ API routes imported successfully")
    except Exception as e:
        print(f"❌ API routes import failed: {e}")
        traceback.print_exc()
    
    # Test 6: Simple server startup test
    print("\n6. Testing server startup...")
    try:
        import uvicorn
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1", 
            port=8003,
            log_level="info"
        )
        server = uvicorn.Server(config)
        print("✅ Uvicorn server config created successfully")
        
        # Try to bind to port (without starting)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('127.0.0.1', 8003))
            sock.close()
            print("✅ Port 8003 is available for binding")
        except OSError as e:
            print(f"❌ Port 8003 binding test failed: {e}")
        
    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎯 Startup test completed")

if __name__ == "__main__":
    asyncio.run(test_startup())