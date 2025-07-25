#!/usr/bin/env python3
"""
Test script for the dependency injection system.

This script verifies that:
1. The DI container can register and resolve services
2. Service interfaces are properly implemented
3. Service lifetime management works correctly
4. Dependencies are injected correctly
5. The bootstrap function creates a fully functional container
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

def setup_logging():
    """Setup logging for test output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

async def test_basic_container_functionality():
    """Test basic container registration and resolution."""
    print("\n=== Testing Basic Container Functionality ===")
    
    try:
        from src.core.di import ServiceContainer, ServiceLifetime
        
        container = ServiceContainer()
        
        # Test singleton registration
        class TestService:
            def __init__(self):
                self.value = 42
        
        container.register_singleton(TestService, TestService)
        
        # Test service resolution
        service1 = await container.get_service(TestService)
        service2 = await container.get_service(TestService)
        
        assert service1 is service2, "Singleton services should be the same instance"
        assert service1.value == 42, "Service should have expected value"
        
        print("✓ Basic container registration and resolution works")
        print("✓ Singleton lifetime management works")
        
        # Test transient registration
        class TransientService:
            def __init__(self):
                self.id = id(self)
        
        container.register_transient(TransientService, TransientService)
        
        transient1 = await container.get_service(TransientService)
        transient2 = await container.get_service(TransientService)
        
        assert transient1 is not transient2, "Transient services should be different instances"
        print("✓ Transient lifetime management works")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic container functionality failed: {e}")
        return False

