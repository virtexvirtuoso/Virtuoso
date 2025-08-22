#!/usr/bin/env python3
"""Override Bybit fetch method with simple working version"""

code = '''
# SIMPLE OVERRIDE - Place this at the END of top_symbols.py

async def simple_fetch_tickers(exchange):
    """Simple ticker fetch that actually works"""
    import aiohttp
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear"}
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        tickers = {}
                        for item in data.get('result', {}).get('list', [])[:15]:
                            symbol = item.get('symbol', '').replace('USDT', '/USDT')
                            tickers[symbol] = {
                                'last': float(item.get('lastPrice', 0)),
                                'volume': float(item.get('volume24h', 0))
                            }
                        return tickers
    except Exception as e:
        print(f"Simple fetch error: {e}")
    return {}
'''

# Add to top_symbols.py
with open("src/core/market/top_symbols.py", "r") as f:
    content = f.read()

# Replace the complex fetch with simple one
new_content = content.replace(
    "tickers = await self.exchange.get_market_tickers()",
    "tickers = await simple_fetch_tickers(self.exchange)"
)

# Add the function at the end
new_content += "\n\n" + code

with open("src/core/market/top_symbols.py", "w") as f:
    f.write(new_content)

print("✅ Added simple ticker fetch override to top_symbols.py")