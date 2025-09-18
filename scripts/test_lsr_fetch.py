#!/usr/bin/env python3
"""Test script to diagnose LSR fetching issues."""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.exchanges.bybit import BybitExchange

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

async def test_lsr_fetch():
    """Test fetching long/short ratio data."""
    
    # Initialize exchange with minimal config
    config = {
        'exchanges': {
            'bybit': {
                'api_key': os.environ.get('BYBIT_API_KEY', ''),
                'api_secret': os.environ.get('BYBIT_API_SECRET', ''),
                'testnet': False,
                'websocket': {'enabled': False}
            }
        }
    }
    
    exchange = BybitExchange(config)
    
    # Initialize the exchange
    print("Initializing Bybit exchange...")
    success = await exchange.initialize()
    if not success:
        print("Failed to initialize exchange!")
        return
    
    # Test symbols
    test_symbols = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT']
    
    for symbol in test_symbols:
        print(f"\n{'='*60}")
        print(f"Testing LSR fetch for {symbol}")
        print('='*60)
        
        try:
            # Fetch LSR data
            lsr_data = await exchange._fetch_long_short_ratio(symbol)
            
            print(f"\nLSR Response for {symbol}:")
            print(f"  Long: {lsr_data.get('long', 'N/A')}%")
            print(f"  Short: {lsr_data.get('short', 'N/A')}%") 
            print(f"  Timestamp: {lsr_data.get('timestamp', 'N/A')}")
            
            # Check if it's the default values
            if lsr_data.get('long') == 50.0 and lsr_data.get('short') == 50.0:
                print("  ⚠️  WARNING: Default values detected (50/50)")
            else:
                print("  ✅ Real data received!")
                
        except Exception as e:
            print(f"  ❌ Error fetching LSR: {e}")
            import traceback
            traceback.print_exc()
    
    # Cleanup
    await exchange.cleanup()
    print("\n✅ Test complete!")

if __name__ == '__main__':
    asyncio.run(test_lsr_fetch())