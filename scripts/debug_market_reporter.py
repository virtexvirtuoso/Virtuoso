#!/usr/bin/env python3
"""
Debug Market Reporter Volume Issue

Test the market overview calculation directly to see if our volume fix is working.
"""

import asyncio
import sys
import os
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add the src directory to Python path
sys.path.insert(0, 'src')

async def debug_volume_data():
    """Debug volume data flow"""
    
    print("=== Debug Market Reporter Volume Data ===")
    
    # Import the market reporter
    from monitoring.market_reporter import MarketReporter
    
    # Create a minimal reporter instance
    reporter = MarketReporter()
    
    # Test symbols
    symbols = ['BTCUSDT', 'ETHUSDT']
    
    try:
        print(f"Testing market overview calculation with symbols: {symbols}")
        
        # Call the market overview calculation directly
        result = await reporter._calculate_market_overview(symbols)
        
        print("=== RESULTS ===")
        print(f"Total volume: {result.get('total_volume', 'NOT_FOUND')}")
        print(f"Total turnover: {result.get('total_turnover', 'NOT_FOUND')}")
        print(f"Volume by pair: {result.get('volume_by_pair', 'NOT_FOUND')}")
        print(f"Failed symbols: {result.get('failed_symbols', 'NOT_FOUND')}")
        
        # Check if we got any data at all
        if result.get('total_volume', 0) > 0:
            print("✅ SUCCESS: Volume data is now working!")
        else:
            print("❌ ISSUE: Volume is still 0.0")
            
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(debug_volume_data()) 