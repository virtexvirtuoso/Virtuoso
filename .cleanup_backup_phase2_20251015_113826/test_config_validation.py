#!/usr/bin/env python3
"""
Test script to validate RPI integration configuration issue analysis.
This script tests the claims about empty config causing KeyError: 'timeframes'
"""

import sys
import os
import traceback
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_empty_config_scenario():
    """Test OrderbookIndicators initialization with empty config to reproduce KeyError."""
    print("=== Testing Empty Config Scenario ===")

    try:
        from src.indicators.orderbook_indicators import OrderbookIndicators

        # Test with empty config (this should cause KeyError: 'timeframes')
        print("1. Attempting to initialize OrderbookIndicators with empty config {}")
        indicators = OrderbookIndicators(config_data={})
        print("   UNEXPECTED: Empty config initialization succeeded!")
        return False

    except KeyError as e:
        if 'timeframes' in str(e):
            print(f"   EXPECTED KeyError: {e}")
            print("   ✓ Claim validated: Empty config causes KeyError: 'timeframes'")
            return True
        else:
            print(f"   UNEXPECTED KeyError (not timeframes): {e}")
            return False
    except Exception as e:
        print(f"   UNEXPECTED Exception: {type(e).__name__}: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_full_config_scenario():
    """Test OrderbookIndicators initialization with full config to validate resolution."""
    print("\n=== Testing Full Config Scenario ===")

    try:
        from src.indicators.orderbook_indicators import OrderbookIndicators

        # Create a full config with timeframes section
        full_config = {
            'timeframes': {
                'base': {
                    'interval': 1,
                    'weight': 0.4,
                    'validation': {'min_candles': 50}
                },
                'ltf': {
                    'interval': 5,
                    'weight': 0.3,
                    'validation': {'min_candles': 30}
                },
                'mtf': {
                    'interval': 15,
                    'weight': 0.2,
                    'validation': {'min_candles': 20}
                },
                'htf': {
                    'interval': 60,
                    'weight': 0.1,
                    'validation': {'min_candles': 10}
                }
            },
            'orderbook': {
                'depth_levels': 10,
                'weights': {
                    'imbalance': 0.3,
                    'pressure': 0.3,
                    'liquidity': 0.2,
                    'spread': 0.2
                }
            }
        }

        print("2. Attempting to initialize OrderbookIndicators with full config")
        indicators = OrderbookIndicators(config_data=full_config)
        print("   ✓ Full config initialization succeeded!")
        print(f"   Component weights: {indicators.component_weights}")
        print(f"   Has retail component: {'retail' in indicators.component_weights}")
        return True

    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_retail_component_integration():
    """Test that retail sentiment component is properly integrated."""
    print("\n=== Testing Retail Component Integration ===")

    try:
        from src.indicators.orderbook_indicators import OrderbookIndicators

        # Full config for initialization
        full_config = {
            'timeframes': {
                'base': {'interval': 1, 'weight': 0.4, 'validation': {'min_candles': 50}},
                'ltf': {'interval': 5, 'weight': 0.3, 'validation': {'min_candles': 30}},
                'mtf': {'interval': 15, 'weight': 0.2, 'validation': {'min_candles': 20}},
                'htf': {'interval': 60, 'weight': 0.1, 'validation': {'min_candles': 10}}
            }
        }

        indicators = OrderbookIndicators(config_data=full_config)

        # Validate retail component is present
        retail_weight = indicators.component_weights.get('retail', 0)
        print(f"3. Retail component weight: {retail_weight}")

        if retail_weight > 0:
            print("   ✓ Retail component is integrated with proper weight")

            # Validate total component count
            component_count = len(indicators.component_weights)
            print(f"   Total components: {component_count}")

            if component_count == 9:  # Should be 9 components including retail
                print("   ✓ All 9 components are present (including retail)")
                return True
            else:
                print(f"   ❌ Expected 9 components, found {component_count}")
                return False
        else:
            print("   ❌ Retail component missing or has zero weight")
            return False

    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
        return False

def main():
    """Main test execution."""
    print("RPI Integration Configuration Validation Test")
    print("=" * 50)

    results = {
        'empty_config_test': test_empty_config_scenario(),
        'full_config_test': test_full_config_scenario(),
        'retail_integration_test': test_retail_component_integration()
    }

    print(f"\n=== Test Results Summary ===")
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall Result: {'✓ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)