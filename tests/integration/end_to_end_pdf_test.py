#!/usr/bin/env python3
"""
End-to-end integration test for PDF generation with the fixes.
This test simulates a complete PDF generation workflow.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.reporting.pdf_generator import ReportGenerator

def test_end_to_end_pdf_generation():
    """Test end-to-end PDF generation with the three critical fixes"""

    print("Starting end-to-end PDF generation test...")

    generator = ReportGenerator()
    temp_dir = tempfile.mkdtemp()

    # Test case 1: Reliability fix (was showing 10,000% instead of 100%)
    signal_data_reliability = {
        "symbol": "BTCUSDT",
        "signal_type": "BUY",
        "confluence_score": 85,
        "price": 50000.0,
        "reliability": 100,  # This was the problematic case (100 -> 10,000%)
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_interpretations": [
            "Strong bullish momentum confirmed",
            "Key resistance level broken with volume"
        ],
        "trade_params": {
            "entry_price": 50000,
            "stop_loss": 48500,
            "targets": [
                {"name": "Target 1", "price": 52000, "size": 50},
                {"name": "Target 2", "price": 54000, "size": 30}
            ]
        }
    }

    # Test case 2: Missing chart overlays fix
    signal_data_chart = {
        "symbol": "ETHUSDT",
        "signal_type": "SELL",
        "confluence_score": 78,
        "price": 3000.0,
        "reliability": 0.8,  # Decimal format
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_interpretations": [
            "Bearish divergence detected",
            "Support level likely to break"
        ],
        "trade_params": {
            # Missing entry_price to test fallback
            "stop_loss": 3100  # Will test auto-generation of targets
        }
    }

    # Test case 3: Missing market interpretations fix
    signal_data_interpretations = {
        "symbol": "ADAUSDT",
        "signal_type": "BUY",
        "confluence_score": 72,
        "price": 1.5,
        "reliability": 0.75,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # No market_interpretations - should fallback to breakdown.interpretations
        "breakdown": {
            "interpretations": [
                "Technical breakout confirmed",
                "Volume surge supporting move"
            ],
            "formatted_analysis": "Strong technical setup with multiple confirmations"
        },
        "trade_params": {
            "entry_price": 1.5,
            "stop_loss": 1.45,
            "targets": [
                {"name": "Target 1", "price": 1.60, "size": 60}
            ]
        }
    }

    test_cases = [
        ("reliability_fix", signal_data_reliability),
        ("chart_overlay_fix", signal_data_chart),
        ("interpretations_fix", signal_data_interpretations)
    ]

    results = []

    for test_name, signal_data in test_cases:
        try:
            print(f"\nTesting {test_name}...")

            # Generate PDF
            pdf_path, json_path, chart_path = generator.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=None,  # Will trigger simulated chart
                output_dir=temp_dir
            )

            success = pdf_path is not None

            if success and os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"✓ {test_name}: PDF generated successfully ({file_size} bytes)")
                results.append((test_name, True, f"PDF size: {file_size} bytes"))
            else:
                print(f"✗ {test_name}: PDF generation failed")
                results.append((test_name, False, "PDF generation failed"))

        except Exception as e:
            print(f"✗ {test_name}: Exception - {str(e)}")
            results.append((test_name, False, f"Exception: {str(e)}"))

    # Summary
    print("\n" + "="*60)
    print("END-TO-END PDF GENERATION TEST RESULTS")
    print("="*60)

    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)

    for test_name, success, details in results:
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {details}")

    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
    print(f"Temp directory: {temp_dir}")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = test_end_to_end_pdf_generation()
    sys.exit(0 if success else 1)