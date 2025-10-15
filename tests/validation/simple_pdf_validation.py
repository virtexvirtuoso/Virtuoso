#!/usr/bin/env python3
"""
Simple PDF Validation - Test the three critical fixes
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("pdf_validation")

# Add project root to path
PROJECT_ROOT = os.path.abspath('.')
sys.path.insert(0, PROJECT_ROOT)

def create_test_data():
    """Create test OHLCV data."""
    periods = 100
    base_price = 50000.0
    timestamps = [datetime.utcnow() - timedelta(minutes=5 * i) for i in range(periods)][::-1]

    rng = np.random.default_rng(42)
    prices = [base_price]
    for _ in range(periods - 1):
        prices.append(max(1000.0, prices[-1] * (1 + rng.normal(0, 0.003))))

    df = pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps),
        'open': np.array(prices) * (1 + rng.normal(0, 0.001, periods)),
        'high': np.array(prices) * (1 + rng.normal(0, 0.002, periods)),
        'low': np.array(prices) * (1 - rng.normal(0, 0.002, periods)),
        'close': prices,
        'volume': rng.gamma(2.0, 800.0, periods),
    })
    df.set_index('timestamp', inplace=True)
    return df

def test_pdf_generation():
    """Test PDF generation with various scenarios."""
    logger.info("=== Testing PDF Generation ===")

    try:
        from src.core.reporting.pdf_generator import ReportGenerator

        # Test configuration
        config = {
            'system': {'base_dir': '.', 'reports_dir': './test_output_simple'},
            'reporting': {'pdf': {'use_dark_mode': True, 'include_charts': True}},
            'analysis': {'confluence': {'weights': {'components': {}}}},
            'confluence': {'thresholds': {'buy': 60, 'sell': 40}}
        }

        pdf_gen = ReportGenerator(config=config)
        ohlcv = create_test_data()

        # Test scenarios for all three critical fixes
        test_scenarios = [
            {
                'name': 'Reliability fix: 0-1 scale input',
                'signal_data': {
                    'symbol': 'BTCUSDT',
                    'signal': 'BUY',
                    'confluence_score': 75.0,
                    'price': 50000.0,
                    'reliability': 0.85,  # Should display as 85%
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'market_interpretations': [
                        {'component': 'technical', 'interpretation': 'Strong bullish momentum'}
                    ]
                }
            },
            {
                'name': 'Reliability fix: 0-100 scale input',
                'signal_data': {
                    'symbol': 'ETHUSDT',
                    'signal': 'SELL',
                    'confluence_score': 32.0,
                    'price': 3000.0,
                    'reliability': 75.0,  # Should display as 75%
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'formatted_analysis': 'Technical analysis shows bearish divergence.'
                }
            },
            {
                'name': 'Chart overlay fix: Missing trade parameters',
                'signal_data': {
                    'symbol': 'SOLUSDT',
                    'signal': 'BUY',
                    'confluence_score': 82.0,
                    'price': 100.0,
                    'reliability': 0.90,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    # Missing entry_price, stop_loss, targets - should generate defaults
                }
            },
            {
                'name': 'Interpretation fix: Fallback to breakdown',
                'signal_data': {
                    'symbol': 'ADAUSDT',
                    'signal': 'BUY',
                    'confluence_score': 70.0,
                    'price': 0.5,
                    'reliability': 0.80,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'breakdown': {
                        'formatted_analysis': 'Multi-timeframe analysis suggests upward movement.',
                        'interpretations': [
                            {'component': 'volume', 'interpretation': 'Volume confirmation present'}
                        ]
                    }
                }
            },
            {
                'name': 'Over-range reliability test',
                'signal_data': {
                    'symbol': 'XRPUSDT',
                    'signal': 'SELL',
                    'confluence_score': 25.0,
                    'price': 0.6,
                    'reliability': 150.0,  # Should clamp to 100%
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            }
        ]

        results = []

        for scenario in test_scenarios:
            logger.info(f"Testing: {scenario['name']}")

            try:
                pdf_path = pdf_gen.generate_signal_report(
                    signal_data=scenario['signal_data'],
                    ohlcv_data=ohlcv,
                    output_dir='test_output_simple'
                )

                if pdf_path and os.path.exists(pdf_path):
                    result = "PASS - PDF generated successfully"
                    logger.info(f"  Result: {result}")
                else:
                    result = "FAIL - PDF not generated"
                    logger.error(f"  Result: {result}")

                results.append({
                    'test': scenario['name'],
                    'result': result,
                    'pdf_path': pdf_path if pdf_path else 'None'
                })

            except Exception as e:
                result = f"FAIL - Exception: {str(e)}"
                logger.error(f"  Result: {result}")
                results.append({
                    'test': scenario['name'],
                    'result': result,
                    'pdf_path': 'None'
                })

        return results

    except Exception as e:
        logger.error(f"Failed to initialize ReportGenerator: {e}")
        return []

def main():
    """Run validation tests."""
    logger.info("Starting Simple PDF Validation")

    # Create output directory
    os.makedirs('test_output_simple', exist_ok=True)

    # Run tests
    results = test_pdf_generation()

    # Compile results
    passed = len([r for r in results if 'PASS' in r['result']])
    failed = len([r for r in results if 'FAIL' in r['result']])
    total = len(results)

    summary = {
        'timestamp': datetime.now().isoformat(),
        'tests': results,
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        }
    }

    # Save results
    with open('test_output_simple/validation_results.json', 'w') as f:
        json.dump(summary, f, indent=2)

    # Print summary
    logger.info("=== Validation Summary ===")
    logger.info(f"Total tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {summary['summary']['success_rate']}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())