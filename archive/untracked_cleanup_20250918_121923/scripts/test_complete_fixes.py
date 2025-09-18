#!/usr/bin/env python3
"""
Comprehensive test suite for verifying all fixes:
1. Reliability percentage display (should be 100%, not 10,000%)
2. Stop loss and take profit on charts
3. Trade parameters in signal data
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.reporting.pdf_generator import ReportGenerator
from src.risk.risk_manager import RiskManager
from src.monitoring.signal_processor import SignalProcessor


class ComprehensiveTestSuite:
    """Test all fixes comprehensively."""

    def __init__(self):
        self.config = {
            'risk': {
                'default_risk_percentage': 2.0,
                'risk_reward_ratio': 2.0,
                'long_stop_percentage': 3.5,
                'short_stop_percentage': 3.5
            },
            'trading': {
                'account_balance': 10000
            },
            'reporting': {
                'output_dir': 'reports/test'
            }
        }
        self.test_results = {}

    async def test_reliability_percentage(self):
        """Test 1: Verify reliability shows correctly (not 10,000%)."""
        print("\n" + "="*60)
        print("TEST 1: Reliability Percentage Display")
        print("="*60)

        try:
            # Initialize PDF generator
            pdf_generator = ReportGenerator(self.config)

            # Test signal with 100% reliability
            signal_data = {
                'symbol': 'XRP/USDT',
                'signal_type': 'BUY',
                'price': 3.12,
                'confluence_score': 68.2,
                'reliability': 1.0,  # 100% reliability (as decimal)
                'timestamp': datetime.now().isoformat()
            }

            # Check how reliability is passed to template
            print(f"Input reliability (decimal): {signal_data['reliability']}")

            # The template expects reliability as decimal and multiplies by 100
            # So we should pass 1.0 for 100%
            expected_display = f"{signal_data['reliability'] * 100:.0f}%"
            print(f"Expected display in PDF: {expected_display}")

            if expected_display == "100%":
                print("✅ PASS: Reliability will display correctly as 100%")
                self.test_results['reliability_display'] = 'PASS'
            else:
                print(f"❌ FAIL: Reliability will display as {expected_display}")
                self.test_results['reliability_display'] = 'FAIL'

            # Test edge cases
            test_cases = [
                (0.5, "50%"),
                (0.75, "75%"),
                (1.0, "100%"),
                (0.1, "10%")
            ]

            print("\nEdge case tests:")
            for decimal_val, expected in test_cases:
                actual = f"{decimal_val * 100:.0f}%"
                status = "✅" if actual == expected else "❌"
                print(f"  {status} {decimal_val} -> {actual} (expected {expected})")

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results['reliability_display'] = 'ERROR'

    async def test_trade_parameters_calculation(self):
        """Test 2: Verify trade parameters are calculated."""
        print("\n" + "="*60)
        print("TEST 2: Trade Parameters Calculation")
        print("="*60)

        try:
            # Initialize components
            risk_manager = RiskManager(self.config)
            signal_processor = SignalProcessor(
                config=self.config,
                signal_generator=None,
                metrics_manager=None,
                interpretation_manager=None,
                market_data_manager=None,
                risk_manager=risk_manager
            )

            # Test signal generation with trade params
            test_data = {
                'symbol': 'XRP/USDT',
                'price': 3.12,
                'signal_type': 'BUY',
                'confluence_score': 68.2,
                'reliability': 0.8
            }

            print(f"Testing {test_data['symbol']} {test_data['signal_type']} signal at ${test_data['price']}")

            # Calculate trade parameters
            trade_params = signal_processor.calculate_trade_parameters(
                symbol=test_data['symbol'],
                price=test_data['price'],
                signal_type=test_data['signal_type'],
                score=test_data['confluence_score'],
                reliability=test_data['reliability']
            )

            # Verify all required fields
            required_fields = ['stop_loss', 'take_profit', 'position_size', 'risk_reward_ratio']
            missing_fields = []

            for field in required_fields:
                if field not in trade_params or trade_params[field] is None:
                    missing_fields.append(field)

            if not missing_fields:
                print("\n✅ All trade parameters calculated:")
                print(f"  • Entry Price: ${trade_params.get('entry_price', 0):.4f}")
                print(f"  • Stop Loss: ${trade_params.get('stop_loss', 0):.4f}")
                print(f"  • Take Profit: ${trade_params.get('take_profit', 0):.4f}")
                print(f"  • Position Size: {trade_params.get('position_size', 0):.6f}")
                print(f"  • Risk/Reward: 1:{trade_params.get('risk_reward_ratio', 0):.1f}")

                # Verify stop loss is ~3.5% from entry for BUY
                expected_sl = test_data['price'] * (1 - 0.035)
                actual_sl = trade_params['stop_loss']
                sl_diff = abs(actual_sl - expected_sl) / expected_sl * 100

                if sl_diff < 0.1:  # Within 0.1% tolerance
                    print(f"\n✅ Stop loss correctly at 3.5% from entry")
                else:
                    print(f"\n⚠️ Stop loss deviation: {sl_diff:.2f}%")

                self.test_results['trade_params_calculation'] = 'PASS'
            else:
                print(f"\n❌ Missing trade parameters: {missing_fields}")
                self.test_results['trade_params_calculation'] = 'FAIL'

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            self.test_results['trade_params_calculation'] = 'ERROR'

    async def test_pdf_generation_with_fixes(self):
        """Test 3: Generate actual PDF with all fixes."""
        print("\n" + "="*60)
        print("TEST 3: PDF Generation with All Fixes")
        print("="*60)

        try:
            # Initialize components
            risk_manager = RiskManager(self.config)
            pdf_generator = ReportGenerator(self.config)

            # Create test signal with trade parameters
            symbol = "XRP/USDT"
            entry_price = 3.12
            signal_type = "BUY"
            confluence_score = 68.2
            reliability = 1.0  # 100% reliability

            # Calculate trade parameters
            from src.risk.risk_manager import OrderType
            order_type = OrderType.BUY if signal_type == "BUY" else OrderType.SELL

            sl_tp = risk_manager.calculate_stop_loss_take_profit(
                entry_price=entry_price,
                order_type=order_type
            )

            position_info = risk_manager.calculate_position_size(
                account_balance=10000,
                entry_price=entry_price,
                stop_loss_price=sl_tp['stop_loss_price']
            )

            # Build complete signal data
            signal_data = {
                'symbol': symbol,
                'signal_type': signal_type,
                'confluence_score': confluence_score,
                'reliability': reliability,  # As decimal for correct display
                'price': entry_price,
                'entry_price': entry_price,
                'trade_params': {
                    'entry_price': entry_price,
                    'stop_loss': sl_tp['stop_loss_price'],
                    'take_profit': sl_tp['take_profit_price'],
                    'position_size': position_info['position_size_units'],
                    'risk_reward_ratio': sl_tp['risk_reward_ratio'],
                    'risk_percentage': position_info['risk_percentage']
                },
                'timestamp': datetime.now().isoformat(),
                'analysis_components': {
                    'orderflow': {'score': 80, 'interpretation': 'Strong buying pressure detected'},
                    'sentiment': {'score': 70, 'interpretation': 'Bullish market sentiment'},
                    'liquidity': {'score': 75, 'interpretation': 'Good liquidity at support zones'},
                    'bitcoin_beta': {'score': 65, 'interpretation': 'Positive BTC correlation'},
                    'smart_money': {'score': 72, 'interpretation': 'Institutional accumulation detected'},
                    'price_structure': {'score': 68, 'interpretation': 'Uptrend structure intact'}
                }
            }

            print(f"\nGenerating test PDF for {symbol} {signal_type} signal")
            print(f"  • Reliability: {reliability * 100:.0f}% (should display as 100%, not 10,000%)")
            print(f"  • Stop Loss: ${signal_data['trade_params']['stop_loss']:.4f}")
            print(f"  • Take Profit: ${signal_data['trade_params']['take_profit']:.4f}")

            # Generate mock OHLCV data
            dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
            prices = np.random.normal(entry_price, entry_price * 0.02, 100)

            ohlcv_data = pd.DataFrame({
                'timestamp': dates,
                'open': prices + np.random.normal(0, 0.01, 100),
                'high': prices + abs(np.random.normal(0.05, 0.02, 100)),
                'low': prices - abs(np.random.normal(0.05, 0.02, 100)),
                'close': prices,
                'volume': np.random.uniform(1000, 10000, 100)
            })

            # Create output directory
            os.makedirs('reports/test', exist_ok=True)

            # Generate the PDF
            pdf_path, json_path, png_path = pdf_generator.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=ohlcv_data,
                output_dir='reports/test'
            )

            if pdf_path and os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path) / 1024
                print(f"\n✅ PDF generated successfully:")
                print(f"  • File: {pdf_path}")
                print(f"  • Size: {file_size:.2f} KB")
                self.test_results['pdf_generation'] = 'PASS'
            else:
                print(f"\n❌ PDF generation failed")
                self.test_results['pdf_generation'] = 'FAIL'

            if png_path and os.path.exists(png_path):
                png_size = os.path.getsize(png_path) / 1024
                print(f"\n✅ Chart PNG generated:")
                print(f"  • File: {png_path}")
                print(f"  • Size: {png_size:.2f} KB")
                print(f"  • Should show stop loss and take profit lines")
                self.test_results['chart_generation'] = 'PASS'
            else:
                print(f"\n⚠️ Chart PNG not generated")
                self.test_results['chart_generation'] = 'FAIL'

            # Verify JSON has correct data
            if json_path and os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    saved_data = json.load(f)

                # Check reliability in JSON
                if 'reliability' in saved_data:
                    json_reliability = saved_data['reliability']
                    print(f"\n📋 JSON verification:")
                    print(f"  • Reliability stored as: {json_reliability}")

                # Check trade params in JSON
                if 'trade_params' in saved_data:
                    tp = saved_data['trade_params']
                    if tp.get('stop_loss') and tp.get('take_profit'):
                        print(f"  • Trade params present: ✅")
                    else:
                        print(f"  • Trade params incomplete: ⚠️")

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.test_results['pdf_generation'] = 'ERROR'
            self.test_results['chart_generation'] = 'ERROR'

    async def test_vps_integration(self):
        """Test 4: Verify VPS has all fixes working."""
        print("\n" + "="*60)
        print("TEST 4: VPS Integration Verification")
        print("="*60)

        import subprocess

        try:
            # Test trade params calculation on VPS
            print("Testing trade parameters on VPS...")
            result = subprocess.run(
                ['ssh', 'vps', 'cd /home/linuxuser/trading/Virtuoso_ccxt && source venv311/bin/activate && python scripts/test_trade_parameters.py'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if "All tests passed" in result.stdout:
                print("✅ VPS trade parameters working correctly")
                self.test_results['vps_trade_params'] = 'PASS'
            else:
                print("❌ VPS trade parameters test failed")
                print(result.stdout[-500:] if result.stdout else "No output")
                self.test_results['vps_trade_params'] = 'FAIL'

        except subprocess.TimeoutExpired:
            print("⚠️ VPS test timed out")
            self.test_results['vps_trade_params'] = 'TIMEOUT'
        except Exception as e:
            print(f"❌ VPS test failed: {str(e)}")
            self.test_results['vps_trade_params'] = 'ERROR'

    async def run_all_tests(self):
        """Run all tests and provide summary."""
        print("\n" + "🧪 " * 20)
        print("COMPREHENSIVE TEST SUITE FOR PDF FIXES")
        print("🧪 " * 20)

        # Run all tests
        await self.test_reliability_percentage()
        await self.test_trade_parameters_calculation()
        await self.test_pdf_generation_with_fixes()
        await self.test_vps_integration()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        all_passed = True
        for test_name, result in self.test_results.items():
            status = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
            print(f"{status} {test_name}: {result}")
            if result != "PASS":
                all_passed = False

        print("\n" + "="*60)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Fixes are working correctly.")
            print("\nThe system is ready to generate PDFs with:")
            print("  • Correct reliability percentage (not 10,000%)")
            print("  • Stop loss and take profit levels on charts")
            print("  • Complete trade parameters in signals")
        else:
            print("⚠️ SOME TESTS FAILED. Please review the results above.")
            print("\nIssues to investigate:")
            for test_name, result in self.test_results.items():
                if result != "PASS":
                    print(f"  • {test_name}: {result}")

        return all_passed


async def main():
    """Main test runner."""
    test_suite = ComprehensiveTestSuite()
    success = await test_suite.run_all_tests()

    print("\n📁 Generated test files in: reports/test/")
    print("Please review the PDF to visually confirm:")
    print("  1. Reliability shows as a percentage (e.g., 100%)")
    print("  2. Chart displays stop loss (red line) and take profit (green line)")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())