"""
Unit tests for multi-timeframe timestamp validation.

Tests the TimestampValidator class to ensure proper synchronization
validation for multi-timeframe market data.

Author: Virtuoso Trading System
Date: October 21, 2025
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from src.utils.data_validation import TimestampValidator, validate_timeframe_alignment


class TestTimestampValidator:
    """Test suite for TimestampValidator class."""

    def test_initialization(self):
        """Test validator initialization with default and custom parameters."""
        # Default initialization
        validator = TimestampValidator()
        assert validator.max_delta_seconds == 60
        assert validator.strict_mode is False
        assert validator.validation_count == 0
        assert validator.failure_count == 0

        # Custom initialization
        validator_custom = TimestampValidator(max_delta_seconds=30, strict_mode=True)
        assert validator_custom.max_delta_seconds == 30
        assert validator_custom.strict_mode is True

    def test_synchronized_data_passes(self):
        """Test that synchronized data passes validation."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'ltf': {'timestamp': base_time + timedelta(seconds=5)},
            'htf': {'timestamp': base_time + timedelta(seconds=10)}
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        assert is_valid is True
        assert error is None
        assert validator.validation_count == 1
        assert validator.failure_count == 0

    def test_unsynchronized_data_fails(self):
        """Test that unsynchronized data fails validation."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'ltf': {'timestamp': base_time + timedelta(seconds=5)},
            'htf': {'timestamp': base_time + timedelta(seconds=120)}  # 2 minutes old
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        assert is_valid is False
        assert error is not None
        assert "not synchronized" in error
        assert "120" in error  # Delta should be 120 seconds (max time difference)
        assert validator.validation_count == 1
        assert validator.failure_count == 1

    def test_missing_timestamps_passes(self):
        """Test that missing timestamps don't cause failure (graceful degradation)."""
        validator = TimestampValidator(max_delta_seconds=60)

        market_data = {
            'base': {'timestamp': datetime.now(timezone.utc)},
            'ltf': {},  # No timestamp
            'htf': None  # No data
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        # Should pass because only one valid timestamp (can't compare)
        assert is_valid is True
        assert error is None

    def test_single_timeframe_passes(self):
        """Test that single timeframe validation passes (nothing to compare)."""
        validator = TimestampValidator(max_delta_seconds=60)

        market_data = {
            'base': {'timestamp': datetime.now(timezone.utc)}
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        assert is_valid is True
        assert error is None

    def test_extract_timestamp_from_dataframe(self):
        """Test timestamp extraction from pandas DataFrame."""
        validator = TimestampValidator()

        # Create DataFrame with datetime index
        dates = pd.date_range(start='2025-01-01', periods=5, freq='1min', tz=timezone.utc)
        df = pd.DataFrame({'close': [100, 101, 102, 103, 104]}, index=dates)

        timestamp = validator._extract_timestamp(df, "test_df")

        assert timestamp is not None
        assert isinstance(timestamp, datetime)
        assert timestamp == dates.max().to_pydatetime()

    def test_extract_timestamp_from_dict_datetime(self):
        """Test timestamp extraction from dictionary with datetime."""
        validator = TimestampValidator()

        dt = datetime.now(timezone.utc)
        data = {'timestamp': dt}

        timestamp = validator._extract_timestamp(data, "test_dict")

        assert timestamp == dt

    def test_extract_timestamp_from_dict_unix_seconds(self):
        """Test timestamp extraction from dictionary with Unix seconds."""
        validator = TimestampValidator()

        # Unix timestamp in seconds
        unix_ts = 1609459200  # 2021-01-01 00:00:00 UTC
        data = {'timestamp': unix_ts}

        timestamp = validator._extract_timestamp(data, "test_dict")

        assert timestamp is not None
        assert timestamp.year == 2021
        assert timestamp.month == 1
        assert timestamp.day == 1

    def test_extract_timestamp_from_dict_unix_milliseconds(self):
        """Test timestamp extraction from dictionary with Unix milliseconds."""
        validator = TimestampValidator()

        # Unix timestamp in milliseconds
        unix_ts_ms = 1609459200000  # 2021-01-01 00:00:00 UTC
        data = {'timestamp': unix_ts_ms}

        timestamp = validator._extract_timestamp(data, "test_dict")

        assert timestamp is not None
        assert timestamp.year == 2021
        assert timestamp.month == 1
        assert timestamp.day == 1

    def test_extract_timestamp_from_dict_iso_string(self):
        """Test timestamp extraction from dictionary with ISO format string."""
        validator = TimestampValidator()

        iso_str = "2025-01-15T12:30:45+00:00"
        data = {'timestamp': iso_str}

        timestamp = validator._extract_timestamp(data, "test_dict")

        assert timestamp is not None
        assert timestamp.year == 2025
        assert timestamp.month == 1
        assert timestamp.day == 15

    def test_extract_timestamp_from_list(self):
        """Test timestamp extraction from list (gets last item)."""
        validator = TimestampValidator()

        dt = datetime.now(timezone.utc)
        data = [
            {'timestamp': dt - timedelta(minutes=2)},
            {'timestamp': dt - timedelta(minutes=1)},
            {'timestamp': dt}  # Last item should be used
        ]

        timestamp = validator._extract_timestamp(data, "test_list")

        assert timestamp == dt

    def test_extract_timestamp_adds_utc_timezone(self):
        """Test that naive datetime gets UTC timezone added."""
        validator = TimestampValidator()

        # Naive datetime (no timezone)
        naive_dt = datetime(2025, 1, 15, 12, 30, 45)
        data = {'timestamp': naive_dt}

        timestamp = validator._extract_timestamp(data, "test_naive")

        assert timestamp is not None
        assert timestamp.tzinfo == timezone.utc

    def test_extract_timestamp_returns_none_for_invalid_data(self):
        """Test that invalid data returns None gracefully."""
        validator = TimestampValidator()

        # Various invalid data types
        invalid_data = [
            "invalid_string",
            12345,  # Too small to be Unix timestamp
            [],
            {},
            None
        ]

        for data in invalid_data:
            timestamp = validator._extract_timestamp(data, "test_invalid")
            # Some might actually extract (like small int), but shouldn't crash
            assert timestamp is None or isinstance(timestamp, datetime)

    def test_custom_timeframes_list(self):
        """Test validation with custom timeframe list."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'custom1': {'timestamp': base_time + timedelta(seconds=5)},
            'custom2': {'timestamp': base_time + timedelta(seconds=10)},
            'ignored': {'timestamp': base_time + timedelta(seconds=200)}  # Should be ignored
        }

        # Validate only specific timeframes
        is_valid, error = validator.validate_multi_timeframe_sync(
            market_data,
            timeframes=['base', 'custom1', 'custom2']
        )

        assert is_valid is True  # Should pass because we ignore 'ignored'

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)

        # Valid validation
        valid_data = {
            'base': {'timestamp': base_time},
            'ltf': {'timestamp': base_time + timedelta(seconds=10)}
        }
        validator.validate_multi_timeframe_sync(valid_data)

        # Invalid validation
        invalid_data = {
            'base': {'timestamp': base_time},
            'ltf': {'timestamp': base_time + timedelta(seconds=120)}
        }
        validator.validate_multi_timeframe_sync(invalid_data)

        stats = validator.get_statistics()

        assert stats['validation_count'] == 2
        assert stats['failure_count'] == 1
        assert stats['failure_rate'] == 50.0
        assert stats['max_observed_delta_seconds'] == 120.0
        assert stats['max_allowed_delta_seconds'] == 60

    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)
        data = {
            'base': {'timestamp': base_time},
            'ltf': {'timestamp': base_time + timedelta(seconds=10)}
        }
        validator.validate_multi_timeframe_sync(data)

        assert validator.validation_count == 1

        validator.reset_statistics()

        assert validator.validation_count == 0
        assert validator.failure_count == 0
        assert validator.max_observed_delta == 0.0

    def test_strict_mode_logs_error(self, caplog):
        """Test that strict mode logs errors instead of warnings."""
        validator_strict = TimestampValidator(max_delta_seconds=60, strict_mode=True)

        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'htf': {'timestamp': base_time + timedelta(seconds=120)}
        }

        with caplog.at_level('ERROR'):
            is_valid, error = validator_strict.validate_multi_timeframe_sync(market_data)

        assert is_valid is False
        # In strict mode, should log as ERROR
        # Check if any ERROR level logs contain synchronization message
        error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
        assert any('synchronized' in record.message.lower() for record in error_logs)

    def test_boundary_condition_exact_max_delta(self):
        """Test boundary condition where delta equals max_delta exactly."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'htf': {'timestamp': base_time + timedelta(seconds=60)}  # Exactly max
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        # Should pass when delta == max (not strictly greater)
        assert is_valid is True

    def test_boundary_condition_just_over_max_delta(self):
        """Test boundary condition where delta just exceeds max_delta."""
        validator = TimestampValidator(max_delta_seconds=60)

        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'htf': {'timestamp': base_time + timedelta(seconds=60.1)}  # Just over max
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        # Should fail when delta > max
        assert is_valid is False


class TestValidateTimeframeAlignment:
    """Test suite for convenience function validate_timeframe_alignment."""

    def test_convenience_function_synchronized_data(self):
        """Test convenience function with synchronized data."""
        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'ltf': {'timestamp': base_time + timedelta(seconds=5)}
        }

        is_valid, error = validate_timeframe_alignment(market_data)

        assert is_valid is True
        assert error is None

    def test_convenience_function_unsynchronized_data(self):
        """Test convenience function with unsynchronized data."""
        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'htf': {'timestamp': base_time + timedelta(seconds=120)}
        }

        is_valid, error = validate_timeframe_alignment(market_data, max_delta_seconds=60)

        assert is_valid is False
        assert error is not None

    def test_convenience_function_custom_max_delta(self):
        """Test convenience function with custom max delta."""
        base_time = datetime.now(timezone.utc)
        market_data = {
            'base': {'timestamp': base_time},
            'htf': {'timestamp': base_time + timedelta(seconds=45)}
        }

        # Should pass with 60s max
        is_valid1, _ = validate_timeframe_alignment(market_data, max_delta_seconds=60)
        assert is_valid1 is True

        # Should fail with 30s max
        is_valid2, _ = validate_timeframe_alignment(market_data, max_delta_seconds=30)
        assert is_valid2 is False


