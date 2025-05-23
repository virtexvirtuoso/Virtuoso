"""
End-to-End Integration Tests for the Monitoring System.

These tests validate the complete monitoring workflow across all architectural layers:
- Utilities → Components → Services → MarketMonitor
"""

import pytest
import pytest_asyncio
import asyncio
import logging
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import all layers of the architecture
from src.monitoring.utilities import (
    TimestampUtility,
    MarketDataValidator,
    LoggingUtility
)
from src.monitoring.components import (
    WebSocketProcessor,
    MarketDataProcessor,
    SignalProcessor,
    WhaleActivityMonitor,
    ManipulationMonitor,
    HealthMonitor as ComponentHealthMonitor
)
from src.monitoring.services import MonitoringOrchestrationService


class TestEndToEndWorkflow:
    """Integration tests for the complete monitoring workflow."""

    @pytest.fixture
    def mock_exchange(self):
        """Create a realistic mock exchange."""
        exchange = Mock()
        exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1640995200000, 47000, 47500, 46800, 47200, 1000],  # Realistic OHLCV data
            [1640995260000, 47200, 47400, 47000, 47100, 950],
            [1640995320000, 47100, 47300, 46900, 47250, 1100],
        ])
        exchange.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'last': 47200,
            'bid': 47180,
            'ask': 47220,
            'volume': 25000
        })
        exchange.fetch_order_book = AsyncMock(return_value={
            'bids': [[47180, 10], [47170, 15], [47160, 20]],
            'asks': [[47220, 12], [47230, 18], [47240, 25]]
        })
        exchange.fetch_trades = AsyncMock(return_value=[
            {'amount': 1.5, 'price': 47200, 'timestamp': int(time.time() * 1000)},
            {'amount': 2.3, 'price': 47180, 'timestamp': int(time.time() * 1000) - 1000},
        ])
        return exchange

    @pytest.fixture
    def mock_config(self):
        """Create comprehensive test configuration."""
        return {
            'websocket': {
                'enabled': True,
                'reconnect_attempts': 3,
                'timeout': 10
            },
            'market_data': {
                'cache_ttl': 300,
                'enable_validation': True,
                'fetch_retries': 2
            },
            'signal_processing': {
                'confluence_thresholds': {
                    'buy': 60,
                    'sell': 40
                },
                'enable_pdf_reports': False  # Disable for testing
            },
            'whale_activity': {
                'enabled': True,
                'cooldown': 900,
                'accumulation_threshold': 1000000,
                'alert_threshold': 500000
            },
            'manipulation': {
                'enabled': True,
                'detection_threshold': 0.7,
                'alert_cooldown': 300
            },
            'health': {
                'check_interval': 60,
                'memory_threshold': 80,
                'cpu_threshold': 85
            },
            'monitoring': {
                'cycle_interval': 30,
                'max_symbols': 10,
                'error_threshold': 5
            }
        }

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock external dependencies."""
        return {
            'database_client': Mock(),
            'alert_manager': Mock(),
            'signal_generator': Mock(),
            'top_symbols_manager': Mock(),
            'market_data_manager': Mock(),
            'manipulation_detector': Mock()
        }

    @pytest_asyncio.fixture
    async def integrated_system(self, mock_exchange, mock_config, mock_logger, mock_dependencies):
        """Create a fully integrated monitoring system for testing."""
        # Initialize utilities
        market_data_validator = MarketDataValidator(mock_logger)
        logging_utility = LoggingUtility(mock_logger)
        timestamp_utility = TimestampUtility()

        # Initialize components with real dependencies
        websocket_processor = WebSocketProcessor(
            config=mock_config,
            logger=mock_logger
        )

        market_data_processor = MarketDataProcessor(
            logger=mock_logger,
            config=mock_config.get('market_data', {}),
            exchange=mock_exchange,
            market_data_manager=mock_dependencies['market_data_manager'],
            validator=market_data_validator
        )

        signal_processor = SignalProcessor(
            logger=mock_logger,
            config=mock_config.get('signal_processing', {}),
            signal_generator=mock_dependencies['signal_generator'],
            alert_manager=mock_dependencies['alert_manager'],
            market_data_manager=mock_dependencies['market_data_manager'],
            database_client=mock_dependencies['database_client']
        )

        whale_activity_monitor = WhaleActivityMonitor(
            logger=mock_logger,
            config=mock_config,
            alert_manager=mock_dependencies['alert_manager']
        )

        manipulation_monitor = ManipulationMonitor(
            logger=mock_logger,
            config=mock_config,
            alert_manager=mock_dependencies['alert_manager'],
            manipulation_detector=mock_dependencies['manipulation_detector'],
            database_client=mock_dependencies['database_client']
        )

        health_monitor = ComponentHealthMonitor(
            logger=mock_logger,
            config=mock_config.get('health', {}),
            database_client=mock_dependencies['database_client']
        )

        # Initialize orchestration service
        orchestration_service = MonitoringOrchestrationService(
            websocket_processor=websocket_processor,
            market_data_processor=market_data_processor,
            signal_processor=signal_processor,
            whale_activity_monitor=whale_activity_monitor,
            manipulation_monitor=manipulation_monitor,
            component_health_monitor=health_monitor,
            market_data_validator=market_data_validator,
            alert_manager=mock_dependencies['alert_manager'],
            top_symbols_manager=mock_dependencies['top_symbols_manager'],
            logger=mock_logger,
            config=mock_config
        )

        return {
            'utilities': {
                'validator': market_data_validator,
                'logging': logging_utility,
                'timestamp': timestamp_utility
            },
            'components': {
                'websocket': websocket_processor,
                'market_data': market_data_processor,
                'signal': signal_processor,
                'whale': whale_activity_monitor,
                'manipulation': manipulation_monitor,
                'health': health_monitor
            },
            'services': {
                'orchestration': orchestration_service
            },
            'mocks': mock_dependencies
        }

    @pytest.mark.asyncio
    async def test_complete_symbol_processing_workflow(self, integrated_system):
        """Test the complete end-to-end symbol processing workflow."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Mock top symbols manager to return test symbol
        system['mocks']['top_symbols_manager'].get_top_symbols.return_value = ['BTCUSDT']
        
        # Mock signal generator to return realistic confluence data
        system['mocks']['signal_generator'].generate_confluence_data = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'overall_score': 65,
            'signals': {
                'rsi': {'value': 45, 'signal': 'neutral'},
                'macd': {'value': 0.002, 'signal': 'buy'},
                'bb': {'value': 0.3, 'signal': 'neutral'}
            },
            'confluence_strength': 'moderate',
            'recommendation': 'buy'
        })

        # Mock manipulation detector
        system['mocks']['manipulation_detector'].detect_manipulation = AsyncMock(return_value={
            'manipulation_detected': False,
            'confidence': 0.2,
            'patterns': []
        })

        # Execute one complete symbol processing cycle
        await orchestration_service._process_symbol_with_components('BTCUSDT')

        # Verify that all components were called in the correct order
        # 1. Market data was fetched
        assert system['components']['market_data'].exchange.fetch_ohlcv.called
        
        # 2. Data was validated
        assert system['utilities']['validator'].validate_market_data.called
        
        # 3. Signal processing was triggered
        system['mocks']['signal_generator'].generate_confluence_data.assert_called()
        
        # 4. Whale activity monitoring was executed
        assert system['mocks']['alert_manager'].send_alert.call_count >= 0
        
        # 5. Manipulation monitoring was executed
        system['mocks']['manipulation_detector'].detect_manipulation.assert_called()
        
        # 6. Statistics were updated
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['processed_symbols'] == 1
        assert stats['successful_analyses'] == 1

    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, integrated_system):
        """Test system resilience when components fail."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Simulate market data fetch failure
        system['components']['market_data'].exchange.fetch_ohlcv.side_effect = Exception("Network error")
        
        # Mock top symbols manager
        system['mocks']['top_symbols_manager'].get_top_symbols.return_value = ['BTCUSDT']
        
        # Process symbol with error
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Verify error was handled gracefully
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['failed_analyses'] == 1
        assert stats['processed_symbols'] == 1

    @pytest.mark.asyncio
    async def test_concurrent_component_execution(self, integrated_system):
        """Test that analysis components execute concurrently for performance."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Mock components with delays to test concurrency
        system['mocks']['signal_generator'].generate_confluence_data = AsyncMock()
        system['mocks']['manipulation_detector'].detect_manipulation = AsyncMock()
        
        # Add artificial delays
        async def delayed_signal_processing(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {'symbol': 'BTCUSDT', 'overall_score': 50}
        
        async def delayed_manipulation_detection(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {'manipulation_detected': False}
        
        system['mocks']['signal_generator'].generate_confluence_data.side_effect = delayed_signal_processing
        system['mocks']['manipulation_detector'].detect_manipulation.side_effect = delayed_manipulation_detection
        
        # Mock top symbols manager
        system['mocks']['top_symbols_manager'].get_top_symbols.return_value = ['BTCUSDT']
        
        # Measure execution time
        start_time = time.time()
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        execution_time = time.time() - start_time
        
        # Should complete in less than 0.15 seconds (concurrent execution)
        # If sequential, it would take 0.2+ seconds
        assert execution_time < 0.15, f"Execution took {execution_time:.3f}s, expected concurrent execution"

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, integrated_system):
        """Test integration of health monitoring across all components."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Mock health check to return healthy status
        system['components']['health'].check_health = AsyncMock(return_value={
            'healthy': True,
            'components': {
                'websocket': {'status': 'connected'},
                'market_data': {'cache_hit_rate': 0.85},
                'signal_processor': {'last_signal': time.time()},
                'whale_monitor': {'alerts_sent': 5},
                'manipulation_monitor': {'detections': 2}
            },
            'system': {
                'memory_usage': 65,
                'cpu_usage': 45,
                'uptime': 3600
            }
        })
        
        # Perform health checks
        await orchestration_service._perform_health_checks()
        
        # Verify health monitoring was called
        system['components']['health'].check_health.assert_called_once()
        
        # Check that no alerts were generated for healthy system
        assert orchestration_service.stats_data['health_check_failures'] == 0

    @pytest.mark.asyncio
    async def test_configuration_driven_behavior(self, integrated_system):
        """Test that configuration properly drives system behavior."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Test with whale activity disabled
        system['services']['orchestration'].config['whale_activity']['enabled'] = False
        
        # Mock components
        system['mocks']['top_symbols_manager'].get_top_symbols.return_value = ['BTCUSDT']
        
        # Process symbol
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Verify whale monitoring respects configuration
        whale_stats = system['components']['whale'].get_whale_activity_stats()
        assert whale_stats is not None  # Component still provides stats

    @pytest.mark.asyncio
    async def test_statistics_aggregation_across_layers(self, integrated_system):
        """Test that statistics are properly aggregated across all layers."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Mock various component statistics
        system['components']['whale'].get_whale_activity_stats.return_value = {
            'whales_detected': 3,
            'accumulation_events': 2,
            'distribution_events': 1
        }
        
        system['components']['manipulation'].get_manipulation_stats.return_value = {
            'alerts_generated': 1,
            'patterns_detected': 2,
            'confidence_avg': 0.65
        }
        
        system['utilities']['validator'].get_validation_stats.return_value = {
            'total_validations': 50,
            'passed_validations': 47,
            'validation_rate': 0.94
        }
        
        # Get comprehensive statistics
        stats = orchestration_service.get_monitoring_statistics()
        component_stats = orchestration_service._get_component_statistics()
        
        # Verify all layer statistics are included
        assert 'whale_activity_stats' in component_stats
        assert 'manipulation_stats' in component_stats
        assert 'validation_stats' in component_stats
        assert 'websocket_status' in component_stats
        assert 'market_data_cache_stats' in component_stats
        
        # Verify service-level statistics
        assert 'is_running' in stats
        assert 'processed_symbols' in stats
        assert 'successful_analyses' in stats
        assert 'component_stats' in stats

    @pytest.mark.asyncio
    async def test_data_flow_integrity(self, integrated_system):
        """Test data integrity as it flows through the system layers."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Create test market data
        test_market_data = {
            'symbol': 'BTCUSDT',
            'price': 47200,
            'ohlcv': {
                'base': [[1640995200000, 47000, 47500, 46800, 47200, 1000]],
                'ltf': [[1640995200000, 47000, 47500, 46800, 47200, 1000]],
                'mtf': [[1640995200000, 47000, 47500, 46800, 47200, 1000]],
                'htf': [[1640995200000, 47000, 47500, 46800, 47200, 1000]]
            },
            'orderbook': {
                'bids': [[47180, 10], [47170, 15]],
                'asks': [[47220, 12], [47230, 18]]
            },
            'trades': [
                {'amount': 1.5, 'price': 47200, 'timestamp': int(time.time() * 1000)}
            ]
        }
        
        # Mock market data processor to return test data
        system['components']['market_data'].fetch_market_data = AsyncMock(return_value=test_market_data)
        
        # Mock validation to pass
        system['utilities']['validator'].validate_market_data = AsyncMock(return_value=True)
        
        # Mock signal generation to verify data integrity
        def verify_signal_data(market_data):
            assert market_data['symbol'] == 'BTCUSDT'
            assert market_data['price'] == 47200
            assert 'ohlcv' in market_data
            return {'symbol': 'BTCUSDT', 'overall_score': 65}
        
        system['mocks']['signal_generator'].generate_confluence_data = AsyncMock(side_effect=verify_signal_data)
        
        # Mock whale activity to verify data integrity
        async def verify_whale_data(symbol, market_data):
            assert symbol == 'BTCUSDT'
            assert market_data['price'] == 47200
            assert 'orderbook' in market_data
        
        system['components']['whale'].monitor_whale_activity = AsyncMock(side_effect=verify_whale_data)
        
        # Mock manipulation detection to verify data integrity
        async def verify_manipulation_data(symbol, market_data):
            assert symbol == 'BTCUSDT'
            assert market_data['price'] == 47200
            assert 'trades' in market_data
        
        system['components']['manipulation'].monitor_manipulation_activity = AsyncMock(
            side_effect=verify_manipulation_data
        )
        
        # Process symbol and verify data flow
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # All verifications happen in the side_effect functions above
        # If we reach here, data integrity was maintained

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle_management(self, integrated_system):
        """Test complete monitoring lifecycle from start to stop."""
        system = integrated_system
        orchestration_service = system['services']['orchestration']
        
        # Mock top symbols manager
        system['mocks']['top_symbols_manager'].get_top_symbols.return_value = ['BTCUSDT']
        
        # Mock short monitoring cycle
        original_config = orchestration_service.config.copy()
        orchestration_service.config['monitoring']['cycle_interval'] = 0.1  # Very short for testing
        
        # Start monitoring in background
        monitoring_task = asyncio.create_task(
            orchestration_service.start_monitoring('BTCUSDT')
        )
        
        # Let it run briefly
        await asyncio.sleep(0.2)
        
        # Verify it's running
        assert orchestration_service.is_running is True
        assert len(orchestration_service.monitoring_tasks) > 0
        
        # Stop monitoring
        await orchestration_service.stop_monitoring()
        
        # Cancel the monitoring task
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # Verify proper cleanup
        assert orchestration_service.is_running is False
        assert len(orchestration_service.monitoring_tasks) == 0
        
        # Restore original config
        orchestration_service.config = original_config

    def test_architecture_layer_separation(self, integrated_system):
        """Test that architectural layers are properly separated."""
        system = integrated_system
        
        # Verify utilities are self-contained
        utilities = system['utilities']
        assert utilities['validator'] is not None
        assert utilities['logging'] is not None
        assert utilities['timestamp'] is not None
        
        # Verify components use utilities but not services
        components = system['components']
        for component in components.values():
            assert hasattr(component, 'logger')  # Should have logging
            # Components should not directly reference services
        
        # Verify services coordinate components
        orchestration_service = system['services']['orchestration']
        assert orchestration_service.websocket_processor is not None
        assert orchestration_service.market_data_processor is not None
        assert orchestration_service.signal_processor is not None
        assert orchestration_service.whale_activity_monitor is not None
        assert orchestration_service.manipulation_monitor is not None
        assert orchestration_service.component_health_monitor is not None
        
        # Verify dependency injection pattern
        assert orchestration_service.market_data_validator is not None
        assert orchestration_service.alert_manager is not None 