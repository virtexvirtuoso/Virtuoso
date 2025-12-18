#!/usr/bin/env python3
"""
Validation Test Script for Manipulation Alert Quick Win Enhancements
Tests OI tracking, liquidation correlation, and LSR warnings
"""

import sys
import os
import time
import asyncio
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.monitoring.alert_manager import AlertManager
from src.core.models.liquidation import LiquidationEvent, LiquidationType, LiquidationSeverity


class TestResults:
    """Track test results"""
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def record_pass(self, test_name: str):
        self.tests_run += 1
        self.tests_passed += 1
        print(f"✅ PASS: {test_name}")

    def record_fail(self, test_name: str, error: str):
        self.tests_run += 1
        self.tests_failed += 1
        self.failures.append((test_name, error))
        print(f"❌ FAIL: {test_name}")
        print(f"   Error: {error}")

    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed} ✅")
        print(f"Failed: {self.tests_failed} ❌")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%")

        if self.failures:
            print("\nFailed Tests:")
            for test_name, error in self.failures:
                print(f"  - {test_name}: {error}")

        return self.tests_failed == 0


class MockLiquidationCache:
    """Mock liquidation cache for testing"""
    def __init__(self):
        self.liquidations = []

    def add_liquidation(self, symbol: str, side: str, size: float, price: float, timestamp: datetime):
        """Add a test liquidation with all required fields"""
        # Determine liquidation type based on side
        liq_type = LiquidationType.LONG_LIQUIDATION if side.lower() == 'buy' else LiquidationType.SHORT_LIQUIDATION

        event = LiquidationEvent(
            event_id=f"test_{len(self.liquidations)}",
            symbol=symbol,
            exchange='bybit',
            timestamp=timestamp,
            # Event classification
            liquidation_type=liq_type,
            severity=LiquidationSeverity.MEDIUM,
            confidence_score=0.85,
            # Price and volume metrics
            trigger_price=price,
            price_impact=-2.5 if side.lower() == 'buy' else 2.5,
            volume_spike_ratio=3.2,
            liquidated_amount_usd=size * price,
            # Market microstructure
            bid_ask_spread_pct=0.05,
            order_book_imbalance=0.3,
            market_depth_impact=1.8,
            # Technical indicators
            volatility_spike=2.1,
            # Event characteristics
            duration_seconds=45
        )
        self.liquidations.append(event)

    def get_recent_liquidations(self, symbol: str, exchange: str = None, minutes: int = 60) -> List[LiquidationEvent]:
        """Get recent liquidations (mock implementation)"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [liq for liq in self.liquidations
                if liq.symbol == symbol and liq.timestamp >= cutoff_time]


def create_test_alert_manager() -> AlertManager:
    """Create AlertManager with test configuration"""
    test_config = {
        'monitoring': {
            'alerts': {
                'enabled': True,
                'discord_webhook_url': 'https://test.webhook.url'
            }
        }
    }
    return AlertManager(test_config)


def test_oi_tracking(results: TestResults):
    """Test #1: OI Change Tracking"""
    print("\n" + "="*70)
    print("TEST #1: OI Change Tracking")
    print("="*70)

    alert_manager = create_test_alert_manager()
    symbol = "BTCUSDT"

    # Test 1.1: Track OI increases
    try:
        alert_manager._track_oi_change(symbol, 100_000_000)
        time.sleep(0.1)
        alert_manager._track_oi_change(symbol, 110_000_000)

        oi_change = alert_manager._calculate_oi_change(symbol, 110_000_000, timeframe=1)

        if oi_change is not None and abs(oi_change - 0.10) < 0.01:  # ~10% increase
            results.record_pass("OI tracking - increase detection")
        else:
            results.record_fail("OI tracking - increase detection",
                              f"Expected ~10% change, got {oi_change}")
    except Exception as e:
        results.record_fail("OI tracking - increase detection", str(e))

    # Test 1.2: Track OI decreases
    try:
        alert_manager._track_oi_change(symbol, 110_000_000)
        time.sleep(0.1)
        alert_manager._track_oi_change(symbol, 95_000_000)

        oi_change = alert_manager._calculate_oi_change(symbol, 95_000_000, timeframe=1)

        if oi_change is not None and oi_change < 0:  # Decrease detected
            results.record_pass("OI tracking - decrease detection")
        else:
            results.record_fail("OI tracking - decrease detection",
                              f"Expected negative change, got {oi_change}")
    except Exception as e:
        results.record_fail("OI tracking - decrease detection", str(e))

    # Test 1.3: Context generation for significant changes
    try:
        alert_manager._track_oi_change(symbol, 100_000_000)
        time.sleep(0.1)
        alert_manager._track_oi_change(symbol, 110_000_000)

        context = alert_manager._get_oi_context(symbol, 110_000_000)

        if "OI Change" in context and "+10" in context:
            results.record_pass("OI context generation - positive change")
        else:
            results.record_fail("OI context generation - positive change",
                              f"Expected OI context with +10%, got: {context}")
    except Exception as e:
        results.record_fail("OI context generation - positive change", str(e))

    # Test 1.4: No context for insignificant changes
    try:
        alert_manager._track_oi_change(symbol, 100_000_000)
        time.sleep(0.1)
        alert_manager._track_oi_change(symbol, 101_000_000)  # Only 1% change

        context = alert_manager._get_oi_context(symbol, 101_000_000)

        if context == "":
            results.record_pass("OI context filtering - insignificant change")
        else:
            results.record_fail("OI context filtering - insignificant change",
                              f"Expected empty context for 1% change, got: {context}")
    except Exception as e:
        results.record_fail("OI context filtering - insignificant change", str(e))


