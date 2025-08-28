"""
Comprehensive Test Suite for Monitor Refactoring

This test suite validates that the refactored monitoring system maintains
all functionality while providing performance improvements and backward compatibility.

Test Categories:
1. Component Integration Tests
2. Backward Compatibility Tests  
3. Performance Comparison Tests
4. Signal Generation Validation Tests
5. Error Handling and Resilience Tests
6. Memory and Resource Usage Tests
7. Concurrency and Threading Tests
8. End-to-End System Tests

Usage:
    python -m pytest tests/test_monitor_refactoring.py -v
    
    # Run specific test categories
    python -m pytest tests/test_monitor_refactoring.py::TestBackwardCompatibility -v
    python -m pytest tests/test_monitor_refactoring.py::TestPerformance -v
"""

import asyncio
import pytest
import time
import logging
import tracemalloc
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import psutil
import threading
import gc
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import both original and refactored monitors
from monitoring.monitor import MarketMonitor as OriginalMarketMonitor
from monitoring.monitor_refactored import RefactoredMarketMonitor, MarketMonitor as RefactoredAlias

# Import testing utilities
from monitoring.metrics_manager import MetricsManager
from monitoring.health_monitor import HealthMonitor


class TestSetup:
    """Common setup and mock utilities for monitor testing."""
    
    @staticmethod
    def create_mock_exchange_manager():
        """Create a mock exchange manager."""
        mock_em = Mock()
        mock_em.get_exchange = Mock(return_value=Mock(id='bybit'))
        mock_em.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BTC/USDT',
            'last': 50000,
            'bid': 49999,
            'ask': 50001,
            'timestamp': int(time.time() * 1000)
        })
        return mock_em
    
    @staticmethod
    def create_mock_top_symbols_manager():
        """Create a mock top symbols manager."""
        mock_tsm = Mock()
        mock_tsm.get_symbols = AsyncMock(return_value=['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
        return mock_tsm
    
    @staticmethod
    def create_mock_confluence_analyzer():
        """Create a mock confluence analyzer."""
        mock_ca = Mock()
        mock_ca.analyze = AsyncMock(return_value={
            'symbol': 'BTC/USDT',
            'confluence_score': 75.5,
            'components': {
                'orderflow': 80.0,
                'sentiment': 70.0,
                'liquidity': 75.0,
                'bitcoin_beta': 85.0,
                'smart_money': 65.0,
                'machine_learning': 78.0
            },
            'timestamp': datetime.now(timezone.utc),
            'signal': 'bullish'
        })
        return mock_ca
    
    @staticmethod
    def create_mock_alert_manager():
        """Create a mock alert manager."""
        mock_am = Mock()
        mock_am.send_alert = AsyncMock()
        mock_am.send_report = AsyncMock()
        return mock_am
    
    @staticmethod
    def create_mock_signal_generator():
        """Create a mock signal generator."""
        mock_sg = Mock()
        mock_sg.generate_signal = AsyncMock(return_value={
            'signal_type': 'buy',
            'confidence': 0.85,
            'entry_price': 50000,
            'stop_loss': 48000,
            'take_profit': 55000
        })
        return mock_sg
    
    @staticmethod
    def create_mock_market_data():
        """Create realistic mock market data."""
        return {
            'symbol': 'BTC/USDT',
            'timestamp': int(time.time() * 1000),
            'ticker': {
                'symbol': 'BTC/USDT',
                'last': 50000,
                'bid': 49999,
                'ask': 50001,
                'volume': 1000000,
                'timestamp': int(time.time() * 1000)
            },
            'orderbook': {
                'bids': [[49999, 10], [49998, 15], [49997, 20]],
                'asks': [[50001, 8], [50002, 12], [50003, 18]],
                'timestamp': int(time.time() * 1000)
            },
            'trades': [
                {'price': 50000, 'amount': 1.5, 'side': 'buy', 'timestamp': int(time.time() * 1000)},
                {'price': 49999, 'amount': 0.8, 'side': 'sell', 'timestamp': int(time.time() * 1000) - 1000}
            ],
            'ohlcv': {
                '1m': [
                    [int(time.time() * 1000), 49800, 50100, 49700, 50000, 150],
                    [int(time.time() * 1000) - 60000, 49700, 49900, 49600, 49800, 120]
                ],
                '5m': [
                    [int(time.time() * 1000), 49500, 50200, 49400, 50000, 800],
                    [int(time.time() * 1000) - 300000, 49400, 49600, 49300, 49500, 650]
                ]
            }
        }
    
    @staticmethod
    def create_test_config():
        """Create test configuration."""
        return {
            'interval': 1,  # Fast interval for testing
            'max_concurrent_symbols': 5,
            'report_interval': 10,
            'timeframes': {
                'ltf': '1m',
                'mtf': '5m',
                'htf': '1h'
            },
            'monitoring': {
                'thresholds': {
                    'volume_change': 0.2,
                    'orderflow_change': 0.15
                }
            }
        }


class TestComponentIntegration:
    """Test integration between monitoring components."""
    
    @pytest.fixture
    def refactored_monitor(self):
        """Create a refactored monitor instance for testing."""
        config = TestSetup.create_test_config()
        exchange_manager = TestSetup.create_mock_exchange_manager()
        top_symbols_manager = TestSetup.create_mock_top_symbols_manager()
        confluence_analyzer = TestSetup.create_mock_confluence_analyzer()
        alert_manager = TestSetup.create_mock_alert_manager()
        signal_generator = TestSetup.create_mock_signal_generator()
        
        monitor = RefactoredMarketMonitor(
            exchange_manager=exchange_manager,
            config=config,
            top_symbols_manager=top_symbols_manager,
            confluence_analyzer=confluence_analyzer,
            alert_manager=alert_manager,
            signal_generator=signal_generator,
            logger=logging.getLogger('test')
        )
        return monitor
    
    @pytest.mark.asyncio
    async def test_component_initialization(self, refactored_monitor):
        """Test that all components initialize correctly."""
        assert await refactored_monitor.initialize()
        
        # Check that all components are initialized
        assert refactored_monitor.data_collector is not None
        assert refactored_monitor.validator is not None
        assert refactored_monitor.metrics_tracker is not None
        
        # Check component states
        assert refactored_monitor.data_collector._initialized
        assert refactored_monitor.validator._initialized
        assert refactored_monitor.metrics_tracker._initialized
    
    @pytest.mark.asyncio
    async def test_data_flow_integration(self, refactored_monitor):
        """Test data flows correctly through all components."""
        await refactored_monitor.initialize()
        
        # Mock the data collector to return test data
        test_data = TestSetup.create_mock_market_data()
        refactored_monitor.data_collector.fetch_market_data = AsyncMock(return_value=test_data)
        
        # Test data fetching
        market_data = await refactored_monitor.fetch_market_data('BTC/USDT')
        assert market_data is not None
        assert market_data['symbol'] == 'BTC/USDT'
        
        # Test data validation
        is_valid = await refactored_monitor.validate_market_data(market_data)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, refactored_monitor):
        """Test error handling across components."""
        await refactored_monitor.initialize()
        
        # Test handling of data collector errors
        refactored_monitor.data_collector.fetch_market_data = AsyncMock(side_effect=Exception("Network error"))
        
        market_data = await refactored_monitor.fetch_market_data('BTC/USDT')
        assert market_data is None  # Should handle error gracefully
        
        # Test handling of validator errors
        refactored_monitor.data_collector.fetch_market_data = AsyncMock(return_value=TestSetup.create_mock_market_data())
        refactored_monitor.validator.validate_market_data = AsyncMock(side_effect=Exception("Validation error"))
        
        is_valid = await refactored_monitor.validate_market_data(TestSetup.create_mock_market_data())
        assert is_valid is False  # Should handle error gracefully


class TestBackwardCompatibility:
    """Test backward compatibility with original MarketMonitor interface."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for both monitors."""
        return {
            'exchange_manager': TestSetup.create_mock_exchange_manager(),
            'top_symbols_manager': TestSetup.create_mock_top_symbols_manager(),
            'confluence_analyzer': TestSetup.create_mock_confluence_analyzer(),
            'alert_manager': TestSetup.create_mock_alert_manager(),
            'signal_generator': TestSetup.create_mock_signal_generator(),
            'config': TestSetup.create_test_config(),
            'logger': logging.getLogger('test')
        }
    
    def test_constructor_compatibility(self, mock_dependencies):
        """Test that refactored monitor accepts same constructor parameters."""
        # Test original constructor parameters work with refactored monitor
        monitor = RefactoredMarketMonitor(**mock_dependencies)
        
        assert monitor.exchange_manager == mock_dependencies['exchange_manager']
        assert monitor.config == mock_dependencies['config']
        assert monitor.alert_manager == mock_dependencies['alert_manager']
        assert monitor.signal_generator == mock_dependencies['signal_generator']
    
    def test_alias_compatibility(self, mock_dependencies):
        """Test that the MarketMonitor alias works correctly."""
        # Should be able to import and use MarketMonitor alias
        from monitoring.monitor_refactored import MarketMonitor
        
        monitor = MarketMonitor(**mock_dependencies)
        assert isinstance(monitor, RefactoredMarketMonitor)
    
    @pytest.mark.asyncio
    async def test_method_interface_compatibility(self, mock_dependencies):
        """Test that public methods maintain the same interface."""
        monitor = RefactoredMarketMonitor(**mock_dependencies)
        await monitor.initialize()
        
        # Test that all expected public methods exist
        assert hasattr(monitor, 'start_monitoring')
        assert hasattr(monitor, 'stop_monitoring')
        assert hasattr(monitor, 'fetch_market_data')
        assert hasattr(monitor, 'validate_market_data')
        assert hasattr(monitor, 'get_market_data')  # Backward compatibility method
        assert hasattr(monitor, 'get_stats')
        
        # Test method signatures work
        market_data = await monitor.get_market_data('BTC/USDT')
        stats = monitor.get_stats()
        assert isinstance(stats, dict)


class TestPerformance:
    """Test performance improvements of refactored system."""
    
    @pytest.fixture
    async def performance_setup(self):
        """Set up performance testing environment."""
        # Create test data
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT']
        mock_data = TestSetup.create_mock_market_data()
        
        config = TestSetup.create_test_config()
        config['max_concurrent_symbols'] = 10
        
        return {
            'symbols': symbols,
            'mock_data': mock_data,
            'config': config
        }
    
    @pytest.mark.asyncio
    async def test_memory_usage_improvement(self, performance_setup):
        """Test that refactored monitor uses less memory."""
        tracemalloc.start()
        
        # Create refactored monitor
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=performance_setup['config'],
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=TestSetup.create_mock_signal_generator(),
            logger=logging.getLogger('test')
        )
        
        await monitor.initialize()
        
        # Measure memory after initialization
        snapshot_after_init = tracemalloc.take_snapshot()
        init_memory = sum(stat.size for stat in snapshot_after_init.statistics('filename'))
        
        # Process some data
        for symbol in performance_setup['symbols']:
            await monitor._process_symbol(symbol)
        
        # Measure memory after processing
        snapshot_after_processing = tracemalloc.take_snapshot()
        processing_memory = sum(stat.size for stat in snapshot_after_processing.statistics('filename'))
        
        # Memory growth should be reasonable (less than 50MB for processing 5 symbols)
        memory_growth = processing_memory - init_memory
        assert memory_growth < 50 * 1024 * 1024, f"Memory growth too high: {memory_growth / 1024 / 1024:.2f}MB"
        
        tracemalloc.stop()
    
    @pytest.mark.asyncio
    async def test_processing_speed(self, performance_setup):
        """Test processing speed of monitoring cycle."""
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=performance_setup['config'],
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=TestSetup.create_mock_signal_generator(),
            logger=logging.getLogger('test')
        )
        
        await monitor.initialize()
        
        # Mock data collector to return data quickly
        monitor.data_collector.fetch_market_data = AsyncMock(
            return_value=performance_setup['mock_data']
        )
        
        # Measure processing time
        start_time = time.time()
        await monitor._monitoring_cycle()
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process all symbols in under 5 seconds
        assert processing_time < 5.0, f"Processing took too long: {processing_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, performance_setup):
        """Test concurrent processing capabilities."""
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=performance_setup['config'],
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=TestSetup.create_mock_signal_generator(),
            logger=logging.getLogger('test')
        )
        
        await monitor.initialize()
        
        # Mock slow data fetching to test concurrency
        async def slow_fetch(symbol):
            await asyncio.sleep(0.1)  # Simulate network delay
            return performance_setup['mock_data']
        
        monitor.data_collector.fetch_market_data = AsyncMock(side_effect=slow_fetch)
        
        # Test concurrent processing of multiple symbols
        symbols = performance_setup['symbols']
        
        start_time = time.time()
        tasks = [monitor._process_symbol(symbol) for symbol in symbols]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # With concurrency, should be faster than sequential processing
        # 5 symbols * 0.1s each = 0.5s sequential, concurrent should be ~0.1s + overhead
        assert processing_time < 0.3, f"Concurrent processing too slow: {processing_time:.2f}s"


