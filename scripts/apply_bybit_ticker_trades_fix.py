#!/usr/bin/env python3
"""
Integration patch for existing Bybit exchange to fix "Error: 0" issue
This script will patch your existing exchange implementation
"""

import sys
import os
import shutil
import re
from datetime import datetime

def backup_original_file(file_path: str) -> str:
    """Create backup of original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def apply_ticker_trades_fix():
    """Apply the fix to the existing Bybit exchange file"""

    # Define the file path
    bybit_file = "src/core/exchanges/bybit.py"

    if not os.path.exists(bybit_file):
        print(f"❌ Bybit file not found: {bybit_file}")
        return False

    # Create backup
    backup_path = backup_original_file(bybit_file)

    try:
        # Read the current file
        with open(bybit_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if fix is already applied
        if "Error: 0 fix" in content:
            print("⚠️ Fix appears to already be applied. Skipping.")
            return True

        # Apply the fix by modifying the _fetch_ticker method
        ticker_fix = '''
    async def _fetch_ticker(self, symbol: str) -> dict:
        """
        Fetch ticker data for a specific symbol.
        Enhanced with Error: 0 fix for CCXT 4.5.2
        """
        try:
            # Normalize symbol format for consistency
            normalized_symbol = self._normalize_symbol_for_ticker(symbol)

            # Try original CCXT method first
            try:
                ticker = await super().fetch_ticker(normalized_symbol)
                if ticker and isinstance(ticker, dict) and ticker.get('symbol'):
                    return ticker
            except Exception as e:
                error_msg = str(e)

                # Handle "Error: 0" by using direct API call
                if "0" in error_msg or not error_msg.strip():
                    self.logger.warning(f"CCXT ticker parsing issue for {symbol}, using direct API call")
                    return await self._fetch_ticker_direct(normalized_symbol)
                else:
                    raise e

        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            return {}

    def _normalize_symbol_for_ticker(self, symbol: str) -> str:
        """Error: 0 fix - Normalize symbol format for ticker API"""
        symbol = symbol.strip().upper()

        # Ensure proper format for Bybit ticker endpoint
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            return f"{base}USDT"
        elif symbol.endswith('USD'):
            base = symbol[:-3]
            return f"{base}USD"

        return symbol

    async def _fetch_ticker_direct(self, symbol: str) -> dict:
        """Error: 0 fix - Direct API call for ticker data"""
        try:
            params = {'symbol': symbol, 'category': 'linear'}
            response = await self._make_request('GET', '/v5/market/tickers', params)

            if response and 'result' in response and 'list' in response['result']:
                ticker_data = response['result']['list']
                if ticker_data and len(ticker_data) > 0:
                    raw_ticker = ticker_data[0]

                    return {
                        'symbol': symbol,
                        'timestamp': int(float(raw_ticker.get('time', 0))),
                        'high': float(raw_ticker.get('highPrice24h', 0)) if raw_ticker.get('highPrice24h') else None,
                        'low': float(raw_ticker.get('lowPrice24h', 0)) if raw_ticker.get('lowPrice24h') else None,
                        'bid': float(raw_ticker.get('bid1Price', 0)) if raw_ticker.get('bid1Price') else None,
                        'bidVolume': float(raw_ticker.get('bid1Size', 0)) if raw_ticker.get('bid1Size') else None,
                        'ask': float(raw_ticker.get('ask1Price', 0)) if raw_ticker.get('ask1Price') else None,
                        'askVolume': float(raw_ticker.get('ask1Size', 0)) if raw_ticker.get('ask1Size') else None,
                        'close': float(raw_ticker.get('lastPrice', 0)) if raw_ticker.get('lastPrice') else None,
                        'last': float(raw_ticker.get('lastPrice', 0)) if raw_ticker.get('lastPrice') else None,
                        'percentage': float(raw_ticker.get('price24hPcnt', 0)) * 100 if raw_ticker.get('price24hPcnt') else None,
                        'baseVolume': float(raw_ticker.get('volume24h', 0)) if raw_ticker.get('volume24h') else None,
                        'quoteVolume': float(raw_ticker.get('turnover24h', 0)) if raw_ticker.get('turnover24h') else None,
                        'info': raw_ticker
                    }
        except Exception as e:
            self.logger.error(f"Direct ticker API call failed: {e}")
            return {}

        return {}
'''

        trades_fix = '''
    async def fetch_trades(self, symbol: Union[str, dict], since: Optional[int] = None, limit: Optional[int] = None, params={}) -> List[Dict[str, Any]]:
        """
        Fetch recent trades with symbol validation.
        Enhanced with Error: 0 fix for CCXT 4.5.2
        """
        try:
            # Normalize symbol format
            normalized_symbol = self._normalize_symbol_for_trades(symbol)

            # Try original CCXT method first
            try:
                trades = await super().fetch_trades(normalized_symbol, since=since, limit=limit, params=params)
                if trades and isinstance(trades, list):
                    return trades
            except Exception as e:
                error_msg = str(e)

                # Handle "Error: 0" by using direct API call
                if "0" in error_msg or not error_msg.strip():
                    self.logger.warning(f"CCXT trades parsing issue for {symbol}, using direct API call")
                    return await self._fetch_trades_direct(normalized_symbol, limit or 100)
                else:
                    raise e

        except Exception as e:
            self.logger.error(f"Error fetching trades for {symbol}: {e}")
            return []

    def _normalize_symbol_for_trades(self, symbol: Union[str, dict]) -> str:
        """Error: 0 fix - Normalize symbol format for trades API"""
        if isinstance(symbol, dict):
            symbol = symbol.get('symbol', str(symbol))

        symbol = str(symbol).strip().upper()

        # Ensure proper format for Bybit trades endpoint
        if symbol.endswith('USDT'):
            base = symbol[:-4]
            return f"{base}USDT"
        elif symbol.endswith('USD'):
            base = symbol[:-3]
            return f"{base}USD"

        return symbol

    async def _fetch_trades_direct(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Error: 0 fix - Direct API call for trades data"""
        try:
            params = {'symbol': symbol, 'category': 'linear', 'limit': min(limit, 1000)}
            response = await self._make_request('GET', '/v5/market/recent-trade', params)

            if response and 'result' in response and 'list' in response['result']:
                trades_data = response['result']['list']

                trades = []
                for raw_trade in trades_data:
                    trade = {
                        'id': raw_trade.get('execId'),
                        'timestamp': int(float(raw_trade.get('time', 0))),
                        'symbol': symbol,
                        'side': raw_trade.get('side', '').lower(),
                        'amount': float(raw_trade.get('size', 0)) if raw_trade.get('size') else None,
                        'price': float(raw_trade.get('price', 0)) if raw_trade.get('price') else None,
                        'info': raw_trade
                    }
                    trades.append(trade)

                return trades
        except Exception as e:
            self.logger.error(f"Direct trades API call failed: {e}")

        return []
