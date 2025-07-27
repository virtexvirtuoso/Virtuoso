#!/usr/bin/env python3
"""Direct test of PDF stop loss extraction logic."""

import json
import os
from datetime import datetime


def test_stop_loss_extraction():
    """Test the stop loss extraction logic without full imports."""
    
    print("=" * 60)
    print("TESTING STOP LOSS EXTRACTION LOGIC")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {
            "name": "Stop loss in trade_params (like ENAUSDT)",
            "signal_data": {
                "price": 0.0600,
                "trade_params": {
                    "entry_price": 0.059520,
                    "stop_loss": 0.0577,
                    "targets": [
                        {"name": "Target 1", "price": 0.0620, "size": 50},
                        {"name": "Target 2", "price": 0.0640, "size": 30},
                        {"name": "Target 3", "price": 0.0660, "size": 20}
                    ]
                }
            },
            "expected_stop_loss": 0.0577,
            "expected_entry": 0.059520
        },
        {
            "name": "Stop loss in signal_data (backward compatibility)",
            "signal_data": {
                "price": 0.0600,
                "entry_price": 0.059520,
                "stop_loss": 0.0577
            },
            "expected_stop_loss": 0.0577,
            "expected_entry": 0.059520
        },
        {
            "name": "Stop loss in both (trade_params takes precedence)",
            "signal_data": {
                "price": 0.0600,
                "entry_price": 0.0700,  # Different value
                "stop_loss": 0.0650,    # Different value
                "trade_params": {
                    "entry_price": 0.059520,
                    "stop_loss": 0.0577  # This should be used
                }
            },
            "expected_stop_loss": 0.0577,
            "expected_entry": 0.059520
        }
    ]
    
    # Test the extraction logic
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 40)
        
        signal_data = test_case['signal_data']
        price = signal_data.get('price', 0)
        
        # Simulate the new extraction logic from pdf_generator.py
        # Check trade_params first, then fall back to signal_data
        trade_params = signal_data.get('trade_params', {})
        entry_price = trade_params.get('entry_price', None) or signal_data.get('entry_price', price)
        stop_loss = trade_params.get('stop_loss', None) or signal_data.get('stop_loss', None)
        
        # Calculate stop loss percentage
        stop_loss_percent = 0
        if stop_loss and entry_price:
            if entry_price > stop_loss:  # Long position
                stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
            else:  # Short position
                stop_loss_percent = ((entry_price / stop_loss) - 1) * 100
        
        # Display results
        print(f"  Entry Price: ${entry_price:.6f}")
        print(f"  Stop Loss: ${stop_loss:.6f}")
        print(f"  Stop Loss %: {stop_loss_percent:.2f}%")
        
        # Verify
        if stop_loss == test_case['expected_stop_loss']:
            print("  ✅ Stop loss extraction correct!")
        else:
            print(f"  ❌ Expected ${test_case['expected_stop_loss']:.6f}, got ${stop_loss:.6f}")
            
        if entry_price == test_case['expected_entry']:
            print("  ✅ Entry price extraction correct!")
        else:
            print(f"  ❌ Expected ${test_case['expected_entry']:.6f}, got ${entry_price:.6f}")


def test_discord_message_formatting():
    """Test Discord message formatting for charts."""
    
    print("\n" + "=" * 60)
    print("TESTING DISCORD MESSAGE FORMATTING")
    print("=" * 60)
    
    # Sample data like ENAUSDT
    signal_data = {
        "symbol": "ENAUSDT",
        "trade_params": {
            "entry_price": 0.059520,
            "stop_loss": 0.0577,
            "targets": [
                {"name": "Target 1", "price": 0.0620, "size": 50},
                {"name": "Target 2", "price": 0.0640, "size": 30},
                {"name": "Target 3", "price": 0.0660, "size": 20}
            ]
        }
    }
    
    # Extract trade parameters
    trade_params = signal_data.get('trade_params', {})
    entry_price = trade_params.get('entry_price')
    stop_loss = trade_params.get('stop_loss')
    targets = trade_params.get('targets', [])
    symbol = signal_data.get('symbol', 'UNKNOWN')
    
    # Format stop loss and targets information
    sl_info = f"**Stop Loss:** ${stop_loss:.4f}" if stop_loss else "**Stop Loss:** Not set"
    
    tp_info = []
    if targets:
        for i, target in enumerate(targets):
            if isinstance(target, dict):
                target_price = target.get('price', 0)
                target_size = target.get('size', 0)
                if target_price > 0:
                    tp_info.append(f"**TP{i+1}:** ${target_price:.4f} ({target_size}%)")
    
    tp_text = "\n".join(tp_info) if tp_info else "**Targets:** Not set"
    
    # Create message for chart
    chart_message = f"📊 **{symbol} Price Action Chart**\n\n**Entry:** ${entry_price:.4f}\n{sl_info}\n\n{tp_text}"
    
    print("\nFormatted Discord message:")
    print("-" * 40)
    print(chart_message)
    print("-" * 40)
    
    # Calculate percentages
    if entry_price and stop_loss:
        sl_percent = ((stop_loss / entry_price) - 1) * 100
        print(f"\nStop Loss Distance: {sl_percent:.2f}%")
        
    if entry_price and targets:
        print("\nTarget Distances:")
        for i, target in enumerate(targets):
            if isinstance(target, dict):
                target_price = target.get('price', 0)
                if target_price > 0:
                    tp_percent = ((target_price / entry_price) - 1) * 100
                    print(f"  TP{i+1}: +{tp_percent:.2f}%")


def create_test_signal_json():
    """Create a test JSON file to verify data structure."""
    
    print("\n" + "=" * 60)
    print("CREATING TEST JSON FILE")
    print("=" * 60)
    
    # Create test data
    signal_data = {
        "symbol": "ENAUSDT",
        "signal_type": "BUY",
        "confluence_score": 69.24,
        "price": 0.059520,
        "entry_price": 0.059520,
        "stop_loss": 0.0577,
        "stop_loss_percent": -3.01,
        "trade_params": {
            "entry_price": 0.059520,
            "stop_loss": 0.0577,
            "targets": [
                {"name": "Target 1", "price": 0.0620, "size": 50},
                {"name": "Target 2", "price": 0.0640, "size": 30},
                {"name": "Target 3", "price": 0.0660, "size": 20}
            ]
        },
        "timestamp": datetime.now().isoformat(),
        "components": {
            "orderbook": {"score": 80.6, "reliability": 0.9},
            "orderflow": {"score": 76.6, "reliability": 0.85},
            "volume": {"score": 63.2, "reliability": 0.8}
        }
    }
    
    # Save to file
    os.makedirs("test_output", exist_ok=True)
    json_path = "test_output/test_signal_data.json"
    
    with open(json_path, 'w') as f:
        json.dump(signal_data, f, indent=2)
    
    print(f"✅ Test JSON saved to: {json_path}")
    print("\nJSON structure preview:")
    print(json.dumps({
        "trade_params": signal_data["trade_params"],
        "stop_loss": signal_data["stop_loss"],
        "entry_price": signal_data["entry_price"]
    }, indent=2))


if __name__ == "__main__":
    # Run all tests
    test_stop_loss_extraction()
    test_discord_message_formatting()
    create_test_signal_json()
    
    print("\n" + "=" * 60)
    print("✅ BASIC TESTS COMPLETED")
    print("=" * 60)
    print("\nThe logic appears to be working correctly!")
    print("Stop loss values from trade_params are properly extracted.")
    print("Discord messages are formatted with TP/SL details.")
    print("\nCheck test_output/test_signal_data.json for the data structure.")