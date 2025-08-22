#!/usr/bin/env python3
"""Simple fix for Bybit connection - use basic requests instead of complex async"""
import json

def create_simple_fetcher():
    """Create a simple market data fetcher"""
    
    code = '''
    async def get_market_tickers_simple(self):
        """Simple market ticker fetch without complex timeout handling"""
        try:
            import aiohttp
            import json
            
            url = f"{self.rest_endpoint}/v5/market/tickers"
            params = {"category": "linear"}
            
            # Simple session with basic timeout
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            result = data.get('result', {})
                            tickers = {}
                            for item in result.get('list', [])[:10]:  # Only get first 10
                                symbol = item.get('symbol', '').replace('USDT', '/USDT')
                                tickers[symbol] = {
                                    'last': float(item.get('lastPrice', 0)),
                                    'volume': float(item.get('volume24h', 0)),
                                    'bid': float(item.get('bid1Price', 0)),
                                    'ask': float(item.get('ask1Price', 0))
                                }
                            return tickers
            return {}
        except Exception as e:
            self.logger.error(f"Simple fetch error: {e}")
            return {}
    '''
    
    # Add the method to bybit.py
    bybit_file = "src/core/exchanges/bybit.py"
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Find where to insert (after get_market_tickers method)
    insert_pos = content.find("async def get_market_tickers(self)")
    if insert_pos > 0:
        # Find the end of the method
        end_pos = content.find("\n    async def", insert_pos + 50)
        if end_pos > 0:
            # Insert our simple method
            content = content[:end_pos] + "\n" + code + "\n" + content[end_pos:]
            
            # Also modify get_market_tickers to use the simple version
            content = content.replace(
                "async def get_market_tickers(self):",
                "async def get_market_tickers(self):\n        # Try simple version first\n        result = await self.get_market_tickers_simple()\n        if result:\n            return result\n        # Original complex version below"
            )
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Added simple Bybit fetcher")
    return True

if __name__ == "__main__":
    create_simple_fetcher()