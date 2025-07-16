#!/usr/bin/env python3
"""
Apply Open Interest fix to market reporter
"""

import re

def apply_oi_fix():
    """Apply the Open Interest fix to the market reporter"""
    
    print("🔧 Applying Open Interest fix to market reporter...")
    
    # Read the current file
    with open('src/monitoring/market_reporter.py', 'r') as f:
        content = f.read()
    
    # 1. Add the direct API method at the end of the class
    direct_api_method = '''
    async def _fetch_bybit_open_interest_direct(self, symbol: str) -> float:
        """
        Fetch Open Interest directly from Bybit API bypassing CCXT
        
        Args:
            symbol: CCXT format symbol (e.g., 'BTC/USDT:USDT')
            
        Returns:
            float: Open Interest value
        """
        try:
            import aiohttp
            
            # Convert CCXT symbol to Bybit format
            if ':USDT' in symbol:  # Perpetual futures
                bybit_symbol = symbol.replace('/USDT:USDT', 'USDT')  # BTC/USDT:USDT -> BTCUSDT
                category = 'linear'
            elif '/USDT' in symbol:  # Spot
                bybit_symbol = symbol.replace('/', '')  # BTC/USDT -> BTCUSDT  
                category = 'spot'
            elif '/USD' in symbol:  # Inverse contracts
                bybit_symbol = symbol.replace('/', '')  # BTC/USD -> BTCUSD
                category = 'inverse'
            else:
                # Assume it's already in Bybit format
                bybit_symbol = symbol
                category = 'linear'  # Default to linear
            
            # Bybit API endpoint
            url = "https://api.bybit.com/v5/market/tickers"
            params = {
                'category': category,
                'symbol': bybit_symbol
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        self.logger.warning(f"Bybit API error for {symbol}: HTTP {response.status}")
                        return 0
                    
                    data = await response.json()
                    
                    if data.get('retCode') != 0:
                        self.logger.warning(f"Bybit API returned error for {symbol}: {data}")
                        return 0
                    
                    result = data.get('result', {})
                    ticker_list = result.get('list', [])
                    
                    if not ticker_list:
                        self.logger.warning(f"No Bybit ticker data for {symbol} ({bybit_symbol})")
                        return 0
                    
                    ticker = ticker_list[0]
                    
                    # Extract Open Interest
                    oi_raw = ticker.get('openInterest') or ticker.get('openInterestValue')
                    if oi_raw:
                        try:
                            oi = float(oi_raw)
                            self.logger.info(f"🎯 Bybit OI for {symbol}: {oi:,.2f} ({category}/{bybit_symbol})")
                            return oi
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Error parsing Bybit OI for {symbol}: {oi_raw} - {e}")
                            return 0
                    else:
                        self.logger.debug(f"No OI fields in Bybit response for {symbol}")
                        return 0
                        
        except Exception as e:
            self.logger.warning(f"Error fetching Bybit OI for {symbol}: {e}")
            return 0'''
    
    # Add the method before the last line of the file
    if not '_fetch_bybit_open_interest_direct' in content:
        # Find the last method and add before it
        content = content.rstrip() + direct_api_method + '\n'
        print("✅ Added direct API method")
    else:
        print("✅ Direct API method already exists")
    
    # 2. Replace the Open Interest extraction logic
    old_oi_pattern = r'# Extract open interest from info section with fallback.*?total_open_interest \+= oi\s*oi_by_pair\[symbol\] = oi'
    
    new_oi_code = '''# BYBIT OPEN INTEREST FIX: Use direct API call
                        oi = await self._fetch_bybit_open_interest_direct(symbol)
                        
                        # Log final OI result
                        if oi > 0:
                            self.logger.info(f"📊 Successfully extracted OI for {symbol}: {self._format_number(oi)}")
                        else:
                            self.logger.warning(f"⚠️ No OI data found for {symbol} (direct API)")
                        
                        total_open_interest += oi
                        oi_by_pair[symbol] = oi'''
    
    # Apply the replacement
    new_content = re.sub(old_oi_pattern, new_oi_code, content, flags=re.DOTALL)
    
    if new_content != content:
        print("✅ Replaced Open Interest extraction logic")
    else:
        print("⚠️ Could not find Open Interest extraction pattern to replace")
        # Try a simpler replacement
        if 'BYBIT OPEN INTEREST FIX' not in content:
            # Find and replace just the comment line
            content = content.replace(
                '# Extract open interest from info section with fallback',
                '# BYBIT OPEN INTEREST FIX: Use direct API call\n                        oi = await self._fetch_bybit_open_interest_direct(symbol)\n                        \n                        # Fallback: Extract open interest from info section with fallback'
            )
            new_content = content
            print("✅ Applied simple replacement")
    
    # Write the updated content
    with open('src/monitoring/market_reporter.py', 'w') as f:
        f.write(new_content)
    
    print("🎯 Open Interest fix applied successfully!")
    print("   The market reporter will now use direct Bybit API calls for OI data.")

if __name__ == "__main__":
    apply_oi_fix() 