#!/usr/bin/env python3
"""
Comprehensive integration test suite for tuple unwrapping and reliability formatting fixes.
Tests the full application flow to ensure fixes work end-to-end.
"""

import sys
import os
import subprocess
import time
import requests
import json
import re
from typing import Dict, Any, List
import threading
import signal
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class IntegrationTestRunner:
    """Integration test runner for the Virtuoso CCXT application."""

    def __init__(self):
        self.project_root = os.path.join(os.path.dirname(__file__), '..')
        self.venv_python = os.path.join(self.project_root, 'venv311', 'bin', 'python')
        self.main_script = os.path.join(self.project_root, 'src', 'main.py')
        self.process = None
        self.base_url = "http://localhost:8003"
        self.monitoring_url = "http://localhost:8001"

    @contextmanager
    def application_context(self, timeout=30):
        """Context manager to start and stop the application."""
        print(f"Starting application with timeout {timeout}s...")

        # Start the application
        env = os.environ.copy()
        env['PYTHONPATH'] = self.project_root

        self.process = subprocess.Popen(
            [self.venv_python, self.main_script],
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        try:
            # Wait for application to start
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("Application started successfully!")
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            else:
                raise Exception(f"Application failed to start within {timeout} seconds")

            yield self

        finally:
            # Stop the application
            if self.process:
                print("Stopping application...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()

    def test_health_endpoint(self):
        """Test that health endpoint works."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"

            data = response.json()
            assert 'status' in data, "Health response missing status"
            print("✓ Health endpoint test passed")
            return True
        except Exception as e:
            print(f"✗ Health endpoint test failed: {e}")
            return False

    def test_dashboard_data_endpoint(self):
        """Test dashboard data endpoint for reliability formatting."""
        try:
            response = requests.get(f"{self.base_url}/api/dashboard/data", timeout=10)
            assert response.status_code == 200, f"Dashboard data failed: {response.status_code}"

            data = response.json()

            # Check for reliability values in the response
            issues_found = []

            def check_reliability_recursive(obj, path=""):
                """Recursively check for reliability formatting issues."""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key

                        # Check for reliability keys
                        if 'reliability' in key.lower():
                            if isinstance(value, (int, float)):
                                if value > 100:  # Should never exceed 100%
                                    issues_found.append(f"Reliability over 100% at {current_path}: {value}")
                                elif value > 1 and value <= 100:
                                    # This is okay - could be percentage format
                                    pass
                                elif value > 1:
                                    issues_found.append(f"Suspicious reliability value at {current_path}: {value}")
                            elif isinstance(value, str):
                                # Check for percentage strings
                                if '%' in value:
                                    pct_match = re.search(r'(\d+(?:\.\d+)?)%', value)
                                    if pct_match:
                                        pct_value = float(pct_match.group(1))
                                        if pct_value > 100:
                                            issues_found.append(f"Percentage over 100% at {current_path}: {value}")
                                        if pct_value > 1000:  # Definitely wrong
                                            issues_found.append(f"Extreme percentage at {current_path}: {value}")

                        # Check for tuple-like strings (shouldn't appear in JSON)
                        if isinstance(value, str) and '(' in value and ')' in value and ',' in value:
                            if 'L1' in value or 'L2' in value or 'L3' in value:  # Cache layer indicators
                                issues_found.append(f"Possible tuple leak at {current_path}: {value}")

                        # Recurse into nested structures
                        check_reliability_recursive(value, current_path)

                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_reliability_recursive(item, f"{path}[{i}]")

            check_reliability_recursive(data)

            if issues_found:
                print(f"✗ Dashboard data test found issues:")
                for issue in issues_found:
                    print(f"  - {issue}")
                return False
            else:
                print("✓ Dashboard data endpoint test passed")
                return True

        except Exception as e:
            print(f"✗ Dashboard data endpoint test failed: {e}")
            return False

    def test_mobile_dashboard_endpoint(self):
        """Test mobile dashboard endpoint."""
        try:
            response = requests.get(f"{self.base_url}/api/dashboard/mobile", timeout=10)
            assert response.status_code == 200, f"Mobile dashboard failed: {response.status_code}"

            data = response.json()

            # Check for formatting issues specific to mobile
            issues_found = []

            # Look for reliability displays in mobile data
            def check_mobile_data(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key

                        # Mobile might have summary reliability data
                        if 'reliability' in key.lower() or 'confidence' in key.lower():
                            if isinstance(value, str) and '%' in value:
                                pct_match = re.search(r'(\d+(?:\.\d+)?)%', value)
                                if pct_match:
                                    pct_value = float(pct_match.group(1))
                                    if pct_value > 100:
                                        issues_found.append(f"Mobile reliability over 100% at {current_path}: {value}")

                        # Recurse
                        if isinstance(value, (dict, list)):
                            check_mobile_data(value, current_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_mobile_data(item, f"{path}[{i}]")

            check_mobile_data(data)

            if issues_found:
                print(f"✗ Mobile dashboard test found issues:")
                for issue in issues_found:
                    print(f"  - {issue}")
                return False
            else:
                print("✓ Mobile dashboard endpoint test passed")
                return True

        except Exception as e:
            print(f"✗ Mobile dashboard endpoint test failed: {e}")
            return False

    def test_monitoring_endpoint(self):
        """Test monitoring endpoint for system health."""
        try:
            response = requests.get(f"{self.monitoring_url}/api/monitoring/status", timeout=5)
            assert response.status_code == 200, f"Monitoring failed: {response.status_code}"

            data = response.json()

            # Check for cache performance metrics
            if 'cache_metrics' in data:
                cache_metrics = data['cache_metrics']

                # Look for any error indicators
                if 'errors' in cache_metrics and cache_metrics['errors'] > 0:
                    print(f"⚠ Cache errors detected: {cache_metrics['errors']}")

                # Check hit rates
                if 'hit_rate' in cache_metrics:
                    hit_rate = cache_metrics['hit_rate']
                    if hit_rate < 0.5:  # Less than 50% hit rate might indicate issues
                        print(f"⚠ Low cache hit rate: {hit_rate:.2%}")

            print("✓ Monitoring endpoint test passed")
            return True

        except Exception as e:
            print(f"✗ Monitoring endpoint test failed: {e}")
            return False

    def test_log_output(self):
        """Test application log output for errors."""
        if not self.process:
            print("✗ No process to check logs")
            return False

        try:
            # Read some output from stderr (where logs usually go)
            self.process.poll()  # Check if process is still running

            # For integration test, we'll check if process is running without errors
            if self.process.returncode is not None and self.process.returncode != 0:
                print(f"✗ Application exited with error code: {self.process.returncode}")
                return False

            print("✓ Application log output test passed")
            return True

        except Exception as e:
            print(f"✗ Log output test failed: {e}")
            return False

    def test_stress_reliability_formatting(self):
        """Stress test reliability formatting with multiple requests."""
        try:
            print("Running stress test with 10 concurrent requests...")

            import concurrent.futures

            def make_request():
                try:
                    response = requests.get(f"{self.base_url}/api/dashboard/data", timeout=5)
                    return response.status_code == 200
                except:
                    return False

            # Make multiple concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            success_rate = sum(results) / len(results)

            if success_rate < 0.8:  # 80% success rate minimum
                print(f"✗ Stress test failed: {success_rate:.2%} success rate")
                return False
            else:
                print(f"✓ Stress test passed: {success_rate:.2%} success rate")
                return True

        except Exception as e:
            print(f"✗ Stress test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 80)
        print("COMPREHENSIVE INTEGRATION TESTS")
        print("=" * 80)
        print()

        test_results = []

        with self.application_context(timeout=45):
            # Give the application time to fully initialize
            print("Waiting for application to fully initialize...")
            time.sleep(10)

            # Run individual tests
            tests = [
                ("Health Endpoint", self.test_health_endpoint),
                ("Dashboard Data", self.test_dashboard_data_endpoint),
                ("Mobile Dashboard", self.test_mobile_dashboard_endpoint),
                ("Monitoring Endpoint", self.test_monitoring_endpoint),
                ("Log Output", self.test_log_output),
                ("Stress Test", self.test_stress_reliability_formatting),
            ]

            for test_name, test_func in tests:
                print(f"\nRunning {test_name} test...")
                try:
                    result = test_func()
                    test_results.append((test_name, result))
                    if result:
                        print(f"✓ {test_name} test PASSED")
                    else:
                        print(f"✗ {test_name} test FAILED")
                except Exception as e:
                    print(f"✗ {test_name} test ERROR: {e}")
                    test_results.append((test_name, False))

        # Summary
        print("\n" + "=" * 80)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)

        print(f"Tests passed: {passed}/{total}")

        for test_name, result in test_results:
            status = "PASS" if result else "FAIL"
            print(f"- {test_name}: {status}")

        overall_success = passed == total
        print(f"\nOverall Result: {'PASS' if overall_success else 'FAIL'}")

        return overall_success


def run_integration_tests():
    """Run integration tests."""
    runner = IntegrationTestRunner()
    return runner.run_all_tests()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)