def test_liquidation_correlation(results: TestResults):
    """Test #2: Liquidation Correlation"""
    print("\n" + "="*70)
    print("TEST #2: Liquidation Correlation")
    print("="*70)

    alert_manager = create_test_alert_manager()
    symbol = "BTCUSDT"

    # Create mock liquidation cache
    mock_cache = MockLiquidationCache()
    alert_manager.liquidation_cache = mock_cache

    # Test 2.1: Detect significant liquidation spike
    try:
        # Add $2M in liquidations
        current_time = datetime.now(timezone.utc)
        mock_cache.add_liquidation(symbol, 'buy', 10.0, 100000, current_time)
        mock_cache.add_liquidation(symbol, 'buy', 5.0, 100000, current_time)
        mock_cache.add_liquidation(symbol, 'buy', 5.0, 100000, current_time)

        liq_data = alert_manager._check_liquidation_correlation(symbol, timeframe=300)

        if liq_data and liq_data['volume_usd'] >= 1_000_000:
            results.record_pass("Liquidation correlation - spike detection")
        else:
            results.record_fail("Liquidation correlation - spike detection",
                              f"Expected spike detection, got: {liq_data}")
    except Exception as e:
        results.record_fail("Liquidation correlation - spike detection", str(e))

    # Test 2.2: Identify long squeeze pattern
    try:
        # Clear previous liquidations
        mock_cache.liquidations = []

        # Add mostly long liquidations
        current_time = datetime.now(timezone.utc)
        for i in range(15):  # 15 long liquidations
            mock_cache.add_liquidation(symbol, 'buy', 5.0, 100000, current_time)
        for i in range(3):   # 3 short liquidations
            mock_cache.add_liquidation(symbol, 'sell', 5.0, 100000, current_time)

        liq_data = alert_manager._check_liquidation_correlation(symbol, timeframe=300)

        if liq_data and liq_data['long_liquidations'] > liq_data['short_liquidations'] * 2:
            results.record_pass("Liquidation correlation - long squeeze pattern")
        else:
            results.record_fail("Liquidation correlation - long squeeze pattern",
                              f"Expected long squeeze, got: {liq_data}")
    except Exception as e:
        results.record_fail("Liquidation correlation - long squeeze pattern", str(e))

    # Test 2.3: Context generation
    try:
        context = alert_manager._get_liquidation_context(symbol)

        if "Liquidation Spike" in context and "LONG" in context.upper():
            results.record_pass("Liquidation context generation")
        else:
            results.record_fail("Liquidation context generation",
                              f"Expected liquidation context, got: {context}")
    except Exception as e:
        results.record_fail("Liquidation context generation", str(e))

    # Test 2.4: Filter insignificant liquidations
    try:
        # Clear and add small liquidations (<$1M)
        mock_cache.liquidations = []
        current_time = datetime.now(timezone.utc)
        mock_cache.add_liquidation(symbol, 'buy', 1.0, 50000, current_time)  # $50k

        liq_data = alert_manager._check_liquidation_correlation(symbol, timeframe=300)

        if liq_data is None:
            results.record_pass("Liquidation filtering - insignificant volume")
        else:
            results.record_fail("Liquidation filtering - insignificant volume",
                              f"Expected None for <$1M, got: {liq_data}")
    except Exception as e:
        results.record_fail("Liquidation filtering - insignificant volume", str(e))


