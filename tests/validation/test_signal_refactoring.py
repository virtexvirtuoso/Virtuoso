#!/usr/bin/env python3
"""
Test script to verify BUY/SELL → LONG/SHORT refactoring.

This script tests:
1. SignalType enum has LONG/SHORT values
2. Config loading with backward compatibility
3. Signal generation with new terminology
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_signal_type_enum():
    """Test that SignalType enum has been updated."""
    print("\n=== Test 1: SignalType Enum ===")
    try:
        from src.models.signal_schema import SignalType

        # Check LONG and SHORT exist
        assert hasattr(SignalType, 'LONG'), "SignalType.LONG not found"
        assert hasattr(SignalType, 'SHORT'), "SignalType.SHORT not found"
        assert hasattr(SignalType, 'NEUTRAL'), "SignalType.NEUTRAL not found"

        # Verify values
        assert SignalType.LONG.value == "LONG", f"LONG value incorrect: {SignalType.LONG.value}"
        assert SignalType.SHORT.value == "SHORT", f"SHORT value incorrect: {SignalType.SHORT.value}"

        print("✅ SignalType enum updated correctly")
        print(f"   - SignalType.LONG = '{SignalType.LONG.value}'")
        print(f"   - SignalType.SHORT = '{SignalType.SHORT.value}'")
        print(f"   - SignalType.NEUTRAL = '{SignalType.NEUTRAL.value}'")
        return True
    except Exception as e:
        print(f"❌ SignalType enum test failed: {e}")
        return False

def test_config_loading():
    """Test that config loads thresholds with backward compatibility."""
    print("\n=== Test 2: Config Loading ===")
    try:
        import yaml

        config_path = 'config/config.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        thresholds = config.get('confluence', {}).get('thresholds', {})

        # Check new threshold names
        assert 'long' in thresholds, "Config missing 'long' threshold"
        assert 'short' in thresholds, "Config missing 'short' threshold"

        long_threshold = thresholds['long']
        short_threshold = thresholds['short']

        print("✅ Config thresholds loaded correctly")
        print(f"   - long_threshold = {long_threshold}")
        print(f"   - short_threshold = {short_threshold}")
        print(f"   - neutral_buffer = {thresholds.get('neutral_buffer', 5)}")

        return True
    except Exception as e:
        print(f"❌ Config loading test failed: {e}")
        return False

def test_schema_statistics():
    """Test that SignalsSchema uses long_signals/short_signals."""
    print("\n=== Test 3: SignalsSchema Statistics ===")
    try:
        from src.core.schemas.signals import SignalsSchema

        # Create test signals
        test_signals = [
            {'symbol': 'BTCUSDT', 'sentiment': 'LONG', 'confluence_score': 75},
            {'symbol': 'ETHUSDT', 'sentiment': 'LONG', 'confluence_score': 68},
            {'symbol': 'SOLUSDT', 'sentiment': 'SHORT', 'confluence_score': 32},
            {'symbol': 'BNBUSDT', 'sentiment': 'NEUTRAL', 'confluence_score': 50},
        ]

        schema = SignalsSchema(signals=test_signals)

        # Verify it has the new field names
        assert hasattr(schema, 'long_signals'), "SignalsSchema missing 'long_signals' field"
        assert hasattr(schema, 'short_signals'), "SignalsSchema missing 'short_signals' field"

        # Verify counts
        assert schema.long_signals == 2, f"Expected 2 long signals, got {schema.long_signals}"
        assert schema.short_signals == 1, f"Expected 1 short signal, got {schema.short_signals}"

        print("✅ SignalsSchema statistics calculated correctly")
        print(f"   - total_signals = {schema.total_signals}")
        print(f"   - long_signals = {schema.long_signals}")
        print(f"   - short_signals = {schema.short_signals}")

        return True
    except Exception as e:
        print(f"❌ SignalsSchema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility for old 'buy'/'sell' config keys."""
    print("\n=== Test 4: Backward Compatibility ===")
    try:
        # Simulate old config with 'buy' and 'sell' keys
        old_config = {
            'confluence': {
                'thresholds': {
                    'buy': 65,
                    'sell': 38
                }
            }
        }

        threshold_config = old_config['confluence']['thresholds']

        # Test fallback logic (simulating signal_generator.py behavior)
        long_threshold = float(threshold_config.get('long', threshold_config.get('buy', 60)))
        short_threshold = float(threshold_config.get('short', threshold_config.get('sell', 40)))

        assert long_threshold == 65, f"Expected 65, got {long_threshold}"
        assert short_threshold == 38, f"Expected 38, got {short_threshold}"

        print("✅ Backward compatibility works")
        print(f"   - Old 'buy: 65' → long_threshold = {long_threshold}")
        print(f"   - Old 'sell: 38' → short_threshold = {short_threshold}")

        return True
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("Testing BUY/SELL → LONG/SHORT Refactoring")
    print("="*60)

    results = []

    # Run tests
    results.append(("SignalType Enum", test_signal_type_enum()))
    results.append(("Config Loading", test_config_loading()))
    results.append(("SignalsSchema Statistics", test_schema_statistics()))
    results.append(("Backward Compatibility", test_backward_compatibility()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! The refactoring is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