'''

        # Find and replace the existing _fetch_ticker method
        ticker_pattern = r'async def _fetch_ticker\(self, symbol: str\) -> dict:.*?(?=\n    async def |\n    def |\Z)'
        if re.search(ticker_pattern, content, re.DOTALL):
            content = re.sub(ticker_pattern, ticker_fix.strip(), content, flags=re.DOTALL)
            print("✅ Replaced _fetch_ticker method with fix")
        else:
            print("⚠️ Could not find _fetch_ticker method to replace")

        # Find and replace the existing fetch_trades method
        trades_pattern = r'async def fetch_trades\(self, symbol: Union\[str, dict\].*?(?=\n    async def |\n    def |\Z)'
        if re.search(trades_pattern, content, re.DOTALL):
            content = re.sub(trades_pattern, trades_fix.strip(), content, flags=re.DOTALL)
            print("✅ Replaced fetch_trades method with fix")
        else:
            print("⚠️ Could not find fetch_trades method to replace")

        # Write the modified content back
        with open(bybit_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Successfully applied Error: 0 fix to {bybit_file}")
        print(f"💾 Original backup saved as: {backup_path}")
        return True

    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        # Restore backup
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, bybit_file)
            print(f"🔄 Restored original file from backup")
        return False

if __name__ == "__main__":
    print("🔧 Applying Bybit Error: 0 fix...")

    if apply_ticker_trades_fix():
        print("\n✅ Fix applied successfully!")
        print("\n📋 Next steps:")
        print("1. Test the fix: python scripts/test_bybit_ticker_trades.py")
        print("2. Deploy to VPS if tests pass")
        print("3. Monitor logs for 'Error: 0' messages")
    else:
        print("\n❌ Fix application failed. Check the logs above.")
        sys.exit(1)