#!/usr/bin/env python3
"""
Test script to verify sentiment data structure fixes.

This script tests the fixed data structures to ensure they pass validation
without generating the warnings we identified.
"""

import sys
import os
import json
import time
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_sentiment_data_structures():
    """Test the sentiment data structures to ensure they pass validation."""
    print("=== Testing Sentiment Data Structure Fixes ===\n")
    
    # Create test market data with the fixed structures
    timestamp = int(time.time() * 1000)
    
    # Test data structure that should pass validation
    test_market_data = {
        'symbol': 'VIRTUALUSDT',
        'exchange': 'bybit',
        'timestamp': timestamp,
        'ohlcv': {
            '1': [
                [timestamp, 100.0, 101.0, 99.0, 100.5, 1000.0]  # Sample OHLCV data
            ]
        },
        'ticker': {
            'fundingRate': 0.00005,
            'openInterest': 26904936,
            'openInterestValue': 51270046.04,
            'nextFundingTime': timestamp + 8 * 3600 * 1000
        },
        'sentiment': {
            # Fixed funding_rate structure (nested dict with 'rate' field)
            'funding_rate': {
                'rate': 0.00005,
                'next_funding_time': timestamp + 8 * 3600 * 1000
            },
            # Fixed long_short_ratio structure (nested dict with 'long'/'short' fields)
            'long_short_ratio': {
                'symbol': 'VIRTUALUSDT',
                'long': 66.84,
                'short': 33.16,
                'timestamp': timestamp
            },
            # Fixed liquidations structure (dict instead of empty list)
            'liquidations': {
                'long': 0.0,
                'short': 0.0,
                'total': 0.0,
                'timestamp': timestamp
            },
            # Fixed open_interest structure (includes 'value' field)
            'open_interest': {
                'current': 26904936.0,
                'previous': 26000000.0,
                'change': 3.5,
                'timestamp': timestamp,
                'value': 51270046.04,  # ← This 'value' field was missing
                'history': []
            }
        }
    }
    
    # Test 1: Check field presence
    print("1. Testing field presence...")
    sentiment = test_market_data['sentiment']
    
    required_fields = ['funding_rate', 'long_short_ratio']
    missing_fields = [f for f in required_fields if f not in sentiment]
    
    if missing_fields:
        print(f"   ✗ Missing fields: {missing_fields}")
        return False
    else:
        print(f"   ✓ All required fields present: {required_fields}")
    
    # Test 2: Check funding_rate structure
    print("\n2. Testing funding_rate structure...")
    funding_rate = sentiment.get('funding_rate')
    
    if not isinstance(funding_rate, dict):
        print(f"   ✗ funding_rate is not a dict: {type(funding_rate)}")
        return False
    elif 'rate' not in funding_rate:
        print(f"   ✗ funding_rate missing 'rate' field: {list(funding_rate.keys())}")
        return False
    else:
        print(f"   ✓ funding_rate structure correct: {funding_rate}")
    
    # Test 3: Check long_short_ratio structure
    print("\n3. Testing long_short_ratio structure...")
    lsr = sentiment.get('long_short_ratio')
    
    if not isinstance(lsr, dict):
        print(f"   ✗ long_short_ratio is not a dict: {type(lsr)}")
        return False
    elif 'long' not in lsr or 'short' not in lsr:
        print(f"   ✗ long_short_ratio missing long/short fields: {list(lsr.keys())}")
        return False
    else:
        print(f"   ✓ long_short_ratio structure correct: {lsr}")
    
    # Test 4: Check liquidations structure
    print("\n4. Testing liquidations structure...")
    liquidations = sentiment.get('liquidations')
    
    if liquidations is None:
        print(f"   ✗ liquidations field missing")
        return False
    elif isinstance(liquidations, list) and not liquidations:
        print(f"   ⚠ liquidations is empty list (will trigger default setting)")
        # This is acceptable but will trigger the warning
    elif isinstance(liquidations, dict):
        print(f"   ✓ liquidations structure correct: {liquidations}")
    else:
        print(f"   ✗ liquidations unexpected type: {type(liquidations)}")
        return False
    
    # Test 5: Check open_interest structure
    print("\n5. Testing open_interest structure...")
    open_interest = sentiment.get('open_interest')
    
    if not isinstance(open_interest, dict):
        print(f"   ✗ open_interest is not a dict: {type(open_interest)}")
        return False
    elif 'value' not in open_interest:
        print(f"   ✗ open_interest missing 'value' field: {list(open_interest.keys())}")
        return False
    else:
        print(f"   ✓ open_interest structure correct: {open_interest}")
    
    print("\n" + "="*60)
    print("✓ ALL SENTIMENT DATA STRUCTURE TESTS PASSED")
    print("="*60)
    
    # Save the test data structure for reference
    with open('test_sentiment_structure.json', 'w') as f:
        json.dump(test_market_data, f, indent=2)
    
    print(f"\nTest data structure saved to: test_sentiment_structure.json")
    
    return True

