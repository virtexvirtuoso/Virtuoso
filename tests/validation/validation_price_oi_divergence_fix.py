#!/usr/bin/env python3
"""
Comprehensive Validation for Price-OI Divergence Fix
==================================================

This script validates that the fix for Price-OI divergence calculation
is working correctly end-to-end. The fix added open_interest_history
to the orderflow data structure in confluence.py.

Test Areas:
1. Core Functionality - Price-OI divergence calculation with real data
2. Data Flow - From market_data_manager through confluence to orderflow_indicators
3. Integration - Complete orderflow analysis pipeline
4. Error Handling - Edge cases and missing data scenarios
5. Code Quality - Consistency and patterns
"""

import sys
import os
import time
import json
import traceback
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.market.market_data_manager import MarketDataManager
from core.analysis.confluence import ConfluenceAnalyzer
from indicators.orderflow_indicators import OrderflowIndicators
from core.exchanges.manager import ExchangeManager
from monitoring.monitor import Monitor

class PriceOIDivergenceValidator:
    """Comprehensive validator for Price-OI divergence fix."""

    def __init__(self):
        self.results = {
            'core_functionality': {},
            'data_flow': {},
            'integration': {},
            'error_handling': {},
            'code_quality': {},
            'overall_decision': 'pending'
        }
        self.test_start_time = time.time()
        print("=" * 80)
        print("PRICE-OI DIVERGENCE FIX VALIDATION")
        print("=" * 80)

    def log_test(self, category: str, test_name: str, status: str, details: Dict = None):
        """Log test results."""
        if category not in self.results:
            self.results[category] = {}

        self.results[category][test_name] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }

        print(f"[{status.upper()}] {category}.{test_name}")
        if details:
            for key, value in details.items():
                print(f"  {key}: {value}")

    def create_mock_market_data_with_oi(self, include_oi_history: bool = True) -> Dict[str, Any]:
        """Create mock market data with open interest for testing."""
        base_timestamp = int(time.time() * 1000)

        # Create OHLCV DataFrame
        timestamps = [base_timestamp - (i * 60000) for i in range(20, 0, -1)]  # 20 minutes of data
        ohlcv_data = []

        base_price = 50000
        for i, ts in enumerate(timestamps):
            # Create trending price data
            price_trend = base_price + (i * 100)  # Upward trend
            ohlcv_data.append({
                'timestamp': ts,
                'open': price_trend - 50,
                'high': price_trend + 100,
                'low': price_trend - 100,
                'close': price_trend,
                'volume': 1000 + (i * 10)
            })

        ohlcv_df = pd.DataFrame(ohlcv_data)
        ohlcv_df.set_index('timestamp', inplace=True)

        # Create open interest history (opposite trend to price for divergence)
        oi_history = []
        base_oi = 100000

        if include_oi_history:
            for i, ts in enumerate(timestamps):
                # Create downward OI trend (opposite to price)
                oi_value = base_oi - (i * 1000)
                oi_history.append({
                    'timestamp': ts,
                    'value': oi_value
                })

        market_data = {
            'symbol': 'BTCUSDT',
            'exchange': 'bybit',
            'timestamp': base_timestamp,
            'ohlcv': {
                'base': ohlcv_df
            },
            'open_interest': {
                'current': oi_history[-1]['value'] if oi_history else None,
                'previous': oi_history[-2]['value'] if len(oi_history) > 1 else None,
                'history': oi_history
            },
            'open_interest_history': oi_history,  # This is the key fix!
            'trades': [],
            'orderbook': {
                'bids': [[50000, 1.0]],
                'asks': [[50010, 1.0]],
                'timestamp': base_timestamp
            },
            'ticker': {
                'last': 50000,
                'timestamp': base_timestamp
            }
        }

        return market_data

    def test_core_functionality(self):
        """Test 1: Core functionality validation."""
        print("\n" + "=" * 50)
        print("TEST 1: CORE FUNCTIONALITY VALIDATION")
        print("=" * 50)

        try:
            # Test with valid OI data
            market_data = self.create_mock_market_data_with_oi(include_oi_history=True)

            # Initialize orderflow indicators
            orderflow = OrderflowIndicators()

            # Test the fixed function directly
            result = orderflow._calculate_price_oi_divergence(market_data)

            self.log_test('core_functionality', 'price_oi_divergence_with_data',
                         'pass' if result['type'] != 'neutral' else 'fail',
                         {
                             'result_type': result['type'],
                             'result_strength': result.get('strength', 0),
                             'oi_history_count': len(market_data['open_interest_history'])
                         })

            # Test without OI data
            market_data_no_oi = self.create_mock_market_data_with_oi(include_oi_history=False)
            result_no_oi = orderflow._calculate_price_oi_divergence(market_data_no_oi)

            self.log_test('core_functionality', 'price_oi_divergence_without_data',
                         'pass' if result_no_oi['type'] == 'neutral' else 'fail',
                         {
                             'result_type': result_no_oi['type'],
                             'result_strength': result_no_oi.get('strength', 0)
                         })

        except Exception as e:
            self.log_test('core_functionality', 'price_oi_divergence_calculation', 'fail',
                         {'error': str(e), 'traceback': traceback.format_exc()})

    def test_data_flow_validation(self):
        """Test 2: Data flow validation."""
        print("\n" + "=" * 50)
        print("TEST 2: DATA FLOW VALIDATION")
        print("=" * 50)

        try:
            # Test confluence.py _prepare_data_for_orderflow
            from core.analysis.confluence import ConfluenceAnalyzer

            confluence = ConfluenceAnalyzer()
            market_data = self.create_mock_market_data_with_oi(include_oi_history=True)

            # Test the fixed method
            orderflow_data = confluence._prepare_data_for_orderflow(market_data)

            # Verify the fix is applied
            has_oi_history = 'open_interest_history' in orderflow_data
            oi_history_populated = (has_oi_history and
                                   isinstance(orderflow_data['open_interest_history'], list) and
                                   len(orderflow_data['open_interest_history']) > 0)

            self.log_test('data_flow', 'confluence_prepare_orderflow_data',
                         'pass' if has_oi_history else 'fail',
                         {
                             'has_oi_history_field': has_oi_history,
                             'oi_history_populated': oi_history_populated,
                             'oi_history_count': len(orderflow_data.get('open_interest_history', []))
                         })

            # Test that the data structure matches what orderflow_indicators expects
            orderflow = OrderflowIndicators()
            result = orderflow._calculate_price_oi_divergence(orderflow_data)

            self.log_test('data_flow', 'orderflow_receives_proper_data',
                         'pass' if result['type'] != 'neutral' else 'fail',
                         {
                             'divergence_calculated': result['type'] != 'neutral',
                             'result_type': result['type']
                         })

        except Exception as e:
            self.log_test('data_flow', 'data_flow_validation', 'fail',
                         {'error': str(e), 'traceback': traceback.format_exc()})

    def test_integration_pipeline(self):
        """Test 3: Integration testing."""
        print("\n" + "=" * 50)
        print("TEST 3: INTEGRATION TESTING")
        print("=" * 50)

        try:
            # Test complete orderflow analysis pipeline
            confluence = ConfluenceAnalyzer()
            market_data = self.create_mock_market_data_with_oi(include_oi_history=True)

            # Run complete orderflow analysis
            orderflow_results = confluence.analyze_indicators(market_data, ['orderflow'])

            # Check if Price-OI divergence was calculated
            has_orderflow = 'orderflow' in orderflow_results
            has_divergences = (has_orderflow and
                             'divergences' in orderflow_results['orderflow'] and
                             'price_oi' in orderflow_results['orderflow']['divergences'])

            price_oi_result = None
            if has_divergences:
                price_oi_result = orderflow_results['orderflow']['divergences']['price_oi']

            self.log_test('integration', 'complete_orderflow_pipeline',
                         'pass' if has_divergences and price_oi_result['type'] != 'neutral' else 'fail',
                         {
                             'has_orderflow_results': has_orderflow,
                             'has_divergences': has_divergences,
                             'price_oi_calculated': price_oi_result is not None,
                             'price_oi_type': price_oi_result['type'] if price_oi_result else 'none'
                         })

            # Test that other orderflow indicators still work (regression check)
            has_other_indicators = (has_orderflow and
                                  any(key in orderflow_results['orderflow']
                                      for key in ['cvd', 'smart_money_flow', 'liquidity_flow']))

            self.log_test('integration', 'other_orderflow_indicators',
                         'pass' if has_other_indicators else 'fail',
                         {
                             'other_indicators_working': has_other_indicators,
                             'available_indicators': list(orderflow_results.get('orderflow', {}).keys())
                         })

        except Exception as e:
            self.log_test('integration', 'integration_pipeline', 'fail',
                         {'error': str(e), 'traceback': traceback.format_exc()})

    def test_error_handling(self):
        """Test 4: Error handling and edge cases."""
        print("\n" + "=" * 50)
        print("TEST 4: ERROR HANDLING & EDGE CASES")
        print("=" * 50)

        try:
            orderflow = OrderflowIndicators()

            # Test case 1: Empty market data
            empty_data = {}
            result1 = orderflow._calculate_price_oi_divergence(empty_data)

            self.log_test('error_handling', 'empty_market_data',
                         'pass' if result1['type'] == 'neutral' else 'fail',
                         {'result': result1})

            # Test case 2: Malformed OI history
            malformed_data = self.create_mock_market_data_with_oi(include_oi_history=True)
            malformed_data['open_interest_history'] = "invalid_data"
            result2 = orderflow._calculate_price_oi_divergence(malformed_data)

            self.log_test('error_handling', 'malformed_oi_history',
                         'pass' if result2['type'] == 'neutral' else 'fail',
                         {'result': result2})

            # Test case 3: Insufficient OI history
            insufficient_data = self.create_mock_market_data_with_oi(include_oi_history=True)
            insufficient_data['open_interest_history'] = [{'timestamp': int(time.time()*1000), 'value': 100}]
            result3 = orderflow._calculate_price_oi_divergence(insufficient_data)

            self.log_test('error_handling', 'insufficient_oi_history',
                         'pass' if result3['type'] == 'neutral' else 'fail',
                         {'result': result3})

            # Test case 4: Missing OHLCV data
            no_ohlcv_data = self.create_mock_market_data_with_oi(include_oi_history=True)
            del no_ohlcv_data['ohlcv']
            result4 = orderflow._calculate_price_oi_divergence(no_ohlcv_data)

            self.log_test('error_handling', 'missing_ohlcv_data',
                         'pass' if result4['type'] == 'neutral' else 'fail',
                         {'result': result4})

        except Exception as e:
            self.log_test('error_handling', 'error_handling_tests', 'fail',
                         {'error': str(e), 'traceback': traceback.format_exc()})

    def test_code_quality(self):
        """Test 5: Code quality and consistency."""
        print("\n" + "=" * 50)
        print("TEST 5: CODE QUALITY & CONSISTENCY")
        print("=" * 50)

        try:
            # Check that both occurrences of _prepare_data_for_orderflow have the fix
            with open('src/core/analysis/confluence.py', 'r') as f:
                content = f.read()

            # Count occurrences of the fix
            fix_count = content.count("'open_interest_history': market_data.get('open_interest_history', [])")
            method_count = content.count("def _prepare_data_for_orderflow")

            self.log_test('code_quality', 'fix_applied_consistently',
                         'pass' if fix_count == method_count and fix_count >= 2 else 'fail',
                         {
                             'fix_occurrences': fix_count,
                             'method_occurrences': method_count,
                             'consistent_application': fix_count == method_count
                         })

            # Check for consistent variable naming
            has_consistent_naming = "'open_interest_history'" in content

            self.log_test('code_quality', 'consistent_variable_naming',
                         'pass' if has_consistent_naming else 'fail',
                         {'consistent_naming': has_consistent_naming})

            # Check that no dead code was introduced
            # Look for unused imports or variables (basic check)
            lines = content.split('\n')
            suspicious_lines = [line for line in lines if 'TODO' in line or 'FIXME' in line or 'DEBUG' in line.upper()]

            self.log_test('code_quality', 'no_dead_code_introduced',
                         'pass' if len(suspicious_lines) == 0 else 'warning',
                         {'suspicious_lines_count': len(suspicious_lines)})

        except Exception as e:
            self.log_test('code_quality', 'code_quality_analysis', 'fail',
                         {'error': str(e), 'traceback': traceback.format_exc()})

    def generate_report(self):
        """Generate comprehensive validation report."""
        print("\n" + "=" * 80)
        print("VALIDATION REPORT")
        print("=" * 80)

        # Calculate overall status
        all_tests = []
        for category, tests in self.results.items():
            if category != 'overall_decision':
                for test_name, test_data in tests.items():
                    all_tests.append(test_data['status'])

        passed_tests = sum(1 for status in all_tests if status == 'pass')
        failed_tests = sum(1 for status in all_tests if status == 'fail')
        warning_tests = sum(1 for status in all_tests if status == 'warning')
        total_tests = len(all_tests)

        # Determine overall decision
        if failed_tests == 0 and passed_tests > 0:
            if warning_tests == 0:
                overall_decision = 'pass'
            else:
                overall_decision = 'conditional_pass'
        else:
            overall_decision = 'fail'

        self.results['overall_decision'] = overall_decision

        print(f"Test Summary:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Warnings: {warning_tests}")
        print(f"  Overall Decision: {overall_decision.upper()}")

        print(f"\nExecution Time: {time.time() - self.test_start_time:.2f} seconds")

        # Detailed results
        print(f"\nDetailed Results:")
        for category, tests in self.results.items():
            if category != 'overall_decision':
                print(f"\n{category.upper().replace('_', ' ')}:")
                for test_name, test_data in tests.items():
                    status_symbol = "✓" if test_data['status'] == 'pass' else "✗" if test_data['status'] == 'fail' else "⚠"
                    print(f"  {status_symbol} {test_name}: {test_data['status']}")
                    if test_data.get('details'):
                        for key, value in test_data['details'].items():
                            print(f"    {key}: {value}")

        # Save results to file
        with open('price_oi_divergence_validation_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nDetailed results saved to: price_oi_divergence_validation_results.json")

        return overall_decision

def main():
    """Main validation execution."""
    validator = PriceOIDivergenceValidator()

    # Run all validation tests
    validator.test_core_functionality()
    validator.test_data_flow_validation()
    validator.test_integration_pipeline()
    validator.test_error_handling()
    validator.test_code_quality()

    # Generate final report
    overall_decision = validator.generate_report()

    print("\n" + "=" * 80)
    print("VALIDATION CONCLUSION")
    print("=" * 80)

    if overall_decision == 'pass':
        print("✓ VALIDATION PASSED")
        print("The Price-OI divergence fix is working correctly.")
        print("All tests passed without issues.")
    elif overall_decision == 'conditional_pass':
        print("⚠ CONDITIONAL PASS")
        print("The Price-OI divergence fix is working correctly.")
        print("Some warnings were found but no critical issues.")
    else:
        print("✗ VALIDATION FAILED")
        print("The Price-OI divergence fix has issues that need to be addressed.")

    return 0 if overall_decision in ['pass', 'conditional_pass'] else 1

if __name__ == "__main__":
    sys.exit(main())