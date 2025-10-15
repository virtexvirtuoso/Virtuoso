#!/usr/bin/env python3
"""
Comprehensive QA Validation for Week 1 Quick Wins Alert Enhancement Implementation
Validates all 14 alert types, cognitive optimizations, and performance claims
"""

import sys
import os
import time
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.monitoring.alert_formatter import OptimizedAlertFormatter

def count_information_chunks(message: str) -> int:
    """
    Count discrete information chunks following Miller's Law (7±2).
    A chunk is a distinct piece of information (header, metric line, action).
    """
    lines = [l.strip() for l in message.split('\n') if l.strip()]
    # Exclude empty lines and dividers
    chunks = [l for l in lines if l and not all(c in ['─', '═', '=', '-'] for c in l.replace(' ', ''))]
    return len(chunks)

def validate_severity_first(message: str) -> bool:
    """Validate that severity indicator appears first in message."""
    severity_indicators = ['🔴 CRITICAL', '🟠 HIGH', '🟡 MODERATE', '🟢 LOW', '🟢 INFO']
    first_line = message.split('\n')[0] if message else ''
    return any(indicator in first_line for indicator in severity_indicators)

def validate_pattern_name(message: str) -> bool:
    """Validate that a clear pattern name exists in the header."""
    first_line = message.split('\n')[0] if message else ''
    # Pattern names should be SHORT and MEMORABLE (2-3 words max)
    pattern_names = [
        'ACCUMULATION SURGE', 'DISTRIBUTION WAVE', 'WHALE ACTIVITY',
        'BREAKOUT SETUP', 'REVERSAL SETUP', 'CONTINUATION SETUP',
        'PRICE SUPPRESSION', 'ARTIFICIAL PUMP', 'SPOOFING DETECTED',
        'STEALTH ACCUMULATION', 'VOLUME SURGE', 'CASCADE WARNING',
        'RESISTANCE BREAK', 'SUPPORT BREAK', 'REGIME SHIFT',
        'BETA EXPANSION', 'MOMENTUM BREAKOUT', 'MEAN REVERSION',
        'LATENCY SPIKE', 'RESOURCE WARNING', 'CONNECTION ISSUE',
        'ASCENDING TRIANGLE', 'BREAKOUT SIGNAL', 'DIVERGENCE DETECTED',
        'VOLATILITY REGIME', 'LIQUIDATION CLUSTER'
    ]
    return any(pattern in first_line for pattern in pattern_names)

def validate_action_statement(message: str) -> bool:
    """Validate that clear action statement exists using imperative verbs."""
    action_markers = ['🎯 ACTION:', '🛑 ACTION:', '⚡ ACTION:']
    return any(marker in message for marker in action_markers)

def validate_redundancy_removal(message: str) -> bool:
    """Validate that redundant information is minimized."""
    # Check for redundant price mentions (should appear max 2 times)
    import re
    price_pattern = r'\$[\d,]+\.[\d]{2}'
    price_mentions = re.findall(price_pattern, message)
    # Count unique prices vs total mentions
    unique_prices = len(set(price_mentions))
    total_mentions = len(price_mentions)
    # Allow up to 2x redundancy for entry/stop/target scenarios
    return total_mentions <= unique_prices * 2

