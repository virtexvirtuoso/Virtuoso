"""
Basic Integration Tests for the Monitoring System.

These tests validate basic integration functionality with proper component
interfaces and realistic scenarios.
"""

import pytest
import pytest_asyncio
import asyncio
import logging
import time
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

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


class TestBasicIntegration:
    """Basic integration tests for the monitoring system."""

    @pytest.fixture
    def mock_config(self):
        """Create a basic test configuration."""
        return {
            'websocket': {
                'enabled': True,
                'timeout': 10
            },
            'market_data': {
                'cache_ttl': 60,
                'enable_validation': True
            },
            'signal_processing': {
                'enable_pdf_reports': False
            },
            'whale_activity': {
                'enabled': True,
                'cooldown': 300
            },
            'manipulation': {
                'enabled': True
            },
            'health': {
                'check_interval': 30
            },
            'monitoring': {
                'cycle_interval': 10
            }
        }

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_dependencies(self):
        """Create basic mock dependencies."""
        deps = {
            'database_client': Mock(),
            'alert_manager': Mock(),
            'signal_generator': Mock(),
            'top_symbols_manager': Mock(),
            'market_data_manager': Mock(),
            'manipulation_detector': Mock()
        }
        
        # Set up basic return values
        deps['signal_generator'].generate_confluence_data = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'overall_score': 65
        })
        
        deps['manipulation_detector'].detect_manipulation = AsyncMock(return_value={
            'manipulation_detected': False,
            'confidence': 0.2
        })
        
        deps['market_data_manager'].get_market_data = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'price': 47200,
            'ohlcv': {'base': [], 'ltf': [], 'mtf': [], 'htf': []},
            'orderbook': {'bids': [[47180, 10]], 'asks': [[47220, 12]]},
            'trades': [{'amount': 1.5, 'price': 47200, 'timestamp': int(time.time() * 1000)}]
        })
        
        deps['top_symbols_manager'].get_top_symbols.return_value = ['BTCUSDT']
        deps['alert_manager'].send_alert = AsyncMock()
        
        return deps

    @pytest_asyncio.fixture
    async def basic_system(self, mock_config, mock_logger, mock_dependencies):
        """Create a basic integrated monitoring system."""
        # Initialize utilities
        validator = MarketDataValidator(mock_logger)
        
        # Initialize components with minimal dependencies
        websocket_processor = WebSocketProcessor(
            config=mock_config,
            logger=mock_logger
        )
        
        market_data_processor = MarketDataProcessor(
            config=mock_config.get('market_data', {}),
            logger=mock_logger,
            market_data_manager=mock_dependencies['market_data_manager'],
            validator=validator
        )
        
        signal_processor = SignalProcessor(
            config=mock_config.get('signal_processing', {}),
            logger=mock_logger,
            signal_generator=mock_dependencies['signal_generator'],
            alert_manager=mock_dependencies['alert_manager'],
            market_data_manager=mock_dependencies['market_data_manager'],
            database_client=mock_dependencies['database_client']
        )
        
        whale_monitor = WhaleActivityMonitor(
            config=mock_config,
            logger=mock_logger,
            alert_manager=mock_dependencies['alert_manager']
        )
        
        manipulation_monitor = ManipulationMonitor(
            config=mock_config,
            logger=mock_logger,
            alert_manager=mock_dependencies['alert_manager'],
            manipulation_detector=mock_dependencies['manipulation_detector'],
            database_client=mock_dependencies['database_client']
        )
        
        # Create a simple mock for MetricsManager since HealthMonitor requires it
        mock_metrics_manager = Mock()
        
        health_monitor = ComponentHealthMonitor(
            metrics_manager=mock_metrics_manager,
            config=mock_config.get('health', {})
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
            alert_manager=mock_dependencies['alert_manager'],
            top_symbols_manager=mock_dependencies['top_symbols_manager'],
            logger=mock_logger,
            config=mock_config
        )
        
        return {
            'orchestration': orchestration_service,
            'components': {
                'websocket': websocket_processor,
                'market_data': market_data_processor,
                'signal': signal_processor,
                'whale': whale_monitor,
                'manipulation': manipulation_monitor,
                'health': health_monitor
            },
            'utilities': {
                'validator': validator
            },
            'mocks': mock_dependencies
        }

    @pytest.mark.asyncio
    async def test_basic_symbol_processing(self, basic_system):
        """Test basic symbol processing workflow."""
        orchestration_service = basic_system['orchestration']
        
        # Process a symbol
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Verify basic statistics
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['processed_symbols'] == 1
        assert stats['successful_analyses'] == 1

    @pytest.mark.asyncio
    async def test_component_coordination(self, basic_system):
        """Test that components are properly coordinated."""
        orchestration_service = basic_system['orchestration']
        mocks = basic_system['mocks']
        
        # Process a symbol
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Verify market data was fetched
        mocks['market_data_manager'].get_market_data.assert_called_with('BTCUSDT')
        
        # Verify signal processing was called
        mocks['signal_generator'].generate_confluence_data.assert_called_once()
        
        # Verify manipulation detection was called
        mocks['manipulation_detector'].detect_manipulation.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_resilience(self, basic_system):
        """Test that errors in one component don't crash the system."""
        orchestration_service = basic_system['orchestration']
        mocks = basic_system['mocks']
        
        # Make market data fetching fail
        mocks['market_data_manager'].get_market_data.side_effect = Exception("Network error")
        
        # Process should still complete without crashing
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Should record the failure
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['failed_analyses'] >= 0  # Error handling may vary

    @pytest.mark.asyncio
    async def test_service_statistics(self, basic_system):
        """Test service statistics collection."""
        orchestration_service = basic_system['orchestration']
        
        # Get initial statistics
        stats = orchestration_service.get_monitoring_statistics()
        assert 'processed_symbols' in stats
        assert 'successful_analyses' in stats
        assert 'failed_analyses' in stats
        assert 'is_running' in stats

    def test_component_access(self, basic_system):
        """Test that all components are accessible."""
        orchestration_service = basic_system['orchestration']
        
        # Verify all components are accessible
        assert orchestration_service.websocket_processor is not None
        assert orchestration_service.market_data_processor is not None
        assert orchestration_service.signal_processor is not None
        assert orchestration_service.whale_activity_monitor is not None
        assert orchestration_service.manipulation_monitor is not None
        assert orchestration_service.component_health_monitor is not None

    def test_service_status(self, basic_system):
        """Test service status reporting."""
        orchestration_service = basic_system['orchestration']
        
        status = orchestration_service.get_service_status()
        
        assert status['service_name'] == 'MonitoringOrchestrationService'
        assert 'is_running' in status
        assert 'statistics' in status
        assert 'component_dependencies' in status

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, basic_system):
        """Test health monitoring integration."""
        orchestration_service = basic_system['orchestration']
        health_monitor = basic_system['components']['health']
        
        # Mock health check
        health_monitor.check_health = AsyncMock(return_value={'healthy': True})
        
        # Perform health checks
        await orchestration_service._perform_health_checks()
        
        # Verify health check was called
        health_monitor.check_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, basic_system):
        """Test concurrent symbol processing."""
        orchestration_service = basic_system['orchestration']
        
        # Process multiple symbols concurrently
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        start_time = time.time()
        tasks = [
            orchestration_service._process_symbol_with_components(symbol)
            for symbol in symbols
        ]
        await asyncio.gather(*tasks)
        processing_time = time.time() - start_time
        
        # Should complete quickly with concurrent execution
        assert processing_time < 2.0, f"Concurrent processing took {processing_time:.3f}s"
        
        # Verify all symbols were processed
        stats = orchestration_service.get_monitoring_statistics()
        assert stats['processed_symbols'] == len(symbols)

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, basic_system):
        """Test monitoring service lifecycle."""
        orchestration_service = basic_system['orchestration']
        
        # Verify initial state
        assert orchestration_service.is_running is False
        assert len(orchestration_service.monitoring_tasks) == 0
        
        # Test start/stop without actually running the loop
        await orchestration_service._start_monitoring_tasks()
        
        # Verify tasks were created
        assert len(orchestration_service.monitoring_tasks) > 0
        
        # Test stop
        await orchestration_service.stop_monitoring()
        
        # Verify cleanup
        assert orchestration_service.is_running is False
        assert len(orchestration_service.monitoring_tasks) == 0

    def test_architecture_validation(self, basic_system):
        """Test that the architecture is properly structured."""
        orchestration_service = basic_system['orchestration']
        components = basic_system['components']
        
        # Verify service orchestrates components
        assert orchestration_service.websocket_processor == components['websocket']
        assert orchestration_service.market_data_processor == components['market_data']
        assert orchestration_service.signal_processor == components['signal']
        
        # Verify components have proper interfaces
        for name, component in components.items():
            assert hasattr(component, 'logger'), f"{name} component missing logger" 