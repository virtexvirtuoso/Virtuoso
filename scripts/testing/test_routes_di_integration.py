#!/usr/bin/env python3
"""
Test FastAPI routes integration with the new dependency injection system.

This test verifies that the updated routes properly use the DI system
instead of direct app state access.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

async def test_alerts_route_di():
    """Test that alerts route uses DI properly."""
    print("Testing alerts route DI integration...")
    
    try:
        from src.api.routes.alerts import get_alert_service_required
        from src.core.interfaces.services import IAlertService
        from unittest.mock import MagicMock
        
        # Test with None service (should raise HTTPException)
        try:
            get_alert_service_required(None)
            print("❌ Should have raised HTTPException for None service")
            return False
        except Exception as e:
            if "Alert service not available" in str(e):
                print("✅ Properly raises exception when alert service unavailable")
            else:
                print(f"❌ Wrong exception type: {e}")
                return False
        
        # Test with mock service
        mock_service = MagicMock(spec=IAlertService)
        result = get_alert_service_required(mock_service)
        if result == mock_service:
            print("✅ Properly returns alert service when available")
        else:
            print("❌ Failed to return correct service")
            return False
        
        print("✅ Alerts route DI integration working")
        return True
        
    except Exception as e:
        print(f"❌ Alerts route DI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_system_route_di():
    """Test that system route uses DI properly."""
    print("\\nTesting system route DI integration...")
    
    try:
        from src.api.routes.system import get_exchange_manager
        from src.core.exchanges.manager import ExchangeManager
        from fastapi import Request
        from unittest.mock import MagicMock, AsyncMock
        
        # Create mock request with DI container
        mock_request = MagicMock(spec=Request)
        mock_container = AsyncMock()
        mock_exchange_manager = MagicMock(spec=ExchangeManager)
        
        # Mock the get_container function
        mock_request.app.state.container = mock_container
        mock_container.get_service = AsyncMock(return_value=mock_exchange_manager)
        
        # Test DI path
        result = await get_exchange_manager(mock_request)
        if result == mock_exchange_manager:
            print("✅ System route properly uses DI container")
        else:
            print("❌ System route DI path failed")
            return False
        
        print("✅ System route DI integration working")
        return True
        
    except Exception as e:
        print(f"❌ System route DI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_alpha_route_di():
    """Test that alpha route uses DI properly."""
    print("\\nTesting alpha route DI integration...")
    
    try:
        from src.api.routes.alpha import get_alpha_scanner
        from src.analysis.core.alpha_scanner import AlphaScannerEngine
        from fastapi import Request
        from unittest.mock import MagicMock, AsyncMock
        
        # Create mock request with DI container
        mock_request = MagicMock(spec=Request)
        mock_container = AsyncMock()
        mock_alpha_scanner = MagicMock(spec=AlphaScannerEngine)
        
        # Mock the get_container function to return container
        mock_request.app.state.container = mock_container
        mock_container.get_service = AsyncMock(return_value=mock_alpha_scanner)
        
        # Mock get_container function
        import src.api.dependencies
        original_get_container = src.api.dependencies.get_container
        src.api.dependencies.get_container = lambda req: mock_container
        
        try:
            # Test DI path
            result = await get_alpha_scanner(mock_request)
            if result == mock_alpha_scanner:
                print("✅ Alpha route properly uses DI container")
            else:
                print("❌ Alpha route DI path failed")
                return False
        finally:
            # Restore original function
            src.api.dependencies.get_container = original_get_container
        
        print("✅ Alpha route DI integration working")
        return True
        
    except Exception as e:
        print(f"❌ Alpha route DI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dependency_helpers():
    """Test the dependency helper functions."""
    print("\\nTesting dependency helper functions...")
    
    try:
        from src.api.dependencies import (
            get_alert_service, get_metrics_service, get_config_service,
            optional_alert_service, optional_metrics_service, optional_config_service
        )
        from fastapi import Request
        from unittest.mock import MagicMock
        
        # Create mock request with app state
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.container = None
        mock_request.app.state.alert_manager = "mock_alert"
        mock_request.app.state.metrics_manager = "mock_metrics"
        mock_request.app.state.config_manager = "mock_config"
        
        # Test fallback behavior
        alert_service = get_alert_service(mock_request)
        if alert_service == "mock_alert":
            print("✅ Alert service fallback works")
        else:
            print(f"❌ Alert service fallback failed: {alert_service}")
            return False
        
        metrics_service = get_metrics_service(mock_request)
        if metrics_service == "mock_metrics":
            print("✅ Metrics service fallback works")
        else:
            print(f"❌ Metrics service fallback failed: {metrics_service}")
            return False
        
        config_service = get_config_service(mock_request)
        if config_service == "mock_config":
            print("✅ Config service fallback works")
        else:
            print(f"❌ Config service fallback failed: {config_service}")
            return False
        
        print("✅ Dependency helper functions working")
        return True
        
    except Exception as e:
        print(f"❌ Dependency helpers test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_route_imports():
    """Test that routes can be imported without errors."""
    print("\\nTesting route imports...")
    
    try:
        from src.api.routes import alerts, system, alpha, dashboard, signals
        print("✅ All routes import successfully")
        
        # Test that routers are defined
        if hasattr(alerts, 'router'):
            print("✅ Alerts router defined")
        else:
            print("❌ Alerts router missing")
            return False
        
        if hasattr(system, 'router'):
            print("✅ System router defined")
        else:
            print("❌ System router missing")
            return False
        
        if hasattr(alpha, 'router'):
            print("✅ Alpha router defined")
        else:
            print("❌ Alpha router missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Route imports test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all route DI integration tests."""
    print("🧪 Testing FastAPI Routes DI Integration")
    print("=" * 60)
    
    tests = [
        ("Route Imports", test_route_imports),
        ("Alerts Route DI", test_alerts_route_di),
        ("System Route DI", test_system_route_di),
        ("Alpha Route DI", test_alpha_route_di),
        ("Dependency Helpers", test_dependency_helpers)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\\n🔍 Running: {test_name}")
        print("-" * 40)
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\\n" + "=" * 60)
    print("📊 ROUTE DI INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\\n🎉 All route DI integration tests passed!")
        print("✨ FastAPI routes are ready for DI-powered operation!")
    else:
        print(f"\\n⚠️ {failed} tests failed. Please review and fix.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)