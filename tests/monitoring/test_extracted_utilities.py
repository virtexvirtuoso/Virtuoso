"""Tests for extracted monitoring utilities."""

import pytest
import pandas as pd
from datetime import datetime, timezone
import logging

from src.monitoring.utilities import TimestampUtility, ccxt_time_to_minutes, MarketDataValidator


class TestTimestampUtility:
    """Test TimestampUtility class."""
    
    def test_get_utc_timestamp_milliseconds(self):
        """Test getting UTC timestamp in milliseconds."""
        ts_ms = TimestampUtility.get_utc_timestamp(as_ms=True)
        assert isinstance(ts_ms, int)
        assert ts_ms > 1600000000000  # Should be after 2020
        
    def test_get_utc_timestamp_seconds(self):
        """Test getting UTC timestamp in seconds."""
        ts_s = TimestampUtility.get_utc_timestamp(as_ms=False)
        assert isinstance(ts_s, int)
        assert ts_s > 1600000000  # Should be after 2020
    
    def test_format_utc_time(self):
        """Test formatting UTC time."""
        timestamp_ms = 1609459200000  # 2021-01-01 00:00:00 UTC
        formatted = TimestampUtility.format_utc_time(timestamp_ms)
        assert "2021-01-01" in formatted
        assert "UTC" in formatted
    
    def test_timestamp_fresh(self):
        """Test checking if timestamp is fresh."""
        current_ts = TimestampUtility.get_utc_timestamp(as_ms=True)
        assert TimestampUtility.is_timestamp_fresh(current_ts, 60.0)  # Should be fresh
        assert not TimestampUtility.is_timestamp_fresh(current_ts - 120000, 60.0)  # 2 minutes old


class TestTimeUtils:
    """Test time utility functions."""
    
    def test_ccxt_time_to_minutes(self):
        """Test converting CCXT timeframes to minutes."""
        assert ccxt_time_to_minutes('1m') == 1
        assert ccxt_time_to_minutes('5m') == 5
        assert ccxt_time_to_minutes('1h') == 60
        assert ccxt_time_to_minutes('4h') == 240
        assert ccxt_time_to_minutes('1d') == 1440
        assert ccxt_time_to_minutes('1w') == 10080
        assert ccxt_time_to_minutes('') == 0
        assert ccxt_time_to_minutes('invalid') == 0


class TestMarketDataValidator:
    """Test MarketDataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return MarketDataValidator(logger=logging.getLogger(__name__))
    
    def test_valid_ohlcv_data(self, validator):
        """Test validation of valid OHLCV data."""
        # Create sample OHLCV DataFrame
        data = {
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [103.0, 104.0, 105.0],
            'volume': [1000, 1100, 1200]
        }
        df = pd.DataFrame(data)
        
        ohlcv_data = {'base': df}
        assert validator._validate_ohlcv(ohlcv_data)
    
    def test_invalid_ohlcv_data(self, validator):
        """Test validation of invalid OHLCV data."""
        # Test with high < low (invalid)
        data = {
            'open': [100.0],
            'high': [95.0],  # High < Low (invalid)
            'low': [105.0],
            'close': [103.0],
            'volume': [1000]
        }
        df = pd.DataFrame(data)
        
        ohlcv_data = {'base': df}
        assert not validator._validate_ohlcv(ohlcv_data)
    
    def test_valid_orderbook_data(self, validator):
        """Test validation of valid orderbook data."""
        orderbook_data = {
            'bids': [[100.0, 10], [99.0, 20], [98.0, 30]],
            'asks': [[101.0, 15], [102.0, 25], [103.0, 35]]
        }
        assert validator._validate_orderbook(orderbook_data)
    
    def test_crossed_orderbook_data(self, validator):
        """Test validation of crossed orderbook data."""
        orderbook_data = {
            'bids': [[102.0, 10]],  # Bid higher than ask (crossed market)
            'asks': [[101.0, 15]]
        }
        assert not validator._validate_orderbook(orderbook_data)
    
    def test_valid_ticker_data(self, validator):
        """Test validation of valid ticker data."""
        ticker_data = {
            'last': 100.0,
            'bid': 99.0,
            'ask': 101.0,
            'high': 105.0,
            'low': 95.0,
            'volume': 10000
        }
        assert validator._validate_ticker(ticker_data)
    
    def test_invalid_ticker_data(self, validator):
        """Test validation of invalid ticker data."""
        ticker_data = {
            'last': 100.0,
            'bid': 101.0,  # Bid higher than ask (crossed)
            'ask': 99.0,
            'high': 105.0,
            'low': 95.0,
            'volume': 10000
        }
        assert not validator._validate_ticker(ticker_data)


if __name__ == "__main__":
    pytest.main([__file__]) 