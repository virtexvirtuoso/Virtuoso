#!/usr/bin/env python3
"""
Comprehensive test suite to validate all fixes and implementations from:
- docs/implementation/CLASS_REORGANIZATION_PLAN.md
- docs/implementation/GLOBAL_STATE_ELIMINATION_PLAN.md

This test searches for missing, misnamed, or deleted methods and validates
the reorganization against the documented plans.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import importlib
import inspect

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

class ReorganizationValidator:
    """Validates implementation against reorganization plans."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.errors = []
        self.warnings = []
        self.successes = []
    
    def log_success(self, message: str):
        """Log a successful validation."""
        self.successes.append(message)
        print(f"✅ {message}")
    
    def log_warning(self, message: str):
        """Log a warning."""
        self.warnings.append(message)
        print(f"⚠️  {message}")
    
    def log_error(self, message: str):
        """Log an error."""
        self.errors.append(message)
        print(f"❌ {message}")
    
    async def validate_all(self) -> bool:
        """Run all validation tests."""
        print("🧪 COMPREHENSIVE REORGANIZATION VALIDATION")
        print("=" * 60)
        
        tests = [
            ("Class Reorganization - Validation System", self.test_validation_system_consolidation),
            ("Class Reorganization - Analysis Package", self.test_analysis_package_consolidation),
            ("Class Reorganization - Error Handling", self.test_error_handling_consolidation),
            ("Global State Elimination - DI Container", self.test_dependency_injection_implementation),
            ("Global State Elimination - Global Variables", self.test_global_variables_eliminated),
            ("Global State Elimination - API Integration", self.test_api_dependency_injection),
            ("Missing Methods Detection", self.test_missing_methods),
            ("Import Path Validation", self.test_import_paths),
            ("Interface Implementation", self.test_interface_compliance),
            ("Service Registration", self.test_service_registration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing: {test_name}")
            print("-" * 50)
            try:
                await test_func()
            except Exception as e:
                self.log_error(f"{test_name} crashed: {e}")
                import traceback
                traceback.print_exc()
        
        return self.print_summary()
    
    async def test_validation_system_consolidation(self):
        """Test Phase 1: Validation System Consolidation from CLASS_REORGANIZATION_PLAN."""
        
        # Test new validation package structure exists
        validation_dir = Path("src/validation")
        if not validation_dir.exists():
            self.log_error("src/validation/ directory not found - consolidation incomplete")
            return
        
        expected_structure = [
            "core/",
            "rules/", 
            "validators/",
            "services/",
            "cache/"
        ]
        
        missing_dirs = []
        for subdir in expected_structure:
            if not (validation_dir / subdir).exists():
                missing_dirs.append(subdir)
        
        if missing_dirs:
            self.log_error(f"Missing validation subdirectories: {missing_dirs}")
        else:
            self.log_success("Validation package structure matches reorganization plan")
        
        # Test core classes exist
        try:
            from src.validation.core.validator import CoreValidator
            from src.validation.core.exceptions import ValidationError
            self.log_success("Core validation classes accessible")
        except ImportError as e:
            self.log_error(f"Core validation classes missing: {e}")
        
        # Test services exist
        try:
            from src.validation.services.sync_service import ValidationService
            from src.validation.services.async_service import AsyncValidationService
            self.log_success("Validation services accessible")
        except ImportError as e:
            self.log_error(f"Validation services missing: {e}")
        
        # Check for old duplicate structure
        old_validation_dir = Path("src/core/validation")
        if old_validation_dir.exists():
            self.log_warning("Old src/core/validation/ directory still exists - incomplete migration")
        else:
            self.log_success("Old validation directory properly removed")
    
    async def test_analysis_package_consolidation(self):
        """Test Phase 2: Analysis Package Consolidation from CLASS_REORGANIZATION_PLAN."""
        
        # Test old core/analysis directory removed
        old_analysis_dir = Path("src/core/analysis")
        if old_analysis_dir.exists():
            self.log_error("src/core/analysis/ directory still exists - migration incomplete")
        else:
            self.log_success("Old core/analysis directory properly removed")
        
        # Test new analysis structure
        analysis_dir = Path("src/analysis")
        if not analysis_dir.exists():
            self.log_error("src/analysis/ directory not found")
            return
        
        expected_subdirs = ["core/", "market/", "data/"]
        for subdir in expected_subdirs:
            if (analysis_dir / subdir).exists():
                self.log_success(f"Analysis {subdir} directory exists")
            else:
                self.log_warning(f"Analysis {subdir} directory missing")
        
        # Test key classes moved correctly
        try:
            from src.analysis.core.alpha_scanner import AlphaScannerEngine
            from src.analysis.core.confluence import ConfluenceAnalyzer
            from src.analysis.core.liquidation_detector import LiquidationDetectionEngine
            self.log_success("Key analysis classes accessible in new location")
        except ImportError as e:
            self.log_error(f"Analysis classes missing after migration: {e}")
    
    async def test_error_handling_consolidation(self):
        """Test Phase 3: Error Handling Consolidation from CLASS_REORGANIZATION_PLAN."""
        
        # Test centralized error package
        error_dir = Path("src/core/error")
        if error_dir.exists():
            self.log_success("Centralized error handling package exists")
            
            # Test key error classes
            try:
                from src.core.error.handlers import BaseErrorHandler
                self.log_success("Error handler classes accessible")
            except ImportError as e:
                self.log_warning(f"Some error classes may be missing: {e}")
        else:
            self.log_warning("Centralized error handling directory not found")
    
    async def test_dependency_injection_implementation(self):
        """Test DI Container implementation from GLOBAL_STATE_ELIMINATION_PLAN."""
        
        # Test ServiceContainer exists (actual implementation, not AppContext from plan)
        try:
            from src.core.di.container import ServiceContainer
            from src.core.di.registration import bootstrap_container
            self.log_success("Dependency Injection container implemented")
            
            # Test container can be created
            container = ServiceContainer()
            if hasattr(container, 'get_service') and hasattr(container, 'register_singleton'):
                self.log_success("ServiceContainer has required methods")
            else:
                self.log_error("ServiceContainer missing required methods")
                
        except ImportError as e:
            self.log_error(f"Dependency Injection container not found: {e}")
        
        # Test service interfaces exist
        try:
            from src.core.interfaces.services import (
                IAlertService, IMetricsService, IConfigService,
                IValidationService, IFormattingService
            )
            self.log_success("Service interfaces implemented")
        except ImportError as e:
            self.log_error(f"Service interfaces missing: {e}")
    
    async def test_global_variables_eliminated(self):
        """Test that global variables from GLOBAL_STATE_ELIMINATION_PLAN are eliminated."""
        
        try:
            import src.main as main_module
            
            # List of problematic globals mentioned in the plan
            problematic_globals = [
                'config_manager', 'exchange_manager', 'portfolio_analyzer',
                'database_client', 'confluence_analyzer', 'top_symbols_manager',
                'market_monitor', 'metrics_manager', 'alert_manager', 
                'market_reporter', 'health_monitor', 'validation_service',
                'market_data_manager'
            ]
            
            found_globals = []
            for global_name in problematic_globals:
                if hasattr(main_module, global_name):
                    global_value = getattr(main_module, global_name)
                    # Check if it's the old problematic pattern (not None, not app_container)
                    if global_value is not None and global_name != 'app_container':
                        found_globals.append(global_name)
            
            if found_globals:
                self.log_error(f"Problematic global variables still exist: {found_globals}")
            else:
                self.log_success("All problematic global variables eliminated")
            
            # Check that app_container is the only global
            if hasattr(main_module, 'app_container'):
                self.log_success("app_container global variable exists as expected")
            else:
                self.log_warning("app_container global variable not found")
                
        except Exception as e:
            self.log_error(f"Could not validate global variables: {e}")
    
    async def test_api_dependency_injection(self):
        """Test API routes use dependency injection instead of global state."""
        
        # Test dependency helpers exist
        try:
            from src.api.dependencies import (
                get_alert_service, get_metrics_service, get_config_service,
                AlertServiceDep, MetricsServiceDep, ConfigServiceDep
            )
            self.log_success("API dependency injection helpers exist")
        except ImportError as e:
            self.log_error(f"API dependency helpers missing: {e}")
        
        # Test key routes use dependency injection
        route_files = [
            "src/api/routes/alerts.py",
            "src/api/routes/system.py", 
            "src/api/routes/alpha.py"
        ]
        
        for route_file in route_files:
            if Path(route_file).exists():
                try:
                    with open(route_file, 'r') as f:
                        content = f.read()
                    
                    # Look for dependency injection patterns
                    if "Depends(" in content and "IAlertService" in content:
                        self.log_success(f"{route_file} uses dependency injection")
                    elif "request.app.state" in content:
                        self.log_warning(f"{route_file} still uses app.state pattern")
                    else:
                        self.log_warning(f"{route_file} dependency injection pattern unclear")
                        
                except Exception as e:
                    self.log_error(f"Could not analyze {route_file}: {e}")
    
    async def test_missing_methods(self):
        """Search for missing, misnamed, or deleted methods."""
        
        # Test key service classes have expected methods
        service_tests = [
            ("IAlertService", ["send_alert", "get_alerts"]),
            ("IMetricsService", ["collect_metrics", "get_metrics"]),
            ("IValidationService", ["validate"]),
            ("ServiceContainer", ["get_service", "register_singleton", "register_transient"])
        ]
        
        for service_name, expected_methods in service_tests:
            try:
                if service_name == "ServiceContainer":
                    from src.core.di.container import ServiceContainer
                    service_class = ServiceContainer
                elif service_name.startswith("I"):
                    from src.core.interfaces.services import IAlertService, IMetricsService, IValidationService
                    service_class = locals()[service_name]
                else:
                    continue
                
                missing_methods = []
                for method_name in expected_methods:
                    if not hasattr(service_class, method_name):
                        missing_methods.append(method_name)
                
                if missing_methods:
                    self.log_error(f"{service_name} missing methods: {missing_methods}")
                else:
                    self.log_success(f"{service_name} has all expected methods")
                    
            except Exception as e:
                self.log_error(f"Could not test {service_name}: {e}")
    
    async def test_import_paths(self):
        """Test that import paths match the reorganization."""
        
        # Test key imports work
        import_tests = [
            ("src.validation.core.validator", "CoreValidator"),
            ("src.analysis.core.alpha_scanner", "AlphaScannerEngine"),
            ("src.analysis.core.confluence", "ConfluenceAnalyzer"),
            ("src.core.di.container", "ServiceContainer"),
            ("src.core.interfaces.services", "IAlertService")
        ]
        
        for module_path, class_name in import_tests:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    self.log_success(f"Import {module_path}.{class_name} works")
                else:
                    self.log_error(f"Class {class_name} not found in {module_path}")
            except ImportError as e:
                self.log_error(f"Cannot import {module_path}: {e}")
    
    async def test_interface_compliance(self):
        """Test that implementations comply with their interfaces."""
        
        try:
            from src.core.interfaces.services import IAlertService, IMetricsService
            from src.monitoring.alert_manager import AlertManager
            from src.monitoring.metrics_manager import MetricsManager
            
            # Test AlertManager implements IAlertService methods
            alert_methods = [method for method in dir(IAlertService) if not method.startswith('_')]
            alert_manager = AlertManager({})
            
            missing_alert_methods = []
            for method in alert_methods:
                if not hasattr(alert_manager, method):
                    missing_alert_methods.append(method)
            
            if missing_alert_methods:
                self.log_warning(f"AlertManager missing interface methods: {missing_alert_methods}")
            else:
                self.log_success("AlertManager implements IAlertService interface")
            
        except Exception as e:
            self.log_error(f"Could not test interface compliance: {e}")
    
    async def test_service_registration(self):
        """Test that services are properly registered in the DI container."""
        
        try:
            from src.core.di.registration import bootstrap_container
            
            # Test bootstrap creates container with services
            container = bootstrap_container()
            
            if container:
                stats = container.get_stats()
                service_count = stats.get('services_registered_count', 0)
                
                if service_count > 20:  # Expect significant number of services
                    self.log_success(f"Service registration working - {service_count} services registered")
                else:
                    self.log_warning(f"Low service count - only {service_count} services registered")
            else:
                self.log_error("Bootstrap container returned None")
                
        except Exception as e:
            self.log_error(f"Could not test service registration: {e}")
    
    def print_summary(self) -> bool:
        """Print validation summary and return success status."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE VALIDATION RESULTS")
        print("=" * 60)
        
        print(f"\n✅ Successes: {len(self.successes)}")
        for success in self.successes:
            print(f"  ✅ {success}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        
        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"  ❌ {error}")
        
        success_rate = len(self.successes) / (len(self.successes) + len(self.errors)) * 100 if (len(self.successes) + len(self.errors)) > 0 else 0
        
        print(f"\n📈 Overall Results:")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Total Issues: {len(self.errors) + len(self.warnings)}")
        
        if len(self.errors) == 0:
            print("\n🎉 All critical validations passed!")
            print("✨ Reorganization implementation is working correctly!")
            return True
        else:
            print(f"\n⚠️  {len(self.errors)} critical issues found")
            print("🔧 Please review and fix the errors above")
            return False

async def main():
    """Run comprehensive reorganization validation."""
    validator = ReorganizationValidator()
    success = await validator.validate_all()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)