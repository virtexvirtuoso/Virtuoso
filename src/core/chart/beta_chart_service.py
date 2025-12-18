"""
Beta Chart Service
Calculates rebased cryptocurrency returns for the Bitcoin Beta dashboard.

This service fetches market data from Bybit and computes percentage returns
where all symbols start at 0% for visual comparison.
"""
import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import aiohttp

logger = logging.getLogger(__name__)

# Meme coin symbol mapping - Bybit uses numeric prefixes for low-priced tokens
BYBIT_SYMBOL_MAP = {
    'PEPE': '1000PEPEUSDT',
    'SHIB': '1000SHIBUSDT',
    'FLOKI': '1000FLOKIUSDT',
    'BONK': '1000BONKUSDT',
    'LUNC': '1000LUNCUSDT',
    'SATS': '1000SATSUSDT',
    'RATS': '1000RATSUSDT',
    'BTT': '1000000BTTUSDT',
    'BABYDOGE': '1000000BABYDOGEUSDT',
}

# Supported timeframes and their configurations
# Keys are hours (floats for sub-hour: 0.25=15min, 0.5=30min)
TIMEFRAME_CONFIG = {
    0.25: {'interval': '5', 'limit': 3},   # 15min = 3 x 5-minute candles
    0.5:  {'interval': '5', 'limit': 6},   # 30min = 6 x 5-minute candles
    1:  {'interval': '1', 'limit': 60},    # 1h = 60 x 1-minute candles
    4:  {'interval': '1', 'limit': 240},   # 4h = 240 x 1-minute candles
    8:  {'interval': '60', 'limit': 8},    # 8h = 8 x 1-hour candles
    12: {'interval': '60', 'limit': 12},   # 12h = 12 x 1-hour candles
    24: {'interval': '60', 'limit': 24},   # 24h = 24 x 1-hour candles
}

# Cache configuration
BETA_CHART_CACHE_TTL = 120  # 2 minutes


def normalize_symbol(symbol: str) -> str:
    """Convert Bybit symbol to normalized base asset name."""
    base = symbol.replace('USDT', '')
    if base.startswith('1000000'):
        return base[7:]
    if base.startswith('1000'):
        return base[4:]
    return base


