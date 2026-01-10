"""
Data collection module for the monitoring system.

This module is responsible for fetching market data from exchanges, including
OHLCV candles, orderbooks, trades, tickers, and other market information.
It provides efficient batch fetching and handles exchange-specific quirks.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd

from .base import MonitoringComponent, DataProvider
from .utils.decorators import handle_monitoring_error, retry_on_error, measure_performance
from .utils.timestamp import TimestampUtility
from .utils.converters import ccxt_time_to_minutes


class DataCollector(MonitoringComponent, DataProvider):
    """Handles all data collection from exchanges.

    This class is responsible for fetching market data from various exchanges,
    including OHLCV data, orderbooks, trades, and tickers. It manages concurrent
    fetching for multiple symbols and handles exchange-specific requirements.

    IMPORTANT: This class can optionally share cache with MarketDataManager to
    prevent data gaps on first-pass symbols. When market_data_manager is provided,
    it will check MDM's pre-warmed cache before making fresh API calls.
    """

    def __init__(
        self,
        exchange_manager,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        market_data_manager=None
    ):
        """Initialize the data collector.

        Args:
            exchange_manager: Exchange manager instance for accessing exchanges
            config: Configuration dictionary
            logger: Optional logger instance
            market_data_manager: Optional MarketDataManager for shared cache access
        """
        super().__init__(logger)

        self.exchange_manager = exchange_manager
        self.config = config or {}
        self.market_data_manager = market_data_manager  # Share cache with MDM
        
        # Configuration for data fetching
        # Handle complex timeframe config or fallback to simple strings
        raw_timeframes = self.config.get('timeframes', {
            'ltf': '5m',   # Low timeframe
            'mtf': '30m',  # Medium timeframe
            'htf': '4h'    # High timeframe
        })
        
        # Extract interval strings from complex config if needed
        self.timeframes = {}
        for tf_name, tf_config in raw_timeframes.items():
            if isinstance(tf_config, dict) and 'interval' in tf_config:
                # Convert interval minutes to timeframe string
                interval_minutes = tf_config['interval']
                if interval_minutes == 1:
                    self.timeframes[tf_name] = '1m'
                elif interval_minutes == 5:
                    self.timeframes[tf_name] = '5m'
                elif interval_minutes == 30:
                    self.timeframes[tf_name] = '30m'
                elif interval_minutes == 240:
                    self.timeframes[tf_name] = '4h'
                elif interval_minutes == 60:
                    self.timeframes[tf_name] = '1h'
                elif interval_minutes == 15:
                    self.timeframes[tf_name] = '15m'
                else:
                    self.timeframes[tf_name] = f'{interval_minutes}m'
            elif isinstance(tf_config, str):
                # Already a string, use as-is
                self.timeframes[tf_name] = tf_config
            else:
                # Fallback to default
                default_map = {'ltf': '5m', 'mtf': '30m', 'htf': '4h', 'base': '1m'}
                self.timeframes[tf_name] = default_map.get(tf_name, '1m')
        
        # Limits for data fetching
        self.ohlcv_limit = self.config.get('ohlcv_limit', 100)
        self.orderbook_limit = self.config.get('orderbook_limit', 20)
        self.trades_limit = self.config.get('trades_limit', 100)
        
        # Concurrency settings
        self.max_concurrent_fetches = self.config.get('max_concurrent_fetches', 10)
        self.fetch_timeout = self.config.get('fetch_timeout', 30.0)
        
        # Cache for recent data (simple in-memory cache)
        self._data_cache = {}
        self._cache_ttl = self.config.get('cache_ttl', 5)  # seconds
        self._max_cache_size = self.config.get('max_cache_size', 50)  # max entries to prevent memory leaks
        
        # Metrics
        self._fetch_stats = {
            'total_fetches': 0,
            'successful_fetches': 0,
            'failed_fetches': 0,
            'cache_hits': 0,
            'average_fetch_time': 0
        }
    
    async def _perform_initialization(self) -> None:
        """Perform component-specific initialization."""
        # Ensure exchange manager is initialized
        if not self.exchange_manager:
            raise ValueError("Exchange manager is required for DataCollector")
        
        self.logger.info("DataCollector initialized with timeframes: %s", self.timeframes)
    
    @measure_performance()
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch complete market data for a symbol.

        This is the main entry point for fetching all market data for a symbol.
        It aggregates OHLCV, orderbook, trades, and ticker data.

        CACHE HIERARCHY (P1 Pipeline Fix):
        1. Check MarketDataManager's pre-warmed cache first (if available)
        2. Fall back to local cache
        3. Make fresh API calls only if both caches miss

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary containing all market data for the symbol
        """
        self._fetch_stats['total_fetches'] += 1

        # P1 FIX: Check MarketDataManager's pre-warmed cache FIRST
        # This prevents data gaps on first-pass symbols (top movers)
        if self.market_data_manager is not None:
            mdm_cache = getattr(self.market_data_manager, 'data_cache', {})
            if symbol in mdm_cache and mdm_cache[symbol]:
                mdm_data = mdm_cache[symbol]
                # Verify cache has essential data (ticker at minimum)
                if mdm_data.get('ticker'):
                    self._fetch_stats['cache_hits'] += 1
                    self.logger.debug(f"Using MDM pre-warmed cache for {symbol}, has premium_index: {'premium_index' in mdm_data}")
                    # Format for consistency with our output
                    return {
                        'symbol': symbol,
                        'timestamp': TimestampUtility.get_utc_timestamp(),
                        'exchange': 'bybit',
                        'ohlcv': mdm_data.get('ohlcv', mdm_data.get('kline', {})),
                        'orderbook': mdm_data.get('orderbook'),
                        'trades': mdm_data.get('trades', []),
                        'ticker': mdm_data.get('ticker'),
                        'long_short_ratio': mdm_data.get('long_short_ratio'),
                        'risk_limit': mdm_data.get('risk_limits'),
                        'open_interest': mdm_data.get('open_interest'),
                        'liquidations': mdm_data.get('liquidations', []),
                        # Phase 1 Predictive Confluence data (2025-12)
                        'premium_index': mdm_data.get('premium_index'),
                        'taker_volume_ratio': mdm_data.get('taker_volume_ratio'),
                    }

        # Check local cache second
        cache_key = f"{symbol}_market_data"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            self._fetch_stats['cache_hits'] += 1
            return cached_data
        
        try:
            # Get exchange instance
            exchange = await self.exchange_manager.get_primary_exchange()
            if not exchange:
                self.logger.error("No exchange available for data fetching")
                self._fetch_stats['failed_fetches'] += 1
                return {}
            
            # Fetch data concurrently
            tasks = [
                self._fetch_ohlcv_all_timeframes(exchange, symbol),
                self._fetch_orderbook(exchange, symbol),
                self._fetch_trades(exchange, symbol),
                self._fetch_ticker(exchange, symbol),
                self._fetch_long_short_ratio(exchange, symbol),  # Add LSR fetching
                self._fetch_risk_limits(exchange, symbol),  # Add risk limits fetching
                self._fetch_premium_index(exchange, symbol),  # Phase 1: premium index
                self._fetch_taker_volume_ratio(exchange, symbol),  # Phase 1: taker volume ratio
                self._fetch_open_interest(exchange, symbol)  # Phase 1: open interest for oi_coiling
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            market_data = {
                'symbol': symbol,
                'timestamp': TimestampUtility.get_utc_timestamp(),
                'exchange': exchange.exchange_id
            }
            
            # Add OHLCV data
            if not isinstance(results[0], Exception):
                market_data['ohlcv'] = results[0]
            else:
                self.logger.error(f"Error fetching OHLCV for {symbol}: {results[0]}")
                market_data['ohlcv'] = {}
            
            # Add orderbook
            if not isinstance(results[1], Exception):
                market_data['orderbook'] = results[1]
            else:
                self.logger.error(f"Error fetching orderbook for {symbol}: {results[1]}")
                market_data['orderbook'] = None
            
            # Add trades
            if not isinstance(results[2], Exception):
                market_data['trades'] = results[2]
            else:
                self.logger.error(f"Error fetching trades for {symbol}: {results[2]}")
                market_data['trades'] = []
            
            # Add ticker
            if not isinstance(results[3], Exception):
                market_data['ticker'] = results[3]
            else:
                self.logger.error(f"Error fetching ticker for {symbol}: {results[3]}")
                market_data['ticker'] = None
            
            # Add long/short ratio
            if len(results) > 4 and not isinstance(results[4], Exception):
                market_data['long_short_ratio'] = results[4]
                self.logger.info(f"LSR data fetched for {symbol}: {results[4]}")
            else:
                if len(results) > 4:
                    self.logger.error(f"Error fetching LSR for {symbol}: {results[4]}")
                market_data['long_short_ratio'] = None
            
            # Add risk limits
            if len(results) > 5 and not isinstance(results[5], Exception):
                market_data['risk_limit'] = results[5]
            else:
                if len(results) > 5:
                    self.logger.error(f"Error fetching risk limits for {symbol}: {results[5]}")
                market_data['risk_limit'] = None
            
            
            # Add premium_index (Phase 1 Predictive Confluence)
            if len(results) > 6 and not isinstance(results[6], Exception):
                market_data["premium_index"] = results[6]
            else:
                market_data["premium_index"] = None
            
            # Add taker_volume_ratio (Phase 1 Predictive Confluence)
            if len(results) > 7 and not isinstance(results[7], Exception):
                market_data["taker_volume_ratio"] = results[7]
            else:
                market_data["taker_volume_ratio"] = None
            
            # Add open_interest (Phase 1 Predictive Confluence - oi_coiling)
            if len(results) > 8 and not isinstance(results[8], Exception):
                market_data["open_interest"] = results[8]
                self.logger.debug(f"OI data added for {symbol}: current={results[8].get('current', 0):.2f}")
            else:
                market_data["open_interest"] = None
            # Cache the data
            self._cache_data(cache_key, market_data)
            
            self._fetch_stats['successful_fetches'] += 1
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            self._fetch_stats['failed_fetches'] += 1
            return {'symbol': symbol, 'error': str(e)}
    
    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch market data for multiple symbols concurrently.
        
        Args:
            symbols: List of trading pair symbols
            
        Returns:
            Dictionary mapping symbols to their market data
        """
        self.logger.info(f"Fetching batch data for {len(symbols)} symbols")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_fetches)
        
        async def fetch_with_semaphore(symbol: str) -> Tuple[str, Dict[str, Any]]:
            """Fetch data with semaphore control."""
            async with semaphore:
                data = await self.fetch_market_data(symbol)
                return symbol, data
        
        # Fetch all symbols concurrently
        tasks = [fetch_with_semaphore(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results into dictionary
        batch_data = {}
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error in batch fetch: {result}")
            else:
                symbol, data = result
                batch_data[symbol] = data
        
        self.logger.info(f"Batch fetch completed: {len(batch_data)}/{len(symbols)} successful")
        return batch_data
    
    @retry_on_error(max_attempts=3, delay=1.0)
    async def _fetch_ohlcv_all_timeframes(
        self,
        exchange,
        symbol: str
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for all configured timeframes.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Dictionary mapping timeframe names to DataFrames
        """
        ohlcv_data = {}
        
        for tf_name, timeframe in self.timeframes.items():
            try:
                candles = await exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    limit=self.ohlcv_limit
                )
                
                if candles:
                    df = self._process_ohlcv_data(candles)
                    ohlcv_data[tf_name] = df
                    self.logger.debug(f"Fetched {len(candles)} candles for {symbol} {timeframe}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching {timeframe} OHLCV for {symbol}: {str(e)}")
                ohlcv_data[tf_name] = pd.DataFrame()
        
        return ohlcv_data
    
    def _process_ohlcv_data(self, candles: List[List]) -> pd.DataFrame:
        """Process raw OHLCV data into DataFrame.
        
        Args:
            candles: Raw OHLCV data from exchange
            
        Returns:
            Processed DataFrame with OHLCV columns
        """
        if not candles:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(
            candles,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Set timestamp as index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Sort by timestamp
        df.sort_index(inplace=True)
        
        return df
    
    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_orderbook(self, exchange, symbol: str) -> Dict[str, Any]:
        """Fetch orderbook data.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Orderbook dictionary with bids and asks
        """
        try:
            orderbook = await exchange.fetch_order_book(symbol, self.orderbook_limit)
            
            # Add timestamp if not present
            if 'timestamp' not in orderbook:
                orderbook['timestamp'] = TimestampUtility.get_utc_timestamp()
            
            return orderbook
            
        except Exception as e:
            self.logger.error(f"Error fetching orderbook for {symbol}: {str(e)}")
            return {'bids': [], 'asks': [], 'timestamp': TimestampUtility.get_utc_timestamp()}
    
    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_trades(self, exchange, symbol: str) -> List[Dict[str, Any]]:
        """Fetch recent trades.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            List of recent trades
        """
        try:
            trades = await exchange.fetch_trades(symbol, limit=self.trades_limit)
            return trades if trades else []
            
        except Exception as e:
            self.logger.error(f"Error fetching trades for {symbol}: {str(e)}")
            return []
    
    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_ticker(self, exchange, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Ticker dictionary
        """
        try:
            ticker = await exchange.fetch_ticker(symbol)
            
            # Add timestamp if not present
            if ticker and 'timestamp' not in ticker:
                ticker['timestamp'] = TimestampUtility.get_utc_timestamp()
            
            return ticker
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            return None
    
    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_long_short_ratio(self, exchange, symbol: str) -> Dict[str, Any]:
        """Fetch long/short ratio data.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Long/short ratio dictionary
        """
        try:
            # Check if exchange has the method
            if hasattr(exchange, 'fetch_long_short_ratio'):
                lsr = await exchange.fetch_long_short_ratio(symbol)
                self.logger.info(f"Successfully fetched LSR for {symbol}: {lsr}")
                return lsr
            else:
                self.logger.warning(f"Exchange does not support LSR fetching")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching LSR for {symbol}: {str(e)}")
            return None
    
    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_risk_limits(self, exchange, symbol: str) -> Dict[str, Any]:
        """Fetch risk limits data.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Risk limits dictionary
        """
        try:
            # Check if exchange has the method
            if hasattr(exchange, 'fetch_risk_limits'):
                risk_limits = await exchange.fetch_risk_limits(symbol)
                return risk_limits
            else:
                self.logger.debug(f"Exchange does not support risk limits fetching")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching risk limits for {symbol}: {str(e)}")
            return None
    
    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if still fresh.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if fresh, None otherwise
        """
        if key in self._data_cache:
            cached_item = self._data_cache[key]
            age = TimestampUtility.get_age_seconds(cached_item['timestamp'])
            
            if age <= self._cache_ttl:
                return cached_item['data']
        
        return None
    
    def _cache_data(self, key: str, data: Dict[str, Any]) -> None:
        """Cache data with timestamp.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        # Clean stale entries proactively to prevent memory leaks
        current_time = TimestampUtility.get_utc_timestamp()
        max_age_ms = self._cache_ttl * 1000
        
        # Remove expired entries before adding new ones
        keys_to_remove = []
        for existing_key, item in self._data_cache.items():
            if current_time - item['timestamp'] > max_age_ms:
                keys_to_remove.append(existing_key)
        
        for remove_key in keys_to_remove:
            del self._data_cache[remove_key]
        
        # Add new cache entry
        self._data_cache[key] = {
            'data': data,
            'timestamp': current_time
        }
        
        # Enforce maximum cache size to prevent memory leaks
        if len(self._data_cache) > self._max_cache_size:
            # Remove oldest entries if cache is full
            cache_items = list(self._data_cache.items())
            cache_items.sort(key=lambda x: x[1]['timestamp'])  # Sort by timestamp
            
            # Keep only the newest entries
            entries_to_keep = cache_items[-self._max_cache_size:]
            self._data_cache = dict(entries_to_keep)
            
            removed_count = len(cache_items) - len(entries_to_keep)
            if removed_count > 0:
                self.logger.debug(f"Removed {removed_count} old cache entries to prevent memory leak")
    
    def _clean_cache(self) -> None:
        """Remove stale entries from cache."""
        current_time = TimestampUtility.get_utc_timestamp()
        max_age_ms = self._cache_ttl * 1000
        
        keys_to_remove = []
        for key, item in self._data_cache.items():
            if current_time - item['timestamp'] > max_age_ms:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._data_cache[key]
        
        if keys_to_remove:
            self.logger.debug(f"Cleaned {len(keys_to_remove)} stale cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get data collector statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            **self._fetch_stats,
            'cache_size': len(self._data_cache),
            'configured_timeframes': list(self.timeframes.values()),
            'is_running': self.is_running
        }
    
    async def clear_cache(self) -> None:
        """Clear all cached data."""
        self._data_cache.clear()
        self.logger.info("Data cache cleared")
    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_premium_index(self, exchange, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch premium index kline data for basis score calculation.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Premium index data dict with 'signal' key containing z_score
        """
        try:
            if hasattr(exchange, 'fetch_premium_index_kline'):
                premium_data = await exchange.fetch_premium_index_kline(symbol)
                if premium_data:
                    self.logger.debug(f"Successfully fetched premium_index for {symbol}")
                    return premium_data
            else:
                self.logger.debug(f"Exchange does not support premium index fetching")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching premium_index for {symbol}: {str(e)}")
            return None

    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_taker_volume_ratio(self, exchange, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch taker buy/sell volume ratio.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Taker volume ratio data dict
        """
        try:
            if hasattr(exchange, 'calculate_taker_buy_sell_ratio'):
                ratio_data = await exchange.calculate_taker_buy_sell_ratio(symbol)
                if ratio_data:
                    self.logger.debug(f"Successfully fetched taker_volume_ratio for {symbol}")
                    return ratio_data
            else:
                self.logger.debug(f"Exchange does not support taker volume ratio")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching taker_volume_ratio for {symbol}: {str(e)}")
            return None

    @retry_on_error(max_attempts=2, delay=0.5)
    async def _fetch_open_interest(self, exchange, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch open interest with history for current + previous values.
        
        Uses fetch_open_interest_history with limit=2 to get both current and 
        previous OI values, enabling proper delta calculation for oi_coiling.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            
        Returns:
            Dict with 'current', 'previous', and 'history' keys, or None on error
        """
        try:
            if hasattr(exchange, 'fetch_open_interest_history'):
                # Fetch last 2 OI readings for delta calculation
                oi_response = await exchange.fetch_open_interest_history(
                    symbol, 
                    interval='5min', 
                    limit=2
                )
                
                history = oi_response.get('history', [])
                
                if len(history) >= 2:
                    # History is sorted newest first
                    current_oi = history[0].get('value', 0)
                    previous_oi = history[1].get('value', 0)
                    
                    self.logger.debug(
                        f"OI for {symbol}: current={current_oi:.2f}, "
                        f"previous={previous_oi:.2f}, delta={((current_oi/previous_oi)-1)*100:.2f}%"
                    )
                    
                    return {
                        'current': current_oi,
                        'previous': previous_oi,
                        'history': history,
                        'timestamp': history[0].get('timestamp', 0)
                    }
                elif len(history) == 1:
                    # Only have current, estimate previous as same (no change)
                    current_oi = history[0].get('value', 0)
                    self.logger.debug(f"Only 1 OI reading for {symbol}, using as both current/previous")
                    return {
                        'current': current_oi,
                        'previous': current_oi,
                        'history': history,
                        'timestamp': history[0].get('timestamp', 0)
                    }
                else:
                    self.logger.warning(f"No OI history returned for {symbol}")
                    return None
            else:
                self.logger.debug(f"Exchange does not support fetch_open_interest_history")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching open_interest for {symbol}: {str(e)}")
            return None
