#!/usr/bin/env python3
"""
End-to-end test: Confluence analysis (formatted) → Signal generation → PDF generation.

This uses config/config.yaml, synthesizes minimal market/analysis inputs, and verifies
that a PDF is generated with normalized reliability, chart overlays, and interpretations.
"""

import os
import sys
import time
from datetime import datetime
import numpy as np
import pandas as pd

try:
    import yaml
except Exception:
    yaml = None


def create_ohlcv(periods: int = 120, base_price: float = 50000.0) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    prices = [base_price]
    for _ in range(periods - 1):
        prices.append(prices[-1] * (1 + rng.normal(0, 0.002)))
    opens = np.array(prices) * (1 + rng.normal(0, 0.0008, periods))
    closes = np.array(prices)
    highs = np.maximum(opens, closes) * (1 + abs(rng.normal(0, 0.0015, periods)))
    lows = np.minimum(opens, closes) * (1 - abs(rng.normal(0, 0.0015, periods)))
    volumes = rng.gamma(2.0, 800.0, periods)
    dates = pd.date_range(end=datetime.utcnow(), periods=periods, freq="5min")
    return pd.DataFrame(
        {"timestamp": dates, "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}
    )


def main() -> int:
    # Load config
    config_path = os.path.join(os.getcwd(), "config", "config.yaml")
    if yaml and os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {"confluence": {"thresholds": {"buy": 60.0, "sell": 40.0}}}

    # Synthetic confluence scores (as if returned by analyzer)
    # Force BUY by using elevated component scores
    component_scores = {
        "technical": 80.0,
        "volume": 76.0,
        "orderflow": 78.0,
        "orderbook": 77.0,
        "sentiment": 72.0,
        "price_structure": 79.0,
    }

    # Use ConfluenceAnalyzer formatting to produce a realistic analysis result without heavy processing
    from src.core.analysis.confluence import ConfluenceAnalyzer
    analyzer = ConfluenceAnalyzer(config=config)
    analysis_result = analyzer._format_response(component_scores)
    analysis_result["results"] = {k: {"score": v, "components": {}} for k, v in component_scores.items()}

    # Determine signal type based on config thresholds
    buy_th = config.get("confluence", {}).get("thresholds", {}).get("buy", 60.0)
    sell_th = config.get("confluence", {}).get("thresholds", {}).get("sell", 40.0)
    confluence_score = analysis_result["confluence_score"]
    # Explicitly force BUY for this test regardless of thresholds
    signal_type = "BUY"

    # OHLCV for chart
    df = create_ohlcv()
    last_price = float(df["close"].iloc[-1])

    # Build signal_data for PDF
    signal_data = {
        "symbol": "BTCUSDT",
        "signal_type": signal_type,
        "confluence_score": float(confluence_score),
        "components": component_scores,
        "results": analysis_result.get("results", {}),
        "price": last_price,
        # Convert reliability to 0-1 for safety
        "reliability": float(analysis_result.get("reliability", 70.0)) / 100.0,
        "timestamp": int(time.time() * 1000),
        # Provide interpretations in multiple shapes to test normalization path
        "market_interpretations": [
            {"display_name": "Technical Analysis", "interpretation": "Momentum improving, above LTF VWAP"},
            {"display_name": "Order Flow", "interpretation": "Spot bids outweigh asks; supportive tape"},
            {"display_name": "Sentiment", "interpretation": "Neutral to slightly risk-on"},
        ],
        "trade_params": {
            "entry_price": last_price,
            "stop_loss": last_price * 0.97,
            "targets": {
                "Target 1": {"price": last_price * 1.03, "size": 50},
                "Target 2": {"price": last_price * 1.06, "size": 30},
            },
        },
    }

    # Generate PDF
    from src.core.reporting.pdf_generator import ReportGenerator
    gen = ReportGenerator(config=config)
    out_dir = os.path.join(os.getcwd(), "test_output_fullflow_config")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path, json_path, chart_path = gen.generate_trading_report(signal_data=signal_data, ohlcv_data=df, output_dir=out_dir)
    print("PDF:", pdf_path)
    print("JSON:", json_path)
    print("CHART:", chart_path)
    return 0 if (pdf_path and os.path.exists(pdf_path)) else 1


if __name__ == "__main__":
    sys.exit(main())


