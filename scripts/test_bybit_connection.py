#!/usr/bin/env python3
"""Test Bybit connection and data fetching"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.exchanges.bybit import BybitExchange
from src.config.manager import ConfigManager

async def test_bybit():
    """Test Bybit API connection"""
    print("🔍 Testing Bybit connection...")
    
    # Load config
    config_manager = ConfigManager()
    bybit_config = config_manager.config['exchanges']['bybit']
    
    # Create exchange
    exchange = BybitExchange(bybit_config)
    
    try:
        # Initialize
        await exchange.initialize()
        print("✅ Exchange initialized")
        
        # Test market data fetch
        print("📊 Fetching market tickers...")
        tickers = await exchange.get_market_tickers()
        
        if tickers:
            print(f"✅ Got {len(tickers)} tickers")
            # Show first 3
            for symbol, data in list(tickers.items())[:3]:
                print(f"  - {symbol}: ${data.get('last', 'N/A')}")
        else:
            print("❌ No tickers received")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await exchange.cleanup()
        print("🧹 Cleaned up")

if __name__ == "__main__":
    asyncio.run(test_bybit())