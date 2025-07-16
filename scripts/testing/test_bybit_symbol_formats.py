#!/usr/bin/env python3
"""
Test different symbol formats with Bybit to find the correct one for Open Interest
"""

import asyncio
import json
from src.core.exchanges.manager import ExchangeManager
from src.config.manager import ConfigManager

async def test_symbol_formats():
    """Test different symbol formats to find the one that works with Bybit ticker API"""
    
    print("=" * 60)
    print("BYBIT SYMBOL FORMAT TESTING")
    print("=" * 60)
    
    # Initialize config and exchange manager
    config_manager = ConfigManager()
    exchange_manager = ExchangeManager(config_manager)
    
    try:
        # Initialize exchanges
        print("🔧 Initializing exchanges...")
        await exchange_manager.initialize()
        
        # Get Bybit exchange
        bybit = await exchange_manager.get_primary_exchange()
        if not bybit:
            print("❌ Could not get Bybit exchange")
            return
            
        print(f"✅ Connected to {bybit.exchange_id} exchange")
        
        # Test different symbol formats
        test_symbols = [
            'BTC/USDT:USDT',    # CCXT perpetual format
            'BTCUSDT',          # Bybit linear format  
            'BTC/USDT',         # CCXT spot format
            'BTCUSD',           # Bybit inverse format
            'BTC-USDT',         # Alternative format
            'BTC_USDT',         # Alternative format
        ]
        
        for symbol in test_symbols:
            print(f"\n{'='*40}")
            print(f"🧪 TESTING SYMBOL: {symbol}")
            print(f"{'='*40}")
            
            try:
                # Fetch ticker using exchange manager
                ticker = await exchange_manager.fetch_ticker(symbol)
                
                if not ticker:
                    print(f"❌ No ticker data for {symbol}")
                    continue
                
                # Check if we have actual data (not all zeros)
                has_data = (ticker.get('last', 0) > 0 or 
                           ticker.get('baseVolume', 0) > 0 or 
                           ticker.get('quoteVolume', 0) > 0)
                
                print(f"✅ Ticker received - Has data: {has_data}")
                print(f"   Last price: {ticker.get('last', 0)}")
                print(f"   Volume: {ticker.get('baseVolume', 0)}")
                print(f"   Quote volume: {ticker.get('quoteVolume', 0)}")
                
                # Check info section
                if 'info' in ticker and ticker['info']:
                    info = ticker['info']
                    print(f"✅ Has 'info' section with {len(info)} fields")
                    
                    # Check for OI fields
                    oi_fields = ['openInterest', 'openInterestValue']
                    oi_found = []
                    
                    for field in oi_fields:
                        if field in info:
                            value = info[field]
                            oi_found.append(f"{field}: {value}")
                    
                    if oi_found:
                        print(f"🎯 Open Interest found: {', '.join(oi_found)}")
                    else:
                        print(f"❌ No Open Interest fields found")
                        print(f"   Available fields: {list(info.keys())[:10]}...")  # Show first 10
                else:
                    print(f"❌ No 'info' section")
                    
            except Exception as e:
                print(f"❌ Error fetching {symbol}: {e}")
                
        print(f"\n{'='*60}")
        print("SUMMARY - Testing completed")
        print(f"{'='*60}")
                
    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n🔧 Closing connections...")
        await exchange_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_symbol_formats()) 