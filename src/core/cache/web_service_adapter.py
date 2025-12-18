#!/usr/bin/env python3
"""
Web Service Cache Adapter
=========================

CRITICAL WEB SERVICE INTEGRATION: Replaces hardcoded fallback data with shared cache reads
to enable real-time live market data display in web service endpoints.

This adapter ensures that web service endpoints retrieve live market data from the shared
cache populated by the trading service, eliminating the 0% cache hit rate issue.

Key Features:
- Shared cache integration for live data access
- Fallback mechanisms for cache miss scenarios
- Performance optimization for web endpoints
- Real-time data synchronization with trading service
- Comprehensive error handling and logging

Integration Points:
- Market overview endpoints
- Dashboard data endpoints
- Signal and analysis endpoints
- Mobile API endpoints
"""

from __future__ import annotations

import asyncio
import logging
import time
import aiohttp
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

# Import shared cache bridge
from .shared_cache_bridge import (
    get_shared_cache_bridge,
    get_market_data,
    DataSource,
    initialize_shared_cache
)

logger = logging.getLogger(__name__)


# =============================================================================
# CoinGecko BTC Dominance Cache (module-level for sharing across instances)
# =============================================================================
_coingecko_cache = {
    'btc_dominance': 57.0,
    'last_updated': 0,
    'ttl': 300  # 5 minutes
}


async def fetch_real_btc_dominance() -> float:
    """
    Fetch real BTC dominance from CoinGecko API.
    Uses caching to avoid rate limits.
    """
    global _coingecko_cache

    current_time = time.time()

    # Return cached if valid
    if current_time - _coingecko_cache['last_updated'] < _coingecko_cache['ttl']:
        return _coingecko_cache['btc_dominance']

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/global',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    btc_dom = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0)
                    if btc_dom > 0:
                        _coingecko_cache['btc_dominance'] = round(btc_dom, 2)
                        _coingecko_cache['last_updated'] = current_time
                        logger.info(f"✅ CoinGecko BTC Dominance updated: {btc_dom:.2f}%")
                        return _coingecko_cache['btc_dominance']
    except Exception as e:
        logger.debug(f"CoinGecko API error: {e}")

    return _coingecko_cache['btc_dominance']

