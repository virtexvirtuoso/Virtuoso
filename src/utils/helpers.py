# helpers.py    

import asyncio
import logging
import yaml
import aiohttp
import pandas as pd
import os
import json
from typing import Dict, Any, Optional, Union, Callable, List, Tuple
import numpy as np
import aiofiles
import functools
import time
import math

logger = logging.getLogger(__name__)

class AsyncRateLimiter:
    def __init__(self, limits: Dict[str, Dict[str, float]]):
        """
        Initialize an asynchronous rate limiter with category-based limits.

        Args:
            limits: Dict mapping categories to their limits, e.g.:
                {
                    'trades': {'requests_per_second': 10, 'burst_limit': 20},
                    'market_data': {'requests_per_second': 5, 'burst_limit': 10}
                }
        """
        self.limits = limits
        self.tokens = {category: config['burst_limit'] 
                      for category, config in limits.items()}
        self.last_update = {category: asyncio.get_event_loop().time() 
                           for category in limits}
        self.locks = {category: asyncio.Lock() 
                     for category in limits}
        
    async def acquire(self, category: str) -> bool:
        """Acquire a token for a specific category.
        
        Args:
            category: The rate limit category to use
            
        Returns:
            bool: True if token acquired, False if rate limited
            
        Raises:
            ValueError: If category doesn't exist
        """
        if category not in self.limits:
            raise ValueError(f"Unknown rate limit category: {category}")
            
        async with self.locks[category]:
            now = asyncio.get_event_loop().time()
            config = self.limits[category]
            elapsed = now - self.last_update[category]
            
            self.tokens[category] = min(
                config['burst_limit'],
                self.tokens[category] + elapsed * config['requests_per_second']
            )
            self.last_update[category] = now
            
            if self.tokens[category] >= 1:
                self.tokens[category] -= 1
                return True
                
            return False
            
    async def wait_for_token(self, category: str) -> None:
        """Wait until a token is available for a category.
        
        Args:
            category: The rate limit category to wait for
        """
        while not await self.acquire(category):
            await asyncio.sleep(0.1)  # Avoid tight loop
            
    @staticmethod
    def rate_limited(category: str):
        """Decorator for rate-limiting async functions by category.
        
        Args:
            category: The rate limit category to use
        """
        def decorator(func):
            async def wrapper(self, *args, **kwargs):
                if hasattr(self, 'rate_limiter'):
                    await self.rate_limiter.wait_for_token(category)
                return await func(self, *args, **kwargs)
            return wrapper
        return decorator

async def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file asynchronously."""
    try:
        async with aiofiles.open(config_path, 'r') as file:
            content = await file.read()
            return yaml.safe_load(content)
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

async def save_metadata(metadata: Dict[str, Any], metadata_path: str) -> None:
    """Save metadata to file asynchronously."""
    try:
        async with aiofiles.open(metadata_path, 'w') as f:
            await f.write(json.dumps(metadata, indent=4))
    except Exception as e:
        logger.error(f"Error saving metadata: {str(e)}")

async def send_discord_alert(webhook_url: str, message: str):
    """Send an alert message to a Discord webhook."""
    async with aiohttp.ClientSession() as session:
        payload = {'content': message}
        try:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status not in [200, 204]:
                    logger.error(f"Failed to send Discord alert. Status code: {resp.status}")
                else:
                    logger.debug("Discord alert sent successfully.")
        except Exception as e:
            logger.error(f"Exception while sending Discord alert: {e}")

def standardize_series(series: pd.Series, window: int = 20) -> pd.Series:
    """Standardize a pandas Series to a range from 1 to 100 using a rolling window."""
    if len(series) < window:
        window = len(series)
    rolling_min = series.rolling(window=window, min_periods=1).min()
    rolling_max = series.rolling(window=window, min_periods=1).max()
    denominator = rolling_max - rolling_min + 1e-9  # Avoid division by zero
    standardized = ((series - rolling_min) / denominator) * 100
    standardized = standardized.clip(1, 100)
    logger.debug(f"Standardized series with rolling window: {standardized.tail()}")
    return standardized

def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize a dictionary of weights to ensure they sum to 1.0."""
    if not weights:
        logger.warning("Empty weights dictionary provided")
        return {}
        
    total_weight = sum(weights.values())
    if total_weight == 0:
        logger.warning("Total weight is zero, cannot normalize")
        return weights
        
    try:
        normalized_weights = {key: value / total_weight for key, value in weights.items()}
        logger.debug(f"Normalized weights: {normalized_weights}")
        return normalized_weights
    except Exception as e:
        logger.error(f"Error normalizing weights: {e}")
        return weights

