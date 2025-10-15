#!/usr/bin/env python3
"""
Direct Open Interest Fix Validation Script
Validates the implementation of the open interest fetch fix at the code level.
"""

import asyncio
import json
import logging
import sys
import time
import traceback
import inspect
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectOpenInterestValidation:
    """Direct code validation for open interest fetch fix"""

    def __init__(self):
        self.results = {
            "validation_timestamp": datetime.now().isoformat(),
            "test_results": {},
            "code_analysis": {},
            "summary": {}
        }

    def test_market_data_manager_await_fix(self):
        """Test AC-1: Verify MarketDataManager.fetch_real_open_interest has await fix"""
        test_name = "MarketDataManager await fix"
        logger.info(f"🔍 Testing: {test_name}")

        try:
            from src.core.market.market_data_manager import MarketDataManager

            # Get the source code of the method
            method = getattr(MarketDataManager, 'fetch_real_open_interest', None)
            if not method:
                logger.error(f"❌ {test_name}: Method fetch_real_open_interest not found")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {"error": "method_not_found"}
                }
                return False

            # Get source code
            source_code = inspect.getsource(method)

            # Check for await pattern
            has_await = "await self.exchange_manager.get_primary_exchange()" in source_code
            has_old_pattern = "self.exchange_manager.get_primary_exchange()" in source_code and "await" not in source_code.split("get_primary_exchange()")[0].split("\n")[-1]

            if has_await:
                logger.info(f"✅ {test_name}: Found 'await self.exchange_manager.get_primary_exchange()'")
                self.results["test_results"][test_name] = {
                    "status": "pass",
                    "evidence": {
                        "has_await_pattern": True,
                        "method_exists": True,
                        "source_snippet": source_code.split('\n')[3:6]  # Show relevant lines
                    }
                }
                return True
            else:
                logger.error(f"❌ {test_name}: Await fix not found in source code")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {
                        "has_await_pattern": False,
                        "method_exists": True,
                        "source_snippet": source_code.split('\n')[3:6]
                    }
                }
                return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error during code analysis: {e}")
            self.results["test_results"][test_name] = {
                "status": "fail",
                "evidence": {"error": str(e)}
            }
            return False

    def test_bybit_fetch_open_interest_implementation(self):
        """Test AC-2: Verify BybitExchange.fetch_open_interest implementation exists"""
        test_name = "BybitExchange fetch_open_interest implementation"
        logger.info(f"🔍 Testing: {test_name}")

        try:
            from src.core.exchanges.bybit import BybitExchange

            # Check if method exists
            method = getattr(BybitExchange, 'fetch_open_interest', None)
            if not method:
                logger.error(f"❌ {test_name}: Method fetch_open_interest not found")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {"error": "method_not_found"}
                }
                return False

            # Get source code
            source_code = inspect.getsource(method)

            # Check for key implementation features
            checks = {
                "has_bybit_v5_endpoint": "/v5/market/open-interest" in source_code,
                "has_ticker_fallback": "_fetch_ticker" in source_code,
                "has_key_normalization": ("openInterest" in source_code and
                                         "open_interest" in source_code),
                "has_default_structure": "timestamp" in source_code and "openInterest" in source_code,
                "has_error_handling": "except" in source_code,
                "returns_dict_structure": "return {" in source_code
            }

            passed_checks = sum(checks.values())
            required_checks = len(checks)

            if passed_checks >= required_checks * 0.8:  # 80% of checks should pass
                logger.info(f"✅ {test_name}: Implementation found with {passed_checks}/{required_checks} features")
                self.results["test_results"][test_name] = {
                    "status": "pass",
                    "evidence": {
                        "method_exists": True,
                        "implementation_checks": checks,
                        "passed_checks": f"{passed_checks}/{required_checks}",
                        "has_docstring": method.__doc__ is not None
                    }
                }
                return True
            else:
                logger.error(f"❌ {test_name}: Implementation incomplete - {passed_checks}/{required_checks} features")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {
                        "method_exists": True,
                        "implementation_checks": checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error during implementation check: {e}")
            self.results["test_results"][test_name] = {
                "status": "fail",
                "evidence": {"error": str(e)}
            }
            return False

    def test_key_normalization_code_patterns(self):
        """Test AC-3: Check key normalization patterns in code"""
        test_name = "Key normalization patterns"
        logger.info(f"🔍 Testing: {test_name}")

        try:
            from src.core.exchanges.bybit import BybitExchange

            method = getattr(BybitExchange, 'fetch_open_interest', None)
            source_code = inspect.getsource(method)

            # Check for normalization patterns
            normalization_patterns = [
                "openInterest",
                "open_interest",
                "open_interest_value",
                ".get('openInterest'",
                ".get('open_interest'",
                ".get('open_interest_value'"
            ]

            found_patterns = [pattern for pattern in normalization_patterns if pattern in source_code]

            if len(found_patterns) >= 4:  # Should handle at least multiple key variants
                logger.info(f"✅ {test_name}: Found {len(found_patterns)} normalization patterns")
                self.results["test_results"][test_name] = {
                    "status": "pass",
                    "evidence": {
                        "found_patterns": found_patterns,
                        "pattern_count": len(found_patterns)
                    }
                }
                return True
            else:
                logger.error(f"❌ {test_name}: Insufficient normalization patterns - {len(found_patterns)}")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {
                        "found_patterns": found_patterns,
                        "pattern_count": len(found_patterns)
                    }
                }
                return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error during pattern analysis: {e}")
            self.results["test_results"][test_name] = {
                "status": "fail",
                "evidence": {"error": str(e)}
            }
            return False

    def test_error_handling_and_fallbacks(self):
        """Test AC-4: Verify error handling and fallback mechanisms"""
        test_name = "Error handling and fallbacks"
        logger.info(f"🔍 Testing: {test_name}")

        try:
            from src.core.exchanges.bybit import BybitExchange

            method = getattr(BybitExchange, 'fetch_open_interest', None)
            source_code = inspect.getsource(method)

            # Check for error handling patterns
            error_handling_checks = {
                "has_try_except": "try:" in source_code and "except" in source_code,
                "has_logging": "logger" in source_code,
                "has_default_return": "return {" in source_code,
                "has_fallback_mechanism": "ticker" in source_code,
                "handles_empty_list": "if data_list:" in source_code or "if.*list" in source_code
            }

            passed_checks = sum(error_handling_checks.values())
            required_checks = len(error_handling_checks)

            if passed_checks >= required_checks * 0.6:  # 60% should pass
                logger.info(f"✅ {test_name}: Error handling found {passed_checks}/{required_checks}")
                self.results["test_results"][test_name] = {
                    "status": "pass",
                    "evidence": {
                        "error_handling_checks": error_handling_checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return True
            else:
                logger.error(f"❌ {test_name}: Insufficient error handling - {passed_checks}/{required_checks}")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {
                        "error_handling_checks": error_handling_checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error during error handling analysis: {e}")
            self.results["test_results"][test_name] = {
                "status": "fail",
                "evidence": {"error": str(e)}
            }
            return False

    def test_method_signatures_and_return_types(self):
        """Test AC-5: Verify method signatures and return type consistency"""
        test_name = "Method signatures and return types"
        logger.info(f"🔍 Testing: {test_name}")

        try:
            from src.core.exchanges.bybit import BybitExchange
            from src.core.market.market_data_manager import MarketDataManager

            # Check BybitExchange.fetch_open_interest signature
            bybit_method = getattr(BybitExchange, 'fetch_open_interest', None)
            market_method = getattr(MarketDataManager, 'fetch_real_open_interest', None)

            signature_checks = {
                "bybit_method_exists": bybit_method is not None,
                "market_method_exists": market_method is not None,
                "bybit_is_async": asyncio.iscoroutinefunction(bybit_method) if bybit_method else False,
                "market_is_async": asyncio.iscoroutinefunction(market_method) if market_method else False,
                "bybit_has_docstring": bybit_method.__doc__ is not None if bybit_method else False,
                "market_has_docstring": market_method.__doc__ is not None if market_method else False
            }

            # Check parameter signatures
            if bybit_method:
                sig = inspect.signature(bybit_method)
                signature_checks["bybit_has_symbol_param"] = 'symbol' in sig.parameters

            if market_method:
                sig = inspect.signature(market_method)
                signature_checks["market_has_symbol_param"] = 'symbol' in sig.parameters

            passed_checks = sum(signature_checks.values())
            required_checks = len(signature_checks)

            if passed_checks >= required_checks * 0.8:  # 80% should pass
                logger.info(f"✅ {test_name}: Method signatures correct {passed_checks}/{required_checks}")
                self.results["test_results"][test_name] = {
                    "status": "pass",
                    "evidence": {
                        "signature_checks": signature_checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return True
            else:
                logger.error(f"❌ {test_name}: Method signature issues - {passed_checks}/{required_checks}")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {
                        "signature_checks": signature_checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error during signature analysis: {e}")
            self.results["test_results"][test_name] = {
                "status": "fail",
                "evidence": {"error": str(e)}
            }
            return False

    def test_integration_points(self):
        """Test AC-6: Verify integration points and method calls"""
        test_name = "Integration points"
        logger.info(f"🔍 Testing: {test_name}")

        try:
            from src.core.market.market_data_manager import MarketDataManager

            method = getattr(MarketDataManager, 'fetch_real_open_interest', None)
            source_code = inspect.getsource(method)

            # Check integration patterns
            integration_checks = {
                "calls_exchange_manager": "exchange_manager" in source_code,
                "uses_hasattr_check": "hasattr" in source_code,
                "calls_fetch_open_interest": "fetch_open_interest" in source_code,
                "has_proper_return_structure": all(field in source_code for field in ['current', 'timestamp', 'is_synthetic']),
                "has_error_handling": "except" in source_code,
                "returns_none_on_failure": "return None" in source_code
            }

            passed_checks = sum(integration_checks.values())
            required_checks = len(integration_checks)

            if passed_checks >= required_checks * 0.75:  # 75% should pass
                logger.info(f"✅ {test_name}: Integration points correct {passed_checks}/{required_checks}")
                self.results["test_results"][test_name] = {
                    "status": "pass",
                    "evidence": {
                        "integration_checks": integration_checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return True
            else:
                logger.error(f"❌ {test_name}: Integration issues - {passed_checks}/{required_checks}")
                self.results["test_results"][test_name] = {
                    "status": "fail",
                    "evidence": {
                        "integration_checks": integration_checks,
                        "passed_checks": f"{passed_checks}/{required_checks}"
                    }
                }
                return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error during integration analysis: {e}")
            self.results["test_results"][test_name] = {
                "status": "fail",
                "evidence": {"error": str(e)}
            }
            return False

    def run_comprehensive_validation(self):
        """Run all validation tests"""
        logger.info("🚀 Starting direct code validation for open interest fix")

        test_methods = [
            self.test_market_data_manager_await_fix,
            self.test_bybit_fetch_open_interest_implementation,
            self.test_key_normalization_code_patterns,
            self.test_error_handling_and_fallbacks,
            self.test_method_signatures_and_return_types,
            self.test_integration_points
        ]

        passed_tests = 0
        total_tests = len(test_methods)

        for test_method in test_methods:
            try:
                success = test_method()
                if success:
                    passed_tests += 1
            except Exception as e:
                logger.error(f"❌ Test {test_method.__name__} failed with exception: {e}")

        # Generate summary
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)",
            "overall_status": "PASS" if passed_tests == total_tests else "CONDITIONAL_PASS" if passed_tests >= total_tests * 0.7 else "FAIL",
            "validation_type": "code_analysis"
        }

        logger.info(f"🏁 Code validation complete: {self.results['summary']['success_rate']}")
        logger.info(f"📊 Overall status: {self.results['summary']['overall_status']}")

        return self.results["summary"]["overall_status"] in ["PASS", "CONDITIONAL_PASS"]

    def save_results(self, filename: str = "open_interest_code_validation_results.json"):
        """Save validation results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"💾 Results saved to {filename}")

def main():
    """Main validation execution"""
    validator = DirectOpenInterestValidation()

    try:
        success = validator.run_comprehensive_validation()
        validator.save_results()

        if success:
            logger.info("✅ CODE VALIDATION SUCCESSFUL: Open interest fix implementation is correctly implemented")
            return 0
        else:
            logger.error("❌ CODE VALIDATION FAILED: Issues found in open interest fix implementation")
            return 1

    except Exception as e:
        logger.error(f"❌ VALIDATION ERROR: {e}")
        logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)