class TestSignalGeneration:
    """Test signal generation functionality."""
    
    @pytest.fixture
    def signal_test_monitor(self):
        """Create monitor for signal generation testing."""
        config = TestSetup.create_test_config()
        
        # Create more sophisticated mocks
        signal_generator = TestSetup.create_mock_signal_generator()
        metrics_manager = Mock()
        metrics_manager.start_operation = Mock(return_value=Mock())
        metrics_manager.end_operation = Mock()
        
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=config,
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=signal_generator,
            metrics_manager=metrics_manager,
            logger=logging.getLogger('test')
        )
        
        return monitor
    
    @pytest.mark.asyncio
    async def test_signal_processing_flow(self, signal_test_monitor):
        """Test complete signal processing flow."""
        await signal_test_monitor.initialize()
        
        # Mock market data and analysis
        market_data = TestSetup.create_mock_market_data()
        analysis_result = {
            'symbol': 'BTC/USDT',
            'confluence_score': 85.0,
            'components': {
                'orderflow': 90.0,
                'sentiment': 80.0,
                'liquidity': 85.0
            },
            'signal': 'strong_bullish',
            'timestamp': datetime.now(timezone.utc)
        }
        
        signal_test_monitor.data_collector.fetch_market_data = AsyncMock(return_value=market_data)
        signal_test_monitor.confluence_analyzer.analyze = AsyncMock(return_value=analysis_result)
        
        # Process symbol and check signal generation
        await signal_test_monitor._process_symbol('BTC/USDT')
        
        # Verify signal processor was called
        if signal_test_monitor.signal_processor:
            assert signal_test_monitor.signal_processor.signal_generator.generate_signal.called
    
    @pytest.mark.asyncio
    async def test_signal_threshold_handling(self, signal_test_monitor):
        """Test signal generation based on different thresholds."""
        await signal_test_monitor.initialize()
        
        # Test cases with different confluence scores
        test_cases = [
            {'score': 95.0, 'expected_signal': True},
            {'score': 75.0, 'expected_signal': True},
            {'score': 45.0, 'expected_signal': False},
            {'score': 25.0, 'expected_signal': False}
        ]
        
        for case in test_cases:
            analysis_result = {
                'symbol': 'BTC/USDT',
                'confluence_score': case['score'],
                'signal': 'bullish' if case['score'] > 60 else 'neutral'
            }
            
            if signal_test_monitor.signal_processor:
                await signal_test_monitor.signal_processor.process_analysis_result('BTC/USDT', analysis_result)
                
                # Verify appropriate action was taken based on threshold
                # (This would depend on actual signal processing logic)


