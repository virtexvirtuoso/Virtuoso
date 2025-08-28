"""
Conversion utilities for the monitoring system.

This module provides functions for converting between different units,
formats, and representations used in the monitoring system.
"""

from typing import Union, Optional, Dict, Any
import re


def ccxt_time_to_minutes(timeframe: str) -> int:
    """Convert CCXT timeframe string to minutes.
    
    This function converts standard CCXT timeframe strings (like '1m', '5m', '1h', '1d')
    to their equivalent in minutes. This is useful for calculations involving
    time periods and intervals.
    
    Args:
        timeframe: Timeframe string in CCXT format (e.g., '1m', '5m', '1h', '4h', '1d', '1w')
        
    Returns:
        Number of minutes in the timeframe
        
    Examples:
        >>> ccxt_time_to_minutes('1m')
        1
        >>> ccxt_time_to_minutes('1h')
        60
        >>> ccxt_time_to_minutes('1d')
        1440
        >>> ccxt_time_to_minutes('1w')
        10080
        
    Note:
        Returns 0 for invalid or empty timeframes to maintain backward compatibility.
    """
    if not timeframe:
        return 0
    
    # Extract unit (last character) and value
    unit = timeframe[-1].lower()
    
    # Extract numeric value (everything except last character)
    value_str = timeframe[:-1]
    
    # Handle case where timeframe is just a number (assume minutes)
    if not unit.isalpha():
        try:
            return int(timeframe)
        except (ValueError, TypeError):
            return 0
    
    # Parse the numeric value
    try:
        value = int(value_str) if value_str.isdigit() else 0
    except (ValueError, TypeError):
        return 0
    
    # Convert based on unit
    if unit == 'm':
        return value
    elif unit == 'h':
        return value * 60
    elif unit == 'd':
        return value * 1440  # 24 * 60
    elif unit == 'w':
        return value * 10080  # 7 * 24 * 60
    elif unit == 'M':  # Month (approximate as 30 days)
        return value * 43200  # 30 * 24 * 60
    elif unit == 'y':  # Year (approximate as 365 days)
        return value * 525600  # 365 * 24 * 60
    else:
        # Unknown unit, return 0 for backward compatibility
        return 0


def minutes_to_ccxt_time(minutes: int) -> str:
    """Convert minutes to CCXT timeframe string.
    
    This function converts a number of minutes to the most appropriate
    CCXT timeframe string representation.
    
    Args:
        minutes: Number of minutes
        
    Returns:
        CCXT timeframe string
        
    Examples:
        >>> minutes_to_ccxt_time(5)
        '5m'
        >>> minutes_to_ccxt_time(60)
        '1h'
        >>> minutes_to_ccxt_time(1440)
        '1d'
        >>> minutes_to_ccxt_time(240)
        '4h'
    """
    if minutes <= 0:
        return '1m'
    
    # Check for exact conversions first
    if minutes % 10080 == 0:  # Weeks
        weeks = minutes // 10080
        return f'{weeks}w'
    elif minutes % 1440 == 0:  # Days
        days = minutes // 1440
        return f'{days}d'
    elif minutes % 60 == 0:  # Hours
        hours = minutes // 60
        return f'{hours}h'
    else:
        return f'{minutes}m'


def parse_symbol_format(symbol: str) -> Dict[str, str]:
    """Parse different symbol formats into components.
    
    Handles various symbol formats like 'BTC/USDT', 'BTCUSDT', 'BTC-USDT', etc.
    
    Args:
        symbol: Trading pair symbol in various formats
        
    Returns:
        Dictionary with 'base', 'quote', and 'normalized' keys
        
    Examples:
        >>> parse_symbol_format('BTC/USDT')
        {'base': 'BTC', 'quote': 'USDT', 'normalized': 'BTC/USDT'}
        >>> parse_symbol_format('BTCUSDT')
        {'base': 'BTC', 'quote': 'USDT', 'normalized': 'BTC/USDT'}
        >>> parse_symbol_format('BTC-USDT')
        {'base': 'BTC', 'quote': 'USDT', 'normalized': 'BTC/USDT'}
    """
    # Handle common separators
    if '/' in symbol:
        parts = symbol.split('/')
        if len(parts) == 2:
            return {
                'base': parts[0].upper(),
                'quote': parts[1].upper(),
                'normalized': f"{parts[0].upper()}/{parts[1].upper()}"
            }
    elif '-' in symbol:
        parts = symbol.split('-')
        if len(parts) == 2:
            return {
                'base': parts[0].upper(),
                'quote': parts[1].upper(),
                'normalized': f"{parts[0].upper()}/{parts[1].upper()}"
            }
    elif ':' in symbol:
        # Handle perpetual format like 'BTCUSDT:USDT'
        main_part = symbol.split(':')[0]
        return parse_symbol_format(main_part)
    else:
        # Try to parse combined format (e.g., 'BTCUSDT')
        # Common quote currencies to check
        quote_currencies = ['USDT', 'USDC', 'USD', 'BUSD', 'EUR', 'GBP', 'BTC', 'ETH', 'BNB']
        
        symbol_upper = symbol.upper()
        for quote in quote_currencies:
            if symbol_upper.endswith(quote):
                base = symbol_upper[:-len(quote)]
                if base:  # Make sure base is not empty
                    return {
                        'base': base,
                        'quote': quote,
                        'normalized': f"{base}/{quote}"
                    }
    
    # If parsing fails, return the symbol as-is
    return {
        'base': symbol.upper(),
        'quote': '',
        'normalized': symbol.upper()
    }


