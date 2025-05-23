"""
Tests for ManipulationMonitor component.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

from src.monitoring.components.manipulation_monitor import ManipulationMonitor


class TestManipulationMonitor:
    """Test cases for ManipulationMonitor component."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            'manipulation_detection': {
                'enabled': True,
                'sensitivity': 'medium'
            }
        }

    @pytest.fixture
    def mock_alert_manager(self):
        """Create a mock alert manager."""
        mock = Mock()
        mock.send_alert = AsyncMock()
        return mock

    @pytest.fixture
    def mock_manipulation_detector(self):
        """Create a mock manipulation detector."""
        mock = Mock()
        mock.analyze_market_data = AsyncMock()
        mock.get_stats = Mock()
        mock.get_manipulation_history = Mock()
        return mock

    @pytest.fixture
    def mock_database_client(self):
        """Create a mock database client."""
        mock = Mock()
        mock.store_manipulation_activity = AsyncMock()
        return mock

    @pytest.fixture
    def mock_manipulation_alert(self):
        """Create a mock manipulation alert."""
        mock = Mock()
        mock.manipulation_type = 'pump_and_dump'
        mock.confidence_score = 0.85
        mock.severity = 'high'
        mock.description = 'Suspicious price and volume patterns detected'
        mock.timestamp = 1640995200
        mock.metrics = {
            'oi_change_15m_pct': 0.15,
            'volume_spike_ratio': 3.5,
            'price_change_15m_pct': 0.08,
            'divergence_detected': True,
            'divergence_strength': 0.7
        }
        return mock

    @pytest.fixture
    def manipulation_monitor(self, mock_logger, mock_config, mock_alert_manager, 
                           mock_manipulation_detector, mock_database_client):
        """Create a ManipulationMonitor instance with mocked dependencies."""
        return ManipulationMonitor(
            logger=mock_logger,
            config=mock_config,
            alert_manager=mock_alert_manager,
            manipulation_detector=mock_manipulation_detector,
            database_client=mock_database_client
        )

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        return {
            'ohlcv': {
                '1m': [
                    [1640995140000, 50000, 50100, 49900, 50050, 1000],
                    [1640995200000, 50050, 50200, 50000, 50180, 1500]
                ]
            },
            'orderbook': {
                'bids': [[50000, 10], [49990, 5]],
                'asks': [[50010, 8], [50020, 6]]
            },
            'trades': [
                {'timestamp': 1640995180000, 'side': 'buy', 'amount': 100, 'price': 50100},
                {'timestamp': 1640995190000, 'side': 'sell', 'amount': 50, 'price': 50080}
            ],
            'ticker': {'last': 50180.0}
        }

    def test_initialization_with_defaults(self):
        """Test ManipulationMonitor initialization with default values."""
        monitor = ManipulationMonitor()
        
        assert monitor.logger is not None
        assert monitor.config == {}
        assert monitor.alert_manager is None
        assert monitor.manipulation_detector is None
        assert monitor.database_client is None

    def test_initialization_with_custom_values(self, mock_logger, mock_config, mock_alert_manager,
                                             mock_manipulation_detector, mock_database_client):
        """Test ManipulationMonitor initialization with custom values."""
        monitor = ManipulationMonitor(
            logger=mock_logger,
            config=mock_config,
            alert_manager=mock_alert_manager,
            manipulation_detector=mock_manipulation_detector,
            database_client=mock_database_client
        )
        
        assert monitor.logger == mock_logger
        assert monitor.config == mock_config
        assert monitor.alert_manager == mock_alert_manager
        assert monitor.manipulation_detector == mock_manipulation_detector
        assert monitor.database_client == mock_database_client

    @pytest.mark.asyncio
    async def test_monitor_manipulation_activity_no_detector(self, mock_logger, mock_config):
        """Test manipulation monitoring without detector."""
        monitor = ManipulationMonitor(logger=mock_logger, config=mock_config)
        
        await monitor.monitor_manipulation_activity('BTCUSDT', {})
        
        # Should log debug message about no detector
        mock_logger.debug.assert_called_with(
            "Skipping manipulation monitoring for BTCUSDT: No manipulation detector"
        )

    @pytest.mark.asyncio
    async def test_monitor_manipulation_activity_no_alert_manager(self, mock_logger, mock_config,
                                                                mock_manipulation_detector):
        """Test manipulation monitoring without alert manager."""
        monitor = ManipulationMonitor(
            logger=mock_logger,
            config=mock_config,
            manipulation_detector=mock_manipulation_detector
        )
        
        await monitor.monitor_manipulation_activity('BTCUSDT', {})
        
        # Should log debug message about no alert manager
        mock_logger.debug.assert_called_with(
            "Skipping manipulation monitoring for BTCUSDT: No alert manager"
        )

    @pytest.mark.asyncio
    async def test_monitor_manipulation_activity_no_alert(self, manipulation_monitor, sample_market_data):
        """Test manipulation monitoring when no manipulation is detected."""
        # Configure detector to return None (no manipulation)
        manipulation_monitor.manipulation_detector.analyze_market_data.return_value = None
        
        await manipulation_monitor.monitor_manipulation_activity('BTCUSDT', sample_market_data)
        
        # Should call detector but not send alerts
        manipulation_monitor.manipulation_detector.analyze_market_data.assert_called_once_with(
            'BTCUSDT', sample_market_data
        )
        manipulation_monitor.alert_manager.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_manipulation_activity_with_alert(self, manipulation_monitor, 
                                                          sample_market_data, mock_manipulation_alert):
        """Test manipulation monitoring when manipulation is detected."""
        # Configure detector to return an alert
        manipulation_monitor.manipulation_detector.analyze_market_data.return_value = mock_manipulation_alert
        
        await manipulation_monitor.monitor_manipulation_activity('BTCUSDT', sample_market_data)
        
        # Should call detector and send alert
        manipulation_monitor.manipulation_detector.analyze_market_data.assert_called_once_with(
            'BTCUSDT', sample_market_data
        )
        manipulation_monitor.alert_manager.send_alert.assert_called_once()
        
        # Should log warning about manipulation
        manipulation_monitor.logger.warning.assert_called_with(
            "Manipulation detected for BTCUSDT: Suspicious price and volume patterns detected"
        )
        
        # Should store data in database
        manipulation_monitor.database_client.store_manipulation_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_manipulation_activity_error_handling(self, manipulation_monitor, 
                                                              sample_market_data):
        """Test error handling in manipulation monitoring."""
        # Configure detector to raise an exception
        manipulation_monitor.manipulation_detector.analyze_market_data.side_effect = Exception("Test error")
        
        await manipulation_monitor.monitor_manipulation_activity('BTCUSDT', sample_market_data)
        
        # Should log the error
        manipulation_monitor.logger.error.assert_called_with(
            "Error monitoring manipulation for BTCUSDT: Test error"
        )
        manipulation_monitor.logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_send_manipulation_alert_high_severity(self, manipulation_monitor, 
                                                       sample_market_data, mock_manipulation_alert):
        """Test sending manipulation alert with high severity."""
        await manipulation_monitor._send_manipulation_alert('BTCUSDT', mock_manipulation_alert, sample_market_data)
        
        # Should send alert with warning level for high severity
        manipulation_monitor.alert_manager.send_alert.assert_called_once()
        call_args = manipulation_monitor.alert_manager.send_alert.call_args
        
        assert call_args[1]['level'] == 'warning'
        message = call_args[1]['message']
        assert '🔸 **Market Manipulation Alert** for BTCUSDT' in message
        assert '• **Type**: Pump And Dump' in message
        assert '• **Confidence**: 85.0%' in message
        assert '• **Severity**: HIGH' in message
        assert '• **Current Price**: $50,180.0000' in message
        assert '• OI Change (15m): +15.0%' in message
        assert '• Volume Spike: 3.5x average' in message
        assert '• Price Change (15m): +8.0%' in message
        assert '• OI-Price Divergence: 70.0% strength' in message
        
        details = call_args[1]['details']
        assert details['type'] == 'manipulation_detection'
        assert details['subtype'] == 'pump_and_dump'
        assert details['symbol'] == 'BTCUSDT'
        assert details['confidence_score'] == 0.85
        assert details['severity'] == 'high'

    @pytest.mark.asyncio
    async def test_send_manipulation_alert_critical_severity(self, manipulation_monitor, 
                                                           sample_market_data):
        """Test sending manipulation alert with critical severity."""
        # Create critical severity alert
        critical_alert = Mock()
        critical_alert.manipulation_type = 'wash_trading'
        critical_alert.confidence_score = 0.95
        critical_alert.severity = 'critical'
        critical_alert.description = 'Clear wash trading patterns detected'
        critical_alert.timestamp = 1640995200
        critical_alert.metrics = {}
        
        await manipulation_monitor._send_manipulation_alert('BTCUSDT', critical_alert, sample_market_data)
        
        # Should send alert with error level for critical severity
        call_args = manipulation_monitor.alert_manager.send_alert.call_args
        assert call_args[1]['level'] == 'error'
        message = call_args[1]['message']
        assert '🚨 **Market Manipulation Alert** for BTCUSDT' in message
        assert '• **Severity**: CRITICAL' in message

    @pytest.mark.asyncio
    async def test_send_manipulation_alert_low_severity(self, manipulation_monitor, 
                                                      sample_market_data):
        """Test sending manipulation alert with low severity."""
        # Create low severity alert
        low_alert = Mock()
        low_alert.manipulation_type = 'spoofing'
        low_alert.confidence_score = 0.65
        low_alert.severity = 'low'
        low_alert.description = 'Potential spoofing activity'
        low_alert.timestamp = 1640995200
        low_alert.metrics = {}
        
        await manipulation_monitor._send_manipulation_alert('BTCUSDT', low_alert, sample_market_data)
        
        # Should send alert with info level for low severity
        call_args = manipulation_monitor.alert_manager.send_alert.call_args
        assert call_args[1]['level'] == 'info'
        message = call_args[1]['message']
        assert '⚠️ **Market Manipulation Alert** for BTCUSDT' in message
        assert '• **Severity**: LOW' in message

    @pytest.mark.asyncio
    async def test_send_manipulation_alert_no_metrics(self, manipulation_monitor, 
                                                    sample_market_data):
        """Test sending manipulation alert without metrics."""
        # Create alert without metrics
        alert_no_metrics = Mock()
        alert_no_metrics.manipulation_type = 'unknown'
        alert_no_metrics.confidence_score = 0.75
        alert_no_metrics.severity = 'medium'
        alert_no_metrics.description = 'Suspicious activity detected'
        alert_no_metrics.timestamp = 1640995200
        alert_no_metrics.metrics = None
        
        await manipulation_monitor._send_manipulation_alert('BTCUSDT', alert_no_metrics, sample_market_data)
        
        # Should send alert without metrics section
        call_args = manipulation_monitor.alert_manager.send_alert.call_args
        message = call_args[1]['message']
        assert 'OI Change' not in message
        assert 'Volume Spike' not in message

    @pytest.mark.asyncio
    async def test_send_manipulation_alert_error_handling(self, manipulation_monitor, 
                                                        sample_market_data, mock_manipulation_alert):
        """Test error handling in alert sending."""
        # Configure alert manager to raise an exception
        manipulation_monitor.alert_manager.send_alert.side_effect = Exception("Alert error")
        
        await manipulation_monitor._send_manipulation_alert('BTCUSDT', mock_manipulation_alert, sample_market_data)
        
        # Should log the error
        manipulation_monitor.logger.error.assert_called_with(
            "Error sending manipulation alert for BTCUSDT: Alert error"
        )

    @pytest.mark.asyncio
    async def test_store_manipulation_data_success(self, manipulation_monitor, mock_manipulation_alert):
        """Test successful manipulation data storage."""
        await manipulation_monitor._store_manipulation_data('BTCUSDT', mock_manipulation_alert)
        
        # Should call database store method with correct data
        manipulation_monitor.database_client.store_manipulation_activity.assert_called_once()
        call_args = manipulation_monitor.database_client.store_manipulation_activity.call_args
        stored_data = call_args[0][0]
        
        assert stored_data['timestamp'] == 1640995200
        assert stored_data['symbol'] == 'BTCUSDT'
        assert stored_data['manipulation_type'] == 'pump_and_dump'
        assert stored_data['confidence_score'] == 0.85
        assert stored_data['severity'] == 'high'
        assert stored_data['description'] == 'Suspicious price and volume patterns detected'
        assert stored_data['metrics'] == mock_manipulation_alert.metrics

    @pytest.mark.asyncio
    async def test_store_manipulation_data_no_database(self, mock_logger, mock_config):
        """Test manipulation data storage without database client."""
        monitor = ManipulationMonitor(logger=mock_logger, config=mock_config)
        
        await monitor._store_manipulation_data('BTCUSDT', Mock())
        
        # Should not raise an error, just return silently
        assert True

    @pytest.mark.asyncio
    async def test_store_manipulation_data_error_handling(self, manipulation_monitor, mock_manipulation_alert):
        """Test error handling in data storage."""
        # Configure database to raise an exception
        manipulation_monitor.database_client.store_manipulation_activity.side_effect = Exception("DB error")
        
        await manipulation_monitor._store_manipulation_data('BTCUSDT', mock_manipulation_alert)
        
        # Should log the error
        manipulation_monitor.logger.error.assert_called_with(
            "Error storing manipulation data for BTCUSDT: DB error"
        )

    def test_get_manipulation_stats_with_detector(self, manipulation_monitor):
        """Test getting manipulation stats when detector is available."""
        expected_stats = {
            'total_analyses': 100,
            'alerts_generated': 5,
            'manipulation_detected': 3,
            'false_positives': 2,
            'avg_confidence': 0.75
        }
        manipulation_monitor.manipulation_detector.get_stats.return_value = expected_stats
        
        stats = manipulation_monitor.get_manipulation_stats()
        
        assert stats == expected_stats
        manipulation_monitor.manipulation_detector.get_stats.assert_called_once()

    def test_get_manipulation_stats_no_detector(self, mock_logger, mock_config):
        """Test getting manipulation stats without detector."""
        monitor = ManipulationMonitor(logger=mock_logger, config=mock_config)
        
        stats = monitor.get_manipulation_stats()
        
        expected_stats = {
            'total_analyses': 0,
            'alerts_generated': 0,
            'manipulation_detected': 0,
            'false_positives': 0,
            'avg_confidence': 0.0
        }
        assert stats == expected_stats

    def test_get_manipulation_stats_error_handling(self, manipulation_monitor):
        """Test error handling in getting manipulation stats."""
        manipulation_monitor.manipulation_detector.get_stats.side_effect = Exception("Stats error")
        
        stats = manipulation_monitor.get_manipulation_stats()
        
        assert stats == {}
        manipulation_monitor.logger.error.assert_called_with(
            "Error getting manipulation stats: Stats error"
        )

    def test_get_manipulation_history_with_detector(self, manipulation_monitor):
        """Test getting manipulation history when detector is available."""
        expected_history = {
            'BTCUSDT': [
                {'timestamp': 1640995200, 'type': 'pump_and_dump', 'confidence': 0.85}
            ]
        }
        manipulation_monitor.manipulation_detector.get_manipulation_history.return_value = expected_history
        
        history = manipulation_monitor.get_manipulation_history('BTCUSDT')
        
        assert history == expected_history
        manipulation_monitor.manipulation_detector.get_manipulation_history.assert_called_once_with('BTCUSDT')

    def test_get_manipulation_history_no_detector(self, mock_logger, mock_config):
        """Test getting manipulation history without detector."""
        monitor = ManipulationMonitor(logger=mock_logger, config=mock_config)
        
        history = monitor.get_manipulation_history()
        
        assert history == {}

    def test_get_manipulation_history_error_handling(self, manipulation_monitor):
        """Test error handling in getting manipulation history."""
        manipulation_monitor.manipulation_detector.get_manipulation_history.side_effect = Exception("History error")
        
        history = manipulation_monitor.get_manipulation_history()
        
        assert history == {}
        manipulation_monitor.logger.error.assert_called_with(
            "Error getting manipulation history: History error"
        )

    def test_is_manipulation_detector_available(self, manipulation_monitor):
        """Test checking if manipulation detector is available."""
        assert manipulation_monitor.is_manipulation_detector_available() is True
        
        manipulation_monitor.manipulation_detector = None
        assert manipulation_monitor.is_manipulation_detector_available() is False

    def test_is_alert_manager_available(self, manipulation_monitor):
        """Test checking if alert manager is available."""
        assert manipulation_monitor.is_alert_manager_available() is True
        
        manipulation_monitor.alert_manager = None
        assert manipulation_monitor.is_alert_manager_available() is False

    def test_is_database_client_available(self, manipulation_monitor):
        """Test checking if database client is available."""
        assert manipulation_monitor.is_database_client_available() is True
        
        manipulation_monitor.database_client = None
        assert manipulation_monitor.is_database_client_available() is False

    def test_get_component_status(self, manipulation_monitor):
        """Test getting component status."""
        status = manipulation_monitor.get_component_status()
        
        expected_status = {
            'manipulation_detector': True,
            'alert_manager': True,
            'database_client': True
        }
        assert status == expected_status

    def test_get_component_status_missing_components(self, mock_logger, mock_config):
        """Test getting component status with missing components."""
        monitor = ManipulationMonitor(logger=mock_logger, config=mock_config)
        
        status = monitor.get_component_status()
        
        expected_status = {
            'manipulation_detector': False,
            'alert_manager': False,
            'database_client': False
        }
        assert status == expected_status

    @pytest.mark.asyncio
    async def test_full_integration_manipulation_detected(self, manipulation_monitor, 
                                                        sample_market_data, mock_manipulation_alert):
        """Test full integration when manipulation is detected."""
        # Configure detector to return an alert
        manipulation_monitor.manipulation_detector.analyze_market_data.return_value = mock_manipulation_alert
        
        # Test the full flow
        await manipulation_monitor.monitor_manipulation_activity('BTCUSDT', sample_market_data)
        
        # Verify all components were called
        manipulation_monitor.manipulation_detector.analyze_market_data.assert_called_once()
        manipulation_monitor.alert_manager.send_alert.assert_called_once()
        manipulation_monitor.database_client.store_manipulation_activity.assert_called_once()
        
        # Verify logging
        manipulation_monitor.logger.warning.assert_called()
        manipulation_monitor.logger.info.assert_called_with(
            "Sent manipulation alert for BTCUSDT: pump_and_dump (confidence: 85.0%)"
        )
        manipulation_monitor.logger.debug.assert_called_with(
            "Stored manipulation data for BTCUSDT in database"
        ) 