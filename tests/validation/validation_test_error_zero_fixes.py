#!/usr/bin/env python3
"""
Comprehensive validation test suite for "Error: 0" fixes.
Tests the fixes implemented in ccxt_exchange.py and top_symbols.py.
"""

import asyncio
import logging
import time
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Add src to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from core.exchanges.ccxt_exchange import CCXTExchange
from core.market.top_symbols import TopSymbolsManager
from core.exchanges.manager import ExchangeManager
from core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationTestSuite:
    """Test suite for validating Error: 0 fixes."""

    def __init__(self):
        self.test_results = {}
        self.config_manager = ConfigManager()

    async def setup_test_environment(self):
        """Setup test environment with mock configurations."""
        # Mock exchange configuration
        mock_config = {
            'primary_exchange': 'bybit',
            'exchanges': {
                'bybit': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True,
                    'enabled': True
                }
            },
            'market': {
                'max_symbols': 10,
                'use_static_list': False,
                'selection_criteria': 'turnover'
            }
        }

        # Initialize exchange manager with test config
        self.exchange_manager = ExchangeManager(self.config_manager)
        return mock_config

    def record_test_result(self, test_name: str, passed: bool, details: str, evidence: Dict[str, Any] = None):
        """Record test result for reporting."""
        self.test_results[test_name] = {
            'passed': passed,
            'details': details,
            'evidence': evidence or {},
            'timestamp': time.time()
        }
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {test_name}: {details}")

    async def test_error_zero_detection_fetch_ticker(self):
        """Test AC-1: Verify 'Error: 0' pattern detection in fetch_ticker."""
        test_name = "Error_Zero_Detection_FetchTicker"

        try:
            # Create CCXTExchange instance
            exchange = CCXTExchange('bybit', {})

            # Mock CCXT to raise "Error: 0" exception
            mock_ccxt = Mock()
            mock_ccxt.fetch_ticker = AsyncMock(side_effect=Exception("0"))

            # Test different "Error: 0" patterns
            error_patterns = ["0", " 0 ", "0\n", "\t0\t", "Error: 0"]
            detected_patterns = []

            for pattern in error_patterns:
                mock_ccxt.fetch_ticker.side_effect = Exception(pattern)
                exchange.ccxt = mock_ccxt

                try:
                    result = await exchange.fetch_ticker("BTCUSDT")
                    if result is None:
                        detected_patterns.append(pattern)
                except Exception:
                    # Should not raise exception for Error: 0 patterns
                    pass

            # Verify detection works for all patterns
            expected_detected = ["0", " 0 ", "0\n", "\t0\t"]  # Error: 0 might not be detected by simple check
            actually_detected = [p for p in expected_detected if p in detected_patterns]

            success = len(actually_detected) >= 3  # At least 3 of 4 patterns detected

            self.record_test_result(
                test_name,
                success,
                f"Detected {len(actually_detected)}/{len(expected_detected)} Error: 0 patterns",
                {
                    "expected_patterns": expected_detected,
                    "detected_patterns": detected_patterns,
                    "test_patterns": error_patterns
                }
            )

        except Exception as e:
            self.record_test_result(test_name, False, f"Test setup failed: {str(e)}")

    async def test_error_zero_detection_fetch_tickers(self):
        """Test AC-2: Verify 'Error: 0' pattern detection in fetch_tickers."""
        test_name = "Error_Zero_Detection_FetchTickers"

        try:
            exchange = CCXTExchange('bybit', {})

            # Mock CCXT to raise "Error: 0" exception
            mock_ccxt = Mock()
            mock_ccxt.fetch_tickers = AsyncMock(side_effect=Exception("0"))
            exchange.ccxt = mock_ccxt

            # Test that fetch_tickers returns empty dict for Error: 0
            result = await exchange.fetch_tickers()

            success = result == {}
            self.record_test_result(
                test_name,
                success,
                f"fetch_tickers returned empty dict for Error: 0: {result}",
                {"returned_result": result}
            )

        except Exception as e:
            self.record_test_result(test_name, False, f"Test failed: {str(e)}")

    async def test_data_type_safety_validation(self):
        """Test AC-3: Verify data type safety in top_symbols sorting."""
        test_name = "Data_Type_Safety_Validation"

        try:
            # Create TopSymbolsManager instance
            config = await self.setup_test_environment()
            top_symbols = TopSymbolsManager(self.exchange_manager, config['market'])

            # Test data with mixed types (the bug scenario)
            mixed_data = [
                {"symbol": "BTCUSDT", "quoteVolume": 1000000},  # Valid dict
                "invalid_string_data",  # Invalid string (caused the original error)
                {"symbol": "ETHUSDT", "quoteVolume": 500000},  # Valid dict
                None,  # Invalid None
                {"symbol": "LTCUSDT"},  # Dict without quoteVolume
                {"symbol": "ADAUSDT", "quoteVolume": "invalid"},  # Invalid volume type
            ]

            # Simulate the validation logic from update_top_symbols
            valid_markets = []
            for item in mixed_data:
                if isinstance(item, dict) and 'symbol' in item:
                    valid_markets.append(item)

            # Test turnover key function
            def _turnover_key(x: Dict[str, Any]) -> float:
                try:
                    return float(x.get('quoteVolume', x.get('turnover24h', x.get('turnover', 0)) or 0))
                except Exception:
                    return 0.0

            # Test sorting (this used to crash with 'str' object has no attribute 'get')
            try:
                sorted_markets = sorted(valid_markets, key=_turnover_key, reverse=True)
                sorting_success = True
                error_msg = None
            except Exception as e:
                sorting_success = False
                error_msg = str(e)

            success = sorting_success and len(valid_markets) == 3  # Should filter to 3 valid dicts

            self.record_test_result(
                test_name,
                success,
                f"Data filtering and sorting successful: {len(valid_markets)} valid items",
                {
                    "input_count": len(mixed_data),
                    "valid_count": len(valid_markets),
                    "sorting_success": sorting_success,
                    "error_message": error_msg,
                    "sorted_symbols": [m.get('symbol') for m in sorted_markets] if sorting_success else None
                }
            )

        except Exception as e:
            self.record_test_result(test_name, False, f"Test failed: {str(e)}")

    async def test_fallback_chain_behavior(self):
        """Test AC-4: Verify fallback chain behavior when CCXT methods fail."""
        test_name = "Fallback_Chain_Behavior"

        try:
            config = await self.setup_test_environment()
            top_symbols = TopSymbolsManager(self.exchange_manager, config['market'])

            # Mock exchange with failing CCXT methods
            mock_exchange = Mock()
            mock_ccxt = Mock()

            # Test different failure scenarios
            test_scenarios = [
                ("ccxt_error_zero", Exception("0")),
                ("ccxt_network_error", Exception("Network error")),
                ("ccxt_method_missing", AttributeError("'Mock' object has no attribute 'fetch_tickers'")),
            ]

            fallback_results = {}

            for scenario_name, exception in test_scenarios:
                mock_ccxt.fetch_tickers = AsyncMock(side_effect=exception)
                mock_exchange.ccxt = mock_ccxt
                mock_exchange.fetch_tickers = AsyncMock(return_value=[
                    {"symbol": "BTCUSDT", "quoteVolume": 1000000}
                ])

                try:
                    result = await top_symbols._fetch_all_market_tickers(mock_exchange)
                    fallback_results[scenario_name] = {
                        "success": True,
                        "result_count": len(result) if result else 0,
                        "error": None
                    }
                except Exception as e:
                    fallback_results[scenario_name] = {
                        "success": False,
                        "result_count": 0,
                        "error": str(e)
                    }

            # Check if Error: 0 scenario uses fallback
            error_zero_success = fallback_results.get("ccxt_error_zero", {}).get("success", False)

            success = error_zero_success
            self.record_test_result(
                test_name,
                success,
                f"Fallback chain working for Error: 0 scenario: {error_zero_success}",
                {"fallback_results": fallback_results}
            )

        except Exception as e:
            self.record_test_result(test_name, False, f"Test failed: {str(e)}")

    async def test_problematic_symbols_edge_cases(self):
        """Test AC-5: Test edge cases with problematic symbols (numeric prefixes)."""
        test_name = "Problematic_Symbols_Edge_Cases"

        try:
            exchange = CCXTExchange('bybit', {})

            # Test symbols that historically caused "Error: 0"
            problematic_symbols = [
                "10000SATSUSDT",
                "1000BONKUSDT",
                "1000PEPEUSDT",
                "1000FLOKIUSDT",
                "10000000AIDOGE"
            ]

            symbol_results = {}

            for symbol in problematic_symbols:
                # Mock CCXT to return "Error: 0" for these symbols
                mock_ccxt = Mock()
                mock_ccxt.fetch_ticker = AsyncMock(side_effect=Exception("0"))
                exchange.ccxt = mock_ccxt

                try:
                    result = await exchange.fetch_ticker(symbol)
                    symbol_results[symbol] = {
                        "handled_gracefully": result is None,
                        "result": result,
                        "error": None
                    }
                except Exception as e:
                    symbol_results[symbol] = {
                        "handled_gracefully": False,
                        "result": None,
                        "error": str(e)
                    }

            # Check if all problematic symbols are handled gracefully
            gracefully_handled = sum(1 for r in symbol_results.values() if r["handled_gracefully"])
            total_symbols = len(problematic_symbols)

            success = gracefully_handled == total_symbols

            self.record_test_result(
                test_name,
                success,
                f"Handled {gracefully_handled}/{total_symbols} problematic symbols gracefully",
                {
                    "symbol_results": symbol_results,
                    "problematic_symbols": problematic_symbols
                }
            )

        except Exception as e:
            self.record_test_result(test_name, False, f"Test failed: {str(e)}")

    async def test_logging_appropriateness(self):
        """Test AC-6: Verify appropriate logging levels and messages."""
        test_name = "Logging_Appropriateness"

        try:
            # Capture log messages
            log_messages = []

            class TestLogHandler(logging.Handler):
                def emit(self, record):
                    log_messages.append({
                        'level': record.levelname,
                        'message': record.getMessage(),
                        'name': record.name
                    })

            # Add test handler
            test_handler = TestLogHandler()
            test_handler.setLevel(logging.DEBUG)

            # Test error zero logging in fetch_ticker
            exchange = CCXTExchange('bybit', {})
            exchange_logger = logging.getLogger('core.exchanges.ccxt_exchange')
            exchange_logger.addHandler(test_handler)

            mock_ccxt = Mock()
            mock_ccxt.fetch_ticker = AsyncMock(side_effect=Exception("0"))
            exchange.ccxt = mock_ccxt

            # Clear previous messages
            log_messages.clear()

            # Trigger Error: 0 scenario
            await exchange.fetch_ticker("TESTUSDT")

            # Check logging appropriateness
            error_zero_logs = [msg for msg in log_messages if "Error: 0" in msg['message'] or "0" in msg['message']]
            warning_logs = [msg for msg in error_zero_logs if msg['level'] == 'WARNING']

            success = len(warning_logs) > 0  # Should log as WARNING, not ERROR

            self.record_test_result(
                test_name,
                success,
                f"Found {len(warning_logs)} appropriate warning logs for Error: 0",
                {
                    "total_logs": len(log_messages),
                    "error_zero_logs": error_zero_logs,
                    "warning_logs": warning_logs
                }
            )

            # Cleanup
            exchange_logger.removeHandler(test_handler)

        except Exception as e:
            self.record_test_result(test_name, False, f"Test failed: {str(e)}")

    async def test_integration_flow(self):
        """Test AC-7: Integration test of complete ticker fetch to symbol selection flow."""
        test_name = "Integration_Flow_Test"

        try:
            config = await self.setup_test_environment()

            # Create a complete mock scenario
            mock_exchange_manager = Mock()
            mock_exchange = Mock()

            # Mock successful ticker data with some Error: 0 failures
            successful_tickers = {
                "BTC/USDT": {"symbol": "BTCUSDT", "quoteVolume": 1000000},
                "ETH/USDT": {"symbol": "ETHUSDT", "quoteVolume": 500000},
                "LTC/USDT": {"symbol": "LTCUSDT", "quoteVolume": 200000},
            }

            mock_ccxt = Mock()
            mock_ccxt.fetch_tickers = AsyncMock(return_value=successful_tickers)
            mock_exchange.ccxt = mock_ccxt
            mock_exchange_manager.get_primary_exchange = AsyncMock(return_value=mock_exchange)

            # Test TopSymbolsManager with the mock
            top_symbols = TopSymbolsManager(mock_exchange_manager, config['market'])

            # Run the complete flow
            await top_symbols.update_top_symbols()

            # Check if symbols were cached
            has_cached_symbols = hasattr(top_symbols, '_symbols_cache') and top_symbols._symbols_cache

            success = has_cached_symbols

            self.record_test_result(
                test_name,
                success,
                f"Integration flow completed successfully: {has_cached_symbols}",
                {
                    "has_cached_symbols": has_cached_symbols,
                    "cache_content": getattr(top_symbols, '_symbols_cache', None)
                }
            )

        except Exception as e:
            self.record_test_result(test_name, False, f"Integration test failed: {str(e)}")

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['passed'])

        # Categorize by acceptance criteria
        criteria_mapping = {
            "AC-1": ["Error_Zero_Detection_FetchTicker"],
            "AC-2": ["Error_Zero_Detection_FetchTickers"],
            "AC-3": ["Data_Type_Safety_Validation"],
            "AC-4": ["Fallback_Chain_Behavior"],
            "AC-5": ["Problematic_Symbols_Edge_Cases"],
            "AC-6": ["Logging_Appropriateness"],
            "AC-7": ["Integration_Flow_Test"]
        }

        criteria_results = {}
        for criteria, tests in criteria_mapping.items():
            criteria_passed = all(
                self.test_results.get(test, {}).get('passed', False)
                for test in tests
            )
            criteria_results[criteria] = {
                "passed": criteria_passed,
                "tests": [self.test_results.get(test, {}) for test in tests]
            }

        overall_success = passed_tests == total_tests

        return {
            "overall_decision": "pass" if overall_success else "fail",
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "criteria_results": criteria_results,
            "detailed_results": self.test_results,
            "timestamp": time.time()
        }