def normalize_exchange_name(exchange: str) -> str:
    """Normalize exchange name to standard format.
    
    Args:
        exchange: Exchange name in various formats
        
    Returns:
        Normalized exchange name
        
    Examples:
        >>> normalize_exchange_name('BINANCE')
        'binance'
        >>> normalize_exchange_name('Bybit')
        'bybit'
        >>> normalize_exchange_name('okx')
        'okx'
    """
    # Remove common suffixes and normalize
    exchange_lower = exchange.lower()
    
    # Remove common suffixes
    suffixes_to_remove = ['spot', 'futures', 'swap', 'perp', 'perpetual', 'margin']
    for suffix in suffixes_to_remove:
        exchange_lower = exchange_lower.replace(suffix, '')
    
    # Remove special characters and spaces
    exchange_lower = re.sub(r'[^a-z0-9]', '', exchange_lower)
    
    # Map common variations to standard names
    exchange_map = {
        'binanceus': 'binance',
        'okex': 'okx',
        'huobipro': 'huobi',
        'gateio': 'gate',
        'kucoinspot': 'kucoin',
        'ftxus': 'ftx',
    }
    
    return exchange_map.get(exchange_lower, exchange_lower)


def convert_price_precision(
    price: float,
    precision: int = 8,
    round_mode: str = 'normal'
) -> float:
    """Convert price to specified precision.
    
    Args:
        price: Price value
        precision: Number of decimal places
        round_mode: Rounding mode ('normal', 'floor', 'ceil')
        
    Returns:
        Price with specified precision
        
    Examples:
        >>> convert_price_precision(1.23456789, 4)
        1.2346
        >>> convert_price_precision(1.23456789, 4, 'floor')
        1.2345
        >>> convert_price_precision(1.23456789, 4, 'ceil')
        1.2346
    """
    if round_mode == 'floor':
        import math
        multiplier = 10 ** precision
        return math.floor(price * multiplier) / multiplier
    elif round_mode == 'ceil':
        import math
        multiplier = 10 ** precision
        return math.ceil(price * multiplier) / multiplier
    else:
        return round(price, precision)


def bytes_to_human_readable(num_bytes: int) -> str:
    """Convert bytes to human-readable format.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Human-readable string (e.g., '1.5 MB', '2.3 GB')
        
    Examples:
        >>> bytes_to_human_readable(1024)
        '1.0 KB'
        >>> bytes_to_human_readable(1048576)
        '1.0 MB'
        >>> bytes_to_human_readable(1500000)
        '1.4 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change (e.g., 10.5 for 10.5% increase)
        
    Examples:
        >>> percentage_change(100, 110)
        10.0
        >>> percentage_change(100, 90)
        -10.0
        >>> percentage_change(0, 100)
        inf
    """
    if old_value == 0:
        return float('inf') if new_value > 0 else float('-inf') if new_value < 0 else 0
    
    return ((new_value - old_value) / abs(old_value)) * 100


def format_large_number(number: float, decimals: int = 2) -> str:
    """Format large numbers with K, M, B suffixes.
    
    Args:
        number: Number to format
        decimals: Number of decimal places
        
    Returns:
        Formatted string (e.g., '1.5K', '2.3M', '1.2B')
        
    Examples:
        >>> format_large_number(1500)
        '1.50K'
        >>> format_large_number(2300000)
        '2.30M'
        >>> format_large_number(1200000000)
        '1.20B'
    """
    abs_number = abs(number)
    sign = '-' if number < 0 else ''
    
    if abs_number < 1000:
        return f"{sign}{abs_number:.{decimals}f}"
    elif abs_number < 1000000:
        return f"{sign}{abs_number/1000:.{decimals}f}K"
    elif abs_number < 1000000000:
        return f"{sign}{abs_number/1000000:.{decimals}f}M"
    elif abs_number < 1000000000000:
        return f"{sign}{abs_number/1000000000:.{decimals}f}B"
    else:
        return f"{sign}{abs_number/1000000000000:.{decimals}f}T"


def convert_to_base_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates: Dict[str, float]
) -> Optional[float]:
    """Convert amount between currencies using exchange rates.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency
        to_currency: Target currency
        rates: Dictionary of exchange rates (currency -> USD rate)
        
    Returns:
        Converted amount or None if conversion not possible
        
    Examples:
        >>> rates = {'BTC': 50000, 'ETH': 3000, 'USD': 1}
        >>> convert_to_base_currency(1, 'BTC', 'USD', rates)
        50000.0
        >>> convert_to_base_currency(10, 'ETH', 'BTC', rates)
        0.6
    """
    if from_currency == to_currency:
        return amount
    
    # Convert to USD first (common base)
    if from_currency in rates and to_currency in rates:
        usd_amount = amount * rates.get(from_currency, 0)
        to_rate = rates.get(to_currency, 0)
        
        if to_rate > 0:
            return usd_amount / to_rate
    
    return None


def sanitize_json_value(value: Any) -> Any:
    """Sanitize a value for JSON serialization.
    
    Converts non-JSON-serializable types to JSON-compatible formats.
    
    Args:
        value: Value to sanitize
        
    Returns:
        JSON-serializable value
    """
    import decimal
    import datetime
    
    if isinstance(value, decimal.Decimal):
        return float(value)
    elif isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    elif hasattr(value, '__dict__'):
        return str(value)
    else:
        return value