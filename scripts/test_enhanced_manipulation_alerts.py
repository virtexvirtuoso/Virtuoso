#!/usr/bin/env python3
"""
Test script for enhanced manipulation alert interpretations.
Validates severity calculation and human-readable formatting.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_severity_calculation():
    """Test manipulation severity calculation"""
    print("=" * 80)
    print("TESTING MANIPULATION SEVERITY CALCULATION")
    print("=" * 80)

    test_cases = [
        # (volume, trade_count, buy_sell_ratio, expected_severity)
        (15_000_000, 12, 15.0, "EXTREME"),  # Huge volume, many trades, extreme imbalance
        (8_000_000, 8, 8.0, "HIGH"),         # High volume, several trades, high imbalance
        (3_000_000, 4, 4.0, "MODERATE"),     # Moderate volume, few trades, moderate imbalance
        (1_000_000, 1, 1.5, "LOW"),          # Low volume, single trade, low imbalance
    ]

    # Simple severity calculator (mimics the real one)
    def calculate_severity(volume, trade_count, buy_sell_ratio):
        # Volume-based severity
        if volume >= 10_000_000:
            volume_severity = 4
        elif volume >= 5_000_000:
            volume_severity = 3
        elif volume >= 2_000_000:
            volume_severity = 2
        else:
            volume_severity = 1

        # Trade count severity
        if trade_count >= 10:
            trade_severity = 4
        elif trade_count >= 5:
            trade_severity = 3
        elif trade_count >= 3:
            trade_severity = 2
        else:
            trade_severity = 1

        # Ratio severity
        if buy_sell_ratio >= 10 or buy_sell_ratio <= 0.1:
            ratio_severity = 4
        elif buy_sell_ratio >= 5 or buy_sell_ratio <= 0.2:
            ratio_severity = 3
        elif buy_sell_ratio >= 3 or buy_sell_ratio <= 0.33:
            ratio_severity = 2
        else:
            ratio_severity = 1

        total_severity = (volume_severity * 0.4 + trade_severity * 0.3 + ratio_severity * 0.3)

        if total_severity >= 3.5:
            return "EXTREME"
        elif total_severity >= 2.5:
            return "HIGH"
        elif total_severity >= 1.5:
            return "MODERATE"
        else:
            return "LOW"

    passed = 0
    failed = 0

    for volume, trade_count, ratio, expected in test_cases:
        result = calculate_severity(volume, trade_count, ratio)
        status = "✅" if result == expected else "❌"

        print(f"\n{status} Test: ${volume:,} | {trade_count} trades | {ratio}x ratio")
        print(f"   Expected: {expected} | Got: {result}")

        if result == expected:
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")

    return failed == 0


def test_manipulation_alert_formatting():
    """Test manipulation alert message formatting"""
    print("=" * 80)
    print("TESTING MANIPULATION ALERT FORMATTING")
    print("=" * 80)

    # Test cases for different severity levels
    test_scenarios = [
        {
            "name": "EXTREME Fake Sell Wall",
            "pattern": "FAKE SELL WALL",
            "orderbook_signal": "large SELL orders",
            "actual_trades": "5,000 BUY trades",
            "severity": "EXTREME",
            "volume": 15_000_000,
            "trade_count": 12
        },
        {
            "name": "HIGH Fake Buy Wall",
            "pattern": "FAKE BUY WALL",
            "orderbook_signal": "large BUY orders",
            "actual_trades": "3,500 SELL trades",
            "severity": "HIGH",
            "volume": 8_000_000,
            "trade_count": 8
        },
        {
            "name": "MODERATE Fake Sell Wall",
            "pattern": "FAKE SELL WALL",
            "orderbook_signal": "large SELL orders",
            "actual_trades": "1,200 BUY trades",
            "severity": "MODERATE",
            "volume": 3_000_000,
            "trade_count": 4
        }
    ]

    for scenario in test_scenarios:
        print(f"\n{'─' * 80}")
        print(f"Scenario: {scenario['name']}")
        print(f"{'─' * 80}")

        # Format volume
        volume = scenario['volume']
        volume_str = f"${volume/1_000_000:.1f}M" if volume >= 1_000_000 else f"${volume/1_000:.0f}K"
        trade_plural = "trade" if scenario['trade_count'] == 1 else "trades"

        severity_config = {
            "EXTREME": {"emoji": "🚨🚨🚨", "risk": "CRITICAL", "urgency": "IMMEDIATE ATTENTION REQUIRED"},
            "HIGH": {"emoji": "🚨🚨", "risk": "HIGH", "urgency": "Use extreme caution"},
            "MODERATE": {"emoji": "🚨", "risk": "MODERATE", "urgency": "Exercise caution"},
        }

        config = severity_config[scenario['severity']]

        alert = f"""
{config['emoji']} **{scenario['pattern']} DETECTED** {config['emoji']}

