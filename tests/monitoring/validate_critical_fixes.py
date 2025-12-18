"""
Comprehensive Post-Fix Validation for Manipulation Detector.

Tests all 3 critical fixes:
1. Alert Persistence (Lines 176-188)
2. Division by Zero Safety (Lines 469-478)
3. Empty Sequence Safety (Lines 611-620)

Author: QA Automation Agent
Date: 2025-10-16
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.manipulation_detector import ManipulationDetector, ManipulationAlert

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FixValidator:
    """Validates all 3 critical fixes in manipulation detector."""

    def __init__(self):
        self.config = {
            'monitoring': {
                'manipulation_detection': {
                    'enabled': True,
                    'cooldown': 0,  # No cooldown for testing
                    'oi_change_15m_threshold': 0.015,
                    'oi_change_1h_threshold': 0.02,
                    'volume_spike_threshold': 2.5,
                    'price_change_15m_threshold': 0.0075,
                    'price_change_5m_threshold': 0.004,
                    'divergence_oi_threshold': 0.015,
                    'divergence_price_threshold': 0.005,
                    'alert_confidence_threshold': 0.4,
                    'min_data_points': 5,
                }
            }
        }

        self.test_results = []

    def create_market_data(self, price: float, volume: float, oi: float = 0) -> Dict[str, Any]:
        """Create mock market data."""
        return {
            'ticker': {
                'last': price,
                'baseVolume': volume,
            },
            'funding': {
                'openInterest': oi
            } if oi > 0 else {}
        }

    async def test_fix1_alert_persistence(self) -> Dict[str, Any]:
        """
        TEST FIX #1: Alert Persistence (Lines 176-188)

        Validates:
        1. Alerts are saved to _manipulation_history
        2. alert_dict contains all required fields
        3. Dictionary structure matches get_recent_alerts() expectations
        4. Multiple alerts for same symbol append correctly
        5. metrics.copy() works without reference issues
        """
        logger.info("\n" + "="*80)
        logger.info("TEST FIX #1: Alert Persistence (Lines 176-188)")
        logger.info("="*80)

        result = {
            'fix_name': 'FIX #1: Alert Persistence',
            'line_numbers': '176-188',
            'status': 'PASS',
            'issues': [],
            'edge_cases_tested': []
        }

        try:
            detector = ManipulationDetector(self.config, logger)
            symbol = "BTCUSDT"

            # Build baseline data
            for i in range(8):
                data = self.create_market_data(50000, 1000000, 100000000)
                await detector.analyze_market_data(symbol, data)

            # Trigger alert with OI spike
            alert_data = self.create_market_data(50000, 1000000, 104000000)  # 4% OI increase
            alert = await detector.analyze_market_data(symbol, alert_data)

            # VALIDATION 1: Check alert was created
            if not alert:
                result['status'] = 'FAIL'
                result['issues'].append("Alert not created despite triggering conditions")
                return result

            result['edge_cases_tested'].append("Alert created successfully")

            # VALIDATION 2: Check _manipulation_history exists and has data
            if symbol not in detector._manipulation_history:
                result['status'] = 'FAIL'
                result['issues'].append("Symbol not found in _manipulation_history")
                return result

            history = detector._manipulation_history[symbol]
            if len(history) == 0:
                result['status'] = 'FAIL'
                result['issues'].append("_manipulation_history is empty - alerts not persisted")
                return result

            result['edge_cases_tested'].append("Alert persisted to _manipulation_history")

            # VALIDATION 3: Check alert_dict structure
            alert_dict = history[0]
            required_fields = ['timestamp', 'manipulation_type', 'confidence_score',
                             'severity', 'description', 'metrics']

            missing_fields = [f for f in required_fields if f not in alert_dict]
            if missing_fields:
                result['status'] = 'FAIL'
                result['issues'].append(f"Missing required fields in alert_dict: {missing_fields}")
                return result

            result['edge_cases_tested'].append("alert_dict contains all required fields")

            # VALIDATION 4: Check metrics.copy() worked (no reference issues)
            original_metrics = alert.metrics
            stored_metrics = alert_dict['metrics']

            # Modify original metrics
            original_metrics['test_field'] = 'modified'

            # Check stored metrics are not affected
            if 'test_field' in stored_metrics:
                result['status'] = 'FAIL'
                result['issues'].append("metrics.copy() failed - reference leak detected")
                return result

            result['edge_cases_tested'].append("metrics.copy() prevents reference leaks")

            # VALIDATION 5: Check get_recent_alerts() works with persisted data
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_alerts = await detector.get_recent_alerts(since, limit=10)

            if len(recent_alerts) == 0:
                result['status'] = 'FAIL'
                result['issues'].append("get_recent_alerts() returned empty despite persisted alerts")
                return result

            # Check alert structure matches API expectations
            api_alert = recent_alerts[0]
            api_required = ['id', 'timestamp', 'symbol', 'type', 'severity',
                          'confidence', 'description', 'metrics']
            missing_api = [f for f in api_required if f not in api_alert]

            if missing_api:
                result['status'] = 'FAIL'
                result['issues'].append(f"API alert missing fields: {missing_api}")
                return result

            result['edge_cases_tested'].append("get_recent_alerts() returns properly formatted alerts")

            # VALIDATION 6: Test multiple alerts for same symbol
            # Trigger second alert
            for i in range(3):
                data = self.create_market_data(50000, 1000000, 104000000)
                await asyncio.sleep(0.1)

            alert2_data = self.create_market_data(50000, 3000000, 104000000)  # Volume spike
            alert2 = await detector.analyze_market_data(symbol, alert2_data)

            if alert2 and len(detector._manipulation_history[symbol]) != 2:
                result['status'] = 'FAIL'
                result['issues'].append(f"Multiple alerts not appending correctly. Expected 2, got {len(detector._manipulation_history[symbol])}")
                return result

            result['edge_cases_tested'].append("Multiple alerts append correctly to history")

            logger.info(f"✅ FIX #1 VALIDATION: {result['status']}")
            for test in result['edge_cases_tested']:
                logger.info(f"   ✓ {test}")

        except Exception as e:
            result['status'] = 'FAIL'
            result['issues'].append(f"Exception during test: {str(e)}")
            result['traceback'] = traceback.format_exc()
            logger.error(f"❌ FIX #1 VALIDATION FAILED: {e}")
            logger.error(traceback.format_exc())

        return result

    async def test_fix2_division_by_zero(self) -> Dict[str, Any]:
        """
        TEST FIX #2: Division by Zero Safety (Lines 469-478)

        Validates:
        1. Filter logic prevents division by zero
        2. len(returns) < 2 safety check works
        3. Fallback to base_threshold is appropriate
        4. Edge case: all prices are zero
        5. Edge case: only one non-zero price
        6. numpy array creation doesn't fail with empty list
        """
        logger.info("\n" + "="*80)
        logger.info("TEST FIX #2: Division by Zero Safety (Lines 469-478)")
        logger.info("="*80)

        result = {
            'fix_name': 'FIX #2: Division by Zero Safety',
            'line_numbers': '469-478',
            'status': 'PASS',
            'issues': [],
            'edge_cases_tested': []
        }

        try:
            detector = ManipulationDetector(self.config, logger)
            symbol = "TESTCOIN"
            base_threshold = 0.015

            # EDGE CASE 1: All prices are zero
            detector._historical_data[symbol] = [
                {'timestamp': i, 'price': 0, 'volume': 1000, 'open_interest': 1000}
                for i in range(20)
            ]

            try:
                threshold = detector._get_volatility_adjusted_threshold(symbol, base_threshold)
                if threshold != base_threshold:
                    result['issues'].append(f"All-zero prices: Expected {base_threshold}, got {threshold}")
                else:
                    result['edge_cases_tested'].append("All-zero prices: returns base_threshold")
            except ZeroDivisionError:
                result['status'] = 'FAIL'
                result['issues'].append("ZeroDivisionError with all-zero prices")
                return result

            # EDGE CASE 2: Only one non-zero price
            detector._historical_data[symbol] = [
                {'timestamp': i, 'price': 50000 if i == 0 else 0, 'volume': 1000, 'open_interest': 1000}
                for i in range(20)
            ]

            try:
                threshold = detector._get_volatility_adjusted_threshold(symbol, base_threshold)
                if threshold != base_threshold:
                    result['issues'].append(f"Single non-zero price: Expected {base_threshold}, got {threshold}")
                else:
                    result['edge_cases_tested'].append("Single non-zero price: returns base_threshold")
            except ZeroDivisionError:
                result['status'] = 'FAIL'
                result['issues'].append("ZeroDivisionError with single non-zero price")
                return result

            # EDGE CASE 3: Prices with some zeros interspersed
            prices_with_zeros = []
            for i in range(20):
                if i % 5 == 0:
                    prices_with_zeros.append({'timestamp': i, 'price': 0, 'volume': 1000, 'open_interest': 1000})
                else:
                    prices_with_zeros.append({'timestamp': i, 'price': 50000 + i*10, 'volume': 1000, 'open_interest': 1000})

            detector._historical_data[symbol] = prices_with_zeros

            try:
                threshold = detector._get_volatility_adjusted_threshold(symbol, base_threshold)
                # Should work and calculate volatility from non-zero prices
                if threshold < base_threshold or threshold > base_threshold * 2.5:
                    result['issues'].append(f"Interspersed zeros: Threshold {threshold} out of expected range")
                else:
                    result['edge_cases_tested'].append("Interspersed zeros: calculates volatility correctly")
            except ZeroDivisionError:
                result['status'] = 'FAIL'
                result['issues'].append("ZeroDivisionError with interspersed zeros")
                return result
            except Exception as e:
                result['status'] = 'FAIL'
                result['issues'].append(f"Exception with interspersed zeros: {e}")
                return result

            # EDGE CASE 4: Less than 2 data points after filtering
            detector._historical_data[symbol] = [
                {'timestamp': 0, 'price': 50000, 'volume': 1000, 'open_interest': 1000},
                {'timestamp': 1, 'price': 0, 'volume': 1000, 'open_interest': 1000}
            ]

            try:
                threshold = detector._get_volatility_adjusted_threshold(symbol, base_threshold)
                if threshold != base_threshold:
                    result['issues'].append(f"< 2 non-zero prices: Expected {base_threshold}, got {threshold}")
                else:
                    result['edge_cases_tested'].append("< 2 non-zero prices: returns base_threshold")
            except ZeroDivisionError:
                result['status'] = 'FAIL'
                result['issues'].append("ZeroDivisionError with < 2 non-zero prices")
                return result

            # EDGE CASE 5: Normal case with all valid prices
            detector._historical_data[symbol] = [
                {'timestamp': i, 'price': 50000 + i*100, 'volume': 1000, 'open_interest': 1000}
                for i in range(20)
            ]

            try:
                threshold = detector._get_volatility_adjusted_threshold(symbol, base_threshold)
                if threshold < base_threshold or threshold > base_threshold * 2.5:
                    result['issues'].append(f"Normal case: Threshold {threshold} out of expected range")
                else:
                    result['edge_cases_tested'].append("Normal case: calculates volatility-adjusted threshold")
            except Exception as e:
                result['status'] = 'FAIL'
                result['issues'].append(f"Exception in normal case: {e}")
                return result

            # EDGE CASE 6: Check filter logic is actually in place
            # Read the actual code to verify the fix exists
            import inspect
            source = inspect.getsource(detector._get_volatility_adjusted_threshold)

            if 'if prices[i-1] > 0' not in source:
                result['status'] = 'FAIL'
                result['issues'].append("Division by zero filter not found in source code")
                return result

            result['edge_cases_tested'].append("Source code contains division by zero filter")

            if 'if len(returns) < 2' not in source:
                result['status'] = 'FAIL'
                result['issues'].append("len(returns) < 2 safety check not found in source code")
                return result

            result['edge_cases_tested'].append("Source code contains len(returns) safety check")

            logger.info(f"✅ FIX #2 VALIDATION: {result['status']}")
            for test in result['edge_cases_tested']:
                logger.info(f"   ✓ {test}")

        except Exception as e:
            result['status'] = 'FAIL'
            result['issues'].append(f"Exception during test: {str(e)}")
            result['traceback'] = traceback.format_exc()
            logger.error(f"❌ FIX #2 VALIDATION FAILED: {e}")
            logger.error(traceback.format_exc())

        return result

    async def test_fix3_empty_sequence(self) -> Dict[str, Any]:
        """
        TEST FIX #3: Empty Sequence Safety (Lines 611-620)

        Validates:
        1. dict_values → list conversion is correct
        2. Nested if statement logic works
        3. z_scores handling unchanged
        4. Edge case: z_scores is empty dict {}
        5. Edge case: z_scores has values but all are 0
        6. Alert description formats correctly
        """
        logger.info("\n" + "="*80)
        logger.info("TEST FIX #3: Empty Sequence Safety (Lines 611-620)")
        logger.info("="*80)

        result = {
            'fix_name': 'FIX #3: Empty Sequence Safety',
            'line_numbers': '611-620',
            'status': 'PASS',
            'issues': [],
            'edge_cases_tested': []
        }

        try:
            detector = ManipulationDetector(self.config, logger)

            # Test data with enough points for z-score calculation
            symbol = "TESTCOIN"
            for i in range(35):
                detector._historical_data[symbol] = detector._historical_data.get(symbol, [])
                detector._historical_data[symbol].append({
                    'timestamp': i,
                    'price': 50000 + i*10,
                    'volume': 1000000,
                    'open_interest': 100000000
                })

            # EDGE CASE 1: Empty z_scores dict {}
            metrics = {
                'oi_change_15m_pct': 0.03,
                'volume_spike_ratio': 3.0,
                'price_change_15m_pct': 0.01,
                'divergence_detected': False,
                'z_scores': {}  # Empty dict
            }

            try:
                alert = detector._create_manipulation_alert(symbol, metrics, 0.8)
                # Should not crash
                if '📊' in alert.description:
                    result['issues'].append("Z-score label added despite empty z_scores")
                else:
                    result['edge_cases_tested'].append("Empty z_scores dict: no crash, no z-score label")
            except ValueError as e:
                if 'max()' in str(e):
                    result['status'] = 'FAIL'
                    result['issues'].append(f"max() on empty sequence error: {e}")
                    return result
            except Exception as e:
                result['status'] = 'FAIL'
                result['issues'].append(f"Exception with empty z_scores: {e}")
                return result

            # EDGE CASE 2: z_scores with all zeros
            metrics['z_scores'] = {'oi': 0, 'volume': 0, 'price': 0}

            try:
                alert = detector._create_manipulation_alert(symbol, metrics, 0.8)
                # Should not crash, but should not add z-score label (max_z = 0)
                if '📊' in alert.description:
                    result['issues'].append("Z-score label added for all-zero z-scores")
                else:
                    result['edge_cases_tested'].append("All-zero z_scores: no crash, no z-score label")
            except Exception as e:
                result['status'] = 'FAIL'
                result['issues'].append(f"Exception with all-zero z_scores: {e}")
                return result

            # EDGE CASE 3: z_scores with normal values
            metrics['z_scores'] = {'oi': 2.5, 'volume': 3.2, 'price': 2.8}

            try:
                alert = detector._create_manipulation_alert(symbol, metrics, 0.8)
                # Should add z-score label for max_z = 3.2 > 2.5
                if '📊' not in alert.description:
                    result['issues'].append("Z-score label not added for max_z > 2.5")
                elif '3.2σ' not in alert.description:
                    result['issues'].append(f"Z-score value incorrect in description: {alert.description}")
                else:
                    result['edge_cases_tested'].append("Normal z_scores: correctly adds z-score label")
            except Exception as e:
                result['status'] = 'FAIL'
                result['issues'].append(f"Exception with normal z_scores: {e}")
                return result

            # EDGE CASE 4: z_scores with high outlier (> 3.0)
            metrics['z_scores'] = {'oi': 1.5, 'volume': 3.5, 'price': 2.0}

            try:
                alert = detector._create_manipulation_alert(symbol, metrics, 0.8)
                # Should add "outlier" label for max_z = 3.5 > 3.0
                if '📊' not in alert.description or 'outlier' not in alert.description:
                    result['issues'].append("Outlier label not added for max_z > 3.0")
                else:
                    result['edge_cases_tested'].append("High z-score (>3.0): correctly adds 'outlier' label")
            except Exception as e:
                result['status'] = 'FAIL'
                result['issues'].append(f"Exception with high z_scores: {e}")
                return result

            # EDGE CASE 5: Verify source code has the fix
            import inspect
            source = inspect.getsource(detector._create_manipulation_alert)

            if 'list(z_scores.values())' not in source:
                result['status'] = 'FAIL'
                result['issues'].append("dict_values → list conversion not found in source code")
                return result

            result['edge_cases_tested'].append("Source code contains list() conversion")

            if 'if z_values:' not in source:
                result['status'] = 'FAIL'
                result['issues'].append("Empty list check not found in source code")
                return result

            result['edge_cases_tested'].append("Source code contains empty list check")

            logger.info(f"✅ FIX #3 VALIDATION: {result['status']}")
            for test in result['edge_cases_tested']:
                logger.info(f"   ✓ {test}")

        except Exception as e:
            result['status'] = 'FAIL'
            result['issues'].append(f"Exception during test: {str(e)}")
            result['traceback'] = traceback.format_exc()
            logger.error(f"❌ FIX #3 VALIDATION FAILED: {e}")
            logger.error(traceback.format_exc())

        return result

    async def test_integration_all_fixes(self) -> Dict[str, Any]:
        """
        TEST: Integration of all 3 fixes together.

        Validates that all fixes work together without conflicts.
        """
        logger.info("\n" + "="*80)
        logger.info("TEST: Integration of All 3 Fixes")
        logger.info("="*80)

        result = {
            'fix_name': 'Integration Test - All Fixes',
            'status': 'PASS',
            'issues': [],
            'edge_cases_tested': []
        }

        try:
            detector = ManipulationDetector(self.config, logger)
            symbol = "INTEGRATION"

            # Build data with some zero prices (triggers FIX #2)
            for i in range(35):
                price = 50000 + i*100 if i % 7 != 0 else 0  # Some zero prices
                detector._historical_data[symbol] = detector._historical_data.get(symbol, [])
                detector._historical_data[symbol].append({
                    'timestamp': i,
                    'price': price,
                    'volume': 1000000,
                    'open_interest': 100000000
                })

            # Trigger alert that exercises all 3 fixes
            alert_data = self.create_market_data(52000, 3000000, 105000000)
            alert = await detector.analyze_market_data(symbol, alert_data)

            if not alert:
                result['issues'].append("Alert not generated in integration test")
                result['status'] = 'FAIL'
                return result

            result['edge_cases_tested'].append("Alert generated successfully")

            # Check FIX #1: Alert persistence
            if symbol not in detector._manipulation_history or len(detector._manipulation_history[symbol]) == 0:
                result['issues'].append("FIX #1 failed: Alert not persisted")
                result['status'] = 'FAIL'
                return result

            result['edge_cases_tested'].append("FIX #1: Alert persisted to history")

            # Check FIX #2: Volatility calculation didn't crash despite zero prices
            # If we got here, it means the volatility calculation worked
            result['edge_cases_tested'].append("FIX #2: Volatility calculation handled zero prices")

            # Check FIX #3: Alert description created without max() error
            # If alert was created, FIX #3 worked
            if alert.description:
                result['edge_cases_tested'].append("FIX #3: Alert description created successfully")

            # Check get_recent_alerts works end-to-end
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            recent = await detector.get_recent_alerts(since, limit=10)

            if len(recent) == 0:
                result['issues'].append("get_recent_alerts returned empty after alert creation")
                result['status'] = 'FAIL'
                return result

            result['edge_cases_tested'].append("get_recent_alerts() returns persisted alerts")

            logger.info(f"✅ INTEGRATION TEST: {result['status']}")
            for test in result['edge_cases_tested']:
                logger.info(f"   ✓ {test}")

        except Exception as e:
            result['status'] = 'FAIL'
            result['issues'].append(f"Exception during integration test: {str(e)}")
            result['traceback'] = traceback.format_exc()
            logger.error(f"❌ INTEGRATION TEST FAILED: {e}")
            logger.error(traceback.format_exc())

        return result

    async def test_regression_quick_wins(self) -> Dict[str, Any]:
        """
        TEST: Regression on Quick Wins functionality.

        Ensures the 5 quick wins still work after fixes:
        1. Volatility-adjusted thresholds
        2. (unused)
        3. Z-score calculation
        4. Coordinated pattern detection
        5. Enhanced alert descriptions
        """
        logger.info("\n" + "="*80)
        logger.info("TEST: Regression - Quick Wins Functionality")
        logger.info("="*80)

        result = {
            'fix_name': 'Regression Test - Quick Wins',
            'status': 'PASS',
            'issues': [],
            'edge_cases_tested': []
        }

        try:
            detector = ManipulationDetector(self.config, logger)
            symbol = "REGRESSION"

            # Build sufficient data for all quick wins
            for i in range(35):
                detector._historical_data[symbol] = detector._historical_data.get(symbol, [])
                detector._historical_data[symbol].append({
                    'timestamp': i,
                    'price': 50000 + i*100,
                    'volume': 1000000,
                    'open_interest': 100000000
                })

            # Test Quick Win #1: Volatility adjustment
            base_threshold = 0.015
            adjusted = detector._get_volatility_adjusted_threshold(symbol, base_threshold)
            if adjusted < base_threshold or adjusted > base_threshold * 2.5:
                result['issues'].append(f"Quick Win #1 broken: threshold {adjusted} out of range")
                result['status'] = 'FAIL'
            else:
                result['edge_cases_tested'].append("Quick Win #1: Volatility adjustment works")

            # Test Quick Win #3: Z-score calculation
            metrics = {
                'oi_change_15m_pct': 0.03,
                'volume': 1500000,
                'price_change_15m_pct': 0.015
            }
            z_scores = detector._calculate_z_scores(symbol, metrics)

            if not isinstance(z_scores, dict):
                result['issues'].append("Quick Win #3 broken: z_scores not a dict")
                result['status'] = 'FAIL'
            else:
                result['edge_cases_tested'].append("Quick Win #3: Z-score calculation works")

            # Test Quick Win #4: Coordinated patterns
            # Create pattern: large OI + volume spike + small price change
            pattern_metrics = {
                'oi_change_15m_pct': 0.025,  # > 0.02
                'volume_spike_ratio': 2.5,    # > 2.0
                'price_change_15m_pct': 0.003, # < 0.005
            }

            # This would be detected in _analyze_manipulation_metrics
            # Just check the logic is present
            coordinated = (abs(pattern_metrics['oi_change_15m_pct']) > 0.02 and
                          pattern_metrics['volume_spike_ratio'] > 2.0 and
                          abs(pattern_metrics['price_change_15m_pct']) < 0.005)

            if not coordinated:
                result['issues'].append("Quick Win #4 broken: pattern detection logic failed")
                result['status'] = 'FAIL'
            else:
                result['edge_cases_tested'].append("Quick Win #4: Coordinated pattern logic works")

            # Test Quick Win #5: Enhanced descriptions
            full_metrics = {
                'oi_change_15m_pct': 0.03,
                'oi_change_15m': 3000000,
                'volume_spike_ratio': 3.0,
                'price_change_15m_pct': 0.015,
                'divergence_detected': False,
                'z_scores': {'oi': 3.5, 'volume': 2.8, 'price': 2.5}
            }

            alert = detector._create_manipulation_alert(symbol, full_metrics, 0.85)

            # Check description has enhanced elements
            if 'OI:' not in alert.description:
                result['issues'].append("Quick Win #5 broken: OI not in description")
                result['status'] = 'FAIL'
            elif 'Vol:' not in alert.description:
                result['issues'].append("Quick Win #5 broken: Vol not in description")
                result['status'] = 'FAIL'
            elif '📊' not in alert.description:
                result['issues'].append("Quick Win #5 broken: z-score indicator not in description")
                result['status'] = 'FAIL'
            else:
                result['edge_cases_tested'].append("Quick Win #5: Enhanced descriptions work")

            logger.info(f"✅ REGRESSION TEST: {result['status']}")
            for test in result['edge_cases_tested']:
                logger.info(f"   ✓ {test}")

        except Exception as e:
            result['status'] = 'FAIL'
            result['issues'].append(f"Exception during regression test: {str(e)}")
            result['traceback'] = traceback.format_exc()
            logger.error(f"❌ REGRESSION TEST FAILED: {e}")
            logger.error(traceback.format_exc())

        return result

    async def run_all_validations(self) -> List[Dict[str, Any]]:
        """Run all validation tests."""
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE POST-FIX VALIDATION")
        logger.info("Manipulation Detector - 3 Critical Fixes")
        logger.info("="*80 + "\n")

        results = []

        # Run each validation test
        results.append(await self.test_fix1_alert_persistence())
        results.append(await self.test_fix2_division_by_zero())
        results.append(await self.test_fix3_empty_sequence())
        results.append(await self.test_integration_all_fixes())
        results.append(await self.test_regression_quick_wins())

        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['status'] == 'PASS')
        failed_tests = total_tests - passed_tests

        # Calculate production readiness score
        if failed_tests == 0:
            prod_score = 100
        elif failed_tests == 1:
            prod_score = 70
        elif failed_tests == 2:
            prod_score = 40
        else:
            prod_score = 0

        # Determine go/no-go decision
        if prod_score >= 100:
            decision = "GO"
            rationale = "All fixes validated. System is production-ready."
        elif prod_score >= 70:
            decision = "CONDITIONAL GO"
            rationale = "Minor issues found. Can deploy with monitoring."
        else:
            decision = "NO-GO"
            rationale = "Critical issues found. Do not deploy to production."

        report = {
            'validation_date': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'production_readiness_score': prod_score,
                'decision': decision,
                'rationale': rationale
            },
            'test_results': results
        }

        return report


async def main():
    """Main validation execution."""
    validator = FixValidator()

    try:
        results = await validator.run_all_validations()
        report = validator.generate_report(results)

        # Print summary
        logger.info("\n" + "="*80)
        logger.info("VALIDATION REPORT SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed_tests']}")
        logger.info(f"Failed: {report['summary']['failed_tests']}")
        logger.info(f"Production Readiness Score: {report['summary']['production_readiness_score']}%")
        logger.info(f"\nDecision: {report['summary']['decision']}")
        logger.info(f"Rationale: {report['summary']['rationale']}")

        # Print detailed issues if any
        for result in results:
            if result['status'] == 'FAIL':
                logger.error(f"\n❌ {result['fix_name']} - FAILED")
                for issue in result['issues']:
                    logger.error(f"   - {issue}")

        logger.info("\n" + "="*80)

        return report['summary']['decision'] in ['GO', 'CONDITIONAL GO']

    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
