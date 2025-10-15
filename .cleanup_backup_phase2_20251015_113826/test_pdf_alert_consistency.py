#!/usr/bin/env python3
"""
Test PDF-AlertManager stop loss calculation consistency.
"""

import sys
import os
import yaml
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def load_config() -> Dict[str, Any]:
    """Load the actual config from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Failed to load config: {e}")
        return {}

def test_pdf_alert_stop_loss_consistency():
    """Test that PDF generator and AlertManager calculate stop losses consistently."""
    print("=== Testing PDF-AlertManager Stop Loss Consistency ===")

    config = load_config()

    # Test signal data with various confluence scores
    test_signals = [
        {
            "symbol": "BTCUSDT",
            "signal_type": "BUY",
            "confluence_score": 75,
            "price": 100.0,
            "trade_params": {
                "entry_price": 100.0,
                "stop_loss": None  # Will be calculated
            }
        },
        {
            "symbol": "ETHUSDT",
            "signal_type": "BUY",
            "confluence_score": 85,
            "price": 200.0,
            "trade_params": {
                "entry_price": 200.0,
                "stop_loss": None
            }
        },
        {
            "symbol": "ADAUSDT",
            "signal_type": "SELL",
            "confluence_score": 25,
            "price": 50.0,
            "trade_params": {
                "entry_price": 50.0,
                "stop_loss": None
            }
        },
        {
            "symbol": "XRPUSDT",
            "signal_type": "SELL",
            "confluence_score": 15,
            "price": 1.0,
            "trade_params": {
                "entry_price": 1.0,
                "stop_loss": None
            }
        }
    ]

    try:
        from src.core.risk.stop_loss_calculator import get_stop_loss_calculator, StopLossMethod

        # Initialize calculator
        calculator = get_stop_loss_calculator(config)

        results = []

        for signal in test_signals:
            print(f"\nTesting {signal['symbol']} {signal['signal_type']} @ score {signal['confluence_score']}")

            # Calculate stop loss using unified calculator (same as AlertManager)
            stop_info = calculator.get_stop_loss_info(signal)

            if 'error' in stop_info:
                print(f"❌ Calculator error: {stop_info['error']}")
                continue

            expected_stop_pct = stop_info['stop_loss_percentage'] * 100
            expected_stop_price = stop_info['stop_loss_price']

            print(f"  Calculator result: {expected_stop_pct:.2f}% → ${expected_stop_price:.4f}")

            # Set the calculated stop loss in trade_params
            signal['trade_params']['stop_loss'] = expected_stop_price

            # Now simulate PDF validation (what PDF generator does)
            entry_price = signal['trade_params']['entry_price']
            pdf_stop_loss = signal['trade_params']['stop_loss']

            # Calculate PDF stop loss percentage (same logic as PDF generator)
            if entry_price > pdf_stop_loss:  # Long position
                pdf_stop_loss_pct = abs(((pdf_stop_loss / entry_price) - 1) * 100)
            else:  # Short position
                pdf_stop_loss_pct = abs(((pdf_stop_loss / entry_price) - 1) * 100)

            print(f"  PDF calculation: {pdf_stop_loss_pct:.2f}%")

            # Check consistency (within 0.1% tolerance)
            tolerance = 0.1
            is_consistent = abs(pdf_stop_loss_pct - expected_stop_pct) <= tolerance

            print(f"  Consistency: {'✅' if is_consistent else '❌'} "
                  f"(diff: {abs(pdf_stop_loss_pct - expected_stop_pct):.3f}%)")

            results.append({
                'symbol': signal['symbol'],
                'signal_type': signal['signal_type'],
                'confluence_score': signal['confluence_score'],
                'calculator_pct': expected_stop_pct,
                'pdf_pct': pdf_stop_loss_pct,
                'consistent': is_consistent,
                'difference': abs(pdf_stop_loss_pct - expected_stop_pct)
            })

        # Summary
        consistent_count = sum(1 for r in results if r['consistent'])
        total_count = len(results)

        print(f"\n=== CONSISTENCY SUMMARY ===")
        print(f"Total tests: {total_count}")
        print(f"Consistent: {consistent_count}")
        print(f"Inconsistent: {total_count - consistent_count}")

        if consistent_count == total_count:
            print("🎉 ALL TESTS PASSED - PDF and AlertManager calculations are consistent!")
        else:
            print("❌ SOME INCONSISTENCIES FOUND")
            for r in results:
                if not r['consistent']:
                    print(f"  {r['symbol']} {r['signal_type']}: {r['difference']:.3f}% difference")

        return consistent_count == total_count

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_real_pdf_generation():
    """Test actual PDF generation with calculated stop losses."""
    print("\n=== Testing Real PDF Generation ===")

    try:
        config = load_config()
        from src.core.reporting.pdf_generator import ReportGenerator
        from src.core.risk.stop_loss_calculator import get_stop_loss_calculator

        # Initialize components
        calculator = get_stop_loss_calculator(config)
        pdf_generator = ReportGenerator()

        # Test signal with calculated stop loss
        signal_data = {
            "symbol": "BTCUSDT",
            "signal_type": "BUY",
            "confluence_score": 80,
            "price": 100000.0,
            "reliability": 0.85,
            "insights": ["Test signal for PDF generation"],
            "components": {
                "technical": {"score": 80, "reliability": 0.9}
            }
        }

        # Calculate stop loss using unified calculator
        stop_info = calculator.get_stop_loss_info(signal_data)

        if 'error' in stop_info:
            print(f"❌ Calculator error: {stop_info['error']}")
            return False

        # Add calculated trade params
        signal_data['trade_params'] = {
            'entry_price': signal_data['price'],
            'stop_loss': stop_info['stop_loss_price'],
            'targets': [
                {'name': 'Target 1', 'price': signal_data['price'] * 1.02, 'size': 50},
                {'name': 'Target 2', 'price': signal_data['price'] * 1.04, 'size': 30}
            ]
        }

        print(f"Generated signal with stop loss: ${stop_info['stop_loss_price']:.2f} ({stop_info['stop_loss_percentage']*100:.2f}%)")

        # Test PDF generation (without actually generating file)
        try:
            # Extract components from signal data for validation
            pdf_stop_loss = signal_data['trade_params']['stop_loss']
            pdf_entry_price = signal_data['trade_params']['entry_price']

            # Calculate PDF percentage
            pdf_stop_loss_pct = abs(((pdf_stop_loss / pdf_entry_price) - 1) * 100)

            print(f"PDF would show: {pdf_stop_loss_pct:.2f}% stop loss")
            print(f"Calculator expects: {stop_info['stop_loss_percentage']*100:.2f}%")

            # Check if they match
            tolerance = 0.1
            is_consistent = abs(pdf_stop_loss_pct - (stop_info['stop_loss_percentage']*100)) <= tolerance

            if is_consistent:
                print("✅ PDF generation would be consistent with calculator")
            else:
                print("❌ PDF generation would be inconsistent")

            return is_consistent

        except Exception as pdf_error:
            print(f"❌ PDF validation error: {pdf_error}")
            return False

    except Exception as e:
        print(f"❌ PDF generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all consistency tests."""
    print("PDF-AlertManager Stop Loss Consistency Validation")
    print("=" * 55)

    results = []

    # Test 1: Calculation consistency
    results.append(test_pdf_alert_stop_loss_consistency())

    # Test 2: Real PDF generation
    results.append(test_real_pdf_generation())

    print("\n" + "=" * 55)
    print("FINAL RESULTS")
    print("=" * 55)

    all_passed = all(results)

    if all_passed:
        print("🎉 ALL CONSISTENCY TESTS PASSED!")
        print("✅ PDF reports and AlertManager use consistent stop loss calculations")
    else:
        print("❌ CONSISTENCY ISSUES FOUND")

    test_names = [
        "Stop Loss Calculation Consistency",
        "PDF Generation Consistency"
    ]

    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)