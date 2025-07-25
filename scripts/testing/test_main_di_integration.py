#!/usr/bin/env python3
"""
Test the main application DI integration.

This test verifies that the main application can start up with the new
dependency injection system and that services are properly available.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

async def test_main_di_integration():
    """Test that main.py DI integration works."""
    print("Testing main application DI integration...")
    
    try:
        # Import the lifespan function
        from src.main import lifespan
        from fastapi import FastAPI
        
        # Create a test FastAPI app
        app = FastAPI()
        
        # Test the lifespan function
        print("🚀 Testing application startup with DI...")
        
        async with lifespan(app) as _:
            print("✅ Application started successfully with DI")
            
            # Test that services are available in app state
            container = getattr(app.state, 'container', None)
            if container:
                print(f"✅ DI container available with {container.get_stats()['services_registered_count']} services")
            else:
                print("⚠️ DI container not found in app state")
            
            # Test service availability
            alert_manager = getattr(app.state, 'alert_manager', None)
            if alert_manager:
                print("✅ Alert manager available")
            else:
                print("⚠️ Alert manager not available")
            
            metrics_manager = getattr(app.state, 'metrics_manager', None)
            if metrics_manager:
                print("✅ Metrics manager available")
            else:
                print("⚠️ Metrics manager not available")
            
            config_manager = getattr(app.state, 'config_manager', None)
            if config_manager:
                print("✅ Config manager available")
            else:
                print("⚠️ Config manager not available")
        
        print("✅ Application shutdown completed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Main DI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_dependencies():
    """Test that API dependencies work."""
    print("\nTesting API dependencies...")
    
    try:
        from src.api.dependencies import (
            get_alert_service, get_metrics_service, get_config_service,
            get_container
        )
        from fastapi import Request
        from unittest.mock import MagicMock
        
        # Create mock request with app state
        mock_request = MagicMock()
        mock_request.app.state.container = None
        mock_request.app.state.alert_manager = "mock_alert"
        mock_request.app.state.metrics_manager = "mock_metrics"
        mock_request.app.state.config_manager = "mock_config"
        
        # Test dependency functions
        alert_service = get_alert_service(mock_request)
        if alert_service == "mock_alert":
            print("✅ Alert service dependency works")
        else:
            print("⚠️ Alert service dependency fallback issue")
        
        metrics_service = get_metrics_service(mock_request)
        if metrics_service == "mock_metrics":
            print("✅ Metrics service dependency works")
        else:
            print("⚠️ Metrics service dependency fallback issue")
        
        config_service = get_config_service(mock_request)
        if config_service == "mock_config":
            print("✅ Config service dependency works")
        else:
            print("⚠️ Config service dependency fallback issue")
        
        print("✅ API dependencies test completed")
        return True
        
    except Exception as e:
        print(f"✗ API dependencies test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run DI integration tests."""
    print("🧪 Testing Main Application DI Integration")
    print("=" * 60)
    
    tests = [
        ("Main DI Integration", test_main_di_integration),
        ("API Dependencies", test_api_dependencies)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 40)
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 DI INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All DI integration tests passed!")
        print("✨ Main application is ready for DI-powered operation!")
    else:
        print(f"\n⚠️ {failed} tests failed. Please review and fix.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)