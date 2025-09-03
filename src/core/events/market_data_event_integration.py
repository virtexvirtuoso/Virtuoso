"""
Market Data Event Integration Service

This module provides a bridge between the existing MarketDataManager and the new
event-driven architecture. It wraps or extends the MarketDataManager to publish
events while maintaining full backward compatibility.

The integration preserves the existing 253x performance optimizations while
adding event-driven capabilities for loose coupling and improved scalability.

Key Features:
- Non-invasive integration with existing MarketDataManager
- Automatic event publishing for all market data updates
- Backward compatibility with existing synchronous consumers
- Performance monitoring and metrics
- Configurable event filtering and throttling
- Circuit breaker protection for event publishing
"""

from typing import Dict, List, Optional, Any, Callable, Union
import asyncio
import logging
import time
import weakref
from datetime import datetime
from dataclasses import asdict

from .event_publisher import EventPublisher
from .event_types import (
    DataType, MarketDataUpdatedEvent, OHLCVDataEvent, 
    OrderBookDataEvent, TradeDataEvent, LiquidationDataEvent
)
from ..interfaces.services import IAsyncDisposable


class MarketDataEventIntegration(IAsyncDisposable):
    """
    Integration service that adds event publishing capabilities to MarketDataManager
    without modifying its core functionality.
    
    This service acts as a decorator/wrapper that intercepts market data updates
    and publishes them as events while preserving all existing behavior.
    """
    
    def __init__(
        self,
        event_publisher: EventPublisher,
        market_data_manager=None,
        enable_event_publishing: bool = True,
        event_throttle_ms: int = 100,
        enable_performance_monitoring: bool = True
    ):
        self.event_publisher = event_publisher
        self.market_data_manager = None
        self.enable_event_publishing = enable_event_publishing
        self.event_throttle_ms = event_throttle_ms
        self.enable_performance_monitoring = enable_performance_monitoring
        
        # Event throttling to prevent overwhelming the event bus
        self._last_event_times: Dict[str, float] = {}
        
        # Performance metrics
        if enable_performance_monitoring:
            self._metrics = {
                'events_published': 0,
                'events_throttled': 0,
                'avg_event_publish_time_ms': 0.0,
                'integration_overhead_ms': 0.0,
                'data_types_processed': set(),
                'symbols_processed': set()
            }
        else:
            self._metrics = None
            
        # Original method references for restoration
        self._original_methods: Dict[str, Callable] = {}
        
        self._logger = logging.getLogger(__name__)
        self._running = False
        
        # Set market data manager if provided
        if market_data_manager:
            self.integrate_with_manager(market_data_manager)

    async def start(self):
        """Start the integration service."""
        if self._running:
            return
            
        await self.event_publisher.start()
        self._running = True
        
        self._logger.info("MarketDataEventIntegration started")

    async def stop(self):
        """Stop the integration service."""
        if not self._running:
            return
            
        # Restore original methods if we wrapped them
        await self._restore_original_methods()
        
        self._running = False
        self._logger.info("MarketDataEventIntegration stopped")

    async def dispose_async(self):
        """Cleanup resources."""
        await self.stop()
        self._last_event_times.clear()
        if self._metrics:
            self._metrics['data_types_processed'].clear()
            self._metrics['symbols_processed'].clear()

    def integrate_with_manager(self, market_data_manager):
        """
        Integrate with an existing MarketDataManager instance.
        
        This method wraps key methods to add event publishing without
        changing the manager's interface or behavior.
        """
        if not market_data_manager:
            return
            
        self.market_data_manager = market_data_manager
        
        # Store reference to original methods
        self._store_original_methods()
        
        # Wrap key methods with event publishing
        self._wrap_data_update_methods()
        
        self._logger.info(
            f"Integrated with MarketDataManager: {type(market_data_manager).__name__}"
        )

    def _store_original_methods(self):
        """Store references to original methods for potential restoration."""
        if not self.market_data_manager:
            return
            
        methods_to_wrap = [
            'update_ticker_data',
            'update_ohlcv_data', 
            'update_orderbook_data',
            'update_trades_data',
            'update_liquidation_data',
            '_handle_websocket_update'
        ]
        
        for method_name in methods_to_wrap:
            if hasattr(self.market_data_manager, method_name):
                original_method = getattr(self.market_data_manager, method_name)
                self._original_methods[method_name] = original_method

    def _wrap_data_update_methods(self):
        """Wrap data update methods with event publishing."""
        if not self.market_data_manager:
            return
            
        # Wrap specific data update methods
        if hasattr(self.market_data_manager, 'update_ohlcv_data'):
            setattr(
                self.market_data_manager,
                'update_ohlcv_data',
                self._wrap_ohlcv_update(self._original_methods.get('update_ohlcv_data'))
            )
            
        if hasattr(self.market_data_manager, 'update_orderbook_data'):
            setattr(
                self.market_data_manager,
                'update_orderbook_data', 
                self._wrap_orderbook_update(self._original_methods.get('update_orderbook_data'))
            )
            
        if hasattr(self.market_data_manager, 'update_trades_data'):
            setattr(
                self.market_data_manager,
                'update_trades_data',
                self._wrap_trades_update(self._original_methods.get('update_trades_data'))
            )
            
        # Wrap WebSocket handler if available
        if hasattr(self.market_data_manager, '_handle_websocket_update'):
            setattr(
                self.market_data_manager,
                '_handle_websocket_update',
                self._wrap_websocket_handler(self._original_methods.get('_handle_websocket_update'))
            )

    def _wrap_ohlcv_update(self, original_method):
        """Wrap OHLCV update method with event publishing."""
        if not original_method:
            return None
            
        async def wrapped_method(symbol: str, timeframe: str, data: Any, *args, **kwargs):
            start_time = time.time()
            
            try:
                # Call original method first
                result = await original_method(symbol, timeframe, data, *args, **kwargs)
                
                # Publish event if enabled and not throttled
                if self._should_publish_event('ohlcv', symbol, timeframe):
                    await self._publish_ohlcv_event(symbol, timeframe, data)
                
                return result
                
            except Exception as e:
                self._logger.error(f"Error in wrapped OHLCV update: {e}")
                raise
            finally:
                if self._metrics and self.enable_performance_monitoring:
                    overhead = (time.time() - start_time) * 1000
                    self._update_overhead_metric(overhead)
                    
        return wrapped_method

    def _wrap_orderbook_update(self, original_method):
        """Wrap orderbook update method with event publishing.""" 
        if not original_method:
            return None
            
        async def wrapped_method(symbol: str, orderbook_data: Dict[str, Any], *args, **kwargs):
            start_time = time.time()
            
            try:
                # Call original method first
                result = await original_method(symbol, orderbook_data, *args, **kwargs)
                
                # Publish event if enabled and not throttled
                if self._should_publish_event('orderbook', symbol):
                    await self._publish_orderbook_event(symbol, orderbook_data)
                    
                return result
                
            except Exception as e:
                self._logger.error(f"Error in wrapped orderbook update: {e}")
                raise
            finally:
                if self._metrics and self.enable_performance_monitoring:
                    overhead = (time.time() - start_time) * 1000
                    self._update_overhead_metric(overhead)
                    
        return wrapped_method

    def _wrap_trades_update(self, original_method):
        """Wrap trades update method with event publishing."""
        if not original_method:
            return None
            
        async def wrapped_method(symbol: str, trades_data: List[Dict[str, Any]], *args, **kwargs):
            start_time = time.time()
            
            try:
                # Call original method first
                result = await original_method(symbol, trades_data, *args, **kwargs)
                
                # Publish event if enabled and not throttled
                if self._should_publish_event('trades', symbol):
                    await self._publish_trades_event(symbol, trades_data)
                    
                return result
                
            except Exception as e:
                self._logger.error(f"Error in wrapped trades update: {e}")
                raise
            finally:
                if self._metrics and self.enable_performance_monitoring:
                    overhead = (time.time() - start_time) * 1000
                    self._update_overhead_metric(overhead)
                    
        return wrapped_method

    def _wrap_websocket_handler(self, original_method):
        """Wrap WebSocket handler with event publishing."""
        if not original_method:
            return None
            
        async def wrapped_method(channel: str, data: Dict[str, Any], *args, **kwargs):
            start_time = time.time()
            
            try:
                # Call original method first
                result = await original_method(channel, data, *args, **kwargs)
                
                # Publish generic market data event
                if self._should_publish_event('websocket', channel):
                    await self._publish_websocket_event(channel, data)
                    
                return result
                
            except Exception as e:
                self._logger.error(f"Error in wrapped WebSocket handler: {e}")
                raise
            finally:
                if self._metrics and self.enable_performance_monitoring:
                    overhead = (time.time() - start_time) * 1000
                    self._update_overhead_metric(overhead)
                    
        return wrapped_method

    def _should_publish_event(self, data_type: str, symbol: str = "", timeframe: str = "") -> bool:
        """Check if event should be published (throttling logic)."""
        if not self.enable_event_publishing or not self._running:
            return False
            
        # Create throttle key
        throttle_key = f"{data_type}:{symbol}:{timeframe}"
        
        current_time = time.time() * 1000  # Convert to milliseconds
        last_event_time = self._last_event_times.get(throttle_key, 0)
        
        if current_time - last_event_time >= self.event_throttle_ms:
            self._last_event_times[throttle_key] = current_time
            return True
        else:
            if self._metrics:
                self._metrics['events_throttled'] += 1
            return False

    async def _publish_ohlcv_event(self, symbol: str, timeframe: str, data: Any):
        """Publish OHLCV data event."""
        try:
            start_time = time.time()
            
            # Extract exchange from market data manager if available
            exchange = getattr(self.market_data_manager, 'exchange_name', 'unknown')
            
            # Handle different data formats
            candles_data = data
            if hasattr(data, 'to_dict'):  # DataFrame
                candles_data = data.to_dict('records')
            elif not isinstance(data, (dict, list)):
                candles_data = {'raw_data': str(data)}
                
            await self.event_publisher.publish_ohlcv_data(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                candles_data=candles_data
            )
            
            if self._metrics:
                self._metrics['events_published'] += 1
                self._metrics['data_types_processed'].add('ohlcv')
                self._metrics['symbols_processed'].add(symbol)
                
                publish_time = (time.time() - start_time) * 1000
                self._update_publish_time_metric(publish_time)
                
        except Exception as e:
            self._logger.error(f"Failed to publish OHLCV event: {e}")

    async def _publish_orderbook_event(self, symbol: str, orderbook_data: Dict[str, Any]):
        """Publish orderbook data event."""
        try:
            start_time = time.time()
            
            exchange = getattr(self.market_data_manager, 'exchange_name', 'unknown')
            
            # Extract bids/asks from orderbook data
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            await self.event_publisher.publish_orderbook_data(
                symbol=symbol,
                exchange=exchange,
                bids=bids,
                asks=asks
            )
            
            if self._metrics:
                self._metrics['events_published'] += 1
                self._metrics['data_types_processed'].add('orderbook')
                self._metrics['symbols_processed'].add(symbol)
                
                publish_time = (time.time() - start_time) * 1000
                self._update_publish_time_metric(publish_time)
                
        except Exception as e:
            self._logger.error(f"Failed to publish orderbook event: {e}")

    async def _publish_trades_event(self, symbol: str, trades_data: List[Dict[str, Any]]):
        """Publish trades data event."""
        try:
            start_time = time.time()
            
            exchange = getattr(self.market_data_manager, 'exchange_name', 'unknown')
            
            # Calculate 24h volume if available
            volume_24h = sum(trade.get('amount', 0) for trade in trades_data)
            
            await self.event_publisher.publish_trade_data(
                symbol=symbol,
                exchange=exchange,
                trades=trades_data,
                volume_24h=volume_24h
            )
            
            if self._metrics:
                self._metrics['events_published'] += 1
                self._metrics['data_types_processed'].add('trades')
                self._metrics['symbols_processed'].add(symbol)
                
                publish_time = (time.time() - start_time) * 1000
                self._update_publish_time_metric(publish_time)
                
        except Exception as e:
            self._logger.error(f"Failed to publish trades event: {e}")

    async def _publish_websocket_event(self, channel: str, data: Dict[str, Any]):
        """Publish generic WebSocket event."""
        try:
            start_time = time.time()
            
            exchange = getattr(self.market_data_manager, 'exchange_name', 'unknown')
            
            # Determine data type from channel
            data_type = DataType.TICKER  # Default
            if 'orderbook' in channel or 'depth' in channel:
                data_type = DataType.ORDERBOOK
            elif 'kline' in channel or 'candle' in channel:
                data_type = DataType.OHLCV
            elif 'trade' in channel:
                data_type = DataType.TRADES
            elif 'liquidation' in channel:
                data_type = DataType.LIQUIDATIONS
                
            # Extract symbol from channel or data
            symbol = data.get('symbol', channel.split('.')[-1] if '.' in channel else 'unknown')
            
            await self.event_publisher.publish_market_data(
                symbol=symbol,
                exchange=exchange,
                data_type=data_type,
                raw_data=data
            )
            
            if self._metrics:
                self._metrics['events_published'] += 1
                self._metrics['data_types_processed'].add('websocket')
                self._metrics['symbols_processed'].add(symbol)
                
                publish_time = (time.time() - start_time) * 1000
                self._update_publish_time_metric(publish_time)
                
        except Exception as e:
            self._logger.error(f"Failed to publish WebSocket event: {e}")

    async def _restore_original_methods(self):
        """Restore original methods to the market data manager."""
        if not self.market_data_manager or not self._original_methods:
            return
            
        for method_name, original_method in self._original_methods.items():
            if hasattr(self.market_data_manager, method_name):
                setattr(self.market_data_manager, method_name, original_method)
                
        self._logger.debug("Restored original methods to MarketDataManager")

    def _update_overhead_metric(self, overhead_ms: float):
        """Update integration overhead metric."""
        if not self._metrics:
            return
            
        current_overhead = self._metrics['integration_overhead_ms']
        events_count = max(self._metrics['events_published'], 1)
        
        self._metrics['integration_overhead_ms'] = (
            (current_overhead * (events_count - 1) + overhead_ms) / events_count
        )

    def _update_publish_time_metric(self, publish_time_ms: float):
        """Update average publish time metric."""
        if not self._metrics:
            return
            
        current_avg = self._metrics['avg_event_publish_time_ms']
        events_count = self._metrics['events_published']
        
        self._metrics['avg_event_publish_time_ms'] = (
            (current_avg * (events_count - 1) + publish_time_ms) / events_count
        )

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get integration metrics."""
        if not self._metrics:
            return None
            
        return {
            **self._metrics,
            'data_types_processed': list(self._metrics['data_types_processed']),
            'symbols_processed': list(self._metrics['symbols_processed']),
            'is_running': self._running,
            'event_publishing_enabled': self.enable_event_publishing,
            'throttle_ms': self.event_throttle_ms,
            'integrated_manager': type(self.market_data_manager).__name__ if self.market_data_manager else None
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        event_publisher_health = await self.event_publisher.health_check()
        
        return {
            'status': 'healthy' if self._running else 'stopped',
            'integration_active': self.market_data_manager is not None,
            'metrics': self.get_metrics(),
            'event_publisher_health': event_publisher_health,
            'original_methods_stored': len(self._original_methods)
        }

    # =============================================================================
    # Manual Event Publishing Methods (for direct use without integration)
    # =============================================================================

    async def publish_ticker_update(
        self,
        symbol: str,
        ticker_data: Dict[str, Any],
        exchange: str = "unknown"
    ):
        """Manually publish ticker update event."""
        if not self._should_publish_event('ticker', symbol):
            return
            
        await self.event_publisher.publish_market_data(
            symbol=symbol,
            exchange=exchange,
            data_type=DataType.TICKER,
            raw_data=ticker_data
        )

    async def publish_liquidation_update(
        self,
        symbol: str,
        liquidation_data: List[Dict[str, Any]],
        exchange: str = "unknown"
    ):
        """Manually publish liquidation data event."""
        if not self._should_publish_event('liquidation', symbol):
            return
            
        # Calculate totals
        total_liquidated = sum(liq.get('size', 0) for liq in liquidation_data)
        long_liquidations = sum(
            liq.get('size', 0) for liq in liquidation_data 
            if liq.get('side', '').lower() == 'buy'
        )
        short_liquidations = sum(
            liq.get('size', 0) for liq in liquidation_data 
            if liq.get('side', '').lower() == 'sell'
        )
        
        event = LiquidationDataEvent(
            symbol=symbol,
            exchange=exchange,
            liquidations=liquidation_data,
            total_liquidated=total_liquidated,
            long_liquidations=long_liquidations,
            short_liquidations=short_liquidations,
            raw_data={'liquidations': liquidation_data}
        )
        
        await self.event_publisher._publish_event(event)