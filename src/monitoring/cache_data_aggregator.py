"""
Cache Data Aggregator - Direct Cache Population Service

This module fixes the circular dependency in the monitoring → cache → dashboard data flow
by providing a service that allows the monitoring system to push data DIRECTLY to cache
without relying on API calls that depend on cached data.

Key Features:
- Direct cache population for critical market data keys
- Market data aggregation and processing
- Signal aggregation and processing
- Market movers calculation
- Independent data generation without API dependencies

Solves the circular dependency: monitoring generates → pushes to cache → dashboard retrieves
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque
import statistics
import math

# Import unified cache writer
from .cache_writer import MonitoringCacheWriter

logger = logging.getLogger(__name__)


class CacheDataAggregator:
    """
    Aggregates monitoring data and pushes it directly to cache.

    This service eliminates the circular dependency by allowing the monitoring
    system to populate cache keys directly with generated analysis data.
    """

    def __init__(self, cache_adapter, config: Optional[Dict[str, Any]] = None, exchange=None):
        """
        Initialize the cache data aggregator.

        Args:
            cache_adapter: Direct cache adapter instance
            config: Configuration dictionary
            exchange: CCXT exchange instance for fetching market-wide data
        """
        self.cache_adapter = cache_adapter
        self.config = config or {}
        self.exchange = exchange

        # Initialize unified cache writer
        self.cache_writer = MonitoringCacheWriter(cache_adapter, config)

        # Data aggregation storage
        self.signal_buffer = deque(maxlen=100)  # Store recent signals
        self.market_data_buffer = {}  # Store recent market data by symbol
        self.analysis_results_buffer = deque(maxlen=50)  # Store recent analysis results

        # Market movers tracking
        self.price_changes = defaultdict(list)  # Track price changes for movers
        self.volume_changes = defaultdict(list)  # Track volume changes

        # Market-wide data (fetched from exchange)
        self.market_wide_tickers = {}  # All perpetual tickers from exchange
        self.last_ticker_fetch = 0  # Last time we fetched market-wide tickers
        self.ticker_fetch_interval = 60  # Fetch tickers every 60 seconds

        # Volatility history for calculating average (rolling 24-hour window)
        self.volatility_history = deque(maxlen=1440)  # 1440 minutes = 24 hours (1 sample/min)

        # BTC price history for realized volatility (rolling 30-day window)
        # Store daily snapshots: {timestamp, price}
        self.btc_price_history = deque(maxlen=30)  # 30 days of daily prices
        self.last_btc_snapshot = 0  # Last time we took a BTC price snapshot

        # Statistics
        self.aggregation_count = 0
        self.last_aggregation_time = 0
        self.cache_push_count = 0
        self.cache_push_errors = 0

    async def add_analysis_result(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """
        Add analysis result and trigger cache updates.

        This is called by the monitoring system after each symbol analysis.
        """
        try:
            # DEBUG: Log first few analysis results to understand structure
            if self.aggregation_count < 3:
                logger.info(f"DEBUG: Analysis result keys for {symbol}: {list(analysis_result.keys())}")
                if 'confluence_score' in analysis_result:
                    logger.info(f"DEBUG: Confluence score for {symbol}: {analysis_result['confluence_score']}")

            # Add to buffer with timestamp
            timestamped_result = {
                **analysis_result,
                'symbol': symbol,
                'timestamp': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat()
            }

            self.analysis_results_buffer.append(timestamped_result)

            # Update market data buffer - extract from market_data structure
            market_data = None
            price = None

            if 'market_data' in analysis_result:
                raw_market_data = analysis_result['market_data']

                # Extract price from ticker (primary source)
                ticker = raw_market_data.get('ticker', {})
                if ticker:
                    price = ticker.get('last') or ticker.get('close') or ticker.get('lastPrice')

                # If no ticker, try ohlcv
                if not price:
                    ohlcv = raw_market_data.get('ohlcv')
                    if ohlcv and isinstance(ohlcv, list) and len(ohlcv) > 0:
                        # OHLCV format: [timestamp, open, high, low, close, volume]
                        price = ohlcv[-1][4] if len(ohlcv[-1]) > 4 else None

                # Build market data dict if we have price
                if price:
                    market_data = {
                        'price': float(price),
                        'price_change_24h': ticker.get('change', 0),
                        'price_change_percent_24h': ticker.get('percentage', 0),
                        'volume_24h': ticker.get('baseVolume', 0) or ticker.get('volume', 0),
                        'high_24h': ticker.get('high', 0),
                        'low_24h': ticker.get('low', 0)
                    }
                elif self.aggregation_count < 3:
                    logger.warning(f"DEBUG: market_data found but no price extracted from ticker/ohlcv for {symbol}")
                    logger.warning(f"DEBUG: ticker keys: {list(ticker.keys()) if ticker else 'No ticker'}")

            elif 'price' in analysis_result:  # Fallback: use direct price data
                market_data = {
                    'price': analysis_result.get('price'),
                    'price_change_24h': analysis_result.get('price_change_24h', 0),
                    'price_change_percent_24h': analysis_result.get('price_change_percent_24h', 0),
                    'volume_24h': analysis_result.get('volume_24h', 0)
                }
            else:
                # DEBUG: Log why market data wasn't extracted
                if self.aggregation_count < 3:
                    logger.warning(f"DEBUG: No market_data or price found for {symbol}. Keys: {list(analysis_result.keys())[:10]}")

            if market_data:
                self.market_data_buffer[symbol] = {
                    **market_data,
                    'last_updated': time.time()
                }
                logger.debug(f"✅ Market data buffered for {symbol}: price={market_data.get('price')}")

            # Track price changes for market movers
            await self._track_price_changes(symbol, analysis_result)

            # Add ALL signals to buffer (dashboard should show all monitored symbols)
            confluence_score = analysis_result.get('confluence_score', 0)
            await self._add_signal_to_buffer(symbol, analysis_result)

            # Log high-quality signals separately
            if confluence_score >= 60:
                logger.info(f"✨ High-quality signal for {symbol} with score {confluence_score:.1f}")
            else:
                logger.debug(f"Added signal for {symbol} with score {confluence_score:.1f}")

            # Update aggregated cache keys
            await self._update_cache_keys()

            self.aggregation_count += 1

        except Exception as e:
            logger.error(f"Error adding analysis result for {symbol}: {e}")

    async def _add_signal_to_buffer(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Add trading signal to buffer."""
        try:
            signal_data = {
                'symbol': symbol,
                'signal_type': analysis_result.get('signal_type', 'BUY'),
                'confluence_score': analysis_result.get('confluence_score', 0),
                'reliability': analysis_result.get('reliability', 0),
                'components': analysis_result.get('components', {}),
                'trade_parameters': analysis_result.get('trade_parameters', {}),
                'timestamp': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat(),
                'signal_id': analysis_result.get('signal_id', ''),
                'transaction_id': analysis_result.get('transaction_id', '')
            }

            self.signal_buffer.append(signal_data)
            logger.info(f"Added signal to buffer: {symbol} {signal_data['signal_type']} (score: {signal_data['confluence_score']:.1f})")

        except Exception as e:
            logger.error(f"Error adding signal to buffer for {symbol}: {e}")

    async def _track_price_changes(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Track price changes for market movers calculation."""
        try:
            # DEBUG: Log function entry
            if len(self.price_changes) < 5:  # Only log first few calls
                logger.info(f"[DEBUG] _track_price_changes called for {symbol}")

            # Try to get market_data, fallback to direct keys
            market_data = analysis_result.get('market_data', analysis_result)

            # DEBUG: Check what keys are available
            if len(self.price_changes) < 5:
                logger.info(f"[DEBUG] {symbol}: market_data type={type(market_data)}")
                if isinstance(market_data, dict):
                    logger.info(f"[DEBUG] {symbol}: market_data keys={list(market_data.keys())[:10]}")
                    if 'ticker' in market_data:
                        logger.info(f"[DEBUG] {symbol}: ticker keys={list(market_data['ticker'].keys())[:10]}")

            price = market_data.get('price') or analysis_result.get('price')

            # CRITICAL FIX: Extract price from ticker if not directly available
            if not price and isinstance(market_data, dict) and 'ticker' in market_data:
                ticker = market_data['ticker']
                price = ticker.get('last') or ticker.get('close') or ticker.get('lastPrice')
                if len(self.price_changes) < 5:
                    logger.info(f"[DEBUG] {symbol}: Extracted price from ticker: {price}")

            if price:
                if len(self.price_changes) < 5:
                    logger.info(f"[DEBUG] {symbol}: Found price: {price}")
                current_price = float(price)
                price_change_24h = market_data.get('price_change_24h', 0) or analysis_result.get('price_change_24h', 0)
                volume_24h = market_data.get('volume_24h', 0) or analysis_result.get('volume_24h', 0)
                price_change_percent = market_data.get('price_change_percent_24h', 0) or analysis_result.get('price_change_percent_24h', 0)

                # CRITICAL FIX: Calculate price change from OHLCV if not provided
                if price_change_percent == 0:
                    if len(self.price_changes) < 5:
                        logger.info(f"[DEBUG] {symbol}: price_change_percent is 0, trying OHLCV calculation")

                    # Try to calculate from OHLCV data (24h ago vs now)
                    if 'market_data' in analysis_result:
                        ohlcv = analysis_result['market_data'].get('ohlcv')
                        if len(self.price_changes) < 5:
                            logger.info(f"[DEBUG] {symbol}: ohlcv type={type(ohlcv)}, is dict={isinstance(ohlcv, dict)}")

                        if ohlcv and isinstance(ohlcv, dict):
                            base_ohlcv = ohlcv.get('base', [])
                            if len(self.price_changes) < 5:
                                logger.info(f"[DEBUG] {symbol}: base_ohlcv length={len(base_ohlcv) if base_ohlcv else 0}")

                            if base_ohlcv and len(base_ohlcv) > 24:  # Need at least 24 candles for 24h change
                                price_24h_ago = base_ohlcv[-24][4]  # Close price 24 candles ago
                                if price_24h_ago > 0:
                                    price_change_percent = ((current_price - price_24h_ago) / price_24h_ago) * 100
                                    logger.info(f"✅ Calculated 24h change for {symbol}: {price_change_percent:.2f}%")
                else:
                    if len(self.price_changes) < 5:
                        logger.info(f"[DEBUG] {symbol}: Already has price_change_percent={price_change_percent}")

                # Store price change data
                price_data = {
                    'price': current_price,
                    'price_change_24h': float(price_change_24h),
                    'price_change_percent': float(price_change_percent),
                    'volume_24h': float(volume_24h),
                    'timestamp': time.time()
                }

                # Keep last 10 data points for each symbol
                if len(self.price_changes[symbol]) >= 10:
                    self.price_changes[symbol].pop(0)

                self.price_changes[symbol].append(price_data)

                if len(self.price_changes) < 5:
                    logger.info(f"[DEBUG] {symbol}: Stored price change data. Buffer now has {len(self.price_changes)} symbols")

        except Exception as e:
            logger.error(f"Error tracking price changes for {symbol}: {e}")

    async def _fetch_market_wide_tickers(self) -> bool:
        """
        Fetch all perpetual futures tickers from exchange for market-wide metrics.

        This provides TRUE market sentiment based on hundreds of perpetual contracts,
        not just the 15 symbols we're actively analyzing.

        Returns:
            bool: True if tickers were successfully fetched and updated
        """
        try:
            # Rate limit: only fetch every 60 seconds
            current_time = time.time()
            if current_time - self.last_ticker_fetch < self.ticker_fetch_interval:
                return False

            if not self.exchange:
                logger.warning("No exchange available for fetching market-wide tickers")
                return False

            # DEBUG: Log exchange info
            exchange_id = getattr(self.exchange, 'exchange_id', getattr(self.exchange, 'id', 'unknown'))
            logger.info(f"Fetching market-wide perpetual tickers from {exchange_id} for true market sentiment...")

            # Check if exchange has fetch_tickers method
            if not hasattr(self.exchange, 'fetch_tickers'):
                logger.error(f"Exchange {exchange_id} does not have fetch_tickers method")
                return False

            # Fetch all linear/perpetual tickers (Bybit specific)
            # For other exchanges, adjust parameters as needed
            # Bybit uses 'category' parameter: linear = perpetual futures
            tickers = await self.exchange.fetch_tickers(category='linear')

            if not tickers:
                logger.warning("No tickers returned from exchange")
                return False

            # Filter for valid tickers with price change data
            # Note: tickers is a list of dicts, not a dict
            valid_tickers = {}
            for ticker in tickers:
                # Only include tickers with valid price change data
                symbol = ticker.get('symbol')
                if symbol and ticker.get('priceChangePercent') is not None and ticker.get('lastPrice') is not None:
                    valid_tickers[symbol] = ticker

            self.market_wide_tickers = valid_tickers
            self.last_ticker_fetch = current_time

            logger.info(f"✅ Fetched {len(valid_tickers)} perpetual tickers for market-wide metrics")
            return True

        except Exception as e:
            logger.error(f"Error fetching market-wide tickers: {e}", exc_info=True)
            return False

    def _calculate_market_wide_metrics(self) -> Dict[str, Any]:
        """
        Calculate market-wide metrics from fetched tickers.

        Returns:
            dict: Market metrics including gainers, losers, volatility, avg_change
        """
        try:
            if not self.market_wide_tickers:
                logger.debug("No market-wide tickers available for metrics calculation")
                return {
                    'gainers': 0,
                    'losers': 0,
                    'volatility': 0.0,
                    'avg_change_percent': 0.0,
                    'total_symbols': 0
                }

            price_changes = []
            gainers = 0
            losers = 0
            neutral = 0

            for symbol, ticker in self.market_wide_tickers.items():
                pct_change = ticker.get('priceChangePercent', 0)

                if pct_change > 0:
                    gainers += 1
                elif pct_change < 0:
                    losers += 1
                else:
                    neutral += 1

                # Collect all price changes for volatility calculation
                if pct_change != 0:
                    price_changes.append(pct_change)

            # Calculate volatility (standard deviation of price changes)
            volatility = 0.0
            if len(price_changes) > 1:
                volatility = abs(statistics.stdev(price_changes))

            # Calculate average price change
            avg_change = 0.0
            if price_changes:
                avg_change = statistics.mean(price_changes)

            total = len(self.market_wide_tickers)

            logger.info(
                f"📊 Market-wide metrics: {gainers} gainers, {losers} losers "
                f"({total} total) | Volatility: {volatility:.2f}% | Avg Change: {avg_change:.2f}%"
            )

            return {
                'gainers': gainers,
                'losers': losers,
                'neutral': neutral,
                'volatility': round(volatility, 2),
                'avg_change_percent': round(avg_change, 2),
                'total_symbols': total
            }

        except Exception as e:
            logger.error(f"Error calculating market-wide metrics: {e}", exc_info=True)
            return {
                'gainers': 0,
                'losers': 0,
                'volatility': 0.0,
                'avg_change_percent': 0.0,
                'total_symbols': 0
            }

    def _calculate_btc_realized_volatility(self) -> Dict[str, float]:
        """
        Calculate BTC realized volatility (annualized).

        This is TRUE crypto volatility - the standard deviation of BTC's
        daily returns over the past 30 days, annualized.

        Returns:
            dict: {
                'btc_volatility': Annualized volatility % (e.g., 52.0),
                'btc_daily_volatility': Daily volatility % (e.g., 2.7),
                'btc_current_price': Current BTC price,
                'days_of_data': Number of days in calculation
            }
        """
        try:
            # Need at least 2 days of data to calculate volatility
            if len(self.btc_price_history) < 2:
                return {
                    'btc_volatility': 0.0,
                    'btc_daily_volatility': 0.0,
                    'btc_current_price': 0.0,
                    'days_of_data': 0
                }

            # Calculate daily log returns
            daily_returns = []
            prices = list(self.btc_price_history)

            for i in range(1, len(prices)):
                prev_price = prices[i-1]['price']
                curr_price = prices[i]['price']

                if prev_price > 0 and curr_price > 0:
                    # Log return: ln(P_t / P_{t-1})
                    log_return = math.log(curr_price / prev_price)
                    daily_returns.append(log_return)

            if len(daily_returns) < 2:
                return {
                    'btc_volatility': 0.0,
                    'btc_daily_volatility': 0.0,
                    'btc_current_price': prices[-1]['price'] if prices else 0.0,
                    'days_of_data': len(prices)
                }

            # Calculate standard deviation of daily returns
            daily_volatility = statistics.stdev(daily_returns)

            # Annualize: σ_annual = σ_daily × sqrt(365)
            annualized_volatility = daily_volatility * math.sqrt(365)

            # Convert to percentage
            daily_volatility_pct = daily_volatility * 100
            annualized_volatility_pct = annualized_volatility * 100

            current_price = prices[-1]['price'] if prices else 0.0

            logger.info(
                f"📊 BTC Realized Volatility: {annualized_volatility_pct:.1f}% annualized "
                f"({daily_volatility_pct:.2f}% daily, {len(daily_returns)} days)"
            )

            return {
                'btc_volatility': round(annualized_volatility_pct, 2),
                'btc_daily_volatility': round(daily_volatility_pct, 2),
                'btc_current_price': current_price,
                'days_of_data': len(daily_returns)
            }

        except Exception as e:
            logger.error(f"Error calculating BTC realized volatility: {e}", exc_info=True)
            return {
                'btc_volatility': 0.0,
                'btc_daily_volatility': 0.0,
                'btc_current_price': 0.0,
                'days_of_data': 0
            }

    async def _track_btc_price(self) -> None:
        """
        Track BTC price once per day for realized volatility calculation.

        Stores daily price snapshots in a rolling 30-day buffer.
        """
        try:
            current_time = time.time()
            time_since_last_snapshot = current_time - self.last_btc_snapshot

            # Only take snapshot once per day (86400 seconds)
            if time_since_last_snapshot < 86400 and self.last_btc_snapshot > 0:
                return

            # Get BTC price from market-wide tickers
            if 'BTCUSDT' in self.market_wide_tickers:
                btc_ticker = self.market_wide_tickers['BTCUSDT']
                btc_price = btc_ticker.get('lastPrice', 0)

                if btc_price > 0:
                    price_snapshot = {
                        'timestamp': current_time,
                        'price': btc_price,
                        'date': datetime.now(timezone.utc).date().isoformat()
                    }

                    self.btc_price_history.append(price_snapshot)
                    self.last_btc_snapshot = current_time

                    logger.info(
                        f"📸 BTC price snapshot: ${btc_price:,.2f} "
                        f"({len(self.btc_price_history)} days of history)"
                    )
            else:
                logger.warning("BTCUSDT not found in market-wide tickers for volatility calculation")

        except Exception as e:
            logger.error(f"Error tracking BTC price: {e}", exc_info=True)

    async def _update_cache_keys(self) -> None:
        """Update all critical cache keys with aggregated data."""
        try:
            # Fetch market-wide tickers for true market sentiment (rate-limited to once per minute)
            await self._fetch_market_wide_tickers()

            # Track BTC price for realized volatility calculation (once per day)
            await self._track_btc_price()

            # Update market:overview
            await self._update_market_overview()

            # Update analysis:signals
            await self._update_analysis_signals()

            # Update market:movers
            await self._update_market_movers()

            self.last_aggregation_time = time.time()

        except Exception as e:
            logger.error(f"Error updating cache keys: {e}")

    async def _update_market_overview(self) -> None:
        """Generate and cache market overview data using unified schema."""
        try:
            # Calculate market statistics from buffered data
            total_symbols = len(self.market_data_buffer)
            active_signals = len([s for s in self.signal_buffer if time.time() - s['timestamp'] < 3600])  # Last hour

            # Calculate average confluence score
            if self.analysis_results_buffer:
                recent_scores = [r.get('confluence_score', 0) for r in list(self.analysis_results_buffer)[-20:]]
                avg_confluence = statistics.mean(recent_scores) if recent_scores else 0
                max_confluence = max(recent_scores) if recent_scores else 0
            else:
                avg_confluence = 0
                max_confluence = 0

            # Calculate market trend
            bullish_signals = len([s for s in self.signal_buffer if s['signal_type'] == 'BUY'])
            bearish_signals = len([s for s in self.signal_buffer if s['signal_type'] == 'SELL'])

            # Generate market regime assessment
            if avg_confluence > 70:
                market_regime = "Strong Trending"
            elif avg_confluence > 60:
                market_regime = "Trending"
            elif avg_confluence > 50:
                market_regime = "Choppy"
            else:
                market_regime = "Ranging"

            # Calculate total volume from buffered market data
            total_volume = sum(
                data.get('volume_24h', 0)
                for data in self.market_data_buffer.values()
            )

            # CRITICAL FIX: Use market-wide metrics from exchange tickers (TRUE market sentiment)
            # This replaces the limited local buffer approach with exchange-wide data
            market_metrics = self._calculate_market_wide_metrics()

            # RENAME: This is market dispersion, not volatility
            market_dispersion = market_metrics['volatility']  # Cross-sectional dispersion of returns
            avg_change_percent = market_metrics['avg_change_percent']
            gainers_count = market_metrics['gainers']
            losers_count = market_metrics['losers']

            # Calculate TRUE BTC realized volatility (annualized)
            btc_vol_data = self._calculate_btc_realized_volatility()
            btc_volatility = btc_vol_data['btc_volatility']  # Annualized %
            btc_daily_vol = btc_vol_data['btc_daily_volatility']
            btc_price = btc_vol_data['btc_current_price']
            btc_vol_days = btc_vol_data['days_of_data']

            # Log market-wide vs monitored comparison
            if market_metrics['total_symbols'] > 0:
                logger.debug(
                    f"Market-wide: {gainers_count}/{losers_count} ({market_metrics['total_symbols']} symbols) | "
                    f"Monitored: {total_symbols} symbols | "
                    f"Dispersion: {market_dispersion}% | Avg Change: {avg_change_percent}%"
                )

            # Track dispersion history for average calculation
            self.volatility_history.append(market_dispersion)

            # Calculate average market dispersion from history
            if len(self.volatility_history) > 0:
                avg_dispersion = statistics.mean(self.volatility_history)
            else:
                avg_dispersion = 8.0  # Fallback default (more realistic than 20%)

            logger.debug(
                f"Market Dispersion: current={market_dispersion:.2f}%, avg={avg_dispersion:.2f}% "
                f"(based on {len(self.volatility_history)} samples)"
            )

            logger.info(
                f"📊 BTC Volatility: {btc_volatility:.1f}% annualized "
                f"({btc_daily_vol:.2f}% daily, {btc_vol_days} days) | "
                f"Market Dispersion: {market_dispersion:.2f}%"
            )

            # Build monitoring format data (old schema format)
            monitoring_data = {
                'total_symbols_monitored': total_symbols,
                'active_signals_1h': active_signals,
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals,
                'avg_confluence_score': round(avg_confluence, 2),
                'max_confluence_score': round(max_confluence, 2),
                'market_state': market_regime,  # Will be mapped to market_regime
                'signal_quality': 'High' if avg_confluence > 65 else 'Medium' if avg_confluence > 55 else 'Low',
                'total_volume': total_volume,

                # RENAMED: Market Dispersion (cross-sectional volatility)
                'market_dispersion': round(market_dispersion, 2),  # Current dispersion of returns
                'avg_market_dispersion': round(avg_dispersion, 2),  # Rolling 24-hour average

                # TRUE Crypto Volatility (BTC realized volatility)
                'btc_volatility': round(btc_volatility, 2),  # Annualized BTC volatility %
                'btc_daily_volatility': round(btc_daily_vol, 2),  # Daily BTC volatility %
                'btc_price': round(btc_price, 2) if btc_price else 0,
                'btc_vol_days': btc_vol_days,  # Days of data used in calculation

                # Keep old field names for backward compatibility (will be deprecated)
                'volatility': round(market_dispersion, 2),  # DEPRECATED: Use market_dispersion
                'avg_volatility': round(avg_dispersion, 2),  # DEPRECATED: Use avg_market_dispersion

                'avg_change_percent': round(avg_change_percent, 2),
                'gainers': gainers_count,
                'losers': losers_count,
                'btc_dom': 59.3,  # TODO: Calculate from BTC dominance
                'last_updated': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat(),
                'data_points': len(self.analysis_results_buffer),
                'buffer_size': len(self.signal_buffer)
            }

            # Use unified cache writer (automatically transforms to unified schema)
            success = await self.cache_writer.write_market_overview(
                monitoring_data,
                ttl=60
            )

            if success:
                logger.debug(
                    f"✅ Updated market:overview with UNIFIED SCHEMA - "
                    f"{total_symbols} symbols, {active_signals} signals"
                )
            else:
                logger.error("Failed to write market overview with unified schema")

        except Exception as e:
            logger.error(f"Error updating market overview cache: {e}", exc_info=True)

    async def _update_analysis_signals(self) -> None:
        """Generate and cache analysis signals data using unified schema."""
        try:
            # Get recent signals (last 2 hours)
            cutoff_time = time.time() - 7200
            recent_signals = [s for s in self.signal_buffer if s['timestamp'] > cutoff_time]

            # Sort by confluence score (highest first)
            recent_signals.sort(key=lambda x: x['confluence_score'], reverse=True)

            # Prepare signals for unified schema (convert to expected format)
            formatted_signals = []
            for signal in recent_signals[:20]:  # Top 20 signals
                # Get market data for the symbol
                market_data = self.market_data_buffer.get(signal['symbol'], {})

                formatted_signal = {
                    'symbol': signal['symbol'],
                    'confluence_score': signal['confluence_score'],
                    'signal_type': signal['signal_type'],
                    'reliability': signal.get('reliability', 75.0),
                    'sentiment': signal['signal_type'],  # BUY/SELL maps to sentiment
                    'components': signal.get('components', {}),
                    'price': market_data.get('price', 0.0),
                    'change_24h': market_data.get('price_change_percent_24h', 0.0),
                    'volume_24h': market_data.get('volume_24h', 0.0),
                    'high_24h': market_data.get('high_24h', 0.0),
                    'low_24h': market_data.get('low_24h', 0.0),
                    'timestamp': signal['timestamp'],
                    'datetime': signal['datetime']
                }
                formatted_signals.append(formatted_signal)

            # Use unified cache writer
            success = await self.cache_writer.write_signals(
                formatted_signals,
                ttl=120
            )

            if success:
                logger.debug(
                    f"✅ Updated analysis:signals with UNIFIED SCHEMA - "
                    f"{len(formatted_signals)} signals"
                )
            else:
                logger.error("Failed to write signals with unified schema")

        except Exception as e:
            logger.error(f"Error updating analysis signals cache: {e}", exc_info=True)

    async def _update_market_movers(self) -> None:
        """Generate and cache market movers data using EXCHANGE-WIDE ticker data."""
        try:
            movers_data = []

            # CRITICAL: Use market-wide tickers (585 symbols) instead of just monitored symbols (15)
            if self.market_wide_tickers:
                # Process all exchange-wide tickers
                for symbol, ticker in self.market_wide_tickers.items():
                    try:
                        price_change_pct = ticker.get('priceChangePercent', 0)

                        mover_entry = {
                            'symbol': symbol,
                            'display_symbol': symbol,  # For frontend display
                            'price': ticker.get('lastPrice', 0),
                            'change': price_change_pct,  # Frontend expects 'change'
                            'change_24h': price_change_pct,
                            'price_change_percent': price_change_pct,
                            'percentage': price_change_pct,
                            'volume': ticker.get('quoteVolume', 0),
                            'volume_24h': ticker.get('quoteVolume', 0),
                            'timestamp': time.time()
                        }

                        movers_data.append(mover_entry)
                    except Exception as e:
                        logger.debug(f"Error processing ticker for {symbol}: {e}")
                        continue

                logger.info(f"📊 Processing {len(movers_data)} tickers for top movers")
            else:
                # Fallback to monitored symbols if exchange-wide data not available
                logger.warning("⚠️ No market-wide tickers available, using monitored symbols")
                for symbol, price_history in self.price_changes.items():
                    if not price_history:
                        continue

                    latest_data = price_history[-1]

                    mover_entry = {
                        'symbol': symbol,
                        'display_symbol': symbol,
                        'price': latest_data['price'],
                        'change': latest_data['price_change_percent'],
                        'price_change_24h': latest_data['price_change_24h'],
                        'price_change_percent': latest_data['price_change_percent'],
                        'volume_24h': latest_data['volume_24h'],
                        'timestamp': latest_data['timestamp']
                    }

                    movers_data.append(mover_entry)

            # Sort by absolute price change percentage
            movers_data.sort(key=lambda x: abs(x.get('price_change_percent', 0)), reverse=True)

            # Get top gainers and losers
            gainers = [m for m in movers_data if m['price_change_percent'] > 0][:10]
            losers = [m for m in movers_data if m['price_change_percent'] < 0][:10]

            # Volume leaders
            volume_leaders = sorted(movers_data, key=lambda x: x.get('volume_24h', 0), reverse=True)[:10]

            # Use unified cache writer
            success = await self.cache_writer.write_market_movers(
                gainers=gainers,
                losers=losers,
                volume_leaders=volume_leaders,
                ttl=90
            )

            if success:
                logger.info(
                    f"✅ Updated market:movers with EXCHANGE-WIDE DATA - "
                    f"{len(gainers)} gainers, {len(losers)} losers from {len(movers_data)} total symbols"
                )
                if gainers:
                    top_gainer = gainers[0]
                    logger.info(f"   Top Gainer: {top_gainer['symbol']} +{top_gainer['price_change_percent']:.2f}%")
                if losers:
                    top_loser = losers[0]
                    logger.info(f"   Top Loser: {top_loser['symbol']} {top_loser['price_change_percent']:.2f}%")
            else:
                logger.error("Failed to write market movers with unified schema")

        except Exception as e:
            logger.error(f"Error updating market movers cache: {e}", exc_info=True)

    async def _push_to_cache(self, key: str, data: Dict[str, Any], expiry: int = 300) -> bool:
        """Push data directly to cache."""
        try:
            # Convert to JSON string
            json_data = json.dumps(data, default=str)

            # Use the multi-tier cache system (DirectCacheAdapter uses 'ttl' parameter)
            await self.cache_adapter.set(key, json_data, ttl=expiry)

            self.cache_push_count += 1
            logger.debug(f"Successfully pushed {key} to cache ({len(json_data)} bytes)")
            return True

        except Exception as e:
            self.cache_push_errors += 1
            logger.error(f"Failed to push {key} to cache: {e}")
            return False

    async def force_cache_update(self) -> Dict[str, bool]:
        """Force update of all cache keys (for testing/debugging)."""
        results = {}

        try:
            # Force market overview update
            await self._update_market_overview()
            results['market:overview'] = True
        except Exception as e:
            logger.error(f"Failed to force update market:overview: {e}")
            results['market:overview'] = False

        try:
            # Force signals update
            await self._update_analysis_signals()
            results['analysis:signals'] = True
        except Exception as e:
            logger.error(f"Failed to force update analysis:signals: {e}")
            results['analysis:signals'] = False

        try:
            # Force movers update
            await self._update_market_movers()
            results['market:movers'] = True
        except Exception as e:
            logger.error(f"Failed to force update market:movers: {e}")
            results['market:movers'] = False

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            'aggregation_count': self.aggregation_count,
            'cache_push_count': self.cache_push_count,
            'cache_push_errors': self.cache_push_errors,
            'last_aggregation_time': self.last_aggregation_time,
            'signal_buffer_size': len(self.signal_buffer),
            'market_data_symbols': len(self.market_data_buffer),
            'analysis_results_count': len(self.analysis_results_buffer),
            'price_tracking_symbols': len(self.price_changes)
        }