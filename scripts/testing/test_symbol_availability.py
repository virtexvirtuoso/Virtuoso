#!/usr/bin/env python3
"""Test script to check available symbols in the system."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import config
from src.core.exchanges.manager import ExchangeManager

async def main():
    """Test symbol availability."""
    print("Testing symbol availability...")
    
    # Initialize exchange manager
    exchange_manager = ExchangeManager(config.get_exchange_config())
    
    try:
        # Initialize exchanges
        await exchange_manager.initialize()
        
        # Get primary exchange
        exchange = await exchange_manager.get_primary_exchange()
        if not exchange:
            print("No primary exchange available")
            return
            
        print(f"Primary exchange: {exchange.id}")
        
        # Load markets
        markets = await exchange.load_markets()
        print(f"Total markets loaded: {len(markets)}")
        
        # Filter for USDT linear perpetuals
        usdt_symbols = [s for s in markets.keys() if s.endswith('USDT') and 'linear' in str(markets[s].get('type', '')).lower()]
        print(f"USDT linear perpetual symbols: {len(usdt_symbols)}")
        
        # Show top 20 symbols
        print("\nTop 20 USDT symbols:")
        for symbol in sorted(usdt_symbols)[:20]:
            print(f"  - {symbol}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await exchange_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())