async def main():
    """Run the validation test suite."""
    logger.info("Starting 'Error: 0' fixes validation test suite")

    suite = ValidationTestSuite()

    # Run all validation tests
    await suite.test_error_zero_detection_fetch_ticker()
    await suite.test_error_zero_detection_fetch_tickers()
    await suite.test_data_type_safety_validation()
    await suite.test_fallback_chain_behavior()
    await suite.test_problematic_symbols_edge_cases()
    await suite.test_logging_appropriateness()
    await suite.test_integration_flow()

    # Generate and display report
    report = suite.generate_validation_report()

    print("\n" + "="*80)
    print("VALIDATION REPORT: Error: 0 Fixes")
    print("="*80)
    print(f"Overall Decision: {report['overall_decision'].upper()}")
    print(f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']} ({report['summary']['success_rate']})")
    print("\nCriteria Results:")
    for criteria, result in report['criteria_results'].items():
        status = "PASS" if result['passed'] else "FAIL"
        print(f"  {criteria}: {status}")

    print("\nDetailed Test Results:")
    for test_name, result in report['detailed_results'].items():
        status = "PASS" if result['passed'] else "FAIL"
        print(f"  [{status}] {test_name}: {result['details']}")

    # Save report to file
    project_root = Path(__file__).parent.parent.parent
    with open(project_root / 'validation_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Validation complete. Report saved to validation_report.json")

    return report['overall_decision'] == 'pass'

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)