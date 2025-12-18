#!/usr/bin/env python3
"""
Trading Service Cache Bridge Integration
=======================================

CRITICAL DATA BRIDGE: Integrates shared cache bridge into trading service
to populate shared cache with live market data for web service consumption.

This module ensures that live market data from the trading service flows
seamlessly to the web service endpoints via shared cache.

Key Integration Points:
1. Market Monitor data collection
2. Signal generation and analysis results
3. Real-time ticker updates
4. Market overview and statistics
5. Trading alerts and notifications

Features:
- Automatic cache population during monitoring cycles
- Real-time data streaming to shared cache
- Performance optimization for critical endpoints
- Error handling and fallback mechanisms
- Metrics tracking for cache bridge performance
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Import shared cache bridge
from .shared_cache_bridge import (
    get_shared_cache_bridge,
    publish_market_data,
    DataSource,
    initialize_shared_cache
)

logger = logging.getLogger(__name__)

class TradingServiceCacheBridge:
    """
    Trading Service Cache Bridge

    Integrates with monitoring system to populate shared cache with live data
    """

    def __init__(self, market_monitor=None):
        self.market_monitor = market_monitor
        self.bridge = get_shared_cache_bridge()
        self.last_update_times = {}
        self.update_intervals = {
            'market:tickers': 5,      # Update every 5 seconds
            'market:overview': 10,    # Update every 10 seconds
            'analysis:signals': 15,   # Update every 15 seconds
            'market:movers': 30,      # Update every 30 seconds
            'analysis:market_regime': 60  # Update every minute
        }
        self.performance_metrics = {
            'cache_updates': 0,
            'failed_updates': 0,
            'data_volume_bytes': 0,
            'last_successful_update': 0
        }

    async def initialize(self):
        """Initialize the trading service cache bridge"""
        try:
            # Initialize shared cache bridge
            success = await initialize_shared_cache()
            if not success:
                logger.error("Failed to initialize shared cache bridge")
                return False

            logger.info("✅ Trading Service Cache Bridge initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize trading service cache bridge: {e}")
            return False

    async def populate_market_overview(self, overview_data: Dict[str, Any]):
        """
        Populate shared cache with market overview data

        CRITICAL: This is the primary integration point for market data
        """
        try:
            if not self._should_update('market:overview'):
                return

            # Enhance overview data with timestamp
            enhanced_data = {
                **overview_data,
                'timestamp': int(time.time()),
                'source': 'trading_service',
                'last_update': datetime.now(timezone.utc).isoformat()
            }

            # Publish to shared cache
            await publish_market_data('market:overview', enhanced_data, ttl=300)

            # Also publish to alternate key for compatibility
            await publish_market_data('virtuoso:market_overview', enhanced_data, ttl=300)

            self._record_successful_update('market:overview', enhanced_data)
            logger.debug(f"Published market overview: {len(enhanced_data)} fields")

        except Exception as e:
            self._record_failed_update('market:overview', e)
            logger.error(f"Failed to populate market overview: {e}")

    async def populate_ticker_data(self, ticker_data: Dict[str, Any]):
        """Populate shared cache with real-time ticker data"""
        try:
            if not self._should_update('market:tickers'):
                return

            # Process and enhance ticker data
            processed_tickers = {}
            for symbol, ticker in ticker_data.items():
                processed_tickers[symbol] = {
                    'symbol': symbol,
                    'price': ticker.get('last', ticker.get('close', 0)),
                    'change_24h': ticker.get('percentage', 0),
                    'volume': ticker.get('baseVolume', ticker.get('volume', 0)),
                    'volume_24h': ticker.get('baseVolume', ticker.get('volume', 0)),
                    'high': ticker.get('high', 0),
                    'low': ticker.get('low', 0),
                    'bid': ticker.get('bid', 0),
                    'ask': ticker.get('ask', 0),
                    'timestamp': int(time.time())
                }

            # Publish to shared cache
            await publish_market_data('market:tickers', processed_tickers, ttl=60)

            self._record_successful_update('market:tickers', processed_tickers)
            logger.debug(f"Published {len(processed_tickers)} tickers to shared cache")

        except Exception as e:
            self._record_failed_update('market:tickers', e)
            logger.error(f"Failed to populate ticker data: {e}")

    async def populate_signals_data(self, signals_data: Dict[str, Any]):
        """
        Populate shared cache with trading signals

        CRITICAL: Ensures web service shows live trading signals
        """
        try:
            if not self._should_update('analysis:signals'):
                return

            # Ensure signals data has proper structure
            processed_signals = {
                'signals': signals_data.get('signals', []),
                'count': len(signals_data.get('signals', [])),
                'timestamp': int(time.time()),
                'source': 'trading_service',
                'last_analysis': datetime.now(timezone.utc).isoformat()
            }

            # Add signal metadata if available
            if 'metadata' in signals_data:
                processed_signals['metadata'] = signals_data['metadata']

            # Publish to shared cache
            await publish_market_data('analysis:signals', processed_signals, ttl=300)

            # Also publish individual signal breakdowns for detailed view
            for signal in processed_signals['signals'][:10]:  # Top 10 signals
                symbol = signal.get('symbol')
                if symbol:
                    breakdown_key = f"confluence:breakdown:{symbol}"
                    breakdown_data = {
                        'symbol': symbol,
                        'overall_score': signal.get('confluence_score', signal.get('score', 50)),
                        'sentiment': signal.get('sentiment', 'NEUTRAL'),
                        'reliability': signal.get('reliability', 75),
                        'components': signal.get('components', {}),
                        'sub_components': signal.get('sub_components', {}),
                        'interpretations': signal.get('interpretations', {}),
                        'timestamp': int(time.time())
                    }
                    await publish_market_data(breakdown_key, breakdown_data, ttl=300)

            self._record_successful_update('analysis:signals', processed_signals)
            logger.debug(f"Published {len(processed_signals['signals'])} signals to shared cache")

        except Exception as e:
            self._record_failed_update('analysis:signals', e)
            logger.error(f"Failed to populate signals data: {e}")

    async def populate_market_movers(self, movers_data: Dict[str, Any]):
        """Populate shared cache with market movers data"""
        try:
            if not self._should_update('market:movers'):
                return

            # Process market movers data
            processed_movers = {
                'gainers': movers_data.get('gainers', []),
                'losers': movers_data.get('losers', []),
                'timestamp': int(time.time()),
                'source': 'trading_service'
            }

            # Ensure gainers/losers have required fields
            for category in ['gainers', 'losers']:
                for mover in processed_movers[category]:
                    if 'symbol' in mover and 'change_24h' not in mover:
                        mover['change_24h'] = mover.get('change', mover.get('percentage', 0))
                    if 'volume_24h' not in mover:
                        mover['volume_24h'] = mover.get('volume', 0)

            # Publish to shared cache
            await publish_market_data('market:movers', processed_movers, ttl=300)

            self._record_successful_update('market:movers', processed_movers)
            logger.debug(f"Published market movers: {len(processed_movers['gainers'])} gainers, {len(processed_movers['losers'])} losers")

        except Exception as e:
            self._record_failed_update('market:movers', e)
            logger.error(f"Failed to populate market movers: {e}")

    async def populate_market_regime(self, regime: str, regime_data: Optional[Dict[str, Any]] = None):
        """Populate shared cache with market regime analysis"""
        try:
            if not self._should_update('analysis:market_regime'):
                return

            # Create comprehensive regime data
            regime_info = {
                'current_regime': regime,
                'timestamp': int(time.time()),
                'source': 'trading_service'
            }

            if regime_data:
                regime_info.update(regime_data)

            # Publish to shared cache
            await publish_market_data('analysis:market_regime', regime, ttl=300)
            await publish_market_data('analysis:market_regime_data', regime_info, ttl=300)

            self._record_successful_update('analysis:market_regime', regime_info)
            logger.debug(f"Published market regime: {regime}")

        except Exception as e:
            self._record_failed_update('analysis:market_regime', e)
            logger.error(f"Failed to populate market regime: {e}")

    async def populate_dashboard_data(self, dashboard_data: Dict[str, Any]):
        """
        Populate comprehensive dashboard data for web service

        CRITICAL: Main integration point for dashboard endpoints
        """
        try:
            # Create comprehensive dashboard dataset
            enhanced_dashboard = {
                **dashboard_data,
                'timestamp': int(time.time()),
                'source': 'trading_service',
                'last_update': datetime.now(timezone.utc).isoformat(),
                'cache_bridge_version': '1.0.0'
            }

            # Publish to shared cache with multiple keys for compatibility
            await publish_market_data('virtuoso:dashboard_data', enhanced_dashboard, ttl=60)
            await publish_market_data('dashboard:complete', enhanced_dashboard, ttl=60)

            self._record_successful_update('dashboard:data', enhanced_dashboard)
            logger.debug("Published comprehensive dashboard data to shared cache")

        except Exception as e:
            self._record_failed_update('dashboard:data', e)
            logger.error(f"Failed to populate dashboard data: {e}")

    async def populate_btc_dominance(self, dominance_value: float):
        """Populate BTC dominance data"""
        try:
            dominance_data = {
                'value': dominance_value,
                'timestamp': int(time.time()),
                'source': 'trading_service'
            }

            await publish_market_data('market:btc_dominance', str(dominance_value), ttl=300)
            await publish_market_data('market:btc_dominance_data', dominance_data, ttl=300)

            logger.debug(f"Published BTC dominance: {dominance_value}%")

        except Exception as e:
            logger.error(f"Failed to populate BTC dominance: {e}")

    async def populate_system_alerts(self, alerts: List[Dict[str, Any]]):
        """Populate system alerts for web service"""
        try:
            alerts_data = {
                'alerts': alerts,
                'count': len(alerts),
                'timestamp': int(time.time()),
                'source': 'trading_service'
            }

            await publish_market_data('system:alerts', alerts, ttl=120)
            await publish_market_data('system:alerts_data', alerts_data, ttl=120)

            logger.debug(f"Published {len(alerts)} system alerts")

        except Exception as e:
            logger.error(f"Failed to populate system alerts: {e}")

    def _should_update(self, key: str) -> bool:
        """Check if key should be updated based on interval"""
        now = time.time()
        last_update = self.last_update_times.get(key, 0)
        interval = self.update_intervals.get(key, 30)

        return (now - last_update) >= interval

    def _record_successful_update(self, key: str, data: Any):
        """Record successful cache update"""
        now = time.time()
        self.last_update_times[key] = now
        self.performance_metrics['cache_updates'] += 1
        self.performance_metrics['last_successful_update'] = now

        # Estimate data size
        try:
            data_str = json.dumps(data) if not isinstance(data, str) else data
            self.performance_metrics['data_volume_bytes'] += len(data_str.encode())
        except:
            pass

    def _record_failed_update(self, key: str, error: Exception):
        """Record failed cache update"""
        self.performance_metrics['failed_updates'] += 1
        logger.warning(f"Cache update failed for {key}: {error}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get cache bridge performance metrics"""
        total_updates = self.performance_metrics['cache_updates'] + self.performance_metrics['failed_updates']
        success_rate = 0
        if total_updates > 0:
            success_rate = (self.performance_metrics['cache_updates'] / total_updates) * 100

        return {
            **self.performance_metrics,
            'success_rate_percent': round(success_rate, 2),
            'total_updates_attempted': total_updates,
            'data_volume_mb': round(self.performance_metrics['data_volume_bytes'] / (1024 * 1024), 2),
            'update_intervals': self.update_intervals,
            'last_update_times': {k: datetime.fromtimestamp(v).isoformat() if v > 0 else None
                                for k, v in self.last_update_times.items()}
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for trading service cache bridge"""
        try:
            bridge_health = await self.bridge.health_check()
            metrics = self.get_performance_metrics()

            return {
                'trading_bridge_status': 'healthy',
                'shared_cache_bridge': bridge_health,
                'performance_metrics': metrics,
                'data_flow_active': time.time() - self.performance_metrics.get('last_successful_update', 0) < 60,
                'timestamp': time.time()
            }

        except Exception as e:
            return {
                'trading_bridge_status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }

# Global instance for easy integration
_trading_bridge_instance = None

def get_trading_service_bridge(market_monitor=None) -> TradingServiceCacheBridge:
    """Get singleton trading service cache bridge"""
    global _trading_bridge_instance
    if _trading_bridge_instance is None:
        _trading_bridge_instance = TradingServiceCacheBridge(market_monitor)
    return _trading_bridge_instance

# Integration hooks for monitoring system
async def integrate_with_market_monitor(market_monitor, cache_bridge: TradingServiceCacheBridge):
    """
    Integrate cache bridge with market monitor

    This function should be called during market monitor initialization
    to establish the data bridge
    """
    try:
        # Initialize cache bridge
        success = await cache_bridge.initialize()
        if not success:
            logger.error("Failed to initialize cache bridge integration")
            return False

        # Hook into market monitor data processing
        original_process_data = getattr(market_monitor, 'process_monitoring_data', None)
        if original_process_data:
            async def enhanced_process_data(*args, **kwargs):
                result = await original_process_data(*args, **kwargs)

                # Extract and publish data to cache bridge
                if result and isinstance(result, dict):
                    try:
                        # Market overview
                        if 'market_overview' in result:
                            await cache_bridge.populate_market_overview(result['market_overview'])

                        # Ticker data
                        if 'tickers' in result:
                            await cache_bridge.populate_ticker_data(result['tickers'])

                        # Signals
                        if 'signals' in result:
                            await cache_bridge.populate_signals_data(result['signals'])

                        # Market movers
                        if 'movers' in result:
                            await cache_bridge.populate_market_movers(result['movers'])

                        # Market regime
                        if 'market_regime' in result:
                            await cache_bridge.populate_market_regime(result['market_regime'])

                        # Complete dashboard data
                        await cache_bridge.populate_dashboard_data(result)

                    except Exception as e:
                        logger.error(f"Error in cache bridge integration: {e}")

                return result

            # Replace the original method
            market_monitor.process_monitoring_data = enhanced_process_data

        logger.info("✅ Cache bridge integrated with market monitor")
        return True

    except Exception as e:
        logger.error(f"Failed to integrate cache bridge with market monitor: {e}")
        return False