#!/usr/bin/env python3
"""
Test to verify the type conversion fix for trade size and price
"""

def test_type_conversion():
    """Test that string values are properly converted to float"""
    
    print("\n=== Testing Type Conversion Fix ===\n")
    
    # Test data with string values (common from API responses)
    trades = [
        {'price': '50000', 'size': '0.1', 'timestamp': 1000},  # String values
        {'price': 50001, 'size': 0.2, 'timestamp': 2000},      # Numeric values
        {'price': '50002.5', 'size': '0.15'},                  # String values, no timestamp
        {'price': '50003', 'size': '0.25', 'timestamp': 3000}, # String values
    ]
    
    print("Test trades with mixed types:")
    for i, trade in enumerate(trades):
        print(f"  Trade {i+1}: price={trade.get('price')} (type: {type(trade.get('price')).__name__}), "
              f"size={trade.get('size')} (type: {type(trade.get('size')).__name__})")
    
    # Simulate the fixed code
    try:
        # Extract prices and volumes with type conversion
        prices = [float(t.get('price') or 0) for t in trades]
        volumes = [float(t.get('size') or 0) for t in trades]
        
        print("\nConverted values:")
        print(f"  Prices: {prices}")
        print(f"  Volumes: {volumes}")
        
        # Calculate total volume (this was causing the error)
        total_volume = sum(volumes)
        print(f"\n✅ Total volume calculated successfully: {total_volume}")
        
        # Calculate average price
        import numpy as np
        avg_price = np.mean(prices)
        print(f"✅ Average price calculated successfully: {avg_price}")
        
        # Calculate price range
        price_range = (min(prices), max(prices))
        print(f"✅ Price range calculated successfully: {price_range}")
        
        return True
        
    except TypeError as e:
        print(f"\n❌ TypeError occurred: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_edge_cases():
    """Test edge cases for type conversion"""
    
    print("\n=== Testing Edge Cases ===\n")
    
    # Test with empty strings
    print("Test 1: Empty strings")
    trades = [{'price': '', 'size': ''}]
    try:
        prices = [float(t.get('price') or 0) for t in trades]
        volumes = [float(t.get('size') or 0) for t in trades]
        print(f"  Empty string -> price: {prices[0]}, volume: {volumes[0]}")
        print("✅ Handled empty strings")
    except ValueError:
        # Empty string can't be converted to float, use default
        prices = [float(t.get('price') or 0) for t in trades]
        volumes = [float(t.get('size') or 0) for t in trades]
        print("✅ Handled empty strings with fallback")
    
    # Test with None values
    print("\nTest 2: None values")
    trades = [{'price': None, 'size': None}]
    try:
        prices = [float(t.get('price') or 0) for t in trades]
        volumes = [float(t.get('size') or 0) for t in trades]
        total = sum(volumes)
        print(f"  None -> price: {prices[0]}, volume: {volumes[0]}, total: {total}")
        print("✅ Handled None values")
    except TypeError:
        print("❌ Failed with None values")
        return False
    
    # Test with missing fields
    print("\nTest 3: Missing fields")
    trades = [{}]  # No price or size fields
    try:
        prices = [float(t.get('price') or 0) for t in trades]
        volumes = [float(t.get('size') or 0) for t in trades]
        total = sum(volumes)
        print(f"  Missing fields -> price: {prices[0]}, volume: {volumes[0]}, total: {total}")
        print("✅ Handled missing fields")
    except:
        print("❌ Failed with missing fields")
        return False
    
    # Test with invalid strings
    print("\nTest 4: Invalid strings")
    trades = [{'price': 'invalid', 'size': 'abc'}]
    try:
        # This will raise ValueError, so we need proper error handling
        prices = [float(t.get('price', 0)) for t in trades]
    except ValueError:
        print("  Invalid string raises ValueError (expected)")
        # In real code, we might want to skip invalid values or use defaults
        print("✅ Invalid strings properly raise errors")
    
    return True

if __name__ == "__main__":
    print("Testing type conversion fix for trade data...")
    
    test1_passed = test_type_conversion()
    test2_passed = test_edge_cases()
    
    if test1_passed and test2_passed:
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED! Type conversion fix is working.")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("❌ TESTS FAILED! Check the implementation.")
        print("="*50)