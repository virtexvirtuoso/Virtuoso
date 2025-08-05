#!/usr/bin/env python3
"""
Test script to verify that the Binance fixes are working correctly.

This script tests:
1. Open interest error handling (fixes 400 Bad Request errors)
2. Long/Short ratio support
3. Risk limits (leverage bracket) support
4. Turnover calculation with quoteVolume field

Usage:
    python scripts/test_binance_fixes.py
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.exchanges.binance import BinanceExchange
from src.config.manager import ConfigManager
from data_acquisition.binance.futures_client import BinanceFuturesClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_binance_fixes():
    """Test all fixed Binance issues."""
    
    print("🔧 Testing Binance Fixes")
    print("=" * 40)
    
    try:
        # Load config and initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        print("✅ Config loaded successfully")
        
        logger.info("Creating Binance exchange...")
        exchange = BinanceExchange(config=config)
        
        logger.info("Initializing Binance exchange...")
        await exchange.initialize()
        print("✅ Binance exchange initialized successfully")
        
        # Test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'ALPACAUSDT']
        
        for symbol in test_symbols:
            print(f"\n🎯 Testing {symbol}")
            print("-" * 20)
            
            # Test 1: Open Interest error handling
            print("1️⃣  Testing open interest error handling...")
            try:
                oi = await exchange.client.fetch_open_interest(symbol)
                print(f"   ✅ Open Interest: {oi:,.0f}")
            except Exception as e:
                print(f"   ⚠️  Open Interest: {e}")
            
            # Test 2: Long/Short Ratio 
            print("2️⃣  Testing long/short ratio support...")
            try:
                ratio = await exchange.fetch_long_short_ratio(symbol)
                print(f"   ✅ Long/Short Ratio: {ratio:.1f}% long, {100-ratio:.1f}% short")
            except Exception as e:
                print(f"   ❌ Long/Short Ratio: {e}")
            
            # Test 3: Risk Limits 
            print("3️⃣  Testing risk limits support...")
            try:
                risk_limits = await exchange.fetch_risk_limits(symbol)
                print(f"   ✅ Risk Limits: Max leverage {risk_limits.get('maxLeverage', 'Unknown')}x")
            except Exception as e:
                print(f"   ❌ Risk Limits: {e}")
                
        # Test 4: Turnover calculation
        print("\n💰 Testing turnover calculation with quoteVolume")
        print("-" * 45)
        try:
            tickers = await exchange.fetch_tickers()
            print(f"✅ Retrieved {len(tickers)} market tickers")
            
            # Show top 5 by turnover
            sorted_tickers = sorted(tickers.items(), key=lambda x: float(x[1].get('quoteVolume', 0)), reverse=True)
            print("   📊 Top 5 by turnover:")
            for i, (symbol, data) in enumerate(sorted_tickers[:5]):
                turnover = float(data.get('quoteVolume', 0))
                print(f"      {i+1}. {symbol}: ${turnover:,.0f}")
        except Exception as e:
            print(f"❌ Turnover test failed: {e}")
        
        # Test 5: Exchange Manager compatibility 
        print("\n🏪 Testing Exchange Manager compatibility")
        print("-" * 37)
        required_methods = ['fetch_long_short_ratio', 'fetch_risk_limits', 'fetch_open_interest']
        for method in required_methods:
            if hasattr(exchange, method):
                print(f"   ✅ {method}: Available")
            else:
                print(f"   ❌ {method}: Missing")
                
        # Test 6: Comprehensive static risk limits test
        print("\n🛡️  Testing Static Risk Limits Implementation")
        print("-" * 50)
        
        # Test different symbol categories
        test_categories = {
            'Major Crypto (Tier 1)': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            'Large Cap (Tier 2)': ['ADAUSDT', 'SOLUSDT', 'XRPUSDT'],
            'Memecoins (Tier 3)': ['DOGEUSDT', '1000PEPEUSDT', 'WIFUSDT'],
            'Newer Tokens (Tier 4)': ['ALPACAUSDT', 'FARTCOINUSDT', 'VIRTUALUSDT'],
            'Unknown USDT': ['UNKNOWNUSDT'],
            'Non-USDT': ['BTCETH']
        }
        
        for category, symbols in test_categories.items():
            print(f"\n   📊 {category}:")
            for symbol in symbols:
                try:
                    # Use the futures client directly to test static limits
                    static_limits = exchange.futures_client.get_static_risk_limits(symbol)
                    max_lev = static_limits['maxLeverage']
                    brackets = len(static_limits['brackets'])
                    print(f"      {symbol}: {max_lev}x leverage, {brackets} brackets")
                except Exception as e:
                    print(f"      {symbol}: ❌ Error - {e}")
        
        await exchange.close()
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_binance_fixes()) 