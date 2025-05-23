"""Timestamp utility functions for market monitoring."""

from datetime import datetime, timezone
from typing import Union


class TimestampUtility:
    """Utility class for standardized timestamp handling."""
    
    @staticmethod
    def get_utc_timestamp(as_ms: bool = True) -> int:
        """Get current UTC timestamp.
        
        Args:
            as_ms: If True, return millisecond timestamp, else seconds
        
        Returns:
            Current UTC timestamp in milliseconds or seconds
        """
        ts = datetime.now(timezone.utc).timestamp()
        return int(ts * 1000) if as_ms else int(ts)
    
    @staticmethod
    def format_utc_time(timestamp_ms: int) -> str:
        """Format millisecond timestamp to human-readable UTC time.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            Formatted UTC time string
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
        """
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    
    @staticmethod
    def datetime_to_milliseconds(dt_object: datetime) -> int:
        """Convert datetime object to millisecond timestamp.
        
        Args:
            dt_object: datetime object
            
        Returns:
            Timestamp in milliseconds
        """
        return int(dt_object.timestamp() * 1000)
    
    @staticmethod
    def get_age_seconds(timestamp_ms: int) -> float:
        """Calculate age in seconds from a millisecond timestamp.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            Age in seconds
        """
        current_ms = TimestampUtility.get_utc_timestamp(as_ms=True)
        return (current_ms - timestamp_ms) / 1000
    
    @staticmethod
    def is_timestamp_fresh(timestamp_ms: int, max_age_seconds: float) -> bool:
        """Check if a timestamp is fresh within a maximum age.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            max_age_seconds: Maximum age in seconds
            
        Returns:
            True if timestamp is fresh, False otherwise
        """
        return TimestampUtility.get_age_seconds(timestamp_ms) <= max_age_seconds 