#!/usr/bin/env python3
"""Final fix for Bybit - replace problematic timeout code with working version"""

def fix_bybit_api():
    """Replace the broken get_market_tickers with working version"""
    
    # Working implementation based on our test
    new_method = '''    async def get_market_tickers(self) -> Dict[str, Dict[str, float]]:
        """Fetch market tickers - FIXED VERSION"""
        try:
            self.logger.debug("Fetching market tickers from Bybit V5 API...")
            
            url = f"{self.rest_endpoint}/v5/market/tickers"
            params = {"category": "linear"}
            
            # Create simple session without complex timeout handling
            if not hasattr(self, '_simple_session') or self._simple_session.closed:
                timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=50)
                self._simple_session = aiohttp.ClientSession(timeout=timeout)
            
            async with self._simple_session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('retCode') == 0:
                        result = data.get('result', {})
                        tickers = {}
                        
                        # Process tickers
                        for item in result.get('list', [])[:50]:  # Limit to 50 symbols
                            symbol = item.get('symbol', '')
                            # Convert BTCUSDT to BTC/USDT format
                            if 'USDT' in symbol and not '/' in symbol:
                                symbol = symbol.replace('USDT', '/USDT')
                            
                            tickers[symbol] = {
                                'symbol': symbol,
                                'last': float(item.get('lastPrice', 0)),
                                'bid': float(item.get('bid1Price', 0)),
                                'ask': float(item.get('ask1Price', 0)),
                                'volume': float(item.get('volume24h', 0)),
                                'percentage': float(item.get('price24hPcnt', 0)) * 100,
                                'high': float(item.get('highPrice24h', 0)),
                                'low': float(item.get('lowPrice24h', 0))
                            }
                        
                        self.logger.info(f"✅ Got {len(tickers)} tickers from Bybit")
                        return tickers
                    else:
                        self.logger.error(f"API error: {data.get('retMsg')}")
                else:
                    self.logger.error(f"HTTP error: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch tickers: {e}")
        
        return {}
'''

    # Also add cleanup for the session
    cleanup_addition = '''
        # Clean up simple session if exists
        if hasattr(self, '_simple_session') and not self._simple_session.closed:
            await self._simple_session.close()
'''
    
    bybit_file = "src/core/exchanges/bybit.py"
    
    # Read the file
    with open(bybit_file, 'r') as f:
        lines = f.readlines()
    
    # Find and replace the get_market_tickers method
    in_method = False
    method_start = -1
    method_end = -1
    indent_count = 0
    
    for i, line in enumerate(lines):
        if 'async def get_market_tickers(self)' in line:
            in_method = True
            method_start = i
            continue
            
        if in_method:
            # Check if we've reached the next method
            if line.strip().startswith('async def ') and i > method_start:
                method_end = i
                break
            # Also check for class end
            if line.strip() and not line.startswith(' '):
                method_end = i
                break
    
    if method_start >= 0 and method_end > method_start:
        # Replace the method
        lines = lines[:method_start] + [new_method + '\n'] + lines[method_end:]
        
        # Also update cleanup method
        for i, line in enumerate(lines):
            if 'async def cleanup(self)' in line:
                # Find where to add cleanup
                for j in range(i+1, min(i+20, len(lines))):
                    if 'await self.session.close()' in lines[j]:
                        lines.insert(j+1, cleanup_addition)
                        break
                break
        
        # Write back
        with open(bybit_file, 'w') as f:
            f.writelines(lines)
        
        print("✅ Fixed Bybit get_market_tickers method")
        print("   - Removed problematic asyncio.timeout")
        print("   - Using simple aiohttp session")
        print("   - Limited to 50 symbols")
        return True
    else:
        print("❌ Could not find method to replace")
        return False

if __name__ == "__main__":
    fix_bybit_api()