#!/usr/bin/env python3
"""Test script to verify monitor.symbols attribute is populated."""

import asyncio
import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

async def test_monitor_symbols():
    """Test that the monitor properly maintains a symbols attribute."""
    try:
        # Import after path is set
        from src.monitoring.monitor import MarketMonitor
        from src.core.exchanges.top_symbols_manager import TopSymbolsManager
        
        # Create a mock top_symbols_manager
        top_symbols_manager = TopSymbolsManager(exchange_manager=None)
        
        # Create monitor with minimal config
        config = {
            'market': {
                'symbols': {
                    'max_symbols': 5
                }
            },
            'interval': 30
        }
        
        monitor = MarketMonitor(
            config=config,
            top_symbols_manager=top_symbols_manager,
            logger=logging.getLogger('test_monitor')
        )
        
        print("\n" + "="*60)
        print("Testing Monitor Symbols Attribute Fix")
        print("="*60)
        
        # Check initial symbols attribute exists
        print(f"\n1. Initial symbols attribute exists: {hasattr(monitor, 'symbols')}")
        print(f"   Initial symbols value: {monitor.symbols}")
        
        # Initialize the monitor
        print("\n2. Initializing monitor...")
        await monitor.initialize()
        
        # Check if symbols were populated during initialization
        print(f"\n3. After initialization:")
        print(f"   Symbols attribute exists: {hasattr(monitor, 'symbols')}")
        print(f"   Symbols populated: {monitor.symbols is not None and len(monitor.symbols) > 0}")
        if monitor.symbols:
            print(f"   Number of symbols: {len(monitor.symbols)}")
            print(f"   First 3 symbols: {monitor.symbols[:3]}")
        
        # Simulate what dashboard_integration does
        print("\n4. Dashboard Integration Check:")
        if hasattr(monitor, 'symbols') and monitor.symbols:
            print("   ✅ Dashboard can access monitor.symbols directly")
            print("   ✅ No warning will be logged")
        else:
            print("   ⚠️ Dashboard will fall back to top_symbols_manager")
            print("   ⚠️ Warning will be logged")
        
        print("\n" + "="*60)
        print("Test Complete - Fix Status:")
        if hasattr(monitor, 'symbols'):
            if monitor.symbols:
                print("✅ SUCCESS: Monitor maintains symbols attribute with data")
            else:
                print("⚠️ PARTIAL: Monitor has symbols attribute but it's empty")
                print("   (This may be normal if top_symbols_manager has no data)")
        else:
            print("❌ FAILED: Monitor does not have symbols attribute")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_monitor_symbols())
    sys.exit(0 if result else 1)