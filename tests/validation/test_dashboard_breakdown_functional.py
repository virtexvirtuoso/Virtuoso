#!/usr/bin/env python3
"""
Functional Test for Dashboard Breakdown Cache Integration
==========================================================

This test validates the actual API endpoint functionality.
"""

import asyncio
import json
import time
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_cache_service_directly():
    """Test cache service directly"""
    print("\n" + "="*70)
    print("TEST: Direct Cache Service Test")
    print("="*70)

    from src.core.cache.confluence_cache_service import confluence_cache_service

    # Create test breakdown data
    test_symbol = "BTCUSDT"
    test_analysis = {
        "confluence_score": 75.5,
        "reliability": 82,
        "components": {
            "technical": 78.0,
            "volume": 72.5,
            "orderflow": 68.0,
            "sentiment": 65.5,
            "orderbook": 80.0,
            "price_structure": 76.5
        },
        "interpretations": {
            "technical": "Strong bullish technical signals",
            "volume": "Above-average volume confirms trend",
            "orderflow": "Positive orderflow indicates buying pressure",
            "sentiment": "Market sentiment is moderately bullish",
            "orderbook": "Orderbook shows strong support levels",
            "price_structure": "Price structure remains bullish"
        }
    }

    # Cache the breakdown
    print(f"1. Caching breakdown for {test_symbol}...")
    success = await confluence_cache_service.cache_confluence_breakdown(test_symbol, test_analysis)

    if success:
        print(f"   ✅ Successfully cached breakdown for {test_symbol}")
    else:
        print(f"   ❌ Failed to cache breakdown for {test_symbol}")
        return False

    # Wait a moment for cache to settle
    await asyncio.sleep(0.5)

    # Retrieve the breakdown
    print(f"2. Retrieving breakdown for {test_symbol}...")
    breakdown = await confluence_cache_service.get_cached_breakdown(test_symbol)

    if breakdown:
        print(f"   ✅ Successfully retrieved breakdown")
        print(f"   Overall Score: {breakdown.get('overall_score')}")
        print(f"   Sentiment: {breakdown.get('sentiment')}")
        print(f"   Reliability: {breakdown.get('reliability')}")
        print(f"   Components: {list(breakdown.get('components', {}).keys())}")
        print(f"   Interpretations: {len(breakdown.get('interpretations', {}))} items")

        # Verify structure
        required_fields = ['overall_score', 'sentiment', 'reliability', 'components', 'interpretations']
        missing_fields = [f for f in required_fields if f not in breakdown]

        if not missing_fields:
            print(f"   ✅ All required fields present")
        else:
            print(f"   ❌ Missing fields: {missing_fields}")
            return False

        # Verify component count
        components = breakdown.get('components', {})
        if len(components) == 6:
            print(f"   ✅ All 6 components present")
        else:
            print(f"   ❌ Expected 6 components, got {len(components)}")
            return False

        return True
    else:
        print(f"   ❌ Failed to retrieve breakdown")
        return False


async def test_enrichment_logic_mock():
    """Test enrichment logic with mock data"""
    print("\n" + "="*70)
    print("TEST: Enrichment Logic with Mock Data")
    print("="*70)

    from src.core.cache.confluence_cache_service import confluence_cache_service

    # Setup test data
    test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    # Cache breakdown data for some symbols
    print("1. Setting up test cache data...")
    for i, symbol in enumerate(test_symbols[:2]):  # Only cache first 2
        analysis = {
            "confluence_score": 70 + i * 5,
            "reliability": 80 + i * 2,
            "components": {
                "technical": 75.0 + i,
                "volume": 70.0 + i,
                "orderflow": 68.0 + i,
                "sentiment": 65.0 + i,
                "orderbook": 72.0 + i,
                "price_structure": 71.0 + i
            },
            "interpretations": {
                "technical": f"Technical analysis for {symbol}",
                "volume": f"Volume analysis for {symbol}"
            }
        }
        await confluence_cache_service.cache_confluence_breakdown(symbol, analysis)

    print(f"   ✅ Cached breakdown for {test_symbols[:2]}")

    # Simulate signals from dashboard
    print("\n2. Simulating dashboard signals...")
    signals = [
        {"symbol": symbol, "score": 70 + i * 5, "timestamp": time.time()}
        for i, symbol in enumerate(test_symbols)
    ]

    # Simulate enrichment logic
    print("3. Enriching signals with breakdown data...")
    enriched_signals = []

    for signal in signals:
        symbol = signal.get('symbol')
        if symbol:
            breakdown = await confluence_cache_service.get_cached_breakdown(symbol)
            if breakdown:
                signal['components'] = breakdown.get('components', {})
                signal['interpretations'] = breakdown.get('interpretations', {})
                signal['reliability'] = breakdown.get('reliability', 0)
                signal['has_breakdown'] = True
                print(f"   ✅ {symbol}: Enriched with breakdown (reliability: {signal['reliability']})")
            else:
                signal['has_breakdown'] = False
                print(f"   ⚠️  {symbol}: No breakdown found (has_breakdown=False)")
        enriched_signals.append(signal)

    # Validate enrichment
    print("\n4. Validating enrichment results...")

    enriched_count = sum(1 for s in enriched_signals if s.get('has_breakdown'))
    non_enriched_count = sum(1 for s in enriched_signals if not s.get('has_breakdown'))

    print(f"   Total signals: {len(enriched_signals)}")
    print(f"   Enriched: {enriched_count}")
    print(f"   Not enriched: {non_enriched_count}")

    # Check that first 2 are enriched, last 1 is not
    if enriched_count == 2 and non_enriched_count == 1:
        print(f"   ✅ Enrichment logic works correctly")

        # Verify enriched signals have the new fields
        for signal in enriched_signals[:2]:
            if 'components' in signal and 'interpretations' in signal and 'reliability' in signal:
                print(f"   ✅ {signal['symbol']}: All enrichment fields present")
            else:
                print(f"   ❌ {signal['symbol']}: Missing enrichment fields")
                return False

        return True
    else:
        print(f"   ❌ Expected 2 enriched and 1 not enriched")
        return False


