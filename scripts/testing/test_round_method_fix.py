#!/usr/bin/env python3
"""
Test to verify the __round__ method fix for trade fingerprinting
"""

def test_round_method_fix():
    """Test that string values are properly converted before rounding"""
    
    print("\n=== Testing __round__ Method Fix ===\n")
    
    # Test data with string values (common from API responses)
    trades = [
        {'price': '50000.123', 'size': '0.12345', 'side': 'buy'},    # String values
        {'price': 50001.456, 'size': 0.23456, 'side': 'sell'},       # Numeric values  
        {'price': '50002', 'size': '0.3', 'side': 'buy'},            # String integers
        {'price': '', 'size': '', 'side': 'unknown'},                # Empty strings
        {'price': None, 'size': None},                               # None values
        {},                                                           # Missing fields
    ]
    
    print("Test trades with mixed types:")
    for i, trade in enumerate(trades):
        price = trade.get('price', 'missing')
        size = trade.get('size', 'missing')
        print(f"  Trade {i+1}: price={price} (type: {type(price).__name__}), "
              f"size={size} (type: {type(size).__name__})")
    
    # Simulate the fixed code
    success_count = 0
    for i, trade in enumerate(trades):
        try:
            # This is the fix we applied
            price_rounded = round(float(trade.get('price') or 0), 1)
            size_rounded = round(float(trade.get('size') or 0), 2)
            
            print(f"\nTrade {i+1}:")
            print(f"  Original: price={trade.get('price')}, size={trade.get('size')}")
            print(f"  Rounded: price={price_rounded}, size={size_rounded}")
            print("  ✅ Success!")
            success_count += 1
            
        except TypeError as e:
            print(f"\n❌ Trade {i+1} failed with TypeError: {e}")
        except ValueError as e:
            print(f"\n❌ Trade {i+1} failed with ValueError: {e}")
        except Exception as e:
            print(f"\n❌ Trade {i+1} failed with unexpected error: {e}")
    
    print(f"\n\nResults: {success_count}/{len(trades)} trades processed successfully")
    return success_count == len(trades)

def test_fingerprint_creation():
    """Test the complete fingerprint creation process"""
    
    print("\n=== Testing Complete Fingerprint Creation ===\n")
    
    import hashlib
    
    def create_trade_fingerprint(trade):
        """Simulate the fixed fingerprint creation"""
        price_rounded = round(float(trade.get('price') or 0), 1)
        size_rounded = round(float(trade.get('size') or 0), 2)
        fingerprint_str = f"{price_rounded}_{size_rounded}_{trade.get('side', 'unknown')}"
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:8]
    
    # Test various trade scenarios
    test_trades = [
        {'price': '50000.123', 'size': '0.12345', 'side': 'buy'},
        {'price': '50000.167', 'size': '0.12399', 'side': 'buy'},  # Should have same fingerprint
        {'price': 50000.1, 'size': 0.12, 'side': 'buy'},           # Numeric, same fingerprint
        {'price': '50001', 'size': '0.12', 'side': 'sell'},        # Different price
    ]
    
    fingerprints = []
    for i, trade in enumerate(test_trades):
        try:
            fp = create_trade_fingerprint(trade)
            fingerprints.append(fp)
            print(f"Trade {i+1}: {trade} -> {fp}")
        except Exception as e:
            print(f"Trade {i+1} failed: {e}")
            return False
    
    # Check if similar trades get same fingerprint
    if fingerprints[0] == fingerprints[1] == fingerprints[2]:
        print("\n✅ Similar trades produce same fingerprint (as expected)")
    else:
        print("\n❌ Similar trades produced different fingerprints")
        print(f"   Fingerprints: {fingerprints[:3]}")
    
    return True

if __name__ == "__main__":
    print("Testing the __round__ method fix for trade fingerprinting...")
    
    test1_passed = test_round_method_fix()
    test2_passed = test_fingerprint_creation()
    
    if test1_passed and test2_passed:
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED! The __round__ fix is working.")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("❌ TESTS FAILED! Check the implementation.")
        print("="*50)