"""
Cache Keys and TTL Configuration
"""

from enum import Enum


class CacheKeys:
    """Centralized cache key definitions."""

    # Confluence analysis cache keys
    CONFLUENCE_PREFIX = "confluence"
    CONFLUENCE_RESULT = "confluence:result:{symbol}"
    CONFLUENCE_SCORE = "confluence:score:{symbol}"
    # Add missing breakdown key helper used by services
    @staticmethod
    def confluence_breakdown(symbol: str) -> str:
        return f"confluence:breakdown:{symbol}"

    @staticmethod
    def confluence_score(symbol: str) -> str:
        return f"confluence:score:{symbol}"

    # Market data cache keys
    MARKET_PREFIX = "market"
    MARKET_DATA = "market:data:{symbol}:{timeframe}"
    MARKET_OVERVIEW = "market:overview"

    # Signal cache keys
    SIGNAL_PREFIX = "signal"
    SIGNAL_DATA = "signal:data:{symbol}"
    SIGNAL_HISTORY = "signal:history:{symbol}"

    # OHLCV cache keys
    OHLCV_PREFIX = "ohlcv"
    OHLCV_DATA = "ohlcv:data:{symbol}:{timeframe}"

    # Alert cache keys
    ALERT_PREFIX = "alert"
    ALERT_DATA = "alert:data:{symbol}"


class CacheTTL:
    """Cache TTL (Time To Live) configuration in seconds."""

    # Short-lived cache (real-time data)
    REALTIME = 5  # 5 seconds
    SHORT = 15  # 15 seconds

    # Medium-lived cache (frequently changing data)
    MEDIUM = 60  # 1 minute
    STANDARD = 300  # 5 minutes

    # Long-lived cache (stable data)
    LONG = 900  # 15 minutes
    EXTENDED = 3600  # 1 hour

    # Specific TTLs
    CONFLUENCE = 30  # 30 seconds for confluence analysis
    MARKET_DATA = 15  # 15 seconds for market data
    SIGNAL_DATA = 60  # 1 minute for signal data
    OHLCV_DATA = 30  # 30 seconds for OHLCV data
    ALERT_DATA = 300  # 5 minutes for alert data