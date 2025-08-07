#!/usr/bin/env python3
"""
Test Bybit API access with proper headers to bypass 403 errors.
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_with_headers():
    """Test Bybit API with browser-like headers."""
    
    # Browser-like headers to bypass CloudFlare
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Origin': 'https://www.bybit.com',
        'Referer': 'https://www.bybit.com/'
    }
    
    test_urls = {
        'server_time': 'https://api.bybit.com/v5/market/time',
        'ticker': 'https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT',
        'symbols': 'https://api.bybit.com/v5/market/instruments-info?category=spot&limit=1'
    }
    
    print("=" * 60)
    print("🧪 Testing Bybit API with Browser Headers")
    print("=" * 60)
    print(f"Time: {datetime.now()}\n")
    
    async with aiohttp.ClientSession() as session:
        for name, url in test_urls.items():
            print(f"\n📍 Testing: {name}")
            print(f"   URL: {url}")
            
            # Test without headers
            print("   Without headers: ", end="")
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print(f"✅ Success (200)")
                    else:
                        print(f"❌ Failed ({response.status})")
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
            
            # Test with headers
            print("   With headers: ", end="")
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Success (200)")
                        
                        # Show sample data
                        if name == 'server_time' and 'result' in data:
                            server_time = data['result'].get('timeSecond', 'N/A')
                            print(f"      Server time: {server_time}")
                        elif name == 'ticker' and 'result' in data:
                            ticker_data = data['result'].get('list', [])
                            if ticker_data:
                                price = ticker_data[0].get('lastPrice', 'N/A')
                                print(f"      BTC Price: ${price}")
                    else:
                        print(f"❌ Failed ({response.status})")
                        body = await response.text()
                        if len(body) < 200:
                            print(f"      Response: {body}")
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print("💡 Recommendations:")
    print("- If headers work: Update the Bybit exchange implementation")
    print("- If both fail: Check network/firewall or use VPN")
    print("- Consider using ccxt library which handles headers automatically")
    print("=" * 60)


async def test_with_ccxt():
    """Test using ccxt library."""
    try:
        import ccxt.async_support as ccxt
        
        print("\n🔧 Testing with CCXT library...")
        
        exchange = ccxt.bybit({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        try:
            # Test fetching ticker
            ticker = await exchange.fetch_ticker('BTC/USDT')
            print(f"✅ CCXT Success!")
            print(f"   BTC Price: ${ticker['last']}")
            print(f"   24h Volume: {ticker['baseVolume']}")
            
        except Exception as e:
            print(f"❌ CCXT Failed: {e}")
        finally:
            await exchange.close()
            
    except ImportError:
        print("⚠️ CCXT not installed. Run: pip install ccxt")


async def test_alternative_endpoints():
    """Test alternative Bybit endpoints."""
    
    alternative_urls = [
        'https://api-testnet.bybit.com/v5/market/time',  # Testnet
        'https://api.bytick.com/v5/market/time',  # Alternative domain
        'https://api.bybit.nl/v5/market/time',  # Netherlands endpoint
    ]
    
    print("\n🌍 Testing Alternative Endpoints...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; TradingBot/1.0)'
    }
    
    async with aiohttp.ClientSession() as session:
        for url in alternative_urls:
            print(f"\n   {url}: ", end="")
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print(f"✅ Success")
                    else:
                        print(f"❌ Status {response.status}")
            except Exception as e:
                error_msg = str(e)
                if 'Cannot connect' in error_msg:
                    print(f"❌ Cannot connect")
                elif 'TimeoutError' in error_msg:
                    print(f"❌ Timeout")
                else:
                    print(f"❌ {error_msg[:30]}")


async def main():
    """Main test execution."""
    
    # Test with headers
    await test_with_headers()
    
    # Test with ccxt
    await test_with_ccxt()
    
    # Test alternatives
    await test_alternative_endpoints()
    
    print("\n✅ Testing complete!")
    print("\nNext steps:")
    print("1. If headers work → Update src/core/exchanges/bybit.py")
    print("2. If CCXT works → Consider using it instead of raw API")
    print("3. If nothing works → Check firewall/VPN or use proxy")


if __name__ == "__main__":
    asyncio.run(main())