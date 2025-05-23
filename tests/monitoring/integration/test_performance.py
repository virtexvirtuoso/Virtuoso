"""
Performance Integration Tests for the Monitoring System.

These tests validate that the modular architecture maintains good performance
characteristics and can handle realistic workloads efficiently.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any

from src.monitoring.services import MonitoringOrchestrationService
from src.monitoring.components import (
    WebSocketProcessor,
    MarketDataProcessor,
    SignalProcessor,
    WhaleActivityMonitor,
    ManipulationMonitor,
    HealthMonitor as ComponentHealthMonitor
)
from src.monitoring.utilities import MarketDataValidator


class TestPerformanceIntegration:
    """Performance tests for the monitoring system."""

    @pytest.fixture
    def performance_config(self):
        """Configuration optimized for performance testing."""
        return {
            'websocket': {
                'enabled': True,
                'batch_size': 100,
                'timeout': 5
            },
            'market_data': {
                'cache_ttl': 60,
                'enable_validation': True,
                'parallel_fetching': True
            },
            'signal_processing': {
                'enable_pdf_reports': False,  # Disable for performance
                'parallel_analysis': True,
                'batch_size': 50
            },
            'whale_activity': {
                'enabled': True,
                'batch_processing': True,
                'optimization_level': 'high'
            },
            'manipulation': {
                'enabled': True,
                'fast_mode': True,
                'parallel_detection': True
            },
            'monitoring': {
                'cycle_interval': 5,
                'max_concurrent_symbols': 20,
                'performance_mode': True
            }
        }

    @pytest.fixture
    def mock_fast_exchange(self):
        """Create a high-performance mock exchange."""
        exchange = Mock()
        
        # Fast OHLCV data generation
        def generate_ohlcv_data():
            base_price = 47000
            return [
                [int(time.time() * 1000) - i * 60000, base_price + i, base_price + i + 100, base_price + i - 50, base_price + i + 25, 1000 + i]
                for i in range(100)  # 100 data points
            ]
        
        exchange.fetch_ohlcv = AsyncMock(side_effect=lambda *args, **kwargs: generate_ohlcv_data())
        exchange.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'last': 47200,
            'bid': 47180,
            'ask': 47220,
            'volume': 25000
        })
        exchange.fetch_order_book = AsyncMock(return_value={
            'bids': [[47180 - i, 10 + i] for i in range(50)],
            'asks': [[47220 + i, 12 + i] for i in range(50)]
        })
        exchange.fetch_trades = AsyncMock(return_value=[
            {'amount': 1.5 + i * 0.1, 'price': 47200 + i, 'timestamp': int(time.time() * 1000) - i * 1000}
            for i in range(20)
        ])
        
        return exchange

    @pytest.fixture
    def mock_fast_dependencies(self):
        """Create high-performance mock dependencies."""
        deps = {
            'database_client': Mock(),
            'alert_manager': Mock(),
            'signal_generator': Mock(),
            'top_symbols_manager': Mock(),
            'market_data_manager': Mock(),
            'manipulation_detector': Mock()
        }
        
        # Fast signal generation
        deps['signal_generator'].generate_confluence_data = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'overall_score': 65,
            'processing_time_ms': 50,
            'signals': {f'indicator_{i}': {'value': i, 'signal': 'neutral'} for i in range(10)}
        })
        
        # Fast manipulation detection
        deps['manipulation_detector'].detect_manipulation = AsyncMock(return_value={
            'manipulation_detected': False,
            'confidence': 0.2,
            'processing_time_ms': 30
        })
        
        # Fast alert manager
        deps['alert_manager'].send_alert = AsyncMock()
        
        return deps

    @pytest_asyncio.fixture
    async def performance_system(self, mock_fast_exchange, performance_config, mock_fast_dependencies):
        """Create a performance-optimized monitoring system."""
        logger = Mock()
        
        # Create components
        validator = MarketDataValidator(logger)
        
        websocket_processor = WebSocketProcessor(
            config=performance_config,
            logger=logger
        )
        
        market_data_processor = MarketDataProcessor(
            logger=logger,
            config=performance_config.get('market_data', {}),
            exchange=mock_fast_exchange,
            market_data_manager=mock_fast_dependencies['market_data_manager'],
            validator=validator
        )
        
        signal_processor = SignalProcessor(
            logger=logger,
            config=performance_config.get('signal_processing', {}),
            signal_generator=mock_fast_dependencies['signal_generator'],
            alert_manager=mock_fast_dependencies['alert_manager'],
            market_data_manager=mock_fast_dependencies['market_data_manager'],
            database_client=mock_fast_dependencies['database_client']
        )
        
        whale_monitor = WhaleActivityMonitor(
            logger=logger,
            config=performance_config,
            alert_manager=mock_fast_dependencies['alert_manager']
        )
        
        manipulation_monitor = ManipulationMonitor(
            logger=logger,
            config=performance_config,
            alert_manager=mock_fast_dependencies['alert_manager'],
            manipulation_detector=mock_fast_dependencies['manipulation_detector'],
            database_client=mock_fast_dependencies['database_client']
        )
        
        health_monitor = ComponentHealthMonitor(
            logger=logger,
            config=performance_config.get('health', {}),
            database_client=mock_fast_dependencies['database_client']
        )
        
        # Create orchestration service
        orchestration_service = MonitoringOrchestrationService(
            websocket_processor=websocket_processor,
            market_data_processor=market_data_processor,
            signal_processor=signal_processor,
            whale_activity_monitor=whale_monitor,
            manipulation_monitor=manipulation_monitor,
            component_health_monitor=health_monitor,
            market_data_validator=validator,
            alert_manager=mock_fast_dependencies['alert_manager'],
            top_symbols_manager=mock_fast_dependencies['top_symbols_manager'],
            logger=logger,
            config=performance_config
        )
        
        return orchestration_service

    @pytest.mark.asyncio
    async def test_single_symbol_processing_performance(self, performance_system):
        """Test performance of processing a single symbol."""
        orchestration_service = performance_system
        
        # Measure processing time for single symbol
        iterations = 10
        processing_times = []
        
        for _ in range(iterations):
            start_time = time.time()
            await orchestration_service._process_symbol_with_components('BTCUSDT')
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
        
        # Calculate performance metrics
        avg_time = statistics.mean(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)
        std_dev = statistics.stdev(processing_times) if len(processing_times) > 1 else 0
        
        # Performance assertions
        assert avg_time < 0.5, f"Average processing time {avg_time:.3f}s exceeds 0.5s threshold"
        assert max_time < 1.0, f"Max processing time {max_time:.3f}s exceeds 1.0s threshold"
        assert std_dev < 0.2, f"Standard deviation {std_dev:.3f}s indicates inconsistent performance"
        
        # Verify successful processing
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['processed_symbols'] == iterations
        assert stats['successful_analyses'] == iterations
        assert stats['success_rate'] == 1.0

    @pytest.mark.asyncio
    async def test_concurrent_symbol_processing_performance(self, performance_system):
        """Test performance of concurrent symbol processing."""
        orchestration_service = performance_system
        
        # Test symbols
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT']
        
        # Measure concurrent processing time
        start_time = time.time()
        
        # Process all symbols concurrently
        tasks = [
            orchestration_service._process_symbol_with_components(symbol)
            for symbol in symbols
        ]
        await asyncio.gather(*tasks)
        
        concurrent_time = time.time() - start_time
        
        # Measure sequential processing time for comparison
        start_time = time.time()
        for symbol in symbols:
            await orchestration_service._process_symbol_with_components(symbol)
        sequential_time = time.time() - start_time
        
        # Concurrent processing should be significantly faster
        performance_improvement = sequential_time / concurrent_time
        assert performance_improvement > 2.0, f"Concurrent processing only {performance_improvement:.2f}x faster than sequential"
        
        # Verify all symbols were processed successfully
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['processed_symbols'] == len(symbols) * 2  # Both concurrent and sequential runs
        assert stats['success_rate'] == 1.0

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, performance_system):
        """Test that memory usage remains stable during extended processing."""
        orchestration_service = performance_system
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many symbols to test memory stability
        for i in range(50):
            await orchestration_service._process_symbol_with_components(f'TEST{i}USDT')
            
            # Check memory every 10 iterations
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable (less than 100MB for 50 symbols)
                assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB after {i+1} symbols"
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 150, f"Total memory increase {total_memory_increase:.2f}MB exceeds threshold"

    @pytest.mark.asyncio
    async def test_high_frequency_processing(self, performance_system):
        """Test system performance under high-frequency processing scenarios."""
        orchestration_service = performance_system
        
        # Simulate high-frequency trading scenario
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        processing_rounds = 20
        max_concurrent = 5
        
        total_start_time = time.time()
        
        for round_num in range(processing_rounds):
            round_start = time.time()
            
            # Process symbols in batches
            for i in range(0, len(symbols), max_concurrent):
                batch = symbols[i:i + max_concurrent]
                tasks = [
                    orchestration_service._process_symbol_with_components(symbol)
                    for symbol in batch
                ]
                await asyncio.gather(*tasks)
            
            round_time = time.time() - round_start
            
            # Each round should complete quickly
            assert round_time < 2.0, f"Round {round_num} took {round_time:.3f}s, exceeds 2.0s threshold"
        
        total_time = time.time() - total_start_time
        
        # Calculate throughput
        total_symbols_processed = len(symbols) * processing_rounds
        throughput = total_symbols_processed / total_time
        
        # Should achieve reasonable throughput
        assert throughput > 5.0, f"Throughput {throughput:.2f} symbols/sec below 5.0 threshold"
        
        # Verify all processing completed successfully
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['processed_symbols'] == total_symbols_processed
        assert stats['success_rate'] == 1.0

    @pytest.mark.asyncio
    async def test_error_handling_performance_impact(self, performance_system):
        """Test that error handling doesn't significantly impact performance."""
        orchestration_service = performance_system
        
        # Test normal processing performance
        normal_times = []
        for _ in range(10):
            start_time = time.time()
            await orchestration_service._process_symbol_with_components('BTCUSDT')
            normal_times.append(time.time() - start_time)
        
        avg_normal_time = statistics.mean(normal_times)
        
        # Introduce errors and test performance
        market_data_processor = orchestration_service.market_data_processor
        original_fetch = market_data_processor.fetch_market_data
        
        # Mock fetch to fail 50% of the time
        call_count = 0
        async def error_prone_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Simulated network error")
            return await original_fetch(*args, **kwargs)
        
        market_data_processor.fetch_market_data = error_prone_fetch
        
        # Test performance with errors
        error_times = []
        for _ in range(10):
            start_time = time.time()
            await orchestration_service._process_symbol_with_components('BTCUSDT')
            error_times.append(time.time() - start_time)
        
        avg_error_time = statistics.mean(error_times)
        
        # Restore original function
        market_data_processor.fetch_market_data = original_fetch
        
        # Error handling should not significantly slow down processing
        performance_impact = avg_error_time / avg_normal_time
        assert performance_impact < 2.0, f"Error handling caused {performance_impact:.2f}x slowdown, exceeds 2.0x threshold"

    @pytest.mark.asyncio
    async def test_component_isolation_performance(self, performance_system):
        """Test that component isolation doesn't introduce performance overhead."""
        orchestration_service = performance_system
        
        # Test individual component performance
        component_times = {}
        
        # Test market data processor
        start_time = time.time()
        for _ in range(20):
            await orchestration_service.market_data_processor.fetch_market_data('BTCUSDT')
        component_times['market_data'] = (time.time() - start_time) / 20
        
        # Test signal processor
        start_time = time.time()
        for _ in range(20):
            await orchestration_service.signal_processor.analyze_confluence_and_generate_signals({
                'symbol': 'BTCUSDT',
                'price': 47200,
                'ohlcv': {'base': []},
                'orderbook': {'bids': [], 'asks': []},
                'trades': []
            })
        component_times['signal'] = (time.time() - start_time) / 20
        
        # Test whale activity monitor
        start_time = time.time()
        for _ in range(20):
            await orchestration_service.whale_activity_monitor.monitor_whale_activity('BTCUSDT', {
                'price': 47200,
                'orderbook': {'bids': [[47180, 10]], 'asks': [[47220, 12]]},
                'trades': []
            })
        component_times['whale'] = (time.time() - start_time) / 20
        
        # Test manipulation monitor
        start_time = time.time()
        for _ in range(20):
            await orchestration_service.manipulation_monitor.monitor_manipulation_activity('BTCUSDT', {
                'price': 47200,
                'trades': [{'amount': 1.5, 'price': 47200, 'timestamp': int(time.time() * 1000)}]
            })
        component_times['manipulation'] = (time.time() - start_time) / 20
        
        # All components should perform efficiently
        for component, avg_time in component_times.items():
            assert avg_time < 0.1, f"{component} component takes {avg_time:.3f}s per call, exceeds 0.1s threshold"

    @pytest.mark.asyncio
    async def test_service_orchestration_overhead(self, performance_system):
        """Test that service orchestration doesn't add significant overhead."""
        orchestration_service = performance_system
        
        # Test direct component calls vs orchestrated calls
        symbol = 'BTCUSDT'
        test_data = {
            'symbol': symbol,
            'price': 47200,
            'ohlcv': {'base': []},
            'orderbook': {'bids': [[47180, 10]], 'asks': [[47220, 12]]},
            'trades': [{'amount': 1.5, 'price': 47200, 'timestamp': int(time.time() * 1000)}]
        }
        
        # Measure direct component calls
        direct_start = time.time()
        for _ in range(10):
            # Simulate direct calls
            await orchestration_service.market_data_processor.fetch_market_data(symbol)
            await orchestration_service.signal_processor.analyze_confluence_and_generate_signals(test_data)
            await orchestration_service.whale_activity_monitor.monitor_whale_activity(symbol, test_data)
            await orchestration_service.manipulation_monitor.monitor_manipulation_activity(symbol, test_data)
        direct_time = time.time() - direct_start
        
        # Measure orchestrated calls
        orchestrated_start = time.time()
        for _ in range(10):
            await orchestration_service._process_symbol_with_components(symbol)
        orchestrated_time = time.time() - orchestrated_start
        
        # Orchestration overhead should be minimal
        overhead_ratio = orchestrated_time / direct_time
        assert overhead_ratio < 1.5, f"Service orchestration adds {overhead_ratio:.2f}x overhead, exceeds 1.5x threshold"

    @pytest.mark.asyncio
    async def test_scalability_characteristics(self, performance_system):
        """Test system scalability with increasing workload."""
        orchestration_service = performance_system
        
        # Test with increasing numbers of symbols
        symbol_counts = [1, 5, 10, 20, 30]
        processing_times = []
        
        for count in symbol_counts:
            symbols = [f'SYMBOL{i}USDT' for i in range(count)]
            
            start_time = time.time()
            tasks = [
                orchestration_service._process_symbol_with_components(symbol)
                for symbol in symbols
            ]
            await asyncio.gather(*tasks)
            processing_time = time.time() - start_time
            
            processing_times.append(processing_time)
            
            # Log performance metrics
            throughput = count / processing_time
            print(f"Processed {count} symbols in {processing_time:.3f}s (throughput: {throughput:.2f} symbols/sec)")
        
        # Verify reasonable scaling characteristics
        # Processing time should scale sublinearly with concurrent execution
        for i in range(1, len(symbol_counts)):
            prev_count, curr_count = symbol_counts[i-1], symbol_counts[i]
            prev_time, curr_time = processing_times[i-1], processing_times[i]
            
            scaling_factor = curr_time / prev_time
            workload_factor = curr_count / prev_count
            
            # Due to concurrency, scaling should be better than linear
            assert scaling_factor < workload_factor, f"Poor scaling from {prev_count} to {curr_count} symbols"

    def test_architecture_performance_benefits(self, performance_system):
        """Test that the modular architecture provides performance benefits."""
        orchestration_service = performance_system
        
        # Verify that components can be used independently for performance
        components = {
            'websocket': orchestration_service.websocket_processor,
            'market_data': orchestration_service.market_data_processor,
            'signal': orchestration_service.signal_processor,
            'whale': orchestration_service.whale_activity_monitor,
            'manipulation': orchestration_service.manipulation_monitor,
            'health': orchestration_service.component_health_monitor
        }
        
        # Each component should be independently accessible
        for name, component in components.items():
            assert component is not None, f"{name} component not accessible"
            assert hasattr(component, 'logger'), f"{name} component missing logger"
        
        # Service should provide comprehensive statistics
        stats = orchestration_service.get_monitoring_statistics()
        assert 'component_stats' in stats
        assert len(stats['component_stats']) > 0
        
        # Service status should include performance metrics
        status = orchestration_service.get_service_status()
        assert 'statistics' in status
        assert 'component_dependencies' in status 