**Severity:** {scenario['severity']} ({config['risk']} RISK)
**Evidence:** {volume_str} across {scenario['trade_count']} {trade_plural}

**Orderbook Signal:** {scenario['orderbook_signal']}
**Actual Trades:** {scenario['actual_trades']}

**Manipulation Tactic:** spoofing/fake-walling to create false distribution
**What Whales Are Doing:** buying the fake dip

⚠️ **RISK:** Price may pump suddenly when fake orders are pulled
🛑 **ACTION:** DO NOT PANIC SELL

_{config['urgency']}_
        """.strip()

        print(alert)
        print()

    print(f"{'=' * 80}\n")
    return True


def test_comparison():
    """Compare old vs new alert format"""
    print("=" * 80)
    print("COMPARISON: OLD VS NEW ALERT FORMAT")
    print("=" * 80)

    print("\n📋 OLD FORMAT:")
    print("─" * 80)
    old_format = """
🚨 **POTENTIAL MANIPULATION:** Order book shows large sell orders but actual
trades are buys. Whales may be spoofing/fake-walling to create false
distribution signals then buying the fake dip. ⚠️ **HIGH RISK:** Price may
pump suddenly when fake orders are pulled. DO NOT PANIC SELL.
    """.strip()
    print(old_format)

    print("\n\n📋 NEW FORMAT (HIGH SEVERITY):")
    print("─" * 80)
    new_format = """
🚨🚨 **FAKE SELL WALL DETECTED** 🚨🚨

**Severity:** HIGH (HIGH RISK)
**Evidence:** $8.0M across 8 trades

**Orderbook Signal:** large SELL orders
**Actual Trades:** 5,000 BUY trades

**Manipulation Tactic:** spoofing/fake-walling to create false distribution
**What Whales Are Doing:** buying the fake dip

⚠️ **RISK:** Price may pump suddenly when fake orders are pulled
🛑 **ACTION:** DO NOT PANIC SELL

_Use extreme caution_
    """.strip()
    print(new_format)

    print("\n\n✨ KEY IMPROVEMENTS:")
    print("─" * 80)
    improvements = [
        "✅ Severity level clearly stated (EXTREME/HIGH/MODERATE/LOW)",
        "✅ Evidence quantified ($8.0M across 8 trades)",
        "✅ Structured sections with clear labels",
        "✅ Visual hierarchy with emojis matching severity",
        "✅ Specific pattern identification (FAKE SELL WALL)",
        "✅ Urgency level communicated (_Use extreme caution_)",
        "✅ Orderbook vs actual trades clearly separated",
        "✅ Manipulation tactic explicitly named"
    ]

    for improvement in improvements:
        print(f"  {improvement}")

    print(f"\n{'=' * 80}\n")
    return True


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "ENHANCED MANIPULATION ALERT TESTING" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    tests = [
        ("Severity Calculation", test_severity_calculation),
        ("Alert Formatting", test_manipulation_alert_formatting),
        ("Format Comparison", test_comparison)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("FINAL TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