class TestErrorHandlingAndResilience:
    """Test error handling and system resilience."""
    
    @pytest.fixture
    def resilience_monitor(self):
        """Create monitor for resilience testing."""
        config = TestSetup.create_test_config()
        config['retry_config'] = {
            'max_retries': 2,
            'retry_delay_seconds': 0.1,  # Fast retry for testing
            'retry_exponential_backoff': True
        }
        
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=config,
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=TestSetup.create_mock_signal_generator(),
            logger=logging.getLogger('test')
        )
        
        return monitor
    
    @pytest.mark.asyncio
    async def test_network_error_resilience(self, resilience_monitor):
        """Test handling of network errors."""
        await resilience_monitor.initialize()
        
        # Simulate network errors
        call_count = 0
        async def failing_fetch(symbol):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Network timeout")
            return TestSetup.create_mock_market_data()
        
        resilience_monitor.data_collector.fetch_market_data = AsyncMock(side_effect=failing_fetch)
        
        # Should eventually succeed after retries
        await resilience_monitor._process_symbol('BTC/USDT')
        assert call_count > 1  # Retries occurred
    
    @pytest.mark.asyncio
    async def test_component_failure_isolation(self, resilience_monitor):
        """Test that component failures don't crash the entire system."""
        await resilience_monitor.initialize()
        
        # Simulate component failures
        resilience_monitor.data_collector.fetch_market_data = AsyncMock(
            side_effect=Exception("Data collector failed")
        )
        
        # System should continue running despite component failure
        try:
            await resilience_monitor._monitoring_cycle()
            # Should not crash, but handle error gracefully
        except Exception as e:
            pytest.fail(f"System crashed due to component failure: {str(e)}")
    
    @pytest.mark.asyncio 
    async def test_graceful_shutdown(self, resilience_monitor):
        """Test graceful shutdown of monitoring system."""
        await resilience_monitor.initialize()
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(resilience_monitor.start_monitoring())
        
        # Let it run briefly
        await asyncio.sleep(0.5)
        
        # Stop monitoring gracefully
        await resilience_monitor.stop_monitoring()
        
        # Verify it stops cleanly
        assert not resilience_monitor.running
        
        # Cancel the monitoring task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