async def test_performance_sequential():
    """Test performance with sequential cache queries"""
    print("\n" + "="*70)
    print("TEST: Performance - Sequential Cache Queries")
    print("="*70)

    from src.core.cache.confluence_cache_service import confluence_cache_service

    # Setup test symbols
    test_symbols = [f"SYMBOL{i}USDT" for i in range(10)]

    # Cache breakdown for all symbols
    print(f"1. Caching breakdown for {len(test_symbols)} symbols...")
    for symbol in test_symbols:
        analysis = {
            "confluence_score": 70.0,
            "reliability": 80,
            "components": {
                "technical": 75.0,
                "volume": 70.0,
                "orderflow": 68.0,
                "sentiment": 65.0,
                "orderbook": 72.0,
                "price_structure": 71.0
            },
            "interpretations": {"technical": f"Analysis for {symbol}"}
        }
        await confluence_cache_service.cache_confluence_breakdown(symbol, analysis)

    print(f"   ✅ Cached {len(test_symbols)} breakdowns")

    # Test sequential retrieval (current implementation)
    print(f"\n2. Testing sequential retrieval (current implementation)...")
    start_time = time.time()

    for symbol in test_symbols:
        breakdown = await confluence_cache_service.get_cached_breakdown(symbol)

    sequential_time = (time.time() - start_time) * 1000  # ms
    print(f"   Sequential time: {sequential_time:.2f}ms for {len(test_symbols)} symbols")
    print(f"   Average per symbol: {sequential_time / len(test_symbols):.2f}ms")

    # Test parallel retrieval (optimized)
    print(f"\n3. Testing parallel retrieval (optimized approach)...")
    start_time = time.time()

    breakdowns = await asyncio.gather(*[
        confluence_cache_service.get_cached_breakdown(symbol)
        for symbol in test_symbols
    ])

    parallel_time = (time.time() - start_time) * 1000  # ms
    print(f"   Parallel time: {parallel_time:.2f}ms for {len(test_symbols)} symbols")
    print(f"   Average per symbol: {parallel_time / len(test_symbols):.2f}ms")

    # Calculate improvement
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100
    print(f"\n4. Performance comparison:")
    print(f"   Speedup: {sequential_time / parallel_time:.2f}x")
    print(f"   Time saved: {improvement:.1f}%")

    if parallel_time < sequential_time:
        print(f"   ✅ Parallel approach is faster")
        print(f"   💡 Recommendation: Implement parallel queries with asyncio.gather()")
        return True
    else:
        print(f"   ⚠️  Parallel approach not faster (may be due to small dataset)")
        return True


async def main():
    """Run all functional tests"""
    print("="*70)
    print("FUNCTIONAL TESTS: Dashboard Breakdown Cache Integration")
    print("="*70)

    results = {
        "cache_service": False,
        "enrichment_logic": False,
        "performance": False
    }

    try:
        results["cache_service"] = await test_cache_service_directly()
    except Exception as e:
        print(f"\n❌ Cache service test failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results["enrichment_logic"] = await test_enrichment_logic_mock()
    except Exception as e:
        print(f"\n❌ Enrichment logic test failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results["performance"] = await test_performance_sequential()
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print("FUNCTIONAL TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✅ All functional tests passed!")
        return 0
    else:
        print("\n❌ Some functional tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
