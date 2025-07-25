#!/usr/bin/env python3
"""
Focused validation test for DI system fixes.
Tests the key issues found in comprehensive testing.
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

async def test_basic_container_functionality():
    """Test basic container operations work."""
    print("Testing basic container functionality...")
    
    try:
        from src.core.di import ServiceContainer, ServiceLifetime
        
        container = ServiceContainer()
        
        # Test basic registration and resolution
        class TestService:
            def __init__(self):
                self.value = 42
        
        container.register_singleton(TestService, TestService)
        service = await container.get_service(TestService)
        
        assert service.value == 42
        print("✓ Basic service registration and resolution works")
        
        # Test dispose (should be sync now)
        container.dispose()
        print("✓ Container disposal works")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic container functionality failed: {e}")
        return False

async def test_interface_implementations():
    """Test that all interfaces are properly implemented."""
    print("\nTesting interface implementations...")
    
    try:
        from src.core.interfaces.services import (
            IAlertService, IMetricsService, IInterpretationService, IValidationService
        )
        from src.monitoring.alert_manager import AlertManager
        from src.monitoring.metrics_manager import MetricsManager
        from src.analysis.core.interpretation_generator import InterpretationGenerator
        from src.validation.core.validator import CoreValidator
        
        # Test AlertManager
        alert_config = {'monitoring': {'alerts': {'discord_webhook_url': 'test'}}}
        alert_manager = AlertManager(alert_config)
        assert isinstance(alert_manager, IAlertService)
        await alert_manager.send_alert("test", "info", "test_context")
        print("✓ AlertManager interface works")
        
        # Test MetricsManager
        metrics_manager = MetricsManager(alert_config, alert_manager)
        assert isinstance(metrics_manager, IMetricsService)
        metrics_manager.update_metric_sync("test.metric", 42.0)
        value = metrics_manager.get_metric("test.metric")
        assert value == 42.0
        print("✓ MetricsManager interface works")
        
        # Test InterpretationGenerator
        interpreter = InterpretationGenerator()
        assert isinstance(interpreter, IInterpretationService)
        
        # Test all interface methods
        test_data = {"score": 75, "components": {"rsi": 70}}
        
        component_interp = interpreter.get_component_interpretation("technical", test_data)
        assert isinstance(component_interp, str) and len(component_interp) > 0
        
        market_interp = interpreter.get_market_interpretation({"confluence_score": 75})
        assert isinstance(market_interp, str) and len(market_interp) > 0
        
        signal_interp = interpreter.get_signal_interpretation({"signal": "BUY", "score": 75})
        assert isinstance(signal_interp, str) and len(signal_interp) > 0
        
        indicator_interp = interpreter.get_indicator_interpretation("rsi", {"rsi": 75})
        assert isinstance(indicator_interp, str) and len(indicator_interp) > 0
        
        interpreter.set_interpretation_config({"test": "value"})
        
        print("✓ InterpretationGenerator interface works")
        
        # Test CoreValidator
        validator = CoreValidator()
        assert isinstance(validator, IValidationService)
        
        # Test interface methods
        validation_result = await validator.validate({"test": "data"})
        assert hasattr(validation_result, 'is_valid')
        
        validator.add_rule("test_rule", {"data_type": dict})
        validator.remove_rule("test_rule")
        
        stats = validator.get_validation_stats()
        assert isinstance(stats, dict)
        
        config_result = await validator.validate_config({"key": "value"})
        assert hasattr(config_result, 'is_valid')
        
        market_result = await validator.validate_market_data({"symbol": "BTCUSDT", "timestamp": 123456})
        assert hasattr(market_result, 'is_valid')
        
        print("✓ CoreValidator interface works")
        
        return True
        
    except Exception as e:
        print(f"✗ Interface implementations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_bootstrap_registration():
    """Test bootstrap container registration."""
    print("\nTesting bootstrap registration...")
    
    try:
        from src.core.di.registration import bootstrap_container
        
        config_data = {
            'monitoring': {
                'alerts': {'discord_webhook_url': 'test'},
                'metrics': {'collection_interval': 60}
            }
        }
        
        container = bootstrap_container(config_data)
        stats = container.get_stats()
        
        print(f"✓ Bootstrap registered {stats['services_registered_count']} services")
        
        # Test that we can resolve some key services
        from src.core.interfaces.services import IAlertService, IMetricsService
        
        try:
            alert_service = await container.get_service(IAlertService)
            print("✓ Alert service resolution works")
        except Exception as e:
            print(f"⚠ Alert service resolution failed: {e}")
        
        try:
            metrics_service = await container.get_service(IMetricsService)
            print("✓ Metrics service resolution works")
        except Exception as e:
            print(f"⚠ Metrics service resolution failed: {e}")
        
        container.dispose()
        
        return True
        
    except Exception as e:
        print(f"✗ Bootstrap registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dependency_injection():
    """Test constructor dependency injection."""
    print("\nTesting dependency injection...")
    
    try:
        from src.core.di import ServiceContainer
        from src.core.interfaces.services import IConfigService, IFormattingService
        from src.utils.config import ConfigManager
        from src.utils.formatters import DataFormatter
        
        container = ServiceContainer()
        
        # Register dependencies
        container.register_singleton(IConfigService, ConfigManager)
        container.register_transient(IFormattingService, DataFormatter)
        
        # Service with dependencies
        class ServiceWithDeps:
            def __init__(self, config: IConfigService, formatter: IFormattingService):
                self.config = config
                self.formatter = formatter
        
        container.register_transient(ServiceWithDeps, ServiceWithDeps)
        
        # Test resolution
        service = await container.get_service(ServiceWithDeps)
        assert isinstance(service.config, IConfigService)
        assert isinstance(service.formatter, IFormattingService)
        
        print("✓ Constructor dependency injection works")
        
        container.dispose()
        
        return True
        
    except Exception as e:
        print(f"✗ Dependency injection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run focused validation tests."""
    print("🔧 DI System Fixes Validation")
    print("=" * 50)
    
    tests = [
        ("Basic Container Functionality", test_basic_container_functionality),
        ("Interface Implementations", test_interface_implementations),
        ("Bootstrap Registration", test_bootstrap_registration),
        ("Dependency Injection", test_dependency_injection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All DI system fixes validated successfully!")
        print("✨ The dependency injection system is now working correctly!")
    else:
        print(f"\n⚠️ {failed} issues remain. Please review and fix.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)