def test_lsr_warnings(results: TestResults):
    """Test #3: Long/Short Ratio Warnings"""
    print("\n" + "="*70)
    print("TEST #3: Long/Short Ratio Warnings")
    print("="*70)

    alert_manager = create_test_alert_manager()

    # Test 3.1: Extreme long crowding (>75%)
    try:
        lsr = 3.5  # 78% long
        warning = alert_manager._get_lsr_warning(lsr)

        if "EXTREME" in warning and "LONG" in warning:
            results.record_pass("LSR warning - extreme long crowding")
        else:
            results.record_fail("LSR warning - extreme long crowding",
                              f"Expected EXTREME LONG warning, got: {warning}")
    except Exception as e:
        results.record_fail("LSR warning - extreme long crowding", str(e))

    # Test 3.2: High short crowding (70-75%)
    try:
        lsr = 0.35  # 26% long = 74% short
        warning = alert_manager._get_lsr_warning(lsr)

        if ("HIGH" in warning or "EXTREME" in warning) and "SHORT" in warning:
            results.record_pass("LSR warning - high short crowding")
        else:
            results.record_fail("LSR warning - high short crowding",
                              f"Expected HIGH SHORT warning, got: {warning}")
    except Exception as e:
        results.record_fail("LSR warning - high short crowding", str(e))

    # Test 3.3: Moderate imbalance (65-70%)
    try:
        lsr = 2.0  # 67% long
        warning = alert_manager._get_lsr_warning(lsr)

        if "MODERATE" in warning and "LONG" in warning:
            results.record_pass("LSR warning - moderate long crowding")
        else:
            results.record_fail("LSR warning - moderate long crowding",
                              f"Expected MODERATE LONG warning, got: {warning}")
    except Exception as e:
        results.record_fail("LSR warning - moderate long crowding", str(e))

    # Test 3.4: Balanced position (no warning)
    try:
        lsr = 1.0  # 50% long, 50% short
        warning = alert_manager._get_lsr_warning(lsr)

        if warning == "":
            results.record_pass("LSR warning - balanced (no warning)")
        else:
            results.record_fail("LSR warning - balanced (no warning)",
                              f"Expected no warning for balanced LSR, got: {warning}")
    except Exception as e:
        results.record_fail("LSR warning - balanced (no warning)", str(e))


def test_integration(results: TestResults):
    """Test #4: Full Integration"""
    print("\n" + "="*70)
    print("TEST #4: Full Integration")
    print("="*70)

    alert_manager = create_test_alert_manager()
    symbol = "BTCUSDT"

    # Set up mock liquidation cache
    mock_cache = MockLiquidationCache()
    alert_manager.liquidation_cache = mock_cache

    # Test 4.1: Generate interpretation with all enhancements
    try:
        # Setup: OI increase
        alert_manager._track_oi_change(symbol, 100_000_000)
        time.sleep(0.1)
        alert_manager._track_oi_change(symbol, 110_000_000)

        # Setup: Liquidations
        current_time = datetime.now(timezone.utc)
        for i in range(20):
            mock_cache.add_liquidation(symbol, 'buy', 5.0, 100000, current_time)

        # Setup: Market data with all context
        market_data = {
            'funding': {
                'openInterest': 110_000_000
            },
            'long_short_ratio': {
                'longShortRatio': 3.0  # 75% long
            }
        }

        # Generate interpretation
        interpretation = alert_manager._generate_plain_english_interpretation(
            signal_strength="CONFLICTING",
            subtype="accumulation",
            symbol=symbol,
            usd_value=2_000_000,
            trades_count=10,
            buy_volume=0,
            sell_volume=100,
            signal_context="POTENTIAL MANIPULATION DETECTED",
            market_data=market_data
        )

        # Verify all enhancements are present
        has_oi = "OI Change" in interpretation
        has_liquidation = "Liquidation Spike" in interpretation
        has_lsr = "Crowd Position" in interpretation

        if has_oi and has_liquidation and has_lsr:
            results.record_pass("Integration - all enhancements present")
        else:
            results.record_fail("Integration - all enhancements present",
                              f"Missing: OI={has_oi}, Liq={has_liquidation}, LSR={has_lsr}")
    except Exception as e:
        results.record_fail("Integration - all enhancements present", str(e))

    # Test 4.2: Graceful degradation (no market data)
    try:
        interpretation = alert_manager._generate_plain_english_interpretation(
            signal_strength="EXECUTING",
            subtype="accumulation",
            symbol=symbol,
            usd_value=2_000_000,
            trades_count=5,
            buy_volume=50,
            sell_volume=0,
            signal_context="Active whale trades",
            market_data=None  # No market data
        )

        # Should still work without enhancements
        if len(interpretation) > 0 and "whale" in interpretation.lower():
            results.record_pass("Integration - graceful degradation")
        else:
            results.record_fail("Integration - graceful degradation",
                              f"Expected basic interpretation, got: {interpretation[:100]}")
    except Exception as e:
        results.record_fail("Integration - graceful degradation", str(e))


def main():
    """Run all validation tests"""
    print("\n" + "="*70)
    print("MANIPULATION ALERT ENHANCEMENTS - VALIDATION TEST SUITE")
    print("="*70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = TestResults()

    # Run all test suites
    test_oi_tracking(results)
    test_liquidation_correlation(results)
    test_lsr_warnings(results)
    test_integration(results)

    # Print summary
    success = results.print_summary()

    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
