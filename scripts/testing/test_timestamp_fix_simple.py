#!/usr/bin/env python3
"""
Simple test to verify the timestamp KeyError fix
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_timestamp_fix():
    """Test the specific methods that were fixed"""
    
    print("\n=== Testing Timestamp Fix ===\n")
    
    # Import the specific module
    try:
        from src.indicators.orderbook_indicators import OrderbookIndicators
        print("✅ Successfully imported OrderbookIndicators")
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return False
    
    # Create a minimal instance
    class MockConfig:
        def __init__(self):
            self.ANALYSIS_CONFIG = {
                'orderbook': {
                    'depth_levels': 10,
                    'imbalance_threshold': 0.6,
                    'large_order_threshold': 10000
                }
            }
            self.RISK_CONFIG = {
                'position_sizing': {
                    'max_position_size': 10000
                }
            }
    
    indicator = OrderbookIndicators(MockConfig())
    
    # Test data with trades - some with timestamp, some without
    test_trades = [
        {
            'price': 50000,
            'size': 0.1,
            'timestamp': 1627500000000,  # Has timestamp
            'side': 'buy'
        },
        {
            'price': 50001,
            'size': 0.2,
            # NO timestamp field - this should not cause error
            'side': 'sell'
        },
        {
            'price': 50002,
            'size': 0.15,
            'timestamp': 1627500001000,  # Has timestamp
            'side': 'buy'
        }
    ]
    
    print("\nTest trades (some missing timestamp):")
    for i, trade in enumerate(test_trades):
        timestamp_status = "has timestamp" if 'timestamp' in trade else "NO TIMESTAMP"
        print(f"  Trade {i+1}: price={trade['price']}, size={trade['size']} - {timestamp_status}")
    
    # Test the fixed method directly
    print("\nTesting _identify_trade_clusters_integrated method...")
    
    try:
        # This method was causing the KeyError
        clusters = indicator._identify_trade_clusters_integrated(test_trades)
        print(f"✅ SUCCESS: Method handled missing timestamps correctly")
        print(f"   Found {len(clusters)} clusters")
        
        # Test with empty list
        empty_clusters = indicator._identify_trade_clusters_integrated([])
        print(f"✅ SUCCESS: Handled empty trades list")
        
    except KeyError as e:
        print(f"❌ FAILED: KeyError occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    except AttributeError as e:
        if "'OrderbookIndicators' object has no attribute '_identify_trade_clusters_integrated'" in str(e):
            print("⚠️  Method not found - checking if it exists in the class...")
            # Check if method exists
            if hasattr(indicator, '_identify_trade_clusters_integrated'):
                print("Method exists but there's another issue")
            else:
                print("Method doesn't exist - might be in a different class")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n=== Test Completed Successfully! ===")
    return True

if __name__ == "__main__":
    success = test_timestamp_fix()
    
    if success:
        print("\n✅ Timestamp fix is working correctly!")
    else:
        print("\n❌ Test failed - check implementation!")