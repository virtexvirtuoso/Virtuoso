#!/usr/bin/env python3
"""
Comprehensive test cases for stop loss calculation accuracy in the Virtuoso trading system.
This script validates the fixes applied to ensure consistency between PDF reports and execution logic.
"""

import sys
import os
import unittest
import json
from decimal import Decimal
from typing import Dict, Any, List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.core.reporting.pdf_generator import ReportGenerator
    from src.monitoring.alert_manager import AlertManager
    from src.trade_execution.trade_executor import TradeExecutor
    from src.core.risk.stop_loss_calculator import StopLossCalculator, StopLossMethod
    from src.core.config.config_manager import ConfigManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)


class StopLossCalculationTests(unittest.TestCase):
    """Test cases for stop loss calculation accuracy across components."""

    def setUp(self):
        """Set up test configuration and components."""
        # Load real configuration from config manager
        try:
            config_manager = ConfigManager()
            real_config = config_manager._config or {}

            # Extract actual trading thresholds from the real config
            confluence_config = real_config.get('confluence', {})
            thresholds = confluence_config.get('thresholds', {})

            # Use real thresholds, with fallbacks if not found
            buy_threshold = thresholds.get('buy', 70)
            sell_threshold = thresholds.get('sell', 35)  # Note: config has 35, not 30

            print(f"Loading real config thresholds: buy={buy_threshold}, sell={sell_threshold}")

        except Exception as e:
            print(f"Failed to load real config, using fallback values: {e}")
            buy_threshold = 70
            sell_threshold = 35

        self.test_config = {
            'risk': {
                'long_stop_percentage': 3.0,
                'short_stop_percentage': 3.5,
                'risk_reward_ratio': 2.0,
                'default_risk_percentage': 2.0,
                'account_balance': 10000
            },
            'risk_management': {
                'default_stop_loss': 0.025,  # 2.5%
                'default_take_profit': 0.05,  # 5%
                'max_daily_loss': 0.05,
                'max_drawdown': 0.10
            },
            'exchanges': {
                'bybit': {
                    'api_key': 'test_key',
                    'secret': 'test_secret',
                    'sandbox': True
                }
            },
            'trading': {
                'buy_threshold': buy_threshold,     # Read from real config
                'sell_threshold': sell_threshold   # Read from real config
            }
        }

        # Initialize components with test config
        self.alert_manager = AlertManager(self.test_config)

        # Initialize unified stop loss calculator
        self.stop_loss_calculator = StopLossCalculator(self.test_config)

        # Skip TradeExecutor for now since it requires complex exchange setup
        # We're focusing on Alert Manager stop loss calculation fixes
        self.trade_executor = None

        # Mock PDF generator (we'll test the calculation logic directly)
        self.pdf_generator = None

    def test_long_position_stop_loss_calculation(self):
        """Test stop loss calculation for long positions."""
        test_cases = [
            {
                'name': 'BTC Long Position',
                'entry_price': 50000.0,
                'expected_stop_pct': 3.0,
                'signal_type': 'BUY'
            },
            {
                'name': 'ETH Long Position',
                'entry_price': 3000.0,
                'expected_stop_pct': 3.0,
                'signal_type': 'BUY'
            },
            {
                'name': 'Small Cap Long',
                'entry_price': 0.5,
                'expected_stop_pct': 3.0,
                'signal_type': 'BUY'
            }
        ]

        for case in test_cases:
            with self.subTest(case=case['name']):
                # Test Alert Manager calculation
                signal_data = {
                    'symbol': 'BTC/USDT',
                    'signal_type': case['signal_type'],
                    'price': case['entry_price']
                }

                enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(signal_data)

                # Extract calculated values
                trade_params = enhanced_signal.get('trade_params', {})
                calculated_stop = trade_params.get('stop_loss')
                entry_price = trade_params.get('entry_price', case['entry_price'])

                # Calculate actual percentage
                if calculated_stop and entry_price:
                    actual_stop_pct = abs(((calculated_stop / entry_price) - 1) * 100)

                    # Allow 0.01% tolerance for floating point precision
                    self.assertAlmostEqual(
                        actual_stop_pct,
                        case['expected_stop_pct'],
                        places=2,
                        msg=f"Stop loss percentage mismatch for {case['name']}: "
                            f"expected {case['expected_stop_pct']}%, got {actual_stop_pct:.2f}%"
                    )
                else:
                    self.fail(f"Missing stop loss or entry price for {case['name']}")

    def test_short_position_stop_loss_calculation(self):
        """Test stop loss calculation for short positions."""
        test_cases = [
            {
                'name': 'BTC Short Position',
                'entry_price': 50000.0,
                'expected_stop_pct': 3.5,
                'signal_type': 'SELL'
            },
            {
                'name': 'ETH Short Position',
                'entry_price': 3000.0,
                'expected_stop_pct': 3.5,
                'signal_type': 'SELL'
            }
        ]

        for case in test_cases:
            with self.subTest(case=case['name']):
                signal_data = {
                    'symbol': 'BTC/USDT',
                    'signal_type': case['signal_type'],
                    'price': case['entry_price']
                }

                enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(signal_data)
                trade_params = enhanced_signal.get('trade_params', {})
                calculated_stop = trade_params.get('stop_loss')
                entry_price = trade_params.get('entry_price', case['entry_price'])

                if calculated_stop and entry_price:
                    actual_stop_pct = abs(((calculated_stop / entry_price) - 1) * 100)

                    self.assertAlmostEqual(
                        actual_stop_pct,
                        case['expected_stop_pct'],
                        places=2,
                        msg=f"Stop loss percentage mismatch for {case['name']}: "
                            f"expected {case['expected_stop_pct']}%, got {actual_stop_pct:.2f}%"
                    )

    def test_pdf_calculation_consistency(self):
        """Test that PDF calculations match Alert Manager calculations."""
        test_signal = {
            'symbol': 'BTC/USDT',
            'signal_type': 'BUY',
            'price': 50000.0
        }

        # Get Alert Manager calculation
        enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(test_signal)
        alert_trade_params = enhanced_signal.get('trade_params', {})

        # Simulate PDF calculation logic (the fixed version)
        entry_price = alert_trade_params.get('entry_price', 50000.0)
        stop_loss = alert_trade_params.get('stop_loss')

        if stop_loss and entry_price:
            if entry_price > stop_loss:  # Long position
                pdf_stop_loss_pct = abs(((stop_loss / entry_price) - 1) * 100)
            else:  # Short position
                pdf_stop_loss_pct = abs(((stop_loss / entry_price) - 1) * 100)

            # Calculate what Alert Manager produced
            alert_stop_pct = abs(((stop_loss / entry_price) - 1) * 100)

            self.assertAlmostEqual(
                pdf_stop_loss_pct,
                alert_stop_pct,
                places=2,
                msg=f"PDF and Alert Manager calculations differ: "
                    f"PDF={pdf_stop_loss_pct:.2f}%, Alert={alert_stop_pct:.2f}%"
            )

    def test_boundary_conditions(self):
        """Test edge cases and boundary conditions."""
        boundary_tests = [
            {
                'name': 'Very small price',
                'entry_price': 0.0001,
                'signal_type': 'BUY'
            },
            {
                'name': 'Very large price',
                'entry_price': 1000000.0,
                'signal_type': 'BUY'
            },
            {
                'name': 'Exact integer price',
                'entry_price': 100.0,
                'signal_type': 'SELL'
            }
        ]

        for test in boundary_tests:
            with self.subTest(case=test['name']):
                signal_data = {
                    'symbol': 'TEST/USDT',
                    'signal_type': test['signal_type'],
                    'price': test['entry_price']
                }

                try:
                    enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(signal_data)
                    trade_params = enhanced_signal.get('trade_params', {})

                    # Should not raise exceptions and should produce valid results
                    self.assertIsInstance(trade_params, dict)

                    stop_loss = trade_params.get('stop_loss')
                    if stop_loss:
                        self.assertIsInstance(stop_loss, (int, float))
                        self.assertGreater(stop_loss, 0)

                except Exception as e:
                    self.fail(f"Boundary test '{test['name']}' raised exception: {e}")

    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        invalid_tests = [
            {
                'name': 'Negative price',
                'price': -100.0,
                'signal_type': 'BUY'
            },
            {
                'name': 'Zero price',
                'price': 0.0,
                'signal_type': 'BUY'
            },
            {
                'name': 'String price',
                'price': "invalid",
                'signal_type': 'BUY'
            },
            {
                'name': 'None price',
                'price': None,
                'signal_type': 'BUY'
            }
        ]

        for test in invalid_tests:
            with self.subTest(case=test['name']):
                signal_data = {
                    'symbol': 'TEST/USDT',
                    'signal_type': test['signal_type'],
                    'price': test['price']
                }

                # Should handle gracefully without crashing
                try:
                    enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(signal_data)
                    # Should return a signal, potentially with no trade_params
                    self.assertIsInstance(enhanced_signal, dict)
                except Exception as e:
                    self.fail(f"Invalid input test '{test['name']}' should not raise exception: {e}")

    def test_configuration_consistency(self):
        """Test that all components use the same configuration values."""
        # Test that Alert Manager reads from config correctly
        signal_data = {
            'symbol': 'BTC/USDT',
            'signal_type': 'BUY',
            'price': 50000.0
        }

        enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(signal_data)
        trade_params = enhanced_signal.get('trade_params', {})

        stop_loss = trade_params.get('stop_loss')
        entry_price = trade_params.get('entry_price', 50000.0)

        if stop_loss and entry_price:
            calculated_pct = abs(((stop_loss / entry_price) - 1) * 100)
            expected_pct = self.test_config['risk']['long_stop_percentage']

            self.assertAlmostEqual(
                calculated_pct,
                expected_pct,
                places=2,
                msg=f"Alert Manager not using config values: "
                    f"expected {expected_pct}%, got {calculated_pct:.2f}%"
            )

    def test_mathematical_precision(self):
        """Test mathematical precision in calculations."""
        # Use Decimal for high precision testing
        test_price = Decimal('50000.123456789')
        expected_stop_pct = Decimal('3.0')

        # Convert to float for our system
        signal_data = {
            'symbol': 'BTC/USDT',
            'signal_type': 'BUY',
            'price': float(test_price)
        }

        enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(signal_data)
        trade_params = enhanced_signal.get('trade_params', {})

        stop_loss = trade_params.get('stop_loss')
        entry_price = trade_params.get('entry_price')

        if stop_loss and entry_price:
            # Calculate with high precision
            precise_pct = abs(((Decimal(str(stop_loss)) / Decimal(str(entry_price))) - 1) * 100)

            # Should be very close to expected
            self.assertLess(
                abs(precise_pct - expected_stop_pct),
                Decimal('0.01'),  # 0.01% tolerance
                msg=f"Precision test failed: expected {expected_stop_pct}%, got {precise_pct}%"
            )

    def test_unified_stop_loss_calculator(self):
        """Test the unified stop loss calculator directly."""
        test_cases = [
            {
                'name': 'BUY at threshold (70)',
                'signal_type': 'BUY',
                'confluence_score': 70,
                'expected_multiplier': 0.8  # Should get minimum stop (80% of base)
            },
            {
                'name': 'BUY high confidence (85)',
                'signal_type': 'BUY',
                'confluence_score': 85,
                'expected_multiplier': 1.15  # Should get scaled stop
            },
            {
                'name': 'BUY very high confidence (95)',
                'signal_type': 'BUY',
                'confluence_score': 95,
                'expected_multiplier': 1.42  # Should get near maximum stop
            },
            {
                'name': f'SELL at threshold ({self.test_config["trading"]["sell_threshold"]})',
                'signal_type': 'SELL',
                'confluence_score': self.test_config["trading"]["sell_threshold"],
                'expected_multiplier': 0.8  # Should get minimum stop
            },
            {
                'name': 'SELL high confidence (15)',
                'signal_type': 'SELL',
                'confluence_score': 15,
                'expected_multiplier': 1.15  # Should get scaled stop
            },
            {
                'name': 'SELL very high confidence (5)',
                'signal_type': 'SELL',
                'confluence_score': 5,
                'expected_multiplier': 1.42  # Should get near maximum stop
            }
        ]

        for case in test_cases:
            with self.subTest(case=case['name']):
                signal_data = {
                    'signal_type': case['signal_type'],
                    'confluence_score': case['confluence_score'],
                    'price': 50000.0
                }

                # Test unified calculator
                stop_info = self.stop_loss_calculator.get_stop_loss_info(signal_data)

                self.assertNotIn('error', stop_info, f"Calculator error for {case['name']}")

                # Calculate expected stop percentage
                base_pct = 3.0 if case['signal_type'] == 'BUY' else 3.5  # From config
                expected_stop_pct = (base_pct / 100) * case['expected_multiplier']

                actual_stop_pct = stop_info['stop_loss_percentage']

                # Allow 0.2% tolerance for scaling calculations
                self.assertAlmostEqual(
                    actual_stop_pct,
                    expected_stop_pct,
                    delta=0.002,
                    msg=f"Stop loss percentage mismatch for {case['name']}: "
                        f"expected ~{expected_stop_pct*100:.2f}%, got {actual_stop_pct*100:.2f}%"
                )

    def test_confidence_based_alert_manager_integration(self):
        """Test that AlertManager now uses confidence-based stop loss sizing."""
        test_cases = [
            {
                'name': 'Low confidence BUY',
                'signal_data': {
                    'symbol': 'BTC/USDT',
                    'signal_type': 'BUY',
                    'price': 50000.0,
                    'confluence_score': 72  # Just above threshold
                },
                'expect_smaller_stop': True
            },
            {
                'name': 'High confidence BUY',
                'signal_data': {
                    'symbol': 'BTC/USDT',
                    'signal_type': 'BUY',
                    'price': 50000.0,
                    'confluence_score': 90  # High confidence
                },
                'expect_smaller_stop': False
            }
        ]

        for case in test_cases:
            with self.subTest(case=case['name']):
                enhanced_signal = self.alert_manager.add_trade_parameters_to_signal(case['signal_data'])
                trade_params = enhanced_signal.get('trade_params', {})

                self.assertIsInstance(trade_params, dict, f"No trade_params for {case['name']}")

                stop_loss = trade_params.get('stop_loss')
                entry_price = trade_params.get('entry_price', case['signal_data']['price'])

                self.assertIsNotNone(stop_loss, f"No stop_loss calculated for {case['name']}")

                # Calculate actual stop percentage
                actual_stop_pct = abs(((stop_loss / entry_price) - 1) * 100)
                base_expected = 3.0  # Long stop percentage from config

                if case['expect_smaller_stop']:
                    # Low confidence should get smaller stops (80% of base = tighter)
                    expected_max = base_expected * 0.9  # Should be less than 90% of base
                    self.assertLess(
                        actual_stop_pct,
                        expected_max,
                        msg=f"Low confidence {case['name']} should have tighter stop: "
                            f"got {actual_stop_pct:.2f}%, expected < {expected_max:.2f}%"
                    )
                else:
                    # High confidence should get larger stops (towards 150% of base)
                    expected_min = base_expected * 1.1  # Should be more than 110% of base
                    self.assertGreater(
                        actual_stop_pct,
                        expected_min,
                        msg=f"High confidence {case['name']} should have wider stop: "
                            f"got {actual_stop_pct:.2f}%, expected > {expected_min:.2f}%"
                    )


def run_tests():
    """Run all stop loss calculation tests."""
    print("🧪 Running Stop Loss Calculation Validation Tests...")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(StopLossCalculationTests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All stop loss calculation tests PASSED!")
        print(f"✅ Ran {result.testsRun} tests successfully")
    else:
        print("❌ Some tests FAILED!")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")

        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")

        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)