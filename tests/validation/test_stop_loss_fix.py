#!/usr/bin/env python3
"""
Test script to verify the stop loss fix in PDF generation.
This tests that the PDF generator properly calculates stop loss when it's missing.
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.reporting.pdf_generator import ReportGenerator
from utils.logging_config import setup_logging

def test_stop_loss_calculation():
    """Test that stop loss is calculated when missing from signal data."""

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Load config
    import yaml
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Create PDF generator
    pdf_gen = ReportGenerator(config)

    # Create test signal data WITHOUT stop_loss
    signal_data = {
        "symbol": "ENAUSDT",
        "price": 0.512,
        "signal_type": "LONG",
        "confluence_score": 70.1,
        "reliability": 100.0,
        "timestamp": "2025-10-27T18:09:23Z",
        "trade_params": {
            "entry_price": 0.512,
            # Note: stop_loss is MISSING - should be calculated
            "targets": {
                "target_1": {"price": 0.535, "change_pct": 4.5, "size_pct": 50},
                "target_2": {"price": 0.550, "change_pct": 7.5, "size_pct": 30},
                "target_3": {"price": 0.573, "change_pct": 12.0, "size_pct": 20}
            }
        },
        "component_data": {
            "orderbook": {"score": 79.2, "impact": 58.4},
            "volume": {"score": 72.3, "impact": 44.5},
            "orderflow": {"score": 70.7, "impact": 41.3},
            "sentiment": {"score": 67.5, "impact": 35.1},
            "technical": {"score": 63.0, "impact": 26.0},
            "price_structure": {"score": 52.3, "impact": 4.5}
        }
    }

    logger.info("=" * 80)
    logger.info("Testing PDF generation with MISSING stop_loss")
    logger.info("=" * 80)
    logger.info(f"Signal: {signal_data['symbol']} {signal_data['signal_type']} @ ${signal_data['price']}")
    logger.info(f"Confluence Score: {signal_data['confluence_score']}")
    logger.info(f"Entry Price: ${signal_data['trade_params']['entry_price']}")
    logger.info(f"Stop Loss in trade_params: {signal_data['trade_params'].get('stop_loss', 'MISSING')}")
    logger.info("")

    # Generate PDF
    try:
        pdf_path, json_path, chart_path = pdf_gen.generate_pdf_report(
            signal_data=signal_data,
            output_dir="src/reports/pdf"
        )

        if pdf_path:
            logger.info(f"✅ PDF generated successfully: {pdf_path}")
            logger.info(f"   JSON: {json_path}")
            logger.info(f"   Chart: {chart_path}")

            # Check if PDF file exists
            if os.path.exists(pdf_path):
                logger.info(f"✅ PDF file exists and is {os.path.getsize(pdf_path)} bytes")

                # Read the JSON to check if stop_loss was calculated
                if json_path and os.path.exists(json_path):
                    import json
                    with open(json_path, 'r') as f:
                        json_data = json.load(f)

                    if 'trade_params' in json_data and 'stop_loss' in json_data['trade_params']:
                        calculated_stop = json_data['trade_params']['stop_loss']
                        logger.info(f"✅ Stop loss was calculated: ${calculated_stop:.6f}")

                        # Calculate expected percentage
                        entry = json_data['trade_params']['entry_price']
                        stop_pct = abs((calculated_stop / entry - 1) * 100)
                        logger.info(f"   Stop loss percentage: {stop_pct:.2f}%")

                        # For a LONG signal with score 70.1, we expect a stop around 2.5-3.5%
                        if 2.0 <= stop_pct <= 4.0:
                            logger.info(f"✅ Stop loss percentage is within expected range (2-4%)")
                            return True
                        else:
                            logger.warning(f"⚠️  Stop loss percentage {stop_pct:.2f}% is outside expected range")
                            return False
                    else:
                        logger.error("❌ Stop loss was not added to JSON data")
                        return False
            else:
                logger.error(f"❌ PDF file does not exist: {pdf_path}")
                return False
        else:
            logger.error("❌ PDF generation failed")
            return False

    except Exception as e:
        logger.error(f"❌ Error during PDF generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_stop_loss_calculation()

    if success:
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Stop loss calculation is working correctly")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED: Stop loss calculation is not working as expected")
        print("=" * 80)
        sys.exit(1)
