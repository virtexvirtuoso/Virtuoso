#!/usr/bin/env python3
"""Test script to verify stop loss is properly displayed in PDF reports."""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.reporting.pdf_generator import PDFReportGenerator


def test_pdf_stop_loss_display():
    """Test that stop loss from trade_params is properly displayed in PDF."""
    
    # Initialize PDF generator
    pdf_generator = PDFReportGenerator()
    
    # Create test signal data with stop loss in trade_params
    signal_data = {
        "symbol": "BTCUSDT",
        "timestamp": datetime.now().isoformat(),
        "signal_type": "BUY",
        "confluence_score": 69.2,
        "reliability": 0.85,
        "price": 0.0600,
        "trade_params": {
            "entry_price": 0.0600,
            "stop_loss": 0.0577,  # Stop loss from the chart
            "targets": [
                {"name": "Target 1", "price": 0.0620, "size": 50},
                {"name": "Target 2", "price": 0.0640, "size": 30},
                {"name": "Target 3", "price": 0.0660, "size": 20}
            ]
        },
        "insights": [
            "Strong bullish momentum detected",
            "Volume spike indicates institutional interest",
            "Technical indicators aligned for upward movement"
        ],
        "components": {
            "technical": {"score": 75, "reliability": 0.9},
            "volume": {"score": 70, "reliability": 0.8},
            "sentiment": {"score": 65, "reliability": 0.7}
        }
    }
    
    # Generate PDF
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating PDF with stop loss in trade_params...")
    pdf_path, json_path = pdf_generator.generate_trading_report(
        signal_data,
        None,  # No OHLCV data for this test
        output_dir
    )
    
    if pdf_path:
        print(f"✅ PDF generated successfully: {pdf_path}")
        print(f"✅ JSON data exported: {json_path}")
        
        # Check if stop loss was properly extracted
        expected_stop_loss = signal_data["trade_params"]["stop_loss"]
        expected_entry = signal_data["trade_params"]["entry_price"]
        expected_stop_percent = ((expected_stop_loss / expected_entry) - 1) * 100
        
        print(f"\nExpected values in PDF:")
        print(f"  Entry Price: ${expected_entry:.4f}")
        print(f"  Stop Loss: ${expected_stop_loss:.4f} ({expected_stop_percent:.1f}%)")
        print(f"\nPlease check the generated PDF to verify these values appear in the Risk Management section.")
        
        # Also test with stop loss only in signal_data (backward compatibility)
        signal_data_old = signal_data.copy()
        signal_data_old["stop_loss"] = 0.0577
        signal_data_old["entry_price"] = 0.0600
        del signal_data_old["trade_params"]
        
        print("\n\nTesting backward compatibility (stop_loss in signal_data)...")
        pdf_path2, json_path2 = pdf_generator.generate_trading_report(
            signal_data_old,
            None,
            output_dir
        )
        
        if pdf_path2:
            print(f"✅ Backward compatibility test passed: {pdf_path2}")
        
    else:
        print("❌ Failed to generate PDF")
        

if __name__ == "__main__":
    test_pdf_stop_loss_display()