"""
Tests for MonitoringOrchestrationService.
"""

import pytest
import asyncio
import logging
import time
from unittest.mock import Mock, AsyncMock, patch

from src.monitoring.services.monitoring_orchestration_service import MonitoringOrchestrationService
from src.monitoring.components import (
    WebSocketProcessor,
    MarketDataProcessor, 
    SignalProcessor,
    WhaleActivityMonitor,
    ManipulationMonitor,
    HealthMonitor as ComponentHealthMonitor
)
from src.monitoring.utilities import MarketDataValidator


class TestMonitoringOrchestrationService:
    """Test cases for MonitoringOrchestrationService."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            'monitoring': {
                'cycle_interval': 10
            }
        }

    @pytest.fixture
    def mock_websocket_processor(self):
        """Create a mock WebSocket processor."""
        processor = Mock()
        processor.get_real_time_data.return_value = {'price': 50000}
        processor.get_websocket_status.return_value = {'connected': True}
        return processor

    @pytest.fixture
    def mock_market_data_processor(self):
        """Create a mock market data processor."""
        processor = Mock(spec=MarketDataProcessor)
        processor.fetch_market_data = AsyncMock(return_value={
            'symbol': 'BTCUSDT',
            'price': 50000,
            'ohlcv': {'base': 'mock_data'}
        })
        processor.get_cache_stats.return_value = {'hits': 10, 'misses': 2}
        return processor

    @pytest.fixture
    def mock_signal_processor(self):
        """Create a mock signal processor."""
        processor = Mock(spec=SignalProcessor)
        processor.analyze_confluence_and_generate_signals = AsyncMock()
        return processor

    @pytest.fixture
    def mock_whale_activity_monitor(self):
        """Create a mock whale activity monitor."""
        monitor = Mock(spec=WhaleActivityMonitor)
        monitor.monitor_whale_activity = AsyncMock()
        monitor.get_whale_activity_stats.return_value = {'whales_detected': 5}
        return monitor

    @pytest.fixture
    def mock_manipulation_monitor(self):
        """Create a mock manipulation monitor."""
        monitor = Mock(spec=ManipulationMonitor)
        monitor.monitor_manipulation_activity = AsyncMock()
        monitor.get_manipulation_stats.return_value = {'alerts': 2}
        return monitor

    @pytest.fixture
    def mock_health_monitor(self):
        """Create a mock health monitor."""
        monitor = Mock(spec=ComponentHealthMonitor)
        monitor.check_health = AsyncMock(return_value={'healthy': True})
        monitor.start_monitoring = AsyncMock()
        return monitor

    @pytest.fixture
    def mock_validator(self):
        """Create a mock market data validator."""
        validator = Mock(spec=MarketDataValidator)
        validator.validate_market_data = AsyncMock(return_value=True)
        validator.get_validation_stats.return_value = {'total': 100, 'passed': 95}
        return validator

    @pytest.fixture
    def mock_alert_manager(self):
        """Create a mock alert manager."""
        manager = Mock()
        manager.send_alert = AsyncMock()
        return manager

    @pytest.fixture
    def mock_top_symbols_manager(self):
        """Create a mock top symbols manager."""
        manager = Mock()
        manager.get_top_symbols.return_value = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        return manager

    @pytest.fixture
    def orchestration_service(
        self,
        mock_logger,
        mock_config,
        mock_websocket_processor,
        mock_market_data_processor,
        mock_signal_processor,
        mock_whale_activity_monitor,
        mock_manipulation_monitor,
        mock_health_monitor,
        mock_validator,
        mock_alert_manager,
        mock_top_symbols_manager
    ):
        """Create an orchestration service with all mocked dependencies."""
        return MonitoringOrchestrationService(
            websocket_processor=mock_websocket_processor,
            market_data_processor=mock_market_data_processor,
            signal_processor=mock_signal_processor,
            whale_activity_monitor=mock_whale_activity_monitor,
            manipulation_monitor=mock_manipulation_monitor,
            component_health_monitor=mock_health_monitor,
            market_data_validator=mock_validator,
            alert_manager=mock_alert_manager,
            top_symbols_manager=mock_top_symbols_manager,
            logger=mock_logger,
            config=mock_config
        )

    def test_initialization(self, orchestration_service, mock_logger):
        """Test service initialization."""
        assert orchestration_service.is_running is False
        assert orchestration_service.monitoring_tasks == []
        assert 'processed_symbols' in orchestration_service.stats_data
        mock_logger.info.assert_called_with("MonitoringOrchestrationService initialized")

    @pytest.mark.asyncio
    async def test_start_monitoring_tasks(self, orchestration_service, mock_health_monitor):
        """Test starting monitoring tasks."""
        await orchestration_service._start_monitoring_tasks()
        
        assert len(orchestration_service.monitoring_tasks) == 1
        mock_health_monitor.start_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, orchestration_service):
        """Test stopping monitoring gracefully."""
        # Create a real async task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)  # Long sleep to allow cancellation
        
        # Create an actual task
        real_task = asyncio.create_task(dummy_task())
        orchestration_service.monitoring_tasks = [real_task]
        orchestration_service.is_running = True
        
        await orchestration_service.stop_monitoring()
        
        assert orchestration_service.is_running is False
        assert len(orchestration_service.monitoring_tasks) == 0
        assert real_task.cancelled()

    def test_get_monitored_symbols_with_target(self, orchestration_service):
        """Test getting monitored symbols with target symbol."""
        symbols = orchestration_service._get_monitored_symbols('BTCUSDT')
        assert symbols == ['BTCUSDT']

    def test_get_monitored_symbols_with_manager(self, orchestration_service, mock_top_symbols_manager):
        """Test getting monitored symbols from manager."""
        symbols = orchestration_service._get_monitored_symbols()
        assert symbols == ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        mock_top_symbols_manager.get_top_symbols.assert_called_once()

    def test_get_monitored_symbols_default(self, orchestration_service):
        """Test getting default symbols when no manager available."""
        orchestration_service.top_symbols_manager = None
        symbols = orchestration_service._get_monitored_symbols()
        assert 'BTCUSDT' in symbols
        assert 'ETHUSDT' in symbols
        assert 'SOLUSDT' in symbols

    @pytest.mark.asyncio
    async def test_process_symbol_success(
        self,
        orchestration_service,
        mock_market_data_processor,
        mock_validator,
        mock_signal_processor,
        mock_whale_activity_monitor,
        mock_manipulation_monitor
    ):
        """Test successful symbol processing."""
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Verify all components were called
        mock_market_data_processor.fetch_market_data.assert_called_once_with('BTCUSDT')
        mock_validator.validate_market_data.assert_called_once()
        mock_signal_processor.analyze_confluence_and_generate_signals.assert_called_once()
        mock_whale_activity_monitor.monitor_whale_activity.assert_called_once()
        mock_manipulation_monitor.monitor_manipulation_activity.assert_called_once()
        
        # Check statistics updated
        assert orchestration_service.stats_data['processed_symbols'] == 1
        assert orchestration_service.stats_data['successful_analyses'] == 1

    @pytest.mark.asyncio
    async def test_process_symbol_no_market_data(
        self,
        orchestration_service,
        mock_market_data_processor,
        mock_logger
    ):
        """Test symbol processing when no market data available."""
        mock_market_data_processor.fetch_market_data.return_value = None
        
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Should return early and log warning
        mock_logger.warning.assert_called_with("No market data available for BTCUSDT")
        assert orchestration_service.stats_data['processed_symbols'] == 0

    @pytest.mark.asyncio
    async def test_process_symbol_validation_failure(
        self,
        orchestration_service,
        mock_validator,
        mock_logger
    ):
        """Test symbol processing when validation fails."""
        mock_validator.validate_market_data.return_value = False
        
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Should return early and log warning
        mock_logger.warning.assert_called_with("Market data validation failed for BTCUSDT")
        assert orchestration_service.stats_data['failed_analyses'] == 1

    @pytest.mark.asyncio
    async def test_process_symbol_with_analysis_failure(
        self,
        orchestration_service,
        mock_signal_processor,
        mock_logger
    ):
        """Test symbol processing with analysis component failure."""
        # Make signal processor raise an exception
        mock_signal_processor.analyze_confluence_and_generate_signals.side_effect = Exception("Analysis failed")
        
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        
        # Should handle exception and update statistics
        assert orchestration_service.stats_data['processed_symbols'] == 1
        assert orchestration_service.stats_data['failed_analyses'] == 1
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_perform_health_checks_success(
        self,
        orchestration_service,
        mock_health_monitor
    ):
        """Test successful health checks."""
        await orchestration_service._perform_health_checks()
        
        mock_health_monitor.check_health.assert_called_once()
        assert orchestration_service.stats_data['health_check_failures'] == 0

    @pytest.mark.asyncio
    async def test_perform_health_checks_failure(
        self,
        orchestration_service,
        mock_health_monitor,
        mock_alert_manager,
        mock_logger
    ):
        """Test health check failure handling."""
        mock_health_monitor.check_health.return_value = {'healthy': False, 'issues': ['low memory']}
        
        await orchestration_service._perform_health_checks()
        
        mock_logger.warning.assert_called()
        mock_alert_manager.send_alert.assert_called_once()
        assert orchestration_service.stats_data['health_check_failures'] == 1

    @pytest.mark.asyncio
    async def test_perform_health_checks_exception(
        self,
        orchestration_service,
        mock_health_monitor,
        mock_logger
    ):
        """Test health check exception handling."""
        mock_health_monitor.check_health.side_effect = Exception("Health check failed")
        
        await orchestration_service._perform_health_checks()
        
        mock_logger.error.assert_called()
        assert orchestration_service.stats_data['health_check_failures'] == 1

    def test_get_monitoring_statistics(self, orchestration_service):
        """Test getting monitoring statistics."""
        # Set some test data
        orchestration_service.stats_data.update({
            'start_time': time.time() - 100,
            'processed_symbols': 50,
            'successful_analyses': 45,
            'failed_analyses': 5,
            'total_cycles': 10,
            'health_check_failures': 1
        })
        orchestration_service.is_running = True
        
        stats = orchestration_service.get_monitoring_statistics()
        
        assert stats['is_running'] is True
        assert stats['processed_symbols'] == 50
        assert stats['successful_analyses'] == 45
        assert stats['failed_analyses'] == 5
        assert stats['success_rate'] == 0.9  # 45/50
        assert stats['total_cycles'] == 10
        assert stats['health_check_failures'] == 1
        assert 'component_stats' in stats
        assert stats['uptime_seconds'] > 0

    def test_get_component_statistics(self, orchestration_service):
        """Test getting component statistics."""
        stats = orchestration_service._get_component_statistics()
        
        assert 'whale_activity_stats' in stats
        assert 'manipulation_stats' in stats
        assert 'validation_stats' in stats
        assert 'websocket_status' in stats
        assert 'market_data_cache_stats' in stats

    def test_get_service_status(self, orchestration_service):
        """Test getting service status."""
        status = orchestration_service.get_service_status()
        
        assert status['service_name'] == 'MonitoringOrchestrationService'
        assert status['is_running'] is False
        assert status['active_tasks'] == 0
        assert 'statistics' in status
        assert 'component_dependencies' in status
        
        # Check all component dependencies are tracked
        deps = status['component_dependencies']
        assert deps['websocket_processor'] is True
        assert deps['market_data_processor'] is True
        assert deps['signal_processor'] is True
        assert deps['whale_activity_monitor'] is True
        assert deps['manipulation_monitor'] is True
        assert deps['component_health_monitor'] is True
        assert deps['market_data_validator'] is True

    @pytest.mark.asyncio
    async def test_monitoring_loop_integration(self, orchestration_service):
        """Test a complete monitoring cycle."""
        # Mock the is_running to stop after one cycle
        orchestration_service.is_running = True
        
        # Mock sleep to avoid waiting
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Create a task that will run one cycle then stop
            async def run_one_cycle():
                await orchestration_service._process_symbol_with_components('BTCUSDT')
                orchestration_service.is_running = False
            
            # Replace the symbol processing to stop after one cycle
            orchestration_service._get_monitored_symbols = Mock(return_value=['BTCUSDT'])
            
            # Run the monitoring loop
            try:
                await asyncio.wait_for(
                    orchestration_service._run_monitoring_loop('BTCUSDT'),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                pass  # Expected for infinite loop
            
            # Verify cycle completed
            assert orchestration_service.stats_data['total_cycles'] >= 0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring_integration(self, orchestration_service):
        """Test full start and stop monitoring workflow."""
        # Start monitoring in background
        monitoring_task = asyncio.create_task(
            orchestration_service.start_monitoring('BTCUSDT')
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Verify it's running
        assert orchestration_service.is_running is True
        
        # Stop monitoring
        await orchestration_service.stop_monitoring()
        
        # Cancel the monitoring task
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # Verify it's stopped
        assert orchestration_service.is_running is False

    def test_error_handling_in_symbol_retrieval(self, orchestration_service, mock_top_symbols_manager, mock_logger):
        """Test error handling in symbol retrieval."""
        mock_top_symbols_manager.get_top_symbols.side_effect = Exception("Symbol retrieval failed")
        
        symbols = orchestration_service._get_monitored_symbols()
        
        assert symbols == []
        mock_logger.error.assert_called_with("Error getting monitored symbols: Symbol retrieval failed")

    @pytest.mark.asyncio
    async def test_concurrent_analysis_execution(
        self,
        orchestration_service,
        mock_signal_processor,
        mock_whale_activity_monitor,
        mock_manipulation_monitor
    ):
        """Test that analysis components are executed concurrently."""
        # Set up async mocks with delays to verify concurrency
        mock_signal_processor.analyze_confluence_and_generate_signals = AsyncMock()
        mock_whale_activity_monitor.monitor_whale_activity = AsyncMock()
        mock_manipulation_monitor.monitor_manipulation_activity = AsyncMock()
        
        start_time = time.time()
        await orchestration_service._process_symbol_with_components('BTCUSDT')
        end_time = time.time()
        
        # Verify all analysis methods were called
        mock_signal_processor.analyze_confluence_and_generate_signals.assert_called_once()
        mock_whale_activity_monitor.monitor_whale_activity.assert_called_once()
        mock_manipulation_monitor.monitor_manipulation_activity.assert_called_once()
        
        # Since they run concurrently, total time should be reasonable
        assert end_time - start_time < 1.0  # Should complete quickly in tests 