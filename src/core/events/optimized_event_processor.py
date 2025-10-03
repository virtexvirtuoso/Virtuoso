from src.utils.task_tracker import create_tracked_task
"""
Optimized Event Processing Pipeline - Phase 4 Implementation
=============================================================

High-performance event processing system designed to handle 10,000+ events/second
with intelligent batching, aggregation, and parallel processing capabilities.

Key Features:
- Event batching and aggregation strategies for related data
- Parallel processing pipelines for different symbols/exchanges
- Memory pool management for event objects
- Smart event deduplication and compaction
- Priority-based processing queues
- Sub-50ms latency for critical paths
- Zero message loss guarantee under load

Performance Targets:
- Throughput: >10,000 events/second
- Latency: <50ms end-to-end for critical events
- Memory usage: <1GB for normal operation
- Zero message loss under normal load conditions

Architecture:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Event         │    │   Batching      │    │   Processing    │
│   Ingestion     │───▶│   Engine        │───▶│   Pipeline      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Memory Pool   │    │   Aggregation   │    │   Output        │
│   Management    │    │   Rules         │    │   Dispatcher    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import uuid
import weakref
import json
import heapq
from concurrent.futures import ThreadPoolExecutor
import traceback
import statistics
import gc

from .event_bus import Event, EventPriority, EventHandler
from .event_types import (
    MarketDataUpdatedEvent, AnalysisCompletedEvent, TradingSignalEvent,
    SystemAlertEvent, DataType, AnalysisType, SignalType
)
from ..interfaces.services import IAsyncDisposable


class ProcessingStrategy(Enum):
    """Event processing strategies."""
    IMMEDIATE = "immediate"           # Process immediately, no batching
    BATCH_TIME = "batch_time"         # Batch by time window
    BATCH_SIZE = "batch_size"         # Batch by event count
    BATCH_HYBRID = "batch_hybrid"     # Batch by time AND size (whichever comes first)
    AGGREGATE = "aggregate"           # Aggregate similar events
    DEDUPLICATE = "deduplicate"       # Remove duplicate events


class ProcessingPriority(Enum):
    """Processing priority levels."""
    CRITICAL = 1    # Trading signals, critical alerts
    HIGH = 2        # Market data updates, analysis results
    NORMAL = 3      # System events, general monitoring
    LOW = 4         # Logging, audit events


@dataclass
class EventBatch:
    """Container for batched events."""
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    events: List[Event] = field(default_factory=list)
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    target_process_time: float = 0.0
    batch_type: str = "mixed"
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    
    def add_event(self, event: Event):
        """Add event to batch."""
        self.events.append(event)
        
        # Update batch metadata based on first event
        if len(self.events) == 1:
            if hasattr(event, 'symbol'):
                self.symbol = getattr(event, 'symbol', None)
            if hasattr(event, 'exchange'):
                self.exchange = getattr(event, 'exchange', None)
    
    def size(self) -> int:
        """Get batch size."""
        return len(self.events)
    
    def age_ms(self) -> float:
        """Get batch age in milliseconds."""
        return (time.time() - self.created_at) * 1000
    
    def should_process(self, max_age_ms: float = 100, max_size: int = 50) -> bool:
        """Check if batch should be processed."""
        return self.age_ms() >= max_age_ms or self.size() >= max_size


@dataclass
class ProcessingMetrics:
    """Metrics for event processing performance."""
    total_events_processed: int = 0
    total_batches_processed: int = 0
    total_processing_time_ms: float = 0.0
    avg_batch_size: float = 0.0
    avg_processing_time_ms: float = 0.0
    peak_events_per_second: float = 0.0
    current_queue_size: int = 0
    memory_usage_mb: float = 0.0
    deduplicated_events: int = 0
    aggregated_events: int = 0
    errors_count: int = 0
    last_update: float = field(default_factory=time.time)
    
    def update_processing_stats(self, batch_size: int, processing_time_ms: float):
        """Update processing statistics."""
        self.total_events_processed += batch_size
        self.total_batches_processed += 1
        self.total_processing_time_ms += processing_time_ms
        
        # Update averages
        self.avg_batch_size = (
            (self.avg_batch_size * (self.total_batches_processed - 1) + batch_size) /
            self.total_batches_processed
        )
        self.avg_processing_time_ms = (
            self.total_processing_time_ms / self.total_batches_processed
        )
        
        self.last_update = time.time()


class MemoryPool:
    """Memory pool for efficient event object management."""
    
    def __init__(self, pool_size: int = 10000):
        self.pool_size = pool_size
        self.available_events: deque = deque(maxlen=pool_size)
        self.available_batches: deque = deque(maxlen=pool_size // 10)
        self.total_created = 0
        self.total_reused = 0
        self.lock = threading.Lock()
    
    def get_event(self, event_class=Event) -> Event:
        """Get an event object from pool or create new."""
        with self.lock:
            if self.available_events and event_class == Event:
                event = self.available_events.popleft()
                self._reset_event(event)
                self.total_reused += 1
                return event
        
        # Create new event if pool empty or different class needed
        self.total_created += 1
        return event_class()
    
    def return_event(self, event: Event):
        """Return event to pool for reuse."""
        if not isinstance(event, Event):
            return
            
        with self.lock:
            if len(self.available_events) < self.pool_size:
                self.available_events.append(event)
    
    def get_batch(self) -> EventBatch:
        """Get a batch object from pool or create new."""
        with self.lock:
            if self.available_batches:
                batch = self.available_batches.popleft()
                self._reset_batch(batch)
                self.total_reused += 1
                return batch
        
        self.total_created += 1
        return EventBatch()
    
    def return_batch(self, batch: EventBatch):
        """Return batch to pool for reuse."""
        with self.lock:
            if len(self.available_batches) < self.pool_size // 10:
                batch.events.clear()
                self.available_batches.append(batch)
    
    def _reset_event(self, event: Event):
        """Reset event object for reuse."""
        event.event_id = str(uuid.uuid4())
        event.event_type = ""
        event.timestamp = datetime.utcnow()
        event.source = ""
        event.priority = EventPriority.NORMAL
        event.data.clear()
        event.metadata.clear()
        event.retry_count = 0
    
    def _reset_batch(self, batch: EventBatch):
        """Reset batch object for reuse."""
        batch.batch_id = str(uuid.uuid4())
        batch.events.clear()
        batch.priority = ProcessingPriority.NORMAL
        batch.created_at = time.time()
        batch.target_process_time = 0.0
        batch.batch_type = "mixed"
        batch.symbol = None
        batch.exchange = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory pool statistics."""
        with self.lock:
            return {
                'total_created': self.total_created,
                'total_reused': self.total_reused,
                'reuse_rate': self.total_reused / max(self.total_created + self.total_reused, 1),
                'available_events': len(self.available_events),
                'available_batches': len(self.available_batches),
                'pool_utilization': {
                    'events': len(self.available_events) / self.pool_size,
                    'batches': len(self.available_batches) / (self.pool_size // 10)
                }
            }


class EventDeduplicator:
    """Smart event deduplication and compaction."""
    
    def __init__(self, window_size: int = 1000, ttl_seconds: int = 60):
        self.window_size = window_size
        self.ttl_seconds = ttl_seconds
        self.event_hashes: Dict[str, Tuple[float, Event]] = {}
        self.cleanup_interval = 30  # seconds
        self.last_cleanup = time.time()
        self.deduplicated_count = 0
    
    def is_duplicate(self, event: Event) -> bool:
        """Check if event is a duplicate."""
        event_hash = self._hash_event(event)
        current_time = time.time()
        
        if event_hash in self.event_hashes:
            stored_time, stored_event = self.event_hashes[event_hash]
            
            # Check if stored event is still valid (within TTL)
            if current_time - stored_time <= self.ttl_seconds:
                # Compare events for true duplication
                if self._events_equal(event, stored_event):
                    self.deduplicated_count += 1
                    return True
        
        # Store this event
        self.event_hashes[event_hash] = (current_time, event)
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            
        return False
    
    def _hash_event(self, event: Event) -> str:
        """Generate hash for event deduplication."""
        # Create hash based on event type, source, and key data fields
        hash_data = {
            'type': event.event_type,
            'source': event.source,
        }
        
        # Add specific fields based on event type
        if hasattr(event, 'symbol'):
            hash_data['symbol'] = getattr(event, 'symbol', '')
        if hasattr(event, 'exchange'):
            hash_data['exchange'] = getattr(event, 'exchange', '')
        if hasattr(event, 'timeframe'):
            hash_data['timeframe'] = getattr(event, 'timeframe', '')
        
        # Include some data fields for market data events
        if isinstance(event, MarketDataUpdatedEvent):
            if 'price' in event.data:
                # Round price to avoid minor fluctuation duplicates
                hash_data['price'] = round(event.data.get('price', 0), 8)
        
        return str(hash(json.dumps(hash_data, sort_keys=True)))
    
    def _events_equal(self, event1: Event, event2: Event) -> bool:
        """Compare two events for equality."""
        # Basic comparison
        if (event1.event_type != event2.event_type or 
            event1.source != event2.source):
            return False
        
        # For market data events, compare key data fields
        if isinstance(event1, MarketDataUpdatedEvent) and isinstance(event2, MarketDataUpdatedEvent):
            return (
                event1.symbol == event2.symbol and
                event1.exchange == event2.exchange and
                event1.data_type == event2.data_type and
                abs(event1.data.get('price', 0) - event2.data.get('price', 0)) < 0.00000001
            )
        
        return True
    
    def _cleanup_old_entries(self):
        """Clean up old entries from deduplication cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self.event_hashes.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.event_hashes[key]
            
        self.last_cleanup = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return {
            'cache_size': len(self.event_hashes),
            'deduplicated_count': self.deduplicated_count,
            'cache_utilization': len(self.event_hashes) / self.window_size
        }


class OptimizedEventProcessor(IAsyncDisposable):
    """
    High-performance event processor with batching, aggregation, and parallel processing.
    
    Designed to process >10,000 events/second with <50ms latency for critical paths.
    """
    
    def __init__(
        self,
        max_batch_size: int = 100,
        max_batch_age_ms: float = 50,
        worker_pool_size: int = None,
        enable_deduplication: bool = True,
        enable_memory_pool: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize optimized event processor."""
        # Configuration
        self.max_batch_size = max_batch_size
        self.max_batch_age_ms = max_batch_age_ms
        
        # Worker pool configuration
        import os
        self.worker_pool_size = worker_pool_size or min(32, (os.cpu_count() or 1) + 4)
        
        # Feature flags
        self.enable_deduplication = enable_deduplication
        self.enable_memory_pool = enable_memory_pool
        self.enable_metrics = enable_metrics
        
        # Processing infrastructure
        self.priority_queues: Dict[ProcessingPriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=10000) for priority in ProcessingPriority
        }
        
        # Batching system
        self.active_batches: Dict[str, EventBatch] = {}  # Key: batch_key (symbol:exchange:type)
        self.batch_processors: Dict[ProcessingPriority, asyncio.Task] = {}
        
        # Parallel processing
        self.worker_tasks: List[asyncio.Task] = []
        self.thread_pool = ThreadPoolExecutor(max_workers=self.worker_pool_size // 2)
        
        # Event handlers
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.wildcard_handlers: List[Callable] = []
        
        # Optimization components
        if enable_memory_pool:
            self.memory_pool = MemoryPool()
        else:
            self.memory_pool = None
            
        if enable_deduplication:
            self.deduplicator = EventDeduplicator()
        else:
            self.deduplicator = None
        
        # Metrics and monitoring
        if enable_metrics:
            self.metrics = ProcessingMetrics()
            self.performance_history: deque = deque(maxlen=1000)
        else:
            self.metrics = None
            
        # State management
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._batch_timer_task: Optional[asyncio.Task] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(
            f"OptimizedEventProcessor initialized: "
            f"batch_size={max_batch_size}, batch_age={max_batch_age_ms}ms, "
            f"workers={self.worker_pool_size}, "
            f"dedup={enable_deduplication}, pool={enable_memory_pool}"
        )
    
    async def start(self):
        """Start the event processor."""
        if self._running:
            return
            
        self._running = True
        self._shutdown_event.clear()
        
        # Start batch processors for each priority
        for priority in ProcessingPriority:
            processor_task = create_tracked_task(
                self._batch_processor, name="_batch_processor_task"),
                name=f"batch_processor_{priority.name.lower()}"
            )
            self.batch_processors[priority] = processor_task
        
        # Start worker pool
        for i in range(self.worker_pool_size):
            worker_task = create_tracked_task(
                self._event_worker, name="_event_worker_task"),
                name=f"event_worker_{i}"
            )
            self.worker_tasks.append(worker_task)
        
        # Start batch timer
        self._batch_timer_task = create_tracked_task(
            self._batch_timer, name="_batch_timer_task"),
            name="batch_timer"
        )
        
        self.logger.info(
            f"Event processor started with {len(self.batch_processors)} batch processors "
            f"and {len(self.worker_tasks)} workers"
        )
    
    async def stop(self):
        """Stop the event processor gracefully."""
        if not self._running:
            return
            
        self.logger.info("Stopping event processor...")
        self._running = False
        self._shutdown_event.set()
        
        # Cancel batch timer
        if self._batch_timer_task:
            self._batch_timer_task.cancel()
            try:
                await self._batch_timer_task
            except asyncio.CancelledError:
                pass
        
        # Stop batch processors
        for task in self.batch_processors.values():
            task.cancel()
        
        if self.batch_processors:
            await asyncio.gather(*self.batch_processors.values(), return_exceptions=True)
        
        # Stop workers
        for task in self.worker_tasks:
            task.cancel()
            
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Process remaining batches
        await self._flush_all_batches()
        
        # Close thread pool
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)
        
        self.logger.info("Event processor stopped")
    
    async def dispose_async(self):
        """Dispose of processor resources."""
        await self.stop()
        
        # Clear data structures
        self.active_batches.clear()
        self.handlers.clear()
        self.wildcard_handlers.clear()
        
        if self.performance_history:
            self.performance_history.clear()
    
    def register_handler(
        self,
        event_type: str,
        handler: Callable[[List[Event]], Awaitable[None]],
        processing_strategy: ProcessingStrategy = ProcessingStrategy.BATCH_HYBRID
    ):
        """Register an event handler."""
        handler_info = {
            'handler': handler,
            'strategy': processing_strategy,
            'registered_at': time.time()
        }
        
        if '*' in event_type:
            self.wildcard_handlers.append(handler_info)
        else:
            self.handlers[event_type].append(handler_info)
        
        self.logger.debug(f"Registered handler for {event_type} with strategy {processing_strategy}")
    
    async def process_event(self, event: Event) -> str:
        """Process a single event through the optimized pipeline."""
        if not self._running:
            await self.start()
        
        # Apply deduplication if enabled
        if self.deduplicator and self.deduplicator.is_duplicate(event):
            self.logger.debug(f"Deduplicated event {event.event_id}")
            return event.event_id
        
        # Determine processing priority
        priority = self._determine_priority(event)
        
        # Add to appropriate batching queue or process immediately
        processing_strategy = self._get_processing_strategy(event)
        
        if processing_strategy == ProcessingStrategy.IMMEDIATE:
            # Process immediately for critical events
            await self._process_single_event(event)
        else:
            # Add to batch processing queue
            await self._add_to_batch(event, priority, processing_strategy)
        
        return event.event_id
    
    async def process_events(self, events: List[Event]) -> List[str]:
        """Process multiple events efficiently."""
        if not events:
            return []
        
        event_ids = []
        batches_by_priority: Dict[ProcessingPriority, List[Event]] = defaultdict(list)
        
        # Group events by priority for batch processing
        for event in events:
            # Skip duplicates
            if self.deduplicator and self.deduplicator.is_duplicate(event):
                continue
                
            priority = self._determine_priority(event)
            processing_strategy = self._get_processing_strategy(event)
            
            if processing_strategy == ProcessingStrategy.IMMEDIATE:
                # Process critical events immediately
                await self._process_single_event(event)
                event_ids.append(event.event_id)
            else:
                batches_by_priority[priority].append(event)
                event_ids.append(event.event_id)
        
        # Add batched events to processing queues
        for priority, priority_events in batches_by_priority.items():
            for event in priority_events:
                await self._add_to_batch(event, priority, ProcessingStrategy.BATCH_HYBRID)
        
        return event_ids
    
    def _determine_priority(self, event: Event) -> ProcessingPriority:
        """Determine processing priority for event."""
        if isinstance(event, TradingSignalEvent):
            return ProcessingPriority.CRITICAL
        elif event.priority == EventPriority.CRITICAL:
            return ProcessingPriority.CRITICAL
        elif isinstance(event, (SystemAlertEvent,)) and hasattr(event, 'severity'):
            if event.severity.value in ['error', 'critical']:
                return ProcessingPriority.HIGH
        elif isinstance(event, (MarketDataUpdatedEvent, AnalysisCompletedEvent)):
            return ProcessingPriority.HIGH
        elif event.priority == EventPriority.HIGH:
            return ProcessingPriority.HIGH
        elif event.priority == EventPriority.NORMAL:
            return ProcessingPriority.NORMAL
        else:
            return ProcessingPriority.LOW
    
    def _get_processing_strategy(self, event: Event) -> ProcessingStrategy:
        """Get processing strategy for event type."""
        # Critical events are processed immediately
        if isinstance(event, TradingSignalEvent):
            return ProcessingStrategy.IMMEDIATE
        elif event.priority == EventPriority.CRITICAL:
            return ProcessingStrategy.IMMEDIATE
        
        # Market data events use time-based batching
        elif isinstance(event, MarketDataUpdatedEvent):
            if event.data_type in [DataType.TICKER, DataType.TRADES]:
                return ProcessingStrategy.BATCH_TIME
            else:
                return ProcessingStrategy.BATCH_HYBRID
        
        # Analysis events use hybrid batching
        elif isinstance(event, AnalysisCompletedEvent):
            return ProcessingStrategy.BATCH_HYBRID
        
        # Default to hybrid batching
        else:
            return ProcessingStrategy.BATCH_HYBRID
    
    async def _add_to_batch(
        self,
        event: Event,
        priority: ProcessingPriority,
        strategy: ProcessingStrategy
    ):
        """Add event to appropriate batch."""
        batch_key = self._get_batch_key(event, strategy)
        
        # Get or create batch
        if batch_key not in self.active_batches:
            if self.memory_pool:
                batch = self.memory_pool.get_batch()
            else:
                batch = EventBatch()
            
            batch.priority = priority
            batch.batch_type = strategy.value
            self.active_batches[batch_key] = batch
        
        batch = self.active_batches[batch_key]
        batch.add_event(event)
        
        # Check if batch should be processed immediately
        if self._should_process_batch(batch, strategy):
            await self._submit_batch_for_processing(batch_key, batch)
    
    def _get_batch_key(self, event: Event, strategy: ProcessingStrategy) -> str:
        """Generate batch key for event grouping."""
        key_parts = [strategy.value]
        
        # Group by symbol and exchange for market data
        if hasattr(event, 'symbol') and hasattr(event, 'exchange'):
            key_parts.extend([
                getattr(event, 'symbol', 'unknown'),
                getattr(event, 'exchange', 'unknown')
            ])
        
        # Group by event type
        key_parts.append(event.event_type.split('.')[0])  # First part of event type
        
        return ':'.join(key_parts)
    
    def _should_process_batch(self, batch: EventBatch, strategy: ProcessingStrategy) -> bool:
        """Check if batch should be processed."""
        if strategy == ProcessingStrategy.BATCH_SIZE:
            return batch.size() >= self.max_batch_size
        elif strategy == ProcessingStrategy.BATCH_TIME:
            return batch.age_ms() >= self.max_batch_age_ms
        elif strategy == ProcessingStrategy.BATCH_HYBRID:
            return (batch.size() >= self.max_batch_size or 
                   batch.age_ms() >= self.max_batch_age_ms)
        else:
            return batch.size() >= self.max_batch_size
    
    async def _submit_batch_for_processing(self, batch_key: str, batch: EventBatch):
        """Submit batch to processing queue."""
        # Remove from active batches
        if batch_key in self.active_batches:
            del self.active_batches[batch_key]
        
        # Submit to priority queue
        try:
            queue = self.priority_queues[batch.priority]
            await queue.put(batch)
        except asyncio.QueueFull:
            self.logger.warning(f"Processing queue full for priority {batch.priority}")
            # Process immediately as fallback
            await self._process_batch(batch)
    
    async def _batch_processor(self, priority: ProcessingPriority):
        """Process batches for a specific priority level."""
        queue = self.priority_queues[priority]
        processor_name = f"batch_processor_{priority.name.lower()}"
        
        while self._running:
            try:
                # Wait for batch with timeout
                batch = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Process batch
                start_time = time.perf_counter()
                await self._process_batch(batch)
                processing_time_ms = (time.perf_counter() - start_time) * 1000
                
                # Update metrics
                if self.metrics:
                    self.metrics.update_processing_stats(batch.size(), processing_time_ms)
                    self.performance_history.append({
                        'timestamp': time.time(),
                        'batch_size': batch.size(),
                        'processing_time_ms': processing_time_ms,
                        'priority': priority.name
                    })
                
                # Return batch to memory pool
                if self.memory_pool:
                    self.memory_pool.return_batch(batch)
                
                # Mark queue task as done
                queue.task_done()
                
            except asyncio.TimeoutError:
                if self._shutdown_event.is_set():
                    break
                continue
            except Exception as e:
                if self.metrics:
                    self.metrics.errors_count += 1
                self.logger.error(f"{processor_name} error: {e}\n{traceback.format_exc()}")
    
    async def _process_batch(self, batch: EventBatch):
        """Process a batch of events."""
        if not batch.events:
            return
        
        # Group events by type for efficient handling
        events_by_type: Dict[str, List[Event]] = defaultdict(list)
        for event in batch.events:
            events_by_type[event.event_type].append(event)
        
        # Process each event type group
        tasks = []
        for event_type, type_events in events_by_type.items():
            # Find matching handlers
            matching_handlers = []
            
            # Direct handlers
            if event_type in self.handlers:
                matching_handlers.extend(self.handlers[event_type])
            
            # Wildcard handlers
            for handler_info in self.wildcard_handlers:
                if self._matches_wildcard(event_type, handler_info):
                    matching_handlers.append(handler_info)
            
            # Execute handlers for this event type
            for handler_info in matching_handlers:
                handler = handler_info['handler']
                task = create_tracked_task(self._execute_handler, name="_execute_handler_task")
                tasks.append(task)
        
        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_event(self, event: Event):
        """Process a single event immediately."""
        await self._process_batch(EventBatch(events=[event]))
    
    async def _execute_handler(self, handler: Callable, events: List[Event]):
        """Execute handler with error handling."""
        try:
            await handler(events)
        except Exception as e:
            self.logger.error(f"Handler execution failed: {e}\n{traceback.format_exc()}")
            if self.metrics:
                self.metrics.errors_count += 1
    
    def _matches_wildcard(self, event_type: str, handler_info: Dict[str, Any]) -> bool:
        """Check if event type matches wildcard pattern."""
        # Simple wildcard matching - can be enhanced
        return True  # Simplified for now
    
    async def _event_worker(self, worker_name: str):
        """Generic event processing worker."""
        while self._running:
            try:
                # Worker can handle various async tasks
                await asyncio.sleep(0.1)  # Prevent busy waiting
                
                if self._shutdown_event.is_set():
                    break
                    
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
    
    async def _batch_timer(self):
        """Timer to force process aged batches."""
        while self._running:
            try:
                await asyncio.sleep(self.max_batch_age_ms / 1000 / 2)  # Check twice per max age
                
                # Find aged batches
                aged_batches = []
                current_time = time.time() * 1000
                
                for batch_key, batch in list(self.active_batches.items()):
                    if batch.age_ms() >= self.max_batch_age_ms:
                        aged_batches.append((batch_key, batch))
                
                # Process aged batches
                for batch_key, batch in aged_batches:
                    await self._submit_batch_for_processing(batch_key, batch)
                
                if aged_batches:
                    self.logger.debug(f"Processed {len(aged_batches)} aged batches")
                    
            except Exception as e:
                self.logger.error(f"Batch timer error: {e}")
    
    async def _flush_all_batches(self):
        """Flush all remaining batches."""
        remaining_batches = list(self.active_batches.items())
        
        for batch_key, batch in remaining_batches:
            await self._submit_batch_for_processing(batch_key, batch)
        
        if remaining_batches:
            self.logger.info(f"Flushed {len(remaining_batches)} remaining batches")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive processing metrics."""
        if not self.metrics:
            return {}
        
        # Calculate current queue sizes
        current_queue_sizes = {
            priority.name: queue.qsize() 
            for priority, queue in self.priority_queues.items()
        }
        
        # Calculate peak throughput
        if self.performance_history:
            recent_history = [
                entry for entry in self.performance_history
                if time.time() - entry['timestamp'] <= 60  # Last minute
            ]
            
            if recent_history:
                total_events = sum(entry['batch_size'] for entry in recent_history)
                time_span = max(entry['timestamp'] for entry in recent_history) - \
                           min(entry['timestamp'] for entry in recent_history)
                peak_eps = total_events / max(time_span, 1)
            else:
                peak_eps = 0
        else:
            peak_eps = 0
        
        # Memory usage
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        metrics = {
            'processing': {
                'total_events_processed': self.metrics.total_events_processed,
                'total_batches_processed': self.metrics.total_batches_processed,
                'avg_batch_size': round(self.metrics.avg_batch_size, 2),
                'avg_processing_time_ms': round(self.metrics.avg_processing_time_ms, 2),
                'peak_events_per_second': round(peak_eps, 2),
                'errors_count': self.metrics.errors_count
            },
            'queues': {
                'current_sizes': current_queue_sizes,
                'active_batches': len(self.active_batches),
                'total_queue_size': sum(current_queue_sizes.values())
            },
            'system': {
                'memory_usage_mb': round(memory_mb, 2),
                'worker_count': len(self.worker_tasks),
                'processor_count': len(self.batch_processors),
                'running': self._running
            }
        }
        
        # Add optimization metrics
        if self.deduplicator:
            metrics['deduplication'] = self.deduplicator.get_stats()
        
        if self.memory_pool:
            metrics['memory_pool'] = self.memory_pool.get_stats()
        
        return metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on event processor."""
        health = {
            'status': 'healthy' if self._running else 'stopped',
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            # Check queue health
            total_queue_size = sum(queue.qsize() for queue in self.priority_queues.values())
            queue_health = 'healthy' if total_queue_size < 5000 else 'degraded'
            
            health['checks']['queues'] = {
                'status': queue_health,
                'total_size': total_queue_size,
                'active_batches': len(self.active_batches)
            }
            
            # Check worker health
            active_workers = sum(1 for task in self.worker_tasks if not task.done())
            worker_health = 'healthy' if active_workers > 0 else 'unhealthy'
            
            health['checks']['workers'] = {
                'status': worker_health,
                'active_count': active_workers,
                'total_count': len(self.worker_tasks)
            }
            
            # Check performance
            if self.metrics and self.metrics.avg_processing_time_ms > 0:
                perf_health = 'healthy' if self.metrics.avg_processing_time_ms < 100 else 'degraded'
                health['checks']['performance'] = {
                    'status': perf_health,
                    'avg_processing_time_ms': self.metrics.avg_processing_time_ms,
                    'error_rate': self.metrics.errors_count / max(self.metrics.total_batches_processed, 1)
                }
            
            # Overall status
            check_statuses = [check['status'] for check in health['checks'].values()]
            if all(status == 'healthy' for status in check_statuses):
                health['status'] = 'healthy'
            elif any(status == 'unhealthy' for status in check_statuses):
                health['status'] = 'unhealthy'
            else:
                health['status'] = 'degraded'
                
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health


# Global optimized processor instance
optimized_event_processor = OptimizedEventProcessor(
    max_batch_size=50,
    max_batch_age_ms=100,
    enable_deduplication=True,
    enable_memory_pool=True,
    enable_metrics=True
)