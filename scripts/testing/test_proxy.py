import os
os.environ['HTTP_PROXY'] = 'socks5://localhost:8080'
os.environ['HTTPS_PROXY'] = 'socks5://localhost:8080'

import ccxt
import asyncio

async def test():
    try:
        # Test Bybit with proxy
        exchange = ccxt.bybit({
            'proxies': {
                'http': 'socks5://localhost:8080',
                'https': 'socks5://localhost:8080'
            }
        })
        
        result = await exchange.fetch_time()
        print(f"✅ Success\! Server time: {result}")
        
        # Check IP location
        import aiohttp
        async with aiohttp.ClientSession() as session:
            proxy = "socks5://localhost:8080"
            async with session.get('https://ipinfo.io/json', proxy=proxy) as resp:
                data = await resp.json()
                print(f"📍 Connected from: {data.get('city')}, {data.get('country')} ({data.get('ip')})")
        
        await exchange.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
