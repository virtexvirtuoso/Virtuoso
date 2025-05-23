"""Tests for market data processor component."""

import pytest
import logging
from unittest.mock import Mock, AsyncMock
import pandas as pd

from src.monitoring.components import MarketDataProcessor
from src.monitoring.utilities import MarketDataValidator


class TestMarketDataProcessor:
    """Test MarketDataProcessor class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            'cache_ttl': 300,
            'timeframes': {
                'base': {'interval': '1m'},
                'ltf': {'interval': '5m'},
                'mtf': {'interval': '30m'},
                'htf': {'interval': '4h'}
            }
        }
    
    @pytest.fixture
    def logger(self):
        """Create test logger."""
        return logging.getLogger(__name__)
    
    @pytest.fixture
    def market_data_manager(self):
        """Create mock market data manager."""
        mock = Mock()
        mock.get_market_data = AsyncMock()
        mock.refresh_components = AsyncMock()
        return mock
    
    @pytest.fixture
    def validator(self, logger):
        """Create market data validator."""
        return MarketDataValidator(logger=logger)
    
    @pytest.fixture
    def processor(self, config, logger, market_data_manager, validator):
        """Create market data processor instance."""
        return MarketDataProcessor(
            config=config,
            logger=logger,
            market_data_manager=market_data_manager,
            validator=validator
        )
    
    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor.config is not None
        assert processor.logger is not None
        assert processor.market_data_manager is not None
        assert processor.validator is not None
        assert processor._cache_ttl == 300
        assert len(processor.timeframe_config) == 4
    
    @pytest.mark.asyncio
    async def test_fetch_market_data_success(self, processor, market_data_manager):
        """Test successful market data fetching."""
        symbol = 'BTCUSDT'
        test_data = {
            'symbol': symbol,
            'ohlcv': {'base': pd.DataFrame()},
            'ticker': {'last': 50000.0}
        }
        
        market_data_manager.get_market_data.return_value = test_data
        
        result = await processor.fetch_market_data(symbol)
        
        assert result == test_data
        assert symbol in processor._market_data_cache
        market_data_manager.get_market_data.assert_called_once_with(symbol)
    
    @pytest.mark.asyncio
    async def test_fetch_market_data_cached(self, processor):
        """Test fetching cached market data."""
        symbol = 'BTCUSDT'
        test_data = {'symbol': symbol, 'ticker': {'last': 50000.0}}
        current_time = processor.timestamp_utility.get_utc_timestamp(as_ms=False)
        
        # Add to cache
        processor._market_data_cache[symbol] = {
            'data': test_data,
            'fetch_time': current_time - 100  # 100 seconds ago
        }
        
        result = await processor.fetch_market_data(symbol)
        
        assert result == test_data
        # Should not call market data manager
        processor.market_data_manager.get_market_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetch_market_data_no_manager(self, config, logger, validator):
        """Test fetching market data without manager."""
        processor = MarketDataProcessor(
            config=config,
            logger=logger,
            market_data_manager=None,
            validator=validator
        )
        
        result = await processor.fetch_market_data('BTCUSDT')
        
        assert result == {}
    
    def test_standardize_ohlcv_list_of_lists(self, processor):
        """Test OHLCV standardization with list of lists format."""
        raw_ohlcv = [
            [1640995200000, 50000.0, 50100.0, 49900.0, 50050.0, 100.5],
            [1640995260000, 50050.0, 50150.0, 49950.0, 50100.0, 95.2]
        ]
        
        result = processor.standardize_ohlcv(raw_ohlcv)
        
        assert 'base' in result
        assert 'ltf' in result
        assert 'mtf' in result
        assert 'htf' in result
        
        base_df = result['base']
        assert isinstance(base_df, pd.DataFrame)
        assert len(base_df) == 2
        assert 'open' in base_df.columns
        assert 'high' in base_df.columns
        assert 'low' in base_df.columns
        assert 'close' in base_df.columns
        assert 'volume' in base_df.columns
    
    def test_standardize_ohlcv_list_of_dicts(self, processor):
        """Test OHLCV standardization with list of dicts format."""
        raw_ohlcv = [
            {
                't': 1640995200000,
                'o': 50000.0,
                'h': 50100.0,
                'l': 49900.0,
                'c': 50050.0,
                'v': 100.5
            },
            {
                't': 1640995260000,
                'o': 50050.0,
                'h': 50150.0,
                'l': 49950.0,
                'c': 50100.0,
                'v': 95.2
            }
        ]
        
        result = processor.standardize_ohlcv(raw_ohlcv)
        
        assert 'base' in result
        base_df = result['base']
        assert isinstance(base_df, pd.DataFrame)
        assert len(base_df) == 2
        assert 'timestamp' in base_df.columns
        assert 'open' in base_df.columns
    
    def test_standardize_ohlcv_empty(self, processor):
        """Test OHLCV standardization with empty data."""
        result = processor.standardize_ohlcv([])
        
        assert 'base' in result
        assert 'ltf' in result
        assert 'mtf' in result
        assert 'htf' in result
        
        for tf_key, df in result.items():
            assert isinstance(df, pd.DataFrame)
            assert df.empty
    
    def test_convert_to_dataframe_list_format(self, processor):
        """Test converting list format to DataFrame."""
        raw_data = [
            [1640995200000, 50000.0, 50100.0, 49900.0, 50050.0, 100.5]
        ]
        
        df = processor._convert_to_dataframe(raw_data)
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'timestamp' in df.columns
        assert 'open' in df.columns
    
    def test_convert_to_dataframe_dict_format(self, processor):
        """Test converting dict format to DataFrame."""
        raw_data = [
            {'time': 1640995200000, 'o': 50000.0, 'h': 50100.0, 'l': 49900.0, 'c': 50050.0, 'v': 100.5}
        ]
        
        df = processor._convert_to_dataframe(raw_data)
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'timestamp' in df.columns  # Should be renamed from 'time'
        assert 'open' in df.columns  # Should be renamed from 'o'
    
    def test_resample_ohlcv(self, processor):
        """Test OHLCV resampling."""
        # Create test DataFrame
        data = [
            [1640995200000, 50000.0, 50100.0, 49900.0, 50050.0, 100.5],
            [1640995260000, 50050.0, 50150.0, 49950.0, 50100.0, 95.2],
            [1640995320000, 50100.0, 50200.0, 50000.0, 50150.0, 80.3]
        ]
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('datetime')
        
        resampled = processor._resample_ohlcv(df, '5Min')
        
        assert isinstance(resampled, pd.DataFrame)
        assert len(resampled) > 0
        assert 'open' in resampled.columns
        assert 'high' in resampled.columns
        assert 'low' in resampled.columns
        assert 'close' in resampled.columns
        assert 'volume' in resampled.columns
    
    def test_resample_ohlcv_empty(self, processor):
        """Test resampling empty DataFrame."""
        empty_df = pd.DataFrame()
        
        result = processor._resample_ohlcv(empty_df, '5Min')
        
        assert result.empty
    
    @pytest.mark.asyncio
    async def test_process_symbol_success(self, processor, market_data_manager):
        """Test successful symbol processing."""
        symbol = 'BTCUSDT'
        test_data = {
            'symbol': symbol,
            'timestamp': 1640995200000,  # Add required timestamp field
            'ohlcv': {  # OHLCV should be a dictionary with timeframes
                'base': pd.DataFrame([
                    [1640995200000, 50000.0, 50100.0, 49900.0, 50050.0, 100.5]
                ], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            },
            'ticker': {'last': 50000.0, 'bid': 49999.0, 'ask': 50001.0, 'high': 51000.0, 'low': 49000.0, 'volume': 1000.0}
        }
        
        market_data_manager.get_market_data.return_value = test_data
        
        result = await processor.process_symbol(symbol)
        
        assert result is not None
        assert result['symbol'] == symbol
        assert 'ohlcv' in result
        assert isinstance(result['ohlcv'], dict)
        assert 'base' in result['ohlcv']
    
    @pytest.mark.asyncio
    async def test_process_symbol_no_data(self, processor, market_data_manager):
        """Test processing symbol with no data."""
        symbol = 'BTCUSDT'
        market_data_manager.get_market_data.return_value = {}
        
        result = await processor.process_symbol(symbol)
        
        assert result is None
    
    def test_get_cached_data_exists(self, processor):
        """Test getting existing cached data."""
        symbol = 'BTCUSDT'
        test_data = {'symbol': symbol, 'ticker': {'last': 50000.0}}
        current_time = processor.timestamp_utility.get_utc_timestamp(as_ms=False)
        
        processor._market_data_cache[symbol] = {
            'data': test_data,
            'fetch_time': current_time - 100  # 100 seconds ago
        }
        
        result = processor.get_cached_data(symbol)
        
        assert result == test_data
    
    def test_get_cached_data_expired(self, processor):
        """Test getting expired cached data."""
        symbol = 'BTCUSDT'
        test_data = {'symbol': symbol, 'ticker': {'last': 50000.0}}
        current_time = processor.timestamp_utility.get_utc_timestamp(as_ms=False)
        
        processor._market_data_cache[symbol] = {
            'data': test_data,
            'fetch_time': current_time - 400  # 400 seconds ago (expired)
        }
        
        result = processor.get_cached_data(symbol)
        
        assert result is None
        assert symbol not in processor._market_data_cache  # Should be removed
    
    def test_get_cached_data_not_exists(self, processor):
        """Test getting non-existent cached data."""
        result = processor.get_cached_data('NONEXISTENT')
        
        assert result is None
    
    def test_clear_cache_specific_symbol(self, processor):
        """Test clearing cache for specific symbol."""
        # Add test data to cache
        processor._market_data_cache['BTCUSDT'] = {'data': {}}
        processor._market_data_cache['ETHUSDT'] = {'data': {}}
        processor._ohlcv_cache['BTCUSDT'] = {'processed': {}}
        
        processor.clear_cache('BTCUSDT')
        
        assert 'BTCUSDT' not in processor._market_data_cache
        assert 'ETHUSDT' in processor._market_data_cache
        assert 'BTCUSDT' not in processor._ohlcv_cache
    
    def test_clear_cache_all(self, processor):
        """Test clearing all cache."""
        # Add test data to cache
        processor._market_data_cache['BTCUSDT'] = {'data': {}}
        processor._market_data_cache['ETHUSDT'] = {'data': {}}
        processor._ohlcv_cache['BTCUSDT'] = {'processed': {}}
        
        processor.clear_cache()
        
        assert len(processor._market_data_cache) == 0
        assert len(processor._ohlcv_cache) == 0
    
    def test_get_cache_stats(self, processor):
        """Test getting cache statistics."""
        symbol = 'BTCUSDT'
        current_time = processor.timestamp_utility.get_utc_timestamp(as_ms=False)
        
        processor._market_data_cache[symbol] = {
            'data': {},
            'fetch_time': current_time - 100,
            'fetch_time_formatted': 'Test Time'
        }
        
        stats = processor.get_cache_stats()
        
        assert stats['total_cached_symbols'] == 1
        assert stats['cache_ttl'] == 300
        assert symbol in stats['symbols']
        assert stats['symbols'][symbol]['age_seconds'] >= 100
        assert not stats['symbols'][symbol]['expired']


if __name__ == "__main__":
    pytest.main([__file__]) 