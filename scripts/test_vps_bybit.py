#!/usr/bin/env python3
"""
Test Bybit API connectivity from VPS.
Run this directly on the VPS to verify API access.
"""

import asyncio
import aiohttp
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


async def test_bybit_direct():
    """Test direct Bybit API access."""
    print("=" * 60)
    print("🧪 Testing Bybit API Access from VPS")
    print("=" * 60)
    
    endpoints = {
        'server_time': 'https://api.bybit.com/v5/market/time',
        'ticker_btc': 'https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT',
        'symbols': 'https://api.bybit.com/v5/market/instruments-info?category=spot&limit=5'
    }
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for name, url in endpoints.items():
            print(f"\n📍 Testing: {name}")
            print(f"   URL: {url[:50]}...")
            
            try:
                start = time.time()
                async with session.get(url) as response:
                    elapsed = (time.time() - start) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            print(f"   ✅ Success in {elapsed:.0f}ms")
                            
                            # Show sample data
                            if name == 'server_time':
                                server_time = data['result'].get('timeSecond')
                                print(f"      Server time: {server_time}")
                            elif name == 'ticker_btc':
                                ticker_list = data['result'].get('list', [])
                                if ticker_list:
                                    price = ticker_list[0].get('lastPrice')
                                    print(f"      BTC Price: ${price}")
                            elif name == 'symbols':
                                symbols_list = data['result'].get('list', [])
                                print(f"      Found {len(symbols_list)} symbols")
                        else:
                            print(f"   ❌ API Error: {data.get('retMsg')}")
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        
            except asyncio.TimeoutError:
                print(f"   ❌ Timeout (>10s)")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")
    
    print("\n" + "=" * 60)


async def test_with_ccxt():
    """Test using ccxt library if available."""
    try:
        import ccxt.async_support as ccxt
        
        print("\n📦 Testing with CCXT library...")
        
        exchange = ccxt.bybit({
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        try:
            # Load markets
            print("   Loading markets...", end="")
            markets = await exchange.load_markets()
            print(f" ✅ ({len(markets)} markets)")
            
            # Fetch ticker
            print("   Fetching BTC ticker...", end="")
            ticker = await exchange.fetch_ticker('BTC/USDT')
            print(f" ✅ ${ticker['last']}")
            
            # Fetch order book
            print("   Fetching order book...", end="")
            orderbook = await exchange.fetch_order_book('BTC/USDT', limit=5)
            print(f" ✅ ({len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks)")
            
        except Exception as e:
            print(f"\n   ❌ CCXT Error: {e}")
        finally:
            await exchange.close()
            
    except ImportError:
        print("\n⚠️  CCXT not installed")


async def test_exchange_manager():
    """Test using the project's exchange manager."""
    try:
        from src.config.manager import ConfigManager
        from src.core.exchanges.manager import ExchangeManager
        
        print("\n🔧 Testing with Exchange Manager...")
        
        config_manager = ConfigManager()
        exchange_manager = ExchangeManager(config_manager)
        
        # Initialize
        print("   Initializing exchange manager...", end="")
        success = await exchange_manager.initialize()
        if success:
            print(" ✅")
            
            # Test ticker fetch
            print("   Fetching BTCUSDT ticker...", end="")
            ticker = await exchange_manager.fetch_ticker('BTCUSDT', 'bybit')
            if ticker:
                print(f" ✅ ${ticker.get('last', 'N/A')}")
            else:
                print(" ❌ No data")
                
        else:
            print(" ❌ Failed to initialize")
            
    except Exception as e:
        print(f"\n   ❌ Exchange Manager Error: {e}")


async def main():
    """Run all tests."""
    # Test direct API
    await test_bybit_direct()
    
    # Test with CCXT
    await test_with_ccxt()
    
    # Test with exchange manager
    await test_exchange_manager()
    
    print("\n✅ Testing complete!")
    print("\nSummary:")
    print("- If direct API works: Network is OK, issue is in the code")
    print("- If CCXT works: Consider using it instead of custom implementation")
    print("- If Exchange Manager fails: Check configuration and error handling")


if __name__ == "__main__":
    asyncio.run(main())