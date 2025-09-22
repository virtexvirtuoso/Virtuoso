#!/usr/bin/env python3
"""
Comprehensive verification for PDF report generation fixes.

Validates:
1) Reliability normalization (should never render 10000%).
2) Chart overlays and targets: presence of Targets table via defaults when missing.
3) Market interpretations/confluence narrative fallback from formatted_analysis/breakdown.

This is a standalone runner (no pytest dependency required).
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("pdf_comprehensive_test")

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, PROJECT_ROOT)


def create_test_ohlcv(periods: int = 120, base_price: float = 50000.0) -> pd.DataFrame:
    """Create realistic OHLCV DataFrame."""
    rng = np.random.default_rng(42)
    timestamps = [datetime.utcnow() - timedelta(minutes=5 * i) for i in range(periods)][::-1]
    prices = [base_price]
    for _ in range(periods - 1):
        prices.append(max(1000.0, prices[-1] * (1 + rng.normal(0, 0.004))))
    opens = np.array(prices) * (1 + rng.normal(0, 0.0015, periods))
    closes = np.array(prices)
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.002, periods)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.002, periods)))
    volumes = rng.gamma(2.0, 800.0, periods)
    df = pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps),
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
    })
    return df


def get_latest_html_path() -> str:
    html_dir = os.path.join(os.getcwd(), 'reports', 'html')
    if not os.path.isdir(html_dir):
        return None
    files = [os.path.join(html_dir, f) for f in os.listdir(html_dir) if f.endswith('.html')]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def run_generation(signal_data, ohlcv=None, output_dir=None):
    from src.core.reporting.pdf_generator import ReportGenerator
    gen = ReportGenerator()
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'test_output_pdf')
    os.makedirs(output_dir, exist_ok=True)
    result = gen.generate_trading_report(signal_data=signal_data, ohlcv_data=ohlcv, output_dir=output_dir)
    # Support both 2-tuple and 3-tuple returns
    pdf_path = result[0] if result else None
    json_path = result[1] if result and len(result) > 1 else None
    chart_path = result[2] if result and len(result) > 2 else None
    return pdf_path, json_path, chart_path


def test_reliability_normalization() -> bool:
    logger.info("=== Test: Reliability normalization ===")
    base_signal = {
        'symbol': 'BTCUSDT',
        'signal_type': 'BUY',
        'confluence_score': 70.0,
        'price': 50000.0,
        'components': {'technical': {'score': 70}},
        # No trade_params to force fallbacks
    }

    # Case A: reliability provided in 0-1 scale
    sig_a = dict(base_signal, reliability=1.0)
    pdf_a, json_a, _ = run_generation(sig_a, ohlcv=create_test_ohlcv())
    assert pdf_a and os.path.exists(pdf_a), "PDF not generated for reliability 1.0"

    # Allow a brief moment for HTML to be written
    time.sleep(0.3)
    html_path = get_latest_html_path()
    assert html_path and os.path.exists(html_path), "HTML not found after generation"
    with open(html_path, 'r') as f:
        html = f.read()
    assert '10000%' not in html, "Reliability rendered as 10000% (expected normalization)"

    # Case B: reliability provided in 0-100 scale
    sig_b = dict(base_signal, reliability=100)
    pdf_b, json_b, _ = run_generation(sig_b, ohlcv=create_test_ohlcv())
    assert pdf_b and os.path.exists(pdf_b), "PDF not generated for reliability 100"
    time.sleep(0.3)
    html_path_b = get_latest_html_path()
    with open(html_path_b, 'r') as f:
        html_b = f.read()
    assert '10000%' not in html_b, "Reliability rendered as 10000% for 100 input"
    return True


def test_overlay_and_targets_defaults() -> bool:
    logger.info("=== Test: Overlay rendering and default targets ===")
    signal = {
        'symbol': 'BTCUSDT',
        'signal_type': 'BUY',
        'confluence_score': 65.0,
        'price': 51000.0,
        'reliability': 0.8,
        'components': {'technical': {'score': 65}},
        # Intentionally no trade_params/targets to trigger defaults
    }
    pdf_path, json_path, chart_path = run_generation(signal, ohlcv=create_test_ohlcv())
    assert pdf_path and os.path.exists(pdf_path), "PDF not generated"
    assert chart_path and os.path.exists(chart_path), "Chart image not generated"
    time.sleep(0.3)
    html_path = get_latest_html_path()
    with open(html_path, 'r') as f:
        html = f.read()
    assert '<th>Target</th>' in html, "Targets table header missing in HTML"
    assert 'Target 1' in html, "Default Target 1 not present (defaults may have failed)"
    return True


def test_interpretations_fallbacks() -> bool:
    logger.info("=== Test: Interpretations fallbacks ===")
    formatted_text = """
• Technical: Momentum weakening, below LTF VWAP
• Order Flow: Net selling pressure persists
• Market Sentiment: Cautious; funding neutral
""".strip()
    signal = {
        'symbol': 'BTCUSDT',
        'signal_type': 'SELL',
        'confluence_score': 40.0,
        'price': 50500.0,
        'reliability': 0.6,
        'components': {'technical': {'score': 40}},
        # No market_interpretations; use formatted text fallback
        'formatted_analysis': formatted_text,
    }
    pdf_path, json_path, chart_path = run_generation(signal, ohlcv=create_test_ohlcv())
    assert pdf_path and os.path.exists(pdf_path), "PDF not generated"
    time.sleep(0.3)
    html_path = get_latest_html_path()
    with open(html_path, 'r') as f:
        html = f.read()
    # We expect at least pieces of the narrative to surface in the insights section
    assert 'Technical:' in html or 'Order Flow:' in html, "Interpretation fallback text not found in HTML"
    return True


def main() -> int:
    # Clean test output dirs
    out_dir = os.path.join(os.getcwd(), 'test_output_pdf')
    if os.path.isdir(out_dir):
        import shutil
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Run tests
    results = []
    for fn in (test_reliability_normalization, test_overlay_and_targets_defaults, test_interpretations_fallbacks):
        try:
            ok = fn()
        except AssertionError as e:
            logger.error(f"Assertion failed: {e}")
            ok = False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            ok = False
        results.append(ok)

    passed = sum(1 for r in results if r)
    total = len(results)
    logger.info("\n" + "=" * 60)
    logger.info(f"PDF Comprehensive Test Summary: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())


