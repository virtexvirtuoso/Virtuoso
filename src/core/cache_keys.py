"""
Cache Keys and TTL Configuration with Symbol Normalization

NAMING CONVENTION NOTE:
"Confluence" terminology is retained in cache keys for backward compatibility.
User-facing branding uses "Alpha Analysis" / "Alpha Score".

Legacy Name -> User-Facing Name:
- confluence:breakdown:{symbol} -> Alpha Analysis breakdown
- confluence:score:{symbol} -> Alpha Score
- confluence:result:{symbol} -> Alpha Analysis result

DO NOT rename cache keys - this would invalidate all cached data and require
cache migration. See docs/07-technical/CONFLUENCE_TO_ALPHA_MIGRATION_PLAN.md
"""

from enum import Enum
try:
    from .naming_mapper import normalize_symbol
except ImportError:
    # Fallback for standalone usage
    def normalize_symbol(symbol: str, target_format: str = 'exchange') -> str:
        return symbol.upper().replace('/', '') if target_format == 'exchange' else symbol


class CacheKeys:
    """Centralized cache key definitions."""

    # Confluence analysis cache keys
    CONFLUENCE_PREFIX = "confluence"
    CONFLUENCE_RESULT = "confluence:result:{symbol}"
    CONFLUENCE_SCORE = "confluence:score:{symbol}"
    # Add missing breakdown key helper used by services
    @staticmethod
    def confluence_breakdown(symbol: str) -> str:
        normalized_symbol = normalize_symbol(symbol, 'exchange')
        return f"confluence:breakdown:{normalized_symbol}"

    @staticmethod
    def confluence_score(symbol: str) -> str:
        normalized_symbol = normalize_symbol(symbol, 'exchange')
        return f"confluence:score:{normalized_symbol}"

    @staticmethod
    def market_data(symbol: str, timeframe: str) -> str:
        normalized_symbol = normalize_symbol(symbol, 'exchange')
        return f"market:data:{normalized_symbol}:{timeframe}"

    @staticmethod
    def signal_data(symbol: str) -> str:
        normalized_symbol = normalize_symbol(symbol, 'exchange')
        return f"signal:data:{normalized_symbol}"

    @staticmethod
    def ohlcv_data(symbol: str, timeframe: str) -> str:
        normalized_symbol = normalize_symbol(symbol, 'exchange')
        return f"ohlcv:data:{normalized_symbol}:{timeframe}"

    @staticmethod
    def alert_data(symbol: str) -> str:
        normalized_symbol = normalize_symbol(symbol, 'exchange')
        return f"alert:data:{normalized_symbol}"

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