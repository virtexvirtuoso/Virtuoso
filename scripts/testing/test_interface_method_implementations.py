#!/usr/bin/env python3
"""
Test that service implementations have all the methods defined in their interfaces.
This ensures interface compliance after adding missing methods.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
import importlib
import inspect

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

async def test_alert_service_interface():
    """Test AlertManager implements all IAlertService methods."""
    print("🔍 Testing AlertManager interface compliance...")
    
    try:
        from src.core.interfaces.services import IAlertService
        from src.monitoring.alert_manager import AlertManager
        
        # Get interface methods
        interface_methods = [method for method in dir(IAlertService) if not method.startswith('_')]
        
        # Create AlertManager instance
        alert_manager = AlertManager({
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': 'test_webhook'
                }
            }
        })
        
        missing_methods = []
        for method_name in interface_methods:
            if not hasattr(alert_manager, method_name):
                missing_methods.append(method_name)
            else:
                # Check if method is callable
                method = getattr(alert_manager, method_name)
                if not callable(method):
                    missing_methods.append(f"{method_name} (not callable)")
        
        if missing_methods:
            print(f"❌ AlertManager missing methods: {missing_methods}")
            return False
        else:
            print("✅ AlertManager implements all IAlertService methods")
            
            # Test specific new methods
            if hasattr(alert_manager, 'get_alerts') and callable(alert_manager.get_alerts):
                print("✅ get_alerts method exists and is callable")
            if hasattr(alert_manager, 'get_alert_stats') and callable(alert_manager.get_alert_stats):
                print("✅ get_alert_stats method exists and is callable")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing AlertManager interface: {e}")
        return False

async def test_metrics_service_interface():
    """Test MetricsManager implements all IMetricsService methods."""
    print("\n🔍 Testing MetricsManager interface compliance...")
    
    try:
        from src.core.interfaces.services import IMetricsService
        from src.monitoring.metrics_manager import MetricsManager
        from src.monitoring.alert_manager import AlertManager
        
        # Get interface methods
        interface_methods = [method for method in dir(IMetricsService) if not method.startswith('_')]
        
        # Create dependencies
        alert_manager = AlertManager({})
        
        # Create MetricsManager instance
        metrics_manager = MetricsManager({
            'monitoring': {
                'metrics': {
                    'collection_interval': 30
                }
            }
        }, alert_manager)
        
        missing_methods = []
        for method_name in interface_methods:
            if not hasattr(metrics_manager, method_name):
                missing_methods.append(method_name)
            else:
                # Check if method is callable
                method = getattr(metrics_manager, method_name)
                if not callable(method):
                    missing_methods.append(f"{method_name} (not callable)")
        
        if missing_methods:
            print(f"❌ MetricsManager missing methods: {missing_methods}")
            return False
        else:
            print("✅ MetricsManager implements all IMetricsService methods")
            
            # Test specific new methods
            if hasattr(metrics_manager, 'collect_metrics') and callable(metrics_manager.collect_metrics):
                print("✅ collect_metrics method exists and is callable")
            if hasattr(metrics_manager, 'get_metrics') and callable(metrics_manager.get_metrics):
                print("✅ get_metrics method exists and is callable")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing MetricsManager interface: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_validation_service_interface():
    """Test CoreValidator implements all IValidationService methods."""
    print("\n🔍 Testing CoreValidator interface compliance...")
    
    try:
        from src.core.interfaces.services import IValidationService
        from src.validation.core.validator import CoreValidator
        
        # Get interface methods
        interface_methods = [method for method in dir(IValidationService) if not method.startswith('_')]
        
        # Create CoreValidator instance
        core_validator = CoreValidator()
        
        missing_methods = []
        for method_name in interface_methods:
            if not hasattr(core_validator, method_name):
                missing_methods.append(method_name)
            else:
                # Check if method is callable
                method = getattr(core_validator, method_name)
                if not callable(method):
                    missing_methods.append(f"{method_name} (not callable)")
        
        if missing_methods:
            print(f"❌ CoreValidator missing methods: {missing_methods}")
            return False
        else:
            print("✅ CoreValidator implements all IValidationService methods")
            return True
            
    except Exception as e:
        print(f"❌ Error testing CoreValidator interface: {e}")
        return False

async def test_di_container_integration():
    """Test that services can be retrieved from DI container with new methods."""
    print("\n🔍 Testing DI container service retrieval...")
    
    try:
        from src.core.di.registration import bootstrap_container
        from src.core.interfaces.services import IAlertService, IMetricsService, IValidationService
        
        # Bootstrap container
        container = bootstrap_container()
        
        # Test alert service
        alert_service = await container.get_service(IAlertService)
        if alert_service and hasattr(alert_service, 'get_alerts'):
            print("✅ Alert service retrieved from DI container with new methods")
        else:
            print("❌ Alert service missing from DI container or missing methods")
            return False
        
        # Test metrics service
        metrics_service = await container.get_service(IMetricsService)
        if metrics_service and hasattr(metrics_service, 'collect_metrics'):
            print("✅ Metrics service retrieved from DI container with new methods")
        else:
            print("❌ Metrics service missing from DI container or missing methods")
            return False
        
        # Test validation service
        validation_service = await container.get_service(IValidationService)
        if validation_service and hasattr(validation_service, 'validate'):
            print("✅ Validation service retrieved from DI container")
        else:
            print("❌ Validation service missing from DI container")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing DI container integration: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run interface compliance tests."""
    print("🧪 TESTING INTERFACE METHOD IMPLEMENTATIONS")
    print("=" * 60)
    
    tests = [
        ("AlertManager Interface", test_alert_service_interface),
        ("MetricsManager Interface", test_metrics_service_interface),
        ("CoreValidator Interface", test_validation_service_interface),
        ("DI Container Integration", test_di_container_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 INTERFACE COMPLIANCE TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All interface compliance tests passed!")
        print("✨ Service implementations are fully compliant with interfaces!")
    else:
        print(f"\n⚠️ {failed} tests failed. Interface compliance issues detected.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)