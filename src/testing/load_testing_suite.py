from src.utils.task_tracker import create_tracked_task
"""
Phase 4 Load Testing Suite - Realistic Trading Scenarios
========================================================

Comprehensive load testing system designed to validate the Phase 4 optimizations
under realistic trading conditions. Tests the complete system stack from event
ingestion through processing to output delivery.

Key Testing Scenarios:
- High-frequency market data ingestion (>10,000 events/second)
- Burst trading activity with signal generation
- Multi-symbol concurrent analysis processing  
- Cache performance under load
- Event sourcing under high throughput
- Memory stability during extended operation
- Failure recovery and resilience testing

Performance Validation:
- Throughput: >10,000 events/second sustained
- Latency: <50ms end-to-end for critical paths
- Memory: <1GB stable usage under load
- Zero message loss verification
- Cache hit rates >95% maintained under load

Test Types:
- Synthetic load tests with realistic trading patterns
- Replay tests using historical market data
- Stress tests with extreme load conditions
- Resilience tests with component failures
- Endurance tests for memory leak detection
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, List, Any, Optional, Callable, Awaitable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import statistics
import threading
from pathlib import Path
import csv
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from ..core.events.optimized_event_processor import OptimizedEventProcessor
from ..core.events.event_sourcing import EventSourcingManager
from ..core.cache.event_driven_cache import EventDrivenCacheController
from ..core.events.event_types import (
    MarketDataUpdatedEvent, AnalysisCompletedEvent, TradingSignalEvent,
    DataType, AnalysisType, SignalType, create_market_data_event
)
from ..core.events.event_bus import Event, EventPriority
from ..monitoring.performance_dashboard import MetricsCollector


class TestScenario(Enum):
    """Load testing scenario types."""
    SYNTHETIC_LOAD = "synthetic_load"           # Generated realistic load
    HISTORICAL_REPLAY = "historical_replay"    # Historical data replay
    BURST_ACTIVITY = "burst_activity"          # Sudden traffic spikes
    SUSTAINED_LOAD = "sustained_load"          # Long-duration testing
    STRESS_TEST = "stress_test"               # Extreme load conditions
    RESILIENCE_TEST = "resilience_test"       # Component failure testing
    MEMORY_ENDURANCE = "memory_endurance"     # Memory leak detection


class LoadPattern(Enum):
    """Load generation patterns."""
    CONSTANT = "constant"       # Steady load
    RAMP_UP = "ramp_up"        # Gradually increasing load
    SPIKE = "spike"            # Sudden load spikes
    WAVE = "wave"              # Sinusoidal load pattern
    RANDOM = "random"          # Random load fluctuations


@dataclass
class LoadTestConfig:
    """Configuration for load testing scenarios."""
    scenario: TestScenario
    duration_seconds: int = 300
    target_events_per_second: int = 5000
    max_events_per_second: int = 15000
    load_pattern: LoadPattern = LoadPattern.CONSTANT
    symbols: List[str] = field(default_factory=lambda: [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT',
        'MATIC/USDT', 'AVAX/USDT', 'LINK/USDT', 'UNI/USDT', 'ATOM/USDT'
    ])
    exchanges: List[str] = field(default_factory=lambda: ['bybit', 'binance'])
    event_types: Dict[str, float] = field(default_factory=lambda: {
        'market_data': 0.7,    # 70% market data events
        'analysis': 0.2,       # 20% analysis events  
        'signals': 0.08,       # 8% trading signals
        'system': 0.02         # 2% system events
    })
    enable_cache_testing: bool = True
    enable_event_sourcing: bool = True
    enable_memory_monitoring: bool = True
    failure_injection_rate: float = 0.0  # 0-1, probability of failures
    
    def validate(self):
        """Validate configuration parameters."""
        if self.duration_seconds <= 0:
            raise ValueError("Duration must be positive")
        if self.target_events_per_second <= 0:
            raise ValueError("Target events per second must be positive")
        if not self.symbols:
            raise ValueError("At least one symbol required")
        if not self.exchanges:
            raise ValueError("At least one exchange required")
        if abs(sum(self.event_types.values()) - 1.0) > 0.01:
            raise ValueError("Event type probabilities must sum to 1.0")


@dataclass
class LoadTestResults:
    """Results from load testing."""
    test_id: str
    scenario: TestScenario
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Event statistics
    total_events_generated: int = 0
    total_events_processed: int = 0
    events_lost: int = 0
    avg_events_per_second: float = 0.0
    peak_events_per_second: float = 0.0
    
    # Performance metrics
    avg_processing_latency_ms: float = 0.0
    p95_processing_latency_ms: float = 0.0
    p99_processing_latency_ms: float = 0.0
    
    # Memory metrics
    initial_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    final_memory_mb: float = 0.0
    memory_growth_mb: float = 0.0
    gc_collections: int = 0
    
    # Cache metrics
    cache_hit_rate: float = 0.0
    cache_operations_per_second: float = 0.0
    cache_errors: int = 0
    
    # Error statistics
    error_count: int = 0
    error_rate: float = 0.0
    timeout_count: int = 0
    
    # Performance assessment
    performance_score: int = 100
    target_throughput_achieved: bool = False
    target_latency_achieved: bool = False
    zero_message_loss: bool = True
    
    # Detailed metrics timeline
    metrics_timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate_performance_score(self):
        """Calculate overall performance score."""
        score = 100
        
        # Throughput assessment
        throughput_ratio = self.avg_events_per_second / max(self.config.target_events_per_second, 1)
        if throughput_ratio < 0.5:
            score -= 40
        elif throughput_ratio < 0.8:
            score -= 20
        elif throughput_ratio < 1.0:
            score -= 10
        
        # Latency assessment
        if self.avg_processing_latency_ms > 100:
            score -= 30
        elif self.avg_processing_latency_ms > 50:
            score -= 15
        
        # Memory assessment
        memory_growth_ratio = self.memory_growth_mb / max(self.initial_memory_mb, 100)
        if memory_growth_ratio > 2.0:  # More than 2x growth
            score -= 25
        elif memory_growth_ratio > 1.5:
            score -= 15
        elif memory_growth_ratio > 1.2:
            score -= 5
        
        # Error rate assessment
        if self.error_rate > 0.05:  # >5% errors
            score -= 20
        elif self.error_rate > 0.01:  # >1% errors
            score -= 10
        
        # Message loss assessment
        if not self.zero_message_loss:
            score -= 15
        
        self.performance_score = max(0, score)
        
        # Set achievement flags
        self.target_throughput_achieved = throughput_ratio >= 1.0
        self.target_latency_achieved = self.avg_processing_latency_ms <= 50
        
        return self.performance_score


class EventGenerator:
    """Generates realistic trading events for load testing."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.symbols = config.symbols
        self.exchanges = config.exchanges
        self.event_types = config.event_types
        
        # Price simulation state
        self.symbol_prices: Dict[str, float] = {}
        self.symbol_trends: Dict[str, float] = {}
        
        # Initialize random prices
        for symbol in self.symbols:
            base_price = random.uniform(0.1, 100000)  # Wide price range
            self.symbol_prices[symbol] = base_price
            self.symbol_trends[symbol] = random.uniform(-0.002, 0.002)  # ±0.2% trend
        
        # Event ID tracking
        self.event_counter = 0
        self.lock = threading.Lock()
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def generate_event(self) -> Event:
        """Generate a single realistic trading event."""
        with self.lock:
            self.event_counter += 1
            event_id = f"test_event_{self.event_counter}"
        
        # Select event type based on probabilities
        rand = random.random()
        cumulative_prob = 0.0
        
        for event_type, prob in self.event_types.items():
            cumulative_prob += prob
            if rand <= cumulative_prob:
                return self._generate_event_by_type(event_type, event_id)
        
        # Default to market data
        return self._generate_market_data_event(event_id)
    
    def _generate_event_by_type(self, event_type: str, event_id: str) -> Event:
        """Generate event of specific type."""
        if event_type == 'market_data':
            return self._generate_market_data_event(event_id)
        elif event_type == 'analysis':
            return self._generate_analysis_event(event_id)
        elif event_type == 'signals':
            return self._generate_signal_event(event_id)
        elif event_type == 'system':
            return self._generate_system_event(event_id)
        else:
            return self._generate_market_data_event(event_id)
    
    def _generate_market_data_event(self, event_id: str) -> MarketDataUpdatedEvent:
        """Generate realistic market data event."""
        symbol = random.choice(self.symbols)
        exchange = random.choice(self.exchanges)
        
        # Update price with realistic movement
        current_price = self.symbol_prices[symbol]
        trend = self.symbol_trends[symbol]
        
        # Add trend + random walk
        price_change = trend + random.uniform(-0.01, 0.01)  # ±1% random
        new_price = current_price * (1 + price_change)
        
        # Ensure price stays positive
        new_price = max(new_price, 0.0001)
        self.symbol_prices[symbol] = new_price
        
        # Occasionally change trend
        if random.random() < 0.01:  # 1% chance
            self.symbol_trends[symbol] = random.uniform(-0.002, 0.002)
        
        # Generate realistic market data
        volume = random.uniform(1000, 1000000)
        spread = new_price * random.uniform(0.0001, 0.002)  # 0.01-0.2% spread
        
        return MarketDataUpdatedEvent(
            event_id=event_id,
            symbol=symbol,
            exchange=exchange,
            data_type=DataType.TICKER,
            timestamp=datetime.utcnow(),
            raw_data={
                'price': new_price,
                'volume': volume,
                'bid': new_price - spread/2,
                'ask': new_price + spread/2,
                'change_24h': price_change * 24,  # Simulated 24h change
            },
            data_quality_score=random.uniform(0.9, 1.0)
        )
    
    def _generate_analysis_event(self, event_id: str) -> AnalysisCompletedEvent:
        """Generate realistic analysis event."""
        symbol = random.choice(self.symbols)
        analysis_types = list(AnalysisType)
        analysis_type = random.choice(analysis_types)
        
        # Generate realistic analysis results
        score = random.uniform(0.0, 1.0)
        confidence = random.uniform(0.5, 0.95)
        
        analysis_result = {
            'technical_indicators': {
                'rsi': random.uniform(0, 100),
                'macd': random.uniform(-1, 1),
                'bollinger_position': random.uniform(0, 1)
            },
            'volume_analysis': {
                'volume_trend': random.choice(['increasing', 'decreasing', 'stable']),
                'volume_strength': random.choice(['strong', 'moderate', 'weak'])
            },
            'price_action': {
                'trend': random.choice(['bullish', 'bearish', 'sideways']),
                'momentum': random.uniform(-1, 1)
            }
        }
        
        return AnalysisCompletedEvent(
            event_id=event_id,
            analyzer_type=analysis_type,
            symbol=symbol,
            timeframe='5m',
            analysis_result=analysis_result,
            score=score,
            confidence=confidence,
            processing_time_ms=random.uniform(5, 50)
        )
    
    def _generate_signal_event(self, event_id: str) -> TradingSignalEvent:
        """Generate realistic trading signal event."""
        symbol = random.choice(self.symbols)
        signal_types = list(SignalType)
        signal_type = random.choice(signal_types)
        
        current_price = self.symbol_prices.get(symbol, 100.0)
        
        return TradingSignalEvent(
            event_id=event_id,
            signal_type=signal_type,
            symbol=symbol,
            timeframe='5m',
            price=current_price,
            confidence=random.uniform(0.6, 0.95),
            strength=random.uniform(0.5, 1.0),
            stop_loss=current_price * random.uniform(0.95, 0.99) if signal_type in [SignalType.LONG, SignalType.STRONG_LONG] else current_price * random.uniform(1.01, 1.05),
            take_profit=current_price * random.uniform(1.02, 1.08) if signal_type in [SignalType.LONG, SignalType.STRONG_LONG] else current_price * random.uniform(0.92, 0.98),
            signal_sources=['confluence_analysis', 'volume_analysis', 'technical_indicators']
        )
    
    def _generate_system_event(self, event_id: str) -> Event:
        """Generate system event."""
        system_events = [
            'system.component.healthy',
            'system.cache.refresh',
            'system.monitor.update',
            'system.maintenance.complete'
        ]
        
        event_type = random.choice(system_events)
        
        return Event(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source='load_test_system',
            priority=EventPriority.LOW,
            data={
                'component': random.choice(['cache', 'database', 'monitor', 'processor']),
                'status': random.choice(['healthy', 'warning', 'error']),
                'details': f'Simulated system event for load testing'
            }
        )