def export_dataframes(
    dataframes: Dict[str, pd.DataFrame],
    export_dir: str = "exports",
    identifier: str = None,
    categories: Dict[str, list] = None,
    enable_export: bool = True
) -> None:
    """
    Export DataFrames to CSV files with metadata.

    Args:
        dataframes (Dict[str, pd.DataFrame]): Dictionary of DataFrames to export.
        export_dir (str): Base export directory.
        identifier (str): Identifier for the export (e.g., symbol name).
        categories (Dict[str, list]): Categories for organizing exports.
        enable_export (bool): Toggle to enable/disable exports.
    """
    if not enable_export:
        logger.debug("Exports disabled, skipping DataFrame export.")
        return

    logger.info(f"Exporting DataFrames with identifier: {identifier}")
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    
    if identifier:
        export_dir = os.path.join(export_dir, identifier, timestamp)
    else:
        export_dir = os.path.join(export_dir, timestamp)
    
    if categories is None:
        categories = {
            'price_data': [
                'base_df',
                'htf_df',
                'mtf_df',
                'ltf_df'
            ],
            'market_data': [
                'orderbook_df',
                'trades_df',
                'tickers_df'
            ],
            'indicators': [
                'momentum_df',
                'volume_df',
                'orderflow_df',
                'position_df',
                'sentiment_df'
            ],
            'analysis': [
                'cvd_df',
                'vwap_df',
                'order_blocks_df'
            ],
            'metrics': [
                'funding_rate_df',
                'open_interest_df',
                'long_short_ratio_df'
            ]
        }

    for category, df_names in categories.items():
        category_dir = os.path.join(export_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        
        for df_name in df_names:
            df = dataframes.get(df_name)
            if df is not None and not df.empty:
                file_name = f"{df_name}.csv"
                file_path = os.path.join(category_dir, file_name)
                try:
                    # Handle special DataFrame serialization cases
                    df = df.copy()
                    
                    # Handle orderbook DataFrame
                    if df_name == "orderbook_df":
                        if 'bids' in df.columns:
                            df['bids'] = df['bids'].apply(lambda x: json.dumps(x))
                        if 'asks' in df.columns:
                            df['asks'] = df['asks'].apply(lambda x: json.dumps(x))
                    
                    # Handle order blocks DataFrame
                    if df_name == "order_blocks_df":
                        if 'blocks' in df.columns:
                            df['blocks'] = df['blocks'].apply(lambda x: json.dumps(x))

                    # Save metadata
                    metadata = {
                        'identifier': identifier,
                        'timestamp': timestamp,
                        'category': category,
                        'data_type': df_name,
                        'columns': list(df.columns),
                        'rows': len(df),
                        'timeframe': df.attrs.get('timeframe', 'N/A'),
                        'last_update': str(df.index[-1]) if isinstance(df.index, pd.DatetimeIndex) else None
                    }
                    
                    metadata_path = os.path.join(category_dir, f"{df_name}_metadata.json")
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=4)

                    # Save DataFrame
                    df.to_csv(file_path, index=True)
                    logger.debug(f"Exported {df_name} DataFrame to {file_path}")
                    
                except Exception as e:
                    logger.error(f"Error exporting {df_name} DataFrame: {e}", exc_info=True)
            else:
                logger.warning(f"{df_name} DataFrame is empty or None, skipping export.")

