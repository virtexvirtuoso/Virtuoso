from src.utils.task_tracker import create_tracked_task
"""
Event Publisher Service for Virtuoso Trading System

This module provides a high-level event publishing service that integrates
with the EventBus infrastructure. It handles event creation, validation,
and publishing while maintaining backward compatibility with existing
synchronous components.

Key Features:
- Automatic event creation from market data
- Batch publishing for performance
- Event validation and enrichment
- Integration with existing cache layers
- Backward compatibility bridge
- Performance monitoring and metrics

The EventPublisher acts as a bridge between the existing synchronous
components and the new event-driven architecture, allowing gradual
migration without disrupting the current 253x performance optimizations.
"""

from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from dataclasses import asdict

from .event_bus import EventBus, Event, EventPriority
from .event_types import (
    DataType, AnalysisType, SignalType, AlertSeverity,
    MarketDataUpdatedEvent, OHLCVDataEvent, OrderBookDataEvent,
    TradeDataEvent, LiquidationDataEvent, AnalysisCompletedEvent,
    TechnicalAnalysisEvent, VolumeAnalysisEvent, ConfluenceAnalysisEvent,
    TradingSignalEvent, SystemAlertEvent, ComponentStatusEvent,
    create_market_data_event, create_analysis_event, create_alert_event
)
from ..interfaces.services import IAsyncDisposable


