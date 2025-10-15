#!/usr/bin/env python3
"""
Focused validation test for AsyncIO session management and signals cache
"""

import asyncio
import logging
import time
import json
import sys
import os
import warnings

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_cache_signals():
    """Test signals cache behavior directly"""
    print("\n=== Testing Signals Cache ===")

    try:
        import aiomcache
        client = aiomcache.Client('localhost', 11211)

        # Check if signals exist
        signals_data = await client.get(b'analysis:signals')

        if signals_data:
            try:
                data = json.loads(signals_data.decode())
                signal_count = len(data.get('signals', []))
                print(f"✅ Found {signal_count} signals in cache")

                if signal_count > 0:
                    sample_signal = data['signals'][0]
                    print(f"Sample signal: {sample_signal.get('symbol', 'N/A')} - score: {sample_signal.get('confluence_score', 0)}")

                return True
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing signals data: {e}")
                return False
        else:
            print("⚠️  No signals found in cache")
            return False

    except Exception as e:
        print(f"❌ Cache test error: {e}")
        return False
    finally:
        try:
            await client.close()
        except:
            pass

async def test_aggregation():
    """Test signals aggregation"""
    print("\n=== Testing Signals Aggregation ===")

    try:
        from src.main import aggregate_confluence_signals

        print("Running aggregation...")
        await aggregate_confluence_signals()

        # Check results
        await asyncio.sleep(2)
        result = await test_cache_signals()

        if result:
            print("✅ Aggregation successful")
        else:
            print("❌ Aggregation failed - no signals populated")

        return result

    except Exception as e:
        print(f"❌ Aggregation test error: {e}")
        return False

async def test_session_basic():
    """Basic session test"""
    print("\n=== Testing Session Management ===")

    # Capture warnings
    warning_messages = []
    original_showwarning = warnings.showwarning

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        warning_messages.append(str(message))

    warnings.showwarning = capture_warning
    warnings.filterwarnings("always")

    try:
        from src.core.exchanges.bybit import BybitExchange

        print("Creating BybitExchange...")
        exchange = BybitExchange('bybit')

        print("Initializing...")
        success = await exchange.initialize()

        if not success:
            print("❌ Exchange initialization failed")
            return False

        print("✅ Exchange initialized")

        # Test session health
        if exchange.session and not exchange.session.closed:
            print("✅ Session is healthy")
        else:
            print("⚠️  Session is not healthy")

        # Test connector health
        if exchange.connector and not exchange.connector.closed:
            print("✅ Connector is healthy")
        else:
            print("⚠️  Connector is not healthy")

        # Test cleanup
        print("Testing cleanup...")
        await exchange.close()

        # Wait a moment for cleanup
        await asyncio.sleep(1)

        # Check for session/connector warnings
        session_warnings = [w for w in warning_messages if 'session' in w.lower() or 'connector' in w.lower()]

        if session_warnings:
            print(f"⚠️  Found {len(session_warnings)} session/connector warnings:")
            for warning in session_warnings[:3]:  # Show first 3
                print(f"   - {warning}")
        else:
            print("✅ No session/connector warnings detected")

        return len(session_warnings) == 0

    except Exception as e:
        print(f"❌ Session test error: {e}")
        return False
    finally:
        warnings.showwarning = original_showwarning

async def main():
    """Run focused validation tests"""
    print("Starting Focused Validation Tests")
    print("=" * 50)

    results = {}

    # Test 1: Cache signals
    results['cache'] = await test_cache_signals()

    # Test 2: Aggregation
    results['aggregation'] = await test_aggregation()

    # Test 3: Session management
    results['session'] = await test_session_basic()

    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper()}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)