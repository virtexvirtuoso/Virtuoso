#!/usr/bin/env python3
"""
Edge Cases Validation for PDF Reporting Fixes

This script tests various edge cases to ensure the fixes work correctly:
1. Reliability values in different formats (0-1, 0-100, >100, negative)
2. Missing market interpretations with various fallback sources
3. Missing trade parameters forcing default generation
4. Extreme values and error conditions
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("edge_cases_validation")

sys.path.insert(0, os.getcwd())

def create_test_ohlcv(base_price: float = 50000.0) -> pd.DataFrame:
    """Create test OHLCV data."""
    rng = np.random.default_rng(42)
    periods = 100
    prices = [base_price]
    for _ in range(periods - 1):
        prices.append(max(1000.0, prices[-1] * (1 + rng.normal(0, 0.004))))

    dates = pd.date_range(end=datetime.now(timezone.utc), periods=periods, freq="5min")
    opens = np.array(prices) * (1 + rng.normal(0, 0.0015, periods))
    closes = np.array(prices)
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.002, periods)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.002, periods)))
    volumes = rng.gamma(2.0, 800.0, periods)

    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
    })

def test_reliability_edge_cases():
    """Test various reliability value formats and edge cases."""
    from src.core.reporting.pdf_generator import ReportGenerator

    test_cases = [
        ("0-1 scale normal", 0.75),
        ("0-100 scale normal", 85.0),
        ("Over 100%", 150.0),
        ("Negative value", -10.0),
        ("Zero", 0.0),
        ("Edge case 1.0", 1.0),
        ("Edge case 100.0", 100.0),
        ("String number", "95.5"),
        ("Invalid string", "not_a_number"),
        ("None value", None),
    ]

    logger.info("=== Testing Reliability Edge Cases ===")
    results = []

    for case_name, reliability_value in test_cases:
        try:
            signal_data = {
                'symbol': 'TESTUSDT',
                'signal_type': 'BUY',
                'confluence_score': 70.0,
                'price': 50000.0,
                'reliability': reliability_value,
                'components': {'technical': {'score': 70}},
            }

            gen = ReportGenerator()
            pdf_path, json_path, chart_path = gen.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=create_test_ohlcv(),
                output_dir='test_edge_cases_output'
            )

            # Check the HTML output for reliability display
            html_files = [f for f in os.listdir('reports/html') if f.endswith('.html')]
            if html_files:
                latest_html = max(html_files, key=lambda f: os.path.getctime(os.path.join('reports/html', f)))
                with open(os.path.join('reports/html', latest_html), 'r') as f:
                    html_content = f.read()

                # Extract reliability value from HTML
                import re
                reliability_match = re.search(r'reliability.*?(\d+\.?\d*)%', html_content, re.IGNORECASE)
                displayed_reliability = float(reliability_match.group(1)) if reliability_match else None

                # Validate it's within expected range
                is_valid = displayed_reliability is not None and 0 <= displayed_reliability <= 100
                results.append((case_name, reliability_value, displayed_reliability, is_valid))

                logger.info(f"{case_name}: {reliability_value} -> {displayed_reliability}% ({'PASS' if is_valid else 'FAIL'})")
            else:
                results.append((case_name, reliability_value, None, False))
                logger.error(f"{case_name}: No HTML output generated")

        except Exception as e:
            results.append((case_name, reliability_value, None, False))
            logger.error(f"{case_name}: Error - {str(e)}")

    return results

def test_interpretations_fallback_scenarios():
    """Test market interpretations fallback mechanisms."""
    from src.core.reporting.pdf_generator import ReportGenerator

    test_cases = [
        ("No interpretations", {}),
        ("Only formatted_analysis", {
            'formatted_analysis': "• RSI: Oversold conditions detected\n• MACD: Bullish crossover emerging\n• Volume: Above average activity"
        }),
        ("Only breakdown.formatted_analysis", {
            'breakdown': {
                'formatted_analysis': "Technical momentum building upward\nOrder flow shows net buying pressure"
            }
        }),
        ("Empty market_interpretations", {
            'market_interpretations': []
        }),
        ("Invalid market_interpretations", {
            'market_interpretations': "not_a_list"
        }),
        ("Mixed format interpretations", {
            'market_interpretations': [
                "Simple string interpretation",
                {"display_name": "Technical", "interpretation": "Strong momentum"},
                {"display_name": "Volume", "interpretation": "High activity"}
            ]
        }),
    ]

    logger.info("=== Testing Market Interpretations Fallbacks ===")
    results = []

    for case_name, extra_data in test_cases:
        try:
            signal_data = {
                'symbol': 'TESTUSDT',
                'signal_type': 'BUY',
                'confluence_score': 65.0,
                'price': 50000.0,
                'reliability': 0.8,
                'components': {'technical': {'score': 65}},
                **extra_data
            }

            gen = ReportGenerator()
            pdf_path, json_path, chart_path = gen.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=create_test_ohlcv(),
                output_dir='test_edge_cases_output'
            )

            # Check if HTML contains interpretations section
            html_files = [f for f in os.listdir('reports/html') if f.endswith('.html')]
            if html_files:
                latest_html = max(html_files, key=lambda f: os.path.getctime(os.path.join('reports/html', f)))
                with open(os.path.join('reports/html', latest_html), 'r') as f:
                    html_content = f.read()

                has_interpretations = 'Market Interpretations' in html_content
                has_insights = 'insight-item' in html_content
                results.append((case_name, has_interpretations, has_insights))

                logger.info(f"{case_name}: Interpretations={has_interpretations}, Insights={has_insights}")
            else:
                results.append((case_name, False, False))
                logger.error(f"{case_name}: No HTML output generated")

        except Exception as e:
            results.append((case_name, False, False))
            logger.error(f"{case_name}: Error - {str(e)}")

    return results

def test_chart_overlay_scenarios():
    """Test chart overlay generation with missing data."""
    from src.core.reporting.pdf_generator import ReportGenerator

    test_cases = [
        ("No trade_params", {}),
        ("Missing entry_price", {'trade_params': {'stop_loss': 48000, 'targets': []}}),
        ("Missing stop_loss", {'trade_params': {'entry_price': 50000, 'targets': []}}),
        ("Missing targets", {'trade_params': {'entry_price': 50000, 'stop_loss': 48000}}),
        ("Empty targets", {'trade_params': {'entry_price': 50000, 'stop_loss': 48000, 'targets': {}}}),
        ("Complete trade_params", {
            'trade_params': {
                'entry_price': 50000,
                'stop_loss': 48000,
                'targets': {'Target 1': {'price': 52000, 'size': 50}}
            }
        }),
    ]

    logger.info("=== Testing Chart Overlay Scenarios ===")
    results = []

    for case_name, trade_data in test_cases:
        try:
            signal_data = {
                'symbol': 'TESTUSDT',
                'signal_type': 'BUY',
                'confluence_score': 70.0,
                'price': 50000.0,
                'reliability': 0.8,
                'components': {'technical': {'score': 70}},
                **trade_data
            }

            gen = ReportGenerator()
            pdf_path, json_path, chart_path = gen.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=create_test_ohlcv(),
                output_dir='test_edge_cases_output'
            )

            # Check if chart was generated and HTML contains targets table
            chart_exists = chart_path and os.path.exists(chart_path)

            html_files = [f for f in os.listdir('reports/html') if f.endswith('.html')]
            has_targets_table = False
            if html_files:
                latest_html = max(html_files, key=lambda f: os.path.getctime(os.path.join('reports/html', f)))
                with open(os.path.join('reports/html', latest_html), 'r') as f:
                    html_content = f.read()
                has_targets_table = 'Target' in html_content and 'Price' in html_content

            results.append((case_name, chart_exists, has_targets_table))
            logger.info(f"{case_name}: Chart={chart_exists}, Targets Table={has_targets_table}")

        except Exception as e:
            results.append((case_name, False, False))
            logger.error(f"{case_name}: Error - {str(e)}")

    return results

def main():
    """Run all edge case tests."""
    # Clean output directory
    os.makedirs('test_edge_cases_output', exist_ok=True)

    # Run all test suites
    reliability_results = test_reliability_edge_cases()
    interpretations_results = test_interpretations_fallback_scenarios()
    chart_results = test_chart_overlay_scenarios()

    # Summary
    logger.info("\n" + "="*80)
    logger.info("EDGE CASES VALIDATION SUMMARY")
    logger.info("="*80)

    logger.info(f"Reliability Edge Cases: {sum(1 for r in reliability_results if r[3])}/{len(reliability_results)} passed")
    logger.info(f"Interpretations Fallbacks: {sum(1 for r in interpretations_results if r[1] or r[2])}/{len(interpretations_results)} passed")
    logger.info(f"Chart Overlays: {sum(1 for r in chart_results if r[1] and r[2])}/{len(chart_results)} passed")

    # Detailed results
    logger.info("\nDETAILED RESULTS:")
    logger.info("Reliability Cases:")
    for case_name, input_val, output_val, is_valid in reliability_results:
        status = "✓" if is_valid else "✗"
        logger.info(f"  {status} {case_name}: {input_val} -> {output_val}%")

    return 0

if __name__ == "__main__":
    sys.exit(main())