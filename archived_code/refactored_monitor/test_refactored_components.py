"""
Integration Test for Refactored Monitoring Components

This test suite validates that the extracted components work together correctly:
- SignalProcessor
- MonitoringWebSocketManager  
- MetricsTracker
- MarketMonitor (refactored)

Run this test to ensure the refactoring maintains system functionality.
"""

import asyncio
import logging
import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.signal_processor import SignalProcessor
from src.monitoring.websocket_manager import MonitoringWebSocketManager
from src.monitoring.metrics_tracker import MetricsTracker
from src.monitoring.market_monitor_refactored import MarketMonitor


class TestRefactoredComponents:
    """Test suite for refactored monitoring components."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            'exchange': 'bybit',
            'monitoring_interval': 5,
            'confluence': {
                'thresholds': {
                    'buy': 60.0,
                    'sell': 40.0,
                    'neutral_buffer': 5.0
                }
            },
            'websocket_config': {
                'enabled': True,
                'use_ws_for_orderbook': True,
                'use_ws_for_trades': True,
                'use_ws_for_tickers': True
            },
            'monitoring': {
                'thresholds': {
                    'volume_change': 0.2,
                    'orderflow_change': 0.15
                },
                'health_thresholds': {
                    'memory_usage_warning': 85.0,
                    'cpu_usage_warning': 80.0
                }
            },
            'trading': {
                'risk_percentage': 2.0,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 6.0
            }
        }
    
    @pytest.fixture
    def mock_managers(self):
        """Mock manager instances."""
        signal_generator = Mock()
        signal_generator.process_signal = Mock()
        signal_generator._generate_enhanced_formatted_data = Mock(return_value={
            'market_interpretations': [],
            'actionable_insights': []
        })
        
        metrics_manager = Mock()
        metrics_manager.update_analysis_metrics = AsyncMock()
        metrics_manager.update_system_metrics = AsyncMock()
        metrics_manager.start_operation = Mock(return_value='mock_operation')
        metrics_manager.end_operation = Mock()
        metrics_manager.record_metric = Mock()
        
        market_data_manager = Mock()
        market_data_manager.get_market_data = AsyncMock(return_value={
            'ticker': {'last': 50000.0, 'close': 50000.0}
        })
        market_data_manager.get_stats = Mock(return_value={
            'rest_calls': 100,
            'websocket_updates': 50,
            'websocket': {
                'connected': True,
                'seconds_since_last_message': 5
            }
        })
        
        interpretation_manager = Mock()
        interpretation_manager.process_interpretations = Mock()
        
        exchange_manager = Mock()
        exchange_manager.ping = AsyncMock()
        
        timestamp_utility = Mock()
        timestamp_utility.get_utc_timestamp = Mock(return_value=1234567890000)
        
        return {
            'signal_generator': signal_generator,
            'metrics_manager': metrics_manager,
            'market_data_manager': market_data_manager,
            'interpretation_manager': interpretation_manager,
            'exchange_manager': exchange_manager,
            'timestamp_utility': timestamp_utility
        }

    def test_signal_processor_initialization(self, mock_config, mock_managers):
        """Test SignalProcessor initialization."""
        processor = SignalProcessor(
            config=mock_config,
            signal_generator=mock_managers['signal_generator'],
            metrics_manager=mock_managers['metrics_manager'],
            interpretation_manager=mock_managers['interpretation_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        assert processor.config == mock_config
        assert processor.signal_generator == mock_managers['signal_generator']
        assert processor.metrics_manager == mock_managers['metrics_manager']
        assert processor.monitoring_thresholds is not None

    def test_websocket_manager_initialization(self, mock_config, mock_managers):
        """Test MonitoringWebSocketManager initialization."""
        ws_manager = MonitoringWebSocketManager(
            config=mock_config,
            symbol='BTCUSDT',
            exchange_id='bybit',
            timestamp_utility=mock_managers['timestamp_utility'],
            metrics_manager=mock_managers['metrics_manager']
        )
        
        assert ws_manager.symbol == 'BTCUSDT'
        assert ws_manager.exchange_id == 'bybit'
        assert not ws_manager.is_connected  # Not connected initially
        assert ws_manager.websocket_config['enabled'] == True

    def test_metrics_tracker_initialization(self, mock_config, mock_managers):
        """Test MetricsTracker initialization."""
        tracker = MetricsTracker(
            config=mock_config,
            metrics_manager=mock_managers['metrics_manager'],
            market_data_manager=mock_managers['market_data_manager'],
            exchange_manager=mock_managers['exchange_manager']
        )
        
        assert tracker.config == mock_config
        assert tracker.metrics_manager == mock_managers['metrics_manager']
        assert tracker._stats['total_messages'] == 0
        assert tracker.health_thresholds is not None

    @pytest.mark.asyncio
    async def test_signal_processor_analysis_processing(self, mock_config, mock_managers):
        """Test signal processing functionality."""
        processor = SignalProcessor(
            config=mock_config,
            signal_generator=mock_managers['signal_generator'],
            metrics_manager=mock_managers['metrics_manager'],
            interpretation_manager=mock_managers['interpretation_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        # Mock analysis result
        analysis_result = {
            'confluence_score': 65.0,
            'reliability': 1.0,
            'components': {
                'volume': 70.0,
                'sentiment': 60.0,
                'orderflow': 65.0
            },
            'results': {},
            'market_interpretations': []
        }
        
        # Test processing
        await processor.process_analysis_result('BTCUSDT', analysis_result)
        
        # Verify metrics were updated
        mock_managers['metrics_manager'].update_analysis_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_generation(self, mock_config, mock_managers):
        """Test signal generation with trade parameters."""
        processor = SignalProcessor(
            config=mock_config,
            signal_generator=mock_managers['signal_generator'],
            metrics_manager=mock_managers['metrics_manager'],
            interpretation_manager=mock_managers['interpretation_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        # Mock analysis result for BUY signal
        analysis_result = {
            'confluence_score': 75.0,
            'reliability': 1.0,
            'components': {'volume': 80.0},
            'results': {},
            'price': 50000.0,
            'transaction_id': 'test-123',
            'signal_id': 'sig-456'
        }
        
        await processor.generate_signal('BTCUSDT', analysis_result)
        
        # Verify signal was processed
        mock_managers['signal_generator'].process_signal.assert_called_once()

    def test_trade_parameters_calculation(self, mock_config, mock_managers):
        """Test trade parameter calculations."""
        processor = SignalProcessor(
            config=mock_config,
            signal_generator=mock_managers['signal_generator'],
            metrics_manager=mock_managers['metrics_manager'],
            interpretation_manager=mock_managers['interpretation_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        # Test BUY signal parameters
        params = processor.calculate_trade_parameters(
            symbol='BTCUSDT',
            price=50000.0,
            signal_type='BUY',
            score=75.0,
            reliability=1.0
        )
        
        assert params['entry_price'] == 50000.0
        assert params['stop_loss'] < 50000.0  # Stop loss below entry for BUY
        assert params['take_profit'] > 50000.0  # Take profit above entry for BUY
        assert params['risk_reward_ratio'] is not None
        assert params['confidence'] == 0.75  # 75/100

    @pytest.mark.asyncio
    async def test_metrics_tracker_health_checks(self, mock_config, mock_managers):
        """Test system health monitoring."""
        tracker = MetricsTracker(
            config=mock_config,
            metrics_manager=mock_managers['metrics_manager'],
            market_data_manager=mock_managers['market_data_manager'],
            exchange_manager=mock_managers['exchange_manager']
        )
        
        # Test system health check
        health = await tracker.check_system_health()
        
        assert 'status' in health
        assert 'components' in health
        assert 'timestamp' in health
        
        # Test individual component checks
        exchange_health = await tracker.check_exchange_health()
        assert 'status' in exchange_health
        
        memory_health = await tracker.check_memory_usage()
        assert 'status' in memory_health
        assert 'usage_percent' in memory_health

    def test_metrics_tracking(self, mock_config, mock_managers):
        """Test metrics recording and statistics."""
        tracker = MetricsTracker(
            config=mock_config,
            metrics_manager=mock_managers['metrics_manager'],
            market_data_manager=mock_managers['market_data_manager'],
            exchange_manager=mock_managers['exchange_manager']
        )
        
        # Record some metrics
        tracker.record_message(is_valid=True, is_delayed=False)
        tracker.record_message(is_valid=False, is_delayed=True)
        tracker.record_error()
        
        stats = tracker.get_stats()
        
        assert stats['total_messages'] == 2
        assert stats['invalid_messages'] == 1
        assert stats['delayed_messages'] == 1
        assert stats['error_count'] == 1
        assert 'uptime_seconds' in stats

    @pytest.mark.asyncio
    async def test_websocket_data_processing(self, mock_config, mock_managers):
        """Test WebSocket message processing."""
        ws_manager = MonitoringWebSocketManager(
            config=mock_config,
            symbol='BTCUSDT',
            exchange_id='bybit',
            timestamp_utility=mock_managers['timestamp_utility'],
            metrics_manager=mock_managers['metrics_manager']
        )
        
        # Mock ticker message
        ticker_message = {
            'data': {
                'data': {
                    'lastPrice': '50000.0',
                    'bid1Price': '49999.0',
                    'ask1Price': '50001.0',
                    'highPrice24h': '51000.0',
                    'lowPrice24h': '49000.0',
                    'volume24h': '1000.0'
                }
            },
            'timestamp': 1234567890000
        }
        
        await ws_manager._process_ticker_update(ticker_message)
        
        # Check if ticker data was stored
        ticker_data = ws_manager.get_ticker_data()
        assert ticker_data is not None
        assert ticker_data['last'] == 50000.0
        assert ticker_data['symbol'] == 'BTCUSDT'

    @pytest.mark.asyncio
    async def test_market_monitor_integration(self, mock_config, mock_managers):
        """Test the refactored MarketMonitor integration."""
        # Mock the core components
        with patch('src.monitoring.market_monitor_refactored.MetricsManager') as MockMetricsManager, \
             patch('src.monitoring.market_monitor_refactored.MarketDataManager') as MockMarketDataManager, \
             patch('src.monitoring.market_monitor_refactored.ConfluenceAnalyzer') as MockConfluenceAnalyzer:
            
            # Setup mocks
            MockMetricsManager.return_value = mock_managers['metrics_manager']
            MockMarketDataManager.return_value = mock_managers['market_data_manager']
            
            mock_confluence = Mock()
            mock_confluence.analyze = AsyncMock(return_value={
                'confluence_score': 65.0,
                'reliability': 1.0,
                'components': {'volume': 70.0}
            })
            MockConfluenceAnalyzer.return_value = mock_confluence
            
            # Create monitor
            monitor = MarketMonitor(
                config=mock_config,
                exchange_manager=mock_managers['exchange_manager'],
                symbol='BTCUSDT'
            )
            
            # Test initialization
            assert monitor.symbol == 'BTCUSDT'
            assert monitor.exchange_id == 'bybit'
            assert monitor.signal_processor is not None
            assert monitor.websocket_manager is not None
            assert monitor.metrics_tracker is not None
            
            # Test symbol processing (mocked)
            mock_market_data = {
                'ticker': {'last': 50000.0},
                'orderbook': {'bids': [[49999.0, 1.0]], 'asks': [[50001.0, 1.0]]},
                'trades': []
            }
            
            monitor.data_collector.collect_market_data = AsyncMock(return_value=mock_market_data)
            monitor.validator.validate_market_data = AsyncMock(return_value=True)
            
            await monitor._process_symbol('BTCUSDT')
            
            # Verify confluence analysis was called
            mock_confluence.analyze.assert_called_once()

    def test_component_interface_compatibility(self, mock_config, mock_managers):
        """Test that extracted components maintain interface compatibility."""
        # Test SignalProcessor interface
        processor = SignalProcessor(
            config=mock_config,
            signal_generator=mock_managers['signal_generator'],
            metrics_manager=mock_managers['metrics_manager'],
            interpretation_manager=mock_managers['interpretation_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        # Check required methods exist
        assert hasattr(processor, 'process_analysis_result')
        assert hasattr(processor, 'generate_signal')
        assert hasattr(processor, 'calculate_trade_parameters')
        assert hasattr(processor, 'monitor_volume')
        assert hasattr(processor, 'monitor_orderflow')
        
        # Test MetricsTracker interface
        tracker = MetricsTracker(
            config=mock_config,
            metrics_manager=mock_managers['metrics_manager'],
            market_data_manager=mock_managers['market_data_manager'],
            exchange_manager=mock_managers['exchange_manager']
        )
        
        # Check required methods exist
        assert hasattr(tracker, 'update_metrics')
        assert hasattr(tracker, 'check_system_health')
        assert hasattr(tracker, 'check_exchange_health')
        assert hasattr(tracker, 'get_stats')
        assert hasattr(tracker, 'record_message')
        assert hasattr(tracker, 'record_error')
        
        # Test WebSocketManager interface
        ws_manager = MonitoringWebSocketManager(
            config=mock_config,
            symbol='BTCUSDT',
            exchange_id='bybit',
            timestamp_utility=mock_managers['timestamp_utility']
        )
        
        # Check required methods exist
        assert hasattr(ws_manager, 'initialize')
        assert hasattr(ws_manager, 'get_websocket_status')
        assert hasattr(ws_manager, 'get_ticker_data')
        assert hasattr(ws_manager, 'get_orderbook_data')
        assert hasattr(ws_manager, 'close')

    def test_error_handling(self, mock_config, mock_managers):
        """Test error handling in components."""
        # Test SignalProcessor error handling
        processor = SignalProcessor(
            config=mock_config,
            signal_generator=None,  # Intentionally None to trigger error path
            metrics_manager=mock_managers['metrics_manager'],
            interpretation_manager=mock_managers['interpretation_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        # This should handle the None signal generator gracefully
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Should not raise exception, just log error
            analysis_result = {'confluence_score': 65.0, 'reliability': 1.0}
            loop.run_until_complete(
                processor.generate_signal('BTCUSDT', analysis_result)
            )
        finally:
            loop.close()
        
        # Test MetricsTracker error handling with invalid config
        invalid_config = {}  # Empty config
        tracker = MetricsTracker(
            config=invalid_config,
            metrics_manager=mock_managers['metrics_manager'],
            market_data_manager=mock_managers['market_data_manager']
        )
        
        # Should initialize with default values
        assert tracker.health_thresholds is not None


def run_integration_tests():
    """Run all integration tests."""
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Running integration tests for refactored monitoring components...")
    
    # Run tests with pytest
    test_file = __file__
    exit_code = pytest.main(['-v', test_file])
    
    if exit_code == 0:
        print("✅ All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed!")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)