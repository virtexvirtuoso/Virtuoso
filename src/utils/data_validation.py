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

    # Default timeframe-aware delta thresholds (in seconds)
    # HTF (4h candles) can naturally lag by up to 4 hours since they only close every 4h
    DEFAULT_TIMEFRAME_DELTAS = {
        'base': 120,      # 2 minutes - base should be fresh
        'ltf': 300,       # 5 minutes - LTF (e.g., 5m candles) can lag slightly
        'htf': 14400,     # 4 hours - HTF (e.g., 4h candles) only updates every 4h
    }

    def __init__(
        self,
        max_delta_seconds: int = 60,
        strict_mode: bool = False,
        timeframe_deltas: Optional[Dict[str, int]] = None
    ):
        """Initialize the timestamp validator.

        Args:
            max_delta_seconds: Default maximum allowed time difference between timeframes (default: 60s).
                              Used as fallback when timeframe-specific deltas aren't configured.
            strict_mode: If True, validation failures cause exceptions.
                        If False (default), validation failures are logged as warnings.
            timeframe_deltas: Optional dict mapping timeframe names to their max allowed delta in seconds.
                             Example: {'base': 120, 'ltf': 300, 'htf': 14400}
                             If not provided, uses DEFAULT_TIMEFRAME_DELTAS.
        """
        self.max_delta_seconds = max_delta_seconds
        self.strict_mode = strict_mode
        self.logger = logger

        # Use provided timeframe deltas or defaults
        self.timeframe_deltas = timeframe_deltas or self.DEFAULT_TIMEFRAME_DELTAS.copy()

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

        # Use base timeframe as the reference point (most recent)
        if 'base' in timestamps:
            reference_time = timestamps['base']
            reference_tf = 'base'
        else:
            # Fallback to most recent timestamp as reference
            reference_tf = max(timestamps, key=lambda k: timestamps[k])
            reference_time = timestamps[reference_tf]

        # Validate each timeframe against the reference using timeframe-specific thresholds
        violations = []
        max_delta_observed = 0.0

        for tf, ts in timestamps.items():
            if tf == reference_tf:
                continue

            delta_seconds = abs((reference_time - ts).total_seconds())

            # Update max observed
            if delta_seconds > max_delta_observed:
                max_delta_observed = delta_seconds

            # Get timeframe-specific threshold, fallback to global default
            max_allowed = self.timeframe_deltas.get(tf, self.max_delta_seconds)

            if delta_seconds > max_allowed:
                violations.append({
                    'timeframe': tf,
                    'delta': delta_seconds,
                    'max_allowed': max_allowed,
                    'timestamp': ts
                })

        # Update statistics
        if max_delta_observed > self.max_observed_delta:
            self.max_observed_delta = max_delta_observed

        # Check for violations
        if violations:
            self.failure_count += 1

            # Format error message with violation details
            timestamp_strs = {
                k: v.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                for k, v in timestamps.items()
            }

            violation_details = ', '.join(
                f"{v['timeframe']}={v['delta']:.0f}s (max:{v['max_allowed']}s)"
                for v in violations
            )

            error_msg = (
                f"Timeframe sync violations: {violation_details}. "
                f"Reference: {reference_tf}={timestamp_strs[reference_tf]}. "
                f"Timestamps: {', '.join(f'{k}={v}' for k, v in timestamp_strs.items())}"
            )

            if self.strict_mode:
                self.logger.error(error_msg)
            else:
                self.logger.warning(error_msg)

            return False, error_msg

        self.logger.debug(
            f"Timeframe sync validated: max_delta={max_delta_observed:.1f}s "
            f"across {len(timestamps)} timeframes (thresholds: {self.timeframe_deltas})"
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

    def get_statistics(self) -> Dict[str, Union[int, float, Dict]]:
        """Get validation statistics for monitoring.

        Returns:
            Dictionary with validation metrics:
            - validation_count: Total validations performed
            - failure_count: Number of validation failures
            - failure_rate: Percentage of failures
            - max_observed_delta: Maximum observed time delta in seconds
            - default_max_delta: Default maximum delta (fallback)
            - timeframe_deltas: Configured per-timeframe thresholds
        """
        failure_rate = (self.failure_count / self.validation_count * 100) if self.validation_count > 0 else 0.0

        return {
            'validation_count': self.validation_count,
            'failure_count': self.failure_count,
            'failure_rate': round(failure_rate, 2),
            'max_observed_delta_seconds': round(self.max_observed_delta, 2),
            'default_max_delta_seconds': self.max_delta_seconds,
            'timeframe_deltas': self.timeframe_deltas.copy()
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
