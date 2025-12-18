#!/usr/bin/env python3
"""
Test reliability scaling edge cases to ensure proper normalization.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), './'))
sys.path.insert(0, PROJECT_ROOT)

def create_test_ohlcv(periods: int = 60, base_price: float = 50000.0) -> pd.DataFrame:
    """Create minimal OHLCV DataFrame."""
    rng = np.random.default_rng(42)
    timestamps = [datetime.now(timezone.utc) - timedelta(minutes=5 * i) for i in range(periods)][::-1]
    prices = [base_price] * periods
    df = pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps),
        'open': prices,
        'high': [p * 1.002 for p in prices],
        'low': [p * 0.998 for p in prices],
        'close': prices,
        'volume': [1000] * periods,
    })
    return df

def test_reliability_edge_cases():
    """Test various reliability input formats to ensure proper normalization."""
    from src.core.reporting.pdf_generator import ReportGenerator

    test_cases = [
        {"reliability": 1.0, "expected": "100.0%", "description": "1.0 scale input"},
        {"reliability": 0.85, "expected": "85.0%", "description": "0.85 scale input"},
        {"reliability": 100, "expected": "100.0%", "description": "100 scale input"},
        {"reliability": 85, "expected": "85.0%", "description": "85 scale input"},
        {"reliability": 1000, "expected": "100.0%", "description": "1000 scale input (should clamp)"},
        {"reliability": 2.5, "expected": "100.0%", "description": "2.5 scale input (should clamp)"},
    ]

    results = []
    gen = ReportGenerator()

    for i, case in enumerate(test_cases):
        signal_data = {
            'symbol': f'TEST{i}USDT',
            'signal_type': 'BUY',
            'confluence_score': 70.0,
            'price': 50000.0,
            'reliability': case["reliability"],
            'components': {'technical': {'score': 70}},
        }

        output_dir = os.path.join(os.getcwd(), 'test_output_edge_cases')
        os.makedirs(output_dir, exist_ok=True)

        try:
            pdf_path, json_path, chart_path = gen.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=create_test_ohlcv(),
                output_dir=output_dir
            )

            # Check if files were generated
            pdf_exists = pdf_path and os.path.exists(pdf_path)

            # Find the corresponding HTML file to check reliability display
            html_files = [f for f in os.listdir(os.path.join(os.getcwd(), 'reports', 'html'))
                         if f.startswith(f'test{i}usdt')]

            html_content = ""
            if html_files:
                html_path = os.path.join(os.getcwd(), 'reports', 'html', html_files[-1])
                if os.path.exists(html_path):
                    with open(html_path, 'r') as f:
                        html_content = f.read()

            # Check if expected percentage appears in HTML
            expected_found = case["expected"] in html_content
            no_10000_percent = "10000%" not in html_content

            results.append({
                "case": case["description"],
                "input": case["reliability"],
                "expected": case["expected"],
                "pdf_generated": pdf_exists,
                "expected_found": expected_found,
                "no_10000_percent": no_10000_percent,
                "passed": pdf_exists and expected_found and no_10000_percent
            })

            print(f"Test {i+1}: {case['description']}")
            print(f"  Input: {case['reliability']}")
            print(f"  Expected: {case['expected']}")
            print(f"  PDF Generated: {pdf_exists}")
            print(f"  Expected Found: {expected_found}")
            print(f"  No 10000%: {no_10000_percent}")
            print(f"  Result: {'PASS' if results[-1]['passed'] else 'FAIL'}")
            print()

        except Exception as e:
            print(f"Test {i+1} FAILED with exception: {e}")
            results.append({
                "case": case["description"],
                "input": case["reliability"],
                "expected": case["expected"],
                "pdf_generated": False,
                "expected_found": False,
                "no_10000_percent": False,
                "passed": False
            })

    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\nReliability Edge Cases Test Summary: {passed}/{total} passed")

    return passed == total

if __name__ == "__main__":
    success = test_reliability_edge_cases()
    sys.exit(0 if success else 1)