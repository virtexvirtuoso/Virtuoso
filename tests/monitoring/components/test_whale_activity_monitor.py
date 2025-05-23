"""
Tests for WhaleActivityMonitor component.
"""

import pytest
import asyncio
import logging
import time
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.monitoring.components.whale_activity_monitor import WhaleActivityMonitor


class TestWhaleActivityMonitor:
    """Test cases for WhaleActivityMonitor component."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            'whale_activity': {
                'enabled': True,
                'cooldown': 900,
                'accumulation_threshold': 1000000,
                'distribution_threshold': 1000000,
                'imbalance_threshold': 0.2,
                'min_order_count': 5,
                'market_percentage': 0.02
            }
        }

    @pytest.fixture
    def mock_alert_manager(self):
        """Create a mock alert manager."""
        mock = Mock()
        mock.send_alert = AsyncMock()
        return mock

    @pytest.fixture
    def whale_monitor(self, mock_logger, mock_config, mock_alert_manager):
        """Create a WhaleActivityMonitor instance with mocked dependencies."""
        return WhaleActivityMonitor(
            logger=mock_logger,
            config=mock_config,
            alert_manager=mock_alert_manager
        )

    @pytest.fixture
    def sample_orderbook(self):
        """Create a sample orderbook for testing."""
        return {
            'bids': [
                [50000, 1.0],
                [49990, 2.0],
                [49980, 10.0],  # Large whale order
                [49970, 1.5],
                [49960, 8.0]   # Large whale order
            ],
            'asks': [
                [50010, 1.0],
                [50020, 2.0],
                [50030, 12.0], # Large whale order
                [50040, 1.5],
                [50050, 1.0]
            ]
        }

    @pytest.fixture
    def sample_trades(self):
        """Create sample trades for testing."""
        current_time = time.time()
        return [
            {
                'timestamp': int((current_time - 600) * 1000),  # 10 minutes ago
                'side': 'buy',
                'amount': 15.0,  # Large whale trade
                'price': 50000
            },
            {
                'timestamp': int((current_time - 300) * 1000),  # 5 minutes ago
                'side': 'sell',
                'amount': 3.0,
                'price': 49995
            },
            {
                'timestamp': int((current_time - 100) * 1000),  # Recent
                'side': 'buy',
                'amount': 20.0,  # Large whale trade
                'price': 50005
            }
        ]

    @pytest.fixture
    def sample_market_data(self, sample_orderbook, sample_trades):
        """Create complete sample market data."""
        return {
            'orderbook': sample_orderbook,
            'trades': sample_trades,
            'ticker': {'last': 50000.0}
        }

    def test_initialization_with_defaults(self):
        """Test WhaleActivityMonitor initialization with default values."""
        monitor = WhaleActivityMonitor()
        
        assert monitor.logger is not None
        assert monitor.config == {}
        assert monitor.alert_manager is None
        assert monitor.whale_activity_config['enabled'] is True
        assert monitor.whale_activity_config['cooldown'] == 900
        assert monitor._last_whale_alert == {}
        assert monitor._last_whale_activity == {}

    def test_initialization_with_custom_values(self, mock_logger, mock_config, mock_alert_manager):
        """Test WhaleActivityMonitor initialization with custom values."""
        monitor = WhaleActivityMonitor(
            logger=mock_logger,
            config=mock_config,
            alert_manager=mock_alert_manager
        )
        
        assert monitor.logger == mock_logger
        assert monitor.config == mock_config
        assert monitor.alert_manager == mock_alert_manager
        assert monitor.whale_activity_config == mock_config['whale_activity']

    def test_calculate_whale_threshold_success(self, whale_monitor, sample_orderbook):
        """Test successful whale threshold calculation."""
        threshold = whale_monitor._calculate_whale_threshold(sample_orderbook)
        
        assert threshold > 0
        # Should be around mean + 2*std of order sizes
        all_sizes = [1.0, 2.0, 10.0, 1.5, 8.0, 1.0, 2.0, 12.0, 1.5, 1.0]
        expected_threshold = np.mean(all_sizes) + 2 * np.std(all_sizes)
        assert abs(threshold - expected_threshold) < 0.1

    def test_calculate_whale_threshold_empty_orderbook(self, whale_monitor):
        """Test whale threshold calculation with empty orderbook."""
        empty_orderbook = {'bids': [], 'asks': []}
        
        threshold = whale_monitor._calculate_whale_threshold(empty_orderbook)
        
        assert threshold == 0

    def test_calculate_whale_threshold_invalid_orders(self, whale_monitor):
        """Test whale threshold calculation with invalid order format."""
        invalid_orderbook = {
            'bids': ['invalid', [50000]],  # Invalid formats
            'asks': [None, {}]
        }
        
        threshold = whale_monitor._calculate_whale_threshold(invalid_orderbook)
        
        assert threshold == 0

    def test_analyze_orderbook_whale_activity_success(self, whale_monitor, sample_orderbook):
        """Test successful orderbook whale activity analysis."""
        whale_threshold = 5.0  # Set threshold to catch whale orders
        current_price = 50000.0
        
        analysis = whale_monitor._analyze_orderbook_whale_activity(
            sample_orderbook, whale_threshold, current_price
        )
        
        assert analysis['whale_bid_volume'] == 18.0  # 10.0 + 8.0
        assert analysis['whale_ask_volume'] == 12.0
        assert analysis['net_volume'] == 6.0  # 18.0 - 12.0
        assert analysis['net_usd_value'] == 300000.0  # 6.0 * 50000
        assert analysis['whale_bid_orders'] == 2
        assert analysis['whale_ask_orders'] == 1
        assert analysis['imbalance'] > 0

    def test_analyze_orderbook_whale_activity_no_whales(self, whale_monitor, sample_orderbook):
        """Test orderbook analysis with high threshold (no whale orders)."""
        whale_threshold = 100.0  # Very high threshold
        current_price = 50000.0
        
        analysis = whale_monitor._analyze_orderbook_whale_activity(
            sample_orderbook, whale_threshold, current_price
        )
        
        assert analysis['whale_bid_volume'] == 0
        assert analysis['whale_ask_volume'] == 0
        assert analysis['net_volume'] == 0
        assert analysis['whale_bid_orders'] == 0
        assert analysis['whale_ask_orders'] == 0

    def test_analyze_trade_whale_activity_success(self, whale_monitor, sample_trades):
        """Test successful trade whale activity analysis."""
        whale_threshold = 10.0  # Set threshold to catch whale trades
        current_time = time.time()
        
        analysis = whale_monitor._analyze_trade_whale_activity(
            sample_trades, whale_threshold, current_time
        )
        
        assert analysis['whale_trades_count'] == 2  # 15.0 and 20.0 trades
        assert analysis['whale_buy_volume'] == 35.0  # 15.0 + 20.0
        assert analysis['whale_sell_volume'] == 0
        assert analysis['net_trade_volume'] == 35.0
        assert analysis['trade_imbalance'] == 1.0

    def test_analyze_trade_whale_activity_empty_trades(self, whale_monitor):
        """Test trade analysis with empty trades list."""
        analysis = whale_monitor._analyze_trade_whale_activity([], 10.0, time.time())
        
        assert analysis == {}

    def test_analyze_trade_whale_activity_old_trades(self, whale_monitor):
        """Test trade analysis with only old trades."""
        old_trades = [{
            'timestamp': int((time.time() - 3600) * 1000),  # 1 hour ago
            'side': 'buy',
            'amount': 50.0,
            'price': 50000
        }]
        
        analysis = whale_monitor._analyze_trade_whale_activity(
            old_trades, 10.0, time.time()
        )
        
        assert analysis['whale_trades_count'] == 0
        assert analysis['whale_buy_volume'] == 0
        assert analysis['whale_sell_volume'] == 0

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_disabled(self, whale_monitor, sample_market_data):
        """Test whale activity monitoring when disabled in config."""
        whale_monitor.whale_activity_config['enabled'] = False
        
        await whale_monitor.monitor_whale_activity('BTCUSDT', sample_market_data)
        
        # Should not send any alerts
        whale_monitor.alert_manager.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_no_alert_manager(self, mock_logger, mock_config):
        """Test whale activity monitoring without alert manager."""
        monitor = WhaleActivityMonitor(logger=mock_logger, config=mock_config)
        
        await monitor.monitor_whale_activity('BTCUSDT', {'orderbook': {}})
        
        # Should log debug message about no alert manager
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_cooldown_period(self, whale_monitor, sample_market_data):
        """Test whale activity monitoring during cooldown period."""
        symbol = 'BTCUSDT'
        whale_monitor._last_whale_alert[symbol] = time.time() - 300  # 5 minutes ago
        
        await whale_monitor.monitor_whale_activity(symbol, sample_market_data)
        
        # Should not send alerts due to cooldown
        whale_monitor.alert_manager.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_invalid_orderbook(self, whale_monitor):
        """Test whale activity monitoring with invalid orderbook."""
        market_data = {
            'orderbook': None,
            'ticker': {'last': 50000.0}
        }
        
        await whale_monitor.monitor_whale_activity('BTCUSDT', market_data)
        
        # Should not send alerts
        whale_monitor.alert_manager.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_no_price(self, whale_monitor, sample_orderbook):
        """Test whale activity monitoring without price information."""
        market_data = {
            'orderbook': sample_orderbook,
            'ticker': {}
        }
        
        await whale_monitor.monitor_whale_activity('BTCUSDT', market_data)
        
        # Should not send alerts
        whale_monitor.alert_manager.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_generate_alerts_accumulation(self, whale_monitor):
        """Test alert generation for whale accumulation."""
        symbol = 'BTCUSDT'
        current_activity = {
            'net_usd_value': 2000000,  # Above threshold
            'net_volume': 40.0,
            'imbalance': 0.3,  # Above threshold
            'bid_percentage': 0.03,  # Above threshold
            'whale_bid_orders': 6,  # Above minimum
            'whale_ask_orders': 2,
            'whale_trades_count': 3,
            'whale_buy_volume': 35.0,
            'whale_sell_volume': 5.0,
            'net_trade_volume': 30.0,
            'trade_imbalance': 0.8
        }
        current_price = 50000.0
        
        await whale_monitor._check_and_generate_alerts(symbol, current_activity, current_price)
        
        # Should send accumulation alert
        whale_monitor.alert_manager.send_alert.assert_called_once()
        call_args = whale_monitor.alert_manager.send_alert.call_args
        assert call_args[1]['level'] == 'info'
        assert 'Whale Accumulation Detected' in call_args[1]['message']
        assert call_args[1]['details']['subtype'] == 'accumulation'

    @pytest.mark.asyncio
    async def test_check_and_generate_alerts_distribution(self, whale_monitor):
        """Test alert generation for whale distribution."""
        symbol = 'BTCUSDT'
        current_activity = {
            'net_usd_value': -2000000,  # Below negative threshold
            'net_volume': -40.0,
            'imbalance': 0.3,  # Above threshold
            'ask_percentage': 0.03,  # Above threshold
            'whale_ask_orders': 6,  # Above minimum
            'whale_bid_orders': 2,
            'whale_trades_count': 3,
            'whale_buy_volume': 5.0,
            'whale_sell_volume': 35.0,
            'net_trade_volume': -30.0,
            'trade_imbalance': -0.8
        }
        current_price = 50000.0
        
        await whale_monitor._check_and_generate_alerts(symbol, current_activity, current_price)
        
        # Should send distribution alert
        whale_monitor.alert_manager.send_alert.assert_called_once()
        call_args = whale_monitor.alert_manager.send_alert.call_args
        assert call_args[1]['level'] == 'info'
        assert 'Whale Distribution Detected' in call_args[1]['message']
        assert call_args[1]['details']['subtype'] == 'distribution'

    @pytest.mark.asyncio
    async def test_check_and_generate_alerts_no_significant_activity(self, whale_monitor):
        """Test alert generation with no significant activity."""
        symbol = 'BTCUSDT'
        current_activity = {
            'net_usd_value': 500000,  # Below threshold
            'imbalance': 0.1,  # Below threshold
            'whale_bid_orders': 2,  # Below minimum
            'whale_ask_orders': 2
        }
        current_price = 50000.0
        
        await whale_monitor._check_and_generate_alerts(symbol, current_activity, current_price)
        
        # Should not send any alerts
        whale_monitor.alert_manager.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_accumulation_alert_with_trade_confirmation(self, whale_monitor):
        """Test accumulation alert generation with trade confirmation."""
        symbol = 'BTCUSDT'
        current_activity = {
            'net_volume': 40.0,
            'net_usd_value': 2000000,
            'whale_bid_orders': 6,
            'bid_percentage': 0.03,
            'imbalance': 0.3,
            'whale_trades_count': 3,
            'whale_buy_volume': 35.0,
            'whale_sell_volume': 5.0,
            'net_trade_volume': 30.0,
            'trade_imbalance': 0.8
        }
        current_price = 50000.0
        
        await whale_monitor._generate_accumulation_alert(symbol, current_activity, current_price)
        
        # Should send alert with trade confirmation
        whale_monitor.alert_manager.send_alert.assert_called_once()
        call_args = whale_monitor.alert_manager.send_alert.call_args
        message = call_args[1]['message']
        assert 'Trade confirmation' in message
        assert '80% confirmed' in message
        
        # Should update last alert time
        assert symbol in whale_monitor._last_whale_alert

    @pytest.mark.asyncio
    async def test_generate_distribution_alert_with_contradiction(self, whale_monitor):
        """Test distribution alert generation with trade contradiction."""
        symbol = 'BTCUSDT'
        current_activity = {
            'net_volume': -40.0,
            'net_usd_value': -2000000,
            'whale_ask_orders': 6,
            'ask_percentage': 0.03,
            'imbalance': 0.3,
            'whale_trades_count': 3,
            'whale_buy_volume': 35.0,  # Contradicts distribution
            'whale_sell_volume': 5.0,
            'net_trade_volume': 30.0,  # Positive (contradicts orderbook)
            'trade_imbalance': 0.8
        }
        current_price = 50000.0
        
        await whale_monitor._generate_distribution_alert(symbol, current_activity, current_price)
        
        # Should send alert with warning about contradiction
        whale_monitor.alert_manager.send_alert.assert_called_once()
        call_args = whale_monitor.alert_manager.send_alert.call_args
        message = call_args[1]['message']
        assert 'Warning' in message
        assert 'distribution but recent trades show buying' in message

    def test_get_whale_activity_history_all_symbols(self, whale_monitor):
        """Test getting whale activity history for all symbols."""
        whale_monitor._last_whale_activity = {
            'BTCUSDT': {'timestamp': 123456, 'net_volume': 10.0},
            'ETHUSDT': {'timestamp': 123457, 'net_volume': -5.0}
        }
        
        history = whale_monitor.get_whale_activity_history()
        
        assert len(history) == 2
        assert 'BTCUSDT' in history
        assert 'ETHUSDT' in history

    def test_get_whale_activity_history_specific_symbol(self, whale_monitor):
        """Test getting whale activity history for a specific symbol."""
        whale_monitor._last_whale_activity = {
            'BTCUSDT': {'timestamp': 123456, 'net_volume': 10.0},
            'ETHUSDT': {'timestamp': 123457, 'net_volume': -5.0}
        }
        
        history = whale_monitor.get_whale_activity_history('BTCUSDT')
        
        assert history == {'timestamp': 123456, 'net_volume': 10.0}

    def test_get_whale_activity_history_unknown_symbol(self, whale_monitor):
        """Test getting whale activity history for unknown symbol."""
        history = whale_monitor.get_whale_activity_history('UNKNOWN')
        
        assert history == {}

    def test_get_whale_activity_stats(self, whale_monitor):
        """Test getting whale activity statistics."""
        whale_monitor._last_whale_activity = {
            'BTCUSDT': {'timestamp': 123456},
            'ETHUSDT': {'timestamp': 123457}
        }
        whale_monitor._last_whale_alert = {
            'BTCUSDT': 123456
        }
        
        stats = whale_monitor.get_whale_activity_stats()
        
        assert stats['monitored_symbols'] == 2
        assert stats['symbols_with_recent_alerts'] == 1
        assert 'config' in stats
        assert 'last_activity_timestamps' in stats

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_full_integration(self, whale_monitor, sample_market_data):
        """Test full integration of whale activity monitoring."""
        symbol = 'BTCUSDT'
        
        # Set up conditions for triggering an alert
        with patch.object(whale_monitor, '_calculate_whale_threshold', return_value=5.0):
            await whale_monitor.monitor_whale_activity(symbol, sample_market_data)
        
        # Should store activity data
        assert symbol in whale_monitor._last_whale_activity
        activity = whale_monitor._last_whale_activity[symbol]
        assert 'timestamp' in activity
        assert 'threshold' in activity
        assert 'whale_bid_volume' in activity

    @pytest.mark.asyncio
    async def test_monitor_whale_activity_error_handling(self, whale_monitor):
        """Test error handling in whale activity monitoring."""
        # Pass invalid market data to trigger an error
        await whale_monitor.monitor_whale_activity('BTCUSDT', 'invalid_data')
        
        # Should log the error
        whale_monitor.logger.error.assert_called()
        whale_monitor.logger.debug.assert_called() 