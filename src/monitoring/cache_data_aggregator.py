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

logger = logging.getLogger(__name__)


class CacheDataAggregator:
    """
    Aggregates monitoring data and pushes it directly to cache.

    This service eliminates the circular dependency by allowing the monitoring
    system to populate cache keys directly with generated analysis data.
    """

    def __init__(self, cache_adapter, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the cache data aggregator.

        Args:
            cache_adapter: Direct cache adapter instance
            config: Configuration dictionary
        """
        self.cache_adapter = cache_adapter
        self.config = config or {}

        # Data aggregation storage
        self.signal_buffer = deque(maxlen=100)  # Store recent signals
        self.market_data_buffer = {}  # Store recent market data by symbol
        self.analysis_results_buffer = deque(maxlen=50)  # Store recent analysis results

        # Market movers tracking
        self.price_changes = defaultdict(list)  # Track price changes for movers
        self.volume_changes = defaultdict(list)  # Track volume changes

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

            # Check if signal was generated - LOWERED threshold from 70 to 60 for testing
            confluence_score = analysis_result.get('confluence_score', 0)
            if confluence_score >= 60:  # Signal threshold (was 70)
                await self._add_signal_to_buffer(symbol, analysis_result)
                logger.info(f"Added signal for {symbol} with score {confluence_score:.1f}")

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
            # Try to get market_data, fallback to direct keys
            market_data = analysis_result.get('market_data', analysis_result)

            price = market_data.get('price') or analysis_result.get('price')
            if price:
                current_price = float(price)
                price_change_24h = market_data.get('price_change_24h', 0) or analysis_result.get('price_change_24h', 0)
                volume_24h = market_data.get('volume_24h', 0) or analysis_result.get('volume_24h', 0)
                price_change_percent = market_data.get('price_change_percent_24h', 0) or analysis_result.get('price_change_percent_24h', 0)

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

        except Exception as e:
            logger.error(f"Error tracking price changes for {symbol}: {e}")

    async def _update_cache_keys(self) -> None:
        """Update all critical cache keys with aggregated data."""
        try:
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
        """Generate and cache market overview data."""
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

            overview_data = {
                'total_symbols_monitored': total_symbols,
                'active_signals_1h': active_signals,
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals,
                'avg_confluence_score': round(avg_confluence, 2),
                'max_confluence_score': round(max_confluence, 2),
                'market_regime': market_regime,
                'signal_quality': 'High' if avg_confluence > 65 else 'Medium' if avg_confluence > 55 else 'Low',
                'last_updated': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat(),
                'data_points': len(self.analysis_results_buffer),
                'buffer_size': len(self.signal_buffer)
            }

            # Push to cache
            await self._push_to_cache('market:overview', overview_data, expiry=60)
            logger.debug(f"Updated market:overview cache - {total_symbols} symbols, {active_signals} signals")

        except Exception as e:
            logger.error(f"Error updating market overview cache: {e}")

    async def _update_analysis_signals(self) -> None:
        """Generate and cache analysis signals data."""
        try:
            # Get recent signals (last 2 hours)
            cutoff_time = time.time() - 7200
            recent_signals = [s for s in self.signal_buffer if s['timestamp'] > cutoff_time]

            # Sort by confluence score (highest first)
            recent_signals.sort(key=lambda x: x['confluence_score'], reverse=True)

            # Group by signal type
            signals_by_type = defaultdict(list)
            for signal in recent_signals:
                signals_by_type[signal['signal_type']].append(signal)

            # Calculate signal statistics
            if recent_signals:
                avg_score = statistics.mean([s['confluence_score'] for s in recent_signals])
                avg_reliability = statistics.mean([s['reliability'] for s in recent_signals])
                top_symbols = list(set([s['symbol'] for s in recent_signals[:10]]))
            else:
                avg_score = 0
                avg_reliability = 0
                top_symbols = []

            signals_data = {
                'recent_signals': recent_signals[:20],  # Top 20 signals
                'total_signals': len(recent_signals),
                'buy_signals': len(signals_by_type['BUY']),
                'sell_signals': len(signals_by_type['SELL']),
                'avg_confluence_score': round(avg_score, 2),
                'avg_reliability': round(avg_reliability, 2),
                'top_symbols': top_symbols,
                'signal_distribution': {
                    'BUY': len(signals_by_type['BUY']),
                    'SELL': len(signals_by_type['SELL'])
                },
                'last_updated': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat()
            }

            # Push to cache
            await self._push_to_cache('analysis:signals', signals_data, expiry=120)
            logger.debug(f"Updated analysis:signals cache - {len(recent_signals)} signals")

        except Exception as e:
            logger.error(f"Error updating analysis signals cache: {e}")

    async def _update_market_movers(self) -> None:
        """Generate and cache market movers data."""
        try:
            movers_data = []

            # Process all symbols with price data
            for symbol, price_history in self.price_changes.items():
                if not price_history:
                    continue

                latest_data = price_history[-1]

                mover_entry = {
                    'symbol': symbol,
                    'price': latest_data['price'],
                    'price_change_24h': latest_data['price_change_24h'],
                    'price_change_percent': latest_data['price_change_percent'],
                    'volume_24h': latest_data['volume_24h'],
                    'timestamp': latest_data['timestamp']
                }

                movers_data.append(mover_entry)

            # Sort by absolute price change percentage
            movers_data.sort(key=lambda x: abs(x['price_change_percent']), reverse=True)

            # Get top gainers and losers
            gainers = [m for m in movers_data if m['price_change_percent'] > 0][:10]
            losers = [m for m in movers_data if m['price_change_percent'] < 0][:10]

            # Volume leaders
            volume_leaders = sorted(movers_data, key=lambda x: x['volume_24h'], reverse=True)[:10]

            market_movers = {
                'top_gainers': gainers,
                'top_losers': losers,
                'volume_leaders': volume_leaders,
                'total_symbols': len(movers_data),
                'avg_change_percent': round(statistics.mean([m['price_change_percent'] for m in movers_data]), 2) if movers_data else 0,
                'market_volatility': 'High' if len([m for m in movers_data if abs(m['price_change_percent']) > 5]) > len(movers_data) * 0.3 else 'Medium',
                'last_updated': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat()
            }

            # Push to cache
            await self._push_to_cache('market:movers', market_movers, expiry=90)
            logger.debug(f"Updated market:movers cache - {len(movers_data)} symbols")

        except Exception as e:
            logger.error(f"Error updating market movers cache: {e}")

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