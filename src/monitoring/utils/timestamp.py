"""
Timestamp utilities for the monitoring system.

This module provides standardized timestamp handling, conversion, and validation
utilities used throughout the monitoring system.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union


class TimestampUtility:
    """Utility class for standardized timestamp handling.
    
    This class provides static methods for timestamp conversion, formatting,
    and validation. All timestamps are handled in UTC to ensure consistency
    across the system.
    """
    
    @staticmethod
    def get_utc_timestamp(as_ms: bool = True) -> int:
        """Get current UTC timestamp.
        
        Args:
            as_ms: If True, return millisecond timestamp, else seconds
        
        Returns:
            Current UTC timestamp in milliseconds or seconds
        
        Examples:
            >>> # Get current timestamp in milliseconds
            >>> ts_ms = TimestampUtility.get_utc_timestamp()
            >>> 
            >>> # Get current timestamp in seconds
            >>> ts_sec = TimestampUtility.get_utc_timestamp(as_ms=False)
        """
        ts = datetime.now(timezone.utc).timestamp()
        return int(ts * 1000) if as_ms else int(ts)
    
    @staticmethod
    def format_utc_time(timestamp_ms: int) -> str:
        """Format millisecond timestamp to human-readable UTC time.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            Formatted UTC time string in format 'YYYY-MM-DD HH:MM:SS.mmm UTC'
            
        Examples:
            >>> ts = 1609459200000  # 2021-01-01 00:00:00 UTC
            >>> formatted = TimestampUtility.format_utc_time(ts)
            >>> print(formatted)  # '2021-01-01 00:00:00.000 UTC'
        """
        dt_object = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt_object.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + ' UTC'
    
    @staticmethod
    def milliseconds_to_datetime(timestamp_ms: int) -> datetime:
        """Convert millisecond timestamp to datetime object.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            datetime object in UTC timezone
            
        Examples:
            >>> ts = 1609459200000
            >>> dt = TimestampUtility.milliseconds_to_datetime(ts)
            >>> print(dt.year, dt.month, dt.day)  # 2021 1 1
        """
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    
    @staticmethod
    def datetime_to_milliseconds(dt_object: datetime) -> int:
        """Convert datetime object to millisecond timestamp.
        
        Args:
            dt_object: datetime object (will be converted to UTC if not already)
            
        Returns:
            Timestamp in milliseconds
            
        Examples:
            >>> dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            >>> ts = TimestampUtility.datetime_to_milliseconds(dt)
            >>> print(ts)  # 1609459200000
        """
        # Ensure datetime is timezone-aware
        if dt_object.tzinfo is None:
            # Assume UTC if no timezone is specified
            dt_object = dt_object.replace(tzinfo=timezone.utc)
        
        return int(dt_object.timestamp() * 1000)
    
    @staticmethod
    def get_age_seconds(timestamp_ms: int) -> float:
        """Calculate age in seconds from a millisecond timestamp.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            Age in seconds (how old the timestamp is)
            
        Examples:
            >>> # Check how old a timestamp is
            >>> old_ts = TimestampUtility.get_utc_timestamp() - 60000  # 1 minute ago
            >>> age = TimestampUtility.get_age_seconds(old_ts)
            >>> print(f"Timestamp is {age:.1f} seconds old")
        """
        current_ms = TimestampUtility.get_utc_timestamp(as_ms=True)
        return (current_ms - timestamp_ms) / 1000
    
    @staticmethod
    def is_timestamp_fresh(
        timestamp_ms: int,
        max_age_seconds: float,
        future_tolerance_seconds: float = 60
    ) -> bool:
        """Check if a timestamp is fresh within a maximum age.
        
        This method checks if a timestamp is within an acceptable age range,
        not too old and not too far in the future (which might indicate
        clock skew issues).
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            max_age_seconds: Maximum acceptable age in seconds
            future_tolerance_seconds: Maximum acceptable future timestamp in seconds
                                     (to handle minor clock skew)
            
        Returns:
            True if timestamp is fresh, False otherwise
            
        Examples:
            >>> current = TimestampUtility.get_utc_timestamp()
            >>> 
            >>> # Check if timestamp is less than 5 minutes old
            >>> is_fresh = TimestampUtility.is_timestamp_fresh(current, 300)
            >>> print(is_fresh)  # True
            >>> 
            >>> # Check old timestamp
            >>> old = current - 600000  # 10 minutes ago
            >>> is_fresh = TimestampUtility.is_timestamp_fresh(old, 300)
            >>> print(is_fresh)  # False
        """
        age = TimestampUtility.get_age_seconds(timestamp_ms)
        
        # Check if timestamp is not too old
        if age > max_age_seconds:
            return False
        
        # Check if timestamp is not too far in the future
        if age < -future_tolerance_seconds:
            return False
        
        return True
    
    @staticmethod
    def seconds_to_milliseconds(seconds: Union[int, float]) -> int:
        """Convert seconds to milliseconds.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Time in milliseconds
        """
        return int(seconds * 1000)
    
    @staticmethod
    def milliseconds_to_seconds(milliseconds: int) -> float:
        """Convert milliseconds to seconds.
        
        Args:
            milliseconds: Time in milliseconds
            
        Returns:
            Time in seconds
        """
        return milliseconds / 1000
    
    @staticmethod
    def get_time_until(target_timestamp_ms: int) -> float:
        """Calculate time until a target timestamp.
        
        Args:
            target_timestamp_ms: Target timestamp in milliseconds
            
        Returns:
            Time until target in seconds (negative if target is in the past)
        """
        current_ms = TimestampUtility.get_utc_timestamp(as_ms=True)
        return (target_timestamp_ms - current_ms) / 1000
    
    @staticmethod
    def add_seconds_to_timestamp(timestamp_ms: int, seconds: float) -> int:
        """Add seconds to a timestamp.
        
        Args:
            timestamp_ms: Base timestamp in milliseconds
            seconds: Number of seconds to add (can be negative)
            
        Returns:
            New timestamp in milliseconds
        """
        return timestamp_ms + int(seconds * 1000)
    
    @staticmethod
    def get_day_start_timestamp(timestamp_ms: Optional[int] = None) -> int:
        """Get the start of day timestamp (00:00:00 UTC).
        
        Args:
            timestamp_ms: Optional timestamp to get day start for.
                         If None, uses current time.
            
        Returns:
            Timestamp in milliseconds for start of day
        """
        if timestamp_ms is None:
            dt = datetime.now(timezone.utc)
        else:
            dt = TimestampUtility.milliseconds_to_datetime(timestamp_ms)
        
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return TimestampUtility.datetime_to_milliseconds(day_start)
    
    @staticmethod
    def get_hour_start_timestamp(timestamp_ms: Optional[int] = None) -> int:
        """Get the start of hour timestamp (XX:00:00 UTC).
        
        Args:
            timestamp_ms: Optional timestamp to get hour start for.
                         If None, uses current time.
            
        Returns:
            Timestamp in milliseconds for start of hour
        """
        if timestamp_ms is None:
            dt = datetime.now(timezone.utc)
        else:
            dt = TimestampUtility.milliseconds_to_datetime(timestamp_ms)
        
        hour_start = dt.replace(minute=0, second=0, microsecond=0)
        return TimestampUtility.datetime_to_milliseconds(hour_start)
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format a duration in seconds to human-readable string.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string (e.g., "2h 30m 15s", "45.2s", "123ms")
        """
        if seconds < 0:
            return f"-{TimestampUtility.format_duration(-seconds)}"
        
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        # Break down into components
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            if hours > 0 or minutes > 0:
                parts.append(f"{secs:.0f}s")
            else:
                parts.append(f"{secs:.1f}s")
        
        return " ".join(parts)
    
    @staticmethod
    def parse_timeframe_to_seconds(timeframe: str) -> int:
        """Parse a timeframe string to seconds.
        
        Supports formats like '1m', '5m', '1h', '4h', '1d', '1w'.
        
        Args:
            timeframe: Timeframe string
            
        Returns:
            Number of seconds in the timeframe
            
        Raises:
            ValueError: If timeframe format is invalid
        """
        if not timeframe or len(timeframe) < 2:
            raise ValueError(f"Invalid timeframe: {timeframe}")
        
        # Extract number and unit
        unit = timeframe[-1].lower()
        try:
            value = int(timeframe[:-1])
        except ValueError:
            raise ValueError(f"Invalid timeframe format: {timeframe}")
        
        # Convert to seconds based on unit
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400  # 24 * 3600
        elif unit == 'w':
            return value * 604800  # 7 * 24 * 3600
        else:
            raise ValueError(f"Unknown timeframe unit: {unit}")
    
    @staticmethod
    def get_aligned_timestamp(timestamp_ms: int, timeframe: str) -> int:
        """Get a timestamp aligned to the start of a timeframe period.
        
        For example, for a '5m' timeframe, returns the timestamp for the
        start of the 5-minute period containing the given timestamp.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            timeframe: Timeframe string (e.g., '1m', '5m', '1h')
            
        Returns:
            Aligned timestamp in milliseconds
        """
        period_seconds = TimestampUtility.parse_timeframe_to_seconds(timeframe)
        period_ms = period_seconds * 1000
        
        # Align to period boundary
        return (timestamp_ms // period_ms) * period_ms