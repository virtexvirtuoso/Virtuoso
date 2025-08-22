#!/usr/bin/env python3
"""Patch Bybit to use working API call"""

def patch_bybit():
    """Add working ticker fetch method"""
    
    patch = '''

# === PATCHED METHOD FOR WORKING TICKER FETCH ===
async def get_market_tickers_working(self) -> Dict[str, Dict[str, float]]:
    """Working ticker fetch without timeout issues"""
    import aiohttp
    
    try:
        url = f"{self.rest_endpoint}/v5/market/tickers"
        params = {"category": "linear"}
        
        # Simple session that works
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        tickers = {}
                        for item in data.get('result', {}).get('list', [])[:20]:
                            symbol = item.get('symbol', '').replace('USDT', '/USDT')
                            tickers[symbol] = {
                                'symbol': symbol,
                                'last': float(item.get('lastPrice', 0)),
                                'bid': float(item.get('bid1Price', 0)),
                                'ask': float(item.get('ask1Price', 0)),
                                'volume': float(item.get('volume24h', 0))
                            }
                        self.logger.info(f"✅ Got {len(tickers)} tickers")
                        return tickers
    except Exception as e:
        self.logger.error(f"Ticker fetch error: {e}")
    
    return {}

# Override the original method
BybitExchange.get_market_tickers = get_market_tickers_working
'''
    
    # Add to the end of bybit.py
    with open("src/core/exchanges/bybit.py", "a") as f:
        f.write(patch)
    
    print("✅ Patched Bybit with working ticker fetch")
    
    # Also fix top_symbols.py to use the new method
    top_symbols_file = "src/core/market/top_symbols.py"
    with open(top_symbols_file, "r") as f:
        content = f.read()
    
    # Make it call get_market_tickers instead of complex fetch
    content = content.replace(
        "tickers = await self.exchange.fetch_market_tickers()",
        "tickers = await self.exchange.get_market_tickers()"
    )
    
    with open(top_symbols_file, "w") as f:
        f.write(content)
    
    print("✅ Updated top_symbols to use working method")

if __name__ == "__main__":
    patch_bybit()