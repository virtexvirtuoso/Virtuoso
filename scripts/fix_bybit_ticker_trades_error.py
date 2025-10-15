#!/usr/bin/env python3
"""
Fix for CCXT Bybit "Error: 0" issue with ticker and trades fetches
Addresses symbol format and response parsing issues in CCXT 4.5.2
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BybitTickerTradesFix:
    """Fix for Bybit ticker and trades 'Error: 0' issue"""

    def __init__(self, exchange_instance):
        self.exchange = exchange_instance

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for Bybit API consistency
        Bybit expects specific format for ticker/trades vs OHLCV
        """
        # Remove any extra characters that might cause issues
        symbol = symbol.strip().upper()

        # Handle common Bybit symbol formats
        if symbol.endswith('USDT'):
            # Ensure it's in the correct format
            base = symbol[:-4]  # Remove USDT
            symbol = f"{base}USDT"
        elif symbol.endswith('USD'):
            base = symbol[:-3]  # Remove USD
            symbol = f"{base}USD"

        return symbol

    async def fetch_ticker_safe(self, symbol: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Safe ticker fetch with proper error handling and retries
        """
        normalized_symbol = self.normalize_symbol(symbol)

        for attempt in range(max_retries):
            try:
                # Method 1: Try with original CCXT method
                ticker = await self.exchange.fetch_ticker(normalized_symbol)
                if ticker and isinstance(ticker, dict) and ticker.get('symbol'):
                    logger.info(f"✅ Ticker fetch successful for {normalized_symbol} (attempt {attempt + 1})")
                    return ticker

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Ticker fetch attempt {attempt + 1} failed for {normalized_symbol}: {error_msg}")

                # If it's the "Error: 0" issue, try alternative approach
                if "0" in error_msg or not error_msg.strip():
                    try:
                        # Method 2: Direct API call
                        ticker = await self._fetch_ticker_direct(normalized_symbol)
                        if ticker:
                            logger.info(f"✅ Direct ticker fetch successful for {normalized_symbol}")
                            return ticker
                    except Exception as e2:
                        logger.warning(f"⚠️ Direct ticker fetch also failed: {str(e2)}")

                # Wait before retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))

        logger.error(f"❌ All ticker fetch attempts failed for {normalized_symbol}")
        return None

    async def fetch_trades_safe(self, symbol: str, limit: int = 100, max_retries: int = 3) -> Optional[List[Dict[str, Any]]]:
        """
        Safe trades fetch with proper error handling and retries
        """
        normalized_symbol = self.normalize_symbol(symbol)

        for attempt in range(max_retries):
            try:
                # Method 1: Try with original CCXT method
                trades = await self.exchange.fetch_trades(normalized_symbol, limit=limit)
                if trades and isinstance(trades, list) and len(trades) > 0:
                    logger.info(f"✅ Trades fetch successful for {normalized_symbol} (attempt {attempt + 1})")
                    return trades

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Trades fetch attempt {attempt + 1} failed for {normalized_symbol}: {error_msg}")

                # If it's the "Error: 0" issue, try alternative approach
                if "0" in error_msg or not error_msg.strip():
                    try:
                        # Method 2: Direct API call
                        trades = await self._fetch_trades_direct(normalized_symbol, limit)
                        if trades:
                            logger.info(f"✅ Direct trades fetch successful for {normalized_symbol}")
                            return trades
                    except Exception as e2:
                        logger.warning(f"⚠️ Direct trades fetch also failed: {str(e2)}")

                # Wait before retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))

        logger.error(f"❌ All trades fetch attempts failed for {normalized_symbol}")
        return None

    async def _fetch_ticker_direct(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Direct API call for ticker data bypassing CCXT parsing issues
        """
        try:
            # Use Bybit's v5 API directly
            params = {'symbol': symbol, 'category': 'linear'}

            # Make direct API call
            response = await self.exchange._make_request('GET', '/v5/market/tickers', params)

            if response and 'result' in response and 'list' in response['result']:
                ticker_data = response['result']['list']
                if ticker_data and len(ticker_data) > 0:
                    raw_ticker = ticker_data[0]

                    # Convert to CCXT format
                    ticker = {
                        'symbol': symbol,
                        'timestamp': int(float(raw_ticker.get('time', 0))),
                        'datetime': None,
                        'high': float(raw_ticker.get('highPrice24h', 0)) if raw_ticker.get('highPrice24h') else None,
                        'low': float(raw_ticker.get('lowPrice24h', 0)) if raw_ticker.get('lowPrice24h') else None,
                        'bid': float(raw_ticker.get('bid1Price', 0)) if raw_ticker.get('bid1Price') else None,
                        'bidVolume': float(raw_ticker.get('bid1Size', 0)) if raw_ticker.get('bid1Size') else None,
                        'ask': float(raw_ticker.get('ask1Price', 0)) if raw_ticker.get('ask1Price') else None,
                        'askVolume': float(raw_ticker.get('ask1Size', 0)) if raw_ticker.get('ask1Size') else None,
                        'vwap': None,
                        'open': None,
                        'close': float(raw_ticker.get('lastPrice', 0)) if raw_ticker.get('lastPrice') else None,
                        'last': float(raw_ticker.get('lastPrice', 0)) if raw_ticker.get('lastPrice') else None,
                        'previousClose': None,
                        'change': None,
                        'percentage': float(raw_ticker.get('price24hPcnt', 0)) * 100 if raw_ticker.get('price24hPcnt') else None,
                        'average': None,
                        'baseVolume': float(raw_ticker.get('volume24h', 0)) if raw_ticker.get('volume24h') else None,
                        'quoteVolume': float(raw_ticker.get('turnover24h', 0)) if raw_ticker.get('turnover24h') else None,
                        'info': raw_ticker
                    }
                    return ticker

        except Exception as e:
            logger.error(f"Direct ticker API call failed: {str(e)}")

        return None

    async def _fetch_trades_direct(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Direct API call for trades data bypassing CCXT parsing issues
        """
        try:
            # Use Bybit's v5 API directly
            params = {'symbol': symbol, 'category': 'linear', 'limit': min(limit, 1000)}

            # Make direct API call
            response = await self.exchange._make_request('GET', '/v5/market/recent-trade', params)

            if response and 'result' in response and 'list' in response['result']:
                trades_data = response['result']['list']

                trades = []
                for raw_trade in trades_data:
                    trade = {
                        'id': raw_trade.get('execId'),
                        'timestamp': int(float(raw_trade.get('time', 0))),
                        'datetime': None,
                        'symbol': symbol,
                        'order': None,
                        'type': None,
                        'side': raw_trade.get('side', '').lower(),
                        'amount': float(raw_trade.get('size', 0)) if raw_trade.get('size') else None,
                        'price': float(raw_trade.get('price', 0)) if raw_trade.get('price') else None,
                        'cost': None,
                        'fee': None,
                        'fees': [],
                        'info': raw_trade
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            logger.error(f"Direct trades API call failed: {str(e)}")

        return None

async def test_fix():
    """Test the fix with problematic symbols"""
    import ccxt.async_support as ccxt

    # Initialize exchange (you'll need to adapt this to your setup)
    exchange = ccxt.bybit({
        'apiKey': 'your_api_key',  # Replace with your key
        'secret': 'your_secret',   # Replace with your secret
        'sandbox': False,
        'enableRateLimit': True,
    })

    # Initialize fix
    fix = BybitTickerTradesFix(exchange)

    # Test symbols that were causing "Error: 0"
    test_symbols = ['10000SATSUSDT', '1000BONKUSDT', 'BTCUSDT', 'ETHUSDT']

    for symbol in test_symbols:
        print(f"\n🔍 Testing {symbol}:")

        # Test ticker
        ticker = await fix.fetch_ticker_safe(symbol)
        if ticker:
            print(f"  ✅ Ticker: {ticker.get('last', 'N/A')} (bid: {ticker.get('bid', 'N/A')}, ask: {ticker.get('ask', 'N/A')})")
        else:
            print(f"  ❌ Ticker fetch failed")

        # Test trades
        trades = await fix.fetch_trades_safe(symbol, limit=5)
        if trades:
            print(f"  ✅ Trades: {len(trades)} trades fetched, latest: {trades[0].get('price', 'N/A')} @ {trades[0].get('amount', 'N/A')}")
        else:
            print(f"  ❌ Trades fetch failed")

    await exchange.close()

if __name__ == "__main__":
    print("🚀 Testing Bybit Ticker/Trades Fix...")
    asyncio.run(test_fix())