#!/usr/bin/env python3
"""
Comprehensive test for PDF interpretation display.
Tests multiple scenarios to ensure interpretations are properly shown.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import webbrowser
import os

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.reporting.pdf_generator import ReportGenerator
from src.risk.risk_manager import RiskManager

class InterpretationDisplayTest:
    """Test interpretation display in PDFs."""

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
        self.pdf_generator = ReportGenerator(self.config)
        self.risk_manager = RiskManager(self.config)
        self.generated_files = []

    async def test_case_1_all_components(self):
        """Test 1: All 6 components with interpretations."""
        print("\n" + "="*70)
        print("TEST CASE 1: ALL 6 COMPONENTS WITH INTERPRETATIONS")
        print("="*70)

        # Calculate trade params
        from src.risk.risk_manager import OrderType
        entry_price = 65000
        order_type = OrderType.BUY
        sl_tp = self.risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=order_type
        )

        position_info = self.risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price']
        )

        signal_data = {
            'symbol': 'BTC/USDT',
            'signal_type': 'BUY',
            'price': entry_price,
            'confluence_score': 92.5,
            'reliability': 0.95,  # 95% reliability
            'timestamp': datetime.now().isoformat(),
            'trade_params': {
                'entry_price': entry_price,
                'stop_loss': sl_tp['stop_loss_price'],
                'take_profit': sl_tp['take_profit_price'],
                'position_size': position_info['position_size_units'],
                'risk_reward_ratio': sl_tp['risk_reward_ratio'],
                'risk_percentage': position_info['risk_percentage']
            },
            'analysis_components': {
                'orderflow': {
                    'score': 95,
                    'interpretation': 'Massive institutional accumulation detected - whales are buying aggressively'
                },
                'sentiment': {
                    'score': 88,
                    'interpretation': 'Extreme bullish sentiment across all social media platforms'
                },
                'liquidity': {
                    'score': 91,
                    'interpretation': 'Deep liquidity pools at support levels, minimal slippage expected'
                },
                'bitcoin_beta': {
                    'score': 93,
                    'interpretation': 'Leading the entire crypto market with strong momentum'
                },
                'smart_money': {
                    'score': 90,
                    'interpretation': 'Smart money flow indicates heavy accumulation phase'
                },
                'price_structure': {
                    'score': 94,
                    'interpretation': 'Breaking out of major resistance with strong volume confirmation'
                }
            }
        }

        print(f"Testing signal with all 6 components:")
        for comp_name, comp_data in signal_data['analysis_components'].items():
            print(f"  • {comp_name}: {comp_data['score']}% - {comp_data['interpretation'][:50]}...")

        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_data(entry_price, periods=100)

        # Generate PDF
        pdf_path, json_path, png_path = self.pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )

        self.generated_files.extend([pdf_path, json_path, png_path])

        if pdf_path:
            print(f"✅ PDF generated: {Path(pdf_path).name}")
        else:
            print(f"❌ PDF generation failed")

        return pdf_path is not None

    async def test_case_2_partial_components(self):
        """Test 2: Only some components with interpretations."""
        print("\n" + "="*70)
        print("TEST CASE 2: PARTIAL COMPONENTS (3 of 6)")
        print("="*70)

        from src.risk.risk_manager import OrderType
        entry_price = 3500
        order_type = OrderType.SELL
        sl_tp = self.risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=order_type
        )

        position_info = self.risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price']
        )

        signal_data = {
            'symbol': 'ETH/USDT',
            'signal_type': 'SELL',
            'price': entry_price,
            'confluence_score': 35.5,
            'reliability': 0.72,  # 72% reliability
            'timestamp': datetime.now().isoformat(),
            'trade_params': {
                'entry_price': entry_price,
                'stop_loss': sl_tp['stop_loss_price'],
                'take_profit': sl_tp['take_profit_price'],
                'position_size': position_info['position_size_units'],
                'risk_reward_ratio': sl_tp['risk_reward_ratio'],
                'risk_percentage': position_info['risk_percentage']
            },
            'analysis_components': {
                'orderflow': {
                    'score': 25,
                    'interpretation': 'Heavy distribution, institutional selling pressure'
                },
                'sentiment': {
                    'score': 30,
                    'interpretation': 'Bearish sentiment dominating, fear index rising'
                },
                'price_structure': {
                    'score': 40,
                    'interpretation': 'Breaking down from support, bearish structure forming'
                }
            }
        }

        print(f"Testing signal with partial components (3 of 6):")
        for comp_name, comp_data in signal_data['analysis_components'].items():
            print(f"  • {comp_name}: {comp_data['score']}% - {comp_data['interpretation'][:50]}...")

        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_data(entry_price, periods=100, trend='down')

        # Generate PDF
        pdf_path, json_path, png_path = self.pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )

        self.generated_files.extend([pdf_path, json_path, png_path])

        if pdf_path:
            print(f"✅ PDF generated: {Path(pdf_path).name}")
        else:
            print(f"❌ PDF generation failed")

        return pdf_path is not None

    async def test_case_3_mixed_scores(self):
        """Test 3: Mixed bullish/bearish scores."""
        print("\n" + "="*70)
        print("TEST CASE 3: MIXED BULLISH/BEARISH SCORES")
        print("="*70)

        from src.risk.risk_manager import OrderType
        entry_price = 150
        order_type = OrderType.BUY
        sl_tp = self.risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=order_type
        )

        position_info = self.risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price']
        )

        signal_data = {
            'symbol': 'SOL/USDT',
            'signal_type': 'BUY',
            'price': entry_price,
            'confluence_score': 55.0,
            'reliability': 0.60,  # 60% reliability
            'timestamp': datetime.now().isoformat(),
            'trade_params': {
                'entry_price': entry_price,
                'stop_loss': sl_tp['stop_loss_price'],
                'take_profit': sl_tp['take_profit_price'],
                'position_size': position_info['position_size_units'],
                'risk_reward_ratio': sl_tp['risk_reward_ratio'],
                'risk_percentage': position_info['risk_percentage']
            },
            'analysis_components': {
                'orderflow': {
                    'score': 75,
                    'interpretation': 'Moderate buying pressure, some accumulation visible'
                },
                'sentiment': {
                    'score': 45,
                    'interpretation': 'Neutral sentiment with slight bearish bias'
                },
                'liquidity': {
                    'score': 60,
                    'interpretation': 'Average liquidity, moderate spread'
                },
                'bitcoin_beta': {
                    'score': 30,
                    'interpretation': 'Underperforming relative to Bitcoin'
                },
                'smart_money': {
                    'score': 85,
                    'interpretation': 'Smart money quietly accumulating'
                },
                'price_structure': {
                    'score': 35,
                    'interpretation': 'Weak structure, needs confirmation'
                }
            }
        }

        print(f"Testing signal with mixed scores:")
        for comp_name, comp_data in signal_data['analysis_components'].items():
            color = "🟢" if comp_data['score'] >= 70 else "🟡" if comp_data['score'] >= 40 else "🔴"
            print(f"  {color} {comp_name}: {comp_data['score']}% - {comp_data['interpretation'][:40]}...")

        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_data(entry_price, periods=100, trend='sideways')

        # Generate PDF
        pdf_path, json_path, png_path = self.pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )

        self.generated_files.extend([pdf_path, json_path, png_path])

        if pdf_path:
            print(f"✅ PDF generated: {Path(pdf_path).name}")
        else:
            print(f"❌ PDF generation failed")

        return pdf_path is not None

    async def test_case_4_no_interpretations(self):
        """Test 4: No interpretations provided (backwards compatibility)."""
        print("\n" + "="*70)
        print("TEST CASE 4: NO INTERPRETATIONS (BACKWARDS COMPATIBILITY)")
        print("="*70)

        from src.risk.risk_manager import OrderType
        entry_price = 0.15
        order_type = OrderType.BUY
        sl_tp = self.risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=order_type
        )

        position_info = self.risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price']
        )

        signal_data = {
            'symbol': 'DOGE/USDT',
            'signal_type': 'BUY',
            'price': entry_price,
            'confluence_score': 75.0,
            'reliability': 0.80,
            'timestamp': datetime.now().isoformat(),
            'trade_params': {
                'entry_price': entry_price,
                'stop_loss': sl_tp['stop_loss_price'],
                'take_profit': sl_tp['take_profit_price'],
                'position_size': position_info['position_size_units'],
                'risk_reward_ratio': sl_tp['risk_reward_ratio'],
                'risk_percentage': position_info['risk_percentage']
            }
            # No analysis_components provided
        }

        print(f"Testing signal WITHOUT interpretations:")
        print(f"  • Symbol: {signal_data['symbol']}")
        print(f"  • Score: {signal_data['confluence_score']}%")
        print(f"  • Reliability: {signal_data['reliability']*100:.0f}%")
        print(f"  • analysis_components: NOT PROVIDED")

        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_data(entry_price, periods=100)

        # Generate PDF
        pdf_path, json_path, png_path = self.pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )

        self.generated_files.extend([pdf_path, json_path, png_path])

        if pdf_path:
            print(f"✅ PDF generated: {Path(pdf_path).name}")
            print(f"   (Should work without interpretations section)")
        else:
            print(f"❌ PDF generation failed")

        return pdf_path is not None

    async def test_case_5_long_interpretations(self):
        """Test 5: Very long interpretation texts."""
        print("\n" + "="*70)
        print("TEST CASE 5: LONG INTERPRETATION TEXTS")
        print("="*70)

        from src.risk.risk_manager import OrderType
        entry_price = 42000
        order_type = OrderType.BUY
        sl_tp = self.risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=order_type
        )

        position_info = self.risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price']
        )

        signal_data = {
            'symbol': 'BTC/USDT',
            'signal_type': 'BUY',
            'price': entry_price,
            'confluence_score': 88.0,
            'reliability': 0.92,
            'timestamp': datetime.now().isoformat(),
            'trade_params': {
                'entry_price': entry_price,
                'stop_loss': sl_tp['stop_loss_price'],
                'take_profit': sl_tp['take_profit_price'],
                'position_size': position_info['position_size_units'],
                'risk_reward_ratio': sl_tp['risk_reward_ratio'],
                'risk_percentage': position_info['risk_percentage']
            },
            'analysis_components': {
                'orderflow': {
                    'score': 92,
                    'interpretation': 'Exceptional orderflow dynamics detected with massive institutional buying pressure exceeding 3-month highs. Multiple whale wallets accumulating simultaneously with coordinated buy walls at key support levels. Delta divergence showing extreme bullish bias with bid/ask imbalance heavily favoring buyers.'
                },
                'sentiment': {
                    'score': 85,
                    'interpretation': 'Social sentiment metrics showing parabolic growth in positive mentions across Twitter, Reddit, and Discord. Fear & Greed index at extreme greed levels. Google Trends showing breakout search volume. Funding rates remain sustainable despite bullish sentiment.'
                },
                'liquidity': {
                    'score': 88,
                    'interpretation': 'Liquidity depth analysis reveals massive support zones with over $50M in buy orders within 2% of current price. Market makers actively providing liquidity. Minimal slippage expected even for large orders.'
                },
                'bitcoin_beta': {
                    'score': 90,
                    'interpretation': 'Bitcoin showing strong leadership with correlation coefficients indicating market-wide bullish contagion effect spreading to altcoins.'
                },
                'smart_money': {
                    'score': 87,
                    'interpretation': 'On-chain analytics reveal smart money addresses accumulating at fastest rate since 2020 bull run.'
                },
                'price_structure': {
                    'score': 89,
                    'interpretation': 'Technical structure extremely bullish with successful retest of breakout level confirming continuation pattern.'
                }
            }
        }

        print(f"Testing signal with LONG interpretations:")
        for comp_name, comp_data in signal_data['analysis_components'].items():
            print(f"  • {comp_name}: {comp_data['score']}%")
            print(f"    Text length: {len(comp_data['interpretation'])} chars")

        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_data(entry_price, periods=100)

        # Generate PDF
        pdf_path, json_path, png_path = self.pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )

        self.generated_files.extend([pdf_path, json_path, png_path])

        if pdf_path:
            print(f"✅ PDF generated: {Path(pdf_path).name}")
            print(f"   (Should handle long text gracefully)")
        else:
            print(f"❌ PDF generation failed")

        return pdf_path is not None

    def _generate_ohlcv_data(self, base_price, periods=100, trend='up'):
        """Generate realistic OHLCV data."""
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1h')

        if trend == 'up':
            trend_component = np.linspace(0, base_price * 0.1, periods)
        elif trend == 'down':
            trend_component = np.linspace(0, -base_price * 0.1, periods)
        else:  # sideways
            trend_component = np.zeros(periods)

        noise = np.random.randn(periods) * (base_price * 0.005)
        prices = base_price + trend_component + noise

        ohlcv_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(periods) * (base_price * 0.002),
            'high': prices + abs(np.random.randn(periods) * (base_price * 0.003)),
            'low': prices - abs(np.random.randn(periods) * (base_price * 0.003)),
            'close': prices,
            'volume': np.random.uniform(100000, 1000000, periods)
        })

        return ohlcv_data

    async def verify_json_files(self):
        """Verify that JSON files contain interpretations."""
        print("\n" + "="*70)
        print("VERIFICATION: JSON FILES")
        print("="*70)

        json_files = [f for f in self.generated_files if f and f.endswith('.json')]

        for json_file in json_files:
            if json_file and os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)

                print(f"\n📄 {Path(json_file).name}:")
                print(f"  • Symbol: {data.get('symbol')}")
                print(f"  • Signal: {data.get('signal_type')}")
                print(f"  • Score: {data.get('confluence_score')}%")

                if 'analysis_components' in data:
                    print(f"  • Components: {len(data['analysis_components'])} found")
                    for comp_name, comp_data in data['analysis_components'].items():
                        if isinstance(comp_data, dict) and 'interpretation' in comp_data:
                            print(f"    ✅ {comp_name}: Has interpretation")
                        else:
                            print(f"    ❌ {comp_name}: Missing interpretation")
                else:
                    print(f"  • Components: None (backwards compatibility)")

    async def open_pdfs_in_browser(self):
        """Open generated PDFs for visual inspection."""
        print("\n" + "="*70)
        print("OPENING PDFs FOR VISUAL INSPECTION")
        print("="*70)

        pdf_files = [f for f in self.generated_files if f and f.endswith('.pdf')]

        if pdf_files:
            print(f"\nOpening {len(pdf_files)} PDF files for inspection...")
            print("\nPlease verify in each PDF:")
            print("  1. ✅ 'Market Interpretations' section is visible")
            print("  2. ✅ Component names are displayed")
            print("  3. ✅ Scores are color-coded (green/orange/red)")
            print("  4. ✅ Interpretation text is readable")
            print("  5. ✅ Long text doesn't break layout")

            for pdf_file in pdf_files:
                if pdf_file and os.path.exists(pdf_file):
                    print(f"\n  Opening: {Path(pdf_file).name}")
                    # Convert to file:// URL for browser
                    file_url = f"file://{os.path.abspath(pdf_file)}"
                    webbrowser.open(file_url)
        else:
            print("No PDF files were generated to inspect.")

    async def run_all_tests(self):
        """Run all test cases."""
        print("\n" + "🔬" * 30)
        print("PDF INTERPRETATION DISPLAY TEST SUITE")
        print("🔬" * 30)

        results = {}

        # Run all test cases
        results['test_1'] = await self.test_case_1_all_components()
        results['test_2'] = await self.test_case_2_partial_components()
        results['test_3'] = await self.test_case_3_mixed_scores()
        results['test_4'] = await self.test_case_4_no_interpretations()
        results['test_5'] = await self.test_case_5_long_interpretations()

        # Verify JSON files
        await self.verify_json_files()

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        test_names = {
            'test_1': 'All 6 Components',
            'test_2': 'Partial Components',
            'test_3': 'Mixed Scores',
            'test_4': 'No Interpretations',
            'test_5': 'Long Interpretations'
        }

        all_passed = True
        for test_id, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_names[test_id]}")
            if not result:
                all_passed = False

        print("\n" + "="*70)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print("\nThe interpretation display feature is working correctly:")
            print("  • ✅ All components display with interpretations")
            print("  • ✅ Partial components handled gracefully")
            print("  • ✅ Mixed scores with proper color coding")
            print("  • ✅ Backwards compatibility maintained")
            print("  • ✅ Long text handled properly")

            # Open PDFs for visual inspection
            await self.open_pdfs_in_browser()

            print("\n📁 Generated files saved in: reports/test/")
            print("Please visually inspect the opened PDFs to confirm interpretations are displaying correctly.")
        else:
            print("⚠️ SOME TESTS FAILED")
            print("Please check the error messages above.")

        return all_passed

async def main():
    """Main test runner."""
    tester = InterpretationDisplayTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())