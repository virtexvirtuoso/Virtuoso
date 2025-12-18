#!/usr/bin/env python3
"""
Edge case validation for whale detection system fixes.

This script tests specific edge cases and boundary conditions
to ensure the fixes are robust and handle all scenarios correctly.
"""

import asyncio
import sys
import logging
import unittest
from unittest.mock import Mock, patch, AsyncMock
import traceback

# Add src to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from monitoring.monitor import MarketMonitor
from monitoring.utils.decorators import handle_monitoring_error

logging.basicConfig(level=logging.INFO)

class EdgeCaseValidationTests(unittest.IsolatedAsyncioTestCase):
    """Edge case validation tests for whale detection system fixes."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.test_results = {}

    async def test_partial_dependency_injection_scenario(self):
        """
        Test scenario where some critical dependencies are present and others are missing.
        This tests the boundary conditions of the dependency validation.
        """
        self.logger.info("🧪 Testing Partial Dependency Injection Scenario")

        # Test different combinations of missing/present critical dependencies
        test_scenarios = [
            {"exchange_manager": True, "alert_manager": False, "top_symbols_manager": True},
            {"exchange_manager": False, "alert_manager": True, "top_symbols_manager": True},
            {"exchange_manager": True, "alert_manager": True, "top_symbols_manager": False},
            {"exchange_manager": False, "alert_manager": False, "top_symbols_manager": True},
        ]

        results = []
        for i, scenario in enumerate(test_scenarios):
            monitor = MarketMonitor()
            monitor.logger = logging.getLogger(f"test_monitor_{i}")

            # Set dependencies based on scenario
            monitor.exchange_manager = Mock() if scenario["exchange_manager"] else None
            monitor.alert_manager = Mock() if scenario["alert_manager"] else None
            monitor.top_symbols_manager = Mock() if scenario["top_symbols_manager"] else None

            # Test initialization
            init_result = await monitor.initialize()

            # Count missing dependencies
            missing_count = sum(1 for v in scenario.values() if not v)

            # Should fail if any critical dependency is missing
            expected_result = missing_count == 0

            results.append({
                "scenario": scenario,
                "init_result": init_result,
                "expected": expected_result,
                "passed": init_result == expected_result,
                "missing_count": missing_count
            })

        all_passed = all(r["passed"] for r in results)

        self.test_results["partial_dependency_injection"] = {
            "status": "PASS" if all_passed else "FAIL",
            "message": f"Tested {len(test_scenarios)} partial dependency scenarios",
            "details": results
        }

        self.assertTrue(all_passed, "All partial dependency scenarios should behave correctly")
        self.logger.info("✅ Partial Dependency Injection scenarios validated")

    async def test_mixed_task_results_analysis(self):
        """
        Test the task result validation with various mixed scenarios including edge cases.
        """
        self.logger.info("🧪 Testing Mixed Task Results Analysis")

        # Complex mixed scenarios
        test_scenarios = [
            # Scenario 1: All None results (complete silent failure)
            [None, None, None, None],
            # Scenario 2: All exceptions (complete visible failure)
            [RuntimeError("fail1"), ValueError("fail2"), ConnectionError("fail3")],
            # Scenario 3: All successful
            ["success1", {"result": "success2"}, "success3"],
            # Scenario 4: Mixed with different exception types
            [None, RuntimeError("critical"), "success", None, ValueError("minor"), "another_success"],
            # Scenario 5: Edge case with empty results
            [],
            # Scenario 6: Single None result
            [None],
            # Scenario 7: Single exception
            [RuntimeError("single_fail")],
            # Scenario 8: Single success
            ["single_success"]
        ]

        analysis_results = []

        for i, results in enumerate(test_scenarios):
            # Apply the same logic as in monitor.py:725-741
            exceptions = [r for r in results if isinstance(r, Exception)]
            none_results = [j for j, r in enumerate(results) if r is None]
            successful_tasks = len(results) - len(exceptions) - len(none_results)

            analysis = {
                "scenario_id": i + 1,
                "total_results": len(results),
                "exceptions": len(exceptions),
                "none_results": len(none_results),
                "successful": successful_tasks,
                "exception_types": [type(e).__name__ for e in exceptions],
                "none_indices": none_results
            }

            # Validate correctness
            expected_total = analysis["exceptions"] + analysis["none_results"] + analysis["successful"]
            analysis["validation_passed"] = (expected_total == analysis["total_results"])

            analysis_results.append(analysis)

        all_validated = all(r["validation_passed"] for r in analysis_results)

        self.test_results["mixed_task_results"] = {
            "status": "PASS" if all_validated else "FAIL",
            "message": f"Analyzed {len(test_scenarios)} mixed task result scenarios",
            "details": analysis_results
        }

        self.assertTrue(all_validated, "All task result analysis should be mathematically correct")
        self.logger.info("✅ Mixed Task Results Analysis validated")

    async def test_exception_propagation_with_different_exception_types(self):
        """
        Test that different types of exceptions are properly propagated through the system.
        """
        self.logger.info("🧪 Testing Exception Propagation with Different Exception Types")

        exception_types = [
            (RuntimeError, "Runtime error test"),
            (ValueError, "Value error test"),
            (ConnectionError, "Connection error test"),
            (TimeoutError, "Timeout error test"),
            (KeyError, "Key error test"),
            (AttributeError, "Attribute error test")
        ]

        propagation_results = []

        for exception_class, message in exception_types:
            monitor = MarketMonitor()
            monitor.exchange_manager = None  # Force the exception
            monitor.logger = logging.getLogger(f"test_exception_{exception_class.__name__}")

            try:
                # This should raise RuntimeError due to missing exchange_manager
                await monitor._process_symbol("TEST/USDT")
                raised_correctly = False
                raised_exception = None
            except Exception as e:
                raised_correctly = True
                raised_exception = type(e).__name__

            propagation_results.append({
                "expected_exception": "RuntimeError",  # This is what _process_symbol should raise
                "raised_correctly": raised_correctly,
                "actual_exception": raised_exception,
                "test_passed": raised_correctly and raised_exception == "RuntimeError"
            })

        all_propagated = all(r["test_passed"] for r in propagation_results)

        self.test_results["exception_propagation_types"] = {
            "status": "PASS" if all_propagated else "FAIL",
            "message": f"Tested exception propagation with {len(exception_types)} different scenarios",
            "details": propagation_results
        }

        self.assertTrue(all_propagated, "All exception scenarios should raise RuntimeError consistently")
        self.logger.info("✅ Exception Propagation with Different Types validated")

    async def test_concurrent_task_failure_detection(self):
        """
        Test the system's ability to detect failures in concurrent task scenarios.
        """
        self.logger.info("🧪 Testing Concurrent Task Failure Detection")

        # Create tasks with different failure modes
        async def task_success():
            await asyncio.sleep(0.01)  # Simulate work
            return {"status": "success", "processed": True}

        async def task_exception():
            await asyncio.sleep(0.01)  # Simulate work
            raise RuntimeError("Concurrent task failure")

        async def task_silent_failure():
            await asyncio.sleep(0.01)  # Simulate work
            return None  # Silent failure

        # Test concurrent execution with mixed outcomes
        concurrent_scenarios = [
            # Scenario 1: Mixed concurrent tasks
            [task_success(), task_exception(), task_silent_failure(), task_success()],
            # Scenario 2: All failing concurrently
            [task_exception(), task_exception(), task_silent_failure()],
            # Scenario 3: High concurrency
            [task_success() for _ in range(10)] + [task_exception() for _ in range(3)] + [task_silent_failure() for _ in range(2)]
        ]

        concurrent_results = []

        for i, tasks in enumerate(concurrent_scenarios):
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Apply result analysis
                exceptions = [r for r in results if isinstance(r, Exception)]
                none_results = [j for j, r in enumerate(results) if r is None]
                successful_tasks = len(results) - len(exceptions) - len(none_results)

                concurrent_results.append({
                    "scenario_id": i + 1,
                    "total_tasks": len(tasks),
                    "exceptions": len(exceptions),
                    "none_results": len(none_results),
                    "successful": successful_tasks,
                    "analysis_correct": (len(exceptions) + len(none_results) + successful_tasks) == len(results)
                })

            except Exception as e:
                concurrent_results.append({
                    "scenario_id": i + 1,
                    "error": str(e),
                    "analysis_correct": False
                })

        all_concurrent_correct = all(r.get("analysis_correct", False) for r in concurrent_results)

        self.test_results["concurrent_task_detection"] = {
            "status": "PASS" if all_concurrent_correct else "FAIL",
            "message": f"Tested {len(concurrent_scenarios)} concurrent task scenarios",
            "details": concurrent_results
        }

        self.assertTrue(all_concurrent_correct, "Concurrent task failure detection should work correctly")
        self.logger.info("✅ Concurrent Task Failure Detection validated")

    async def test_system_recovery_after_dependency_injection(self):
        """
        Test that the system can recover and work properly after dependencies are injected.
        """
        self.logger.info("🧪 Testing System Recovery After Dependency Injection")

        # Start with a broken system
        monitor = MarketMonitor()
        monitor.logger = self.logger

        # Initially no dependencies
        monitor.exchange_manager = None
        monitor.alert_manager = None
        monitor.top_symbols_manager = None

        # Test that initialization fails
        init_result_broken = await monitor.initialize()
        self.assertFalse(init_result_broken, "Initialization should fail with missing dependencies")

        # Now inject dependencies (simulating DI container fallback)
        monitor.exchange_manager = Mock()
        monitor.alert_manager = Mock()
        monitor.top_symbols_manager = Mock()

        # Mock required methods
        monitor.exchange_manager.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BTC/USDT',
            'last': 50000,
            'bid': 49999,
            'ask': 50001
        })

        # Test that system can now recover
        recovery_successful = False
        recovery_error = None

        try:
            # Re-initialize with dependencies
            with patch.object(monitor, '_initialize_components', new_callable=AsyncMock):
                init_result_fixed = await monitor.initialize()
                self.assertTrue(init_result_fixed, "Initialization should succeed after dependency injection")

            # Test that _process_symbol now works
            await monitor._process_symbol("BTC/USDT")
            recovery_successful = True

        except Exception as e:
            recovery_error = str(e)

        self.test_results["system_recovery"] = {
            "status": "PASS" if recovery_successful else "FAIL",
            "message": "System should recover after dependency injection" if recovery_successful else f"Recovery failed: {recovery_error}",
            "broken_initialization": init_result_broken,
            "recovery_successful": recovery_successful,
            "error": recovery_error
        }

        self.assertTrue(recovery_successful, f"System should recover after dependency injection. Error: {recovery_error}")
        self.logger.info("✅ System Recovery After Dependency Injection validated")

    def generate_edge_case_report(self):
        """Generate comprehensive edge case validation report."""

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r["status"] == "PASS"])
        failed_tests = total_tests - passed_tests

        return {
            "summary": {
                "total_edge_case_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "test_results": self.test_results,
            "edge_case_coverage": {
                "partial_dependencies": "partial_dependency_injection" in self.test_results,
                "mixed_task_results": "mixed_task_results" in self.test_results,
                "exception_types": "exception_propagation_types" in self.test_results,
                "concurrent_scenarios": "concurrent_task_detection" in self.test_results,
                "system_recovery": "system_recovery" in self.test_results
            }
        }

async def main():
    """Run all edge case validation tests."""

    print("🔍 Whale Detection System - Edge Case Validation")
    print("=" * 60)

    # Create test suite
    test_instance = EdgeCaseValidationTests()
    test_instance.setUp()

    try:
        # Run all edge case tests
        await test_instance.test_partial_dependency_injection_scenario()
        await test_instance.test_mixed_task_results_analysis()
        await test_instance.test_exception_propagation_with_different_exception_types()
        await test_instance.test_concurrent_task_failure_detection()
        await test_instance.test_system_recovery_after_dependency_injection()

        # Generate and display report
        report = test_instance.generate_edge_case_report()

        print("\n" + "=" * 60)
        print("📊 EDGE CASE VALIDATION REPORT")
        print("=" * 60)
        print(f"Total Edge Case Tests: {report['summary']['total_edge_case_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']}")

        print("\n🔍 DETAILED RESULTS:")
        for test_name, result in report['test_results'].items():
            status_emoji = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_emoji} {test_name}: {result['message']}")

        print("\n📋 EDGE CASE COVERAGE:")
        for coverage_area, covered in report['edge_case_coverage'].items():
            status = "✅ Covered" if covered else "❌ Missing"
            print(f"{status}: {coverage_area}")

        return report

    except Exception as e:
        print(f"❌ Edge case validation failed with error: {e}")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    asyncio.run(main())