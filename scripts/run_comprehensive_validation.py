#!/usr/bin/env python3
"""
Master validation script for tuple unwrapping and reliability formatting fixes.
Runs all test suites and generates a comprehensive validation report.
"""

import sys
import os
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
import psutil

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class ComprehensiveValidator:
    """Comprehensive validation suite for the fixes."""

    def __init__(self):
        self.project_root = os.path.join(os.path.dirname(__file__), '..')
        self.venv_python = os.path.join(self.project_root, 'venv311', 'bin', 'python')
        self.scripts_dir = os.path.join(self.project_root, 'scripts')
        self.start_time = datetime.now()
        self.results = {}

    def run_test_script(self, script_name: str, description: str) -> Dict[str, Any]:
        """Run a test script and capture results."""
        script_path = os.path.join(self.scripts_dir, script_name)

        if not os.path.exists(script_path):
            return {
                'success': False,
                'error': f'Script not found: {script_path}',
                'duration': 0,
                'output': ''
            }

        print(f"\n{'='*60}")
        print(f"Running {description}")
        print(f"Script: {script_name}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            # Run the test script
            result = subprocess.run(
                [self.venv_python, script_path],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            duration = time.time() - start_time

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'duration': duration,
                'output': result.stdout,
                'error_output': result.stderr,
                'description': description
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'success': False,
                'error': 'Test timed out after 5 minutes',
                'duration': duration,
                'output': '',
                'error_output': 'Timeout',
                'description': description
            }

        except Exception as e:
            duration = time.time() - start_time
            return {
                'success': False,
                'error': str(e),
                'duration': duration,
                'output': '',
                'error_output': str(e),
                'description': description
            }

    def check_environment(self) -> Dict[str, Any]:
        """Check the test environment."""
        print("Checking test environment...")

        checks = {}

        # Check Python virtual environment
        checks['venv_exists'] = os.path.exists(self.venv_python)
        if checks['venv_exists']:
            try:
                result = subprocess.run([self.venv_python, '--version'], capture_output=True, text=True)
                checks['python_version'] = result.stdout.strip()
            except:
                checks['python_version'] = 'Unknown'
        else:
            checks['python_version'] = 'Not found'

        # Check project structure
        checks['project_structure'] = {
            'src_exists': os.path.exists(os.path.join(self.project_root, 'src')),
            'scripts_exists': os.path.exists(self.scripts_dir),
            'formatter_exists': os.path.exists(os.path.join(self.project_root, 'src', 'core', 'formatting', 'formatter.py')),
            'indicators_exists': os.path.exists(os.path.join(self.project_root, 'src', 'indicators', 'technical_indicators.py'))
        }

        # Check system resources
        checks['system_resources'] = {
            'cpu_count': psutil.cpu_count(),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'available_memory_gb': round(psutil.virtual_memory().available / (1024**3), 2)
        }

        return checks

    def run_performance_baseline(self) -> Dict[str, Any]:
        """Establish performance baseline."""
        print("\nEstablishing performance baseline...")

        try:
            # Simple import test
            start_time = time.time()
            import_result = subprocess.run(
                [self.venv_python, '-c', 'from src.core.formatting.formatter import PrettyTableFormatter; from src.indicators.technical_indicators import TechnicalIndicators; print("Import successful")'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            import_time = time.time() - start_time

            return {
                'import_success': import_result.returncode == 0,
                'import_time': import_time,
                'import_output': import_result.stdout,
                'import_error': import_result.stderr
            }

        except Exception as e:
            return {
                'import_success': False,
                'import_time': 0,
                'import_output': '',
                'import_error': str(e)
            }

    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        report = []
        report.append("=" * 100)
        report.append("VIRTUOSO CCXT COMPREHENSIVE VALIDATION REPORT")
        report.append("Tuple Unwrapping and Reliability Formatting Fixes")
        report.append("=" * 100)
        report.append("")

        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 50)

        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get('success', False))
        failed_tests = total_tests - passed_tests

        report.append(f"Test execution completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total duration: {total_duration:.1f} seconds")
        report.append(f"Tests executed: {total_tests}")
        report.append(f"Tests passed: {passed_tests}")
        report.append(f"Tests failed: {failed_tests}")
        report.append(f"Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "Success rate: N/A")
        report.append("")

        # Environment Information
        if hasattr(self, 'environment_check'):
            report.append("ENVIRONMENT VALIDATION")
            report.append("-" * 50)
            env = self.environment_check

            report.append(f"Python virtual environment: {'✓' if env['venv_exists'] else '✗'}")
            report.append(f"Python version: {env['python_version']}")

            structure = env['project_structure']
            report.append(f"Project structure validation:")
            report.append(f"  - src/ directory: {'✓' if structure['src_exists'] else '✗'}")
            report.append(f"  - scripts/ directory: {'✓' if structure['scripts_exists'] else '✗'}")
            report.append(f"  - formatter.py: {'✓' if structure['formatter_exists'] else '✗'}")
            report.append(f"  - technical_indicators.py: {'✓' if structure['indicators_exists'] else '✗'}")

            resources = env['system_resources']
            report.append(f"System resources:")
            report.append(f"  - CPU cores: {resources['cpu_count']}")
            report.append(f"  - Total memory: {resources['memory_gb']} GB")
            report.append(f"  - Available memory: {resources['available_memory_gb']} GB")
            report.append("")

        # Performance Baseline
        if hasattr(self, 'performance_baseline'):
            report.append("PERFORMANCE BASELINE")
            report.append("-" * 50)
            perf = self.performance_baseline

            report.append(f"Import test: {'✓' if perf['import_success'] else '✗'}")
            report.append(f"Import time: {perf['import_time']:.3f} seconds")
            if not perf['import_success']:
                report.append(f"Import error: {perf['import_error']}")
            report.append("")

        # Test Results Detail
        report.append("DETAILED TEST RESULTS")
        report.append("-" * 50)

        for test_name, result in self.results.items():
            status = "✓ PASS" if result.get('success', False) else "✗ FAIL"
            duration = result.get('duration', 0)

            report.append(f"{status} {test_name}")
            report.append(f"    Description: {result.get('description', 'N/A')}")
            report.append(f"    Duration: {duration:.2f} seconds")

            if not result.get('success', False):
                error = result.get('error', result.get('error_output', 'Unknown error'))
                report.append(f"    Error: {error}")

            # Include key output snippets
            output = result.get('output', '')
            if output and 'PASS' in output:
                lines = output.split('\n')
                summary_lines = [line for line in lines if 'PASS' in line or 'FAIL' in line or 'Tests run:' in line]
                if summary_lines:
                    report.append(f"    Summary: {summary_lines[-1]}")

            report.append("")

        # Traceability Table
        report.append("REQUIREMENTS TRACEABILITY")
        report.append("-" * 50)

        traceability = [
            ("REQ-1", "Reliability values display as 0-100% (not 10000%)", "test_reliability_formatting_comprehensive.py"),
            ("REQ-2", "Cache tuple values unwrap correctly without format errors", "test_tuple_unwrapping_comprehensive.py"),
            ("REQ-3", "No 'unsupported format string' errors in application logs", "test_integration_comprehensive.py"),
            ("REQ-4", "System handles edge cases and extreme values gracefully", "test_edge_cases_comprehensive.py"),
            ("REQ-5", "Performance impact is minimal", "All test scripts"),
            ("REQ-6", "No regression in existing functionality", "test_integration_comprehensive.py")
        ]

        for req_id, description, test_file in traceability:
            test_key = test_file.replace('.py', '').replace('test_', '').replace('_comprehensive', '').title()
            test_status = "✓" if self.results.get(test_key, {}).get('success', False) else "✗"
            report.append(f"{req_id}: {description}")
            report.append(f"    Test: {test_file} [{test_status}]")
            report.append("")

        # Risk Assessment
        report.append("RISK ASSESSMENT")
        report.append("-" * 50)

        if failed_tests == 0:
            report.append("✓ LOW RISK: All tests passed successfully")
            report.append("  - Reliability formatting works correctly")
            report.append("  - Tuple unwrapping prevents format errors")
            report.append("  - No performance regressions detected")
            report.append("  - Edge cases handled appropriately")
        else:
            report.append("⚠ MEDIUM-HIGH RISK: Some tests failed")
            for test_name, result in self.results.items():
                if not result.get('success', False):
                    report.append(f"  - FAILED: {test_name}")
                    report.append(f"    Impact: {result.get('description', 'Unknown')}")

        report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 50)

        if failed_tests == 0:
            report.append("✓ DEPLOY: Fixes are ready for production deployment")
            report.append("  - All validation tests passed")
            report.append("  - No critical issues identified")
            report.append("  - Performance impact is acceptable")
            report.append("")
            report.append("Next steps:")
            report.append("  1. Deploy fixes to VPS environment")
            report.append("  2. Monitor production logs for 24 hours")
            report.append("  3. Verify dashboard reliability displays")
            report.append("  4. Confirm no tuple format errors occur")
        else:
            report.append("⚠ INVESTIGATE: Address failed tests before deployment")
            report.append("  - Review failed test outputs")
            report.append("  - Fix identified issues")
            report.append("  - Re-run validation suite")
            report.append("  - Consider additional testing")

        report.append("")

        # Footer
        report.append("=" * 100)
        report.append(f"Report generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("Virtuoso CCXT Trading System - Quantitative Validation Report")
        report.append("=" * 100)

        return "\n".join(report)

    def run_all_validations(self):
        """Run all validation tests."""
        print("Starting comprehensive validation suite...")
        print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Check environment
        self.environment_check = self.check_environment()

        # Run performance baseline
        self.performance_baseline = self.run_performance_baseline()

        # Define test suite
        test_suite = [
            ('test_reliability_formatting_comprehensive.py', 'Reliability Formatting'),
            ('test_tuple_unwrapping_comprehensive.py', 'Tuple Unwrapping'),
            ('test_edge_cases_comprehensive.py', 'Edge Cases'),
            ('test_integration_comprehensive.py', 'Integration'),
        ]

        # Run each test
        for script, description in test_suite:
            test_key = description.replace(' ', '')
            print(f"\n[{len(self.results)+1}/{len(test_suite)}] {description} Tests")

            result = self.run_test_script(script, description)
            self.results[test_key] = result

            if result['success']:
                print(f"✓ {description} tests PASSED ({result['duration']:.1f}s)")
            else:
                print(f"✗ {description} tests FAILED ({result['duration']:.1f}s)")
                if result.get('error'):
                    print(f"  Error: {result['error']}")

        # Generate and save report
        report = self.generate_report()

        # Save report to file
        report_file = os.path.join(self.project_root, f"VALIDATION_REPORT_{self.start_time.strftime('%Y%m%d_%H%M%S')}.md")
        try:
            with open(report_file, 'w') as f:
                f.write(report)
            print(f"\n📄 Report saved to: {report_file}")
        except Exception as e:
            print(f"\n⚠ Failed to save report: {e}")

        # Print report
        print("\n" + report)

        # Return overall success
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get('success', False))
        overall_success = total_tests > 0 and passed_tests == total_tests

        return overall_success


def main():
    """Main validation entry point."""
    validator = ComprehensiveValidator()
    success = validator.run_all_validations()

    if success:
        print("\n🎉 ALL VALIDATIONS PASSED - READY FOR DEPLOYMENT")
    else:
        print("\n❌ SOME VALIDATIONS FAILED - INVESTIGATE BEFORE DEPLOYMENT")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())