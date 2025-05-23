"""Tests for WebSocket processor component."""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock
import pandas as pd

from src.monitoring.components import WebSocketProcessor


class TestWebSocketProcessor:
    """Test WebSocketProcessor class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            'websocket': {
                'enabled': True,
                'url': 'wss://test.example.com'
            }
        }
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger(__name__)
    
    @pytest.fixture
    def metrics_manager(self):
        """Create mock metrics manager."""
        mock = Mock()
        mock.start_operation = Mock(return_value='test_operation')
        mock.end_operation = Mock()
        mock.record_metric = Mock()
        return mock
    
    @pytest.fixture
    def health_monitor(self):
        """Create mock health monitor."""
        mock = Mock()
        mock._create_alert = Mock()
        return mock
    
    @pytest.fixture
    def processor(self, config, logger, metrics_manager, health_monitor):
        """Create WebSocket processor instance."""
        return WebSocketProcessor(
            config=config,
            logger=logger,
            metrics_manager=metrics_manager,
            health_monitor=health_monitor
        )
    
    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor.config is not None
        assert processor.logger is not None
        assert processor.ws_manager is None
        assert 'ticker' in processor.ws_data
        assert 'kline' in processor.ws_data
        assert 'orderbook' in processor.ws_data
        assert 'trades' in processor.ws_data
        assert 'liquidations' in processor.ws_data
    
    def test_set_symbol_info(self, processor):
        """Test setting symbol information."""
        symbol = {'base': 'BTC', 'quote': 'USDT'}
        symbol_str = 'BTCUSDT'
        exchange_id = 'bybit'
        
        processor.set_symbol_info(symbol, symbol_str, exchange_id)
        
        assert processor.symbol == symbol
        assert processor.symbol_str == symbol_str
        assert processor.exchange_id == exchange_id
    
    def test_register_callback(self, processor):
        """Test registering data callbacks."""
        callback = Mock()
        
        processor.register_data_callback('ticker', callback)
        
        assert 'ticker' in processor.data_callbacks
        assert callback in processor.data_callbacks['ticker']
    
    @pytest.mark.asyncio
    async def test_notify_callbacks(self, processor):
        """Test callback notification."""
        sync_callback = Mock()
        async_callback = AsyncMock()
        
        processor.register_data_callback('ticker', sync_callback)
        processor.register_data_callback('ticker', async_callback)
        
        test_data = {'test': 'data'}
        
        await processor._notify_callbacks('ticker', test_data)
        
        sync_callback.assert_called_once_with('ticker', test_data)
        async_callback.assert_called_once_with('ticker', test_data)
    
    @pytest.mark.asyncio
    async def test_process_ticker_update(self, processor):
        """Test ticker update processing."""
        processor.set_symbol_info({'base': 'BTC', 'quote': 'USDT'}, 'BTCUSDT', 'bybit')
        
        message = {
            'data': {
                'data': {
                    'lastPrice': '50000.5',
                    'bid1Price': '50000.0',
                    'ask1Price': '50001.0',
                    'highPrice24h': '51000.0',
                    'lowPrice24h': '49000.0',
                    'volume24h': '1000.5',
                    'time': 1640995200000
                }
            },
            'timestamp': 1640995200000
        }
        
        await processor._process_ticker_update(message)
        
        ticker = processor.ws_data['ticker']
        assert ticker['last'] == 50000.5
        assert ticker['bid'] == 50000.0
        assert ticker['ask'] == 50001.0
        assert ticker['high'] == 51000.0
        assert ticker['low'] == 49000.0
        assert ticker['volume'] == 1000.5
        assert processor.ws_data['last_update_time']['ticker'] > 0
    
    @pytest.mark.asyncio
    async def test_process_kline_update(self, processor):
        """Test kline update processing."""
        processor.set_symbol_info({'base': 'BTC', 'quote': 'USDT'}, 'BTCUSDT', 'bybit')
        
        message = {
            'topic': 'klineV2.1',
            'data': {
                'data': [{
                    'timestamp': 1640995200000,
                    'open': '50000.0',
                    'high': '50100.0',
                    'low': '49900.0',
                    'close': '50050.0',
                    'volume': '100.5'
                }]
            },
            'timestamp': 1640995200000
        }
        
        await processor._process_kline_update(message)
        
        assert 'base' in processor.ws_data['kline']
        kline_df = processor.ws_data['kline']['base']
        assert isinstance(kline_df, pd.DataFrame)
        assert len(kline_df) == 1
        assert processor.ws_data['last_update_time']['kline'] > 0
    
    @pytest.mark.asyncio
    async def test_process_orderbook_update(self, processor):
        """Test orderbook update processing."""
        processor.set_symbol_info({'base': 'BTC', 'quote': 'USDT'}, 'BTCUSDT', 'bybit')
        
        message = {
            'data': {
                'data': {
                    'timestamp': 1640995200000,
                    'bids': [['50000.0', '10.0'], ['49999.0', '5.0']],
                    'asks': [['50001.0', '8.0'], ['50002.0', '12.0']]
                }
            },
            'timestamp': 1640995200000
        }
        
        await processor._process_orderbook_update(message)
        
        orderbook = processor.ws_data['orderbook']
        assert len(orderbook['bids']) == 2
        assert len(orderbook['asks']) == 2
        assert orderbook['bids'][0][0] == '50000.0'  # Best bid
        assert orderbook['asks'][0][0] == '50001.0'  # Best ask
        assert processor.ws_data['last_update_time']['orderbook'] > 0
    
    @pytest.mark.asyncio
    async def test_process_trade_update(self, processor):
        """Test trade update processing."""
        processor.set_symbol_info({'base': 'BTC', 'quote': 'USDT'}, 'BTCUSDT', 'bybit')
        
        message = {
            'data': {
                'data': [{
                    'tradeId': '12345',
                    'timestamp': 1640995200000,
                    'price': '50000.5',
                    'size': '1.5',
                    'side': 'buy'
                }]
            },
            'timestamp': 1640995200000
        }
        
        await processor._process_trade_update(message)
        
        trades = processor.ws_data['trades']
        assert len(trades) == 1
        assert trades[0]['id'] == '12345'
        assert trades[0]['price'] == 50000.5
        assert trades[0]['amount'] == 1.5
        assert trades[0]['side'] == 'buy'
        assert processor.ws_data['last_update_time']['trades'] > 0
    
    @pytest.mark.asyncio
    async def test_process_liquidation_update(self, processor, health_monitor):
        """Test liquidation update processing."""
        processor.set_symbol_info({'base': 'BTC', 'quote': 'USDT'}, 'BTCUSDT', 'bybit')
        
        message = {
            'data': {
                'data': {
                    'timestamp': 1640995200000,
                    'price': '50000.0',
                    'size': '2.5',
                    'side': 'long'
                }
            },
            'timestamp': 1640995200000
        }
        
        await processor._process_liquidation_update(message)
        
        liquidations = processor.ws_data['liquidations']
        assert len(liquidations) == 1
        assert liquidations[0]['price'] == 50000.0
        assert liquidations[0]['size'] == 2.5
        assert liquidations[0]['side'] == 'long'
        assert liquidations[0]['source'] == 'websocket'
        assert processor.ws_data['last_update_time']['liquidations'] > 0
        
        # Check health monitor alert was created
        health_monitor._create_alert.assert_called_once()
    
    def test_get_real_time_data(self, processor):
        """Test getting real-time data."""
        # Add some test data
        processor.ws_data['ticker'] = {'last': 50000.0}
        
        # Get all data
        all_data = processor.get_real_time_data()
        assert 'ticker' in all_data
        assert all_data['ticker']['last'] == 50000.0
        
        # Get specific data type
        ticker_data = processor.get_real_time_data('ticker')
        assert ticker_data['last'] == 50000.0
    
    def test_is_data_fresh(self, processor):
        """Test data freshness check."""
        current_time = processor.timestamp_utility.get_utc_timestamp()
        
        # No data yet
        assert not processor.is_data_fresh('ticker')
        
        # Fresh data
        processor.ws_data['last_update_time']['ticker'] = current_time
        assert processor.is_data_fresh('ticker', max_age_seconds=60.0)
        
        # Old data
        processor.ws_data['last_update_time']['ticker'] = current_time - 120000  # 2 minutes ago
        assert not processor.is_data_fresh('ticker', max_age_seconds=60.0)
    
    def test_get_websocket_status(self, processor):
        """Test getting WebSocket status."""
        # Without WebSocket manager
        status = processor.get_websocket_status()
        assert not status['connected']
        assert 'enabled' in status
        
        # With mock WebSocket manager
        ws_manager = Mock()
        ws_manager.get_status.return_value = {'connected': True, 'url': 'wss://test.com'}
        processor.ws_manager = ws_manager
        
        status = processor.get_websocket_status()
        assert status['connected']
        assert 'data_freshness' in status


if __name__ == "__main__":
    pytest.main([__file__]) 