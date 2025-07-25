#!/usr/bin/env python3

"""
Test FrequencyAlert signal_data access
"""

import sys
sys.path.append('.')
from src.monitoring.signal_frequency_tracker import FrequencyAlert, SignalType

# Test creating a FrequencyAlert with signal_data
test_signal_data = {
    "symbol": "BTCUSDT",
    "signal_type": "BUY",
    "confluence_score": 75.8,
    "components": {"technical": 78.2, "volume": 71.5},
    "reliability": 92.5
}

alert = FrequencyAlert(
    symbol="BTCUSDT",
    signal_type=SignalType.BUY,
    current_score=75.8,
    previous_score=0.0,
    time_since_last=0.0,
    frequency_count=1,
    alert_message="Test alert",
    timestamp=1234567890,
    alert_id="test-123",
    signal_data=test_signal_data
)

print("🧪 Testing FrequencyAlert signal_data access")
print("="*50)

# Test .get() method access (like dictionary)
signal_data = alert.get('signal_data')
print(f"✅ signal_data access: {signal_data is not None}")
print(f"📊 Symbol from signal_data: {signal_data.get('symbol') if signal_data else 'None'}")
print(f"🎯 Confluence score: {signal_data.get('confluence_score') if signal_data else 'None'}")

# Test extracting data like the alert manager would
if signal_data:
    print("\n📋 Signal Data Contents:")
    print(f"  - Symbol: {signal_data.get('symbol', 'UNKNOWN')}")
    print(f"  - Signal Type: {signal_data.get('signal_type', 'BUY')}")
    print(f"  - Confluence Score: {signal_data.get('confluence_score', 0)}")
    print(f"  - Components: {signal_data.get('components', {})}")
    print(f"  - Reliability: {signal_data.get('reliability', 0)}")
    print("\n✅ Rich formatting data is accessible!")
else:
    print("❌ signal_data is None")

print("\n🎉 Test completed!")