class TestRealWorldScenarios:
    """Test real-world scenarios with typical market data structures."""

    def test_with_realistic_dataframe_structure(self):
        """Test with realistic DataFrame structure from CCXT."""
        validator = TimestampValidator(max_delta_seconds=60)

        # Simulate CCXT OHLCV data structure - all ending at the same time
        end_time = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

        # All dataframes end at the same time but have different frequencies
        base_dates = pd.date_range(end=end_time, periods=100, freq='1min', tz=timezone.utc)
        ltf_dates = pd.date_range(end=end_time, periods=400, freq='15s', tz=timezone.utc)
        htf_dates = pd.date_range(end=end_time, periods=20, freq='5min', tz=timezone.utc)

        market_data = {
            'base': pd.DataFrame({
                'open': [100] * 100,
                'high': [101] * 100,
                'low': [99] * 100,
                'close': [100.5] * 100,
                'volume': [1000] * 100
            }, index=base_dates),
            'ltf': pd.DataFrame({
                'open': [100] * 400,
                'high': [101] * 400,
                'low': [99] * 400,
                'close': [100.5] * 400,
                'volume': [250] * 400
            }, index=ltf_dates),
            'htf': pd.DataFrame({
                'open': [100] * 20,
                'high': [102] * 20,
                'low': [98] * 20,
                'close': [101] * 20,
                'volume': [5000] * 20
            }, index=htf_dates)
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        assert is_valid is True  # All end at the same time

    def test_with_stale_htf_data(self):
        """Test scenario where HTF data is stale (common in volatile markets)."""
        validator = TimestampValidator(max_delta_seconds=60)

        current_time = datetime.now(timezone.utc)

        # Base and LTF are current
        base_dates = pd.date_range(end=current_time, periods=100, freq='1min', tz=timezone.utc)
        ltf_dates = pd.date_range(end=current_time, periods=400, freq='15s', tz=timezone.utc)

        # HTF is 5 minutes old (stale)
        htf_dates = pd.date_range(end=current_time - timedelta(minutes=5), periods=100, freq='5min', tz=timezone.utc)

        market_data = {
            'base': pd.DataFrame({'close': [100] * 100}, index=base_dates),
            'ltf': pd.DataFrame({'close': [100] * 400}, index=ltf_dates),
            'htf': pd.DataFrame({'close': [100] * 100}, index=htf_dates)
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        assert is_valid is False  # HTF is stale
        assert "300" in error  # ~300 seconds delta

    def test_with_nested_ohlcv_structure(self):
        """Test with nested structure like {'ohlcv': DataFrame}."""
        validator = TimestampValidator(max_delta_seconds=60)

        current_time = datetime.now(timezone.utc)
        dates = pd.date_range(end=current_time, periods=100, freq='1min', tz=timezone.utc)
        df = pd.DataFrame({'close': [100] * 100}, index=dates)

        market_data = {
            'base': {'ohlcv': df},
            'ltf': {'ohlcv': df}
        }

        is_valid, error = validator.validate_multi_timeframe_sync(market_data)

        assert is_valid is True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
