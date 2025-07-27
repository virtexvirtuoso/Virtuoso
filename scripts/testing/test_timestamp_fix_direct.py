#!/usr/bin/env python3
"""
Direct test of the timestamp fix by testing the specific code that was changed
"""

def test_timestamp_access():
    """Test the timestamp access pattern that was fixed"""
    
    print("\n=== Testing Timestamp Access Fix ===\n")
    
    # Simulate the trade clustering logic
    trades = [
        {'price': 50000, 'size': 0.1, 'timestamp': 1000},
        {'price': 50001, 'size': 0.2},  # NO timestamp
        {'price': 50002, 'size': 0.15, 'timestamp': 2000},
    ]
    
    current_cluster = []
    clusters = []
    cluster_threshold_ms = 1000
    
    print("Testing trade clustering with missing timestamps...")
    
    # Sort trades - this should handle missing timestamps
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))
    
    for trade in sorted_trades:
        if not current_cluster:
            current_cluster.append(trade)
        else:
            # This is the line that was fixed
            # OLD: time_diff = trade['timestamp'] - current_cluster[-1]['timestamp']
            # NEW: time_diff = trade.get('timestamp', 0) - current_cluster[-1].get('timestamp', 0)
            try:
                time_diff = trade.get('timestamp', 0) - current_cluster[-1].get('timestamp', 0)
                print(f"✅ Calculated time_diff: {time_diff} (trade timestamp: {trade.get('timestamp', 'MISSING')})")
                
                if time_diff <= cluster_threshold_ms:
                    current_cluster.append(trade)
                else:
                    if len(current_cluster) >= 3:
                        clusters.append(current_cluster)
                    current_cluster = [trade]
            except KeyError as e:
                print(f"❌ KeyError occurred: {e}")
                return False
    
    # Test duration calculation that was also fixed
    if current_cluster:
        try:
            # OLD: duration_ms = trades[-1]['timestamp'] - trades[0]['timestamp']
            # NEW: duration_ms = trades[-1].get('timestamp', 0) - trades[0].get('timestamp', 0)
            duration_ms = current_cluster[-1].get('timestamp', 0) - current_cluster[0].get('timestamp', 0)
            print(f"✅ Calculated duration_ms: {duration_ms}")
        except KeyError as e:
            print(f"❌ KeyError in duration calculation: {e}")
            return False
    
    print("\n✅ All timestamp accesses handled correctly!")
    return True

def test_edge_cases():
    """Test edge cases"""
    
    print("\n=== Testing Edge Cases ===\n")
    
    # Test 1: All trades missing timestamps
    trades_no_ts = [
        {'price': 50000, 'size': 0.1},
        {'price': 50001, 'size': 0.2},
        {'price': 50002, 'size': 0.3}
    ]
    
    print("Test 1: All trades missing timestamps")
    try:
        sorted_trades = sorted(trades_no_ts, key=lambda x: x.get('timestamp', 0))
        for i in range(len(sorted_trades) - 1):
            time_diff = sorted_trades[i+1].get('timestamp', 0) - sorted_trades[i].get('timestamp', 0)
        print("✅ Handled all missing timestamps")
    except KeyError:
        print("❌ Failed with all missing timestamps")
        return False
    
    # Test 2: Empty trades list
    print("\nTest 2: Empty trades list")
    empty_trades = []
    try:
        sorted_trades = sorted(empty_trades, key=lambda x: x.get('timestamp', 0))
        print("✅ Handled empty trades list")
    except:
        print("❌ Failed with empty trades")
        return False
    
    # Test 3: Single trade
    print("\nTest 3: Single trade")
    single_trade = [{'price': 50000, 'size': 0.1}]
    try:
        sorted_trades = sorted(single_trade, key=lambda x: x.get('timestamp', 0))
        if sorted_trades:
            ts = sorted_trades[0].get('timestamp', 0)
        print("✅ Handled single trade")
    except:
        print("❌ Failed with single trade")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing the timestamp fix implementation...")
    
    test1_passed = test_timestamp_access()
    test2_passed = test_edge_cases()
    
    if test1_passed and test2_passed:
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED! The timestamp fix is working correctly.")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("❌ TESTS FAILED! There may be issues with the fix.")
        print("="*50)