def test_all_alert_types() -> Tuple[int, int, List[str]]:
    """Test all 14 alert types for proper formatting."""
    formatter = OptimizedAlertFormatter()
    passed = 0
    failed = 0
    failures = []

    test_cases = [
        # 1. Whale Alert
        ('whale', {
            'symbol': 'BTCUSDT',
            'current_price': 43500.50,
            'net_usd_value': 5000000,
            'whale_trades_count': 8,
            'volume_multiple': '3.5x',
            'whale_buy_volume': 3500000,
            'whale_sell_volume': 1500000
        }),

        # 2. Manipulation Alert
        ('manipulation', {
            'symbol': 'ETHUSDT',
            'manipulation_type': 'divergence',
            'confidence_score': 0.85,
            'metrics': {
                'oi_change_15m': 0.15,
                'price_change_15m': -0.05,
                'volume_ratio': 4.2,
                'suspicious_trades': 12
            }
        }),

        # 3. Smart Money Alert
        ('smart_money', {
            'symbol': 'BTCUSDT',
            'event_type': 'stealth_accumulation',
            'sophistication_score': 8.5,
            'confidence': 0.75,
            'institutional_probability': 0.80,
            'patterns_detected': ['stealth_accumulation', 'iceberg_orders']
        }),

        # 4. Volume Spike Alert
        ('volume_spike', {
            'symbol': 'SOLUSDT',
            'price_change': '+2.3%',
            'current_volume': 15000000,
            'average_volume': 5000000,
            'volume_ratio': 3.0,
            'duration_minutes': 15
        }),

        # 5. Confluence Alert
        ('confluence', {
            'symbol': 'BTCUSDT',
            'confluence_score': 85,
            'signal_direction': 'BUY',
            'timeframe': '1h',
            'entry_price': 43500,
            'stop_loss': 43000,
            'take_profit_1': 44000,
            'take_profit_2': 44500,
            'take_profit_3': 45000,
            'components': {
                'trend': 75,
                'momentum': 80,
                'volume': 85,
                'volatility': 70,
                'sentiment': 75,
                'structure': 80
            }
        }),

        # 6. Liquidation Alert
        ('liquidation', {
            'symbol': 'BTCUSDT',
            'side': 'long',
            'amount_usd': 2500000,
            'price': 43200,
            'total_liquidations_1h': 15000000,
            'liquidation_rate': 'increasing'
        }),

        # 7. Price Alert
        ('price', {
            'symbol': 'ETHUSDT',
            'trigger_type': 'resistance_break',
            'trigger_price': 2300,
            'current_price': 2315,
            'change_percent': '+0.65%',
            'volume_at_break': 8000000
        }),

        # 8. Market Condition Alert
        ('market_condition', {
            'condition': 'regime_change',
            'from_state': 'low_volatility',
            'to_state': 'high_volatility',
            'affected_symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT'],
            'confidence': 0.78,
            'recommendations': 'Reduce leverage and position sizes'
        }),

        # 9. Alpha Scanner Alert
        ('alpha', {
            'symbol': 'AVAXUSDT',
            'tier': 'HIGH',
            'pattern_type': 'momentum_breakout',
            'alpha_magnitude': 0.045,
            'confidence': 0.82,
            'entry_zones': [35.5, 36.0],
            'targets': [38.0, 40.0, 42.0],
            'stop_loss': 34.0,
            'volume_confirmed': True,
            'trading_insight': 'Strong uptrend with increasing volume'
        }),

        # 10. System Health Alert
        ('system_health', {
            'component': 'memory',
            'severity': 'warning',
            'current_value': 85,
            'threshold': 80,
            'affected_services': ['data_processor', 'websocket_handler', 'alert_manager'],
            'recommendations': ['Clear cache', 'Restart data processor']
        }),

        # 11. Market Report Alert
        ('market_report', {
            'report_type': 'hourly',
            'period': 'Jan 1, 2025 14:00-15:00 UTC',
            'summary': {
                'total_alerts': 45,
                'critical_alerts': 8,
                'top_symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                'market_regime': 'high_volatility',
                'system_health': 'healthy'
            }
        }),

        # 12. System Alert
        ('system', {
            'severity': 'warning',
            'component': 'exchange_api',
            'message': 'Increased latency detected',
            'action': 'Monitoring, failover activated',
            'metrics': {
                'current_latency': 650,
                'success_rate': 0.95
            }
        }),

        # 13. Error Alert
        ('error', {
            'severity': 'critical',
            'component': 'trade_executor',
            'error': 'Insufficient Balance',
            'details': 'Order value exceeds available balance',
            'symbol': 'BTCUSDT',
            'impact': 'Trade execution halted',
            'recovery_attempted': True,
            'recovery_status': 'failed'
        }),

        # 14. Signal Alert
        ('signal', {
            'signal_type': 'triangle_breakout',
            'symbol': 'LINKUSDT',
            'alpha_value': 0.038,
            'confidence': 0.73,
            'timeframe': '4h',
            'pattern_name': 'Ascending Triangle',
            'entry_zone': [14.5, 14.8],
            'target': 16.5,
            'stop_loss': 13.8,
            'risk_reward': 2.5
        })
    ]

    print("\n" + "="*80)
    print("TESTING ALL 14 ALERT TYPES")
    print("="*80)

    for alert_type, data in test_cases:
        print(f"\n{'─'*80}")
        print(f"Testing: {alert_type.upper()} Alert")
        print(f"{'─'*80}")

        try:
            message = formatter.format_alert(alert_type, data)

            # Validate cognitive optimizations
            has_severity_first = validate_severity_first(message)
            has_pattern_name = validate_pattern_name(message) or alert_type in ['market_report', 'system', 'error']
            has_action = validate_action_statement(message)
            no_redundancy = validate_redundancy_removal(message)
            chunk_count = count_information_chunks(message)
            meets_millers_law = chunk_count <= 7

            # Print results
            print(f"✅ Message generated: {len(message)} chars")
            print(f"{'✅' if has_severity_first else '❌'} Severity-first ordering")
            print(f"{'✅' if has_pattern_name else '❌'} Pattern name present")
            print(f"{'✅' if has_action else '❌'} Action statement present")
            print(f"{'✅' if no_redundancy else '❌'} Redundancy minimized")
            print(f"{'✅' if meets_millers_law else '❌'} Information chunks: {chunk_count}/7 (Miller's Law)")

            # Check if all criteria met
            all_passed = all([
                has_severity_first,
                has_pattern_name,
                has_action,
                no_redundancy,
                meets_millers_law
            ])

            if all_passed:
                passed += 1
                print(f"✅ PASSED")
            else:
                failed += 1
                failures.append(f"{alert_type}: Failed validation criteria")
                print(f"❌ FAILED")

            # Print sample message (truncated)
            print(f"\nSample output (first 300 chars):")
            print(f"{message[:300]}...")

        except Exception as e:
            failed += 1
            failures.append(f"{alert_type}: Exception - {str(e)}")
            print(f"❌ EXCEPTION: {str(e)}")

    return passed, failed, failures