class WebServiceCacheAdapter:
    """
    Web Service Cache Adapter

    Provides optimized cache access for web service endpoints with automatic
    fallback to shared cache when local cache misses occur.
    """

    def __init__(self):
        self.bridge = get_shared_cache_bridge()
        self.fallback_data_cache = {}
        self.access_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cross_service_hits': 0,
            'fallback_uses': 0,
            'last_live_data_time': 0
        }

    async def initialize(self):
        """Initialize web service cache adapter"""
        try:
            # Initialize shared cache bridge
            success = await initialize_shared_cache()
            if not success:
                logger.warning("Shared cache bridge initialization failed - using fallback mode")

            logger.info("✅ Web Service Cache Adapter initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize web service cache adapter: {e}")
            return False

    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Get market overview with live data from trading service

        CRITICAL: This replaces hardcoded data with live market data
        """
        self.access_metrics['total_requests'] += 1

        try:
            # Try to get live data from shared cache
            data, is_cross_service = await get_market_data('market:overview')

            if data and isinstance(data, dict):
                self._record_successful_access(is_cross_service)

                # Enhance with additional calculated fields
                enhanced_data = self._enhance_market_overview(data)

                logger.debug(f"Market overview retrieved: {len(enhanced_data)} fields (live data: {is_cross_service})")
                return enhanced_data

            # Try alternative cache keys
            data, is_cross_service = await get_market_data('virtuoso:market_overview')
            if data and isinstance(data, dict):
                self._record_successful_access(is_cross_service)
                enhanced_data = self._enhance_market_overview(data)
                logger.debug(f"Market overview from alt key: {len(enhanced_data)} fields")
                return enhanced_data

        except Exception as e:
            logger.error(f"Error retrieving market overview from shared cache: {e}")

        # Fallback to realistic default data
        self._record_fallback_use()
        return self._get_fallback_market_overview()

    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard overview with live data

        CRITICAL: Main dashboard endpoint integration
        """
        self.access_metrics['total_requests'] += 1

        try:
            # Try to get complete dashboard data first
            dashboard_data, is_cross_service = await get_market_data('virtuoso:dashboard_data')

            if dashboard_data and isinstance(dashboard_data, dict):
                self._record_successful_access(is_cross_service)
                logger.debug("Dashboard overview from complete dataset")
                return dashboard_data

            # Build dashboard from individual components
            overview_data = await self._get_live_market_overview()
            signals_data = await self._get_live_signals()
            movers_data = await self._get_live_market_movers()
            regime_data = await self._get_live_market_regime()

            # Construct comprehensive dashboard
            dashboard = {
                'summary': {
                    'total_symbols': overview_data.get('total_symbols', 0),
                    'total_volume': overview_data.get('total_volume', 0),
                    'total_volume_24h': overview_data.get('total_volume_24h', 0),
                    'average_change': overview_data.get('average_change', 0),
                    'timestamp': int(time.time())
                },
                'market_regime': regime_data,
                'signals': signals_data.get('signals', [])[:10],  # Top 10
                'top_gainers': movers_data.get('gainers', [])[:5],
                'top_losers': movers_data.get('losers', [])[:5],
                'momentum': {
                    'gainers': len([m for m in movers_data.get('gainers', []) if m.get('change_24h', 0) > 0]),
                    'losers': len([m for m in movers_data.get('losers', []) if m.get('change_24h', 0) < 0])
                },
                'volatility': {
                    'value': overview_data.get('volatility', 0),
                    'level': 'high' if overview_data.get('volatility', 0) > 5 else 'normal'
                },
                'source': 'shared_cache_bridge',
                'data_source': 'live' if any([overview_data, signals_data.get('signals'), movers_data.get('gainers')]) else 'fallback',
                'timestamp': int(time.time())
            }

            has_live_data = any([
                overview_data.get('total_symbols', 0) > 0,
                len(signals_data.get('signals', [])) > 0,
                len(movers_data.get('gainers', [])) > 0
            ])

            if has_live_data:
                self._record_successful_access(True)
            else:
                self._record_fallback_use()

            logger.debug(f"Dashboard overview constructed: {dashboard['data_source']} data")
            return dashboard

        except Exception as e:
            logger.error(f"Error constructing dashboard overview: {e}")
            self._record_fallback_use()
            return self._get_fallback_dashboard_overview()

    async def get_signals(self) -> Dict[str, Any]:
        """
        Get trading signals from shared cache

        CRITICAL: Ensures web endpoints show live trading signals
        """
        self.access_metrics['total_requests'] += 1

        try:
            data, is_cross_service = await get_market_data('analysis:signals')

            if data and isinstance(data, dict) and data.get('signals'):
                self._record_successful_access(is_cross_service)

                result = {
                    'signals': data['signals'],
                    'count': len(data['signals']),
                    'timestamp': data.get('timestamp', int(time.time())),
                    'source': 'shared_cache',
                    'data_source': 'live'
                }

                logger.debug(f"Retrieved {len(data['signals'])} live signals")
                return result

        except Exception as e:
            logger.error(f"Error retrieving signals from shared cache: {e}")

        # Fallback
        self._record_fallback_use()
        return {
            'signals': [],
            'count': 0,
            'timestamp': int(time.time()),
            'source': 'fallback',
            'data_source': 'fallback'
        }

    async def get_dashboard_symbols(self) -> Dict[str, Any]:
        """Get symbol data with live market information"""
        self.access_metrics['total_requests'] += 1

        try:
            # Get live ticker data
            tickers, is_cross_service_tickers = await get_market_data('market:tickers')
            signals, is_cross_service_signals = await get_market_data('analysis:signals')

            if tickers and isinstance(tickers, dict):
                # Process tickers with signals
                symbols = []
                signal_map = {}

                if signals and isinstance(signals, dict):
                    signal_map = {s.get('symbol'): s for s in signals.get('signals', [])}

                for symbol, ticker in list(tickers.items())[:50]:  # Top 50
                    symbol_data = {
                        'symbol': symbol,
                        'price': ticker.get('price', 0),
                        'change_24h': ticker.get('change_24h', 0),
                        'volume': ticker.get('volume', 0),
                        'volume_24h': ticker.get('volume_24h', ticker.get('volume', 0))
                    }

                    # Add signal data if available
                    if symbol in signal_map:
                        signal = signal_map[symbol]
                        symbol_data['signal_score'] = signal.get('score', signal.get('confluence_score', 50))
                        symbol_data['components'] = signal.get('components', {})

                    symbols.append(symbol_data)

                # Sort by volume
                symbols.sort(key=lambda x: x.get('volume', 0), reverse=True)

                is_cross_service = is_cross_service_tickers or is_cross_service_signals
                self._record_successful_access(is_cross_service)

                return {
                    'symbols': symbols,
                    'count': len(symbols),
                    'timestamp': int(time.time()),
                    'source': 'shared_cache',
                    'data_source': 'live'
                }

        except Exception as e:
            logger.error(f"Error retrieving dashboard symbols: {e}")

        # Fallback
        self._record_fallback_use()
        return {
            'symbols': [],
            'count': 0,
            'timestamp': int(time.time()),
            'source': 'fallback',
            'data_source': 'fallback'
        }

    async def get_market_movers(self) -> Dict[str, Any]:
        """Get market movers from shared cache"""
        self.access_metrics['total_requests'] += 1

        try:
            data, is_cross_service = await get_market_data('market:movers')

            if data and isinstance(data, dict):
                self._record_successful_access(is_cross_service)

                return {
                    'gainers': data.get('gainers', []),
                    'losers': data.get('losers', []),
                    'timestamp': data.get('timestamp', int(time.time())),
                    'source': 'shared_cache',
                    'data_source': 'live'
                }

        except Exception as e:
            logger.error(f"Error retrieving market movers: {e}")

        # Fallback
        self._record_fallback_use()
        return {
            'gainers': [],
            'losers': [],
            'timestamp': int(time.time()),
            'source': 'fallback',
            'data_source': 'fallback'
        }

    async def get_mobile_data(self) -> Dict[str, Any]:
        """
        Get mobile dashboard data with live confluence scores

        CRITICAL: Mobile API integration with live data
        """
        self.access_metrics['total_requests'] += 1

        try:
            # Fetch real BTC dominance from CoinGecko (updates cache for fallback values)
            await fetch_real_btc_dominance()

            # Get all required data components
            overview_data = await self._get_live_market_overview()
            signals_data = await self._get_live_signals()
            movers_data = await self._get_live_market_movers()
            regime_data = await self._get_live_market_regime()
            tickers_data, _ = await get_market_data('market:tickers')

            # CRITICAL FIX: Check if overview_data contains valid (non-cache-warmer) data
            # Cache warmer data has all zeros/empty values and should NOT be used
            is_cache_warmer_data = (
                overview_data.get('trend_strength', 0) == 0 and
                overview_data.get('gainers', 0) == 0 and
                overview_data.get('losers', 0) == 0 and
                overview_data.get('total_volume_24h', 0) == 0
            )

            if is_cache_warmer_data:
                logger.warning("⚠️ Detected cache warmer data in overview - attempting fallback to market-overview endpoint")
                # Try the market-overview endpoint which often has real data
                fallback_overview, _ = await get_market_data('market:overview')
                if fallback_overview and isinstance(fallback_overview, dict):
                    # Check if fallback has valid data
                    fallback_has_data = (
                        fallback_overview.get('trend_strength', 0) > 0 or
                        fallback_overview.get('gainers', 0) > 0 or
                        fallback_overview.get('losers', 0) > 0
                    )
                    if fallback_has_data:
                        logger.info("✅ Using fallback market-overview data instead of cache warmer")
                        overview_data = fallback_overview

            # Process confluence scores with live data
            confluence_scores = []
            signal_list = signals_data.get('signals', [])

            for signal in signal_list[:15]:  # Top 15 for mobile
                symbol = signal.get('symbol', '')

                # Try to get detailed breakdown
                breakdown_data, _ = await get_market_data(f'confluence:breakdown:{symbol}')

                # Get ticker data for this symbol
                ticker = {}
                if tickers_data and isinstance(tickers_data, dict):
                    ticker = tickers_data.get(symbol, {})

                if breakdown_data and isinstance(breakdown_data, dict):
                    # Use detailed breakdown data
                    confluence_scores.append({
                        "symbol": symbol,
                        "score": round(breakdown_data.get('overall_score', signal.get('score', 50)), 2),
                        "sentiment": breakdown_data.get('sentiment', 'NEUTRAL'),
                        "reliability": breakdown_data.get('reliability', 75),
                        "price": signal.get('price', ticker.get('price', 0)),
                        "change_24h": round(signal.get('change_24h', ticker.get('change_24h', 0)), 2),
                        "volume_24h": signal.get('volume_24h', ticker.get('volume_24h', 0)),
                        "high_24h": signal.get('high_24h', ticker.get('high', 0)),
                        "low_24h": signal.get('low_24h', ticker.get('low', 0)),
                        "components": breakdown_data.get('components', signal.get('components', {})),
                        "sub_components": breakdown_data.get('sub_components', {}),
                        "interpretations": breakdown_data.get('interpretations', {}),
                        "has_breakdown": True,
                        "score_history": breakdown_data.get('score_history', [])
                    })
                else:
                    # Use signal data with ticker enhancement
                    confluence_scores.append({
                        "symbol": symbol,
                        "score": round(signal.get('score', signal.get('confluence_score', 50)), 2),
                        "sentiment": signal.get('sentiment', 'NEUTRAL'),
                        "price": signal.get('price', ticker.get('price', 0)),
                        "change_24h": round(signal.get('change_24h', ticker.get('change_24h', 0)), 2),
                        "volume_24h": signal.get('volume_24h', ticker.get('volume_24h', 0)),
                        "high_24h": signal.get('high_24h', ticker.get('high', 0)),
                        "low_24h": signal.get('low_24h', ticker.get('low', 0)),
                        "reliability": signal.get('reliability', 75),
                        "components": signal.get('components', {}),
                        "has_breakdown": False,
                        "score_history": []  # No history available without breakdown
                    })

            # Get perps data for Perpetuals Pulse widget
            logger.info("📊 Getting perps data for Perpetuals Pulse widget")
            perps_data = await self._get_live_perps_data(overview_data)
            logger.info(f"📦 Perps data retrieved: {perps_data}")

            # CRITICAL FIX: If regime_data is still "Initializing", use overview's market_regime
            final_regime = regime_data
            if regime_data in ('Initializing', 'unknown', 'initializing'):
                overview_regime = overview_data.get('market_regime', '')
                # Handle case where market_regime might be a dict
                if isinstance(overview_regime, dict):
                    overview_regime = overview_regime.get('regime', '')
                if overview_regime and overview_regime not in ('Initializing', 'unknown', 'initializing'):
                    final_regime = overview_regime
                    logger.info(f"✅ Using overview market_regime '{final_regime}' instead of '{regime_data}'")

            # Build mobile response
            mobile_data = {
                "market_overview": {
                    "market_regime": final_regime,
                    "trend_strength": overview_data.get('trend_strength', 0),
                    "volatility": overview_data.get('current_volatility', overview_data.get('volatility', 0)),
                    "current_volatility": overview_data.get('current_volatility', 0),
                    "avg_volatility": overview_data.get('avg_volatility', 0),
                    "btc_dominance": overview_data.get('btc_dominance', _coingecko_cache['btc_dominance']),
                    "btc_price": overview_data.get('btc_price', 0),
                    "btc_volatility": overview_data.get('btc_volatility', 0),
                    "btc_daily_volatility": overview_data.get('btc_daily_volatility', 0),
                    "market_dispersion": overview_data.get('market_dispersion', 0),
                    "avg_market_dispersion": overview_data.get('avg_market_dispersion', 0),
                    "total_volume_24h": overview_data.get('total_volume_24h', 0),
                    "average_change": overview_data.get('average_change', 0),
                    # CRITICAL FIX: Include gainers/losers for market sentiment
                    "gainers": overview_data.get('gainers', 0),
                    "losers": overview_data.get('losers', 0)
                },
                "confluence_scores": confluence_scores,
                "top_movers": {
                    "gainers": movers_data.get('gainers', [])[:5],
                    "losers": movers_data.get('losers', [])[:5]
                },
                "perps": perps_data,
                "timestamp": int(time.time()),
                "status": "success",
                "source": "shared_cache",
                "data_source": "live" if confluence_scores else "fallback"
            }

            if confluence_scores:
                self._record_successful_access(True)
            else:
                self._record_fallback_use()

            logger.debug(f"Mobile data constructed: {len(confluence_scores)} confluence scores")
            return mobile_data

        except Exception as e:
            logger.error(f"Error constructing mobile data: {e}")
            self._record_fallback_use()
            return self._get_fallback_mobile_data()

    # Helper methods for live data access
    async def _get_live_market_overview(self) -> Dict[str, Any]:
        """Get live market overview data"""
        try:
            data, _ = await get_market_data('market:overview')
            return data if isinstance(data, dict) else {}
        except:
            return {}

    async def _get_live_signals(self) -> Dict[str, Any]:
        """Get live signals data"""
        try:
            data, _ = await get_market_data('analysis:signals')
            return data if isinstance(data, dict) else {}
        except:
            return {}

    async def _get_live_market_movers(self) -> Dict[str, Any]:
        """Get live market movers data - derives from signals if cache is empty"""
        try:
            # First try the dedicated movers cache key
            data, _ = await get_market_data('market:movers')
            if data and isinstance(data, dict) and (data.get('gainers') or data.get('losers')):
                return data

            # Fallback: Derive top movers from signals data
            logger.info("⚠️ market:movers empty, deriving from analysis:signals")
            signals_data, _ = await get_market_data('analysis:signals')
            if not signals_data or not isinstance(signals_data, dict):
                return {"gainers": [], "losers": []}

            signals = signals_data.get('signals', [])
            if not signals:
                return {"gainers": [], "losers": []}

            # Sort by change_24h to get gainers and losers
            sorted_by_change = sorted(
                [s for s in signals if s.get('change_24h') is not None],
                key=lambda x: x.get('change_24h', 0),
                reverse=True
            )

            # Top gainers (positive changes, sorted highest first)
            gainers = [
                {
                    "symbol": s.get('symbol', ''),
                    "display_symbol": s.get('symbol', '').replace('USDT', ''),
                    "change_24h": s.get('change_24h', 0),
                    "price": s.get('price', 0),
                    "volume_24h": s.get('volume_24h', 0)
                }
                for s in sorted_by_change[:10]
                if s.get('change_24h', 0) > 0
            ]

            # Top losers (negative changes, sorted most negative first)
            losers = [
                {
                    "symbol": s.get('symbol', ''),
                    "display_symbol": s.get('symbol', '').replace('USDT', ''),
                    "change_24h": s.get('change_24h', 0),
                    "price": s.get('price', 0),
                    "volume_24h": s.get('volume_24h', 0)
                }
                for s in reversed(sorted_by_change[-10:])
                if s.get('change_24h', 0) < 0
            ]

            logger.info(f"✅ Derived {len(gainers)} gainers, {len(losers)} losers from signals")
            return {"gainers": gainers, "losers": losers}
        except Exception as e:
            logger.error(f"Error getting market movers: {e}")
            return {"gainers": [], "losers": []}

    async def _get_live_perps_data(self, overview_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get perpetuals market data for Perpetuals Pulse widget

        Includes funding rate, long/short ratio, and advanced metrics like
        funding z-score and L/S entropy (health indicator)
        """
        logger.info("🔍 _get_live_perps_data called")
        try:
            # Get BTC ticker for funding rate
            logger.info("📡 Fetching BTC ticker for funding rate")
            btc_ticker, _ = await get_market_data('ticker:BTCUSDT')
            logger.info(f"✅ Got BTC ticker: {btc_ticker is not None}")

            # Calculate funding z-score (how extreme is the current funding rate)
            funding_rate = btc_ticker.get('funding_rate', 0) if btc_ticker else 0
            # Typical funding rates range from -0.001 to 0.001 (0.1%)
            # Z-score: number of standard deviations from mean
            # Assuming mean=0, std=0.0003 (30 basis points)
            funding_zscore = funding_rate / 0.0003 if funding_rate != 0 else 0.0

            # Calculate L/S entropy (market health indicator)
            # Entropy measures how balanced the long/short ratio is
            # 70%+ = healthy (balanced market), <40% = unhealthy (overcrowded)
            long_pct = overview_data.get('long_percentage', 50)
            short_pct = 100 - long_pct

            # Shannon entropy normalized to 0-1 range
            # Maximum entropy (most balanced) = 0.5/0.5 split
            # Minimum entropy (least balanced) = 1.0/0.0 or 0.0/1.0 split
            import math
            if long_pct > 0 and short_pct > 0:
                p_long = long_pct / 100
                p_short = short_pct / 100
                entropy = -(p_long * math.log2(p_long) + p_short * math.log2(p_short))
                # Normalize: max entropy for 2 outcomes is log2(2) = 1.0
                ls_entropy = entropy / 1.0
            else:
                ls_entropy = 0.0  # Completely one-sided = unhealthy

            perps_result = {
                "funding_rate": funding_rate,
                "funding_zscore": round(funding_zscore, 2),
                "long_pct": round(long_pct, 1),
                "short_pct": round(short_pct, 1),
                "ls_entropy": round(ls_entropy, 2),
                "open_interest": overview_data.get('total_open_interest', 0),
                "volume_24h": overview_data.get('total_volume_24h', 0),
                "cex_pct": 90,  # Default CEX dominance
                "dex_pct": 10,
                "basis_pct": 0.0  # Futures-spot basis
            }
            logger.info(f"✅ Perps data calculated successfully: funding_zscore={perps_result['funding_zscore']}, ls_entropy={perps_result['ls_entropy']}")
            return perps_result
        except Exception as e:
            logger.error(f"❌ Error getting perps data: {e}", exc_info=True)
            return {
                "funding_rate": 0.0,
                "funding_zscore": 0.0,
                "long_pct": 50.0,
                "short_pct": 50.0,
                "ls_entropy": 0.5,
                "open_interest": 0,
                "volume_24h": 0,
                "cex_pct": 90,
                "dex_pct": 10,
                "basis_pct": 0.0
            }

    async def _get_live_market_regime(self) -> str:
        """Get live market regime with cache_warmer placeholder detection"""
        try:
            # First try analysis:market_regime (which returns a dict)
            data, _ = await get_market_data('analysis:market_regime')

            if isinstance(data, dict):
                # Check if this is cache_warmer placeholder data
                is_placeholder = data.get('status') == 'cache_warmer_generated'
                regime = data.get('regime', 'unknown')

                # Skip placeholder "Initializing" values - try fallback instead
                if not is_placeholder and regime not in ('Initializing', 'unknown', None):
                    return regime if isinstance(regime, str) else str(regime)

            elif isinstance(data, str) and data not in ('Initializing', 'unknown', 'initializing'):
                # Direct string value (non-placeholder)
                return data

            # Fallback: Try market:overview which has market_regime as string
            overview_data, _ = await get_market_data('market:overview')
            if isinstance(overview_data, dict):
                regime = overview_data.get('market_regime', 'unknown')
                # Handle case where market_regime is also a dict (nested placeholder)
                if isinstance(regime, dict):
                    regime = regime.get('regime', 'unknown')
                if regime and regime not in ('Initializing', 'unknown', None):
                    return regime if isinstance(regime, str) else str(regime)

            # Last resort: return a user-friendly loading state
            return 'Loading...'
        except Exception as e:
            logger.debug(f"Error getting market regime: {e}")
            return 'unknown'

    def _enhance_market_overview(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance market overview data with calculated fields"""
        enhanced = dict(data)

        # Ensure all required fields exist
        if 'total_volume_24h' not in enhanced and 'total_volume' in enhanced:
            enhanced['total_volume_24h'] = enhanced['total_volume']

        if 'spot_volume_24h' not in enhanced:
            enhanced['spot_volume_24h'] = enhanced.get('total_volume_24h', 0)

        if 'btc_dominance' not in enhanced or enhanced['btc_dominance'] == 0:
            enhanced['btc_dominance'] = _coingecko_cache['btc_dominance']  # Use CoinGecko cached value

        if 'trend_strength' not in enhanced:
            enhanced['trend_strength'] = 50  # Neutral default

        enhanced['timestamp'] = int(time.time())
        return enhanced

    def _record_successful_access(self, is_cross_service: bool):
        """Record successful data access"""
        self.access_metrics['cache_hits'] += 1
        if is_cross_service:
            self.access_metrics['cross_service_hits'] += 1
            self.access_metrics['last_live_data_time'] = time.time()

    def _record_fallback_use(self):
        """Record fallback data usage"""
        self.access_metrics['fallback_uses'] += 1

    # Fallback data methods
    def _get_fallback_market_overview(self) -> Dict[str, Any]:
        """Fallback market overview data"""
        return {
            'total_symbols': 0,
            'total_volume': 0,
            'total_volume_24h': 0,
            'average_change': 0,
            'volatility': 0,
            'btc_dominance': _coingecko_cache['btc_dominance'],
            'trend_strength': 50,
            'timestamp': int(time.time()),
            'data_source': 'fallback'
        }

    def _get_fallback_dashboard_overview(self) -> Dict[str, Any]:
        """Fallback dashboard overview"""
        return {
            'summary': {
                'total_symbols': 0,
                'total_volume': 0,
                'total_volume_24h': 0,
                'average_change': 0,
                'timestamp': int(time.time())
            },
            'market_regime': 'unknown',
            'signals': [],
            'top_gainers': [],
            'top_losers': [],
            'momentum': {'gainers': 0, 'losers': 0},
            'volatility': {'value': 0, 'level': 'normal'},
            'source': 'fallback',
            'data_source': 'fallback',
            'timestamp': int(time.time())
        }

    def _get_fallback_mobile_data(self) -> Dict[str, Any]:
        """Fallback mobile data"""
        return {
            "market_overview": {
                "market_regime": "unknown",
                "trend_strength": 50,
                "volatility": 0,
                "current_volatility": 0,
                "avg_volatility": 0,
                "btc_dominance": _coingecko_cache['btc_dominance'],
                "btc_price": 0,
                "btc_volatility": 0,
                "btc_daily_volatility": 0,
                "market_dispersion": 0,
                "avg_market_dispersion": 0,
                "total_volume_24h": 0,
                "average_change": 0,
                "gainers": 0,
                "losers": 0
            },
            "confluence_scores": [],
            "top_movers": {"gainers": [], "losers": []},
            "timestamp": int(time.time()),
            "status": "fallback",
            "source": "fallback",
            "data_source": "fallback"
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get web service cache adapter performance metrics"""
        total = self.access_metrics['total_requests']
        if total == 0:
            return {**self.access_metrics, 'cache_hit_rate_percent': 0, 'cross_service_hit_rate_percent': 0}

        cache_hit_rate = (self.access_metrics['cache_hits'] / total) * 100
        cross_service_rate = (self.access_metrics['cross_service_hits'] / total) * 100

        return {
            **self.access_metrics,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'cross_service_hit_rate_percent': round(cross_service_rate, 2),
            'fallback_rate_percent': round((self.access_metrics['fallback_uses'] / total) * 100, 2),
            'live_data_available': time.time() - self.access_metrics['last_live_data_time'] < 120,
            'timestamp': time.time()
        }

# Global instance
_web_cache_adapter_instance = None

def get_web_service_cache_adapter() -> WebServiceCacheAdapter:
    """Get singleton web service cache adapter"""
    global _web_cache_adapter_instance
    if _web_cache_adapter_instance is None:
        _web_cache_adapter_instance = WebServiceCacheAdapter()
    return _web_cache_adapter_instance