async def test_service_interfaces():
    """Test that service interfaces are properly implemented."""
    print("\n=== Testing Service Interfaces ===")
    
    try:
        from src.core.interfaces.services import IAlertService, IMetricsService, IInterpretationService
        from src.monitoring.alert_manager import AlertManager
        from src.monitoring.metrics_manager import MetricsManager
        from src.analysis.core.interpretation_generator import InterpretationGenerator
        
        # Test AlertManager implements IAlertService
        alert_config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': 'test_url'
                }
            }
        }
        alert_manager = AlertManager(alert_config)
        assert isinstance(alert_manager, IAlertService), "AlertManager should implement IAlertService"
        assert hasattr(alert_manager, 'send_alert'), "AlertManager should have send_alert method"
        print("✓ AlertManager implements IAlertService interface")
        
        # Test MetricsManager implements IMetricsService
        metrics_manager = MetricsManager(alert_config, alert_manager)
        assert isinstance(metrics_manager, IMetricsService), "MetricsManager should implement IMetricsService"
        assert hasattr(metrics_manager, 'update_metric'), "MetricsManager should have update_metric method"
        print("✓ MetricsManager implements IMetricsService interface")
        
        # Test InterpretationGenerator implements IInterpretationService
        interpreter = InterpretationGenerator()
        assert isinstance(interpreter, IInterpretationService), "InterpretationGenerator should implement IInterpretationService"
        assert hasattr(interpreter, 'generate_interpretation'), "InterpretationGenerator should have generate_interpretation method"
        print("✓ InterpretationGenerator implements IInterpretationService interface")
        
        return True
        
    except Exception as e:
        print(f"✗ Service interface testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dependency_injection():
    """Test dependency injection with constructor injection."""
    print("\n=== Testing Dependency Injection ===")
    
    try:
        from src.core.di import ServiceContainer
        from src.utils.formatters import DataFormatter
        from src.utils.config import ConfigManager
        from src.analysis.core.interpretation_generator import InterpretationGenerator
        from src.core.interfaces.services import IFormattingService, IConfigService, IInterpretationService
        
        container = ServiceContainer()
        
        # Register dependencies
        container.register_singleton(IConfigService, ConfigManager)
        container.register_transient(IFormattingService, DataFormatter)
        container.register_scoped(IInterpretationService, InterpretationGenerator)
        
        # Test resolution with dependencies
        interpreter = await container.get_service(IInterpretationService)
        assert interpreter is not None, "Should be able to resolve InterpretationGenerator"
        print("✓ Service resolution with dependencies works")
        
        # Test that same scoped instance is returned within scope
        interpreter2 = await container.get_service(IInterpretationService)
        assert interpreter is interpreter2, "Scoped services should return same instance in default scope"
        print("✓ Scoped service lifetime works")
        
        return True
        
    except Exception as e:
        print(f"✗ Dependency injection testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_service_registration_functions():
    """Test the service registration functions."""
    print("\n=== Testing Service Registration Functions ===")
    
    try:
        from src.core.di import bootstrap_container, register_core_services
        from src.core.di import ServiceContainer
        
        # Test individual registration function
        container = ServiceContainer()
        config_data = {
            'monitoring': {
                'alerts': {'discord_webhook_url': 'test'},
                'metrics': {'collection_interval': 60}
            }
        }
        
        register_core_services(container, config_data)
        
        # Check that services were registered
        stats = container.get_stats()
        assert stats['services_registered_count'] > 0, "Should have registered some services"
        print(f"✓ Core services registration: {stats['services_registered_count']} services registered")
        
        # Test bootstrap function
        full_container = bootstrap_container(config_data)
        full_stats = full_container.get_stats()
        assert full_stats['services_registered_count'] > stats['services_registered_count'], "Bootstrap should register more services"
        print(f"✓ Bootstrap container: {full_stats['services_registered_count']} services registered")
        
        return True
        
    except Exception as e:
        print(f"✗ Service registration functions testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_service_health_checks():
    """Test service health checking functionality."""
    print("\n=== Testing Service Health Checks ===")
    
    try:
        from src.core.di import ServiceContainer
        
        container = ServiceContainer()
        
        # Register a service with health check
        class HealthyService:
            def is_healthy(self):
                return True
        
        container.register_singleton(HealthyService, HealthyService)
        container.register_health_check(HealthyService, lambda: True)
        
        # Test health check
        health_status = await container.check_health()
        assert 'HealthyService' in health_status, "Health check should include registered service"
        assert health_status['HealthyService'] is True, "Health check should return True"
        
        print("✓ Service health checks work")
        return True
        
    except Exception as e:
        print(f"✗ Service health checks testing failed: {e}")
        return False

async def test_container_scoping():
    """Test service scoping functionality."""
    print("\n=== Testing Container Scoping ===")
    
    try:
        from src.core.di import ServiceContainer
        
        container = ServiceContainer()
        
        class ScopedService:
            def __init__(self):
                self.id = id(self)
        
        container.register_scoped(ScopedService, ScopedService)
        
        # Test different scopes
        async with container.scope("scope1") as scope1:
            service1a = await scope1.get_service(ScopedService)
            service1b = await scope1.get_service(ScopedService)
            assert service1a is service1b, "Same scope should return same instance"
        
        async with container.scope("scope2") as scope2:
            service2 = await scope2.get_service(ScopedService)
            assert service1a.id != service2.id, "Different scopes should have different instances"
        
        print("✓ Service scoping works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Container scoping testing failed: {e}")
        return False

async def test_interface_methods():
    """Test that interface methods work correctly."""
    print("\n=== Testing Interface Methods ===")
    
    try:
        # Test AlertManager interface methods
        from src.monitoring.alert_manager import AlertManager
        
        alert_config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': 'test_url'
                }
            }
        }
        alert_manager = AlertManager(alert_config)
        
        # Test interface method (should not raise exception)
        await alert_manager.send_alert("Test message", "info", "test_context", {"test": "metadata"})
        print("✓ AlertManager interface method works")
        
        # Test MetricsManager interface methods
        from src.monitoring.metrics_manager import MetricsManager
        
        metrics_manager = MetricsManager(alert_config, alert_manager)
        
        # Test interface methods
        metrics_manager.update_metric_sync("test.metric", 42.0, {"tag": "value"})
        value = metrics_manager.get_metric("test.metric")
        assert value == 42.0, "Should retrieve the metric value"
        
        # Use sync version for simple counter test
        metrics_manager.update_metric_sync("test.counter", 5.0)
        counter_value = metrics_manager.get_metric("test.counter")
        assert counter_value == 5.0, "Counter should have expected value"
        
        # Test histogram sync
        metrics_manager.update_metric_sync("test.histogram", 100.0)
        
        snapshot = metrics_manager.get_metrics_snapshot("test")
        assert len(snapshot) > 0, "Should have metrics in snapshot"
        
        print("✓ MetricsManager interface methods work")
        
        # Test InterpretationGenerator interface methods
        from src.analysis.core.interpretation_generator import InterpretationGenerator
        
        interpreter = InterpretationGenerator()
        
        test_data = {"score": 75, "components": {"rsi": 70}}
        interpretation = interpreter.generate_interpretation("technical", test_data)
        assert isinstance(interpretation, str), "Should return string interpretation"
        assert len(interpretation) > 0, "Interpretation should not be empty"
        
        cross_components = {"technical": test_data, "volume": {"score": 60}}
        cross_insights = interpreter.generate_cross_component_interpretation(cross_components)
        assert isinstance(cross_insights, list), "Should return list of insights"
        
        actionable = interpreter.generate_actionable_summary(cross_components, 70.0)
        assert isinstance(actionable, list), "Should return list of actionable insights"
        
        print("✓ InterpretationGenerator interface methods work")
        
        return True
        
    except Exception as e:
        print(f"✗ Interface methods testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all dependency injection tests."""
    print("🧪 Starting Dependency Injection System Tests")
    setup_logging()
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Basic Container Functionality", test_basic_container_functionality),
        ("Service Interfaces", test_service_interfaces),
        ("Dependency Injection", test_dependency_injection),
        ("Service Registration Functions", test_service_registration_functions),
        ("Service Health Checks", test_service_health_checks),
        ("Container Scoping", test_container_scoping),
        ("Interface Methods", test_interface_methods),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} tests...")
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            test_results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 DEPENDENCY INJECTION SYSTEM TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:<12} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All dependency injection tests passed!")
        print("\n✨ The dependency injection system is ready for production use!")
        print("\nNext steps:")
        print("1. Update core components to use dependency injection")
        print("2. Integrate DI container into main application startup")
        print("3. Add more comprehensive integration tests")
    else:
        print("⚠️  Some tests failed. Please review and fix issues before proceeding.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)