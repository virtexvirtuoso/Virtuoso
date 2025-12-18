from src.utils.task_tracker import create_tracked_task
"""
Confluence Analyzer Event-Driven Adapter

This module provides an event-driven adapter for the ConfluenceAnalyzer,
demonstrating how to migrate existing analyzers to the new event-driven
architecture while maintaining backward compatibility and performance.

The adapter:
- Subscribes to market data events from the EventBus
- Processes data through the existing ConfluenceAnalyzer
- Publishes analysis results as events
- Maintains the original analyzer's interface for backward compatibility
- Preserves all performance optimizations

This serves as a reference implementation for migrating other analyzers
to the event-driven pattern as outlined in Phase 1 of the architectural
improvement roadmap.
"""

from typing import Dict, List, Optional, Any, Callable, Set
import asyncio
import logging
import time
import json
from datetime import datetime, timedelta, timezone
from dataclasses import asdict
import traceback

from .event_bus import EventBus, Event, EventPriority
from .event_publisher import EventPublisher
from .event_types import (
    DataType, AnalysisType, SignalType,
    MarketDataUpdatedEvent, OHLCVDataEvent, ConfluenceAnalysisEvent,
    create_analysis_event
)
from ..interfaces.services import IAsyncDisposable


class ConfluenceEventAdapter(IAsyncDisposable):
    """
    Event-driven adapter for ConfluenceAnalyzer that demonstrates the migration
    pattern from synchronous to event-driven architecture.
    
    This adapter:
    1. Subscribes to relevant market data events
    2. Processes events through the existing ConfluenceAnalyzer
    3. Publishes results as analysis events
    4. Maintains backward compatibility with synchronous interface
    """
    
    def __init__(
        self,
        confluence_analyzer,
        event_bus: EventBus,
        event_publisher: EventPublisher,
        enable_event_processing: bool = True,
        enable_backward_compatibility: bool = True,
        processing_timeout_ms: int = 5000,
        batch_processing: bool = True
    ):
        self.confluence_analyzer = confluence_analyzer
        self.event_bus = event_bus
        self.event_publisher = event_publisher
        self.enable_event_processing = enable_event_processing
        self.enable_backward_compatibility = enable_backward_compatibility
        self.processing_timeout_ms = processing_timeout_ms
        self.batch_processing = batch_processing
        
        # Event subscription tracking
        self._subscription_ids: List[str] = []
        self._subscribed_symbols: Set[str] = set()
        self._subscribed_timeframes: Set[str] = set()
        
        # Data accumulation for batch processing
        self._pending_data: Dict[str, Dict[str, Any]] = {}  # symbol -> timeframe -> data
        self._batch_lock = asyncio.Lock()
        self._last_batch_process = {}  # symbol -> timeframe -> timestamp
        self._batch_timeout_s = 1.0  # Process batches after 1 second of inactivity
        
        # Performance tracking
        self._performance_metrics = {
            'events_processed': 0,
            'analysis_runs': 0,
            'avg_processing_time_ms': 0.0,
            'event_to_result_latency_ms': 0.0,
            'batch_sizes': [],
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Circuit breaker for resilience
        self._circuit_breaker = {
            'failure_count': 0,
            'failure_threshold': 5,
            'reset_timeout_s': 60,
            'last_failure_time': 0,
            'state': 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        }
        
        # Result caching to avoid duplicate processing
        self._result_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_s = 30
        
        self._logger = logging.getLogger(__name__)
        self._running = False
        self._batch_processor_task = None

    async def start(self):
        """Start the event-driven adapter."""
        if self._running:
            return
            
        self._running = True
        
        # Start event bus and publisher
        await self.event_bus.start()
        await self.event_publisher.start()
        
        # Subscribe to market data events if event processing is enabled
        if self.enable_event_processing:
            await self._setup_event_subscriptions()
            
        # Start batch processor if enabled
        if self.batch_processing:
            self._batch_processor_task = create_tracked_task(self._batch_processor(), name="auto_tracked_task")
            
        self._logger.info("ConfluenceEventAdapter started")

    async def stop(self):
        """Stop the adapter gracefully."""
        if not self._running:
            return
            
        self._running = False
        
        # Unsubscribe from events
        for subscription_id in self._subscription_ids:
            await self.event_bus.unsubscribe(subscription_id)
        self._subscription_ids.clear()
        
        # Stop batch processor
        if self._batch_processor_task:
            self._batch_processor_task.cancel()
            try:
                await self._batch_processor_task
            except asyncio.CancelledError:
                pass
                
        # Process any remaining batched data
        await self._process_all_pending_data()
        
        self._logger.info("ConfluenceEventAdapter stopped")

    async def dispose_async(self):
        """Cleanup resources."""
        await self.stop()
        self._pending_data.clear()
        self._result_cache.clear()
        self._subscribed_symbols.clear()
        self._subscribed_timeframes.clear()

    async def _setup_event_subscriptions(self):
        """Set up subscriptions to relevant market data events."""
        
        # Subscribe to OHLCV data events (primary input for confluence analysis)
        ohlcv_handler_id = await self.event_bus.subscribe(
            event_type="market_data.ohlcv",
            handler=self._handle_ohlcv_event,
            priority=10,  # High priority for market data processing
            circuit_breaker_config={
                'failure_threshold': self._circuit_breaker['failure_threshold'],
                'recovery_timeout': self._circuit_breaker['reset_timeout_s']
            }
        )
        self._subscription_ids.append(ohlcv_handler_id)
        
        # Subscribe to order book events for additional confluence factors
        orderbook_handler_id = await self.event_bus.subscribe(
            event_type="market_data.orderbook",
            handler=self._handle_orderbook_event,
            priority=5
        )
        self._subscription_ids.append(orderbook_handler_id)
        
        # Subscribe to trade events for volume analysis
        trades_handler_id = await self.event_bus.subscribe(
            event_type="market_data.trades",
            handler=self._handle_trades_event,
            priority=5
        )
        self._subscription_ids.append(trades_handler_id)
        
        self._logger.info(f"Set up {len(self._subscription_ids)} event subscriptions")

    async def _handle_ohlcv_event(self, event: Event):
        """Handle OHLCV data events - primary trigger for confluence analysis."""
        if not isinstance(event, OHLCVDataEvent):
            return
            
        start_time = time.time()
        
        try:
            symbol = event.symbol
            timeframe = event.timeframe
            
            self._subscribed_symbols.add(symbol)
            self._subscribed_timeframes.add(timeframe)
            
            if self.batch_processing:
                # Add to batch for processing
                await self._add_to_batch(symbol, timeframe, 'ohlcv', event)
            else:
                # Process immediately
                await self._process_confluence_analysis(symbol, timeframe, {'ohlcv': event})
                
            self._performance_metrics['events_processed'] += 1
            
        except Exception as e:
            await self._handle_processing_error(e, 'ohlcv_event', event)
            
        finally:
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics('event_processing', processing_time)

    async def _handle_orderbook_event(self, event: Event):
        """Handle order book events for liquidity analysis."""
        if not isinstance(event, MarketDataUpdatedEvent) or event.data_type != DataType.ORDERBOOK:
            return
            
        try:
            symbol = event.symbol
            
            if self.batch_processing:
                # Find matching timeframes and add to batch
                for timeframe in self._subscribed_timeframes:
                    await self._add_to_batch(symbol, timeframe, 'orderbook', event)
            else:
                # Process for all timeframes immediately (orderbook is timeframe-agnostic)
                for timeframe in self._subscribed_timeframes:
                    await self._process_confluence_analysis(symbol, timeframe, {'orderbook': event})
                    
            self._performance_metrics['events_processed'] += 1
            
        except Exception as e:
            await self._handle_processing_error(e, 'orderbook_event', event)

    async def _handle_trades_event(self, event: Event):
        """Handle trade events for volume and flow analysis."""
        if not isinstance(event, MarketDataUpdatedEvent) or event.data_type != DataType.TRADES:
            return
            
        try:
            symbol = event.symbol
            
            if self.batch_processing:
                for timeframe in self._subscribed_timeframes:
                    await self._add_to_batch(symbol, timeframe, 'trades', event)
            else:
                for timeframe in self._subscribed_timeframes:
                    await self._process_confluence_analysis(symbol, timeframe, {'trades': event})
                    
            self._performance_metrics['events_processed'] += 1
            
        except Exception as e:
            await self._handle_processing_error(e, 'trades_event', event)

    async def _add_to_batch(self, symbol: str, timeframe: str, data_type: str, event: Event):
        """Add event data to batch for processing."""
        async with self._batch_lock:
            key = f"{symbol}:{timeframe}"
            
            if key not in self._pending_data:
                self._pending_data[key] = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'data': {},
                    'last_update': time.time()
                }
                
            self._pending_data[key]['data'][data_type] = event
            self._pending_data[key]['last_update'] = time.time()

    async def _batch_processor(self):
        """Background task to process batched data."""
        while self._running:
            try:
                await asyncio.sleep(0.5)  # Check every 500ms
                
                current_time = time.time()
                keys_to_process = []
                
                async with self._batch_lock:
                    for key, batch_data in self._pending_data.items():
                        # Process if batch is old enough or has OHLCV data (primary trigger)
                        time_since_update = current_time - batch_data['last_update']
                        has_ohlcv = 'ohlcv' in batch_data['data']
                        
                        if time_since_update >= self._batch_timeout_s or has_ohlcv:
                            keys_to_process.append(key)
                
                # Process batches outside the lock
                for key in keys_to_process:
                    await self._process_batch(key)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Batch processor error: {e}")

    async def _process_batch(self, key: str):
        """Process a single batch of accumulated data."""
        async with self._batch_lock:
            if key not in self._pending_data:
                return
                
            batch_data = self._pending_data.pop(key)
            
        symbol = batch_data['symbol']
        timeframe = batch_data['timeframe']
        data = batch_data['data']
        
        try:
            await self._process_confluence_analysis(symbol, timeframe, data)
            
            # Update batch size metrics
            batch_size = len(data)
            self._performance_metrics['batch_sizes'].append(batch_size)
            
            # Keep only last 100 batch sizes for memory efficiency
            if len(self._performance_metrics['batch_sizes']) > 100:
                self._performance_metrics['batch_sizes'] = self._performance_metrics['batch_sizes'][-100:]
                
        except Exception as e:
            await self._handle_processing_error(e, f'batch_processing:{key}', batch_data)

    async def _process_confluence_analysis(
        self,
        symbol: str,
        timeframe: str,
        event_data: Dict[str, Event]
    ):
        """Process confluence analysis with event data."""
        start_time = time.time()
        
        try:
            # Check circuit breaker
            if self._circuit_breaker['state'] == 'OPEN':
                if time.time() - self._circuit_breaker['last_failure_time'] > self._circuit_breaker['reset_timeout_s']:
                    self._circuit_breaker['state'] = 'HALF_OPEN'
                else:
                    self._logger.debug(f"Circuit breaker OPEN for {symbol}:{timeframe}")
                    return
                    
            # Check cache first
            cache_key = f"{symbol}:{timeframe}:{hash(str(sorted(event_data.keys())))}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self._performance_metrics['cache_hits'] += 1
                await self._publish_analysis_result(cached_result)
                return
            else:
                self._performance_metrics['cache_misses'] += 1
                
            # Convert event data to format expected by ConfluenceAnalyzer
            market_data = await self._convert_events_to_market_data(symbol, timeframe, event_data)
            
            if not market_data:
                self._logger.debug(f"No market data available for {symbol}:{timeframe}")
                return
                
            # Run confluence analysis with timeout
            analysis_task = create_tracked_task(
                self._run_confluence_analysis(symbol, timeframe, market_data, name="auto_tracked_task")
            )
            
            try:
                result = await asyncio.wait_for(
                    analysis_task, 
                    timeout=self.processing_timeout_ms / 1000
                )
                
                # Cache successful result
                self._cache_result(cache_key, result)
                
                # Publish analysis result as event
                await self._publish_analysis_result(result)
                
                # Reset circuit breaker on success
                self._circuit_breaker['failure_count'] = 0
                self._circuit_breaker['state'] = 'CLOSED'
                
                self._performance_metrics['analysis_runs'] += 1
                
            except asyncio.TimeoutError:
                self._logger.warning(f"Analysis timeout for {symbol}:{timeframe}")
                analysis_task.cancel()
                raise
                
        except Exception as e:
            await self._handle_processing_error(e, f'confluence_analysis:{symbol}:{timeframe}', event_data)
            
        finally:
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics('confluence_analysis', processing_time)

    async def _convert_events_to_market_data(
        self,
        symbol: str,
        timeframe: str,
        event_data: Dict[str, Event]
    ) -> Optional[Dict[str, Any]]:
        """Convert event data to format expected by ConfluenceAnalyzer."""
        market_data = {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now(timezone.utc),
            'data': {}
        }
        
        try:
            # Process OHLCV data (primary requirement)
            if 'ohlcv' in event_data:
                ohlcv_event = event_data['ohlcv']
                if hasattr(ohlcv_event, 'candles') and ohlcv_event.candles is not None:
                    market_data['data']['ohlcv'] = ohlcv_event.candles
                elif 'candles' in ohlcv_event.raw_data:
                    market_data['data']['ohlcv'] = ohlcv_event.raw_data['candles']
                else:
                    market_data['data']['ohlcv'] = ohlcv_event.raw_data
                    
            # Process order book data
            if 'orderbook' in event_data:
                orderbook_event = event_data['orderbook']
                market_data['data']['orderbook'] = {
                    'bids': orderbook_event.raw_data.get('bids', []),
                    'asks': orderbook_event.raw_data.get('asks', [])
                }
                
            # Process trades data
            if 'trades' in event_data:
                trades_event = event_data['trades']
                market_data['data']['trades'] = trades_event.raw_data.get('trades', [])
                
            # Ensure we have at least OHLCV data
            if 'ohlcv' not in market_data['data']:
                return None
                
            return market_data
            
        except Exception as e:
            self._logger.error(f"Error converting event data: {e}")
            return None

    async def _run_confluence_analysis(
        self,
        symbol: str,
        timeframe: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run the actual confluence analysis."""
        try:
            # Call the original ConfluenceAnalyzer
            analyzer = getattr(self, 'confluence_analyzer', None)
            if analyzer and hasattr(analyzer, 'analyze') and callable(getattr(analyzer, 'analyze')):
                # Async analyzer
                try:
                    result = await analyzer.analyze(market_data)
                except Exception as e:
                    logger.debug(f"confluence_analyzer.analyze error: {e}")
                    return None
            elif hasattr(self.confluence_analyzer, 'run_analysis'):
                # Sync analyzer - run in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.confluence_analyzer.run_analysis,
                    market_data
                )
            else:
                raise AttributeError("ConfluenceAnalyzer missing analyze or run_analysis method")
                
            # Ensure result has required fields
            if not isinstance(result, dict):
                result = {'raw_result': result}
                
            # Add metadata
            result.update({
                'symbol': symbol,
                'timeframe': timeframe,
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'adapter_version': '1.0.0'
            })
            
            return result
            
        except Exception as e:
            self._logger.error(f"ConfluenceAnalyzer execution error: {e}")
            raise

    async def _publish_analysis_result(self, result: Dict[str, Any]):
        """Publish confluence analysis result as event."""
        try:
            # Extract key metrics from result
            confluence_score = result.get('confluence_score', 0.0)
            dimension_scores = result.get('dimension_scores', {})
            components = result.get('components', {})
            
            # Determine signal type from score
            signal_type = SignalType.NEUTRAL
            if confluence_score > 60:
                signal_type = SignalType.LONG
            elif confluence_score < 40:
                signal_type = SignalType.SHORT
                
            signal_strength = abs(confluence_score - 50) / 50  # 0-1 scale
            
            # Publish confluence analysis event
            await self.event_publisher.publish_confluence_analysis(
                symbol=result.get('symbol', ''),
                timeframe=result.get('timeframe', ''),
                confluence_score=confluence_score,
                dimension_scores=dimension_scores,
                final_signal=signal_type,
                signal_strength=signal_strength,
                components=components,
                confidence=result.get('confidence', signal_strength),
                processing_time_ms=result.get('processing_time_ms', 0)
            )
            
        except Exception as e:
            self._logger.error(f"Failed to publish analysis result: {e}")
            raise

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result if still valid."""
        if cache_key not in self._result_cache:
            return None
            
        cached_data = self._result_cache[cache_key]
        if time.time() - cached_data['timestamp'] > self._cache_ttl_s:
            del self._result_cache[cache_key]
            return None
            
        return cached_data['result']

    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache analysis result."""
        self._result_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Clean old cache entries
        current_time = time.time()
        keys_to_remove = [
            k for k, v in self._result_cache.items()
            if current_time - v['timestamp'] > self._cache_ttl_s
        ]
        for k in keys_to_remove:
            del self._result_cache[k]

    async def _handle_processing_error(self, error: Exception, context: str, data: Any):
        """Handle processing errors with circuit breaker logic."""
        self._performance_metrics['error_count'] += 1
        
        # Update circuit breaker
        self._circuit_breaker['failure_count'] += 1
        self._circuit_breaker['last_failure_time'] = time.time()
        
        if self._circuit_breaker['failure_count'] >= self._circuit_breaker['failure_threshold']:
            self._circuit_breaker['state'] = 'OPEN'
            self._logger.warning(f"Circuit breaker OPEN after {self._circuit_breaker['failure_count']} failures")
            
        self._logger.error(f"Processing error in {context}: {error}\n{traceback.format_exc()}")
        
        # Publish error alert
        try:
            await self.event_publisher.publish_system_alert(
                alert_type="analysis_error",
                severity="error" if self._circuit_breaker['state'] != 'OPEN' else "critical",
                title=f"ConfluenceAnalyzer Error in {context}",
                message=str(error),
                component="ConfluenceEventAdapter",
                error_details={'context': context, 'error': str(error)}
            )
        except:
            pass  # Don't let alert publishing errors cascade

    def _update_performance_metrics(self, operation: str, time_ms: float):
        """Update performance metrics."""
        if operation == 'event_processing':
            current_avg = self._performance_metrics['event_to_result_latency_ms']
            count = self._performance_metrics['events_processed']
        else:  # confluence_analysis
            current_avg = self._performance_metrics['avg_processing_time_ms']
            count = self._performance_metrics['analysis_runs']
            
        if count > 0:
            new_avg = ((current_avg * (count - 1)) + time_ms) / count
            
            if operation == 'event_processing':
                self._performance_metrics['event_to_result_latency_ms'] = new_avg
            else:
                self._performance_metrics['avg_processing_time_ms'] = new_avg

    async def _process_all_pending_data(self):
        """Process all remaining batched data during shutdown."""
        async with self._batch_lock:
            keys_to_process = list(self._pending_data.keys())
            
        for key in keys_to_process:
            try:
                await self._process_batch(key)
            except Exception as e:
                self._logger.error(f"Error processing pending batch {key}: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        avg_batch_size = (
            sum(self._performance_metrics['batch_sizes']) / len(self._performance_metrics['batch_sizes'])
            if self._performance_metrics['batch_sizes'] else 0
        )
        
        return {
            **self._performance_metrics,
            'avg_batch_size': avg_batch_size,
            'subscribed_symbols': len(self._subscribed_symbols),
            'subscribed_timeframes': len(self._subscribed_timeframes),
            'pending_batches': len(self._pending_data),
            'cache_size': len(self._result_cache),
            'circuit_breaker_state': self._circuit_breaker['state'],
            'success_rate': (
                (self._performance_metrics['analysis_runs'] - self._performance_metrics['error_count']) /
                max(self._performance_metrics['analysis_runs'], 1)
            )
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'healthy' if self._running else 'stopped',
            'event_processing_enabled': self.enable_event_processing,
            'subscriptions_active': len(self._subscription_ids),
            'circuit_breaker_state': self._circuit_breaker['state'],
            'performance_metrics': self.get_performance_metrics(),
            'analyzer_available': self.confluence_analyzer is not None
        }

    # =============================================================================
    # Backward Compatibility Interface
    # =============================================================================

    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Backward compatibility method that maintains the original synchronous interface
        while optionally publishing results as events.
        """
        if not self.enable_backward_compatibility:
            raise NotImplementedError("Backward compatibility disabled")
            
        try:
            # Run analysis through the original analyzer
            analyzer = getattr(self, 'confluence_analyzer', None)
            if analyzer and hasattr(analyzer, 'analyze') and callable(getattr(analyzer, 'analyze')):
                try:
                    result = await analyzer.analyze(market_data)
                except Exception as e:
                    logger.debug(f"confluence_analyzer.analyze error: {e}")
                    return None
            elif hasattr(self.confluence_analyzer, 'run_analysis'):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.confluence_analyzer.run_analysis,
                    market_data
                )
            else:
                raise AttributeError("ConfluenceAnalyzer missing required methods")
                
            # Optionally publish result as event
            if self.enable_event_processing and self._running:
                try:
                    await self._publish_analysis_result(result)
                except Exception as e:
                    self._logger.warning(f"Failed to publish compatibility result: {e}")
                    
            return result
            
        except Exception as e:
            self._logger.error(f"Backward compatibility analysis failed: {e}")
            raise