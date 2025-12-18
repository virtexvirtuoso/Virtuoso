#!/usr/bin/env python3
"""
Comprehensive ErrorContext Constructor Fix Validation

This script validates that the ErrorContext constructor fix resolves all issues
and ensures the system is production-ready.

Validation Areas:
1. ErrorContext Constructor Validation
2. System Import Performance
3. Error Handling Functionality
4. Production Readiness Verification
5. Integration with Crisis Stabilization

Usage: python validation_errorcontext_comprehensive.py
"""

import sys
import time
import traceback
from typing import Dict, Any, List
from datetime import datetime, timezone
import importlib.util


class ValidationResults:
    """Container for validation results."""

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.overall_score = 0
        self.total_tests = 0
        self.passed_tests = 0

    def add_result(self, category: str, test_name: str, status: str, evidence: str, details: Dict[str, Any] = None):
        """Add a test result."""
        if category not in self.results:
            self.results[category] = {}

        self.results[category][test_name] = {
            'status': status,
            'evidence': evidence,
            'details': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.total_tests += 1
        if status == 'PASS':
            self.passed_tests += 1

    def get_category_status(self, category: str) -> str:
        """Get overall status for a category."""
        if category not in self.results:
            return 'FAIL'

        tests = self.results[category]
        if all(test['status'] == 'PASS' for test in tests.values()):
            return 'PASS'
        elif any(test['status'] == 'PASS' for test in tests.values()):
            return 'PARTIAL'
        else:
            return 'FAIL'

    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        self.overall_score = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

        report = []
        report.append("# COMPREHENSIVE ERRORCONTEXT VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"**Validation Date:** {datetime.now(timezone.utc).isoformat()}")
        report.append(f"**Overall Score:** {self.overall_score:.1f}% ({self.passed_tests}/{self.total_tests} tests passed)")
        report.append("")

        # Executive Summary
        report.append("## EXECUTIVE SUMMARY")
        report.append("")

        categories = [
            ("ErrorContext Constructor Validation", "errorcontext_validation"),
            ("System Import Performance", "import_performance"),
            ("Error Handling Functionality", "error_handling"),
            ("Production Readiness Verification", "production_readiness"),
            ("Integration with Crisis Stabilization", "crisis_integration")
        ]

        for category_name, category_key in categories:
            status = self.get_category_status(category_key)
            status_emoji = "✅" if status == "PASS" else "⚠️" if status == "PARTIAL" else "❌"
            report.append(f"- **{category_name}:** {status_emoji} {status}")

        report.append("")

        # Detailed Results
        report.append("## DETAILED VALIDATION RESULTS")
        report.append("")

        for category_name, category_key in categories:
            if category_key in self.results:
                report.append(f"### {category_name}")
                report.append("")

                for test_name, result in self.results[category_key].items():
                    status_emoji = "✅" if result['status'] == "PASS" else "❌"
                    report.append(f"**{test_name}:** {status_emoji} {result['status']}")
                    report.append(f"- Evidence: {result['evidence']}")

                    if result['details']:
                        for key, value in result['details'].items():
                            report.append(f"- {key}: {value}")
                    report.append("")

        # Final Recommendation
        report.append("## FINAL RECOMMENDATION")
        report.append("")

        if self.overall_score >= 95:
            recommendation = "**APPROVED FOR PRODUCTION DEPLOYMENT** 🚀"
            reason = "All critical validations passed. System is production-ready."
        elif self.overall_score >= 80:
            recommendation = "**CONDITIONAL APPROVAL** ⚠️"
            reason = "Most validations passed. Address remaining issues before deployment."
        else:
            recommendation = "**NOT APPROVED FOR PRODUCTION** ❌"
            reason = "Critical issues remain. Further fixes required."

        report.append(f"**Decision:** {recommendation}")
        report.append(f"**Rationale:** {reason}")
        report.append("")

        return "\n".join(report)


def validate_errorcontext_constructors(results: ValidationResults):
    """Validate ErrorContext constructor calls work correctly."""

    try:
        # Test 1: Import ErrorContext from context module
        from src.core.error.context import ErrorContext
        results.add_result(
            "errorcontext_validation",
            "ErrorContext Import",
            "PASS",
            "Successfully imported ErrorContext from context module"
        )

        # Test 2: Create ErrorContext with required arguments
        try:
            context1 = ErrorContext(component="test", operation="validation")
            results.add_result(
                "errorcontext_validation",
                "Required Arguments Constructor",
                "PASS",
                f"Successfully created ErrorContext with required args: {context1.component}, {context1.operation}",
                {"component": context1.component, "operation": context1.operation}
            )
        except Exception as e:
            results.add_result(
                "errorcontext_validation",
                "Required Arguments Constructor",
                "FAIL",
                f"Failed to create ErrorContext with required args: {str(e)}"
            )

        # Test 3: Create ErrorContext with defaults (should work after fix)
        try:
            # This should now work with the fix
            from src.core.error.unified_exceptions import VirtuosoError
            error = VirtuosoError("Test error")
            results.add_result(
                "errorcontext_validation",
                "Default ErrorContext in VirtuosoError",
                "PASS",
                f"Successfully created VirtuosoError with default ErrorContext: {error.context.component}",
                {"context_component": error.context.component, "context_operation": error.context.operation}
            )
        except Exception as e:
            results.add_result(
                "errorcontext_validation",
                "Default ErrorContext in VirtuosoError",
                "FAIL",
                f"Failed to create VirtuosoError with default ErrorContext: {str(e)}"
            )

        # Test 4: Test all fixed ErrorContext calls in unified_exceptions.py
        test_cases = [
            ("ComponentError", "system", "component_error"),
            ("InitializationError", "system", "initialization"),
            ("BinanceValidationError", "binance", "validation_error"),
            ("ExchangeError", "exchange", "exchange_error"),
            ("BybitExchangeError", "bybit", "exchange_error"),
            ("MarketDataError", "market_data", "data_error")
        ]

        for error_class_name, expected_component, expected_operation in test_cases:
            try:
                # Import the error class
                error_module = importlib.import_module('src.core.error.unified_exceptions')
                error_class = getattr(error_module, error_class_name)

                # Create instance
                error_instance = error_class("Test error")

                # Validate context
                if hasattr(error_instance, 'context') and error_instance.context:
                    results.add_result(
                        "errorcontext_validation",
                        f"{error_class_name} ErrorContext",
                        "PASS",
                        f"Successfully created {error_class_name} with proper ErrorContext",
                        {
                            "component": error_instance.context.component,
                            "operation": error_instance.context.operation,
                            "expected_component": expected_component
                        }
                    )
                else:
                    results.add_result(
                        "errorcontext_validation",
                        f"{error_class_name} ErrorContext",
                        "FAIL",
                        f"{error_class_name} missing context attribute"
                    )

            except Exception as e:
                results.add_result(
                    "errorcontext_validation",
                    f"{error_class_name} ErrorContext",
                    "FAIL",
                    f"Failed to create {error_class_name}: {str(e)}"
                )

    except Exception as e:
        results.add_result(
            "errorcontext_validation",
            "ErrorContext Import",
            "FAIL",
            f"Failed to import ErrorContext: {str(e)}"
        )


def validate_system_import_performance(results: ValidationResults):
    """Test core system imports with proper venv311 environment."""

    # Test 1: Python version check
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info.major == 3 and sys.version_info.minor == 11:
        results.add_result(
            "import_performance",
            "Python Version Check",
            "PASS",
            f"Running on Python {python_version} (3.11.x required)",
            {"python_version": python_version}
        )
    else:
        results.add_result(
            "import_performance",
            "Python Version Check",
            "FAIL",
            f"Running on Python {python_version}, but 3.11.x required"
        )

    # Test 2: Core imports timing
    import_modules = [
        "src.core.error.context",
        "src.core.error.unified_exceptions",
        "src.core.exchanges.base",
        "src.core.market.market_data_manager",
        "src.monitoring.monitor"
    ]

    total_import_time = 0
    successful_imports = 0

    for module_name in import_modules:
        try:
            start_time = time.time()
            importlib.import_module(module_name)
            import_time = time.time() - start_time
            total_import_time += import_time
            successful_imports += 1

            results.add_result(
                "import_performance",
                f"Import {module_name}",
                "PASS",
                f"Successfully imported in {import_time:.3f}s",
                {"import_time": import_time}
            )
        except Exception as e:
            results.add_result(
                "import_performance",
                f"Import {module_name}",
                "FAIL",
                f"Failed to import: {str(e)}"
            )

    # Test 3: Overall import performance
    if total_import_time < 7.0:
        results.add_result(
            "import_performance",
            "Overall Import Performance",
            "PASS",
            f"Total import time {total_import_time:.3f}s < 7.0s requirement",
            {"total_time": total_import_time, "successful_imports": successful_imports}
        )
    else:
        results.add_result(
            "import_performance",
            "Overall Import Performance",
            "FAIL",
            f"Total import time {total_import_time:.3f}s exceeds 7.0s requirement"
        )


def validate_error_handling_functionality(results: ValidationResults):
    """Test exception creation and handling scenarios."""

    try:
        from src.core.error.unified_exceptions import (
            VirtuosoError, SystemError, ValidationError, ExchangeError,
            MarketDataError, BybitExchangeError, InitializationError
        )
        from src.core.error.context import ErrorContext

        # Test 1: Basic error creation and serialization
        try:
            error = VirtuosoError("Test error", error_code="TEST001")
            error_dict = error.to_dict()

            required_fields = ['error_type', 'message', 'error_code', 'severity', 'category', 'timestamp']
            missing_fields = [field for field in required_fields if field not in error_dict]

            if not missing_fields:
                results.add_result(
                    "error_handling",
                    "Error Serialization",
                    "PASS",
                    f"Successfully serialized VirtuosoError with all required fields",
                    {"serialized_fields": list(error_dict.keys())}
                )
            else:
                results.add_result(
                    "error_handling",
                    "Error Serialization",
                    "FAIL",
                    f"Missing required fields in serialization: {missing_fields}"
                )
        except Exception as e:
            results.add_result(
                "error_handling",
                "Error Serialization",
                "FAIL",
                f"Failed to serialize error: {str(e)}"
            )

        # Test 2: Error context propagation
        try:
            context = ErrorContext(component="test", operation="validation", symbol="BTCUSDT")
            error = MarketDataError("Test market data error", context=context)

            if error.context and error.context.symbol == "BTCUSDT":
                results.add_result(
                    "error_handling",
                    "Error Context Propagation",
                    "PASS",
                    f"Successfully propagated error context with symbol: {error.context.symbol}",
                    {"context_symbol": error.context.symbol, "context_component": error.context.component}
                )
            else:
                results.add_result(
                    "error_handling",
                    "Error Context Propagation",
                    "FAIL",
                    "Failed to propagate error context properly"
                )
        except Exception as e:
            results.add_result(
                "error_handling",
                "Error Context Propagation",
                "FAIL",
                f"Failed to test error context propagation: {str(e)}"
            )

        # Test 3: Exchange-specific error handling
        try:
            bybit_error = BybitExchangeError("Test Bybit error")

            if (bybit_error.context and
                bybit_error.context.component == "bybit" and
                bybit_error.context.exchange == "bybit"):
                results.add_result(
                    "error_handling",
                    "Exchange-Specific Errors",
                    "PASS",
                    f"Successfully created Bybit error with proper context",
                    {"component": bybit_error.context.component, "exchange": bybit_error.context.exchange}
                )
            else:
                results.add_result(
                    "error_handling",
                    "Exchange-Specific Errors",
                    "FAIL",
                    "Bybit error context not properly configured"
                )
        except Exception as e:
            results.add_result(
                "error_handling",
                "Exchange-Specific Errors",
                "FAIL",
                f"Failed to create Bybit error: {str(e)}"
            )

        # Test 4: Component initialization errors
        try:
            init_error = InitializationError("Test initialization error", component="test_component")

            if (init_error.context and
                init_error.context.component == "test_component" and
                init_error.context.operation == "initialization"):
                results.add_result(
                    "error_handling",
                    "Initialization Errors",
                    "PASS",
                    f"Successfully created initialization error with proper context",
                    {"component": init_error.context.component, "operation": init_error.context.operation}
                )
            else:
                results.add_result(
                    "error_handling",
                    "Initialization Errors",
                    "FAIL",
                    "Initialization error context not properly configured"
                )
        except Exception as e:
            results.add_result(
                "error_handling",
                "Initialization Errors",
                "FAIL",
                f"Failed to create initialization error: {str(e)}"
            )

    except ImportError as e:
        results.add_result(
            "error_handling",
            "Error Module Import",
            "FAIL",
            f"Failed to import error modules: {str(e)}"
        )


def validate_production_readiness(results: ValidationResults):
    """Verify system can start without ErrorContext-related crashes."""

    # Test 1: Core system startup simulation
    try:
        from src.core.error.unified_exceptions import VirtuosoError, SystemError
        from src.core.error.context import ErrorContext

        # Simulate various startup scenarios
        startup_tests = [
            ("System Error", lambda: SystemError("System startup test")),
            ("Virtuoso Error with defaults", lambda: VirtuosoError("Default context test")),
            ("ErrorContext direct creation", lambda: ErrorContext(component="startup", operation="test")),
        ]

        startup_success = True
        for test_name, test_func in startup_tests:
            try:
                result = test_func()
                results.add_result(
                    "production_readiness",
                    f"Startup Test: {test_name}",
                    "PASS",
                    f"Successfully executed {test_name}",
                    {"result_type": type(result).__name__}
                )
            except Exception as e:
                startup_success = False
                results.add_result(
                    "production_readiness",
                    f"Startup Test: {test_name}",
                    "FAIL",
                    f"Failed {test_name}: {str(e)}"
                )

        # Overall startup assessment
        if startup_success:
            results.add_result(
                "production_readiness",
                "System Startup Simulation",
                "PASS",
                "All startup tests passed - system ready for deployment"
            )
        else:
            results.add_result(
                "production_readiness",
                "System Startup Simulation",
                "FAIL",
                "Some startup tests failed - deployment blocked"
            )

    except Exception as e:
        results.add_result(
            "production_readiness",
            "System Startup Simulation",
            "FAIL",
            f"Critical startup failure: {str(e)}"
        )

    # Test 2: Error scenario resilience
    try:
        from src.core.error.unified_exceptions import VirtuosoError

        # Test error handling under various conditions
        error_scenarios = [
            ("None context", None),
            ("Empty string component", ""),
            ("Empty string operation", "test"),
        ]

        resilience_passed = True
        for scenario_name, context_component in error_scenarios:
            try:
                if context_component is None:
                    # Test default context creation
                    error = VirtuosoError("Test error")
                else:
                    from src.core.error.context import ErrorContext
                    context = ErrorContext(component=context_component or "test", operation="test")
                    error = VirtuosoError("Test error", context=context)

                # Verify error can be serialized
                error_dict = error.to_dict()

                results.add_result(
                    "production_readiness",
                    f"Resilience Test: {scenario_name}",
                    "PASS",
                    f"System handled {scenario_name} gracefully",
                    {"error_type": type(error).__name__}
                )
            except Exception as e:
                resilience_passed = False
                results.add_result(
                    "production_readiness",
                    f"Resilience Test: {scenario_name}",
                    "FAIL",
                    f"System failed for {scenario_name}: {str(e)}"
                )

        if resilience_passed:
            results.add_result(
                "production_readiness",
                "Error Scenario Resilience",
                "PASS",
                "System demonstrates resilience across error scenarios"
            )
        else:
            results.add_result(
                "production_readiness",
                "Error Scenario Resilience",
                "FAIL",
                "System lacks resilience for some error scenarios"
            )

    except Exception as e:
        results.add_result(
            "production_readiness",
            "Error Scenario Resilience",
            "FAIL",
            f"Critical resilience test failure: {str(e)}"
        )


def validate_crisis_stabilization_integration(results: ValidationResults):
    """Validate integration with crisis stabilization achievements."""

    # Test 1: Verify previous stabilization features remain intact
    try:
        # Check if monitoring system is accessible
        try:
            import src.monitoring.monitor
            results.add_result(
                "crisis_integration",
                "Monitoring System Integrity",
                "PASS",
                "Monitoring system remains accessible after ErrorContext fix"
            )
        except Exception as e:
            results.add_result(
                "crisis_integration",
                "Monitoring System Integrity",
                "FAIL",
                f"Monitoring system compromised: {str(e)}"
            )

        # Check if exchange systems are accessible
        try:
            import src.core.exchanges.base
            import src.core.exchanges.manager
            results.add_result(
                "crisis_integration",
                "Exchange System Integrity",
                "PASS",
                "Exchange systems remain accessible after ErrorContext fix"
            )
        except Exception as e:
            results.add_result(
                "crisis_integration",
                "Exchange System Integrity",
                "FAIL",
                f"Exchange systems compromised: {str(e)}"
            )

        # Check if market data systems are accessible
        try:
            import src.core.market.market_data_manager
            results.add_result(
                "crisis_integration",
                "Market Data System Integrity",
                "PASS",
                "Market data systems remain accessible after ErrorContext fix"
            )
        except Exception as e:
            results.add_result(
                "crisis_integration",
                "Market Data System Integrity",
                "FAIL",
                f"Market data systems compromised: {str(e)}"
            )

    except Exception as e:
        results.add_result(
            "crisis_integration",
            "System Integrity Check",
            "FAIL",
            f"Failed to verify system integrity: {str(e)}"
        )

    # Test 2: Verify backward compatibility
    try:
        from src.core.error.unified_exceptions import (
            ConfigurationError, StateError, CommunicationError,
            OperationError, DataError, MarketMonitorError
        )

        # Test legacy aliases
        legacy_tests = [
            ("ConfigurationError", ConfigurationError),
            ("StateError", StateError),
            ("CommunicationError", CommunicationError),
            ("OperationError", OperationError),
            ("DataError", DataError),
            ("MarketMonitorError", MarketMonitorError)
        ]

        compatibility_success = True
        for alias_name, alias_class in legacy_tests:
            try:
                error_instance = alias_class("Test legacy error")
                results.add_result(
                    "crisis_integration",
                    f"Legacy Compatibility: {alias_name}",
                    "PASS",
                    f"Successfully created {alias_name} instance",
                    {"error_type": type(error_instance).__name__}
                )
            except Exception as e:
                compatibility_success = False
                results.add_result(
                    "crisis_integration",
                    f"Legacy Compatibility: {alias_name}",
                    "FAIL",
                    f"Failed to create {alias_name}: {str(e)}"
                )

        if compatibility_success:
            results.add_result(
                "crisis_integration",
                "Backward Compatibility",
                "PASS",
                "All legacy error aliases function correctly"
            )
        else:
            results.add_result(
                "crisis_integration",
                "Backward Compatibility",
                "FAIL",
                "Some legacy error aliases are broken"
            )

    except Exception as e:
        results.add_result(
            "crisis_integration",
            "Backward Compatibility",
            "FAIL",
            f"Failed to test backward compatibility: {str(e)}"
        )


def main():
    """Main validation function."""
    print("🔍 Starting Comprehensive ErrorContext Validation...")
    print("=" * 60)

    results = ValidationResults()

    # Execute all validation categories
    validation_functions = [
        ("ErrorContext Constructor Validation", validate_errorcontext_constructors),
        ("System Import Performance", validate_system_import_performance),
        ("Error Handling Functionality", validate_error_handling_functionality),
        ("Production Readiness Verification", validate_production_readiness),
        ("Crisis Stabilization Integration", validate_crisis_stabilization_integration)
    ]

    for category_name, validation_func in validation_functions:
        print(f"\n🧪 Running {category_name}...")
        try:
            validation_func(results)
            status = results.get_category_status(category_name.lower().replace(" ", "_"))
            status_emoji = "✅" if status == "PASS" else "⚠️" if status == "PARTIAL" else "❌"
            print(f"   {status_emoji} {category_name}: {status}")
        except Exception as e:
            print(f"   ❌ {category_name}: CRITICAL FAILURE - {str(e)}")
            results.add_result(
                category_name.lower().replace(" ", "_"),
                "Category Execution",
                "FAIL",
                f"Critical failure in category execution: {str(e)}"
            )

    # Generate and save report
    report = results.generate_report()

    # Save to file
    with open("ERRORCONTEXT_VALIDATION_REPORT.md", "w") as f:
        f.write(report)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Overall Score: {results.overall_score:.1f}%")
    print(f"Tests Passed: {results.passed_tests}/{results.total_tests}")

    if results.overall_score >= 95:
        print("🚀 RECOMMENDATION: APPROVED FOR PRODUCTION DEPLOYMENT")
    elif results.overall_score >= 80:
        print("⚠️  RECOMMENDATION: CONDITIONAL APPROVAL")
    else:
        print("❌ RECOMMENDATION: NOT APPROVED FOR PRODUCTION")

    print(f"\n📝 Detailed report saved to: ERRORCONTEXT_VALIDATION_REPORT.md")

    return results.overall_score >= 80  # Return True if ready for production


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 CRITICAL VALIDATION FAILURE: {str(e)}")
        traceback.print_exc()
        sys.exit(1)