class BetaChartService:
    """
    Service for generating beta chart data (rebased returns).

    Usage:
        service = BetaChartService()
        data = await service.generate_chart_data(timeframe_hours=4)
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.BetaChartService")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch_klines(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """Fetch kline data from Bybit for a single symbol."""
        url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"

        try:
            session = await self._get_session()
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0 and 'result' in data:
                        candles = []
                        for c in data['result']['list']:
                            candles.append({
                                'timestamp': int(c[0]),
                                'open': float(c[1]),
                                'high': float(c[2]),
                                'low': float(c[3]),
                                'close': float(c[4]),
                                'volume': float(c[5])
                            })
                        # Bybit returns newest first, reverse for chronological order
                        return list(reversed(candles))
        except Exception as e:
            self.logger.debug(f"Error fetching klines for {symbol}: {e}")
        return []

    async def generate_chart_data(self, timeframe_hours: float = 4) -> Dict[str, Any]:
        """
        Generate rebased returns chart data for top 25 symbols.

        Args:
            timeframe_hours: Hours of historical data (0.25=15min, 0.5=30min, 1, 4, 8, 12, 24)

        Returns:
            Dict with chart_data, overview, performance metrics, and metadata
        """
        start_time = time.time()

        # Validate and get timeframe config
        if timeframe_hours not in TIMEFRAME_CONFIG:
            timeframe_hours = 4
        config = TIMEFRAME_CONFIG[timeframe_hours]
        interval = config['interval']
        limit = config['limit']

        self.logger.info(f"Generating beta chart data for {timeframe_hours}h timeframe...")

        try:
            session = await self._get_session()

            # Step 1: Fetch all tickers
            tickers_url = "https://api.bybit.com/v5/market/tickers?category=linear"
            async with session.get(tickers_url, timeout=10) as response:
                if response.status != 200:
                    raise Exception("Failed to fetch Bybit tickers")

                data = await response.json()
                if data.get('retCode') != 0:
                    raise Exception(f"Bybit API error: {data.get('retMsg')}")

                tickers = data['result']['list']

            # Step 2: Filter and sort USDT perpetuals by volume
            usdt_tickers = []
            for t in tickers:
                symbol = t['symbol']
                if symbol.endswith('USDT') and 'PERP' not in symbol:
                    try:
                        turnover = float(t.get('turnover24h', 0))
                        price = float(t.get('lastPrice', 0))
                        change_24h = float(t.get('price24hPcnt', 0)) * 100

                        usdt_tickers.append({
                            'symbol': symbol,
                            'normalized': normalize_symbol(symbol),
                            'price': price,
                            'turnover_24h': turnover,
                            'change_24h': change_24h
                        })
                    except (ValueError, KeyError):
                        continue

            # Sort by turnover (volume)
            usdt_tickers.sort(key=lambda x: x['turnover_24h'], reverse=True)

            # Step 3: Select top 25 symbols (always include BTC first)
            top_symbols = []
            btc_added = False

            for t in usdt_tickers:
                if t['normalized'] == 'BTC':
                    if not btc_added:
                        top_symbols.insert(0, t)
                        btc_added = True
                elif len(top_symbols) < 25:
                    top_symbols.append(t)

                if len(top_symbols) >= 25:
                    break

            # Step 4: Fetch historical klines for each symbol
            historical_data = {}

            for ticker in top_symbols:
                symbol = ticker['symbol']
                normalized = ticker['normalized']

                # Check if we need to map to a different symbol (meme coins)
                fetch_symbol = BYBIT_SYMBOL_MAP.get(normalized, symbol)

                candles = await self._fetch_klines(fetch_symbol, interval, limit)

                if candles:
                    historical_data[normalized] = candles

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.05)

            # Step 5: Calculate rebased returns (all start at 0%)
            chart_data = {}
            performance_summary = []

            for symbol, candles in historical_data.items():
                if len(candles) < 2:
                    continue

                initial_price = candles[0]['close']
                if initial_price == 0:
                    continue

                rebased = []
                for c in candles:
                    pct_change = ((c['close'] - initial_price) / initial_price) * 100
                    rebased.append({
                        'timestamp': c['timestamp'],
                        'value': round(pct_change, 4)
                    })

                chart_data[symbol] = rebased

                # Final performance for sorting
                final_change = rebased[-1]['value'] if rebased else 0
                performance_summary.append({
                    'symbol': symbol,
                    'change': round(final_change, 2)
                })

            # Sort by performance for legend ordering
            performance_summary.sort(key=lambda x: x['change'], reverse=True)

            # Calculate overview stats
            btc_change = chart_data.get('BTC', [{}])[-1].get('value', 0) if 'BTC' in chart_data else 0
            outperformers = len([p for p in performance_summary if p['change'] > 1.0])
            underperformers = len([p for p in performance_summary if p['change'] < -3.0])

            generation_time = round(time.time() - start_time, 2)
            self.logger.info(f"Beta chart data generated in {generation_time}s ({len(chart_data)} symbols)")

            return {
                'chart_data': chart_data,
                'performance_order': [p['symbol'] for p in performance_summary],
                'performance_summary': performance_summary,
                'overview': {
                    'btc_change': round(btc_change, 2),
                    'symbols_count': len(chart_data),
                    'outperformers': outperformers,
                    'underperformers': underperformers,
                    'timeframe_hours': timeframe_hours
                },
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'generation_time_seconds': generation_time,
                'cache_ttl_seconds': BETA_CHART_CACHE_TTL
            }

        except Exception as e:
            self.logger.error(f"Error generating beta chart data: {e}")
            raise


# Singleton instance for use across the application
_beta_chart_service: Optional[BetaChartService] = None


def get_beta_chart_service() -> BetaChartService:
    """Get the singleton BetaChartService instance."""
    global _beta_chart_service
    if _beta_chart_service is None:
        _beta_chart_service = BetaChartService()
    return _beta_chart_service


async def generate_beta_chart_data(timeframe_hours: float = 4) -> Dict[str, Any]:
    """
    Convenience function to generate beta chart data.

    Args:
        timeframe_hours: Hours of data (0.25=15min, 0.5=30min, 1, 4, 8, 12, 24)

    Returns:
        Dict with chart data and metadata
    """
    service = get_beta_chart_service()
    return await service.generate_chart_data(timeframe_hours)
