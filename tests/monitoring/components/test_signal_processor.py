"""
Tests for SignalProcessor component.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid
import os

from src.monitoring.components.signal_processor import SignalProcessor, DataUnavailableError
from src.monitoring.utilities.timestamp_utils import TimestampUtility


class TestSignalProcessor:
    """Test cases for SignalProcessor component."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            'confluence': {
                'thresholds': {
                    'buy': 60.0,
                    'sell': 40.0
                }
            },
            'trading': {
                'risk': {
                    'max_risk_per_trade': 0.02,
                    'stop_loss_percentage': 0.02
                },
                'account_balance': 10000
            }
        }

    @pytest.fixture
    def mock_signal_generator(self):
        """Create a mock signal generator."""
        mock = Mock()
        mock._generate_enhanced_formatted_data = Mock(return_value={
            'market_interpretations': [
                {'component': 'Technical', 'display_name': 'Technical', 'interpretation': 'Bullish trend'},
                {'component': 'Volume', 'display_name': 'Volume', 'interpretation': 'High volume'}
            ],
            'actionable_insights': ['Buy signal detected'],
            'influential_components': ['technical', 'volume']
        })
        mock.report_manager = Mock()
        mock.report_manager.generate_and_attach_report = AsyncMock(return_value=(True, '/path/to/report.pdf', None))
        mock.generate_signals = AsyncMock(return_value=[{'signal': 'BUY', 'symbol': 'BTCUSDT'}])
        return mock

    @pytest.fixture
    def mock_alert_manager(self):
        """Create a mock alert manager."""
        mock = Mock()
        mock.handlers = ['discord', 'email']
        mock.process_signals = AsyncMock()
        return mock

    @pytest.fixture
    def mock_market_data_manager(self):
        """Create a mock market data manager."""
        mock = Mock()
        mock.get_market_data = AsyncMock(return_value={
            'ticker': {'last': 50000.0, 'close': 49999.0}
        })
        return mock

    @pytest.fixture
    def mock_database_client(self):
        """Create a mock database client."""
        mock = Mock()
        mock.store_analysis = AsyncMock()
        return mock

    @pytest.fixture
    def mock_confluence_analyzer(self):
        """Create a mock confluence analyzer."""
        mock = Mock()
        mock.analyze = AsyncMock(return_value={
            'confluence_score': 75.0,
            'components': {'technical': 80, 'volume': 70},
            'results': {'trend': 'bullish'},
            'reliability': 0.8
        })
        return mock

    @pytest.fixture
    def signal_processor(self, mock_logger, mock_config, mock_signal_generator, 
                        mock_alert_manager, mock_market_data_manager, 
                        mock_database_client, mock_confluence_analyzer):
        """Create a SignalProcessor instance with mocked dependencies."""
        return SignalProcessor(
            logger=mock_logger,
            config=mock_config,
            signal_generator=mock_signal_generator,
            alert_manager=mock_alert_manager,
            market_data_manager=mock_market_data_manager,
            database_client=mock_database_client,
            confluence_analyzer=mock_confluence_analyzer,
            timestamp_utility=TimestampUtility()
        )

    @pytest.mark.asyncio
    async def test_process_analysis_result_success(self, signal_processor):
        """Test successful processing of analysis result."""
        symbol = "BTCUSDT"
        result = {
            'confluence_score': 75.0,
            'components': {'technical': 80},
            'reliability': 0.8
        }

        with patch.object(signal_processor, '_generate_signal', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {'signal': 'BUY'}
            
            await signal_processor.process_analysis_result(symbol, result)
            
            # Verify transaction ID was added
            assert 'transaction_id' in result
            mock_generate.assert_called_once_with(symbol, result)

    @pytest.mark.asyncio
    async def test_process_analysis_result_invalid_result(self, signal_processor):
        """Test processing with invalid analysis result."""
        symbol = "BTCUSDT"
        result = None

        with patch.object(signal_processor, '_generate_signal', new_callable=AsyncMock) as mock_generate:
            await signal_processor.process_analysis_result(symbol, result)
            
            # Should not call _generate_signal with invalid result
            mock_generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_signal_success(self, signal_processor):
        """Test successful signal generation."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 75.0,
            'components': {'technical': 80, 'volume': 70},
            'results': {'trend': 'bullish'},
            'reliability': 0.8,
            'price': 50000.0,
            'transaction_id': str(uuid.uuid4())
        }

        signal = await signal_processor._generate_signal(symbol, analysis_result)
        
        assert signal is not None
        assert signal['symbol'] == symbol
        assert signal['confluence_score'] == 75.0
        assert signal['signal_type'] == 'BUY'  # Above buy threshold of 60
        assert signal['reliability'] == 0.8
        assert signal['price'] == 50000.0
        assert 'trade_params' in signal
        assert 'timestamp' in signal

    @pytest.mark.asyncio
    async def test_generate_signal_sell_signal(self, signal_processor):
        """Test generation of sell signal."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 30.0,  # Below sell threshold of 40
            'components': {'technical': 20, 'volume': 40},
            'results': {'trend': 'bearish'},
            'reliability': 0.7,
            'price': 50000.0,
            'transaction_id': str(uuid.uuid4())
        }

        signal = await signal_processor._generate_signal(symbol, analysis_result)
        
        assert signal is not None
        assert signal['signal_type'] == 'SELL'

    @pytest.mark.asyncio
    async def test_generate_signal_neutral_signal(self, signal_processor):
        """Test generation of neutral signal."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 50.0,  # Between thresholds
            'components': {'technical': 50, 'volume': 50},
            'results': {'trend': 'sideways'},
            'reliability': 0.6,
            'price': 50000.0,
            'transaction_id': str(uuid.uuid4())
        }

        signal = await signal_processor._generate_signal(symbol, analysis_result)
        
        assert signal is not None
        assert signal['signal_type'] == 'NEUTRAL'

    @pytest.mark.asyncio
    async def test_generate_signal_no_signal_generator(self, mock_logger, mock_config):
        """Test signal generation without signal generator."""
        processor = SignalProcessor(logger=mock_logger, config=mock_config)
        
        symbol = "BTCUSDT"
        analysis_result = {'confluence_score': 75.0}

        signal = await processor._generate_signal(symbol, analysis_result)
        
        assert signal is None
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_generate_signal_price_from_market_data_manager(self, signal_processor):
        """Test price retrieval from market data manager when not in analysis result."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 75.0,
            'components': {'technical': 80},
            'reliability': 0.8,
            'transaction_id': str(uuid.uuid4())
        }

        signal = await signal_processor._generate_signal(symbol, analysis_result)
        
        assert signal is not None
        assert signal['price'] == 50000.0  # From mock market data manager

    def test_calculate_trade_parameters_buy_signal(self, signal_processor):
        """Test trade parameter calculation for buy signal."""
        symbol = "BTCUSDT"
        price = 50000.0
        signal_type = "BUY"
        score = 75.0
        reliability = 0.8

        params = signal_processor._calculate_trade_parameters(symbol, price, signal_type, score, reliability)
        
        assert params['entry_price'] == price
        assert params['stop_loss'] < price  # Stop loss below entry for buy
        assert params['take_profit'] > price  # Take profit above entry for buy
        assert params['risk_reward_ratio'] == 2.0
        assert params['confidence'] > 0
        assert params['position_size'] > 0

    def test_calculate_trade_parameters_sell_signal(self, signal_processor):
        """Test trade parameter calculation for sell signal."""
        symbol = "BTCUSDT"
        price = 50000.0
        signal_type = "SELL"
        score = 25.0
        reliability = 0.7

        params = signal_processor._calculate_trade_parameters(symbol, price, signal_type, score, reliability)
        
        assert params['entry_price'] == price
        assert params['stop_loss'] > price  # Stop loss above entry for sell
        assert params['take_profit'] < price  # Take profit below entry for sell
        assert params['risk_reward_ratio'] == 2.0

    def test_calculate_trade_parameters_neutral_signal(self, signal_processor):
        """Test trade parameter calculation for neutral signal."""
        symbol = "BTCUSDT"
        price = 50000.0
        signal_type = "NEUTRAL"
        score = 50.0
        reliability = 0.6

        params = signal_processor._calculate_trade_parameters(symbol, price, signal_type, score, reliability)
        
        assert params['entry_price'] == price
        assert params['stop_loss'] is None
        assert params['take_profit'] is None
        assert params['position_size'] is None

    def test_calculate_trade_parameters_none_price(self, signal_processor):
        """Test trade parameter calculation with None price."""
        symbol = "BTCUSDT"
        price = None
        signal_type = "BUY"
        score = 75.0
        reliability = 0.8

        params = signal_processor._calculate_trade_parameters(symbol, price, signal_type, score, reliability)
        
        assert params['entry_price'] is None
        assert params['stop_loss'] is None
        assert params['take_profit'] is None
        assert params['position_size'] is None

    def test_calculate_trade_parameters_none_values(self, signal_processor):
        """Test trade parameter calculation with None score and reliability."""
        symbol = "BTCUSDT"
        price = 50000.0
        signal_type = "BUY"
        score = None
        reliability = None

        params = signal_processor._calculate_trade_parameters(symbol, price, signal_type, score, reliability)
        
        # Should use default values
        assert params['entry_price'] == price
        assert params['confidence'] == 0.25  # (50/100) * 0.5

    @pytest.mark.asyncio
    async def test_analyze_confluence_and_generate_signals_success(self, signal_processor):
        """Test successful confluence analysis and signal generation."""
        market_data = {
            'symbol': 'BTCUSDT',
            'ticker': {'last': 50000.0},
            'ohlcv': {'base': 'mock_data'}
        }

        await signal_processor.analyze_confluence_and_generate_signals(market_data)
        
        # Verify confluence analyzer was called
        signal_processor.confluence_analyzer.analyze.assert_called_once_with(market_data)
        
        # Verify signal generator was called
        signal_processor.signal_generator.generate_signals.assert_called_once()
        
        # Verify alert manager processed signals
        signal_processor.alert_manager.process_signals.assert_called_once()
        
        # Verify database storage
        signal_processor.database_client.store_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_confluence_data_unavailable_error(self, signal_processor):
        """Test confluence analysis with DataUnavailableError."""
        market_data = {'symbol': 'BTCUSDT'}
        
        signal_processor.confluence_analyzer.analyze.side_effect = DataUnavailableError("No data")

        await signal_processor.analyze_confluence_and_generate_signals(market_data)
        
        # Should return early without generating signals
        signal_processor.signal_generator.generate_signals.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_confluence_no_signal_generator(self, mock_logger, mock_config, mock_confluence_analyzer):
        """Test confluence analysis without signal generator."""
        processor = SignalProcessor(
            logger=mock_logger,
            config=mock_config,
            confluence_analyzer=mock_confluence_analyzer
        )
        
        market_data = {'symbol': 'BTCUSDT'}

        await processor.analyze_confluence_and_generate_signals(market_data)
        
        # Should return early without signal generator
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_confluence_exception_handling(self, signal_processor):
        """Test exception handling in confluence analysis."""
        market_data = {'symbol': 'BTCUSDT'}
        
        signal_processor.confluence_analyzer.analyze.side_effect = Exception("Test error")

        await signal_processor.analyze_confluence_and_generate_signals(market_data)
        
        # Should use default scores and continue
        signal_processor.signal_generator.generate_signals.assert_called_once()

    def test_get_default_scores(self, signal_processor):
        """Test generation of default scores."""
        symbol = "BTCUSDT"
        
        scores = signal_processor._get_default_scores(symbol)
        
        assert scores['confluence_score'] == 50.0
        assert scores['symbol'] == symbol
        assert scores['reliability'] == 0.5
        assert 'timestamp' in scores

    def test_get_ohlcv_for_report(self, signal_processor):
        """Test OHLCV data retrieval for reports."""
        symbol = "BTCUSDT"
        timeframe = "ltf"
        
        result = signal_processor._get_ohlcv_for_report(symbol, timeframe)
        
        # Should return None as it's not implemented in the component
        assert result is None

    @pytest.mark.asyncio
    async def test_signal_generation_with_enhanced_data(self, signal_processor):
        """Test signal generation with enhanced formatted data."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 75.0,
            'components': {'technical': 80, 'volume': 70},
            'results': {'trend': 'bullish'},
            'reliability': 0.8,
            'price': 50000.0,
            'transaction_id': str(uuid.uuid4())
        }

        signal = await signal_processor._generate_signal(symbol, analysis_result)
        
        assert signal is not None
        assert 'market_interpretations' in signal
        assert 'actionable_insights' in signal
        assert 'influential_components' in signal
        
        # Verify enhanced data was processed
        assert len(signal['market_interpretations']) == 2
        assert signal['actionable_insights'] == ['Buy signal detected']

    @pytest.mark.asyncio
    async def test_signal_generation_with_report_generation(self, signal_processor):
        """Test signal generation with PDF report generation."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 75.0,
            'components': {'technical': 80},
            'reliability': 0.8,
            'price': 50000.0,
            'transaction_id': str(uuid.uuid4())
        }

        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000):
            
            signal = await signal_processor._generate_signal(symbol, analysis_result)
            
            assert signal is not None
            assert 'pdf_path' in signal
            
            # Verify report manager was called
            signal_processor.signal_generator.report_manager.generate_and_attach_report.assert_called()

    @pytest.mark.asyncio
    async def test_signal_generation_error_handling(self, signal_processor):
        """Test error handling in signal generation."""
        symbol = "BTCUSDT"
        analysis_result = {
            'confluence_score': 75.0,
            'transaction_id': str(uuid.uuid4())
        }

        # Make trade parameter calculation fail
        with patch.object(signal_processor, '_calculate_trade_parameters', side_effect=Exception("Test error")):
            signal = await signal_processor._generate_signal(symbol, analysis_result)
            
            assert signal is not None
            # Should have default trade parameters with the price from market data manager
            assert signal['trade_params']['entry_price'] == 50000.0  # Price from mock market data manager
            assert signal['trade_params']['stop_loss'] is None
            assert signal['trade_params']['take_profit'] is None

    def test_initialization_with_defaults(self):
        """Test SignalProcessor initialization with default values."""
        processor = SignalProcessor()
        
        assert processor.logger is not None
        assert processor.config == {}
        assert processor.signal_generator is None
        assert processor.alert_manager is None
        assert processor.market_data_manager is None
        assert processor.database_client is None
        assert processor.confluence_analyzer is None
        assert processor.timestamp_utility is not None

    def test_initialization_with_custom_values(self, mock_logger, mock_config):
        """Test SignalProcessor initialization with custom values."""
        processor = SignalProcessor(logger=mock_logger, config=mock_config)
        
        assert processor.logger == mock_logger
        assert processor.config == mock_config 