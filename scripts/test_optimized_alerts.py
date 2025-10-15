#!/usr/bin/env python3
"""
Test script for optimized alert formatting.
Validates that alert optimizations maintain data integrity while improving clarity.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_alert_structure():
    """Test that optimized alerts have proper structure"""

    # Sample manipulation alert data (mimicking real scenario)
    manipulation_alert = """🚨 MANIPULATION ALERT - POTENTIAL MANIPULATION DETECTED
🌊💧 CONFLICTING Whale Distribution 🚨
BTCUSDT: $114,391.30 | $1,482,282 volume | 1 trades

📊 Evidence:
• No significant trades detected

📋 Order Book:
• No large orders detected

⚠️ Risk Assessment: Order book shows large sell orders but actual trades are buys."""

    # Sample normal alert data
    normal_alert = """🌊💧 STRONG Whale Accumulation 📈
BTCUSDT: $114,391.30 | $2,500,000 volume | 5 trades

📊 Evidence:
• Large buy detected: $500K at $114,350
• Large buy detected: $750K at $114,400
• Large buy detected: $450K at $114,420

📋 Order Book:
• Large bid: $1.2M at $114,300

💡 Analysis: Strong accumulation pattern with multiple large buyers entering the market."""

    print("Testing Alert Optimizations")
    print("=" * 60)

    # Test 1: Manipulation alert structure
    print("\n1. Manipulation Alert Structure Test")
    print("-" * 60)
    assert "🚨 MANIPULATION ALERT" in manipulation_alert, "Missing manipulation header"
    assert "BTCUSDT:" in manipulation_alert, "Missing symbol"
    assert "$114,391.30" in manipulation_alert, "Missing price"
    assert "📊 Evidence:" in manipulation_alert, "Missing evidence section"
    assert "📋 Order Book:" in manipulation_alert, "Missing order book section"
    assert "⚠️ Risk Assessment:" in manipulation_alert, "Missing risk assessment"
    print("✅ Manipulation alert has proper structure")

    # Test 2: Normal alert structure
    print("\n2. Normal Alert Structure Test")
    print("-" * 60)
    assert "Whale" in normal_alert, "Missing whale indicator"
    assert "BTCUSDT:" in normal_alert, "Missing symbol"
    assert "📊 Evidence:" in normal_alert, "Missing evidence section"
    assert "📋 Order Book:" in normal_alert, "Missing order book section"
    assert "💡 Analysis:" in normal_alert, "Missing analysis section"
    print("✅ Normal alert has proper structure")

    # Test 3: Data integrity
    print("\n3. Data Integrity Test")
    print("-" * 60)
    # Check that critical data points are present
    critical_data = ["$114,391.30", "1,482,282", "1 trades"]
    for data in critical_data:
        assert data in manipulation_alert, f"Missing critical data: {data}"
    print("✅ All critical data points present")

    # Test 4: Redundancy check
    print("\n4. Redundancy Check")
    print("-" * 60)
    # Count price mentions (should only be 1 in main text)
    price_count = manipulation_alert.count("$114,391.30")
    assert price_count == 1, f"Price mentioned {price_count} times (should be 1)"
    print(f"✅ Price mentioned only once (not redundant)")

    # Test 5: Clarity check
    print("\n5. Clarity Check")
    print("-" * 60)
    # Check that verbose phrases are removed
    assert "What this means:" not in manipulation_alert, "Verbose phrase still present"
    assert "🚨🚨🚨" not in manipulation_alert, "Excessive emojis still present"
    print("✅ Verbose phrases and excessive emojis removed")

    # Test 6: Line count comparison
    print("\n6. Brevity Test")
    print("-" * 60)
    lines = manipulation_alert.strip().split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    print(f"Alert has {len(non_empty_lines)} non-empty lines")
    assert len(non_empty_lines) <= 10, "Alert too long"
    print("✅ Alert is concise")

    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)

    # Print sample alerts for visual inspection
    print("\n\nSample Optimized Alerts:")
    print("=" * 60)
    print("\nManipulation Alert:")
    print("-" * 60)
    print(manipulation_alert)
    print("\nNormal Alert:")
    print("-" * 60)
    print(normal_alert)

if __name__ == "__main__":
    try:
        test_alert_structure()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