class TimeframeUtils:
    """Utility class for timeframe operations with proper configuration mapping."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with standardized timeframe config"""
        # Load timeframe intervals
        self.timeframe_minutes = {}
        for tf_name, tf_config in config['timeframes'].items():
            try:
                self.timeframe_minutes[tf_name] = int(tf_config['interval'])
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid interval for timeframe {tf_name}: {e}")
                continue
        
        # Load required points
        self.required_points = {}
        for tf_name, tf_config in config['timeframes'].items():
            try:
                self.required_points[tf_name] = int(tf_config.get('required', 200))
            except ValueError as e:
                logger.error(f"Invalid required points for timeframe {tf_name}: {e}")
                continue
        
        # Load timeframe weights
        self.timeframe_weights = {}
        for tf_name, tf_config in config['timeframes'].items():
            try:
                self.timeframe_weights[tf_name] = float(tf_config.get('weight', 0.25))
            except ValueError as e:
                logger.error(f"Invalid weight for timeframe {tf_name}: {e}")
                continue
        
        # Normalize weights to sum to 1.0
        weight_sum = sum(self.timeframe_weights.values())
        if not math.isclose(weight_sum, 1.0, rel_tol=1e-9):
            logger.warning(f"Timeframe weights sum to {weight_sum}, normalizing to 1.0")
            for tf in self.timeframe_weights:
                self.timeframe_weights[tf] /= weight_sum
    
    def get_complete_candles(self, df: pd.DataFrame, timeframe_type: str) -> pd.DataFrame:
        """Get only complete candles from the DataFrame for the specified timeframe."""
        if df.empty:
            return df
            
        minutes = self.timeframe_minutes.get(timeframe_type)
        if not minutes:
            logger.error(f"Invalid timeframe type: {timeframe_type}")
            return df
            
        if self.is_candle_closed(df.index[-1], minutes):
            return df
        return df.iloc[:-1]
    
    def validate_timeframe_data(self, price_data: Dict[str, pd.DataFrame]) -> bool:
        """Validate multi-timeframe price data structure and integrity."""
        try:
            # Check all timeframes exist
            if not all(tf in price_data for tf in self.timeframe_minutes.keys()):
                logger.error("Missing required timeframes")
                return False
            
            # Validate each timeframe's data
            for tf_name, df in price_data.items():
                if df.empty:
                    logger.error(f"Empty DataFrame for {tf_name}")
                    return False
                
                # Check minimum required points
                if len(df) < self.required_points[tf_name]:
                    logger.error(
                        f"Insufficient data points for {tf_name}. "
                        f"Got {len(df)}, need {self.required_points[tf_name]}"
                    )
                    return False
                    
                # Check DataFrame structure and ensure UTC timezone
                if not isinstance(df.index, pd.DatetimeIndex):
                    logger.error(f"Invalid index type for {tf_name}")
                    return False
                
                # Ensure timezone awareness
                if df.index.tz is None:
                    logger.warning(f"Converting naive timestamps to UTC for {tf_name}")
                    df.index = df.index.tz_localize('UTC')
                    
                # Verify required columns
                required_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover']
                if not all(col in df.columns for col in required_cols):
                    logger.error(f"Missing required columns in {tf_name}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating timeframe data: {e}")
            return False

    def is_candle_closed(self, timestamp: pd.Timestamp, timeframe_minutes: int) -> bool:
        """
        Check if a candle at the given timestamp is closed based on the timeframe.
        
        Args:
            timestamp: The timestamp to check
            timeframe_minutes: The timeframe in minutes
            
        Returns:
            bool: True if the candle is closed, False otherwise
        """
        current_time = pd.Timestamp.now(tz=timestamp.tz)
        candle_end = timestamp + pd.Timedelta(minutes=timeframe_minutes)
        return current_time >= candle_end

    def clear_cache(self):
        """Clear the cached candles."""
        self._last_candles.clear()
        self._partial_candles.clear()

    def get_cached_data(self) -> Dict[str, Any]:
        """Get the current cached data for debugging."""
        return {
            'last_candles': self._last_candles,
            'partial_candles': self._partial_candles
        }

def log_dataframe(self, df: pd.DataFrame, name: str, max_rows: int = 5) -> None:
        """
        Logs the DataFrame's structure and a preview of its contents.

        Args:
            df (pd.DataFrame): The DataFrame to log.
            name (str): A name identifier for the DataFrame.
            max_rows (int): Number of rows to display from head and tail.
        """
        if df.empty:
            logger.debug(f"{name} is empty.")
            return
        
        logger.debug(f"{name} shape: {df.shape}")
        logger.debug(f"{name} columns: {df.columns.tolist()}")
        logger.debug(f"{name} - Head:\n{df.head(max_rows)}")
        logger.debug(f"{name} - Tail:\n{df.tail(max_rows)}")

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        
    Returns:
        Decorated function that will retry on failure
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            retries = 0
            delay = base_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}")
                        raise
                        
                    # Calculate next delay with exponential backoff
                    delay = min(delay * 2, max_delay)
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"after {delay:.1f}s delay. Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
                    
        return wrapper
    return decorator

def format_timestamp(timestamp: Optional[int] = None) -> str:
    """Format timestamp into human readable string.
    
    Args:
        timestamp: Unix timestamp in milliseconds
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp / 1000))

def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(symbol, str):
        return False
    
    # Basic symbol validation (e.g., BTCUSDT)
    if len(symbol) < 5:  # Minimum length for valid symbol
        return False
        
    # Should contain only alphanumeric characters
    if not symbol.isalnum():
        return False
        
    return True

def calculate_interval_ms(interval: str) -> int:
    """Convert interval string to milliseconds.
    
    Args:
        interval: Interval string (e.g., '1m', '1h', '1d')
        
    Returns:
        int: Interval in milliseconds
    """
    multipliers = {
        'm': 60 * 1000,  # minutes
        'h': 60 * 60 * 1000,  # hours
        'd': 24 * 60 * 60 * 1000,  # days
        'w': 7 * 24 * 60 * 60 * 1000,  # weeks
        'M': 30 * 24 * 60 * 60 * 1000  # months (approximate)
    }
    
    if not interval:
        return 60 * 1000  # Default to 1 minute
        
    # Extract number and unit
    number = ''
    unit = interval[-1]
    
    for char in interval[:-1]:
        if char.isdigit():
            number += char
            
    if not number:
        number = '1'
        
    if unit not in multipliers:
        return 60 * 1000  # Default to 1 minute
        
    return int(number) * multipliers[unit]
