#!/usr/bin/env python3
"""
Test script to verify the timestamp KeyError fix in orderbook_indicators.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.indicators.orderbook_indicators import OrderbookIndicators
from src.config.trading.market_config import MarketConfig
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_timestamp_fix():
    """Test that missing timestamp fields don't cause KeyError"""
    
    print("\n=== Testing Timestamp Fix ===\n")
    
    # Initialize indicator
    market_config = MarketConfig()
    indicator = OrderbookIndicators(market_config)
    
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
        },
        {
            'price': 50003,
            'size': 0.25,
            # NO timestamp field
            'side': 'sell'
        }
    ]
    
    print("Test trades (some missing timestamp):")
    for i, trade in enumerate(test_trades):
        timestamp_status = "has timestamp" if 'timestamp' in trade else "NO TIMESTAMP"
        print(f"  Trade {i+1}: price={trade['price']}, size={trade['size']} - {timestamp_status}")
    
    print("\nTesting _identify_trade_clusters_integrated method...")
    
    try:
        # This method was causing the KeyError
        clusters = indicator._identify_trade_clusters_integrated(test_trades)
        print(f"✅ SUCCESS: Method handled missing timestamps correctly")
        print(f"   Found {len(clusters)} clusters")
        
        # Also test _analyze_trade_patterns_integrated
        print("\nTesting _analyze_trade_patterns_integrated method...")
        result = indicator._analyze_trade_patterns_integrated(test_trades)
        print(f"✅ SUCCESS: Trade pattern analysis completed")
        print(f"   Pattern score: {result.get('pattern_score', 0)}")
        print(f"   Velocity: {result.get('velocity', 0)}")
        
    except KeyError as e:
        print(f"❌ FAILED: KeyError occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test with empty trades
    print("\nTesting with empty trades list...")
    try:
        empty_result = indicator._analyze_trade_patterns_integrated([])
        print(f"✅ SUCCESS: Handled empty trades correctly")
    except Exception as e:
        print(f"❌ FAILED with empty trades: {e}")
        return False
    
    # Test with all trades missing timestamp
    print("\nTesting with all trades missing timestamp...")
    trades_no_timestamp = [
        {'price': 50000, 'size': 0.1, 'side': 'buy'},
        {'price': 50001, 'size': 0.2, 'side': 'sell'},
        {'price': 50002, 'size': 0.15, 'side': 'buy'}
    ]
    
    try:
        clusters = indicator._identify_trade_clusters_integrated(trades_no_timestamp)
        print(f"✅ SUCCESS: Handled all missing timestamps correctly")
        print(f"   Found {len(clusters)} clusters")
    except Exception as e:
        print(f"❌ FAILED with all missing timestamps: {e}")
        return False
    
    print("\n=== All Tests Passed! ===")
    return True

def main():
    """Run the test"""
    success = asyncio.run(test_timestamp_fix())
    
    if success:
        print("\n✅ Timestamp fix is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Timestamp fix has issues!")
        sys.exit(1)

if __name__ == "__main__":
    main()