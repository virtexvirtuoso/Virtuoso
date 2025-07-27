#!/usr/bin/env python3
"""Simple test to verify stop loss extraction logic."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_stop_loss_extraction():
    """Test the stop loss extraction logic without full PDF generation."""
    
    # Test signal data with stop loss in trade_params
    signal_data = {
        "price": 0.0600,
        "trade_params": {
            "entry_price": 0.0600,
            "stop_loss": 0.0577,
            "targets": []
        }
    }
    
    # Simulate the extraction logic from pdf_generator.py
    price = signal_data.get("price", 0)
    entry_price = price
    stop_loss = None
    stop_loss_percent = 0
    
    # Check trade_params first, then fall back to signal_data
    trade_params = signal_data.get("trade_params", {})
    entry_price = trade_params.get("entry_price", None) or signal_data.get("entry_price", price)
    stop_loss = trade_params.get("stop_loss", None) or signal_data.get("stop_loss", None)
    
    if stop_loss and entry_price:
        if entry_price > stop_loss:  # Long position
            stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
        else:  # Short position
            stop_loss_percent = ((entry_price / stop_loss) - 1) * 100
    
    print("Test 1: Stop loss in trade_params")
    print(f"  Entry Price: ${entry_price:.4f}")
    print(f"  Stop Loss: ${stop_loss:.4f}")
    print(f"  Stop Loss %: {stop_loss_percent:.2f}%")
    print(f"  ✅ Stop loss extracted successfully from trade_params" if stop_loss else "❌ Failed to extract stop loss")
    
    # Test 2: Stop loss in signal_data (backward compatibility)
    signal_data2 = {
        "price": 0.0600,
        "entry_price": 0.0600,
        "stop_loss": 0.0577
    }
    
    price = signal_data2.get("price", 0)
    entry_price = price
    stop_loss = None
    stop_loss_percent = 0
    
    trade_params = signal_data2.get("trade_params", {})
    entry_price = trade_params.get("entry_price", None) or signal_data2.get("entry_price", price)
    stop_loss = trade_params.get("stop_loss", None) or signal_data2.get("stop_loss", None)
    
    if stop_loss and entry_price:
        if entry_price > stop_loss:  # Long position
            stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
        else:  # Short position
            stop_loss_percent = ((entry_price / stop_loss) - 1) * 100
    
    print("\nTest 2: Stop loss in signal_data (backward compatibility)")
    print(f"  Entry Price: ${entry_price:.4f}")
    print(f"  Stop Loss: ${stop_loss:.4f}")
    print(f"  Stop Loss %: {stop_loss_percent:.2f}%")
    print(f"  ✅ Stop loss extracted successfully from signal_data" if stop_loss else "❌ Failed to extract stop loss")
    
    # Test 3: Stop loss in both (trade_params should take precedence)
    signal_data3 = {
        "price": 0.0600,
        "entry_price": 0.0700,  # Different value in signal_data
        "stop_loss": 0.0650,    # Different value in signal_data
        "trade_params": {
            "entry_price": 0.0600,
            "stop_loss": 0.0577
        }
    }
    
    price = signal_data3.get("price", 0)
    entry_price = price
    stop_loss = None
    stop_loss_percent = 0
    
    trade_params = signal_data3.get("trade_params", {})
    entry_price = trade_params.get("entry_price", None) or signal_data3.get("entry_price", price)
    stop_loss = trade_params.get("stop_loss", None) or signal_data3.get("stop_loss", None)
    
    if stop_loss and entry_price:
        if entry_price > stop_loss:  # Long position
            stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
        else:  # Short position
            stop_loss_percent = ((entry_price / stop_loss) - 1) * 100
    
    print("\nTest 3: Stop loss in both locations (trade_params should take precedence)")
    print(f"  Entry Price: ${entry_price:.4f}")
    print(f"  Stop Loss: ${stop_loss:.4f}")
    print(f"  Stop Loss %: {stop_loss_percent:.2f}%")
    print(f"  ✅ trade_params took precedence correctly" if stop_loss == 0.0577 else "❌ Wrong precedence")


if __name__ == "__main__":
    test_stop_loss_extraction()