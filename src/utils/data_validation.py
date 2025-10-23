"""
Data validation utilities for multi-timeframe synchronization.

This module provides validation for multi-timeframe market data to ensure
temporal alignment and prevent score inversions during volatile markets.

Author: Virtuoso Trading System
Date: October 21, 2025
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Union
import logging
import pandas as pd

from src.monitoring.utils.timestamp import TimestampUtility

logger = logging.getLogger(__name__)


class TimestampValidator:
    """Validates timestamp synchronization for multi-timeframe data.

    This validator ensures that data from different timeframes (base, LTF, HTF)
    is temporally aligned within acceptable bounds. This prevents score inversions
    that can occur when aggregating stale data from slower timeframes with fresh
    data from faster timeframes during volatile markets.

    Example:
        >>> validator = TimestampValidator(max_delta_seconds=60)
        >>> market_data = {
        ...     'base': df_base,
        ...     'ltf': df_ltf,
        ...     'htf': df_htf
        ... }
        >>> is_valid, error = validator.validate_multi_timeframe_sync(market_data)
        >>> if not is_valid:
        ...     logger.warning(f"Data not synchronized: {error}")
    """

    def __init__(self, max_delta_seconds: int = 60, strict_mode: bool = False):
        """Initialize the timestamp validator.

        Args:
            max_delta_seconds: Maximum allowed time difference between timeframes (default: 60s).
                              In normal markets, 60s is acceptable. For HFT, use 1-5s.
            strict_mode: If True, validation failures cause exceptions.
                        If False (default), validation failures are logged as warnings.
        """
        self.max_delta_seconds = max_delta_seconds
        self.strict_mode = strict_mode
        self.logger = logger

        # Statistics for monitoring
        self.validation_count = 0
        self.failure_count = 0
        self.max_observed_delta = 0.0

    def validate_multi_timeframe_sync(
        self,
        market_data: Dict[str, Any],
        timeframes: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate that all timeframe data is from approximately the same time.

        This is the main validation method. It extracts timestamps from each timeframe
        and ensures they're within acceptable bounds.

        Args:
            market_data: Dictionary containing timeframe data
            timeframes: List of timeframe keys to validate (default: ['base', 'ltf', 'htf'])

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if all timestamps are within acceptable range
            - error_message: Description of validation failure, or None if valid

        Examples:
            >>> # Valid synchronized data
            >>> data = {
            ...     'base': {'timestamp': datetime.now()},
            ...     'ltf': {'timestamp': datetime.now()}
            ... }
            >>> is_valid, _ = validator.validate_multi_timeframe_sync(data)
            >>> assert is_valid

            >>> # Invalid unsynchronized data
            >>> old_time = datetime.now() - timedelta(minutes=5)
            >>> data = {
            ...     'base': {'timestamp': datetime.now()},
            ...     'htf': {'timestamp': old_time}
            ... }
            >>> is_valid, error = validator.validate_multi_timeframe_sync(data)
            >>> assert not is_valid
        """
        self.validation_count += 1

        if timeframes is None:
            timeframes = ['base', 'ltf', 'htf']

        # Extract timestamps from each timeframe
        timestamps = {}
        for tf in timeframes:
            if tf not in market_data:
                continue

            tf_data = market_data[tf]
            timestamp = self._extract_timestamp(tf_data, tf)

            if timestamp is None:
                self.logger.debug(f"No timestamp found for timeframe: {tf}")
                continue

            timestamps[tf] = timestamp

        # Need at least 2 timeframes to validate synchronization
        if len(timestamps) < 2:
            self.logger.debug(
                f"Insufficient timeframes for sync validation: {len(timestamps)} timeframe(s). "
                "At least 2 required. Passing through."
            )
            return True, None

        # Calculate time deltas
        timestamp_values = list(timestamps.values())
        min_time = min(timestamp_values)
        max_time = max(timestamp_values)
        delta_seconds = (max_time - min_time).total_seconds()

        # Update statistics
        if delta_seconds > self.max_observed_delta:
            self.max_observed_delta = delta_seconds

        # Check if delta exceeds threshold
        if delta_seconds > self.max_delta_seconds:
            self.failure_count += 1

            # Format timestamps for error message
            timestamp_strs = {
                k: v.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                for k, v in timestamps.items()
            }

            error_msg = (
                f"Timeframe data not synchronized: {delta_seconds:.1f}s delta "
                f"(max: {self.max_delta_seconds}s). "
                f"Timestamps: {', '.join(f'{k}={v}' for k, v in timestamp_strs.items())}"
            )

            if self.strict_mode:
                self.logger.error(error_msg)
            else:
                self.logger.warning(error_msg)

            return False, error_msg

        self.logger.debug(
            f"Timeframe sync validated: {delta_seconds:.1f}s delta "
            f"(max: {self.max_delta_seconds}s) across {len(timestamps)} timeframes"
        )
        return True, None

    def _extract_timestamp(
        self,
        data: Any,
        timeframe_name: str = "unknown"
    ) -> Optional[datetime]:
        """Extract timestamp from various data formats.

        Supports multiple data structures:
        - DataFrame with datetime index
        - Dictionary with timestamp/time/datetime fields
        - List/tuple with timestamp in last item
        - Raw timestamp (int/float/datetime)

        Args:
            data: Data that may contain timestamp
            timeframe_name: Name of timeframe for logging

        Returns:
            datetime object in UTC or None if not found
        """
        # Case 1: None or empty data
        if data is None:
            return None

        # Case 2: DataFrame with datetime index
        if isinstance(data, pd.DataFrame):
            if not data.empty and hasattr(data.index, 'max'):
                try:
                    latest_index = data.index.max()
                    if isinstance(latest_index, pd.Timestamp):
                        dt = latest_index.to_pydatetime()
                        # Ensure UTC timezone
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        self.logger.debug(
                            f"Extracted timestamp from DataFrame index ({timeframe_name}): {dt}"
                        )
                        return dt
                except Exception as e:
                    self.logger.debug(
                        f"Failed to extract timestamp from DataFrame index ({timeframe_name}): {e}"
                    )

        # Case 3: Dictionary with timestamp field
        if isinstance(data, dict):
            # Try common timestamp field names
            for key in ['timestamp', 'time', 'datetime', 'ts', 'date']:
                if key in data and data[key] is not None:
                    value = data[key]

                    # Sub-case: datetime object
                    if isinstance(value, datetime):
                        dt = value
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        self.logger.debug(
                            f"Extracted timestamp from dict['{key}'] ({timeframe_name}): {dt}"
                        )
                        return dt

                    # Sub-case: Unix timestamp (seconds or milliseconds)
                    elif isinstance(value, (int, float)):
                        # Heuristic: if > 1e10, assume milliseconds
                        if value > 1e10:
                            dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
                        else:
                            dt = datetime.fromtimestamp(value, tz=timezone.utc)
                        self.logger.debug(
                            f"Extracted timestamp from dict['{key}'] as Unix ({timeframe_name}): {dt}"
                        )
                        return dt

                    # Sub-case: ISO format string
                    elif isinstance(value, str):
                        try:
                            # Try parsing ISO format
                            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            self.logger.debug(
                                f"Extracted timestamp from dict['{key}'] as ISO ({timeframe_name}): {dt}"
                            )
                            return dt
                        except ValueError:
                            self.logger.debug(
                                f"Failed to parse timestamp string from dict['{key}'] ({timeframe_name}): {value}"
                            )

            # Try extracting from OHLCV data if present
            if 'ohlcv' in data and isinstance(data['ohlcv'], pd.DataFrame):
                return self._extract_timestamp(data['ohlcv'], f"{timeframe_name}.ohlcv")

            # Try extracting from nested data
            if 'data' in data:
                return self._extract_timestamp(data['data'], f"{timeframe_name}.data")

        # Case 4: List/array of data with timestamp field
        if isinstance(data, (list, tuple)) and len(data) > 0:
            # Get last item's timestamp (most recent)
            last_item = data[-1]
            if isinstance(last_item, dict):
                return self._extract_timestamp(last_item, f"{timeframe_name}[last]")

        # Case 5: Direct datetime object
        if isinstance(data, datetime):
            dt = data
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        # Case 6: Direct Unix timestamp
        if isinstance(data, (int, float)):
            if data > 1e10:
                return datetime.fromtimestamp(data / 1000, tz=timezone.utc)
            else:
                return datetime.fromtimestamp(data, tz=timezone.utc)

        return None

    def get_statistics(self) -> Dict[str, Union[int, float]]:
        """Get validation statistics for monitoring.

        Returns:
            Dictionary with validation metrics:
            - validation_count: Total validations performed
            - failure_count: Number of validation failures
            - failure_rate: Percentage of failures
            - max_observed_delta: Maximum observed time delta in seconds
            - max_allowed_delta: Configured maximum delta
        """
        failure_rate = (self.failure_count / self.validation_count * 100) if self.validation_count > 0 else 0.0

        return {
            'validation_count': self.validation_count,
            'failure_count': self.failure_count,
            'failure_rate': round(failure_rate, 2),
            'max_observed_delta_seconds': round(self.max_observed_delta, 2),
            'max_allowed_delta_seconds': self.max_delta_seconds
        }

    def reset_statistics(self):
        """Reset validation statistics."""
        self.validation_count = 0
        self.failure_count = 0
        self.max_observed_delta = 0.0


def validate_timeframe_alignment(
    market_data: Dict[str, Any],
    max_delta_seconds: int = 60,
    strict: bool = False
) -> Tuple[bool, Optional[str]]:
    """Convenience function for one-off timestamp validation.

    This is a simpler interface for cases where you don't need to maintain
    a validator instance.

    Args:
        market_data: Dictionary containing timeframe data
        max_delta_seconds: Maximum allowed time difference (default: 60s)
        strict: If True, raise exception on validation failure

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_timeframe_alignment(market_data)
        >>> if not is_valid:
        ...     logger.warning(f"Using base timeframe only: {error}")
    """
    validator = TimestampValidator(max_delta_seconds=max_delta_seconds, strict_mode=strict)
    return validator.validate_multi_timeframe_sync(market_data)