class LoadPatternGenerator:
    """Generates different load patterns for testing."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.pattern = config.load_pattern
        self.base_rate = config.target_events_per_second
        self.max_rate = config.max_events_per_second
        self.duration = config.duration_seconds
        
    def get_events_per_second(self, elapsed_seconds: float) -> int:
        """Get target events per second at given time."""
        progress = elapsed_seconds / self.duration
        
        if self.pattern == LoadPattern.CONSTANT:
            return self.base_rate
        
        elif self.pattern == LoadPattern.RAMP_UP:
            # Linearly increase from base_rate to max_rate
            return int(self.base_rate + (self.max_rate - self.base_rate) * progress)
        
        elif self.pattern == LoadPattern.SPIKE:
            # Periodic spikes
            spike_interval = 60  # seconds
            spike_duration = 10  # seconds
            
            cycle_position = elapsed_seconds % spike_interval
            if cycle_position < spike_duration:
                return self.max_rate
            else:
                return self.base_rate
        
        elif self.pattern == LoadPattern.WAVE:
            # Sinusoidal pattern
            wave_frequency = 0.01  # Hz
            amplitude = (self.max_rate - self.base_rate) / 2
            offset = (self.max_rate + self.base_rate) / 2
            
            return int(offset + amplitude * np.sin(2 * np.pi * wave_frequency * elapsed_seconds))
        
        elif self.pattern == LoadPattern.RANDOM:
            # Random fluctuations
            return random.randint(self.base_rate // 2, self.max_rate)
        
        else:
            return self.base_rate


class PerformanceProfiler:
    """Profiles system performance during load testing."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.metrics_history: List[Dict[str, Any]] = []
        self.process = psutil.Process()
        self.initial_memory = 0.0
        self.peak_memory = 0.0
        self.gc_count_start = 0
        self.collection_interval = 1.0  # seconds
        self.profiling_task: Optional[asyncio.Task] = None
        
    async def start_profiling(self):
        """Start performance profiling."""
        self.start_time = time.time()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory
        self.gc_count_start = len(gc.get_stats()) if hasattr(gc, 'get_stats') else 0
        
        # Start collection task
        self.profiling_task = create_tracked_task(self._collect_metrics(), name="auto_tracked_task")
    
    async def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return summary."""
        if self.profiling_task:
            self.profiling_task.cancel()
            try:
                await self.profiling_task
            except asyncio.CancelledError:
                pass
        
        end_time = time.time()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        gc_count_end = len(gc.get_stats()) if hasattr(gc, 'get_stats') else 0
        
        return {
            'duration_seconds': end_time - (self.start_time or 0),
            'initial_memory_mb': self.initial_memory,
            'peak_memory_mb': self.peak_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': final_memory - self.initial_memory,
            'gc_collections': gc_count_end - self.gc_count_start,
            'metrics_samples': len(self.metrics_history)
        }
    
    async def _collect_metrics(self):
        """Collect performance metrics periodically."""
        while True:
            try:
                current_time = time.time()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # Update peak memory
                self.peak_memory = max(self.peak_memory, memory_mb)
                
                # Collect metrics
                metrics = {
                    'timestamp': current_time,
                    'elapsed_seconds': current_time - (self.start_time or current_time),
                    'memory_mb': memory_mb,
                    'cpu_percent': self.process.cpu_percent(),
                    'threads': self.process.num_threads(),
                    'open_files': len(self.process.open_files()),
                    'connections': len(self.process.connections())
                }
                
                self.metrics_history.append(metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger(__name__).error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.collection_interval)


class LoadTestRunner:
    """Main load test runner that orchestrates testing scenarios."""
    
    def __init__(
        self,
        event_processor: OptimizedEventProcessor,
        event_sourcing: Optional[EventSourcingManager] = None,
        cache_controller: Optional[EventDrivenCacheController] = None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize load test runner."""
        self.event_processor = event_processor
        self.event_sourcing = event_sourcing
        self.cache_controller = cache_controller
        self.metrics_collector = metrics_collector
        
        # Test state
        self.current_test: Optional[LoadTestResults] = None
        self.running = False
        
        # Event tracking
        self.events_generated = 0
        self.events_processed = 0
        self.processing_times: List[float] = []
        
        # Background tasks
        self.generation_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Synchronization
        self.event_lock = threading.Lock()
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    async def run_test(self, config: LoadTestConfig) -> LoadTestResults:
        """Run a complete load test scenario."""
        # Validate configuration
        config.validate()
        
        # Initialize test results
        test_id = str(uuid.uuid4())
        self.current_test = LoadTestResults(
            test_id=test_id,
            scenario=config.scenario,
            config=config,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),  # Will be updated
            duration_seconds=0.0
        )
        
        self.logger.info(f"Starting load test {test_id}: {config.scenario.value}")
        
        try:
            # Start profiling
            profiler = PerformanceProfiler()
            await profiler.start_profiling()
            
            # Initialize components
            await self._initialize_test_components()
            
            # Register event handler for processing tracking
            await self._register_processing_handler()
            
            # Run the actual test
            await self._execute_test_scenario(config, profiler)
            
            # Stop profiling and collect final metrics
            profiling_results = await profiler.stop_profiling()
            
            # Finalize results
            await self._finalize_test_results(profiling_results)
            
            self.logger.info(
                f"Load test completed: {self.current_test.total_events_generated} events generated, "
                f"{self.current_test.total_events_processed} processed, "
                f"performance score: {self.current_test.performance_score}"
            )
            
            return self.current_test
            
        except Exception as e:
            self.logger.error(f"Load test failed: {e}")
            if self.current_test:
                self.current_test.end_time = datetime.utcnow()
                self.current_test.error_count += 1
            raise
        
        finally:
            await self._cleanup_test_components()
    
    async def _initialize_test_components(self):
        """Initialize test components."""
        # Start event processor if not running
        if not self.event_processor._running:
            await self.event_processor.start()
        
        # Initialize event sourcing if enabled
        if self.event_sourcing and not self.current_test.config.enable_event_sourcing:
            pass  # Skip if disabled
        
        # Initialize cache controller if available
        if self.cache_controller:
            # Start cache controller if not running
            pass  # Assume it's already initialized
        
        # Reset counters
        self.events_generated = 0
        self.events_processed = 0
        self.processing_times.clear()
        self.running = True
    
    async def _register_processing_handler(self):
        """Register handler to track event processing."""
        async def processing_handler(events: List[Event]):
            """Handler that tracks processed events."""
            with self.event_lock:
                self.events_processed += len(events)
                # Record processing time (simplified)
                processing_time = time.time() * 1000  # ms
                self.processing_times.extend([processing_time] * len(events))
        
        # Register handler for all event types
        self.event_processor.register_handler("*", processing_handler)
    
    async def _execute_test_scenario(self, config: LoadTestConfig, profiler: PerformanceProfiler):
        """Execute the main test scenario."""
        # Initialize event generator and load pattern
        event_generator = EventGenerator(config)
        load_pattern = LoadPatternGenerator(config)
        
        # Start background monitoring
        self.monitoring_task = create_tracked_task(
            self._monitor_test_progress(config, profiler, name="auto_tracked_task")
        )
        
        # Generate and send events according to load pattern
        start_time = time.time()
        
        while time.time() - start_time < config.duration_seconds and self.running:
            elapsed = time.time() - start_time
            target_rate = load_pattern.get_events_per_second(elapsed)
            
            # Calculate events to generate in this second
            events_this_second = target_rate
            
            # Generate events in batches for efficiency
            batch_size = min(100, events_this_second)
            batches = events_this_second // batch_size
            remainder = events_this_second % batch_size
            
            # Generate event batches
            for batch_num in range(batches):
                if not self.running:
                    break
                
                batch_events = []
                for _ in range(batch_size):
                    event = event_generator.generate_event()
                    batch_events.append(event)
                
                # Process batch
                await self._process_event_batch(batch_events, config)
            
            # Handle remainder
            if remainder > 0 and self.running:
                remainder_events = []
                for _ in range(remainder):
                    event = event_generator.generate_event()
                    remainder_events.append(event)
                await self._process_event_batch(remainder_events, config)
            
            # Control rate to achieve target events per second
            await asyncio.sleep(0.1)  # Small delay between batches
        
        # Wait a bit for processing to complete
        await asyncio.sleep(2)
    
    async def _process_event_batch(self, events: List[Event], config: LoadTestConfig):
        """Process a batch of events."""
        try:
            # Send to event processor
            event_ids = await self.event_processor.process_events(events)
            
            with self.event_lock:
                self.events_generated += len(events)
            
            # Optionally test cache operations
            if config.enable_cache_testing and self.cache_controller:
                await self._test_cache_operations(events)
            
            # Optionally test event sourcing
            if config.enable_event_sourcing and self.event_sourcing:
                for event in events:
                    await self.event_sourcing.source_event(event)
            
            # Inject failures if configured
            if config.failure_injection_rate > 0 and random.random() < config.failure_injection_rate:
                raise Exception("Injected test failure")
                
        except Exception as e:
            self.logger.warning(f"Batch processing error: {e}")
            if self.current_test:
                self.current_test.error_count += len(events)
    
    async def _test_cache_operations(self, events: List[Event]):
        """Test cache operations with events."""
        for event in events:
            if hasattr(event, 'symbol'):
                # Test cache get/set operations
                cache_key = f"test:{event.symbol}:latest"
                
                # Try to get
                cached_value, hit = await self.cache_controller.get_cache(cache_key)
                
                # Set new value
                await self.cache_controller.set_cache(
                    cache_key,
                    {
                        'timestamp': time.time(),
                        'event_type': event.event_type,
                        'data': event.data
                    },
                    ttl=30
                )
    
    async def _monitor_test_progress(self, config: LoadTestConfig, profiler: PerformanceProfiler):
        """Monitor test progress and collect metrics."""
        start_time = time.time()
        
        while self.running:
            try:
                elapsed = time.time() - start_time
                
                # Collect current metrics
                with self.event_lock:
                    current_generated = self.events_generated
                    current_processed = self.events_processed
                    current_processing_times = self.processing_times.copy()
                
                # Calculate rates
                generation_rate = current_generated / max(elapsed, 1)
                processing_rate = current_processed / max(elapsed, 1)
                
                # Calculate latencies
                avg_latency = 0.0
                if current_processing_times:
                    avg_latency = statistics.mean(current_processing_times)
                
                # Record timeline metrics
                if self.current_test:
                    self.current_test.metrics_timeline.append({
                        'timestamp': time.time(),
                        'elapsed_seconds': elapsed,
                        'events_generated': current_generated,
                        'events_processed': current_processed,
                        'generation_rate': generation_rate,
                        'processing_rate': processing_rate,
                        'avg_latency_ms': avg_latency,
                        'memory_mb': profiler.process.memory_info().rss / 1024 / 1024
                    })
                
                # Log progress
                self.logger.info(
                    f"Test progress: {elapsed:.1f}s, "
                    f"Generated: {current_generated}, "
                    f"Processed: {current_processed}, "
                    f"Rate: {generation_rate:.1f} gen/s, {processing_rate:.1f} proc/s"
                )
                
                await asyncio.sleep(5)  # Report every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _finalize_test_results(self, profiling_results: Dict[str, Any]):
        """Finalize test results with collected metrics."""
        if not self.current_test:
            return
        
        end_time = datetime.utcnow()
        self.current_test.end_time = end_time
        self.current_test.duration_seconds = (end_time - self.current_test.start_time).total_seconds()
        
        # Event statistics
        with self.event_lock:
            self.current_test.total_events_generated = self.events_generated
            self.current_test.total_events_processed = self.events_processed
            self.current_test.events_lost = max(0, self.events_generated - self.events_processed)
            
            # Calculate rates
            duration = max(self.current_test.duration_seconds, 1)
            self.current_test.avg_events_per_second = self.events_processed / duration
            
            # Calculate peak rate from timeline
            if self.current_test.metrics_timeline:
                rates = [m['processing_rate'] for m in self.current_test.metrics_timeline]
                self.current_test.peak_events_per_second = max(rates) if rates else 0.0
            
            # Calculate latency statistics
            if self.processing_times:
                self.current_test.avg_processing_latency_ms = statistics.mean(self.processing_times)
                sorted_times = sorted(self.processing_times)
                n = len(sorted_times)
                self.current_test.p95_processing_latency_ms = sorted_times[int(n * 0.95)] if n > 0 else 0
                self.current_test.p99_processing_latency_ms = sorted_times[int(n * 0.99)] if n > 0 else 0
        
        # Memory statistics
        self.current_test.initial_memory_mb = profiling_results['initial_memory_mb']
        self.current_test.peak_memory_mb = profiling_results['peak_memory_mb']
        self.current_test.final_memory_mb = profiling_results['final_memory_mb']
        self.current_test.memory_growth_mb = profiling_results['memory_growth_mb']
        self.current_test.gc_collections = profiling_results['gc_collections']
        
        # Cache metrics (if available)
        if self.cache_controller:
            cache_metrics = self.cache_controller.get_comprehensive_metrics()
            key_mgmt = cache_metrics.get('key_management', {})
            self.current_test.cache_hit_rate = key_mgmt.get('avg_hit_rate', 0.0)
            
            operations = cache_metrics.get('operations', {})
            total_ops = sum(operations.values())
            self.current_test.cache_operations_per_second = total_ops / duration
        
        # Error statistics
        self.current_test.error_rate = self.current_test.error_count / max(self.current_test.total_events_generated, 1)
        self.current_test.zero_message_loss = self.current_test.events_lost == 0
        
        # Calculate performance score
        self.current_test.calculate_performance_score()
    
    async def _cleanup_test_components(self):
        """Cleanup test components."""
        self.running = False
        
        # Cancel background tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Force garbage collection
        gc.collect()
    
    async def stop_test(self):
        """Stop the current test."""
        self.running = False
        self.logger.info("Load test stop requested")