def test_performance_claims() -> bool:
    """Test claimed 75% reduction in processing time."""
    formatter = OptimizedAlertFormatter()

    print("\n" + "="*80)
    print("TESTING PERFORMANCE CLAIMS")
    print("="*80)

    # Test data
    test_data = {
        'symbol': 'BTCUSDT',
        'current_price': 43500.50,
        'net_usd_value': 5000000,
        'whale_trades_count': 8,
        'volume_multiple': '3.5x',
        'whale_buy_volume': 3500000,
        'whale_sell_volume': 1500000
    }

    # Warm up
    for _ in range(10):
        formatter.format_whale_alert(test_data)

    # Benchmark
    iterations = 1000
    start_time = time.time()
    for _ in range(iterations):
        formatter.format_whale_alert(test_data)
    end_time = time.time()

    avg_time_ms = ((end_time - start_time) / iterations) * 1000

    print(f"\nAverage formatting time: {avg_time_ms:.2f}ms per alert")
    print(f"Target: <10ms per alert (claimed 75% reduction from ~12ms to ~3ms)")

    # Very generous threshold - should be sub-millisecond
    if avg_time_ms < 10:
        print(f"✅ PASSED: Performance is acceptable")
        return True
    else:
        print(f"❌ FAILED: Performance too slow")
        return False