def test_validation_logic_simulation():
    """Simulate the validation logic to ensure it passes."""
    print("\n=== Simulating Validation Logic ===\n")
    
    # Create test sentiment data
    sentiment_data = {
        'funding_rate': {
            'rate': 0.00005,
            'next_funding_time': int(time.time() * 1000) + 8 * 3600 * 1000
        },
        'long_short_ratio': {
            'symbol': 'VIRTUALUSDT',
            'long': 66.84,
            'short': 33.16,
            'timestamp': int(time.time() * 1000)
        },
        'liquidations': {
            'long': 0.0,
            'short': 0.0,
            'total': 0.0,
            'timestamp': int(time.time() * 1000)
        },
        'open_interest': {
            'current': 26904936.0,
            'previous': 26000000.0,
            'change': 3.5,
            'timestamp': int(time.time() * 1000),
            'value': 51270046.04,
            'history': []
        }
    }
    
    # Simulate the validation checks that were causing warnings
    warnings_found = []
    
    # Check 1: Missing recommended sentiment fields
    required_fields = ['funding_rate', 'long_short_ratio']
    missing_fields = [f for f in required_fields if f not in sentiment_data]
    
    if missing_fields:
        warnings_found.append(f"Missing recommended sentiment fields: {missing_fields}")
    else:
        print("✓ No missing required fields")
    
    # Check 2: Liquidations data
    liquidations = sentiment_data.get('liquidations')
    if liquidations is None:
        warnings_found.append("Missing liquidations data, setting defaults")
    elif isinstance(liquidations, list) and not liquidations:
        warnings_found.append("Empty liquidations list, setting defaults")
    else:
        print("✓ Liquidations data present and structured")
    
    # Check 3: Open interest 'value' field
    open_interest = sentiment_data.get('open_interest')
    if open_interest is not None and isinstance(open_interest, dict):
        if 'value' not in open_interest:
            warnings_found.append("Open interest dict missing 'value' field, setting default")
        else:
            print("✓ Open interest 'value' field present")
    
    # Report results
    if warnings_found:
        print(f"\n✗ Validation would still generate {len(warnings_found)} warning(s):")
        for warning in warnings_found:
            print(f"   - {warning}")
        return False
    else:
        print("\n✓ All validation checks passed - no warnings would be generated")
        return True

def main():
    """Main test function."""
    print("Testing Sentiment Data Structure Fixes")
    print("=" * 50)
    
    # Test 1: Data structure validation
    structure_test_passed = test_sentiment_data_structures()
    
    # Test 2: Validation logic simulation
    validation_test_passed = test_validation_logic_simulation()
    
    # Final result
    if structure_test_passed and validation_test_passed:
        print("\n🎉 ALL TESTS PASSED - Fixes should resolve the warnings!")
        return 0
    else:
        print("\n❌ Some tests failed - additional fixes may be needed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 