class LoadTestSuite:
    """Comprehensive load testing suite with multiple scenarios."""
    
    def __init__(
        self,
        event_processor: OptimizedEventProcessor,
        event_sourcing: Optional[EventSourcingManager] = None,
        cache_controller: Optional[EventDrivenCacheController] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        results_dir: str = "test_results"
    ):
        """Initialize load test suite."""
        self.event_processor = event_processor
        self.event_sourcing = event_sourcing
        self.cache_controller = cache_controller
        self.metrics_collector = metrics_collector
        
        # Results management
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Test runner
        self.test_runner = LoadTestRunner(
            event_processor, event_sourcing, cache_controller, metrics_collector
        )
        
        # Test results
        self.test_results: List[LoadTestResults] = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    async def run_full_suite(self) -> Dict[str, Any]:
        """Run the complete load testing suite."""
        self.logger.info("Starting comprehensive load testing suite")
        
        # Define test scenarios
        test_scenarios = [
            # Baseline performance test
            LoadTestConfig(
                scenario=TestScenario.SYNTHETIC_LOAD,
                duration_seconds=180,
                target_events_per_second=5000,
                load_pattern=LoadPattern.CONSTANT
            ),
            
            # High throughput test
            LoadTestConfig(
                scenario=TestScenario.STRESS_TEST,
                duration_seconds=120,
                target_events_per_second=10000,
                max_events_per_second=15000,
                load_pattern=LoadPattern.RAMP_UP
            ),
            
            # Burst activity test
            LoadTestConfig(
                scenario=TestScenario.BURST_ACTIVITY,
                duration_seconds=240,
                target_events_per_second=3000,
                max_events_per_second=12000,
                load_pattern=LoadPattern.SPIKE
            ),
            
            # Endurance test
            LoadTestConfig(
                scenario=TestScenario.SUSTAINED_LOAD,
                duration_seconds=600,  # 10 minutes
                target_events_per_second=7000,
                load_pattern=LoadPattern.CONSTANT,
                enable_memory_monitoring=True
            ),
            
            # Resilience test with failures
            LoadTestConfig(
                scenario=TestScenario.RESILIENCE_TEST,
                duration_seconds=300,
                target_events_per_second=5000,
                load_pattern=LoadPattern.WAVE,
                failure_injection_rate=0.001  # 0.1% failure rate
            )
        ]
        
        # Run each test scenario
        suite_start_time = time.time()
        
        for i, config in enumerate(test_scenarios, 1):
            self.logger.info(f"Running test scenario {i}/{len(test_scenarios)}: {config.scenario.value}")
            
            try:
                # Wait between tests to allow system recovery
                if i > 1:
                    self.logger.info("Waiting for system recovery...")
                    await asyncio.sleep(30)
                
                # Run test
                result = await self.test_runner.run_test(config)
                self.test_results.append(result)
                
                # Save individual result
                await self._save_test_result(result)
                
                self.logger.info(
                    f"Test {i} completed - Performance score: {result.performance_score}, "
                    f"Throughput: {result.avg_events_per_second:.1f} events/s"
                )
                
            except Exception as e:
                self.logger.error(f"Test scenario {i} failed: {e}")
                continue
        
        suite_duration = time.time() - suite_start_time
        
        # Generate comprehensive report
        suite_report = await self._generate_suite_report(suite_duration)
        
        # Save suite report
        await self._save_suite_report(suite_report)
        
        self.logger.info(f"Load testing suite completed in {suite_duration:.1f} seconds")
        return suite_report
    
    async def _save_test_result(self, result: LoadTestResults):
        """Save individual test result."""
        timestamp = result.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f"test_{result.scenario.value}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert to JSON-serializable format
        result_data = {
            'test_id': result.test_id,
            'scenario': result.scenario.value,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat(),
            'duration_seconds': result.duration_seconds,
            'total_events_generated': result.total_events_generated,
            'total_events_processed': result.total_events_processed,
            'events_lost': result.events_lost,
            'avg_events_per_second': result.avg_events_per_second,
            'peak_events_per_second': result.peak_events_per_second,
            'avg_processing_latency_ms': result.avg_processing_latency_ms,
            'p95_processing_latency_ms': result.p95_processing_latency_ms,
            'p99_processing_latency_ms': result.p99_processing_latency_ms,
            'initial_memory_mb': result.initial_memory_mb,
            'peak_memory_mb': result.peak_memory_mb,
            'final_memory_mb': result.final_memory_mb,
            'memory_growth_mb': result.memory_growth_mb,
            'cache_hit_rate': result.cache_hit_rate,
            'cache_operations_per_second': result.cache_operations_per_second,
            'error_count': result.error_count,
            'error_rate': result.error_rate,
            'performance_score': result.performance_score,
            'target_throughput_achieved': result.target_throughput_achieved,
            'target_latency_achieved': result.target_latency_achieved,
            'zero_message_loss': result.zero_message_loss,
            'config': {
                'scenario': result.config.scenario.value,
                'duration_seconds': result.config.duration_seconds,
                'target_events_per_second': result.config.target_events_per_second,
                'load_pattern': result.config.load_pattern.value,
                'symbols': result.config.symbols,
                'exchanges': result.config.exchanges
            },
            'metrics_timeline': result.metrics_timeline
        }
        
        with open(filepath, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        self.logger.info(f"Test result saved: {filepath}")
    
    async def _generate_suite_report(self, suite_duration: float) -> Dict[str, Any]:
        """Generate comprehensive suite report."""
        if not self.test_results:
            return {'error': 'No test results available'}
        
        # Aggregate statistics
        total_events_generated = sum(r.total_events_generated for r in self.test_results)
        total_events_processed = sum(r.total_events_processed for r in self.test_results)
        total_errors = sum(r.error_count for r in self.test_results)
        
        avg_throughput = statistics.mean([r.avg_events_per_second for r in self.test_results])
        avg_latency = statistics.mean([r.avg_processing_latency_ms for r in self.test_results])
        avg_performance_score = statistics.mean([r.performance_score for r in self.test_results])
        
        peak_throughput = max([r.peak_events_per_second for r in self.test_results])
        peak_memory = max([r.peak_memory_mb for r in self.test_results])
        
        # Success metrics
        throughput_success = sum(1 for r in self.test_results if r.target_throughput_achieved)
        latency_success = sum(1 for r in self.test_results if r.target_latency_achieved)
        zero_loss_success = sum(1 for r in self.test_results if r.zero_message_loss)
        
        # Performance assessment
        overall_success = all([
            avg_throughput >= 5000,    # Minimum acceptable throughput
            avg_latency <= 50,         # Maximum acceptable latency
            peak_memory <= 1024,       # Memory constraint
            total_errors / max(total_events_generated, 1) <= 0.01  # Max 1% error rate
        ])
        
        # Generate recommendations
        recommendations = []
        if avg_throughput < 10000:
            recommendations.append("Consider optimizing event processing pipeline for higher throughput")
        if avg_latency > 50:
            recommendations.append("Focus on reducing event processing latency")
        if peak_memory > 1024:
            recommendations.append("Implement memory optimization strategies")
        if total_errors > 0:
            recommendations.append("Investigate and fix error conditions")
        
        if not recommendations:
            recommendations.append("System meets all performance targets - excellent performance!")
        
        return {
            'suite_summary': {
                'total_tests': len(self.test_results),
                'suite_duration_seconds': suite_duration,
                'overall_success': overall_success,
                'timestamp': datetime.utcnow().isoformat()
            },
            'aggregate_metrics': {
                'total_events_generated': total_events_generated,
                'total_events_processed': total_events_processed,
                'total_errors': total_errors,
                'avg_throughput_eps': avg_throughput,
                'peak_throughput_eps': peak_throughput,
                'avg_latency_ms': avg_latency,
                'peak_memory_mb': peak_memory,
                'avg_performance_score': avg_performance_score
            },
            'success_metrics': {
                'throughput_targets_met': f"{throughput_success}/{len(self.test_results)}",
                'latency_targets_met': f"{latency_success}/{len(self.test_results)}",
                'zero_message_loss': f"{zero_loss_success}/{len(self.test_results)}",
                'overall_success_rate': f"{sum([r.performance_score >= 80 for r in self.test_results])}/{len(self.test_results)}"
            },
            'performance_targets': {
                'target_throughput_eps': 10000,
                'target_latency_ms': 50,
                'target_memory_mb': 1024,
                'target_error_rate': 0.01
            },
            'recommendations': recommendations,
            'test_results': [
                {
                    'scenario': r.scenario.value,
                    'performance_score': r.performance_score,
                    'throughput_eps': r.avg_events_per_second,
                    'latency_ms': r.avg_processing_latency_ms,
                    'memory_peak_mb': r.peak_memory_mb,
                    'error_rate': r.error_rate,
                    'targets_achieved': {
                        'throughput': r.target_throughput_achieved,
                        'latency': r.target_latency_achieved,
                        'zero_loss': r.zero_message_loss
                    }
                }
                for r in self.test_results
            ]
        }
    
    async def _save_suite_report(self, report: Dict[str, Any]):
        """Save comprehensive suite report."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        json_filename = f"load_test_suite_report_{timestamp}.json"
        json_filepath = self.results_dir / json_filename
        
        with open(json_filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save CSV summary
        csv_filename = f"load_test_suite_summary_{timestamp}.csv"
        csv_filepath = self.results_dir / csv_filename
        
        with open(csv_filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Scenario', 'Performance Score', 'Throughput (eps)', 'Latency (ms)', 
                'Peak Memory (MB)', 'Error Rate', 'Throughput Target', 'Latency Target', 'Zero Loss'
            ])
            
            # Data rows
            for result in report['test_results']:
                writer.writerow([
                    result['scenario'],
                    result['performance_score'],
                    result['throughput_eps'],
                    result['latency_ms'],
                    result['memory_peak_mb'],
                    result['error_rate'],
                    result['targets_achieved']['throughput'],
                    result['targets_achieved']['latency'],
                    result['targets_achieved']['zero_loss']
                ])
        
        self.logger.info(f"Suite report saved: {json_filepath}, {csv_filepath}")


# Global load test suite instance
# Will be initialized with actual components during testing
load_test_suite: Optional[LoadTestSuite] = None