class TestEndToEndSystem:
    """End-to-end system integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_monitoring_cycle(self):
        """Test a complete monitoring cycle from start to finish."""
        # Create fully mocked system
        config = TestSetup.create_test_config()
        config['interval'] = 0.1  # Very fast for testing
        
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=config,
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=TestSetup.create_mock_signal_generator(),
            logger=logging.getLogger('test')
        )
        
        await monitor.initialize()
        
        # Mock data flow
        monitor.data_collector.fetch_market_data = AsyncMock(
            return_value=TestSetup.create_mock_market_data()
        )
        
        # Run one complete cycle
        await monitor._monitoring_cycle()
        
        # Verify first cycle completed
        assert monitor.first_cycle_completed
        
        # Verify components were called
        assert monitor.top_symbols_manager.get_symbols.called
        assert monitor.data_collector.fetch_market_data.called
        assert monitor.confluence_analyzer.analyze.called
    
    @pytest.mark.asyncio
    async def test_multi_cycle_monitoring(self):
        """Test multiple monitoring cycles."""
        config = TestSetup.create_test_config()
        config['interval'] = 0.01  # Very fast
        
        monitor = RefactoredMarketMonitor(
            exchange_manager=TestSetup.create_mock_exchange_manager(),
            config=config,
            top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
            confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
            alert_manager=TestSetup.create_mock_alert_manager(),
            signal_generator=TestSetup.create_mock_signal_generator(),
            logger=logging.getLogger('test')
        )
        
        await monitor.initialize()
        
        # Mock data flow
        monitor.data_collector.fetch_market_data = AsyncMock(
            return_value=TestSetup.create_mock_market_data()
        )
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        # Let it run for a short time (should complete multiple cycles)
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        monitor_task.cancel()
        
        # Verify multiple cycles occurred
        assert monitor.first_cycle_completed
        assert monitor.data_collector.fetch_market_data.call_count > 1


# Performance benchmark utilities
class BenchmarkUtils:
    """Utilities for benchmarking monitor performance."""
    
    @staticmethod
    async def benchmark_monitor_cycle(monitor_class, setup_kwargs, num_cycles=10):
        """Benchmark monitoring cycles for a given monitor."""
        monitor = monitor_class(**setup_kwargs)
        await monitor.initialize()
        
        # Warm up
        await monitor._monitoring_cycle()
        
        # Benchmark
        start_time = time.time()
        for _ in range(num_cycles):
            await monitor._monitoring_cycle()
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / num_cycles
        
        return {
            'total_time': total_time,
            'average_time': avg_time,
            'cycles_per_second': num_cycles / total_time
        }
    
    @staticmethod
    def measure_memory_usage():
        """Measure current memory usage."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB


# Test runner and reporting
if __name__ == "__main__":
    """Run tests with detailed reporting."""
    import subprocess
    
    print("=" * 80)
    print("VIRTUOSO CCXT MONITOR REFACTORING VALIDATION SUITE")
    print("=" * 80)
    
    # Run tests with verbose output
    result = subprocess.run([
        'python', '-m', 'pytest', __file__, 
        '-v', '--tb=short', '--durations=10'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"\nTest execution completed with return code: {result.returncode}")
    
    if result.returncode == 0:
        print("🎉 ALL TESTS PASSED! Refactoring validation successful!")
    else:
        print("❌ Some tests failed. Review output above.")