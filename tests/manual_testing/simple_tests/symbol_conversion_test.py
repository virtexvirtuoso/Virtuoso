#!/usr/bin/env python
"""
Simple test to verify the _convert_to_exchange_symbol method fix
"""

import sys

# Define the original and fixed versions of the method
def original_convert_to_exchange_symbol(symbol):
    """Original method before fix"""
    # Bybit expects symbols without a separator
    if '/' in symbol:
        return symbol.replace('/', '')
    return symbol

def fixed_convert_to_exchange_symbol(symbol):
    """Fixed method that handles :USDT suffix properly"""
    result = symbol
    
    # First, handle the '/' replacement
    if '/' in result:
        result = result.replace('/', '')
    
    # Then handle the :USDT suffix
    if ':USDT' in result:
        result = result.replace(':USDT', '')
        
    return result

# Test cases
test_cases = [
    {"input": "BTC/USDT", "expected_original": "BTCUSDT", "expected_fixed": "BTCUSDT"},
    {"input": "ETH/USDT", "expected_original": "ETHUSDT", "expected_fixed": "ETHUSDT"},
    {"input": "BTCUSDT", "expected_original": "BTCUSDT", "expected_fixed": "BTCUSDT"},
    {"input": "BTCUSDT:USDT", "expected_original": "BTCUSDT:USDT", "expected_fixed": "BTCUSDT"},
    {"input": "ETH/USDT:USDT", "expected_original": "ETHUSDT:USDT", "expected_fixed": "ETHUSDT"}
]

def run_tests():
    """Run all test cases"""
    print("Testing symbol conversion...\n")
    all_passed = True
    
    for i, test in enumerate(test_cases):
        input_symbol = test["input"]
        expected_original = test["expected_original"]
        expected_fixed = test["expected_fixed"]
        
        # Test original version
        result_original = original_convert_to_exchange_symbol(input_symbol)
        original_passed = result_original == expected_original
        
        # Test fixed version
        result_fixed = fixed_convert_to_exchange_symbol(input_symbol)
        fixed_passed = result_fixed == expected_fixed
        
        # Print results
        print(f"Test {i+1}: Input '{input_symbol}'")
        print(f"  Original: '{result_original}' {'✓' if original_passed else '✗'}")
        print(f"  Fixed:    '{result_fixed}' {'✓' if fixed_passed else '✗'}")
        
        # Check the key fix: BTCUSDT:USDT -> BTCUSDT
        if input_symbol == "BTCUSDT:USDT":
            print(f"\n*** Key fix test for '{input_symbol}' ***")
            print(f"  Original: '{result_original}' {'' if original_passed else '(Problem: Keeps the :USDT suffix)'}")
            print(f"  Fixed:    '{result_fixed}' {'' if fixed_passed else '(Problem: Should be BTCUSDT)'}")
            
            # Detailed explanation
            if not original_passed and fixed_passed:
                print(f"  ✓ Fix works! The original method didn't handle the :USDT suffix,")
                print(f"    but the fixed method correctly converts BTCUSDT:USDT to BTCUSDT.")
        
        # Update all_passed
        if not fixed_passed:
            all_passed = False
    
    print("\nSummary of fixes:")
    print("1. Original method: Fails to handle perpetual contract symbols with :USDT suffix")
    print("2. Fixed method: Properly handles both standard (BTC/USDT) and perpetual (BTCUSDT:USDT) symbols")
    print(f"\nOverall test result: {'PASS' if all_passed else 'FAIL'}")
    
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 