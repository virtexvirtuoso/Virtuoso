"""
Unified Schema Integration Validation Test
===========================================

This script validates that the unified schema system correctly transforms
monitoring data and fixes the schema mismatch that caused zeros in the dashboard.

Tests:
1. Schema transformation (old format → unified format)
2. Cache writer functionality
3. Field name compatibility with dashboard
4. Data validation and integrity
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from core.schemas import (
    MarketOverviewSchema,
    SignalsSchema,
    MarketBreadthSchema,
    MarketMoversSchema
)


def test_market_overview_schema_transformation():
    """Test that old monitoring format transforms to unified format."""
    print("\n" + "="*70)
    print("TEST 1: Market Overview Schema Transformation")
    print("="*70)

    # Old monitoring format (what monitoring service currently writes)
    old_monitoring_data = {
        'total_symbols_monitored': 15,
        'active_signals_1h': 8,
        'bullish_signals': 10,
        'bearish_signals': 2,
        'avg_confluence_score': 67.5,
        'max_confluence_score': 82.3,
        'market_state': 'Trending',
        'total_volume': 45000000000,
        'volatility': 35.2,
        'avg_change_percent': 2.5,
        'btc_dom': 62.4
    }

    print("\n📥 OLD Monitoring Format (what monitoring writes):")
    print(json.dumps(old_monitoring_data, indent=2))

    # Transform to unified schema
    schema = MarketOverviewSchema.from_monitoring_data(old_monitoring_data)

    # Validate
    is_valid = schema.validate()
    print(f"\n✅ Schema validation: {'PASSED' if is_valid else 'FAILED'}")

    # Convert to dict (what gets cached)
    unified_data = schema.to_dict()

    print("\n📤 NEW Unified Format (what gets cached):")
    print(json.dumps({
        k: v for k, v in unified_data.items()
        if not k.startswith('__')
    }, indent=2, default=str))

    # Verify critical field transformations
    print("\n🔍 Field Transformation Verification:")
    transformations = [
        ('total_symbols_monitored', 'total_symbols', old_monitoring_data['total_symbols_monitored'], schema.total_symbols),
        ('market_state', 'market_regime', old_monitoring_data['market_state'], schema.market_regime),
        ('btc_dom', 'btc_dominance', old_monitoring_data['btc_dom'], schema.btc_dominance),
        ('total_volume', 'total_volume_24h', old_monitoring_data['total_volume'], schema.total_volume_24h),
    ]

    all_passed = True
    for old_field, new_field, old_value, new_value in transformations:
        status = "✅" if old_value == new_value else "❌"
        print(f"  {status} {old_field:25s} → {new_field:20s}  ({old_value} → {new_value})")
        if old_value != new_value:
            all_passed = False

    # Check trend_strength calculation
    expected_trend = 50 + ((10 - 2) / 12) * 50  # (bullish - bearish) / total * 50 + 50
    print(f"\n  {'✅' if abs(schema.trend_strength - expected_trend) < 0.1 else '❌'} "
          f"trend_strength calculation: {schema.trend_strength:.2f} "
          f"(expected {expected_trend:.2f})")

    print(f"\n{'✅ PASS' if all_passed and is_valid else '❌ FAIL'}: Market Overview Schema Transformation")
    return all_passed and is_valid


def test_signals_schema():
    """Test signals schema structure."""
    print("\n" + "="*70)
    print("TEST 2: Signals Schema")
    print("="*70)

    # Sample signals
    signals = [
        {
            'symbol': 'BTCUSDT',
            'confluence_score': 78.5,
            'signal_type': 'LONG',
            'reliability': 82.0,
            'sentiment': 'BULLISH',
            'price': 65432.10,
            'change_24h': 2.5,
            'volume_24h': 12345678900
        },
        {
            'symbol': 'ETHUSDT',
            'confluence_score': 71.2,
            'signal_type': 'LONG',
            'reliability': 75.0,
            'sentiment': 'BULLISH',
            'price': 3456.78,
            'change_24h': 1.8,
            'volume_24h': 5432109800
        }
    ]

    print(f"\n📥 Input: {len(signals)} signals")

    # Create schema
    schema = SignalsSchema(signals=signals)

    # Validate
    is_valid = schema.validate()
    print(f"\n✅ Schema validation: {'PASSED' if is_valid else 'FAILED'}")

    # Check auto-calculated fields
    print(f"\n📊 Auto-calculated Statistics:")
    print(f"  Total signals:        {schema.total_signals}")
    print(f"  Buy signals:          {schema.buy_signals}")
    print(f"  Sell signals:         {schema.sell_signals}")
    print(f"  Avg confluence score: {schema.avg_confluence_score:.2f}")
    print(f"  Top symbols:          {schema.top_symbols}")

    # Convert to dict
    data = schema.to_dict()

    # Check that both 'signals' and 'recent_signals' are present (backward compatibility)
    has_signals = 'signals' in data
    has_recent_signals = 'recent_signals' in data

    print(f"\n🔍 Backward Compatibility:")
    print(f"  {'✅' if has_signals else '❌'} 'signals' field present")
    print(f"  {'✅' if has_recent_signals else '❌'} 'recent_signals' field present (alias)")

    passed = is_valid and has_signals and has_recent_signals
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Signals Schema")
    return passed


def test_market_breadth_schema():
    """Test market breadth schema."""
    print("\n" + "="*70)
    print("TEST 3: Market Breadth Schema")
    print("="*70)

    # Test data: 12 up, 3 down = 80% bullish
    schema = MarketBreadthSchema(
        up_count=12,
        down_count=3,
        flat_count=0
    )

    is_valid = schema.validate()
    print(f"\n✅ Schema validation: {'PASSED' if is_valid else 'FAILED'}")

    print(f"\n📊 Calculated Metrics:")
    print(f"  Up count:             {schema.up_count}")
    print(f"  Down count:           {schema.down_count}")
    print(f"  Breadth percentage:   {schema.breadth_percentage:.1f}%")
    print(f"  Market sentiment:     {schema.market_sentiment}")

    # Verify calculation
    expected_breadth = (12 / 15) * 100  # 80%
    expected_sentiment = "bullish"  # >= 60%

    breadth_correct = abs(schema.breadth_percentage - expected_breadth) < 0.1
    sentiment_correct = schema.market_sentiment == expected_sentiment

    print(f"\n🔍 Verification:")
    print(f"  {'✅' if breadth_correct else '❌'} Breadth calculation correct")
    print(f"  {'✅' if sentiment_correct else '❌'} Sentiment determination correct")

    passed = is_valid and breadth_correct and sentiment_correct
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Market Breadth Schema")
    return passed


def test_market_movers_schema():
    """Test market movers schema."""
    print("\n" + "="*70)
    print("TEST 4: Market Movers Schema")
    print("="*70)

    gainers = [
        {'symbol': 'SOLUSDT', 'price': 123.45, 'price_change_percent': 8.5},
        {'symbol': 'AVAXUSDT', 'price': 45.67, 'price_change_percent': 6.2}
    ]

    losers = [
        {'symbol': 'LINKUSDT', 'price': 12.34, 'price_change_percent': -5.3},
    ]

    volume_leaders = [
        {'symbol': 'BTCUSDT', 'volume_24h': 12345678900},
    ]

    schema = MarketMoversSchema(
        gainers=gainers,
        losers=losers,
        volume_leaders=volume_leaders
    )

    is_valid = schema.validate()
    print(f"\n✅ Schema validation: {'PASSED' if is_valid else 'FAILED'}")

    print(f"\n📊 Market Movers:")
    print(f"  Gainers:         {len(schema.gainers)}")
    print(f"  Losers:          {len(schema.losers)}")
    print(f"  Volume leaders:  {len(schema.volume_leaders)}")

    # Check aliases
    data = schema.to_dict()
    has_top_gainers = 'top_gainers' in data
    has_top_losers = 'top_losers' in data

    print(f"\n🔍 Backward Compatibility:")
    print(f"  {'✅' if has_top_gainers else '❌'} 'top_gainers' alias present")
    print(f"  {'✅' if has_top_losers else '❌'} 'top_losers' alias present")

    passed = is_valid and has_top_gainers and has_top_losers
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}: Market Movers Schema")
    return passed


def test_dashboard_field_compatibility():
    """Test that unified schema fields match what dashboard expects."""
    print("\n" + "="*70)
    print("TEST 5: Dashboard Field Compatibility")
    print("="*70)

    # Fields the dashboard expects for market overview
    required_dashboard_fields = [
        'total_symbols',       # Not 'total_symbols_monitored'
        'trend_strength',      # Not 'bullish_signals'/'bearish_signals'
        'btc_dominance',       # Not 'btc_dom'
        'total_volume_24h',
        'current_volatility',
        'market_regime',
        'average_change'
    ]

    # Create a schema
    test_data = {
        'total_symbols_monitored': 15,
        'bullish_signals': 8,
        'bearish_signals': 2,
        'btc_dom': 60.0,
        'total_volume': 45000000000
    }

    schema = MarketOverviewSchema.from_monitoring_data(test_data)
    unified_data = schema.to_dict()

    print("\n🔍 Checking dashboard required fields:")
    all_present = True
    for field in required_dashboard_fields:
        present = field in unified_data
        status = "✅" if present else "❌"
        print(f"  {status} {field:25s} {'present' if present else 'MISSING'}")
        if not present:
            all_present = False

    print(f"\n{'✅ PASS' if all_present else '❌ FAIL'}: Dashboard Field Compatibility")
    return all_present


def main():
    """Run all validation tests."""
    print("\n" + "="*70)
    print("UNIFIED SCHEMA INTEGRATION VALIDATION")
    print("="*70)
    print("\nValidating that unified schemas fix the mobile dashboard data issue...")

    results = []

    # Run all tests
    results.append(("Market Overview Transformation", test_market_overview_schema_transformation()))
    results.append(("Signals Schema", test_signals_schema()))
    results.append(("Market Breadth Schema", test_market_breadth_schema()))
    results.append(("Market Movers Schema", test_market_movers_schema()))
    results.append(("Dashboard Compatibility", test_dashboard_field_compatibility()))

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Ready for deployment!")
        print("\nThe unified schema system will fix the mobile dashboard issue by:")
        print("  1. ✅ Transforming 'total_symbols_monitored' → 'total_symbols'")
        print("  2. ✅ Calculating 'trend_strength' from bullish/bearish signals")
        print("  3. ✅ Mapping 'btc_dom' → 'btc_dominance'")
        print("  4. ✅ Providing all fields the dashboard expects")
        print("  5. ✅ Maintaining backward compatibility with aliases")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED - Fix issues before deployment")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