class EventPublisher(IAsyncDisposable):
    """
    High-level event publishing service that acts as a bridge between
    existing components and the event-driven architecture.
    
    This service provides:
    - Type-safe event creation and publishing
    - Automatic event enrichment with metadata
    - Batch publishing for performance
    - Integration with existing cache and DI systems
    - Metrics and monitoring capabilities
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        enable_batching: bool = True,
        batch_size: int = 100,
        batch_timeout_ms: int = 100,
        enable_metrics: bool = True
    ):
        self.event_bus = event_bus
        self.enable_batching = enable_batching
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.enable_metrics = enable_metrics
        
        # Batching infrastructure
        self._pending_events: List[Event] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._last_batch_time = time.time()
        
        # Metrics
        if enable_metrics:
            self._metrics = {
                'events_created': 0,
                'events_published': 0,
                'batch_count': 0,
                'avg_batch_size': 0.0,
                'publish_errors': 0,
                'enrichment_time_ms': 0.0,
                'total_publish_time_ms': 0.0
            }
        else:
            self._metrics = None
            
        # Event enrichment callbacks
        self._enrichment_callbacks: Dict[str, List[Callable[[Event], Event]]] = {}
        
        self._logger = logging.getLogger(__name__)
        self._running = False
        
        self._logger.info("EventPublisher initialized with batching=%s", enable_batching)

    async def start(self):
        """Start the event publisher."""
        if self._running:
            return
            
        self._running = True
        
        # Start event bus if not running
        await self.event_bus.start()
        
        # Start batch processing if enabled
        if self.enable_batching:
            self._batch_task = create_tracked_task(self._batch_processor(), name="auto_tracked_task")
            
        self._logger.info("EventPublisher started")

    async def stop(self):
        """Stop the event publisher gracefully."""
        if not self._running:
            return
            
        self._running = False
        
        # Process any remaining batched events
        if self.enable_batching and self._pending_events:
            await self._flush_batch()
            
        # Cancel batch processor
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
                
        self._logger.info("EventPublisher stopped")

    async def dispose_async(self):
        """Cleanup resources."""
        await self.stop()
        self._pending_events.clear()
        self._enrichment_callbacks.clear()

    # =============================================================================
    # Market Data Event Publishing
    # =============================================================================

    async def publish_market_data(
        self,
        symbol: str,
        exchange: str,
        data_type: DataType,
        raw_data: Dict[str, Any],
        timeframe: str = "",
        processed_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Publish market data event.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name (e.g., 'bybit')
            data_type: Type of market data
            raw_data: Raw data from exchange
            timeframe: Timeframe for OHLCV data
            processed_data: Optional processed/normalized data
            
        Returns:
            Event ID
        """
        event = create_market_data_event(
            symbol=symbol,
            exchange=exchange,
            data_type=data_type,
            raw_data=raw_data,
            timeframe=timeframe,
            processed_data=processed_data,
            **kwargs
        )
        
        return await self._publish_event(event)

    async def publish_ohlcv_data(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        candles_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        **kwargs
    ) -> str:
        """Publish OHLCV candle data event."""
        import pandas as pd
        
        # Convert to DataFrame if needed
        if isinstance(candles_data, list):
            candles_df = pd.DataFrame(candles_data)
        elif isinstance(candles_data, dict) and 'candles' in candles_data:
            candles_df = pd.DataFrame(candles_data['candles'])
        else:
            candles_df = None
            
        event = OHLCVDataEvent(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            raw_data=candles_data if isinstance(candles_data, dict) else {'candles': candles_data},
            candles=candles_df,
            candle_count=len(candles_df) if candles_df is not None else 0,
            timeframe_minutes=self._parse_timeframe_minutes(timeframe),
            **kwargs
        )
        
        return await self._publish_event(event)

    async def publish_orderbook_data(
        self,
        symbol: str,
        exchange: str,
        bids: List[List[float]],
        asks: List[List[float]],
        **kwargs
    ) -> str:
        """Publish order book data event."""
        spread = asks[0][0] - bids[0][0] if bids and asks else 0.0
        
        event = OrderBookDataEvent(
            symbol=symbol,
            exchange=exchange,
            bids=bids,
            asks=asks,
            spread=spread,
            depth=max(len(bids), len(asks)),
            raw_data={'bids': bids, 'asks': asks},
            **kwargs
        )
        
        return await self._publish_event(event)

    async def publish_trade_data(
        self,
        symbol: str,
        exchange: str,
        trades: List[Dict[str, Any]],
        volume_24h: float = 0.0,
        **kwargs
    ) -> str:
        """Publish trade data event."""
        event = TradeDataEvent(
            symbol=symbol,
            exchange=exchange,
            trades=trades,
            volume_24h=volume_24h,
            trade_count=len(trades),
            raw_data={'trades': trades, 'volume_24h': volume_24h},
            **kwargs
        )
        
        return await self._publish_event(event)

    # =============================================================================
    # Analysis Event Publishing
    # =============================================================================

    async def publish_analysis_result(
        self,
        analyzer_type: AnalysisType,
        symbol: str,
        timeframe: str,
        analysis_result: Dict[str, Any],
        score: float = 0.0,
        confidence: float = 0.0,
        processing_time_ms: float = 0.0,
        **kwargs
    ) -> str:
        """Publish analysis result event."""
        event = create_analysis_event(
            analyzer_type=analyzer_type,
            symbol=symbol,
            timeframe=timeframe,
            analysis_result=analysis_result,
            score=score,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            **kwargs
        )
        
        return await self._publish_event(event)

    async def publish_technical_analysis(
        self,
        symbol: str,
        timeframe: str,
        indicators: Dict[str, float],
        signals: Dict[str, str],
        trend_direction: str = "neutral",
        **kwargs
    ) -> str:
        """Publish technical analysis result."""
        event = TechnicalAnalysisEvent(
            symbol=symbol,
            timeframe=timeframe,
            indicators=indicators,
            signals=signals,
            trend_direction=trend_direction,
            analysis_result={
                'indicators': indicators,
                'signals': signals,
                'trend_direction': trend_direction
            },
            score=kwargs.get('score', 0.0),
            **kwargs
        )
        
        return await self._publish_event(event)

    async def publish_confluence_analysis(
        self,
        symbol: str,
        timeframe: str,
        confluence_score: float,
        dimension_scores: Dict[str, float],
        final_signal: SignalType,
        signal_strength: float,
        components: Dict[str, Dict[str, Any]],
        **kwargs
    ) -> str:
        """Publish confluence analysis result."""
        event = ConfluenceAnalysisEvent(
            symbol=symbol,
            timeframe=timeframe,
            confluence_score=confluence_score,
            dimension_scores=dimension_scores,
            final_signal=final_signal,
            signal_strength=signal_strength,
            components=components,
            analysis_result={
                'confluence_score': confluence_score,
                'dimension_scores': dimension_scores,
                'final_signal': final_signal.value,
                'signal_strength': signal_strength,
                'components': components
            },
            score=confluence_score,
            **kwargs
        )
        
        return await self._publish_event(event)

    # =============================================================================
    # Signal Event Publishing
    # =============================================================================

    async def publish_trading_signal(
        self,
        signal_type: SignalType,
        symbol: str,
        timeframe: str,
        price: float,
        confidence: float,
        strength: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_sources: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Publish trading signal event."""
        event = TradingSignalEvent(
            signal_type=signal_type,
            symbol=symbol,
            timeframe=timeframe,
            price=price,
            confidence=confidence,
            strength=strength,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_sources=signal_sources or [],
            **kwargs
        )
        
        return await self._publish_event(event)

    # =============================================================================
    # Alert Event Publishing
    # =============================================================================

    async def publish_system_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        component: str = "",
        **kwargs
    ) -> str:
        """Publish system alert event."""
        event = create_alert_event(
            alert_type=alert_type,
            severity=severity,
            message=message,
            component=component,
            title=title,
            **kwargs
        )
        
        return await self._publish_event(event)

    async def publish_performance_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
        **kwargs
    ) -> str:
        """Publish performance alert."""
        return await self.publish_system_alert(
            alert_type="performance",
            severity=severity,
            title=f"Performance Alert: {metric_name}",
            message=f"{metric_name} is {current_value}, threshold: {threshold_value}",
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            **kwargs
        )

    # =============================================================================
    # Component Status Events
    # =============================================================================

    async def publish_component_status(
        self,
        component_name: str,
        old_status: str,
        new_status: str,
        status_data: Optional[Dict[str, Any]] = None,
        health_score: float = 1.0,
        **kwargs
    ) -> str:
        """Publish component status change event."""
        event = ComponentStatusEvent(
            component_name=component_name,
            old_status=old_status,
            new_status=new_status,
            status_data=status_data or {},
            health_score=health_score,
            **kwargs
        )
        
        return await self._publish_event(event)

    # =============================================================================
    # Batch Publishing
    # =============================================================================

    async def publish_batch(self, events: List[Event]) -> List[str]:
        """Publish multiple events in a single batch."""
        if not events:
            return []
            
        # Enrich events
        enriched_events = []
        for event in events:
            enriched_event = await self._enrich_event(event)
            enriched_events.append(enriched_event)
            
        # Publish to event bus
        event_ids = await self.event_bus.publish_many(enriched_events)
        
        if self._metrics:
            self._metrics['events_published'] += len(event_ids)
            self._metrics['batch_count'] += 1
            self._update_avg_batch_size(len(event_ids))
            
        self._logger.debug(f"Published batch of {len(event_ids)} events")
        
        return event_ids

    # =============================================================================
    # Event Enrichment
    # =============================================================================

    def add_enrichment_callback(
        self,
        event_type: str,
        callback: Callable[[Event], Event]
    ):
        """Add event enrichment callback for specific event type."""
        if event_type not in self._enrichment_callbacks:
            self._enrichment_callbacks[event_type] = []
        self._enrichment_callbacks[event_type].append(callback)
        
        self._logger.debug(f"Added enrichment callback for {event_type}")

    def remove_enrichment_callback(
        self,
        event_type: str,
        callback: Callable[[Event], Event]
    ):
        """Remove event enrichment callback."""
        if event_type in self._enrichment_callbacks:
            try:
                self._enrichment_callbacks[event_type].remove(callback)
                if not self._enrichment_callbacks[event_type]:
                    del self._enrichment_callbacks[event_type]
            except ValueError:
                pass

    # =============================================================================
    # Metrics and Health
    # =============================================================================

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get publisher metrics."""
        if not self._metrics:
            return None
            
        return {
            **self._metrics,
            'pending_events': len(self._pending_events),
            'is_running': self._running,
            'batching_enabled': self.enable_batching
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        event_bus_health = await self.event_bus.health_check()
        
        return {
            'status': 'healthy' if self._running else 'stopped',
            'metrics': self.get_metrics(),
            'event_bus_health': event_bus_health,
            'enrichment_callbacks': len(self._enrichment_callbacks)
        }

    # =============================================================================
    # Internal Methods
    # =============================================================================

    async def _publish_event(self, event: Event) -> str:
        """Internal method to publish a single event."""
        start_time = time.time()
        
        try:
            # Enrich event
            enriched_event = await self._enrich_event(event)
            
            if self._metrics:
                self._metrics['events_created'] += 1
            
            # Handle batching
            if self.enable_batching:
                await self._add_to_batch(enriched_event)
                return enriched_event.event_id
            else:
                # Direct publish
                event_id = await self.event_bus.publish(enriched_event)
                
                if self._metrics:
                    self._metrics['events_published'] += 1
                    
                return event_id
                
        except Exception as e:
            if self._metrics:
                self._metrics['publish_errors'] += 1
                
            self._logger.error(f"Failed to publish event: {e}")
            raise
            
        finally:
            if self._metrics:
                publish_time = (time.time() - start_time) * 1000
                self._metrics['total_publish_time_ms'] += publish_time

    async def _enrich_event(self, event: Event) -> Event:
        """Enrich event with additional metadata and run callbacks."""
        start_time = time.time()
        
        try:
            # Add standard metadata
            if 'publisher' not in event.metadata:
                event.metadata['publisher'] = 'EventPublisher'
            if 'published_at' not in event.metadata:
                event.metadata['published_at'] = datetime.now(timezone.utc).isoformat()
                
            # Run enrichment callbacks
            if event.event_type in self._enrichment_callbacks:
                for callback in self._enrichment_callbacks[event.event_type]:
                    try:
                        event = callback(event)
                    except Exception as e:
                        self._logger.warning(f"Enrichment callback failed: {e}")
                        
            return event
            
        finally:
            if self._metrics:
                enrichment_time = (time.time() - start_time) * 1000
                self._metrics['enrichment_time_ms'] += enrichment_time

    async def _add_to_batch(self, event: Event):
        """Add event to batch for later processing."""
        async with self._batch_lock:
            self._pending_events.append(event)
            
            # Check if we should flush immediately
            if len(self._pending_events) >= self.batch_size:
                await self._flush_batch()

    async def _batch_processor(self):
        """Background task to process batched events."""
        while self._running:
            try:
                await asyncio.sleep(self.batch_timeout_ms / 1000)
                
                # Check if we have events to flush
                if self._pending_events and (
                    time.time() - self._last_batch_time > self.batch_timeout_ms / 1000
                ):
                    await self._flush_batch()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Batch processor error: {e}")

    async def _flush_batch(self):
        """Flush pending events to event bus."""
        async with self._batch_lock:
            if not self._pending_events:
                return
                
            events_to_publish = self._pending_events.copy()
            self._pending_events.clear()
            self._last_batch_time = time.time()
            
        # Publish outside the lock
        try:
            event_ids = await self.event_bus.publish_many(events_to_publish)
            
            if self._metrics:
                self._metrics['events_published'] += len(event_ids)
                self._metrics['batch_count'] += 1
                self._update_avg_batch_size(len(event_ids))
                
            self._logger.debug(f"Flushed batch of {len(event_ids)} events")
            
        except Exception as e:
            self._logger.error(f"Failed to flush batch: {e}")
            if self._metrics:
                self._metrics['publish_errors'] += len(events_to_publish)

    def _update_avg_batch_size(self, batch_size: int):
        """Update average batch size metric."""
        if self._metrics:
            current_avg = self._metrics['avg_batch_size']
            batch_count = self._metrics['batch_count']
            
            self._metrics['avg_batch_size'] = (
                (current_avg * (batch_count - 1) + batch_size) / batch_count
            )

    def _parse_timeframe_minutes(self, timeframe: str) -> int:
        """Parse timeframe string to minutes."""
        if not timeframe:
            return 1
            
        timeframe = timeframe.lower().strip()
        
        # Handle common formats
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 24 * 60
        elif timeframe.isdigit():
            return int(timeframe)
        else:
            # Default mappings
            mapping = {
                '1min': 1, '5min': 5, '15min': 15, '30min': 30,
                '1hour': 60, '4hour': 240, '1day': 1440
            }
            return mapping.get(timeframe, 1)