def test_integration_with_alert_manager() -> bool:
    """Test integration with alert_manager.py"""
    print("\n" + "="*80)
    print("TESTING INTEGRATION WITH ALERT MANAGER")
    print("="*80)

    try:
        from src.monitoring.alert_manager import AlertManager

        # Check that AlertManager imports AlertFormatter
        config = {}
        manager = AlertManager(config)

        has_formatter = hasattr(manager, 'alert_formatter')
        formatter_type = type(manager.alert_formatter).__name__

        print(f"{'✅' if has_formatter else '❌'} AlertManager has alert_formatter attribute")
        print(f"Formatter type: {formatter_type}")
        print(f"{'✅' if formatter_type in ['AlertFormatter', 'OptimizedAlertFormatter'] else '❌'} Correct formatter type")

        return has_formatter and formatter_type in ['AlertFormatter', 'OptimizedAlertFormatter']
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_backward_compatibility() -> bool:
    """Test that AlertFormatter alias works for backward compatibility."""
    print("\n" + "="*80)
    print("TESTING BACKWARD COMPATIBILITY")
    print("="*80)

    try:
        from src.monitoring.alert_formatter import AlertFormatter, OptimizedAlertFormatter

        # Check that alias exists
        alias_works = AlertFormatter is OptimizedAlertFormatter
        print(f"{'✅' if alias_works else '❌'} AlertFormatter alias points to OptimizedAlertFormatter")

        # Test instantiation via alias
        formatter = AlertFormatter()
        has_format_method = hasattr(formatter, 'format_alert')
        print(f"{'✅' if has_format_method else '❌'} Formatter has format_alert method")

        return alias_works and has_format_method
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_code_quality() -> Tuple[bool, List[str]]:
    """Test code quality aspects."""
    print("\n" + "="*80)
    print("TESTING CODE QUALITY")
    print("="*80)

    issues = []

    try:
        formatter = OptimizedAlertFormatter()

        # Check all 14 formatters exist
        required_methods = [
            'format_whale_alert',
            'format_manipulation_alert',
            'format_smart_money_alert',
            'format_volume_spike_alert',
            'format_confluence_alert',
            'format_liquidation_alert',
            'format_price_alert',
            'format_market_condition_alert',
            'format_alpha_alert',
            'format_system_health_alert',
            'format_market_report_alert',
            'format_system_alert',
            'format_error_alert',
            'format_signal_alert'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(formatter, method):
                missing_methods.append(method)

        if missing_methods:
            issues.append(f"Missing methods: {', '.join(missing_methods)}")
            print(f"❌ Missing methods: {len(missing_methods)}")
        else:
            print(f"✅ All 14 alert formatters present")

        # Check dispatch dictionary completeness
        test_data = {'symbol': 'TEST', 'severity': 'info'}
        alert_types = [
            'whale', 'manipulation', 'smart_money', 'volume_spike',
            'confluence', 'liquidation', 'price', 'market_condition',
            'alpha', 'system_health', 'market_report', 'system',
            'error', 'signal'
        ]

        dispatch_failures = []
        for alert_type in alert_types:
            try:
                result = formatter.format_alert(alert_type, test_data)
                if not result:
                    dispatch_failures.append(alert_type)
            except Exception as e:
                dispatch_failures.append(f"{alert_type} ({str(e)})")

        if dispatch_failures:
            issues.append(f"Dispatch failures: {', '.join(dispatch_failures)}")
            print(f"❌ Dispatch failures: {len(dispatch_failures)}")
        else:
            print(f"✅ All alert types dispatch correctly")

        # Check error handling (fallback formatter)
        try:
            result = formatter.format_alert('unknown_type', test_data)
            if result:
                print(f"✅ Fallback formatter works for unknown alert types")
            else:
                issues.append("Fallback formatter returns empty result")
                print(f"❌ Fallback formatter returns empty result")
        except Exception as e:
            issues.append(f"Fallback formatter failed: {str(e)}")
            print(f"❌ Fallback formatter failed")

        return len(issues) == 0, issues

    except Exception as e:
        issues.append(f"Code quality test failed: {str(e)}")
        print(f"❌ Code quality test failed: {str(e)}")
        return False, issues

def main():
    """Run comprehensive validation suite."""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*10 + "COMPREHENSIVE ALERT ENHANCEMENT QA VALIDATION" + " "*23 + "║")
    print("║" + " "*20 + "Week 1 Quick Wins Implementation" + " "*25 + "║")
    print("╚" + "═"*78 + "╝")
    print("\n")

    results = {}

    # Test 1: All Alert Types
    passed, failed, failures = test_all_alert_types()
    results['Alert Types'] = (passed, failed, passed == 14 and failed == 0)

    # Test 2: Performance
    perf_pass = test_performance_claims()
    results['Performance'] = (1 if perf_pass else 0, 0 if perf_pass else 1, perf_pass)

    # Test 3: Integration
    integration_pass = test_integration_with_alert_manager()
    results['Integration'] = (1 if integration_pass else 0, 0 if integration_pass else 1, integration_pass)

    # Test 4: Backward Compatibility
    compat_pass = test_backward_compatibility()
    results['Backward Compatibility'] = (1 if compat_pass else 0, 0 if compat_pass else 1, compat_pass)

    # Test 5: Code Quality
    quality_pass, quality_issues = test_code_quality()
    results['Code Quality'] = (1 if quality_pass else 0, 0 if quality_pass else 1, quality_pass)

    # Final Summary
    print("\n" + "="*80)
    print("FINAL VALIDATION SUMMARY")
    print("="*80)

    for test_name, (p, f, status) in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {test_name}: {p} passed, {f} failed")

    # Overall Status
    all_passed = all(status for _, _, status in results.values())

    print("\n" + "="*80)
    if all_passed:
        print("✅ OVERALL STATUS: READY FOR VPS DEPLOYMENT")
        print("="*80)
        print("\nAll validation tests passed. Implementation meets:")
        print("  • All 14 alert types functional")
        print("  • Cognitive optimization criteria (Miller's Law, severity-first, etc.)")
        print("  • Performance targets (<10ms per alert)")
        print("  • Integration with existing systems")
        print("  • Backward compatibility maintained")
        print("  • Code quality standards")
        return 0
    else:
        print("❌ OVERALL STATUS: NOT READY FOR DEPLOYMENT")
        print("="*80)
        print("\nIssues found:")
        for test_name, (p, f, status) in results.items():
            if not status:
                print(f"  • {test_name}: FAILED")
        if failures:
            print("\nDetailed failures:")
            for failure in failures:
                print(f"  • {failure}")
        if quality_issues:
            print("\nCode quality issues:")
            for issue in quality_issues:
                print(f"  • {issue}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
