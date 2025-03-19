"""Market data monitoring system.

This module provides monitoring functionality for market data:
- Performance monitoring
- Data quality monitoring
- System health monitoring
- Alert generation
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Callable, Union
import traceback
import signal
import sys
import functools
import psutil
import pandas as pd
import numpy as np
from src.indicators.orderflow_indicators import DataUnavailableError
from src.signal_generation.signal_generator import SignalGenerator
import tracemalloc
from collections import defaultdict
import datetime as dt  # Import datetime module separately for time
import copy  # For deep copying data structures

# Import matplotlib for visualization
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import io
import base64
from pathlib import Path

from src.core.validation import (
    ValidationService,
    AsyncValidationService,
    ValidationContext,
    ValidationResult,
    TimeRangeRule,
    SymbolRule
)
from src.core.error.models import ErrorContext, ErrorSeverity
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.alert_manager import AlertManager
from src.core.market.top_symbols import TopSymbolsManager
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.market.market_data_manager import MarketDataManager  # Import the new MarketDataManager
from src.monitoring.health_monitor import HealthMonitor
from src.core.exchanges.websocket_manager import WebSocketManager  # Import WebSocketManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

tracemalloc.start()

def ccxt_time_to_minutes(timeframe: str) -> int:
    """Convert CCXT timeframe string to minutes.
    
    Args:
        timeframe: Timeframe string (e.g., '1m', '5m', '1h', '1d')
        
    Returns:
        Number of minutes in the timeframe
    """
    if not timeframe:
        return 0
    
    unit = timeframe[-1]
    value = int(timeframe[:-1]) if timeframe[:-1].isdigit() else 0
    
    if unit == 'm':
        return value
    elif unit == 'h':
        return value * 60
    elif unit == 'd':
        return value * 1440  # 24 * 60
    elif unit == 'w':
        return value * 10080  # 7 * 24 * 60
    else:
        return int(timeframe) if timeframe.isdigit() else 0

def handle_monitoring_error(func: Callable) -> Callable:
    """Decorator to handle monitoring errors.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    return wrapper

class TimeRangeValidationRule:
    """Validation rule for checking time ranges."""
    
    def __init__(self, monitor):
        self.monitor = monitor
        self.name = "time_range"
        
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate time range for data.
        
        Args:
            data: Data dictionary containing timestamp
            
        Returns:
            bool: True if time range is valid
        """
        try:
            timestamp = data.get('timestamp')
            if not timestamp:
                return False
                
            # Convert timestamp to datetime if needed
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp)
                
            # Get current time
            now = datetime.now()
            
            # Check if timestamp is within acceptable range
            max_age = timedelta(hours=24)  # Max 24 hours old
            min_time = now - max_age
            
            return min_time <= timestamp <= now
            
        except Exception as e:
            self.monitor.logger.error(f"Error validating time range: {str(e)}")
            return False

class MarketDataValidator:
    """Comprehensive validation system for market data."""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Define validation rules for different data types
        self.validation_rules = {
            'ohlcv': self._validate_ohlcv,
            'orderbook': self._validate_orderbook,
            'trades': self._validate_trades,
            'ticker': self._validate_ticker,
            'funding': self._validate_funding
        }
        
        # Track validation statistics
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'warnings': 0,
            'data_types': {}
        }
    
    def validate_market_data(self, market_data):
        """Comprehensive validation of entire market data."""
        self.logger.debug("\n=== Starting comprehensive market data validation ===")
        
        # Increment total validations
        self.validation_stats['total_validations'] += 1
        
        # Check if market_data is a dictionary
        if not isinstance(market_data, dict):
            self.logger.error(f"Market data must be a dictionary, got {type(market_data)}")
            self.validation_stats['failed_validations'] += 1
            return False
        
        # Check for required base fields
        required_fields = ['symbol', 'timestamp']
        missing_fields = [field for field in required_fields if field not in market_data]
        if missing_fields:
            self.logger.error(f"Missing required fields in market data: {missing_fields}")
            self.validation_stats['failed_validations'] += 1
            return False
        
        # Check each data type using appropriate validator
        validation_results = {}
        overall_result = True
        
        for data_type, validator in self.validation_rules.items():
            if data_type in market_data:
                # Initialize stats tracking for this data type if needed
                if data_type not in self.validation_stats['data_types']:
                    self.validation_stats['data_types'][data_type] = {
                        'validations': 0,
                        'passes': 0,
                        'failures': 0
                    }
                
                self.validation_stats['data_types'][data_type]['validations'] += 1
                
                # Run validation
                result = validator(market_data[data_type])
                validation_results[data_type] = result
                
                # Update stats
                if result:
                    self.validation_stats['data_types'][data_type]['passes'] += 1
                else:
                    self.validation_stats['data_types'][data_type]['failures'] += 1
                    overall_result = False
        
        # Update overall stats
        if overall_result:
            self.validation_stats['passed_validations'] += 1
        else:
            self.validation_stats['failed_validations'] += 1
            
        self.logger.debug(f"Validation results: {validation_results}")
        self.logger.debug(f"Overall validation result: {'PASS' if overall_result else 'FAIL'}")
        
        return overall_result
    
    def _validate_ohlcv(self, ohlcv_data):
        """Validate OHLCV data for all timeframes."""
        if not isinstance(ohlcv_data, dict):
            self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv_data)}")
            return False
        
        # Required timeframes
        required_timeframes = ['base', 'ltf', 'mtf', 'htf']
        available_timeframes = set(ohlcv_data.keys())
        missing_timeframes = set(required_timeframes) - available_timeframes
        
        if missing_timeframes:
            self.logger.warning(f"Missing timeframes in OHLCV data: {missing_timeframes}")
            # We can still validate with some missing timeframes, but at least one should be present
            if len(available_timeframes) == 0:
                self.logger.error("No timeframes available in OHLCV data")
                return False
        
        # Validate each timeframe
        valid_timeframes = 0
        for timeframe, data in ohlcv_data.items():
            if isinstance(data, pd.DataFrame):
                if data.empty:
                    self.logger.warning(f"Empty DataFrame for timeframe {timeframe}")
                    continue
                
                # Check required columns
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in data.columns]
                
                if missing_columns:
                    self.logger.warning(f"Timeframe {timeframe} missing columns: {missing_columns}")
                    continue
                
                # Check for NaN values
                nan_counts = data.isna().sum()
                if nan_counts.sum() > 0:
                    self.logger.warning(f"NaN values found in timeframe {timeframe}: {nan_counts}")
                
                # Check that high >= low
                invalid_hl = data[data['high'] < data['low']]
                if not invalid_hl.empty:
                    self.logger.error(f"Found {len(invalid_hl)} candles where high < low in {timeframe}")
                    return False
                
                # Check that high >= open and high >= close
                invalid_ho = data[data['high'] < data['open']]
                invalid_hc = data[data['high'] < data['close']]
                if not invalid_ho.empty or not invalid_hc.empty:
                    self.logger.error(f"Found candles with invalid high values in {timeframe}")
                    return False
                
                # Check that low <= open and low <= close
                invalid_lo = data[data['low'] > data['open']]
                invalid_lc = data[data['low'] > data['close']]
                if not invalid_lo.empty or not invalid_lc.empty:
                    self.logger.error(f"Found candles with invalid low values in {timeframe}")
                    return False
                
                # Check for negative values
                negative_values = data[(data[['open', 'high', 'low', 'close', 'volume']] < 0).any(axis=1)]
                if not negative_values.empty:
                    self.logger.error(f"Found {len(negative_values)} candles with negative values in {timeframe}")
                    return False
                
                # Check for chronological order and duplicates
                if data.index.name == 'timestamp' and isinstance(data.index, pd.DatetimeIndex):
                    if not data.index.is_monotonic_increasing:
                        self.logger.error(f"Timestamps in {timeframe} are not in chronological order")
                        return False
                    
                    if len(data.index) != len(data.index.unique()):
                        self.logger.error(f"Duplicate timestamps found in {timeframe}")
                        return False
                
                # Mark this timeframe as valid
                valid_timeframes += 1
        
        # Return True if at least one timeframe is valid
        if valid_timeframes > 0:
            self.logger.debug(f"OHLCV validation passed with {valid_timeframes} valid timeframes")
            return True
        
        self.logger.error("No valid timeframes found in OHLCV data")
        return False
    
    def _validate_orderbook(self, orderbook_data):
        """Validate orderbook data."""
        # Handle nested orderbook structure
        if isinstance(orderbook_data, dict):
            # Check for the Bybit structure with result containing 'b' and 'a'
            if 'result' in orderbook_data and isinstance(orderbook_data['result'], dict):
                result_data = orderbook_data['result']
                if 'b' in result_data and 'a' in result_data:
                    # Extract bids and asks from the result structure
                    orderbook_data = {
                        'bids': result_data.get('b', []),
                        'asks': result_data.get('a', [])
                    }
        
        if not isinstance(orderbook_data, dict):
            self.logger.error(f"Orderbook data must be a dictionary, got {type(orderbook_data)}")
            return False
        
        # Check for required fields
        required_fields = ['bids', 'asks']
        missing_fields = [field for field in required_fields if field not in orderbook_data]
        if missing_fields:
            self.logger.error(f"Missing required fields in orderbook data: {missing_fields}")
            self.logger.debug(f"Orderbook keys: {list(orderbook_data.keys())}")
            return False
        
        # Check that bids and asks are lists
        if not isinstance(orderbook_data['bids'], list) or not isinstance(orderbook_data['asks'], list):
            self.logger.error("Bids and asks must be lists")
            self.logger.debug(f"Bids type: {type(orderbook_data['bids'])}, Asks type: {type(orderbook_data['asks'])}")
            return False
        
        # Check that bids and asks are not empty
        if len(orderbook_data['bids']) == 0 and len(orderbook_data['asks']) == 0:
            self.logger.warning("Both bids and asks are empty in orderbook")
            return False
        
        # Check format of bids and asks
        if orderbook_data['bids']:
            if not all(isinstance(bid, list) and len(bid) >= 2 for bid in orderbook_data['bids']):
                self.logger.error("Invalid bid format in orderbook")
                return False
        
        if orderbook_data['asks']:
            if not all(isinstance(ask, list) and len(ask) >= 2 for ask in orderbook_data['asks']):
                self.logger.error("Invalid ask format in orderbook")
                return False
        
        # Check that bids are in descending order (highest to lowest)
        if len(orderbook_data['bids']) > 1:
            for i in range(len(orderbook_data['bids']) - 1):
                if orderbook_data['bids'][i][0] < orderbook_data['bids'][i+1][0]:
                    self.logger.error("Bids are not in descending order")
                    return False
        
        # Check that asks are in ascending order (lowest to highest)
        if len(orderbook_data['asks']) > 1:
            for i in range(len(orderbook_data['asks']) - 1):
                if orderbook_data['asks'][i][0] > orderbook_data['asks'][i+1][0]:
                    self.logger.error("Asks are not in ascending order")
                    return False
        
        # Check for crossed book (highest bid > lowest ask)
        if orderbook_data['bids'] and orderbook_data['asks']:
            highest_bid = orderbook_data['bids'][0][0]
            lowest_ask = orderbook_data['asks'][0][0]
            if highest_bid >= lowest_ask:
                self.logger.error(f"Crossed orderbook detected: highest bid {highest_bid} >= lowest ask {lowest_ask}")
                return False
        
        self.logger.debug("Orderbook validation passed")
        return True
    
    def _validate_trades(self, trades_data):
        """Validate trades data."""
        # Handle common case where trades data is nested
        self.logger.debug("=== TRADES VALIDATION DEBUG ===")
        self.logger.debug(f"Trades data type: {type(trades_data)}")
        
        if isinstance(trades_data, dict):
            # Try to extract trades list from common nested structures
            self.logger.debug(f"Trades data keys: {list(trades_data.keys())}")
            
            if 'result' in trades_data and isinstance(trades_data['result'], dict) and 'list' in trades_data['result']:
                self.logger.debug("Found trades in result.list structure")
                trades_data = trades_data['result']['list']
            elif 'list' in trades_data:
                self.logger.debug("Found trades in list structure")
                trades_data = trades_data['list']
            elif 'result' in trades_data and isinstance(trades_data['result'], list):
                # Sometimes result itself might be the list
                self.logger.debug("Found trades in result structure")
                trades_data = trades_data['result']
        
        if not isinstance(trades_data, (list, pd.DataFrame)):
            self.logger.error(f"Trades data must be a list or DataFrame, got {type(trades_data)}")
            self.logger.debug(f"Trades data keys: {list(trades_data.keys()) if isinstance(trades_data, dict) else 'N/A'}")
            self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
            return False
        
        # If it's a DataFrame, check it's not empty
        if isinstance(trades_data, pd.DataFrame):
            if trades_data.empty:
                self.logger.warning("Trades DataFrame is empty")
                self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                return True  # Empty trades data is technically valid
            
            # Check required columns - look for either amount or size field
            required_columns = ['timestamp', 'price']
            size_field_options = ['amount', 'size', 'quantity', 'qty']
            
            # Check if at least one size field option exists
            has_size_field = any(field in trades_data.columns for field in size_field_options)
            
            missing_columns = [col for col in required_columns if col not in trades_data.columns]
            if missing_columns or not has_size_field:
                missing_str = ", ".join(missing_columns)
                size_msg = "no size field (need one of: amount, size, quantity, qty)" if not has_size_field else ""
                self.logger.warning(f"Trades DataFrame missing columns: {missing_str} {size_msg}")
            
            # Check for negative prices or amounts
            if 'price' in trades_data.columns:
                neg_prices = trades_data[trades_data['price'] <= 0]
                if not neg_prices.empty:
                    self.logger.error(f"Found {len(neg_prices)} trades with negative/zero prices")
                    self.logger.debug(f"Sample negative price trade: {neg_prices.iloc[0].to_dict()}")
            
            # Check any available size field
            for size_field in size_field_options:
                if size_field in trades_data.columns:
                    neg_amounts = trades_data[trades_data[size_field] <= 0]
                    if not neg_amounts.empty:
                        self.logger.error(f"Found {len(neg_amounts)} trades with negative/zero {size_field}")
                        self.logger.debug(f"Sample negative {size_field} trade: {neg_amounts.iloc[0].to_dict()}")
                    break
            
            # Check timestamp order if available
            if 'timestamp' in trades_data.columns and trades_data['timestamp'].is_monotonic_decreasing:
                self.logger.warning("Trades are not in chronological order (newest first)")
            
            self.logger.debug(f"Trades validation passed with {len(trades_data)} trades")
            self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
            return True
        
        # If it's a list, check it's not empty
        if len(trades_data) == 0:
            self.logger.warning("Trades list is empty")
            self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
            return True  # Empty trades data is technically valid
        
        # Log some info about the trades list
        self.logger.debug(f"Trades list contains {len(trades_data)} trades")
        if trades_data:
            self.logger.debug(f"First trade type: {type(trades_data[0])}")
            if isinstance(trades_data[0], dict):
                self.logger.debug(f"First trade keys: {list(trades_data[0].keys())}")
                self.logger.debug(f"First trade values: {trades_data[0]}")
        
        # Check each trade
        for i, trade in enumerate(trades_data[:100]):  # Check at most 100 trades
            if not isinstance(trade, dict):
                self.logger.error(f"Trade at index {i} is not a dictionary, type: {type(trade)}")
                self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                return False
            
            # Check for price field
            if 'price' not in trade:
                self.logger.error(f"Trade at index {i} missing price field")
                self.logger.debug(f"Trade keys: {list(trade.keys())}")
                self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                return False
            
            # Check for amount/quantity/size field (different exchanges use different names)
            size_field = None
            for field in ['amount', 'size', 'quantity', 'qty']:
                if field in trade:
                    size_field = field
                    break
                    
            if not size_field:
                self.logger.error(f"Trade at index {i} missing size field (looked for: amount, size, quantity, qty)")
                self.logger.debug(f"Trade keys: {list(trade.keys())}")
                self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                return False
            
            # Check for positive price
            price = trade['price']
            # Only log if there's an issue
            try:
                price_value = float(price) if isinstance(price, str) else price
                if price_value <= 0:
                    self.logger.error(f"Trade at index {i} has invalid price: {price} (converted to {price_value})")
                    self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                    return False
            except (ValueError, TypeError) as e:
                self.logger.error(f"Error converting price {price} to float: {str(e)}")
                self.logger.debug(f"Price validation failed for trade {i}: price={price} (type: {type(price)})")
                self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                return False
            
            # Check for positive amount/size
            amount = trade[size_field]
            # Only log if there's an issue
            try:
                amount_value = float(amount) if isinstance(amount, str) else amount
                if amount_value <= 0:
                    self.logger.error(f"Trade at index {i} has invalid {size_field}: {amount} (converted to {amount_value})")
                    self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                    return False
            except (ValueError, TypeError) as e:
                self.logger.error(f"Error converting {size_field} {amount} to float: {str(e)}")
                self.logger.debug(f"Size validation failed for trade {i}: {size_field}={amount} (type: {type(amount)})")
                self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
                return False
        
        self.logger.debug(f"Trades validation passed with {len(trades_data)} trades")
        self.logger.debug("=== END TRADES VALIDATION DEBUG ===")
        return True
    
    def _validate_ticker(self, ticker_data):
        """Validate ticker data."""
        if not isinstance(ticker_data, dict):
            self.logger.error(f"Ticker data must be a dictionary, got {type(ticker_data)}")
            return False
        
        # Check for critical fields
        critical_fields = ['last']
        missing_critical = [field for field in critical_fields if field not in ticker_data]
        if missing_critical:
            self.logger.error(f"Missing critical fields in ticker data: {missing_critical}")
            return False
        
        # Check for recommended fields
        recommended_fields = ['bid', 'ask', 'high', 'low', 'volume']
        missing_recommended = [field for field in recommended_fields if field not in ticker_data]
        if missing_recommended:
            self.logger.warning(f"Missing recommended fields in ticker data: {missing_recommended}")
        
        # Check that numeric fields have valid values
        numeric_fields = ['last', 'bid', 'ask', 'high', 'low', 'volume']
        for field in numeric_fields:
            if field in ticker_data and ticker_data[field] is not None:
                if not isinstance(ticker_data[field], (int, float)):
                    self.logger.error(f"Ticker field {field} is not numeric: {ticker_data[field]}")
                    return False
                
                if field != 'change24h' and ticker_data[field] <= 0:
                    self.logger.error(f"Ticker field {field} has invalid value: {ticker_data[field]}")
                    return False
        
        # Check for crossed values
        if 'bid' in ticker_data and 'ask' in ticker_data:
            if ticker_data['bid'] is not None and ticker_data['ask'] is not None:
                if ticker_data['bid'] >= ticker_data['ask']:
                    self.logger.error(f"Crossed ticker values: bid ({ticker_data['bid']}) >= ask ({ticker_data['ask']})")
                    return False
        
        # Check high/low consistency
        if 'high' in ticker_data and 'low' in ticker_data:
            if ticker_data['high'] is not None and ticker_data['low'] is not None:
                if ticker_data['high'] < ticker_data['low']:
                    self.logger.error(f"Invalid ticker values: high ({ticker_data['high']}) < low ({ticker_data['low']})")
                    return False
        
        self.logger.debug("Ticker validation passed")
        return True
    
    def _validate_funding(self, funding_data):
        """Validate funding rate data."""
        if not isinstance(funding_data, dict):
            self.logger.error(f"Funding data must be a dictionary, got {type(funding_data)}")
            return False
        
        # Check for required fields
        required_fields = ['fundingRate']
        missing_fields = [field for field in required_fields if field not in funding_data]
        if missing_fields:
            self.logger.warning(f"Missing fields in funding data: {missing_fields}")
            # Not critical, could still be valid
        
        # Check that funding rate is within reasonable bounds (typically -1% to 1% for most exchanges)
        if 'fundingRate' in funding_data:
            funding_rate = funding_data['fundingRate']
            if not isinstance(funding_rate, (int, float)):
                self.logger.error(f"Funding rate is not numeric: {funding_rate}")
                return False
            
            # Check for extreme values
            if abs(funding_rate) > 0.05:  # 5% threshold
                self.logger.warning(f"Extreme funding rate detected: {funding_rate}")
        
        # Check nextFundingTime is in the future
        if 'nextFundingTime' in funding_data:
            next_time = funding_data['nextFundingTime']
            if isinstance(next_time, (int, float)):
                current_time = int(time.time() * 1000) if next_time > 1000000000000 else int(time.time())
                if next_time < current_time:
                    self.logger.warning("Next funding time is in the past")
        
        self.logger.debug("Funding data validation passed")
        return True
    
    def get_validation_stats(self):
        """Get validation statistics."""
        return self.validation_stats

class LoggingUtility:
    """Centralized logging utility to standardize and consolidate logging operations."""
    
    def __init__(self, logger):
        """Initialize the logging utility.
        
        Args:
            logger: Logger instance to use for logging
        """
        self.logger = logger
    
    def log_raw_response(self, data_type: str, symbol: str, data: Any) -> None:
        """Log raw API responses with detailed structure analysis.
        
        Args:
            data_type: Type of data (OHLCV, Orderbook, Trades)
            symbol: Symbol being processed
            data: Raw response data
        """
        try:
            self.logger.debug(f"\n=== Raw {data_type} Response for {symbol} ===")
            
            # Handle different data types appropriately
            if data_type == 'OHLCV':
                self._log_ohlcv_data(data)
            elif data_type == 'Orderbook':
                self._log_orderbook_data(data)
            elif data_type == 'Trades':
                self._log_trades_data(data)
            else:
                # Generic logging for other data types
                if isinstance(data, dict):
                    self.logger.debug(f"Dictionary with {len(data)} keys: {list(data.keys())}")
                    for key in list(data.keys())[:5]:  # Show first 5 keys
                        value = data[key]
                        self.logger.debug(f"  {key}: {type(value)} {self._format_sample(value)}")
                elif isinstance(data, list):
                    self.logger.debug(f"List with {len(data)} items")
                    for i, item in enumerate(data[:3]):  # Show first 3 items
                        self.logger.debug(f"  [{i}]: {type(item)} {self._format_sample(item)}")
                elif isinstance(data, pd.DataFrame):
                    self.logger.debug(f"DataFrame with shape {data.shape}")
                    self.logger.debug(f"Columns: {list(data.columns)}")
                    if not data.empty:
                        self.logger.debug(f"Sample:\n{data.head(2)}")
                else:
                    self.logger.debug(f"Type: {type(data)}")
                    self.logger.debug(f"Value: {self._format_sample(data)}")
            
            self.logger.debug(f"=== End Raw {data_type} Response ===\n")
        except Exception as e:
            self.logger.warning(f"Error logging raw {data_type} response: {str(e)}")
    
    def _log_ohlcv_data(self, data: Any) -> None:
        """Log OHLCV data with detailed analysis."""
        if isinstance(data, dict):
            # Handle timeframe dictionary
            self.logger.debug(f"OHLCV contains {len(data)} timeframes: {list(data.keys())}")
            
            for tf, tf_data in data.items():
                self.logger.debug(f"\nTimeframe: {tf}")
                
                if isinstance(tf_data, pd.DataFrame):
                    self._log_ohlcv_dataframe(tf_data)
                elif isinstance(tf_data, dict) and 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                    self._log_ohlcv_dataframe(tf_data['data'])
                else:
                    self.logger.debug(f"  Type: {type(tf_data)}")
        
        elif isinstance(data, pd.DataFrame):
            # Handle direct DataFrame
            self._log_ohlcv_dataframe(data)
        
        elif isinstance(data, list):
            # Handle list format (common in raw API responses)
            self.logger.debug(f"OHLCV data is a list with {len(data)} items")
            
            if data:
                # Check first item to determine format
                first_item = data[0]
                if isinstance(first_item, list):
                    self.logger.debug(f"List format with {len(first_item)} columns")
                    self.logger.debug(f"First candle: {first_item}")
                    
                    # Try to convert to DataFrame for better analysis
                    try:
                        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        if len(first_item) == len(columns):
                            df = pd.DataFrame(data, columns=columns)
                            self._log_ohlcv_dataframe(df)
                    except Exception as e:
                        self.logger.debug(f"Could not convert to DataFrame: {str(e)}")
    
    def _log_ohlcv_dataframe(self, df: pd.DataFrame) -> None:
        """Log details of OHLCV DataFrame."""
        self.logger.debug(f"  Shape: {df.shape}")
        self.logger.debug(f"  Columns: {list(df.columns)}")
        self.logger.debug(f"  Index type: {type(df.index)}")
        
        if not df.empty:
            # Show basic statistics
            self.logger.debug("\n  Basic statistics:")
            stats = df.describe().transpose()
            self.logger.debug(f"{stats}")
            
            # Check for NaN values
            nan_count = df.isna().sum().sum()
            if nan_count > 0:
                self.logger.debug(f"\n  Contains {nan_count} NaN values")
                self.logger.debug(f"  NaN counts by column:\n{df.isna().sum()}")
            
            # Log time range
            if hasattr(df, 'index') and isinstance(df.index, pd.DatetimeIndex):
                self.logger.debug(f"\n  Time range: {df.index.min()} to {df.index.max()}")
                self.logger.debug(f"  Duration: {df.index.max() - df.index.min()}")
            
            # Show first and last candles
            self.logger.debug("\n  First candle:")
            self.logger.debug(f"{df.iloc[0]}")
            self.logger.debug("\n  Last candle:")
            self.logger.debug(f"{df.iloc[-1]}")
    
    def _log_orderbook_data(self, data: Any) -> None:
        """Log orderbook data with detailed analysis."""
        if not isinstance(data, dict):
            self.logger.debug(f"Orderbook is not a dictionary: {type(data)}")
            return
        
        # Check for required fields
        required_fields = ['bids', 'asks']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            self.logger.debug(f"Orderbook missing required fields: {missing_fields}")
        
        # Log basic statistics
        if 'bids' in data and isinstance(data['bids'], list):
            bids = data['bids']
            self.logger.debug(f"Bids: {len(bids)} levels")
            if bids:
                self.logger.debug(f"  Top 3 bids:")
                for i, bid in enumerate(bids[:3]):
                    self.logger.debug(f"    {i+1}. Price: {bid[0]}, Qty: {bid[1]}")
                
                # Calculate bid sum
                bid_qty_sum = sum(bid[1] for bid in bids)
                self.logger.debug(f"  Total bid quantity: {bid_qty_sum}")
        
        if 'asks' in data and isinstance(data['asks'], list):
            asks = data['asks']
            self.logger.debug(f"Asks: {len(asks)} levels")
            if asks:
                self.logger.debug(f"  Top 3 asks:")
                for i, ask in enumerate(asks[:3]):
                    self.logger.debug(f"    {i+1}. Price: {ask[0]}, Qty: {ask[1]}")
                
                # Calculate ask sum
                ask_qty_sum = sum(ask[1] for ask in asks)
                self.logger.debug(f"  Total ask quantity: {ask_qty_sum}")
        
        # Calculate bid-ask spread if possible
        if 'bids' in data and 'asks' in data and data['bids'] and data['asks']:
            best_bid = data['bids'][0][0]
            best_ask = data['asks'][0][0]
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
            
            self.logger.debug(f"\nBid-ask spread: {spread} ({spread_pct:.4f}%)")
            self.logger.debug(f"Best bid: {best_bid}, Best ask: {best_ask}")
    
    def _log_trades_data(self, data: Any) -> None:
        """Log trades data with detailed analysis."""
        if isinstance(data, list):
            self.logger.debug(f"Trades: {len(data)} trades")
            
            if not data:
                return
            
            # Show sample trades
            self.logger.debug("\nSample trades:")
            for i, trade in enumerate(data[:3]):
                self.logger.debug(f"  Trade {i+1}: {trade}")
            
            # Try to calculate some statistics
            try:
                # Extract prices and volumes more efficiently
                prices = []
                volumes = []
                for trade in data:
                    if 'price' in trade:
                        prices.append(float(trade.get('price', 0)))
                    if 'amount' in trade or 'quantity' in trade:
                        volumes.append(float(trade.get('amount', trade.get('quantity', 0))))
                
                if prices:
                    # Use numpy for efficient statistics calculation
                    prices_array = np.array(prices)
                    avg_price = np.mean(prices_array)
                    min_price = np.min(prices_array)
                    max_price = np.max(prices_array)
                    
                    self.logger.debug(f"\nPrice statistics:")
                    self.logger.debug(f"  Min: {min_price}, Max: {max_price}, Avg: {avg_price:.4f}")
                
                if volumes:
                    # Use numpy for efficient volume statistics
                    volumes_array = np.array(volumes)
                    total_volume = np.sum(volumes_array)
                    avg_volume = np.mean(volumes_array)
                    
                    self.logger.debug(f"\nVolume statistics:")
                    self.logger.debug(f"  Total: {total_volume}, Avg: {avg_volume:.4f}")
                
                # Count buy vs sell trades if side is available
                buy_count = sum(1 for trade in data if trade.get('side') == 'buy')
                sell_count = sum(1 for trade in data if trade.get('side') == 'sell')
                
                self.logger.debug(f"\nTrade directions:")
                self.logger.debug(f"  Buy: {buy_count} ({buy_count/len(data)*100:.1f}%)")
                self.logger.debug(f"  Sell: {sell_count} ({sell_count/len(data)*100:.1f}%)")
            
            except Exception as e:
                self.logger.debug(f"Error calculating trade statistics: {str(e)}")
        
        elif isinstance(data, pd.DataFrame):
            self.logger.debug(f"Trades DataFrame with shape {data.shape}")
            
            if data.empty:
                return
            
            self.logger.debug(f"Columns: {list(data.columns)}")
            self.logger.debug(f"\nSample trades:\n{data.head(3)}")
            
            # Show basic statistics
            try:
                if 'price' in data.columns:
                    self.logger.debug(f"\nPrice statistics:")
                    self.logger.debug(f"  Min: {data['price'].min()}, Max: {data['price'].max()}, "
                                     f"Avg: {data['price'].mean():.4f}")
                
                if 'amount' in data.columns:
                    self.logger.debug(f"\nVolume statistics:")
                    self.logger.debug(f"  Total: {data['amount'].sum()}, Avg: {data['amount'].mean():.4f}")
                
                # Count buy vs sell trades if side is available
                if 'side' in data.columns:
                    counts = data['side'].value_counts()
                    self.logger.debug(f"\nTrade directions:\n{counts}")
            
            except Exception as e:
                self.logger.debug(f"Error calculating trade statistics: {str(e)}")
    
    def _format_sample(self, value: Any) -> str:
        """Format a sample of a value for logging."""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        elif isinstance(value, dict):
            return f"{{...}} with {len(value)} keys"
        elif isinstance(value, list):
            return f"[...] with {len(value)} items"
        elif isinstance(value, pd.DataFrame):
            return f"DataFrame with shape {value.shape}"
        else:
            return str(type(value))

    def log_operation(self, operation_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log the start of an operation with standardized formatting.
        
        Args:
            operation_name: Name of the operation being performed
            details: Optional dictionary of details to log
        """
        self.logger.debug(f"\n=== {operation_name} ===")
        if details:
            for key, value in details.items():
                self.logger.debug(f"{key}: {value}")

    def log_operation_result(self, operation_name: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None:
        """Log the result of an operation with standardized formatting.
        
        Args:
            operation_name: Name of the operation that was performed
            success: Whether the operation was successful
            details: Optional dictionary of details to log
        """
        status = "SUCCESS" if success else "FAILED"
        self.logger.debug(f"=== {operation_name}: {status} ===")
        if details:
            for key, value in details.items():
                self.logger.debug(f"{key}: {value}")
        self.logger.debug("\n")

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

class MarketMonitor:
    """Class for monitoring market data from exchanges."""
    
    def __init__(
        self,
        exchange=None,
        symbol: Optional[str] = None,
        exchange_manager=None,
        database_client=None,
        portfolio_analyzer=None,
        confluence_analyzer=None,
        timeframes: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
        metrics_manager: Optional[MetricsManager] = None,
        health_monitor: Optional[HealthMonitor] = None,
        validation_config: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        alert_manager=None,
        signal_generator=None,
        top_symbols_manager=None,
        market_data_manager=None,
        **kwargs
    ):
        """Initialize MarketMonitor.
        
        Args:
            exchange: ccxt exchange instance (can be None if exchange_manager is provided)
            symbol: Trading pair symbol (can be None if using TopSymbolsManager)
            exchange_manager: Exchange manager instance
            database_client: Database client for storing analysis results
            portfolio_analyzer: Portfolio analyzer for position management
            confluence_analyzer: Confluence analyzer for market analysis
            timeframes: Dictionary of timeframes to fetch (keys: 'ltf', 'mtf', 'htf', values: timeframe strings)
            logger: Optional logger instance
            metrics_manager: Optional metrics manager instance
            health_monitor: Optional health monitor instance
            validation_config: Optional validation configuration
            config: Optional configuration dictionary
            alert_manager: Alert manager for sending notifications
            signal_generator: Signal generator for trading signals
            top_symbols_manager: Manager for determining which symbols to monitor
            market_data_manager: Manager for retrieving and caching market data
            **kwargs: Additional keyword arguments
        """
        # Store core components
        self.exchange_manager = exchange_manager
        self.database_client = database_client
        self.portfolio_analyzer = portfolio_analyzer
        self.confluence_analyzer = confluence_analyzer
        self.alert_manager = alert_manager
        self.signal_generator = signal_generator
        self.top_symbols_manager = top_symbols_manager
        self.market_data_manager = market_data_manager
        
        # Store exchange info
        self.exchange = exchange
        self.exchange_id = getattr(exchange, 'id', None) if exchange else 'unknown'
        
        # Store full configuration
        self.config = config or {}
        
        # Setup symbol (can be None if using TopSymbolsManager)
        self.symbol = symbol
        self.symbol_str = symbol.replace('/', '') if symbol else None  # Remove / for filename compatibility
        
        # Set up logger
        self.logger = logger or logging.getLogger(__name__)
        
        # Set up logging utility
        self.logging_utility = LoggingUtility(self.logger)
        
        # Set up metrics manager
        self.metrics_manager = metrics_manager or MetricsManager()
        
        # Set up health monitor
        self.health_monitor = health_monitor
        if self.health_monitor and self.exchange_id:
            # Register this exchange with the health monitor
            self.health_monitor.register_api(self.exchange_id)
        
        # Initialize timeframes
        default_timeframes = {'ltf': '1m', 'mtf': '15m', 'htf': '1h'}
        self.timeframes = default_timeframes.copy()
        if timeframes:
            self.timeframes.update(timeframes)
        
        # Add base timeframe (use the lowest timeframe)
        timeframe_values = sorted(self.timeframes.values(), key=lambda x: ccxt_time_to_minutes(x))
        self.timeframes['base'] = timeframe_values[0] if timeframe_values else '1m'
        
        # Configure validation
        default_validation = {
            'max_ohlcv_age_seconds': 300,  # Max age of newest candle in seconds
            'min_ohlcv_candles': 20,       # Minimum number of candles required
            'max_orderbook_age_seconds': 60, # Max age of orderbook in seconds
            'min_orderbook_levels': 5,      # Minimum orderbook levels required
            'max_trades_age_seconds': 300,  # Max age of newest trade in seconds
            'min_trades_count': 5,          # Minimum number of trades required
        }
        self.validation_config = default_validation.copy()
        if validation_config:
            self.validation_config.update(validation_config)
        
        # Rate limiting configuration
        self.rate_limit_config = kwargs.get('rate_limit_config', {
            'enabled': True,
            'max_requests_per_second': 5,  # Default: 5 requests per second
            'timeout_seconds': 10          # Default: 10 second timeout
        })
        
        # Retry configuration
        self.retry_config = kwargs.get('retry_config', {
            'max_retries': 3,              # Default: 3 retries
            'retry_delay_seconds': 2,      # Default: 2 second delay between retries
            'retry_exponential_backoff': True  # Exponential backoff
        })
        
        # Debug configuration
        self.debug_config = kwargs.get('debug_config', {
            'log_raw_responses': False,    # Log raw API responses
            'verbose_validation': False,   # Verbose validation logs
            'save_visualizations': False,  # Save visualizations to disk
            'visualization_dir': 'visualizations'  # Directory for saved visualizations
        })
        
        # Create visualization directory if needed
        if self.debug_config.get('save_visualizations', False):
            Path(self.debug_config.get('visualization_dir', 'visualizations')).mkdir(parents=True, exist_ok=True)
        
        # WebSocket configuration and initialization
        self.websocket_config = kwargs.get('websocket_config', {
            'enabled': True,               # Enable/disable WebSocket
            'use_ws_for_orderbook': True,  # Use WebSocket for orderbook updates
            'use_ws_for_trades': True,     # Use WebSocket for trades updates
            'use_ws_for_tickers': True     # Use WebSocket for ticker updates
        })
        
        # Initialize WebSocket Manager if enabled
        self.ws_manager = None
        self.ws_data = {
            'orderbook': None,             # Latest orderbook from WebSocket
            'trades': [],                  # Recent trades from WebSocket
            'ticker': None,                # Latest ticker from WebSocket
            'kline': {},                   # OHLCV data from WebSocket
            'last_update_time': {          # Last update timestamp for each data type
                'orderbook': 0,
                'trades': 0,
                'ticker': 0,
                'kline': 0
            }
        }
        
        # Initialize monitoring state variables
        self.running = False
        self._last_update_time = 0
        self._error_count = 0
        self.last_report_time = None
        self.report_times = self._calculate_report_times() if hasattr(self, '_calculate_report_times') else []
        self._stats = {
            'total_messages': 0,
            'invalid_messages': 0,
            'delayed_messages': 0,
            'error_count': 0
        }
        self.interval = self.config.get('monitoring', {}).get('interval', 60)
        self.data_validator = MarketDataValidator(self.logger) if 'MarketDataValidator' in globals() else None
        
        # Initialize active state for monitoring
        self._active = True
        
        # Initialize large order monitoring
        self.large_order_config = self.config.get('monitoring', {}).get('large_orders', {
            'enabled': True,
            'threshold_usd': 1000000,  # $1M default threshold
            'cooldown': 300,           # 5 minutes between alerts for same symbol
            'min_price': 0,            # No minimum price filter
            'excluded_symbols': [],    # No excluded symbols 
            'included_symbols': []     # Monitor all symbols
        })
        self._last_check = {}
        
        # Initialize WebSocket if enabled and we have a symbol
        if self.websocket_config.get('enabled', True) and self.symbol_str:
            self._initialize_websocket()
        
        # Initialize market data cache for fetch_market_data method
        self._market_data_cache = {}
        self._cache_ttl = 300  # 5 minutes default cache TTL
        self._last_ohlcv_update = {}
        
        self.logger.info(f"Initialized MarketMonitor for {self.exchange_id}")
        
        # Add TimestampUtility instance
        self.timestamp_utility = TimestampUtility()

    def _initialize_websocket(self) -> None:
        """Initialize WebSocket connection for real-time data."""
        try:
            # Skip if no symbol is provided
            if not self.symbol_str:
                self.logger.info("Skipping WebSocket initialization: No symbol provided")
                return
                
            # Initialize WebSocket Manager with the same config
            self.ws_manager = WebSocketManager(self.config)
            
            # Register callback for WebSocket messages
            self.ws_manager.register_message_callback(self._process_websocket_message)
            
            # Create the list of symbols for the WebSocket manager to track
            symbols = [self.symbol_str]
            
            # Initialize asynchronously using create_task
            # Note: This will be executed when the event loop is running
            asyncio.create_task(self.ws_manager.initialize(symbols))
            
            self.logger.info(f"WebSocket integration initialized for {self.symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.ws_manager = None
            
            # Update health status if available
            if self.health_monitor:
                self.health_monitor._create_alert(
                    level="warning",
                    source=f"websocket:{self.exchange_id}",
                    message=f"Failed to initialize WebSocket: {str(e)}"
                )

    async def _process_websocket_message(self, symbol: str, topic: str, message: Dict[str, Any]) -> None:
        """Process WebSocket message and update internal data.
        
        Args:
            symbol: Trading pair symbol
            topic: Message topic
            message: WebSocket message data
        """
        try:
            # Start performance tracking
            operation = self.metrics_manager.start_operation(f"process_ws_message_{topic}")
            
            # Check if the message is for the symbol we're monitoring
            if symbol != self.symbol_str:
                self.metrics_manager.end_operation(operation)
                return
                
            # Process based on topic type
            if "tickers" in topic:
                await self._process_ticker_update(message)
            elif "kline" in topic:
                await self._process_kline_update(message)
            elif "orderbook" in topic:
                await self._process_orderbook_update(message)
            elif "publicTrade" in topic:
                await self._process_trade_update(message)
            elif "liquidation" in topic:
                await self._process_liquidation_update(message)
            else:
                self.logger.debug(f"Received unhandled topic: {topic}")
                
            # Record metrics
            self.metrics_manager.record_metric("websocket_messages_processed", 1)
            self.metrics_manager.record_metric(f"websocket_messages_{topic}", 1)
            
            # End operation
            self.metrics_manager.end_operation(operation)
            
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message for {topic}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # End operation if it was started
            if 'operation' in locals():
                self.metrics_manager.end_operation(operation, success=False)

    # Add placeholder methods for processing different message types
    async def _process_ticker_update(self, message: Dict[str, Any]) -> None:
        """Process ticker update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract ticker data
            ticker_data = data.get('data', {})
            if not ticker_data:
                return
                
            # Format ticker data
            ticker = {
                'symbol': self.symbol,
                'last': float(ticker_data.get('lastPrice', 0)),
                'bid': float(ticker_data.get('bid1Price', 0)),
                'ask': float(ticker_data.get('ask1Price', 0)),
                'high': float(ticker_data.get('highPrice24h', 0)),
                'low': float(ticker_data.get('lowPrice24h', 0)),
                'volume': float(ticker_data.get('volume24h', 0)),
                'timestamp': int(ticker_data.get('time', timestamp))
            }
            
            # Add additional data if available
            if 'openInterest' in ticker_data:
                ticker['openInterest'] = float(ticker_data['openInterest'])
            if 'fundingRate' in ticker_data:
                ticker['fundingRate'] = float(ticker_data['fundingRate'])
            if 'nextFundingTime' in ticker_data:
                ticker['nextFundingTime'] = int(ticker_data['nextFundingTime'])
            
            # Update internal state
            self.ws_data['ticker'] = ticker
            self.ws_data['last_update_time']['ticker'] = timestamp
            
            # Log update
            self.logger.debug(f"Updated ticker data from WebSocket: Last price: {ticker['last']}")
            
        except Exception as e:
            self.logger.error(f"Error processing ticker update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_kline_update(self, message: Dict[str, Any]) -> None:
        """Process OHLCV update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract kline data
            kline_data = data.get('data', [])
            if not kline_data:
                return
                
            # Get interval from topic
            topic = message.get('topic', '')
            interval = '1'  # Default to 1 minute
            if '.' in topic:
                parts = topic.split('.')
                if len(parts) > 1:
                    interval = parts[1]  # Extract interval from topic
            
            # Map to standard timeframe key
            timeframe_map = {
                '1': 'base',
                '5': 'ltf',
                '30': 'mtf',
                '60': 'mtf',
                '240': 'htf',
                '1D': 'htf'
            }
            
            tf_key = timeframe_map.get(interval, 'base')
            
            # Format candle data
            candles = []
            for candle in kline_data:
                formatted_candle = {
                    'timestamp': int(candle.get('timestamp', 0) or candle.get('start', 0)),
                    'open': float(candle.get('open', 0)),
                    'high': float(candle.get('high', 0)),
                    'low': float(candle.get('low', 0)),
                    'close': float(candle.get('close', 0)),
                    'volume': float(candle.get('volume', 0))
                }
                candles.append(formatted_candle)
            
            # Create DataFrame
            if candles:
                df = pd.DataFrame(candles)
                if 'timestamp' in df.columns:
                    df.set_index('timestamp', inplace=True)
                    df.index = pd.to_datetime(df.index, unit='ms')
                
                # Update internal state
                if tf_key not in self.ws_data['kline']:
                    self.ws_data['kline'][tf_key] = df
                else:
                    # Merge with existing data
                    existing_df = self.ws_data['kline'][tf_key]
                    merged_df = pd.concat([existing_df, df])
                    
                    # Remove duplicates
                    merged_df = merged_df[~merged_df.index.duplicated(keep='last')]
                    
                    # Sort by index
                    merged_df.sort_index(inplace=True)
                    
                    # Keep only the latest candles (max 1000)
                    if len(merged_df) > 1000:
                        merged_df = merged_df.iloc[-1000:]
                        
                    self.ws_data['kline'][tf_key] = merged_df
                
                self.ws_data['last_update_time']['kline'] = timestamp
                
                # Log update
                self.logger.debug(f"Updated {tf_key} OHLCV data from WebSocket: {len(candles)} candles")
                
        except Exception as e:
            self.logger.error(f"Error processing kline update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_orderbook_update(self, message: Dict[str, Any]) -> None:
        """Process orderbook update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract orderbook data
            orderbook_data = data.get('data', {})
            if not orderbook_data:
                return
            
            # Format orderbook data
            orderbook = {
                'symbol': self.symbol,
                'timestamp': int(orderbook_data.get('timestamp', timestamp)),
                'bids': orderbook_data.get('bids', []),
                'asks': orderbook_data.get('asks', [])
            }
            
            # Sort bids (desc) and asks (asc)
            if orderbook['bids']:
                orderbook['bids'] = sorted(orderbook['bids'], key=lambda x: float(x[0]), reverse=True)
            if orderbook['asks']:
                orderbook['asks'] = sorted(orderbook['asks'], key=lambda x: float(x[0]))
            
            # Update internal state
            self.ws_data['orderbook'] = orderbook
            self.ws_data['last_update_time']['orderbook'] = timestamp
            
            # Log update
            self.logger.debug(f"Updated orderbook from WebSocket: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_trade_update(self, message: Dict[str, Any]) -> None:
        """Process trade update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract trade data
            trade_data = data.get('data', [])
            if not trade_data:
                return
            
            # Format trade data
            trades = []
            for trade in trade_data:
                formatted_trade = {
                    'id': trade.get('tradeId', str(timestamp) + str(len(self.ws_data['trades']))),
                    'timestamp': int(trade.get('timestamp', timestamp)),
                    'price': float(trade.get('price', 0)),
                    'amount': float(trade.get('size', 0)),
                    'side': trade.get('side', 'unknown').lower(),
                    'symbol': self.symbol
                }
                trades.append(formatted_trade)
            
            # Update internal state - keep only most recent 1000 trades
            self.ws_data['trades'] = (trades + self.ws_data['trades'])[:1000]
            self.ws_data['last_update_time']['trades'] = timestamp
            
            # Log update
            self.logger.debug(f"Added {len(trades)} new trades from WebSocket. Total: {len(self.ws_data['trades'])}")
            
        except Exception as e:
            self.logger.error(f"Error processing trade update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_liquidation_update(self, message: Dict[str, Any]) -> None:
        """Process liquidation update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract liquidation data
            liquidation_data = data.get('data', {})
            if not liquidation_data:
                return
            
            # Format liquidation data
            liquidation = {
                'symbol': self.symbol,
                'timestamp': int(liquidation_data.get('timestamp', timestamp)),
                'price': float(liquidation_data.get('price', 0)),
                'size': float(liquidation_data.get('size', 0)),
                'side': liquidation_data.get('side', 'unknown').lower()
            }
            
            # Log liquidation event
            self.logger.warning(f"Liquidation detected: {liquidation['side']} {liquidation['size']} {self.symbol} @ {liquidation['price']}")
            
            # If health monitor is available, create alert
            if self.health_monitor:
                self.health_monitor._create_alert(
                    level="info",
                    source=f"liquidation:{self.exchange_id}:{self.symbol_str}",
                    message=f"Liquidation: {liquidation['side']} {liquidation['size']} {self.symbol} @ {liquidation['price']}"
                )
            
        except Exception as e:
            self.logger.error(f"Error processing liquidation update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def close(self) -> None:
        """Close connections and clean up resources."""
        try:
            self.logger.info(f"Closing MarketMonitor for {self.symbol}")
            
            # Close WebSocket connection if available
            if self.ws_manager:
                await self.ws_manager.close()
                self.logger.info("WebSocket connection closed")
            
        except Exception as e:
            self.logger.error(f"Error closing MarketMonitor: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def get_websocket_status(self) -> Dict[str, Any]:
        """Get current WebSocket status."""
        if self.ws_manager:
            status = self.ws_manager.get_status()
            # Add data freshness
            status['data_freshness'] = {
                data_type: time.time() - timestamp/1000 if timestamp > 0 else float('inf')
                for data_type, timestamp in self.ws_data['last_update_time'].items()
            }
            return status
        else:
            return {
                'connected': False,
                'enabled': self.websocket_config.get('enabled', False)
            }

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("\nShutdown signal received. Cleaning up...")
        self.running = False

    async def start(self):
        """Start the market monitor."""
        try:
            # Check for required components
            if not self.exchange_manager:
                self.logger.error("No exchange manager available")
                return
                
            if not self.top_symbols_manager:
                self.logger.error("No top symbols manager available")
                return
                
            if not self.market_data_manager:
                self.logger.error("No market data manager available")
                return
            
            # Get primary exchange from exchange manager if not already set
            if not self.exchange:
                self.exchange = await self.exchange_manager.get_primary_exchange()
                if not self.exchange:
                    self.logger.error("No primary exchange available")
                    return
                    
                # Update exchange ID
                self.exchange_id = self.exchange.exchange_id
                
            self.logger.debug(f"Exchange instance retrieved: {bool(self.exchange)}")
            self.logger.debug("Initializing exchange...")
            
            # Initialize exchange
            await self.exchange.initialize()
            
            self.logger.debug("Setting exchange in TopSymbolsManager...")
            self.top_symbols_manager.set_exchange(self.exchange)
            
            self.logger.info("Waiting for initial data collection...")
            self.logger.info("Updating top symbols...")
            
            # Get symbols directly from top_symbols_manager
            self.symbols = await self.top_symbols_manager.get_symbols()
            if not self.symbols:
                self.logger.warning("No symbols to monitor")
                return
                
            self.logger.info(f"Monitoring symbols: {self.symbols}")
            
            # Extract symbol strings from symbol dictionaries for components that need simple strings
            symbol_strings = []
            for symbol_data in self.symbols:
                if isinstance(symbol_data, dict) and 'symbol' in symbol_data:
                    symbol_strings.append(symbol_data['symbol'])
                elif isinstance(symbol_data, str):
                    symbol_strings.append(symbol_data)
                    
            # Initialize market data manager with symbols to monitor
            await self.market_data_manager.initialize(symbol_strings)
            
            # Start data monitoring in the market data manager
            await self.market_data_manager.start_monitoring()
            
            # Initialize monitoring state
            self.running = True
            self._last_update_time = time.time()
            
            # Start monitoring tasks
            self.logger.info("Starting monitoring tasks...")
            self._monitoring_task = asyncio.create_task(self._run_monitoring_loop())
            
            # Start metrics manager if available
            if self.metrics_manager:
                self.logger.info("Starting metrics manager...")
                await self.metrics_manager.start()
                
            # Start alert manager if available  
            if self.alert_manager:
                self.logger.info("Starting alert manager...")
                await self.alert_manager.start()
                
            self.logger.info("Market monitor started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting monitor: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def _monitoring_cycle(self):
        """Run a single monitoring cycle."""
        try:
            logger.debug("=== Starting Monitoring Cycle ===")
            
            # Get symbols to monitor
            symbols = await self.top_symbols_manager.get_symbols()
            symbol_display = [s['symbol'] if isinstance(s, dict) and 'symbol' in s else s for s in symbols[:5]]
            if len(symbols) > 5:
                symbol_display.append('...')
            logger.debug(f"Symbol manager returned {len(symbols)} symbols: {symbol_display}")
            
            if not symbols:
                logger.warning("Empty symbol list detected!")
                return
            
            # Process each symbol - now using MarketDataManager for efficient data fetching
            for symbol in symbols:
                try:
                    await self._process_symbol(symbol)
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {str(e)}")
                    continue
                
            # Check if it's time for a report
            current_time = datetime.now(timezone.utc)
            should_generate_report = (
                self._is_report_time() and 
                (not self.last_report_time or 
                 (current_time - self.last_report_time).total_seconds() > 300)
            )
            
            if should_generate_report:
                await self._generate_market_report()
                self.last_report_time = current_time
            
        except Exception as e:
            self.logger.error(f"Monitoring cycle error: {str(e)}")
            self.logger.debug(f"Stack trace:\n{traceback.format_exc()}")

    async def _process_symbol(self, symbol: str) -> None:
        """Process a single symbol with market data from MarketDataManager"""
        if not self.exchange_manager:
            self.logger.error("Exchange manager not available")
            return

        if not self.alert_manager:
            self.logger.warning("Alert manager not initialized")
        
        try:
            # Extract symbol string if needed
            symbol_str = symbol['symbol'] if isinstance(symbol, dict) and 'symbol' in symbol else symbol
            
            # Get market data from MarketDataManager
            self.logger.info(f"=== Starting analysis process for {symbol_str} ===")
            market_data = await self.fetch_market_data(symbol_str)
            if not market_data:
                self.logger.error(f"No market data available for {symbol_str}")
                return

            # Log what data we have
            data_components = []
            if 'ticker' in market_data and market_data['ticker']:
                data_components.append('ticker')
            if 'orderbook' in market_data and market_data['orderbook']:
                data_components.append('orderbook')
            if 'trades' in market_data and isinstance(market_data['trades'], list):
                data_components.append(f"trades ({len(market_data['trades'])})")
            if 'ohlcv' in market_data and market_data['ohlcv']:
                timeframes = market_data['ohlcv'].keys()
                data_components.append(f"ohlcv ({', '.join(timeframes)})")
            
            self.logger.info(f"Market data for {symbol_str} contains: {', '.join(data_components)}")

            # Validate market data
            self.logger.info(f"Validating market data for {symbol_str}")
            try:
                validation_result = await self.validate_market_data(market_data)
                if not validation_result:
                    self.logger.error(f"Invalid data for {symbol_str}")
                    return
            except TypeError as e:
                self.logger.error(f"Error validating market data: {str(e)}")
                # Fall back to sync validation if async fails
                if hasattr(self, 'validate_market_data_sync'):
                    try:
                        validation_result = self.validate_market_data_sync(market_data)
                        if not validation_result:
                            self.logger.error(f"Invalid data for {symbol_str} (sync validation)")
                            return
                    except Exception as inner_e:
                        self.logger.error(f"Error in sync validation: {str(inner_e)}")
                        self.logger.error("Continuing with analysis anyway despite validation errors")
                else:
                    self.logger.error("Cannot validate market data. Continuing with analysis anyway.")
            except Exception as e:
                self.logger.error(f"Unexpected error during validation: {str(e)}")
                self.logger.debug(traceback.format_exc())
                self.logger.warning("Continuing with analysis despite validation errors")

            # Check if we have the confluence analyzer
            if not self.confluence_analyzer:
                self.logger.error("Confluence analyzer not initialized - cannot perform analysis")
                return

            # Process analysis
            self.logger.info(f"=== Running confluence analysis for {symbol_str} ===")
            start_time = time.time()
            try:
                analysis_result = await self.confluence_analyzer.analyze(market_data)
                elapsed = time.time() - start_time
                self.logger.info(f"Confluence analysis completed in {elapsed:.2f}s")
                
                # Log analysis results
                if analysis_result:
                    score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
                    reliability = analysis_result.get('reliability', 0)
                    self.logger.info(f"Confluence score: {score:.2f} (reliability: {reliability:.2f})")
                    
                    # Log component scores if available
                    components = analysis_result.get('components', {})
                    if components:
                        component_scores = []
                        for name, value in components.items():
                            if isinstance(value, dict) and 'score' in value:
                                component_scores.append(f"{name}: {value['score']:.2f}")
                            elif isinstance(value, (int, float)):
                                component_scores.append(f"{name}: {value:.2f}")
                        if component_scores:
                            self.logger.info(f"Component scores: {', '.join(component_scores)}")
                else:
                    self.logger.warning(f"Confluence analysis returned no results for {symbol_str}")
            except Exception as e:
                elapsed = time.time() - start_time
                self.logger.error(f"Confluence analysis failed after {elapsed:.2f}s: {str(e)}")
                self.logger.error(traceback.format_exc())
                return
            
            # Process the analysis result (generate signals, etc.)
            self.logger.info(f"Processing analysis results for {symbol_str}")
            await self._process_analysis_result(symbol_str, analysis_result)
            self.logger.info(f"=== Completed analysis process for {symbol_str} ===")

        except AttributeError as e:
            self.logger.error(f"Missing component: {str(e)}")
        except Exception as e:
            self.logger.error(f"Processing failed for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def stop(self) -> None:
        """Stop the market monitor."""
        self.running = False
        
        # Stop the market data manager
        await self.market_data_manager.stop()
        
        # Cleanup other resources
        await self._cleanup()

    async def _cleanup(self):
        """Cleanup resources."""
        try:
            logger.info("Cleaning up resources...")
            # Close exchange connections
            if hasattr(self, 'exchange_manager'):
                await self.exchange_manager.close()
            
            # Cancel any pending tasks
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()
                    
            # Close WebSocket connection
            if hasattr(self, '_ws') and self._ws:
                await self._ws.close()
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    async def _run_monitoring_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info("Starting monitoring loop...")
        
        while self.running:
            try:
                # Run monitoring cycle
                await self._monitoring_cycle()
                
                # Update monitoring metrics
                await self._update_metrics(None)  # We'll update metrics without analysis results
                
                # Check system health
                health_status = await self._check_system_health()
                if health_status['status'] != 'healthy':
                    self.logger.warning(f"System health check: {health_status['status']}")
                    
                    # Check if any component is critical
                    critical_components = [
                        comp for comp, status in health_status['components'].items()
                        if status.get('status') == 'critical'
                    ]
                    
                    if critical_components:
                        self.logger.error(f"Critical components: {critical_components}")
                        
                        # Generate alert for critical components
                        await self._generate_alert(
                            f"Critical system health issues detected: {', '.join(critical_components)}"
                        )
                
                # Check and update market data manager statistics
                mdm_stats = self.market_data_manager.get_stats()
                if self.metrics_manager:
                    await self.metrics_manager.update_system_metrics({
                        'market_data_manager': {
                            'rest_calls': mdm_stats.get('rest_calls', 0),
                            'websocket_updates': mdm_stats.get('websocket_updates', 0),
                            'websocket_connected': mdm_stats.get('websocket', {}).get('connected', False)
                        }
                    })
                
                # Sleep until next cycle
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                self.logger.debug(traceback.format_exc())
                self._error_count += 1
                
                # Back off on errors
                await asyncio.sleep(5)

    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data using the data validator.
        
        This is the central validation method that replaces multiple redundant implementations.
        It performs comprehensive validation of market data structure, freshness, and content.
        
        Args:
            market_data: Market data to validate
            
        Returns:
            bool: True if market data is valid
        """
        # Start performance tracking
        operation = self.metrics_manager.start_operation("validate_market_data")
        
        try:
            # Log validation operation
            self.logger.debug(f"Validating market data for {market_data.get('symbol', 'unknown')}")
            
            # First check basic structure
            if not isinstance(market_data, dict):
                self.logger.error("Market data must be a dictionary")
                return False
            
            # Check for required base fields
            required_fields = ['symbol', 'timestamp']
            missing_fields = [field for field in required_fields if field not in market_data]
            if missing_fields:
                self.logger.error(f"Missing required fields in market data: {missing_fields}")
                return False
            
            # Use the data validator for comprehensive validation
            if hasattr(self, 'data_validator') and self.data_validator is not None:
                result = self.data_validator.validate_market_data(market_data)
                
                # Get validation stats for metrics
                validation_stats = self.data_validator.get_validation_stats()
                
                # Record validation metrics
                self.metrics_manager.record_metric("validation.total", validation_stats['total_validations'])
                self.metrics_manager.record_metric("validation.passed", validation_stats['passed_validations'])
                self.metrics_manager.record_metric("validation.failed", validation_stats['failed_validations'])
            else:
                # If no data validator is available, do basic validation
                self.logger.warning("No data validator available, performing basic validation only")
                result = True  # Assume valid if basic checks pass
            
            # Check timeframes if ohlcv data is present
            if 'ohlcv' in market_data and hasattr(self, 'validate_timeframes'):
                # Make sure we're not awaiting the result if it's not a coroutine
                if callable(self.validate_timeframes):
                    try:
                        timeframe_results = self.validate_timeframes(market_data.get('ohlcv', {}))
                        if isinstance(timeframe_results, dict) and not any(timeframe_results.values()):
                            self.logger.error("All timeframes validation failed")
                            result = False
                    except Exception as e:
                        self.logger.error(f"Error validating timeframes: {str(e)}")
            
            # End performance tracking
            self.metrics_manager.end_operation(operation)
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # End operation with failure
            self.metrics_manager.end_operation(operation, success=False)
            return False

    # This is the non-async version that delegates to the data validator directly
    def validate_market_data_sync(self, market_data: Dict[str, Any]) -> bool:
        """Synchronous version of validate_market_data that delegates to the data validator.
        
        Args:
            market_data: Market data to validate
            
        Returns:
            bool: True if market data is valid
        """
        try:
            self.logger.debug("=== SYNC VALIDATION DEBUG START ===")
            self.logger.debug(f"Processing market data with keys: {list(market_data.keys())}")
            
            # Preprocess market data to ensure numeric types are properly handled
            self.logger.debug("Starting data preprocessing")
            processed_market_data = self._preprocess_market_data_for_validation(market_data)
            self.logger.debug("Preprocessing completed")
            
            # Call validation on preprocessed data
            self.logger.debug("Starting validation on preprocessed data")
            validation_result = self.data_validator.validate_market_data(processed_market_data)
            self.logger.debug(f"Validation result on preprocessed data: {validation_result}")
            
            self.logger.debug("=== SYNC VALIDATION DEBUG END ===")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error in synchronous market data validation: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Try to continue with unprocessed data if preprocessing failed
            try:
                self.logger.debug("=== FALLBACK VALIDATION DEBUG START ===")
                self.logger.debug("Starting fallback validation with original data")
                fallback_result = self.data_validator.validate_market_data(market_data)
                self.logger.debug(f"Fallback validation result: {fallback_result}")
                self.logger.debug("=== FALLBACK VALIDATION DEBUG END ===")
                return fallback_result
            except Exception as inner_e:
                self.logger.error(f"Fallback validation also failed: {str(inner_e)}")
                self.logger.debug(traceback.format_exc())
            return False
            
    def _preprocess_market_data_for_validation(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess market data to ensure numeric values are handled correctly.
        
        This method converts string numeric values to float in common fields that might
        cause comparison issues during validation.
        
        Args:
            market_data: Raw market data dictionary
            
        Returns:
            Dict[str, Any]: Processed market data with numeric conversions
        """
        # Create a deep copy to avoid modifying the original data
        processed = copy.deepcopy(market_data)
        
        try:
            # Add enhanced debugging - log the input structure but only at start
            self.logger.debug("=== PREPROCESSING MARKET DATA DEBUG ===")
            self.logger.debug(f"Market data keys: {list(market_data.keys())}")
            
            # Process orderbook data
            if 'orderbook' in processed and isinstance(processed['orderbook'], dict):
                self.logger.debug(f"Processing orderbook with keys: {list(processed['orderbook'].keys())}")
                
                # Handle nested orderbook structure (Bybit format with result.b and result.a)
                if 'result' in processed['orderbook'] and isinstance(processed['orderbook']['result'], dict):
                    result_data = processed['orderbook']['result']
                    if 'b' in result_data and 'a' in result_data:
                        # Copy bids and asks to standard format
                        processed['orderbook']['bids'] = result_data['b']
                        processed['orderbook']['asks'] = result_data['a']
                        self.logger.debug("Restructured orderbook from result.b/result.a format")
                
                # Log summary of processing, not individual levels
                for side in ['bids', 'asks']:
                    if side in processed['orderbook'] and isinstance(processed['orderbook'][side], list):
                        levels_count = len(processed['orderbook'][side])
                        converted_count = 0
                        
                        for i, level in enumerate(processed['orderbook'][side]):
                            if isinstance(level, (list, tuple)) and len(level) >= 2:
                                # Convert price and size to float
                                try:
                                    if isinstance(level[0], str):
                                        processed['orderbook'][side][i] = [float(level[0]), float(level[1])]
                                        converted_count += 1
                                except (ValueError, TypeError):
                                    # Leave as is if conversion fails
                                    pass
                        
                        # Log summary instead of each conversion
                        if converted_count > 0:
                            self.logger.debug(f"Converted {converted_count}/{levels_count} orderbook {side} levels to float")
            
            # Process trades data with less verbose logging
            if 'trades' in processed:
                self.logger.debug(f"Processing trades data, type: {type(processed['trades'])}")
                original_trades = processed['trades']
                
                # Detect the structure of trades data and extract/normalize the list
                trades_list = None
                trades_structure = 'unknown'
                
                # If trades are in a dict (like API responses with metadata)
                if isinstance(original_trades, dict):
                    # Check for Bybit specific nested structure (result.list)
                    if 'result' in original_trades and isinstance(original_trades['result'], dict) and 'list' in original_trades['result']:
                        trades_list = original_trades['result']['list']
                        trades_structure = 'result.list'
                    # Check if trades are nested in a 'list' key
                    elif 'list' in original_trades:
                        trades_list = original_trades['list']
                        trades_structure = 'list'
                    # Check for 'result' containing a list directly
                    elif 'result' in original_trades and isinstance(original_trades['result'], list):
                        trades_list = original_trades['result']
                        trades_structure = 'result'
                    # Handle other potential structures
                    elif 'data' in original_trades and isinstance(original_trades['data'], list):
                        trades_list = original_trades['data']
                        trades_structure = 'data'
                # If trades is already a list
                elif isinstance(original_trades, list):
                    trades_list = original_trades
                    trades_structure = 'direct_list'
                
                # If we successfully extracted a trades list, process it
                if trades_list is not None:
                    self.logger.debug(f"Extracted trades list from '{trades_structure}' structure with {len(trades_list)} trades")
                    processed['trades_original_format'] = trades_structure
                    
                    # Process the extracted trades list
                    processed_trades = []
                    total_conversions = 0
                    
                    for i, trade in enumerate(trades_list):
                        if isinstance(trade, dict):
                            # Create a processed copy of the trade
                            processed_trade = trade.copy()
                            
                            # Log only the first trade as a sample
                            if i == 0:
                                self.logger.debug(f"Sample trade keys: {list(trade.keys())}")
                                
                            # Convert price and amount/size to float
                            converted_fields = 0
                            for field in trade:
                                if field not in ['symbol', 'side', 'id', 'execId', 'direction', 'tickDirection'] and isinstance(trade[field], str):
                                    try:
                                        processed_trade[field] = float(trade[field])
                                        converted_fields += 1
                                    except (ValueError, TypeError):
                                        pass
                            
                            total_conversions += converted_fields
                            
                            # Handle field mapping but log only first trade
                            if 'price' not in processed_trade and 'execPrice' in processed_trade:
                                processed_trade['price'] = processed_trade['execPrice']
                                if i == 0:
                                    self.logger.debug(f"Mapped execPrice to price field")
                            
                            if 'size' not in processed_trade and 'execQty' in processed_trade:
                                processed_trade['size'] = processed_trade['execQty']
                                if i == 0:
                                    self.logger.debug(f"Mapped execQty to size field")
                            
                            if 'amount' not in processed_trade and 'size' in processed_trade:
                                processed_trade['amount'] = processed_trade['size']
                                if i == 0:
                                    self.logger.debug(f"Added amount field from size")

                            # Map execId to id (needed for orderflow analysis)
                            if "id" not in processed_trade and "execId" in processed_trade:
                                processed_trade["id"] = processed_trade["execId"]
                                if i == 0:
                                    self.logger.debug(f"Mapped execId to id field")
                            
                            processed_trades.append(processed_trade)
                    
                    # Update processed data with the normalized trades list
                    processed['trades'] = processed_trades
                    self.logger.debug(f"Processed {len(processed_trades)} trades with {total_conversions} field conversions")
                else:
                    # Enhanced fallback handling for unknown trade structures
                    self.logger.warning(f"Could not extract trades list from trades data, attempting additional fallbacks")
                    
                    # If it's a dictionary, try to identify any list that might contain trades
                    if isinstance(original_trades, dict):
                        potential_trade_lists = []
                        
                        # Try to find any list with trade-like data in the dict
                        for key, value in original_trades.items():
                            if isinstance(value, list) and len(value) > 0:
                                potential_trade_lists.append((key, value))
                        
                        # If we found potential trade lists, use the one that looks most like trades
                        if potential_trade_lists:
                            # Sort by length - assume longer lists are more likely to be trades
                            potential_trade_lists.sort(key=lambda x: len(x[1]), reverse=True)
                            
                            # Check if items in the list look like trades (has price or amount)
                            for key, value in potential_trade_lists:
                                if value and isinstance(value[0], dict):
                                    # Check if it has trade-like fields
                                    first_item = value[0]
                                    trade_fields = ['price', 'amount', 'size', 'quantity', 'side', 'time', 'timestamp']
                                    
                                    # If it has at least one trade-like field, use this list
                                    if any(field in first_item for field in trade_fields):
                                        trades_list = value
                                        trades_structure = f"extracted_from_{key}"
                                        self.logger.debug(f"Found trade-like list in key '{key}' with {len(trades_list)} items")
                                        
                                        # Process this list similarly to the normal case
                                        processed_trades = []
                                        for trade in trades_list:
                                            if isinstance(trade, dict):
                                                processed_trade = trade.copy()
                                                for field in trade:
                                                    if field not in ['symbol', 'side', 'id'] and isinstance(trade[field], str):
                                                        try:
                                                            processed_trade[field] = float(trade[field])
                                                        except (ValueError, TypeError):
                                                            pass
                                                processed_trades.append(processed_trade)
                                        
                                        processed['trades'] = processed_trades
                                        self.logger.debug(f"Processed {len(processed_trades)} trades from fallback approach")
                                        break
                        
                        # If we still don't have a list, create an empty one
                        if 'trades' not in processed or not isinstance(processed['trades'], list):
                            self.logger.warning("All fallback approaches failed, creating empty trades list")
                            processed['trades'] = []
                    else:
                        # If it's not a dict or list, create an empty list
                        self.logger.warning(f"Trades data type {type(original_trades)} is not supported, creating empty list")
                        processed['trades'] = []
            
            # Process ticker data more efficiently
            if 'ticker' in processed and isinstance(processed['ticker'], dict):
                converted_count = 0
                ticker_fields = list(processed['ticker'].keys())
                
                for field in ticker_fields:
                    value = processed['ticker'][field]
                    if isinstance(value, str) and field not in ['symbol']:
                        try:
                            processed['ticker'][field] = float(value)
                            converted_count += 1
                        except (ValueError, TypeError):
                            pass
                
                # Log summary instead of individual conversions
                if converted_count > 0:
                    self.logger.debug(f"Converted {converted_count}/{len(ticker_fields)} ticker fields to float")
            
            self.logger.debug("=== END PREPROCESSING DEBUG ===")        
            return processed
            
        except Exception as e:
            self.logger.error(f"Error preprocessing market data: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Return original data if preprocessing fails
            return market_data

    async def _update_metrics(self, analysis_results: Optional[List[Dict[str, Any]]]) -> None:
        """Update monitoring metrics."""
        try:
            if not self.metrics_manager:
                return
                
            # Convert all values to float and ensure they are numeric
            metrics = {
                'total_messages': float(self._stats['total_messages']),
                'invalid_messages': float(self._stats['invalid_messages']),
                'delayed_messages': float(self._stats['delayed_messages']),
                'error_count': float(self._stats['error_count']),
                'last_update_time': float(time.time())
            }
            
            # Add market data manager stats
            mdm_stats = self.market_data_manager.get_stats()
            metrics.update({
                'rest_calls': float(mdm_stats.get('rest_calls', 0)),
                'websocket_updates': float(mdm_stats.get('websocket_updates', 0)),
            })
            
            # Update monitoring metrics as system metrics
            await self.metrics_manager.update_system_metrics(metrics)
            
        except Exception as e:
            error_context = ErrorContext(
                component="market_monitor",
                operation="update_metrics"
            )
            if self.error_handler:
                await self.error_handler.handle_error(
                    error=e,
                    context=error_context,
                    severity=ErrorSeverity.LOW
                )
            else:
                logger.error(f"Error updating metrics: {str(e)}")
                
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        try:
            health_status = {
                'status': 'healthy',
                'components': {
                    'exchange': await self._check_exchange_health(),
                    'database': await self._check_database_health(),
                    'memory': await self._check_memory_usage(),
                    'cpu': await self._check_cpu_usage(),
                    'market_data_manager': await self._check_market_data_manager_health()
                }
            }
            
            # Check if any component is unhealthy
            for component, status in health_status['components'].items():
                if status.get('status') != 'healthy':
                    health_status['status'] = 'warning'
                    
                    if status.get('status') == 'critical':
                        health_status['status'] = 'critical'
                        break
                    
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def _check_exchange_health(self) -> Dict[str, Any]:
        """Check exchange connectivity and response times."""
        try:
            if not self.exchange_manager:
                return {'status': 'error', 'message': 'Exchange not initialized'}
                
            # Test API connection
            await self.exchange_manager.ping()
            return {'status': 'healthy'}
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def _check_market_data_manager_health(self) -> Dict[str, Any]:
        """Check health of the market data manager."""
        try:
            stats = self.market_data_manager.get_stats()
            websocket_status = stats.get('websocket', {})
            
            # Check WebSocket connection
            if not websocket_status.get('connected', False):
                return {
                    'status': 'warning',
                    'message': 'WebSocket not connected',
                    'details': websocket_status
                }
            
            # Check time since last WebSocket message
            seconds_since_last_message = websocket_status.get('seconds_since_last_message', 0)
            if seconds_since_last_message > 60:  # No message in last minute
                return {
                    'status': 'warning',
                    'message': f'No WebSocket message received in {seconds_since_last_message:.1f}s',
                    'details': websocket_status
                }
            
            # Check data freshness (oldest symbol data)
            if 'data_freshness' in stats:
                max_age = 0
                oldest_symbol = None
                
                for symbol, freshness in stats['data_freshness'].items():
                    age = freshness.get('age_seconds', 0)
                    if age > max_age:
                        max_age = age
                        oldest_symbol = symbol
                
                if max_age > 300:  # Data older than 5 minutes
                    return {
                        'status': 'warning',
                        'message': f'Data for {oldest_symbol} is {max_age:.1f}s old',
                        'details': {
                            'oldest_symbol': oldest_symbol,
                            'age_seconds': max_age
                        }
                    }
            
            # All checks passed
            return {'status': 'healthy'}
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            # Add your database health check logic here
            return {'status': 'healthy'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'status': 'healthy' if memory.percent < 90 else 'warning',
                'usage': memory.percent
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def _check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            return {
                'status': 'healthy' if cpu_percent < 80 else 'warning',
                'usage': cpu_percent
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def _check_thresholds(self) -> None:
        """Check monitoring thresholds and generate alerts."""
        try:
            # Check invalid message ratio
            if self._stats['total_messages'] > 0:
                invalid_ratio = (
                    self._stats['invalid_messages'] /
                    self._stats['total_messages']
                )
                
                if invalid_ratio > self.config.get('max_invalid_ratio', 0.1):
                    await self._generate_alert(
                        f"High invalid message ratio: {invalid_ratio:.2%}"
                    )
                    
            # Check delayed message ratio
            if self._stats['total_messages'] > 0:
                delayed_ratio = (
                    self._stats['delayed_messages'] /
                    self._stats['total_messages']
                )
                
                if delayed_ratio > self.config.get('max_delayed_ratio', 0.1):
                    await self._generate_alert(
                        f"High delayed message ratio: {delayed_ratio:.2%}"
                    )
                    
            # Check error count
            if self._stats['error_count'] > self.config.get('max_errors', 100):
                await self._generate_alert(
                    f"High error count: {self._stats['error_count']}"
                )
                
        except Exception as e:
            logger.error(f"Error checking thresholds: {str(e)}")
            
    async def _generate_alert(self, message: str) -> None:
        """Generate monitoring alert.
        
        Args:
            message: Alert message
        """
        try:
            if self.alert_manager:
                await self.alert_manager.send_alert(
                    message=message,
                    level="warning",
                    component="monitor"
                )
            else:
                logger.warning(f"Monitor alert: {message}")
                
        except Exception as e:
            logger.error(f"Error generating alert: {str(e)}")
            
    @property
    def stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        # Combine internal stats with market data manager stats
        combined_stats = self._stats.copy()
        
        # Add market data manager stats if available
        if hasattr(self, 'market_data_manager'):
            mdm_stats = self.market_data_manager.get_stats()
            combined_stats['market_data_manager'] = mdm_stats
        
        return combined_stats

    async def _process_analysis_result(self, symbol: str, result: Dict[str, Any]) -> None:
        """Process and handle analysis results"""
        try:
            self.logger.debug("\nProcessing Analysis Result")
            self.logger.debug(f"Result: {result}")

            # Extract key metrics
            confluence_score = result.get('score', result.get('confluence_score', 0))
            reliability = result.get('reliability', 0)
            components = result.get('components', {})
            
            # Log component scores
            self.logger.debug("\n=== Component Scores ===")
            for component, score in components.items():
                self.logger.debug(f"{component}: {score}")
            
            # Generate signal if score meets thresholds
            threshold = self.config.get('analysis', {}).get('confluence_thresholds', {}).get('buy', 70)
            if confluence_score >= threshold:
                await self._generate_signal(symbol, result)
                self.logger.info(f"Generated signal for {symbol} with score {confluence_score}")
            else:
                self.logger.debug(f"No signal generated - confluence score {confluence_score} below threshold {threshold}")

            # Update metrics
            if self.metrics_manager:
                await self.metrics_manager.update_analysis_metrics(symbol, result)

        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _generate_signal(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Generate trading signal based on analysis results"""
        try:
            self.logger.debug("\n=== Generating Signal ===")
            
            # Create signal data
            signal_data = {
                'symbol': symbol,
                'timestamp': pd.Timestamp.now().isoformat(),
                'confluence_score': analysis_result.get('score', analysis_result.get('confluence_score', 0)),
                'reliability': analysis_result.get('reliability', 0),
                'components': analysis_result.get('components', {}),
                'metadata': analysis_result.get('metadata', {})
            }

            # Add signal direction
            score = signal_data['confluence_score']
            buy_threshold = self.config.get('analysis', {}).get('confluence_thresholds', {}).get('buy', 70)
            sell_threshold = self.config.get('analysis', {}).get('confluence_thresholds', {}).get('sell', 30)
            
            if score >= buy_threshold:
                signal_data['direction'] = 'buy'
            elif score <= sell_threshold:
                signal_data['direction'] = 'sell'
            else:
                signal_data['direction'] = 'neutral'

            # Send signal to signal generator if available
            if self.signal_generator:
                await self.signal_generator.process_signal(signal_data)
            
            # Also send to alert manager
            if self.alert_manager:
                await self.alert_manager.process_signal(signal_data)
            
            self.logger.debug(f"Signal generated for {symbol}: {signal_data['direction']}")

        except Exception as e:
            self.logger.error(f"Error generating signal: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _calculate_report_times(self) -> list:
        """Calculate the daily report times in UTC (00:00, 09:00, 13:00, 21:00)"""
        base_time = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Define specific hours for reports
        report_hours = [0, 9, 13, 21]
        
        report_times = [
            (base_time + timedelta(hours=h)).time()
            for h in report_hours
        ]
        
        self.logger.debug(f"Calculated report times (UTC): {report_times}")
        return report_times

    def _is_report_time(self) -> bool:
        """Check if it's time to generate a report"""
        current_time = datetime.now(timezone.utc).time()
        
        # Add logging to debug report timing
        self.logger.debug(f"Checking report time - Current UTC time: {current_time}")
        self.logger.debug(f"Scheduled report times: {self.report_times}")
        
        # Check if current time is close to any of the report times
        for report_time in self.report_times:
            current_minutes = current_time.hour * 60 + current_time.minute
            report_minutes = report_time.hour * 60 + report_time.minute
            
            # Allow a 5-minute window
            if abs(current_minutes - report_minutes) <= 5:
                self.logger.debug(f"Report time matched: {report_time}")
                return True
            
        return False

    def _get_default_scores(self, symbol: str) -> Dict[str, Any]:
        """Return default scores when analysis fails."""
        return {
            'symbol': symbol,
            'score': 50.0,
            'components': {
                'momentum': 50.0,
                'volume': 50.0,
                'orderflow': 50.0,
                'orderbook': 50.0,
                'position': 50.0,
                'sentiment': 50.0
            },
            'metadata': {
                'timestamp': int(time.time() * 1000),
                'status': 'ERROR',
                'error': 'Failed to calculate scores'
            }
        }

    async def analyze_market_data(self, market_data: Dict[str, Any]) -> None:
        """
        Analyze market data and generate signals
        
        Args:
            market_data: Dictionary containing all market data including:
                - symbol: Trading pair symbol
                - ticker: Latest ticker data
                - orderbook: Current orderbook
                - trades: Recent trades
                - ohlcv: OHLCV data for different timeframes
        """
        try:
            symbol = market_data['symbol']
            self.logger.debug(f"Analyzing market data for {symbol}")

            # Get analysis from confluence analyzer
            analysis_result = await self.confluence_analyzer.analyze(market_data)
            if not analysis_result:
                self.logger.warning(f"No analysis result for {symbol}")
                analysis_result = self._get_default_scores(symbol)

            # Generate signals based on analysis
            signals = await self.signal_generator.generate_signals(
                symbol=symbol,
                market_data=market_data,
                analysis=analysis_result
            )

            # Process any signals through alert manager
            if signals:
                self.logger.info(f"Generated signals for {symbol}: {signals}")
                await self.alert_manager.process_signals(signals)
            else:
                self.logger.debug(f"No signals generated for {symbol}")

            # Store analysis results
            await self.database_client.store_analysis(
                symbol=symbol,
                analysis=analysis_result,
                signals=signals
            )

        except Exception as e:
            self.logger.error(f"Error analyzing market data for {market_data.get('symbol')}: {str(e)}", exc_info=True)
            # Use default scores on error
            analysis_result = self._get_default_scores(market_data.get('symbol'))

    def _format_number(self, num: float) -> str:
        """Format large numbers with K/M/B suffixes."""
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num/1_000:.2f}K"
        else:
            return f"{num:.2f}"

    def _calculate_market_overview(self) -> Dict[str, Any]:
        """Calculate market overview metrics"""
        try:
            total_turnover = 0
            total_oi = 0
            
            for symbol, symbol_data in self.top_symbols_manager.get_all_symbol_data().items():
                ticker = symbol_data.get('ticker', {})
                
                # Use turnover24h instead of volume24h for futures
                turnover = float(ticker.get('turnover24h', 0))
                total_turnover += turnover
                
                # Extract open interest and convert to float
                oi = float(ticker.get('openInterest', 0))
                total_oi += oi
                
            return {
                'total_volume': total_turnover,
                'total_oi': total_oi,
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market overview: {str(e)}")
            return {
                'total_volume': 0,
                'total_oi': 0,
                'timestamp': int(time.time() * 1000)
            }

    def _calculate_btc_betas(self, top_pairs: List[str], lookback_periods: int = 20) -> List[tuple]:
        """Calculate beta coefficients relative to BTC."""
        try:
            # Get BTC data
            btc_data = self.top_symbols_manager.get_symbol_data('BTCUSDT')
            if not btc_data or 'ohlcv' not in btc_data:
                self.logger.warning("No BTC data available for beta calculation")
                return []

            # Get base timeframe DataFrame
            btc_df = btc_data['ohlcv'].get('base', {}).get('data')
            if not isinstance(btc_df, pd.DataFrame):
                self.logger.warning("BTC data is not in DataFrame format")
                return []
            
            # Use vectorized numpy operations instead of calculating betas one by one
            btc_returns = btc_df['close'].pct_change().dropna().tail(lookback_periods).values
            btc_mean = np.mean(btc_returns)
            btc_var = np.var(btc_returns)
            
            betas = []
            for symbol in top_pairs:
                if symbol == 'BTCUSDT':
                    continue

                try:
                    pair_data = self.top_symbols_manager.get_symbol_data(symbol)
                    if not pair_data or 'ohlcv' not in pair_data:
                        continue

                    # Get pair DataFrame
                    pair_df = pair_data['ohlcv'].get('base', {}).get('data')
                    if not isinstance(pair_df, pd.DataFrame):
                        continue

                    if len(pair_df) < lookback_periods:
                        continue

                    # Calculate pair returns using DataFrame operations
                    pair_df['returns'] = pair_df['close'].pct_change() * 100
                    returns = pair_df['returns'].dropna().tail(lookback_periods).values

                    if len(returns) != len(btc_returns):
                        continue

                    # Calculate beta using numpy operations
                    mean_return = returns.mean()
                    covariance = np.mean((returns - mean_return) * (btc_returns - btc_mean))
                    variance = np.var(btc_returns)

                    if variance != 0:
                        beta = covariance / variance
                        betas.append((symbol, beta))

                except Exception as e:
                    self.logger.debug(f"Error calculating beta for {symbol}: {str(e)}")
                    continue

            return sorted(betas, key=lambda x: abs(x[1]), reverse=True)

        except Exception as e:
            self.logger.error(f"Error calculating BTC betas: {str(e)}")
            self.logger.debug("Error details:", exc_info=True)
            return []

    def monitor_liquidations(self, market_data):
        """Monitor for large liquidation events"""
        current_time = time.time()
        
        # Clean old events
        self.liquidation_events = [event for event in self.liquidation_events 
                                 if current_time - event['timestamp'] < self.liquidation_window]
        
        if 'liquidation_amount' in market_data:
            liquidation = {
                'timestamp': current_time,
                'amount': market_data['liquidation_amount'],
                'symbol': market_data['symbol']
            }
            
            self.liquidation_events.append(liquidation)
            
            # Calculate total liquidations in window
            total_liquidations = sum(event['amount'] for event in self.liquidation_events)
            
            if total_liquidations > self.liquidation_threshold:
                self.alert_manager.send_alert(
                    'LARGE_LIQUIDATION',
                    f'Large liquidation event detected: ${total_liquidations:,.2f} in last {self.liquidation_window/60:.0f} minutes',
                    severity='HIGH'
                )

    async def _process_liquidation_queue(self):
        """Process queued liquidation events."""
        try:
            while True:
                liquidation_data = await self._liquidation_queue.get()
                await self.handle_liquidation(liquidation_data)
                self._liquidation_queue.task_done()
        except Exception as e:
            self.logger.error(f"Error processing liquidation queue: {str(e)}")

    async def _subscribe_to_liquidations(self, symbol: str) -> None:
        """Subscribe to liquidation events for a symbol."""
        try:
            # Subscribe to liquidation channel
            await self.ws_handler.subscribe_liquidations(symbol)
        except Exception as e:
            self.logger.error(f"Error subscribing to liquidations for {symbol}: {str(e)}")

    def handle_liquidation(self, message):
        """Handle incoming liquidation message."""
        try:
            loop = asyncio.get_event_loop()
            liquidation_data = self.process_liquidation_message(message)
            
            if liquidation_data:
                if loop.is_running():
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._liquidation_queue.put(liquidation_data)))
                else:
                    loop.run_until_complete(self._liquidation_queue.put(liquidation_data))
        except Exception as e:
            self.logger.error(f"Error handling liquidation message: {str(e)}")

    def process_liquidation_message(self, message):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.handle_liquidation(message))
            else:
                loop.run_until_complete(self.handle_liquidation(message))
        except Exception as e:
            self.logger.error(f"Error processing liquidation message: {str(e)}")

    def _calculate_risk_metrics(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate market risk metrics."""
        try:
            metrics = {
                'volatility': {},
                'liquidations': {},
                'funding_rates': {},
                'market_sentiment': 0
            }
            
            # Calculate market-wide metrics
            for symbol in top_pairs:
                data = self.top_symbols_manager.get_symbol_data(symbol)
                if not data:
                    continue
                    
                # Get OHLCV data
                ohlcv = data.get('ohlcv', {}).get('base', {}).get('data')
                if isinstance(ohlcv, pd.DataFrame) and not ohlcv.empty:
                    # Calculate volatility (20-period standard deviation of returns)
                    returns = ohlcv['close'].pct_change()
                    vol = returns.std() * 100  # Convert to percentage
                    metrics['volatility'][symbol] = vol
                    
                # Get funding rate
                funding_rate = float(data.get('ticker', {}).get('fundingRate', 0)) * 100
                metrics['funding_rates'][symbol] = funding_rate
                
                # Get liquidation data
                liquidations = data.get('liquidations', {})
                if liquidations:
                    metrics['liquidations'][symbol] = {
                        'long_liq': float(liquidations.get('long_liquidations', 0)),
                        'short_liq': float(liquidations.get('short_liquidations', 0))
                    }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {str(e)}")
            return {}

    def _format_risk_metrics(self, risk_metrics: Dict[str, Any]) -> str:
        """Format risk metrics for display."""
        if not risk_metrics:
            return "Risk metrics calculation failed"
            
        lines = []
        
        # High Volatility Pairs
        if risk_metrics.get('volatility'):
            vol_pairs = sorted(
                risk_metrics['volatility'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            if vol_pairs:
                lines.append("**High Volatility:**")
                for symbol, vol in vol_pairs:
                    lines.append(f"• {symbol}: {vol:.1f}% 24h")
        
        # Extreme Funding Rates
        if risk_metrics.get('funding_rates'):
            extreme_funding = [
                (s, r) for s, r in risk_metrics['funding_rates'].items()
                if abs(r) > 0.1  # More than 0.1% funding rate
            ]
            if extreme_funding:
                lines.append("\n**Notable Funding Rates:**")
                for symbol, rate in sorted(extreme_funding, key=lambda x: abs(x[1]), reverse=True)[:3]:
                    lines.append(f"• {symbol}: {rate:+.3f}%")
        
        # Large Liquidations
        if risk_metrics.get('liquidations'):
            significant_liqs = []
            for symbol, liq_data in risk_metrics['liquidations'].items():
                total_liqs = liq_data['long_liq'] + liq_data['short_liq']
                if total_liqs > 1000000:  # More than $1M
                    significant_liqs.append((symbol, total_liqs))
            
            if significant_liqs:
                lines.append("\n**Significant Liquidations (24h):**")
                for symbol, amount in sorted(significant_liqs, key=lambda x: x[1], reverse=True)[:3]:
                    lines.append(f"• {symbol}: ${amount/1e6:.1f}M")
        
        # Market Risk Level
        total_vol = sum(risk_metrics.get('volatility', {}).values()) / len(risk_metrics.get('volatility', [1]))
        risk_level = "🟢 Low" if total_vol < 50 else "🟡 Medium" if total_vol < 80 else "🔴 High"
        lines.append(f"\n**Market Risk Level:** {risk_level}")
        
        return "\n".join(lines)

    def should_monitor_symbol(self, symbol: str, price: float) -> bool:
        """Check if symbol should be monitored for large orders."""
        try:
            # Check if monitoring is enabled
            if not self.large_order_config['enabled']:
                return False
                
            # Check price minimum
            if price < self.large_order_config['min_price']:
                return False
                
            # Check excluded symbols
            if symbol in self.large_order_config['excluded_symbols']:
                return False
                
            # Check included symbols (if specified)
            included = self.large_order_config['included_symbols']
            if included and symbol not in included:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking symbol monitoring: {str(e)}")
            return False
            
    async def process_orderbook(self, symbol: str, orderbook_data: Dict[str, Any]):
        """Process orderbook data for monitoring."""
        try:
            # Only proceed if orderbook_data is valid
            if not orderbook_data or not isinstance(orderbook_data, dict):
                return orderbook_data
                
            # Get current price
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            if not bids or not asks:
                return orderbook_data
                
            mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2
            
            # Check if monitoring is active
            if not hasattr(self, '_active') or not self._active:
                return orderbook_data
                
            # Check if we should monitor this symbol
            if not self.should_monitor_symbol(symbol, mid_price):
                return orderbook_data
                
            # Check cooldown
            current_time = time.time()
            if current_time - self._last_check.get(symbol, 0) < self.large_order_config.get('cooldown', 300):
                return orderbook_data
                
            self._last_check[symbol] = current_time
            
            # Return the processed orderbook
            return orderbook_data
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook for monitoring: {str(e)}")
            return orderbook_data  # Return original data in case of error

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        try:
            return {
                'active': self._active,
                'large_orders': {
                    'enabled': self.large_order_config['enabled'],
                    'threshold_usd': self.large_order_config['threshold_usd'],
                    'monitored_symbols': len(self.large_order_config['included_symbols']) or 'all',
                    'excluded_symbols': len(self.large_order_config['excluded_symbols'])
                },
                'last_check': dict(self._last_check)
            }
        except Exception as e:
            self.logger.error(f"Error getting monitoring stats: {str(e)}")
            return {}

    def process_liquidation_alert(self, liquidation_data):
        """Process liquidation events and generate alerts."""
        # Cooldown settings
        LIQUIDATION_COOLDOWN = 60  # 1 minute cooldown between similar alerts
        
        symbol = liquidation_data['symbol']
        current_time = time.time()
        
        # Check cooldown
        if symbol in self._last_check and \
           current_time - self._last_check[symbol] < LIQUIDATION_COOLDOWN:
            return
            
        self._last_check[symbol] = current_time
        
        # Calculate value in USD first
        value_usd = liquidation_data['size'] * liquidation_data['price']
        
        # Value-based threshold
        SIGNIFICANT_VALUE_THRESHOLD = 250_000  # $250k USD minimum for alerts
        
        if value_usd >= SIGNIFICANT_VALUE_THRESHOLD:
            # Determine side emoji and color indicator
            side = liquidation_data['side']
            if side.lower() == 'buy':  # Long liquidation
                side_emoji = "🔴"
                position_type = "LONG"
                impact = "Potential bearish pressure as forced selling may drive prices lower"
            else:  # Short liquidation
                side_emoji = "🟢"
                position_type = "SHORT"
                impact = "Potential bullish pressure as forced buying may drive prices higher"
            
            # Convert timestamp to UTC and format
            utc_time = datetime.utcfromtimestamp(liquidation_data['timestamp']/1000)
            
            # Get market context if available
            market_data = self.top_symbols_manager.get_symbol_data(liquidation_data['symbol'])
            context = ""
            if market_data:
                try:
                    # Get 1h price change
                    ohlcv = market_data.get('ohlcv', {}).get('1h', {}).get('data')
                    if isinstance(ohlcv, pd.DataFrame) and not ohlcv.empty:
                        price_change_1h = ((liquidation_data['price'] - ohlcv['close'].iloc[-2]) / ohlcv['close'].iloc[-2]) * 100
                        context = f"\n📈 Price Change (1h): {price_change_1h:+.2f}%"
                except Exception as e:
                    self.logger.debug(f"Error calculating price context: {str(e)}")
            
            # Get symbol's quote currency (e.g., USDT from BTCUSDT)
            quote_currency = symbol[-4:] if symbol.endswith('USDT') else symbol[-3:]
            
            # Format message with detailed information
            message = (
                f"💥 {position_type} Position Liquidated\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏷️ Symbol: {liquidation_data['symbol']}\n"
                f"⏰ Time: {utc_time.strftime('%H:%M:%S')} UTC\n"
                f" Size: {liquidation_data['size']:.4f} {symbol.replace(quote_currency, '')}\n"
                f"💵 Value: ${value_usd:,.2f}\n"
                f"📊 Price: ${liquidation_data['price']:,.2f}{context}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Market Impact: {impact}"
            )
            
            self.alert_manager.send_alert("WARNING", message, "liquidation")

    async def _prepare_market_data(self, symbol: str) -> Dict[str, Any]:
        """Prepare market data with caching and proper structure."""
        try:
            current_time = time.time()
            
            # Check cache
            if symbol in self._market_data_cache:
                cache_entry = self._market_data_cache[symbol]
                if current_time - cache_entry['timestamp'] < self._cache_ttl:
                    return cache_entry['data']

            # Fetch new data
            raw_data = await self.exchange_manager.fetch_market_data(symbol)
            if not raw_data:
                logger.error(f"No market data available for {symbol}")
                return None

            # Structure the data in required format
            market_data = {
                'symbol': symbol,
                'ohlcv': {
                    'base': {'data': raw_data['ohlcv']['base']},
                    'ltf': {'data': raw_data['ohlcv']['ltf']},
                    'mtf': {'data': raw_data['ohlcv']['mtf']},
                    'htf': {'data': raw_data['ohlcv']['htf']}
                },
                'orderbook': raw_data.get('orderbook', {}),
                'ticker': raw_data.get('ticker', {}),
                'metadata': {
                    'exchange': self.exchange_manager.get_exchange_name(),
                    'market_type': 'futures',
                    'quote_currency': 'USDT'
                }
            }

            # Cache the structured data
            self._market_data_cache[symbol] = {
                'timestamp': current_time,
                'data': market_data
            }

            return market_data

        except Exception as e:
            logger.error(f"Error preparing market data for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None

    async def process_market_data(self, symbol: str, market_data: Dict[str, Any] = None) -> None:
        """Process market data and generate signals."""
        try:
            self.logger.debug(f"\n=== Processing Analysis for {symbol} ===")
            
            # Fetch market data if not provided
            if market_data is None:
                market_data = await self.fetch_market_data(symbol)
                if market_data is None:
                    return
            
            # Validate market data structure
            if not self.data_validator.validate_market_data(market_data):
                self.logger.error(f"Invalid market data structure for {symbol}")
                return

            # Process data through DataProcessor
            processed_data = await self.data_processor.process(market_data)
            
            # Run confluence analysis
            analysis_result = await self.confluence_analyzer.analyze(processed_data)
            
            # Log analysis results
            self.logger.debug("\n=== Analysis Results ===")
            self.logger.debug(f"Confluence Score: {analysis_result.get('confluence_score', 0):.2f}")
            self.logger.debug(f"Reliability: {analysis_result.get('reliability', 0):.2f}")
            
            # Update monitoring metrics
            await self._update_metrics([analysis_result])
            
            # Process analysis result
            await self._process_analysis_result(symbol, analysis_result)
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}", exc_info=True)
            
            # Update error stats
            self._stats['error_count'] += 1
            
            # Handle error through error handler if available
            if self.error_handler:
                error_context = ErrorContext(
                    component="market_monitor",
                    operation="process_market_data",
                    symbol=symbol
                )
                await self.error_handler.handle_error(
                    error=e,
                    context=error_context,
                    severity=ErrorSeverity.MEDIUM
                )

    async def analyze_symbol(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Analyze market data for a symbol.
        
        This method validates timeframes and runs analysis to generate trading signals.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data dictionary
            
        Returns:
            bool: True if analysis was successful
        """
        try:
            # Validate timeframes first
            if not self.validate_timeframes(market_data.get('ohlcv', {})):
                self.logger.error(f"Invalid timeframe data for {symbol}")
                return False
            
            # Run analysis to generate analysis result
            analysis_result = await self.confluence_analyzer.analyze(market_data)
            
            if not analysis_result:
                self.logger.error(f"Failed to generate analysis result for {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {str(e)}", exc_info=True)
            return False

        # Generate trading signal based on analysis results
        try:
            self.logger.debug("\n=== Generating Signal ===")
            
            # Create signal data
            signal_data = {
                'symbol': symbol,
                'timestamp': pd.Timestamp.now().isoformat(),
                'confluence_score': analysis_result.get('score', analysis_result.get('confluence_score', 0)),
                'reliability': analysis_result.get('reliability', 0),
                'components': analysis_result.get('components', {}),
                'metadata': analysis_result.get('metadata', {})
            }

            # Add signal direction
            score = signal_data['confluence_score']
            buy_threshold = self.config.get('analysis', {}).get('confluence_thresholds', {}).get('buy', 70)
            sell_threshold = self.config.get('analysis', {}).get('confluence_thresholds', {}).get('sell', 30)
            
            if score >= buy_threshold:
                signal_data['direction'] = 'buy'
            elif score <= sell_threshold:
                signal_data['direction'] = 'sell'
            else:
                signal_data['direction'] = 'neutral'

            # Send signal to signal generator if available
            if self.signal_generator:
                await self.signal_generator.process_signal(signal_data)
            
            # Also send to alert manager
            if self.alert_manager:
                await self.alert_manager.process_signal(signal_data)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating signal: {str(e)}")
            return False

    def _validate_market_data_structure(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data structure."""
        try:
            if not isinstance(market_data, dict):
                return False
                
            required_fields = ['symbol', 'ticker', 'orderbook', 'metadata']
            if not all(field in market_data for field in required_fields):
                return False
                
            # Check ticker fields
            ticker_fields = ['last', 'bid', 'ask', 'volume', 'turnover', 'timestamp']
            if not all(field in market_data['ticker'] for field in ticker_fields):
                return False
                
            # Check orderbook fields
            if not all(field in market_data['orderbook'] for field in ['bids', 'asks', 'timestamp']):
                return False
                
            # Check metadata fields
            metadata_fields = ['exchange', 'market_type', 'quote_currency']
            if not all(field in market_data['metadata'] for field in metadata_fields):
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error validating market data structure: {str(e)}")
            return False

    async def _check_score_changes(self, symbol: str, current: Dict[str, float], previous: Dict[str, float]) -> None:
        """Check for significant score changes."""
        try:
            for indicator, score in current.items():
                if indicator in previous:
                    change = abs(score - previous[indicator])
                    if change > self.monitoring_thresholds['score_change']:
                        await self._handle_score_change(symbol, indicator, score, previous[indicator])
                        
        except Exception as e:
            self.logger.error(f"Error checking score changes: {str(e)}")

    async def _check_indicator_divergences(self, symbol: str, scores: Dict[str, float]) -> None:
        """Check for divergences between indicators."""
        try:
            # Check momentum-volume divergence
            if 'momentum' in scores and 'volume' in scores:
                divergence = abs(scores['momentum'] - scores['volume'])
                if divergence > self.monitoring_thresholds['divergence']:
                    await self._handle_divergence(symbol, 'momentum', 'volume', divergence)
                    
            # Check orderflow-orderbook divergence
            if 'orderflow' in scores and 'orderbook' in scores:
                divergence = abs(scores['orderflow'] - scores['orderbook'])
                if divergence > self.monitoring_thresholds['divergence']:
                    await self._handle_divergence(symbol, 'orderflow', 'orderbook', divergence)
                    
        except Exception as e:
            self.logger.error(f"Error checking divergences: {str(e)}")

    async def _monitor_momentum(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor momentum indicators for significant changes."""
        try:
            if previous is None:
                return
                
            # Check for significant changes
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['momentum_change']:
                await self._handle_momentum_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring momentum: {str(e)}")

    async def _monitor_volume(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor volume indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['volume_change']:
                await self._handle_volume_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring volume: {str(e)}")

    async def _monitor_orderflow(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor orderflow indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['orderflow_change']:
                await self._handle_orderflow_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring orderflow: {str(e)}")

    async def _monitor_orderbook(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor orderbook indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['orderbook_change']:
                await self._handle_orderbook_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring orderbook: {str(e)}")

    async def _monitor_position(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor position indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['position_change']:
                await self._handle_position_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring position: {str(e)}")

    async def _monitor_sentiment(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor sentiment indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['sentiment_change']:
                await self._handle_sentiment_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring sentiment: {str(e)}")

    # Add corresponding alert handlers
    async def _handle_momentum_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant momentum changes."""
        message = f"Significant momentum change for {symbol}: {previous:.2f} -> {current['score']:.2f}"
        await self.alert_manager.send_alert("MOMENTUM", message, level="INFO")

    async def _handle_volume_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant volume changes."""
        message = f"Significant volume change for {symbol}: {previous:.2f} -> {current['score']:.2f}"
        await self.alert_manager.send_alert("VOLUME", message, level="INFO")

    async def _handle_orderflow_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant orderflow changes."""
        message = f"Significant orderflow change for {symbol}: {previous:.2f} -> {current['score']:.2f}"
        await self.alert_manager.send_alert("ORDERFLOW", message, level="INFO")

    async def _handle_orderbook_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant orderbook changes."""
        message = f"Significant orderbook change for {symbol}: {previous:.2f} -> {current['score']:.2f}"
        await self.alert_manager.send_alert("ORDERBOOK", message, level="INFO")

    async def _handle_position_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant position changes."""
        message = f"Significant position change for {symbol}: {previous:.2f} -> {current['score']:.2f}"
        await self.alert_manager.send_alert("POSITION", message, level="INFO")

    async def _handle_sentiment_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant sentiment changes."""
        message = f"Significant sentiment change for {symbol}: {previous:.2f} -> {current['score']:.2f}"
        await self.alert_manager.send_alert("SENTIMENT", message, level="INFO")

    async def _process_market_data(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Process market data for monitoring and analysis.
        
        This consolidated method handles all market data processing functionality,
        replacing multiple redundant implementations.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data dictionary
        """
        try:
            # Start performance tracking
            operation = self.metrics_manager.start_operation("process_market_data")
            
            # Log the operation
            self.logger.debug(f"\n=== Processing market data for {symbol} ===")
            
            # If symbol is not provided in the arguments, try to get it from the market data
            symbol = symbol or market_data.get('symbol', 'unknown')
            
            # Validate market data
            if not await self.validate_market_data(market_data):
                self.logger.error(f"Invalid market data for {symbol}")
                self.metrics_manager.end_operation(operation, success=False)
                return
            
            # Calculate metrics
            ticker = market_data.get('ticker', {})
            price = float(ticker.get('last', 0))
            change24h = float(ticker.get('change24h', 0))
            volume = float(ticker.get('volume', 0))
            funding_rate = float(ticker.get('fundingRate', 0))

            # Monitor significant price changes
            if abs(change24h) > 5.0:  # 5% threshold
                await self.alert_manager.send_alert(
                    "PRICE_CHANGE",
                    f"Significant price change for {symbol}: {change24h:+.2f}%",
                    level="INFO"
                )

            # Monitor funding rate extremes
            if abs(funding_rate) > 0.001:  # 0.1% threshold
                await self.alert_manager.send_alert(
                    "FUNDING_RATE",
                    f"High funding rate for {symbol}: {funding_rate:.4f}",
                    level="INFO"
                )

            # Monitor orderbook imbalances
            orderbook = market_data.get('orderbook', {})
            if orderbook:
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])
                
                if bids and asks:
                    # Extract the quantities from the first 5 levels and convert to numpy array for efficient calculations
                    bid_quantities = np.array([float(bid[1]) for bid in bids[:5]])
                    ask_quantities = np.array([float(ask[1]) for ask in asks[:5]])
                    
                    bid_sum = np.sum(bid_quantities)
                    ask_sum = np.sum(ask_quantities)
                    
                    if bid_sum > 0 and ask_sum > 0:
                        imbalance = (bid_sum - ask_sum) / (bid_sum + ask_sum)
                        if abs(imbalance) > 0.2:  # 20% imbalance threshold
                            direction = "buy" if imbalance > 0 else "sell"
                            await self.alert_manager.send_alert(
                                "ORDERBOOK_IMBALANCE",
                                f"Large {direction} imbalance for {symbol}: {abs(imbalance):.1%}",
                                level="INFO"
                            )
            
            # Update indicators
            self._update_indicators(market_data)
            
            # Generate signals
            signals = self._generate_signals(market_data)
            
            # Process alerts
            self._process_alerts(signals)
            
            # Record metrics
            self.metrics_manager.record_metric(f"market_data_processed.{symbol}", 1)
            
            # End performance tracking
            self.metrics_manager.end_operation(operation)
            self.logger.debug(f"Successfully processed market data for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error processing market data for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Record error metric
            self.metrics_manager.record_metric(f"market_data_errors.{symbol}", 1)
            
            # End operation with failure if it was started
            if 'operation' in locals():
                self.metrics_manager.end_operation(operation, success=False)
    
    # This synchronous version is kept for backward compatibility and delegates to the async version
    def _process_market_data_sync(self, market_data: Dict) -> None:
        """Synchronous wrapper for _process_market_data.
        
        Args:
            market_data: Market data dictionary
        """
        try:
            symbol = market_data.get('symbol', 'unknown')
            loop = asyncio.get_event_loop()
            
            if loop.is_running():
                asyncio.create_task(self._process_market_data(symbol, market_data))
            else:
                loop.run_until_complete(self._process_market_data(symbol, market_data))
                
        except Exception as e:
            self.logger.error(f"Error in synchronous market data processing: {str(e)}")
    
    # Remove the duplicate _process_market_data method at around line 2868

    async def _generate_market_report(self) -> None:
        """Generate and send comprehensive market report."""
        try:
            # Get top trading pairs
            symbols = await self.top_symbols_manager.get_symbols()
            if not symbols:
                self.logger.warning("No symbols available for market report")
                return

            # Collect market data
            market_overview = {
                'total_volume': 0,
                'total_turnover': 0,
                'gainers': [],
                'losers': [],
                'high_funding': [],
                'imbalances': []
            }

            # Get market data manager stats
            mdm_stats = self.market_data_manager.get_stats()
            
            # Format report
            report = {
                "title": "Market Monitor Status Report",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {
                    "symbols_monitored": len(symbols),
                    "websocket_status": mdm_stats.get('websocket', {}).get('connected', False),
                    "rest_calls": mdm_stats.get('rest_calls', 0),
                    "websocket_updates": mdm_stats.get('websocket_updates', 0)
                },
                "system_health": await self._check_system_health()
            }
            
            # Send report through alert manager
            if self.alert_manager:
                await self.alert_manager.send_alert(
                    message="Market Monitor Status Report",
                    level="INFO",
                    details=report
                )

        except Exception as e:
            self.logger.error(f"Error generating market report: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _format_market_report(self, overview: Dict[str, Any], top_pairs: List[str]) -> Dict[str, Any]:
        """Format market report as Discord embed."""
        current_time = datetime.now()
        utc_time = datetime.now(timezone.utc)
        
        embed = {
            "title": "🎯 Market Monitor Report",
            "description": (
                f"Generated at: {current_time.strftime('%Y-%m-%d %H:%M:%S')} Local\n"
                f"UTC: {utc_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                "\n─────────────────────────────"
            ),
            "color": 0x6B46C1,
            "timestamp": utc_time.isoformat(),
            "fields": [],
            "footer": {
                "text": "Virtuoso Market Monitor",
                "icon_url": "https://raw.githubusercontent.com/virtuoso-dev/virtuoso/main/assets/logo.png"
            }
        }
        
        # Add market overview
        embed["fields"].append({
            "name": "📊 Market Overview",
            "value": (
                f"Total 24h Turnover: ${overview['total_volume']/1e9:.2f}B\n"
                f"Total Open Interest: ${overview['total_oi']/1e9:.2f}B\n"
                "\n─────────────────────────────"
            ),
            "inline": False
        })
        
        # Add BTC Beta Coefficients
        betas = self._calculate_btc_betas(top_pairs)
        if betas:
            beta_text = []
            for symbol, beta in betas[:5]:
                direction = "📈" if beta > 0 else "📉"
                beta_text.append(f"{direction} **{symbol}**: {beta:>8.2f}")
            
            embed["fields"].append({
                "name": "📊 BTC Beta Coefficients",
                "value": "\n".join(beta_text) + "\n\n─────────────────────────────",
                "inline": False
            })
        
        # Add Top Trading Pairs field
        pairs_data = []
        for symbol in top_pairs[:5]:
            data = self.top_symbols_manager.get_symbol_data(symbol)
            if not data:
                continue
            
            ticker = data.get('ticker', {})
            price = float(ticker.get('last', 0))
            turnover = float(ticker.get('turnover24h', 0))
            change = float(ticker.get('change24h', 0))
            oi = float(ticker.get('openInterest', 0))
            
            emoji = "🟢" if change >= 0 else "🔴"
            pairs_data.append(
                f"{emoji} **{symbol}**\n"
                f"Price: ${price:,.2f} | 24h: {change:+.2f}%\n"
                f"Turn: {self._format_number(turnover)} | OI: {self._format_number(oi)}\n"
            )
        
        embed["fields"].append({
            "name": "💹 Top Trading Pairs",
            "value": "\n".join(pairs_data) + "\n─────────────────────────────",
            "inline": False
        })
        
        # Add Notable Market Movements
        gainers = []
        losers = []
        for symbol in top_pairs:
            data = self.top_symbols_manager.get_symbol_data(symbol)
            if not data:
                continue
            change = float(data.get('ticker', {}).get('change24h', 0))
            if change > 3:
                gainers.append((symbol, change))
            elif change < -3:
                losers.append((symbol, change))
        
        movements = []
        if gainers:
            gainers_text = "\n".join(
                f"🚀 {symbol}: +{change:.2f}%"
                for symbol, change in sorted(gainers, key=lambda x: x[1], reverse=True)[:5]
            )
            movements.append(f"**Top Gainers (>3%):**\n{gainers_text}")
        
        if losers:
            losers_text = "\n".join(
                f"📉 {symbol}: {change:.2f}%"
                for symbol, change in sorted(losers, key=lambda x: x[1])[:5]
            )
            movements.append(f"\n**Top Losers (<-3%):**\n{losers_text}")
        
        if movements:
            embed["fields"].append({
                "name": "⚡ Notable Movements",
                "value": "\n".join(movements) + "\n\n─────────────────────────────",
                "inline": False
            })
        
        # Add Risk Metrics field
        risk_metrics = self._calculate_risk_metrics(top_pairs)
        embed["fields"].append({
            "name": "⚠️ Risk Metrics",
            "value": (
                self._format_risk_metrics(risk_metrics) +
                "\n\n─────────────────────────────"
            ),
            "inline": False
        })
        
        # Add System Status
        embed["fields"].append({
            "name": "🖥️ System Status",
            "value": (
                "✓ Market Monitor: Active\n"
                "✓ Data Collection: Running\n"
                "✓ Analysis Engine: Ready\n"
                f"✓ Monitoring {len(top_pairs)} pairs"
            ),
            "inline": False
        })
        
        return {
            "username": "Virtuoso Market Monitor",
            "avatar_url": "https://raw.githubusercontent.com/virtuoso-dev/virtuoso/main/assets/logo.png",
            "embeds": [embed]
        }

    async def process_symbol(self, symbol: str) -> None:
        """Process a single symbol."""
        self.logger.debug(f"\n=== Processing Symbol: {symbol} ===")
        
        try:
            # Fetch real-time market data using correct method
            market_data = await self.fetch_market_data(symbol)
            
            if not market_data:
                self.logger.error(f"Failed to fetch market data for {symbol}")
                return
                
            # Get OHLCV data with caching
            ohlcv_data = await self._get_cached_ohlcv(symbol)
            
            # Update market_data with cached OHLCV
            market_data['ohlcv'] = ohlcv_data
            
            # Use cached OHLCV data for confluence analysis and signal generation
            await self.analyze_confluence_and_generate_signals(market_data)
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {str(e)}", exc_info=True)

    async def _get_cached_ohlcv(self, symbol: str) -> Dict[str, Any]:
        """Get OHLCV data with caching."""
        current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
        
        # Check cache
        if (symbol in self._ohlcv_cache and 
            current_time - self._last_ohlcv_update.get(symbol, 0) < self._cache_ttl):
            return self._ohlcv_cache[symbol]
        
        # Fetch all timeframes in one batch
        timeframes = {
            'base': '1',
            'ltf': '5', 
            'mtf': '30',
            'htf': '240'
        }
        
        ohlcv_data = {}
        raw_responses = {}  # Store raw responses
        
        for tf_name, interval in timeframes.items():
            # Add delay between requests
            await asyncio.sleep(0.5)
            
            # Fetch data
            raw_data = await self.exchange_manager._fetch_ohlcv(
                symbol=symbol,
                timeframe=interval
            )
            
            # Log raw response using helper
            self._log_raw_response(f'OHLCV {tf_name}', symbol, raw_data)
            
            # Store raw response
            raw_responses[tf_name] = raw_data
            
            # Convert to DataFrame
            if raw_data:
                df = pd.DataFrame(raw_data)
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                # Ensure timestamps are in UTC
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df.set_index('timestamp', inplace=True)
                ohlcv_data[tf_name] = {
                    'data': df,
                    'raw_response': raw_data  # Store raw response with processed data
                }
            else:
                self.logger.error(f"Failed to fetch {tf_name} timeframe data for {symbol}")
                return None
        
        fetch_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
        # Update cache with both processed and raw data
        self._ohlcv_cache[symbol] = {
            'processed': ohlcv_data,
            'raw_responses': raw_responses,
            'fetch_time': fetch_time,
            'fetch_time_formatted': self.timestamp_utility.format_utc_time(fetch_time * 1000)
        }
        self._last_ohlcv_update[symbol] = fetch_time
        
        return ohlcv_data

    def _needs_update(self, symbol: str, timeframe: str, interval: str) -> bool:
        """Check if timeframe needs updating based on interval."""
        if symbol not in self._last_ohlcv_update:
            return True
            
        current_time = self.timestamp_utility.get_utc_timestamp(as_ms=False)
        last_update = self._last_ohlcv_update.get(symbol, 0)
        
        # Convert interval to seconds
        interval_seconds = {
            '1': 60,
            '5': 300,
            '30': 1800,
            '240': 14400
        }.get(interval, 60)
        
        # Add small buffer to ensure we don't miss candles
        return (current_time - last_update) >= (interval_seconds * 0.8)

    def _merge_ohlcv_data(self, cached_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """Merge new OHLCV data with cached data."""
        if cached_data is None:
            return new_data
            
        if new_data is None:
            return cached_data
            
        # Combine and remove duplicates, keeping newer data
        merged = pd.concat([cached_data, new_data])
        merged = merged[~merged.index.duplicated(keep='last')]
        merged.sort_index(inplace=True)
        
        # Keep only the most recent 200 candles
        return merged.tail(200)

    def _process_market_data(self, market_data: Dict) -> None:
        """Process the market data"""
        try:
            symbol = market_data['symbol']
            
            # Update indicators
            self._update_indicators(market_data)
            
            # Generate signals
            signals = self._generate_signals(market_data)
            
            # Process alerts
            self._process_alerts(signals)
            
            self.logger.debug(f"Successfully processed market data for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}", exc_info=True)

    def _validate_timeframes(self, market_data: Dict[str, Any]) -> bool:
        """Validate timeframe data"""
        try:
            if 'timeframes' not in market_data:
                self.logger.error("Missing timeframes data")
                return False
                
            # Check using standardized names
            required_tfs = ['base', 'ltf', 'mtf', 'htf']
            for tf_name in required_tfs:
                config = self.TIMEFRAME_CONFIG[tf_name]
                if tf_name not in market_data['timeframes']:
                    self.logger.error(f"Missing {config['friendly_name']} timeframe")
                    return False
                    
                df = market_data['timeframes'][tf_name]
                if not isinstance(df, pd.DataFrame) or df.empty:
                    self.logger.error(f"Invalid {config['friendly_name']} DataFrame")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating timeframes: {str(e)}")
            return False

    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch market data for a symbol using the exchange manager
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict containing market data
        """
        try:
            # Extract pure symbol string if passed market object
            clean_symbol = symbol['symbol'] if isinstance(symbol, dict) else symbol
            
            self.logger.debug(f"\n=== Raw Market Data Fetch for {clean_symbol} at {self.timestamp_utility.format_utc_time(self.timestamp_utility.get_utc_timestamp())} ===")
            
            # Use exchange manager to fetch market data atomically
            raw_ohlcv, raw_ob, raw_trades = await asyncio.gather(
                self.exchange.fetch_ohlcv(clean_symbol),
                self.exchange_manager.get_orderbook(clean_symbol, "bybit"),
                self.exchange.fetch_trades(clean_symbol)
            )
            
            # Log raw responses using helper
            self._log_raw_response('OHLCV', clean_symbol, raw_ohlcv)
            self._log_raw_response('Orderbook', clean_symbol, raw_ob)
            self._log_raw_response('Trades', clean_symbol, raw_trades)
            
            fetch_time = self.timestamp_utility.get_utc_timestamp()
            market_data = {
                'symbol': clean_symbol,
                'timestamp': fetch_time,
                'ohlcv': self._standardize_ohlcv(raw_ohlcv),
                'orderbook': raw_ob,
                'trades': raw_trades,
                'raw_responses': {  # Store raw responses for debugging
                    'ohlcv': raw_ohlcv,
                    'orderbook': raw_ob,
                    'trades': raw_trades
                },
                'metadata': {
                    'fetch_time': self.timestamp_utility.format_utc_time(fetch_time),
                    'source': 'market_monitor'
                }
            }
            
            if not market_data:
                self.logger.error(f"Failed to fetch market data for {clean_symbol}")
                return None
                
            return market_data
            
        except Exception as e:
            self.logger.error(f"Data fetch failed for {clean_symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def analyze_confluence_and_generate_signals(self, market_data: Dict[str, Any]) -> None:
        """
        Analyze market data through confluence analyzer and generate trading signals
        
        Args:
            market_data: Dictionary containing all market data including:
                - symbol: Trading pair symbol
                - ticker: Latest ticker data
                - orderbook: Current orderbook
                - trades: Recent trades
                - ohlcv: OHLCV data for different timeframes
        """
        try:
            symbol = market_data['symbol']
            self.logger.debug(f"Running confluence analysis for {symbol}")
            
            # Add detailed logging of data structure
            self.logger.debug("=== Market Data Structure ===")
            self.logger.debug(f"Market data keys: {market_data.keys()}")
            self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")
            self.logger.debug(f"Base timeframe type: {type(market_data['ohlcv']['base'])}")
            self.logger.debug(f"Base timeframe structure: {market_data['ohlcv']['base']}")
            
            # Get analysis from confluence analyzer
            try:
                analysis_result = await self.confluence_analyzer.analyze(market_data)
            except DataUnavailableError as e:
                self.logger.error(f"Aborting analysis: {str(e)}")
                return
            except Exception as e:
                self.logger.warning(f"No confluence analysis result for {symbol}")
                analysis_result = self._get_default_scores(symbol)

            # Generate signals based on analysis
            signals = await self.signal_generator.generate_signals(
                symbol=symbol,
                market_data=market_data,
                analysis=analysis_result
            )

            # Process any signals through alert manager
            if signals:
                self.logger.info(f"Generated signals for {symbol}: {signals}")
                await self.alert_manager.process_signals(signals)
            else:
                self.logger.debug(f"No signals generated for {symbol}")

            # Store analysis results
            await self.database_client.store_analysis(
                symbol=symbol,
                analysis=analysis_result,
                signals=signals
            )

        except Exception as e:
            self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)
            # Use default scores on error
            analysis_result = self._get_default_scores(market_data.get('symbol'))

    async def fetch_trade_history(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch required trade history."""
        try:
            # Fetch maximum allowed trades
            raw_trades = await self.exchange_manager.fetch_recent_trades(symbol, limit=1000)
            
            # Log raw response using helper
            self._log_raw_response('Trade History', symbol, raw_trades)
            
            if len(raw_trades) < 1000:
                self.logger.warning(f"Could only fetch {len(raw_trades)} trades, less than required 1000")
            
            fetch_time = self._get_utc_timestamp()
            return {
                'trades': raw_trades,
                'raw_response': raw_trades,  # Store raw response
                'fetch_time': fetch_time,
                'fetch_time_formatted': self._format_utc_time(fetch_time)
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching trade history: {str(e)}")
            return []

    def _get_symbol_string(self, symbol: Union[str, dict]) -> str:
        """Extract symbol string from either string or symbol dict.
        
        Args:
            symbol: Symbol string or dictionary
            
        Returns:
            Symbol string
            
        Raises:
            ValueError: If symbol is invalid
        """
        if isinstance(symbol, dict):
            if 'symbol' not in symbol:
                raise ValueError("Invalid symbol dictionary - missing 'symbol' key")
            return symbol['symbol']
        return str(symbol)

    async def fetch_market_data(self, symbol: Union[str, dict], use_cache: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch market data for a symbol, with optional caching."""
        try:
            symbol_str = self._get_symbol_string(symbol)
            
            fetch_start = self.timestamp_utility.get_utc_timestamp()
            
            # Check cache first if caching is enabled
            if use_cache and not force_refresh and self._market_data_cache.get(symbol_str):
                cache_entry = self._market_data_cache[symbol_str]
                cache_age = self.timestamp_utility.get_age_seconds(cache_entry.get('timestamp', 0))
                
                if cache_age < self._cache_ttl:
                    self.logger.debug(f"Using cached market data for {symbol_str} (age: {cache_age:.2f}s)")
                    return cache_entry['data']
            
            self.logger.debug(f"\n=== Fetching Market Data for {symbol_str} at {self.timestamp_utility.format_utc_time(fetch_start)} ===")
            
            # Fetch OHLCV data
            raw_ohlcv = await self._fetch_with_retry("fetch_ohlcv", symbol_str, timeframe="1m", limit=1000)
            self.logger.debug(f"\n=== Raw OHLCV Response for {symbol_str} ===")
            
            if isinstance(raw_ohlcv, list):
                self.logger.debug(f"OHLCV data is a list with {len(raw_ohlcv)} items")
            else:
                self.logger.debug(f"OHLCV data type: {type(raw_ohlcv)}")
                if isinstance(raw_ohlcv, dict):
                    self.logger.debug(f"OHLCV keys: {list(raw_ohlcv.keys())}")
            
            self.logger.debug("=== End Raw OHLCV Response ===\n")
            
            # Fetch orderbook data
            raw_orderbook = await self._fetch_with_retry("get_orderbook", symbol_str, limit=50)
            self.logger.debug(f"\n=== Raw Orderbook Response for {symbol_str} ===")
            
            if isinstance(raw_orderbook, dict) and 'bids' in raw_orderbook and 'asks' in raw_orderbook:
                bids = raw_orderbook['bids']
                asks = raw_orderbook['asks']
                
                # Log orderbook summary
                self.logger.debug(f"Bids: {len(bids)} levels")
                if len(bids) > 0:
                    self.logger.debug("  Top 3 bids:")
                    for i, bid in enumerate(bids[:3]):
                        self.logger.debug(f"    {i+1}. Price: {bid[0]}, Qty: {bid[1]}")
                    total_bid_qty = sum(bid[1] for bid in bids)
                    self.logger.debug(f"  Total bid quantity: {total_bid_qty}")
                
                self.logger.debug(f"Asks: {len(asks)} levels")
                if len(asks) > 0:
                    self.logger.debug("  Top 3 asks:")
                    for i, ask in enumerate(asks[:3]):
                        self.logger.debug(f"    {i+1}. Price: {ask[0]}, Qty: {ask[1]}")
                    total_ask_qty = sum(ask[1] for ask in asks)
                    self.logger.debug(f"  Total ask quantity: {total_ask_qty}")
                
                if len(bids) > 0 and len(asks) > 0:
                    best_bid = bids[0][0]
                    best_ask = asks[0][0]
                    spread = best_ask - best_bid
                    spread_pct = (spread / best_bid) * 100
                    self.logger.debug(f"\nBid-ask spread: {spread} ({spread_pct:.4f}%)")
                    self.logger.debug(f"Best bid: {best_bid}, Best ask: {best_ask}")
            else:
                self.logger.debug(f"Orderbook data type: {type(raw_orderbook)}")
                if isinstance(raw_orderbook, dict):
                    self.logger.debug(f"Orderbook keys: {list(raw_orderbook.keys())}")
            
            self.logger.debug("=== End Raw Orderbook Response ===\n")
            
            # Fetch trades data
            raw_trades = await self._fetch_with_retry("fetch_trades", symbol_str, limit=1000)
            self.logger.debug(f"\n=== Raw Trades Response for {symbol_str} ===")
            
            # Log trades summary (truncated for brevity)
            self.logger.debug("=== End Raw Trades Response ===\n")

            # Process orderbook data
            processed_orderbook = await self.process_orderbook(symbol_str, raw_orderbook)
            
            # Standardize OHLCV data
            standardized_ohlcv = self._standardize_ohlcv(raw_ohlcv)
            
            # Create market data structure
            market_data = {
                'symbol': symbol_str,
                'timestamp': self.timestamp_utility.get_utc_timestamp(),
                'ohlcv': standardized_ohlcv,
                'orderbook': processed_orderbook,
                'trades': raw_trades
            }
            
            # Add additional market info if available
            if self.exchange:
                ticker = None
                # Try different ticker method names with fallbacks
                try:
                    # Try get_ticker first (Bybit's method name)
                    ticker = await self._fetch_with_retry("get_ticker", symbol_str)
                except AttributeError:
                    try:
                        # Fall back to fetch_tickers (plural) if get_ticker doesn't exist
                        tickers_response = await self._fetch_with_retry("fetch_tickers", [symbol_str])
                        ticker = tickers_response.get(symbol_str, {}) if isinstance(tickers_response, dict) else {}
                    except AttributeError:
                        try:
                            # Finally try original fetch_ticker method
                            ticker = await self._fetch_with_retry("fetch_ticker", symbol_str)
                        except AttributeError:
                            self.logger.warning(f"No ticker method available for {self.exchange_id}")
                            ticker = {}
                
                if ticker:
                    market_data['ticker'] = ticker
            
                # Try to get funding rate for perpetual contracts
                try:
                    funding_rate = await self._fetch_with_retry("get_funding_rate", symbol_str)
                    if funding_rate:
                        market_data['funding_rate'] = funding_rate
                except Exception as e:
                    self.logger.debug(f"Funding rate not available for {symbol_str}: {str(e)}")
            
            # Cache the result
            self._market_data_cache[symbol_str] = {
                'timestamp': self.timestamp_utility.get_utc_timestamp(),
                'data': market_data
            }
            
            fetch_end = self.timestamp_utility.get_utc_timestamp()
            fetch_duration = (fetch_end - fetch_start) / 1000
            self.logger.debug(f"Market data fetch for {symbol_str} completed in {fetch_duration:.2f}s")
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {self._get_symbol_string(symbol)}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}

    def _standardize_ohlcv(self, raw_ohlcv) -> Dict[str, Any]:
        """
        Standardize OHLCV data from the exchange into a consistent format.
        
        Args:
            raw_ohlcv: The raw OHLCV data from the exchange
            
        Returns:
            Dict containing standardized OHLCV data with timeframes
        """
        try:
            if not raw_ohlcv or len(raw_ohlcv) == 0:
                self.logger.warning("Empty OHLCV data received")
                return {
                    'base': [],
                    'ltf': [],
                    'mtf': [],
                    'htf': []
                }
                
            # Convert to dataframe if it's a list of lists or dict
            if isinstance(raw_ohlcv, list):
                if len(raw_ohlcv) == 0:
                    return {
                        'base': [],
                        'ltf': [],
                        'mtf': [],
                        'htf': []
                    }
                    
                # Handle different formats from exchanges
                if isinstance(raw_ohlcv[0], list):
                    # Format: [timestamp, open, high, low, close, volume]
                    df = pd.DataFrame(raw_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                elif isinstance(raw_ohlcv[0], dict):
                    # Common dict format from exchanges
                    df = pd.DataFrame(raw_ohlcv)
                    
                    # Rename columns if needed
                    column_mapping = {
                        't': 'timestamp',
                        'time': 'timestamp',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume'
                    }
                    
                    df = df.rename(columns={col: new_col for col, new_col in column_mapping.items() if col in df.columns})
            elif isinstance(raw_ohlcv, dict):
                # Some exchanges return dict with timeframes
                timeframes = {}
                for tf_key, candles in raw_ohlcv.items():
                    if isinstance(candles, list) and len(candles) > 0:
                        tf_df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        timeframes[tf_key] = tf_df.to_dict('records')
                
                if timeframes:
                    return timeframes
                
                # Handle other dict formats
                self.logger.warning(f"Unsupported OHLCV dict format: {list(raw_ohlcv.keys())}")
                return {
                    'base': [],
                    'ltf': [],
                    'mtf': [],
                    'htf': []
                }
            else:
                self.logger.warning(f"Unsupported OHLCV data type: {type(raw_ohlcv)}")
                return {
                    'base': [],
                    'ltf': [],
                    'mtf': [],
                    'htf': []
                }
            
            # Ensure timestamp is numeric
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_numeric(df['timestamp'])
            
            # Sort by timestamp
            if 'timestamp' in df.columns:
                df = df.sort_values('timestamp')
            
            # Convert numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col])
            
            # Create base timeframe data
            base_data = df.to_dict('records')
            
            # Create other timeframes if needed
            # For now, we'll return the same data for all timeframes
            return {
                'base': base_data,
                'ltf': base_data,  # In a real implementation, you would resample these
                'mtf': base_data,
                'htf': base_data
            }
            
        except Exception as e:
            self.logger.error(f"Error standardizing OHLCV data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {
                'base': [],
                'ltf': [],
                'mtf': [],
                'htf': []
            }

    async def _start_monitoring_tasks(self) -> None:
        """Initialize and start monitoring tasks."""
        try:
            self.logger.info("Starting monitoring tasks...")
            
            # Create monitoring task
            self._monitoring_task = asyncio.create_task(self._run_monitoring_loop())
            
            # Start metrics manager if available
            if self.metrics_manager:
                await self.metrics_manager.start()
                
            # Start alert manager if available
            if self.alert_manager:
                await self.alert_manager.start()
                
            self.logger.info("Monitoring tasks started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring tasks: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    def _log_raw_response(self, data_type: str, symbol: str, data: Any) -> None:
        """Enhanced logging for raw API responses with detailed structure analysis.
        
        Args:
            data_type: Type of data (OHLCV, Orderbook, Trades)
            symbol: Symbol being processed
            data: Raw response data
        """
        try:
            self.logger.debug(f"\n=== Raw {data_type} Response for {symbol} ===")
            
            # Handle different data types appropriately
            if data_type == 'OHLCV':
                self._log_ohlcv_data(data)
            elif data_type == 'Orderbook':
                self._log_orderbook_data(data)
            elif data_type == 'Trades':
                self._log_trades_data(data)
            else:
                # Generic logging for other data types
                if isinstance(data, dict):
                    self.logger.debug(f"Dictionary with {len(data)} keys: {list(data.keys())}")
                    for key in list(data.keys())[:5]:  # Show first 5 keys
                        value = data[key]
                        self.logger.debug(f"  {key}: {type(value)} {self._format_sample(value)}")
                elif isinstance(data, list):
                    self.logger.debug(f"List with {len(data)} items")
                    for i, item in enumerate(data[:3]):  # Show first 3 items
                        self.logger.debug(f"  [{i}]: {type(item)} {self._format_sample(item)}")
                elif isinstance(data, pd.DataFrame):
                    self.logger.debug(f"DataFrame with shape {data.shape}")
                    self.logger.debug(f"Columns: {list(data.columns)}")
                    if not data.empty:
                        self.logger.debug(f"Sample:\n{data.head(2)}")
                else:
                    self.logger.debug(f"Type: {type(data)}")
                    self.logger.debug(f"Value: {self._format_sample(data)}")
            
            self.logger.debug(f"=== End Raw {data_type} Response ===\n")
        except Exception as e:
            self.logger.warning(f"Error logging raw {data_type} response: {str(e)}")

    def _log_ohlcv_data(self, data: Any) -> None:
        """Log OHLCV data with detailed analysis.
        
        Args:
            data: OHLCV data to log
        """
        if isinstance(data, dict):
            # Handle timeframe dictionary
            self.logger.debug(f"OHLCV contains {len(data)} timeframes: {list(data.keys())}")
            
            for tf, tf_data in data.items():
                self.logger.debug(f"\nTimeframe: {tf}")
                
                if isinstance(tf_data, pd.DataFrame):
                    self._log_ohlcv_dataframe(tf_data)
                elif isinstance(tf_data, dict) and 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                    self._log_ohlcv_dataframe(tf_data['data'])
                else:
                    self.logger.debug(f"  Type: {type(tf_data)}")
        
        elif isinstance(data, pd.DataFrame):
            # Handle direct DataFrame
            self._log_ohlcv_dataframe(data)
        
        elif isinstance(data, list):
            # Handle list format (common in raw API responses)
            self.logger.debug(f"OHLCV data is a list with {len(data)} items")
            
            if data:
                # Check first item to determine format
                first_item = data[0]
                if isinstance(first_item, list):
                    self.logger.debug(f"List format with {len(first_item)} columns")
                    self.logger.debug(f"First candle: {first_item}")
                    
                    # Try to convert to DataFrame for better analysis
                    try:
                        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        if len(first_item) == len(columns):
                            df = pd.DataFrame(data, columns=columns)
                            self._log_ohlcv_dataframe(df)
                    except Exception as e:
                        self.logger.debug(f"Could not convert to DataFrame: {str(e)}")
    
    def _log_ohlcv_dataframe(self, df: pd.DataFrame) -> None:
        """Log details of OHLCV DataFrame.
        
        Args:
            df: DataFrame to log
        """
        self.logger.debug(f"  Shape: {df.shape}")
        self.logger.debug(f"  Columns: {list(df.columns)}")
        self.logger.debug(f"  Index type: {type(df.index)}")
        
        if not df.empty:
            # Show basic statistics
            self.logger.debug("\n  Basic statistics:")
            stats = df.describe().transpose()
            self.logger.debug(f"{stats}")
            
            # Check for NaN values
            nan_count = df.isna().sum().sum()
            if nan_count > 0:
                self.logger.debug(f"\n  Contains {nan_count} NaN values")
                self.logger.debug(f"  NaN counts by column:\n{df.isna().sum()}")
            
            # Log time range
            if hasattr(df, 'index') and isinstance(df.index, pd.DatetimeIndex):
                self.logger.debug(f"\n  Time range: {df.index.min()} to {df.index.max()}")
                self.logger.debug(f"  Duration: {df.index.max() - df.index.min()}")
            
            # Show first and last candles
            self.logger.debug("\n  First candle:")
            self.logger.debug(f"{df.iloc[0]}")
            self.logger.debug("\n  Last candle:")
            self.logger.debug(f"{df.iloc[-1]}")
    
    def _log_orderbook_data(self, data: Any) -> None:
        """Log orderbook data with detailed analysis.
        
        Args:
            data: Orderbook data to log
        """
        if not isinstance(data, dict):
            self.logger.debug(f"Orderbook is not a dictionary: {type(data)}")
            return
        
        # Check for required fields
        required_fields = ['bids', 'asks']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            self.logger.debug(f"Orderbook missing required fields: {missing_fields}")
        
        # Log basic statistics
        if 'bids' in data and isinstance(data['bids'], list):
            bids = data['bids']
            self.logger.debug(f"Bids: {len(bids)} levels")
            if bids:
                self.logger.debug(f"  Top 3 bids:")
                for i, bid in enumerate(bids[:3]):
                    self.logger.debug(f"    {i+1}. Price: {bid[0]}, Qty: {bid[1]}")
                
                # Calculate bid sum
                bid_qty_sum = sum(bid[1] for bid in bids)
                self.logger.debug(f"  Total bid quantity: {bid_qty_sum}")
        
        if 'asks' in data and isinstance(data['asks'], list):
            asks = data['asks']
            self.logger.debug(f"Asks: {len(asks)} levels")
            if asks:
                self.logger.debug(f"  Top 3 asks:")
                for i, ask in enumerate(asks[:3]):
                    self.logger.debug(f"    {i+1}. Price: {ask[0]}, Qty: {ask[1]}")
                
                # Calculate ask sum
                ask_qty_sum = sum(ask[1] for ask in asks)
                self.logger.debug(f"  Total ask quantity: {ask_qty_sum}")
        
        # Calculate bid-ask spread if possible
        if 'bids' in data and 'asks' in data and data['bids'] and data['asks']:
            best_bid = data['bids'][0][0]
            best_ask = data['asks'][0][0]
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100
            
            self.logger.debug(f"\nBid-ask spread: {spread} ({spread_pct:.4f}%)")
            self.logger.debug(f"Best bid: {best_bid}, Best ask: {best_ask}")
    
    def _log_trades_data(self, data: Any) -> None:
        """Log trades data with detailed analysis.
        
        Args:
            data: Trades data to log
        """
        if isinstance(data, list):
            self.logger.debug(f"Trades: {len(data)} trades")
            
            if not data:
                return
            
            # Show sample trades
            self.logger.debug("\nSample trades:")
            for i, trade in enumerate(data[:3]):
                self.logger.debug(f"  Trade {i+1}: {trade}")
            
            # Try to calculate some statistics
            try:
                # Extract prices and volumes more efficiently
                prices = []
                volumes = []
                for trade in data:
                    if 'price' in trade:
                        prices.append(float(trade.get('price', 0)))
                    if 'amount' in trade or 'quantity' in trade:
                        volumes.append(float(trade.get('amount', trade.get('quantity', 0))))
                
                if prices:
                    # Use numpy for efficient statistics calculation
                    prices_array = np.array(prices)
                    avg_price = np.mean(prices_array)
                    min_price = np.min(prices_array)
                    max_price = np.max(prices_array)
                    
                    self.logger.debug(f"\nPrice statistics:")
                    self.logger.debug(f"  Min: {min_price}, Max: {max_price}, Avg: {avg_price:.4f}")
                
                if volumes:
                    # Use numpy for efficient volume statistics
                    volumes_array = np.array(volumes)
                    total_volume = np.sum(volumes_array)
                    avg_volume = np.mean(volumes_array)
                    
                    self.logger.debug(f"\nVolume statistics:")
                    self.logger.debug(f"  Total: {total_volume}, Avg: {avg_volume:.4f}")
                
                # Count buy vs sell trades if side is available
                if data and len(data) > 0 and 'side' in data[0]:
                    # Count trades by side in one pass through the data
                    buy_count = 0
                    sell_count = 0
                    for trade in data:
                        side = trade.get('side')
                        if side == 'buy':
                            buy_count += 1
                        elif side == 'sell':
                            sell_count += 1
                
                    self.logger.debug(f"\nTrade directions:")
                    self.logger.debug(f"  Buy: {buy_count} ({buy_count/len(data)*100:.1f}%)")
                    self.logger.debug(f"  Sell: {sell_count} ({sell_count/len(data)*100:.1f}%)")
            
            except Exception as e:
                self.logger.debug(f"Error calculating trade statistics: {str(e)}")
        
        elif isinstance(data, pd.DataFrame):
            self.logger.debug(f"Trades DataFrame with shape {data.shape}")
            
            if data.empty:
                return
            
            self.logger.debug(f"Columns: {list(data.columns)}")
            self.logger.debug(f"\nSample trades:\n{data.head(3)}")
            
            # Show basic statistics
            try:
                if 'price' in data.columns:
                    self.logger.debug(f"\nPrice statistics:")
                    self.logger.debug(f"  Min: {data['price'].min()}, Max: {data['price'].max()}, "
                                     f"Avg: {data['price'].mean():.4f}")
                
                if 'amount' in data.columns:
                    self.logger.debug(f"\nVolume statistics:")
                    self.logger.debug(f"  Total: {data['amount'].sum()}, Avg: {data['amount'].mean():.4f}")
                
                # Count buy vs sell trades if side is available
                if 'side' in data.columns:
                    counts = data['side'].value_counts()
                    self.logger.debug(f"\nTrade directions:\n{counts}")
            
            except Exception as e:
                self.logger.debug(f"Error calculating trade statistics: {str(e)}")
    
    def _format_sample(self, value: Any) -> str:
        """Format a sample of a value for logging.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted string representation
        """
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        elif isinstance(value, dict):
            return f"{{...}} with {len(value)} keys"
        elif isinstance(value, list):
            return f"[...] with {len(value)} items"
        elif isinstance(value, pd.DataFrame):
            return f"DataFrame with shape {value.shape}"
        else:
            return str(type(value))
    
    def visualize_market_data(self, market_data: Dict[str, Any], output_dir: Optional[str] = None) -> Dict[str, str]:
        """Generate visualizations for market data components.
        
        Args:
            market_data: Market data dictionary
            output_dir: Optional directory to save visualizations
            
        Returns:
            Dictionary mapping data types to base64-encoded PNG images
        """
        try:
            operation = self.metrics_manager.start_operation("visualize_market_data")
            
            visualizations = {}
            symbol = market_data.get('symbol_str', 'unknown')
            
            # Create output directory if specified
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            
            # Visualize OHLCV data if available
            if 'ohlcv' in market_data and market_data['ohlcv']:
                ohlcv_vis = self._visualize_ohlcv(market_data['ohlcv'], symbol)
                visualizations['ohlcv'] = ohlcv_vis
                
                if output_dir:
                    self._save_visualization(ohlcv_vis, output_dir, f"{symbol}_ohlcv.png")
            
            # Visualize orderbook if available
            if 'orderbook' in market_data and market_data['orderbook']:
                orderbook_vis = self._visualize_orderbook(market_data['orderbook'], symbol)
                visualizations['orderbook'] = orderbook_vis
                
                if output_dir:
                    self._save_visualization(orderbook_vis, output_dir, f"{symbol}_orderbook.png")
            
            # Visualize trades if available
            if 'trades' in market_data and market_data['trades']:
                trades_vis = self._visualize_trades(market_data['trades'], symbol)
                visualizations['trades'] = trades_vis
                
                if output_dir:
                    self._save_visualization(trades_vis, output_dir, f"{symbol}_trades.png")
            
            self.metrics_manager.end_operation(operation)
            return visualizations
            
        except Exception as e:
            self.logger.error(f"Error visualizing market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            if 'operation' in locals():
                self.metrics_manager.end_operation(operation, success=False)
                
            return {}
    
    def _visualize_ohlcv(self, ohlcv_data: Dict[str, Any], symbol: str) -> str:
        """Generate OHLCV visualization.
        
        Args:
            ohlcv_data: OHLCV data dictionary
            symbol: Trading pair symbol
        
        Returns:
            Base64-encoded PNG image
        """
        # Create figure with 2 subplots (price and volume)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f"OHLCV Data for {symbol}", fontsize=16)
        
        # Get the base timeframe data
        df = None
        
        if isinstance(ohlcv_data, dict):
            # Try to get base timeframe first, then any available timeframe
            timeframe_priority = ['base', 'ltf', 'mtf', 'htf']
            
            for tf in timeframe_priority:
                if tf in ohlcv_data:
                    tf_data = ohlcv_data[tf]
                    
                    if isinstance(tf_data, pd.DataFrame) and not tf_data.empty:
                        df = tf_data
                        break
                    elif isinstance(tf_data, dict) and 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                        df = tf_data['data']
                        break
        elif isinstance(ohlcv_data, pd.DataFrame):
            df = ohlcv_data
        
        if df is None or df.empty:
            self.logger.warning(f"No valid OHLCV data for visualization")
            # Create an empty visualization
            fig.text(0.5, 0.5, "No OHLCV data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # Ensure DataFrame has datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                # Convert timestamp column to datetime
                df.set_index('timestamp', inplace=True)
                df.index = pd.to_datetime(df.index, unit='ms')
            else:
                # Create a dummy index
                df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='T')
        
        # Create candlestick chart
        ax1.set_title(f"Price (Timeframe: {getattr(df, 'timeframe', 'unknown')})")
        
        # Calculate candlestick colors
        colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]
        
        # Plot candlesticks
        for i, (timestamp, row) in enumerate(df.iterrows()):
            # Draw body
            ax1.plot([i, i], [row['open'], row['close']], color=colors[i], linewidth=3)
            # Draw wicks
            ax1.plot([i, i], [row['low'], row['high']], color=colors[i], linewidth=1)
        
        # Set x-axis labels
        ax1.set_xticks(range(0, len(df), max(1, len(df) // 10)))
        ax1.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])
        
        # Add volume subplot
        ax2.set_title("Volume")
        ax2.bar(range(len(df)), df['volume'], color=colors, alpha=0.7)
        
        # Set x-axis labels for volume chart
        ax2.set_xticks(range(0, len(df), max(1, len(df) // 10)))
        ax2.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _visualize_orderbook(self, orderbook_data: Dict[str, Any], symbol: str) -> str:
        """Generate orderbook visualization.
        
        Args:
            orderbook_data: Orderbook data dictionary
            symbol: Trading pair symbol
        
        Returns:
            Base64-encoded PNG image
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.suptitle(f"Orderbook for {symbol}", fontsize=16)
        
        # Check if orderbook data is valid
        if not isinstance(orderbook_data, dict) or 'bids' not in orderbook_data or 'asks' not in orderbook_data:
            self.logger.warning(f"Invalid orderbook data for visualization")
            # Create an empty visualization
            fig.text(0.5, 0.5, "No orderbook data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        bids = orderbook_data['bids']
        asks = orderbook_data['asks']
        
        if not bids or not asks:
            self.logger.warning(f"Empty bids or asks in orderbook")
            # Create an empty visualization
            fig.text(0.5, 0.5, "Empty orderbook data", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # Extract price and quantity
        bid_prices = [bid[0] for bid in bids[:20]]  # Limit to 20 levels
        bid_quantities = [bid[1] for bid in bids[:20]]
        ask_prices = [ask[0] for ask in asks[:20]]
        ask_quantities = [ask[1] for ask in asks[:20]]
        
        # Cumulative quantities - use numpy's cumsum for efficiency
        bid_cumulative = np.cumsum(bid_quantities).tolist()
        ask_cumulative = np.cumsum(ask_quantities).tolist()
        
        # Plot bids (cumulative)
        ax.step(bid_prices, bid_cumulative, where='post', color='green', label='Bids')
        ax.fill_between(bid_prices, bid_cumulative, step='post', alpha=0.2, color='green')
        
        # Plot asks (cumulative)
        ax.step(ask_prices, ask_cumulative, where='post', color='red', label='Asks')
        ax.fill_between(ask_prices, ask_cumulative, step='post', alpha=0.2, color='red')
        
        # Set labels and legend
        ax.set_xlabel('Price')
        ax.set_ylabel('Cumulative Quantity')
        ax.legend()
        
        # Calculate and show spread
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100
        
        ax.axvline(x=best_bid, color='green', linestyle='--', alpha=0.7)
        ax.axvline(x=best_ask, color='red', linestyle='--', alpha=0.7)
        
        ax.text(0.5, 0.02, f"Spread: {spread:.8f} ({spread_pct:.4f}%)", 
                transform=ax.transAxes, ha='center', fontsize=10, 
                bbox=dict(facecolor='white', alpha=0.8))
        
        # Format y-axis with comma separators for large numbers
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _visualize_trades(self, trades_data: Any, symbol: str) -> str:
        """Generate trades visualization.
        
        Args:
            trades_data: Trades data
            symbol: Trading pair symbol
            
        Returns:
            Base64-encoded PNG image
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10))
        fig.suptitle(f"Recent Trades for {symbol}", fontsize=16)
        
        # Convert trades to DataFrame if needed
        if isinstance(trades_data, list):
            try:
                # Extract relevant fields
                trade_list = []
                for trade in trades_data:
                    trade_dict = {
                        'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),
                        'price': float(trade.get('price', 0)),
                        'amount': float(trade.get('amount', trade.get('quantity', 0))),
                        'side': trade.get('side', 'unknown')
                    }
                    trade_list.append(trade_dict)
                
                df = pd.DataFrame(trade_list)
                
                # Sort by timestamp
                if 'timestamp' in df.columns:
                    df.sort_values('timestamp', inplace=True)
            except Exception as e:
                self.logger.warning(f"Error converting trades to DataFrame: {str(e)}")
                fig.text(0.5, 0.5, "Error processing trades data", ha='center', va='center')
                return self._fig_to_base64(fig)
        elif isinstance(trades_data, pd.DataFrame):
            df = trades_data.copy()
            
            # Ensure columns exist
            required_cols = ['timestamp', 'price', 'amount', 'side']
            for col in required_cols:
                if col not in df.columns:
                    self.logger.warning(f"Missing column {col} in trades DataFrame")
                    fig.text(0.5, 0.5, f"Missing required column: {col}", ha='center', va='center')
                    return self._fig_to_base64(fig)
        else:
            self.logger.warning(f"Invalid trades data type: {type(trades_data)}")
            fig.text(0.5, 0.5, "Invalid trades data format", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        if df.empty:
            fig.text(0.5, 0.5, "No trades data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # 1. Price over time
        ax1.set_title("Price over time")
        ax1.plot(df['timestamp'], df['price'], marker='.', linestyle='-', alpha=0.7)
        
        # Color points by trade side if available
        if 'side' in df.columns:
            buy_mask = df['side'] == 'buy'
            sell_mask = df['side'] == 'sell'
            
            ax1.scatter(df.loc[buy_mask, 'timestamp'], df.loc[buy_mask, 'price'], 
                        color='green', s=20, alpha=0.7, label='Buy')
            ax1.scatter(df.loc[sell_mask, 'timestamp'], df.loc[sell_mask, 'price'], 
                        color='red', s=20, alpha=0.7, label='Sell')
            ax1.legend()
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # 2. Trade sizes
        ax2.set_title("Trade Sizes")
        ax2.bar(range(len(df)), df['amount'], color='blue', alpha=0.7)
        ax2.set_ylabel("Amount")
        ax2.set_xlabel("Trade Number")
        
        # 3. Buy vs Sell volumes
        ax3.set_title("Buy vs Sell Volume")
        
        if 'side' in df.columns:
            # Group by side and sum amounts
            volume_by_side = df.groupby('side')['amount'].sum()
            
            # Create pie chart
            colors = {'buy': 'green', 'sell': 'red'}
            pie_colors = [colors.get(side, 'gray') for side in volume_by_side.index]
            
            ax3.pie(volume_by_side, labels=volume_by_side.index, autopct='%1.1f%%', 
                   startangle=90, colors=pie_colors)
            ax3.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        else:
            ax3.text(0.5, 0.5, "No side information available", ha='center', va='center', transform=ax3.transAxes)
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convert Matplotlib figure to base64-encoded string.
        
        Args:
            fig: Matplotlib figure
            
        Returns:
            Base64-encoded PNG image
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return img_str
    
    def _save_visualization(self, base64_img: str, output_dir: str, filename: str) -> None:
        """Save base64-encoded visualization to file.
        
        Args:
            base64_img: Base64-encoded image
            output_dir: Output directory
            filename: Output filename
        """
        try:
            img_data = base64.b64decode(base64_img)
            output_path = Path(output_dir) / filename
            
            with open(output_path, 'wb') as f:
                f.write(img_data)
                
            self.logger.debug(f"Saved visualization to {output_path}")
            
        except Exception as e:
            self.logger.warning(f"Error saving visualization: {str(e)}")

    def validate_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate market data for completeness and freshness.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Validation result dictionary
        """
        result = {
            'overall_valid': True,
            'ohlcv_valid': True,
            'orderbook_valid': True,
            'trades_valid': True,
            'details': {}
        }
        
        # Record validation operation
        operation = self.metrics_manager.start_operation("validate_market_data")
        
        try:
            # Configure logging verbosity
            verbose = self.debug_config.get('verbose_validation', False)
            details = {}
            
            # Validate OHLCV data
            ohlcv_valid = True
            ohlcv_details = {}
            
            for tf_key, df in market_data['ohlcv'].items():
                tf_valid = True
                tf_details = {}
                
                # Check if data is a valid DataFrame
                if not isinstance(df, pd.DataFrame):
                    # Try to convert to DataFrame if it's a list
                    if isinstance(df, list):
                        if not df:  # Empty list
                            tf_valid = False
                            tf_details['error'] = "Empty data list"
                        else:
                            try:
                                # Try to convert list to DataFrame
                                df = pd.DataFrame(df)
                                # Update the market data with the DataFrame
                                market_data['ohlcv'][tf_key] = df
                            except Exception as e:
                                tf_valid = False
                                tf_details['error'] = f"Could not convert list to DataFrame: {str(e)}"
                    else:
                        tf_valid = False
                        tf_details['error'] = f"Invalid data type: {type(df)}"
                
                # Now check if DataFrame is empty (only if it's a DataFrame now)
                if isinstance(df, pd.DataFrame) and df.empty:
                    tf_valid = False
                    tf_details['error'] = "Empty DataFrame"
                elif isinstance(df, pd.DataFrame):
                    # Check minimum number of candles
                    min_candles = self.validation_config.get('min_ohlcv_candles', 20)
                    if len(df) < min_candles:
                        tf_valid = False
                        tf_details['candle_count_issue'] = f"Only {len(df)} candles, minimum {min_candles} required"
                    
                    # Check freshness of newest candle
                    if isinstance(df.index, pd.DatetimeIndex):
                        latest_ts = df.index.max()
                        # Ensure latest_ts has timezone info if it doesn't already
                        if latest_ts.tzinfo is None:
                            latest_ts = latest_ts.tz_localize('UTC')
                    else:
                        # If index is not datetime, try to use last row's timestamp
                        latest_ts = pd.to_datetime(df.iloc[-1].name, unit='ms').tz_localize('UTC')
                    
                    max_age_seconds = self.validation_config.get('max_ohlcv_age_seconds', 300)
                    age_seconds = (pd.Timestamp.now(tz='UTC') - latest_ts).total_seconds()
                    
                    if age_seconds > max_age_seconds:
                        tf_valid = False
                        tf_details['freshness_issue'] = f"Newest candle is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                
                ohlcv_details[tf_key] = {
                    'valid': tf_valid,
                    'details': tf_details
                }
                
                if not tf_valid:
                    ohlcv_valid = False
            
            result['ohlcv_valid'] = ohlcv_valid
            details['ohlcv'] = ohlcv_details
            
            # Validate orderbook
            orderbook_valid = True
            orderbook_details = {}
            
            if market_data['orderbook'] is None:
                orderbook_valid = False
                orderbook_details['error'] = "No orderbook data"
            else:
                # Check the structure of orderbook data which might be nested in result
                orderbook_data = market_data['orderbook']
                
                # Handle case where orderbook is in result.b (bids) and result.a (asks) format
                if 'result' in orderbook_data and isinstance(orderbook_data['result'], dict):
                    result_data = orderbook_data['result']
                    if 'b' in result_data and 'a' in result_data:
                        # Extract bids and asks from the result structure
                        orderbook_data['bids'] = result_data.get('b', [])
                        orderbook_data['asks'] = result_data.get('a', [])
                
                # Now check for bids and asks
                if 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                    orderbook_valid = False
                    orderbook_details['structure_issue'] = f"Missing bids or asks fields. Keys: {list(orderbook_data.keys())}"
                else:
                    # Check minimum number of levels
                    min_levels = self.validation_config.get('min_orderbook_levels', 5)
                    bid_length = len(orderbook_data['bids']) if isinstance(orderbook_data['bids'], list) else 0
                    ask_length = len(orderbook_data['asks']) if isinstance(orderbook_data['asks'], list) else 0
                    
                    if (bid_length < min_levels or ask_length < min_levels):
                        orderbook_valid = False
                        orderbook_details['depth_issue'] = (
                            f"Insufficient depth: {bid_length} bids, "
                            f"{ask_length} asks, minimum {min_levels} required"
                        )
                
                # Check freshness if timestamp is available
                if 'timestamp' in orderbook_data:
                    max_age_seconds = self.validation_config.get('max_orderbook_age_seconds', 60)
                    age_seconds = (time.time() * 1000 - orderbook_data['timestamp']) / 1000
                    
                    if age_seconds > max_age_seconds:
                        orderbook_valid = False
                        orderbook_details['freshness_issue'] = f"Orderbook is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
            
            result['orderbook_valid'] = orderbook_valid
            details['orderbook'] = orderbook_details
            
            # Validate trades
            trades_valid = True
            trades_details = {}
            
            if market_data['trades'] is None:
                trades_valid = False
                trades_details['error'] = "No trades data"
            else:
                # Handle different trades data structures
                trades_data = market_data['trades']
                
                # If trades is a dict, it might have the actual trades under 'list' or 'result'
                if isinstance(trades_data, dict):
                    # Try to extract trades list from common nested structures
                    if 'result' in trades_data and isinstance(trades_data['result'], dict) and 'list' in trades_data['result']:
                        trades_data = trades_data['result']['list']
                    elif 'list' in trades_data:
                        trades_data = trades_data['list']
                    elif 'result' in trades_data and isinstance(trades_data['result'], list):
                        # Sometimes result itself might be the list
                        trades_data = trades_data['result']
                
                # Now check if trades is a list
                if not isinstance(trades_data, list):
                    trades_valid = False
                    trades_details['error'] = f"Trades data must be a list, got {type(trades_data)}. Keys: {list(market_data['trades'].keys()) if isinstance(market_data['trades'], dict) else 'N/A'}"
                else:
                    # Check minimum number of trades
                    min_trades = self.validation_config.get('min_trades_count', 5)
                    if len(trades_data) < min_trades:
                        trades_valid = False
                        trades_details['count_issue'] = f"Only {len(trades_data)} trades, minimum {min_trades} required"
                    
                    # Check freshness of newest trade, but only if there are trades
                    if trades_data and len(trades_data) > 0:
                        # First make sure we have valid trade objects
                        valid_trades = [trade for trade in trades_data 
                                      if isinstance(trade, dict) and 'timestamp' in trade]
                        
                        if valid_trades:
                            newest_ts = max(trade['timestamp'] for trade in valid_trades)
                            max_age_seconds = self.validation_config.get('max_trades_age_seconds', 300)
                            age_seconds = (time.time() * 1000 - newest_ts) / 1000
                            
                            if age_seconds > max_age_seconds:
                                trades_valid = False
                                trades_details['freshness_issue'] = f"Newest trade is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                        else:
                            trades_valid = False
                            trades_details['format_issue'] = "No valid trade objects with timestamp found"
            
            result['trades_valid'] = trades_valid
            details['trades'] = trades_details
            
            # Set overall validity
            result['overall_valid'] = ohlcv_valid and orderbook_valid and trades_valid
            result['details'] = details
            
            # Log validation results if verbose
            if verbose:
                if result['overall_valid']:
                    self.logger.debug(f"Market data validation passed for {self.symbol}")
                else:
                    self.logger.warning(f"Market data validation failed for {self.symbol}: {details}")
            
            # Record metrics
            self.metrics_manager.record_metric('validation_passed', int(result['overall_valid']))
            self.metrics_manager.record_metric('ohlcv_valid', int(result['ohlcv_valid']))
            self.metrics_manager.record_metric('orderbook_valid', int(result['orderbook_valid']))
            self.metrics_manager.record_metric('trades_valid', int(result['trades_valid']))
            
            self.metrics_manager.end_operation(operation)
            
            # If validation failed and health monitor is available, consider creating alerts
            if not result['overall_valid'] and self.health_monitor:
                # Only create alerts for persistent validation failures
                # We could track these failures in a history to only alert after multiple failures
                invalid_components = []
                if not result['ohlcv_valid']:
                    invalid_components.append("OHLCV")
                if not result['orderbook_valid']:
                    invalid_components.append("Orderbook")
                if not result['trades_valid']:
                    invalid_components.append("Trades")
                
                if invalid_components:
                    self.health_monitor._create_alert(
                        level="warning",
                        source=f"validation:{self.exchange_id}:{self.symbol_str}",
                        message=f"Market data validation failed for {self.symbol}: {', '.join(invalid_components)}"
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            if 'operation' in locals():
                self.metrics_manager.end_operation(operation, success=False)
            
            return {
                'overall_valid': False,
                'error': str(e),
                'details': {}
            }

    async def _fetch_with_retry(self, method_name: str, *args, **kwargs) -> Any:
        """Execute an exchange API method with retry logic.
        
        Args:
            method_name: Name of the ccxt method to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
        
        Returns:
            API response data
        
        Raises:
            Exception: If all retries fail
        """
        # Setup retry configuration
        max_retries = self.retry_config.get('max_retries', 3)
        retry_delay = self.retry_config.get('retry_delay_seconds', 2)
        exponential_backoff = self.retry_config.get('retry_exponential_backoff', True)
        
        # Apply rate limiting if enabled
        if self.rate_limit_config.get('enabled', True):
            await self._apply_rate_limiting()
        
        # Get the method to call
        if not hasattr(self.exchange, method_name):
            raise AttributeError(f"Exchange {self.exchange_id} does not have method {method_name}")
        
        method = getattr(self.exchange, method_name)
        
        # Try the call with retries
        last_error = None
        retry_count = 0
        
        operation = self.metrics_manager.start_operation(f"api_call_{method_name}")
        
        while retry_count <= max_retries:
            try:
                # Execute the API call
                self.logger.debug(f"Calling {method_name} (attempt {retry_count + 1}/{max_retries + 1})")
                
                # Measure the time taken
                start_time = time.time()
                response = await method(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record metrics
                self.metrics_manager.record_metric(f'api_duration_{method_name}', duration)
                self.metrics_manager.record_metric('api_success', 1)
                
                # Log the success
                self.logger.debug(f"{method_name} completed in {duration:.2f}s")
                
                # End operation
                self.metrics_manager.end_operation(operation)
                
                return response
                
            except Exception as e:
                # Record the error
                error_type = type(e).__name__
                error_message = str(e)
                
                # Log the error
                self.logger.warning(f"{method_name} failed (attempt {retry_count + 1}/{max_retries + 1}): {error_type}: {error_message}")
                
                # Record metrics
                self.metrics_manager.record_metric('api_error', 1)
                self.metrics_manager.record_metric(f'api_error_{error_type}', 1)
                
                # Store last error
                last_error = e
                
                # Check if we should retry
                if retry_count >= max_retries:
                    self.logger.error(f"All {max_retries + 1} attempts for {method_name} failed")
                    self.metrics_manager.end_operation(operation, success=False)
                    raise last_error
                
                # Calculate delay for next retry
                if exponential_backoff:
                    current_delay = retry_delay * (2 ** retry_count)
                else:
                    current_delay = retry_delay
                
                self.logger.debug(f"Retrying in {current_delay:.1f}s...")
                await asyncio.sleep(current_delay)
                
                retry_count += 1
        
        # This should never be reached due to the raise in the loop
        self.metrics_manager.end_operation(operation, success=False)
        raise last_error if last_error else RuntimeError(f"Failed to execute {method_name}")

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting based on configuration."""
        try:
            # Simple rate limiting implementation
            max_requests = self.rate_limit_config.get('max_requests_per_second', 5)
            
            # Track request time directly in the object instead of using metrics manager
            current_time = time.time()
            
            # Initialize _last_request_time attribute if it doesn't exist
            if not hasattr(self, '_last_request_time'):
                self._last_request_time = 0
            
            if self._last_request_time > 0:
                time_since_last = current_time - self._last_request_time
                min_interval = 1.0 / max_requests
                
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)
            
            # Update last request time
            self._last_request_time = current_time
            
            # Still record the metric if metrics manager is available
            if self.metrics_manager:
                self.metrics_manager.record_metric('last_api_request_time', current_time)
        except Exception as e:
            self.logger.warning(f"Error applying rate limiting: {str(e)}")
            # Continue without rate limiting if there's an error

    def _get_utc_timestamp(self, as_ms: bool = True) -> int:
        """Get current UTC timestamp.
        
        Args:
            as_ms: If True, return millisecond timestamp, else seconds
        
        Returns:
            Current UTC timestamp in milliseconds or seconds
        """
        ts = dt.datetime.now(dt.timezone.utc).timestamp()
        return int(ts * 1000) if as_ms else int(ts)

    def _format_analysis_results(self, analysis_result, symbol_str):
        """
        Format analysis results with enhanced visualization options:
        1. Structured dashboard with tables
        2. Color coding for scores (terminal colors)
        3. Visual gauges using ASCII art
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
            
        Returns:
            str: Formatted analysis output
        """
        if not analysis_result:
            return f"No analysis results available for {symbol_str}"
        
        score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
        reliability = analysis_result.get('reliability', 0)
        components = analysis_result.get('components', {})
        
        # Function to determine color based on score
        def get_color_code(value):
            if value >= 70:
                return "\033[92m"  # Green for bullish
            elif value >= 45:
                return "\033[93m"  # Yellow for neutral
            else:
                return "\033[91m"  # Red for bearish
        
        # Function to create ASCII gauge
        def create_gauge(value):
            gauge_width = 20
            filled = int((value / 100) * gauge_width)
            gauge = "["
            for i in range(gauge_width):
                if i < filled:
                    if value >= 70:
                        gauge += "█"  # Green area (filled)
                    elif value >= 45:
                        gauge += "▒"  # Yellow area (filled)
                    else:
                        gauge += "░"  # Red area (filled)
                else:
                    gauge += " "
            gauge += "]"
            return gauge
        
        # Format headers for dashboard
        header = f"\n{'=' * 60}\n"
        header += f"ANALYSIS DASHBOARD FOR {symbol_str} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"{'=' * 60}\n"
        
        # Format main confluence score
        color_code = get_color_code(score)
        reset_code = "\033[0m"
        main_score = f"CONFLUENCE SCORE: {color_code}{score:.2f}{reset_code}/100 "
        main_score += f"(Reliability: {reliability:.2f})\n"
        main_score += create_gauge(score) + "\n"
        
        # Format component scores table
        component_table = "\nCOMPONENT SCORES:\n"
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        component_table += f"| {'Component':<23} | {'Score':<8} | {'Visual':<20} |\n"
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        
        # Add components to table
        if components:
            for name, value in components.items():
                if isinstance(value, dict) and 'score' in value:
                    comp_score = value['score']
                elif isinstance(value, (int, float)):
                    comp_score = value
                else:
                    continue
                    
                color = get_color_code(comp_score)
                component_table += f"| {name:<23} | {color}{comp_score:<8.2f}{reset_code} | {create_gauge(comp_score):<20} |\n"
        
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        
        # Combine all sections
        formatted_output = header + main_score + component_table
        
        # Add interpretation if available
        interpretation = analysis_result.get('overall_interpretation', '')
        if interpretation:
            formatted_output += f"\nINTERPRETATION: {interpretation}\n"
        
        formatted_output += f"{'=' * 60}\n"
        
        return formatted_output
        
    def log_analysis_result(self, analysis_result, symbol_str):
        """
        Log analysis results with enhanced formatting.
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
        """
        if not analysis_result:
            self.logger.warning(f"No analysis results available for {symbol_str}")
            return
            
        # Use the new formatted output
        formatted_analysis = self._format_analysis_results(analysis_result, symbol_str)
        self.logger.info(formatted_analysis)

class ErrorHandler:
    """Centralized error handling class to standardize error handling throughout the code."""
    
    def __init__(self, logger, metrics_manager=None):
        """Initialize the error handler.
        
        Args:
            logger: Logger instance for error logging
            metrics_manager: Optional metrics manager for tracking errors
        """
        self.logger = logger
        self.metrics_manager = metrics_manager
    
    def handle_error(self, error: Exception, operation: str, component: str = "market_monitor", 
                    severity: str = "ERROR", extra_data: Dict[str, Any] = None) -> None:
        """Handle an error with standardized logging and metrics.
        
        Args:
            error: The exception that occurred
            operation: The operation that failed
            component: The component where the error occurred
            severity: Error severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            extra_data: Additional data to log with the error
        """
        # Determine log level
        log_level = getattr(logging, severity, logging.ERROR)
        
        # Prepare error message
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the error with appropriate level
        self.logger.log(log_level, f"{component}.{operation} failed: {error_type}: {error_message}")
        
        # Log traceback for errors and criticals
        if log_level >= logging.ERROR:
            self.logger.debug(traceback.format_exc())
        
        # Log extra data if provided
        if extra_data:
            self.logger.debug(f"Additional error context: {extra_data}")
        
        # Record metrics if metrics manager is available
        if self.metrics_manager:
            self.metrics_manager.record_metric(f"errors.{component}.{operation}", 1)
            self.metrics_manager.record_metric(f"errors.{error_type}", 1)
            self.metrics_manager.record_error(f"{component}.{operation}", error_message)
    
    async def handle_async_operation(self, operation_func, operation_name: str, *args, 
                                    component: str = "market_monitor", severity: str = "ERROR", 
                                    **kwargs) -> Any:
        """Execute an async operation with standardized error handling.
        
        Args:
            operation_func: Async function to execute
            operation_name: Name of the operation for logging and metrics
            *args: Positional arguments for the operation function
            component: The component executing the operation
            severity: Error severity if operation fails
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            The result of the operation, or None if it fails
        """
        # Start performance tracking if metrics manager is available
        operation_metric = None
        if self.metrics_manager:
            operation_metric = self.metrics_manager.start_operation(operation_name)
        
        try:
            # Execute the operation
            result = await operation_func(*args, **kwargs)
            
            # End operation metric if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric)
                
            return result
            
        except Exception as e:
            # Handle the error
            self.handle_error(e, operation_name, component, severity)
            
            # End operation metric with failure if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric, success=False)
                
            return None
    
    def handle_sync_operation(self, operation_func, operation_name: str, *args, 
                             component: str = "market_monitor", severity: str = "ERROR", 
                             **kwargs) -> Any:
        """Execute a synchronous operation with standardized error handling.
        
        Args:
            operation_func: Function to execute
            operation_name: Name of the operation for logging and metrics
            *args: Positional arguments for the operation function
            component: The component executing the operation
            severity: Error severity if operation fails
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            The result of the operation, or None if it fails
        """
        # Start performance tracking if metrics manager is available
        operation_metric = None
        if self.metrics_manager:
            operation_metric = self.metrics_manager.start_operation(operation_name)
        
        try:
            # Execute the operation
            result = operation_func(*args, **kwargs)
            
            # End operation metric if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric)
                
            return result
            
        except Exception as e:
            # Handle the error
            self.handle_error(e, operation_name, component, severity)
            
            # End operation metric with failure if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric, success=False)
                
            return None

# Update the MarketMonitor.__init__ method to use the ErrorHandler
# Add the following line to the __init__ method
# self.error_handler = ErrorHandler(self.logger, self.metrics_manager)

# Then in methods that use try/except, replace with:
# result = await self.error_handler.handle_async_operation(
#     self._some_operation_func, "operation_name", arg1, arg2, kwarg1=value1
# )

class VisualizationUtility:
    """Utility class for generating visualizations from market data."""
    
    def __init__(self, logger):
        """Initialize visualization utility.
        
        Args:
            logger: Logger instance for logging visualization operations
        """
        self.logger = logger
    
    def visualize_market_data(self, market_data: Dict[str, Any], output_dir: Optional[str] = None) -> Dict[str, str]:
        """Generate visualizations for market data components.
        
        Args:
            market_data: Market data dictionary
            output_dir: Optional directory to save visualizations
            
        Returns:
            Dictionary mapping data types to base64-encoded PNG images
        """
        try:
            visualizations = {}
            symbol = market_data.get('symbol_str', 'unknown')
            
            # Create output directory if specified
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            
            # Visualize OHLCV data if available
            if 'ohlcv' in market_data and market_data['ohlcv']:
                ohlcv_vis = self._visualize_ohlcv(market_data['ohlcv'], symbol)
                visualizations['ohlcv'] = ohlcv_vis
                
                if output_dir:
                    self._save_visualization(ohlcv_vis, output_dir, f"{symbol}_ohlcv.png")
            
            # Visualize orderbook if available
            if 'orderbook' in market_data and market_data['orderbook']:
                orderbook_vis = self._visualize_orderbook(market_data['orderbook'], symbol)
                visualizations['orderbook'] = orderbook_vis
                
                if output_dir:
                    self._save_visualization(orderbook_vis, output_dir, f"{symbol}_orderbook.png")
            
            # Visualize trades if available
            if 'trades' in market_data and market_data['trades']:
                trades_vis = self._visualize_trades(market_data['trades'], symbol)
                visualizations['trades'] = trades_vis
                
                if output_dir:
                    self._save_visualization(trades_vis, output_dir, f"{symbol}_trades.png")
            
            return visualizations
            
        except Exception as e:
            self.logger.error(f"Error visualizing market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}
    
    def _visualize_ohlcv(self, ohlcv_data: Dict[str, Any], symbol: str) -> str:
        """Generate OHLCV visualization.
        
        Args:
            ohlcv_data: OHLCV data dictionary
            symbol: Trading pair symbol
        
        Returns:
            Base64-encoded PNG image
        """
        # Create figure with 2 subplots (price and volume)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f"OHLCV Data for {symbol}", fontsize=16)
        
        # Get the base timeframe data
        df = None
        
        if isinstance(ohlcv_data, dict):
            # Try to get base timeframe first, then any available timeframe
            timeframe_priority = ['base', 'ltf', 'mtf', 'htf']
            
            for tf in timeframe_priority:
                if tf in ohlcv_data:
                    tf_data = ohlcv_data[tf]
                    
                    if isinstance(tf_data, pd.DataFrame) and not tf_data.empty:
                        df = tf_data
                        break
                    elif isinstance(tf_data, dict) and 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                        df = tf_data['data']
                        break
        elif isinstance(ohlcv_data, pd.DataFrame):
            df = ohlcv_data
        
        if df is None or df.empty:
            self.logger.warning(f"No valid OHLCV data for visualization")
            # Create an empty visualization
            fig.text(0.5, 0.5, "No OHLCV data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # Ensure DataFrame has datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                # Convert timestamp column to datetime
                df.set_index('timestamp', inplace=True)
                df.index = pd.to_datetime(df.index, unit='ms')
            else:
                # Create a dummy index
                df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='T')
        
        # Create candlestick chart
        ax1.set_title(f"Price (Timeframe: {getattr(df, 'timeframe', 'unknown')})")
        
        # Calculate candlestick colors
        colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]
        
        # Plot candlesticks
        for i, (timestamp, row) in enumerate(df.iterrows()):
            # Draw body
            ax1.plot([i, i], [row['open'], row['close']], color=colors[i], linewidth=3)
            # Draw wicks
            ax1.plot([i, i], [row['low'], row['high']], color=colors[i], linewidth=1)
        
        # Set x-axis labels
        ax1.set_xticks(range(0, len(df), max(1, len(df) // 10)))
        ax1.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])
        
        # Add volume subplot
        ax2.set_title("Volume")
        ax2.bar(range(len(df)), df['volume'], color=colors, alpha=0.7)
        
        # Set x-axis labels for volume chart
        ax2.set_xticks(range(0, len(df), max(1, len(df) // 10)))
        ax2.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _visualize_orderbook(self, orderbook_data: Dict[str, Any], symbol: str) -> str:
        """Generate orderbook visualization.
        
        Args:
            orderbook_data: Orderbook data dictionary
            symbol: Trading pair symbol
        
        Returns:
            Base64-encoded PNG image
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.suptitle(f"Orderbook for {symbol}", fontsize=16)
        
        # Check if orderbook data is valid
        if not isinstance(orderbook_data, dict) or 'bids' not in orderbook_data or 'asks' not in orderbook_data:
            self.logger.warning(f"Invalid orderbook data for visualization")
            # Create an empty visualization
            fig.text(0.5, 0.5, "No orderbook data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        bids = orderbook_data['bids']
        asks = orderbook_data['asks']
        
        if not bids or not asks:
            self.logger.warning(f"Empty bids or asks in orderbook")
            # Create an empty visualization
            fig.text(0.5, 0.5, "Empty orderbook data", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # Extract price and quantity
        bid_prices = [bid[0] for bid in bids[:20]]  # Limit to 20 levels
        bid_quantities = [bid[1] for bid in bids[:20]]
        ask_prices = [ask[0] for ask in asks[:20]]
        ask_quantities = [ask[1] for ask in asks[:20]]
        
        # Cumulative quantities - use numpy's cumsum for efficiency
        bid_cumulative = np.cumsum(bid_quantities).tolist()
        ask_cumulative = np.cumsum(ask_quantities).tolist()
        
        # Plot bids (cumulative)
        ax.step(bid_prices, bid_cumulative, where='post', color='green', label='Bids')
        ax.fill_between(bid_prices, bid_cumulative, step='post', alpha=0.2, color='green')
        
        # Plot asks (cumulative)
        ax.step(ask_prices, ask_cumulative, where='post', color='red', label='Asks')
        ax.fill_between(ask_prices, ask_cumulative, step='post', alpha=0.2, color='red')
        
        # Set labels and legend
        ax.set_xlabel('Price')
        ax.set_ylabel('Cumulative Quantity')
        ax.legend()
        
        # Calculate and show spread
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100
        
        ax.axvline(x=best_bid, color='green', linestyle='--', alpha=0.7)
        ax.axvline(x=best_ask, color='red', linestyle='--', alpha=0.7)
        
        ax.text(0.5, 0.02, f"Spread: {spread:.8f} ({spread_pct:.4f}%)", 
                transform=ax.transAxes, ha='center', fontsize=10, 
                bbox=dict(facecolor='white', alpha=0.8))
        
        # Format y-axis with comma separators for large numbers
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _visualize_trades(self, trades_data: Any, symbol: str) -> str:
        """Generate trades visualization.
        
        Args:
            trades_data: Trades data
            symbol: Trading pair symbol
            
        Returns:
            Base64-encoded PNG image
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10))
        fig.suptitle(f"Recent Trades for {symbol}", fontsize=16)
        
        # Convert trades to DataFrame if needed
        if isinstance(trades_data, list):
            try:
                # Extract relevant fields
                trade_list = []
                for trade in trades_data:
                    trade_dict = {
                        'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),
                        'price': float(trade.get('price', 0)),
                        'amount': float(trade.get('amount', trade.get('quantity', 0))),
                        'side': trade.get('side', 'unknown')
                    }
                    trade_list.append(trade_dict)
                
                df = pd.DataFrame(trade_list)
                
                # Sort by timestamp
                if 'timestamp' in df.columns:
                    df.sort_values('timestamp', inplace=True)
            except Exception as e:
                self.logger.warning(f"Error converting trades to DataFrame: {str(e)}")
                fig.text(0.5, 0.5, "Error processing trades data", ha='center', va='center')
                return self._fig_to_base64(fig)
        elif isinstance(trades_data, pd.DataFrame):
            df = trades_data.copy()
            
            # Ensure columns exist
            required_cols = ['timestamp', 'price', 'amount', 'side']
            for col in required_cols:
                if col not in df.columns:
                    self.logger.warning(f"Missing column {col} in trades DataFrame")
                    fig.text(0.5, 0.5, f"Missing required column: {col}", ha='center', va='center')
                    return self._fig_to_base64(fig)
        else:
            self.logger.warning(f"Invalid trades data type: {type(trades_data)}")
            fig.text(0.5, 0.5, "Invalid trades data format", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        if df.empty:
            fig.text(0.5, 0.5, "No trades data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # 1. Price over time
        ax1.set_title("Price over time")
        ax1.plot(df['timestamp'], df['price'], marker='.', linestyle='-', alpha=0.7)
        
        # Color points by trade side if available
        if 'side' in df.columns:
            buy_mask = df['side'] == 'buy'
            sell_mask = df['side'] == 'sell'
            
            ax1.scatter(df.loc[buy_mask, 'timestamp'], df.loc[buy_mask, 'price'], 
                        color='green', s=20, alpha=0.7, label='Buy')
            ax1.scatter(df.loc[sell_mask, 'timestamp'], df.loc[sell_mask, 'price'], 
                        color='red', s=20, alpha=0.7, label='Sell')
            ax1.legend()
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # 2. Trade sizes
        ax2.set_title("Trade Sizes")
        ax2.bar(range(len(df)), df['amount'], color='blue', alpha=0.7)
        ax2.set_ylabel("Amount")
        ax2.set_xlabel("Trade Number")
        
        # 3. Buy vs Sell volumes
        ax3.set_title("Buy vs Sell Volume")
        
        if 'side' in df.columns:
            # Group by side and sum amounts
            volume_by_side = df.groupby('side')['amount'].sum()
            
            # Create pie chart
            colors = {'buy': 'green', 'sell': 'red'}
            pie_colors = [colors.get(side, 'gray') for side in volume_by_side.index]
            
            ax3.pie(volume_by_side, labels=volume_by_side.index, autopct='%1.1f%%', 
                   startangle=90, colors=pie_colors)
            ax3.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        else:
            ax3.text(0.5, 0.5, "No side information available", ha='center', va='center', transform=ax3.transAxes)
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convert Matplotlib figure to base64-encoded string.
        
        Args:
            fig: Matplotlib figure
            
        Returns:
            Base64-encoded PNG image
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return img_str
    
    def _save_visualization(self, base64_img: str, output_dir: str, filename: str) -> None:
        """Save base64-encoded visualization to file.
        
        Args:
            base64_img: Base64-encoded image
            output_dir: Output directory
            filename: Output filename
        """
        try:
            img_data = base64.b64decode(base64_img)
            output_path = Path(output_dir) / filename
            
            with open(output_path, 'wb') as f:
                f.write(img_data)
                
            self.logger.debug(f"Saved visualization to {output_path}")
            
        except Exception as e:
            self.logger.warning(f"Error saving visualization: {str(e)}")

    def validate_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate market data for completeness and freshness.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Validation result dictionary
        """
        result = {
            'overall_valid': True,
            'ohlcv_valid': True,
            'orderbook_valid': True,
            'trades_valid': True,
            'details': {}
        }
        
        # Record validation operation
        operation = self.metrics_manager.start_operation("validate_market_data")
        
        try:
            # Configure logging verbosity
            verbose = self.debug_config.get('verbose_validation', False)
            details = {}
            
            # Validate OHLCV data
            ohlcv_valid = True
            ohlcv_details = {}
            
            for tf_key, df in market_data['ohlcv'].items():
                tf_valid = True
                tf_details = {}
                
                # Check if data is a valid DataFrame
                if not isinstance(df, pd.DataFrame):
                    # Try to convert to DataFrame if it's a list
                    if isinstance(df, list):
                        if not df:  # Empty list
                            tf_valid = False
                            tf_details['error'] = "Empty data list"
                        else:
                            try:
                                # Try to convert list to DataFrame
                                df = pd.DataFrame(df)
                                # Update the market data with the DataFrame
                                market_data['ohlcv'][tf_key] = df
                            except Exception as e:
                                tf_valid = False
                                tf_details['error'] = f"Could not convert list to DataFrame: {str(e)}"
                    else:
                        tf_valid = False
                        tf_details['error'] = f"Invalid data type: {type(df)}"
                
                # Now check if DataFrame is empty (only if it's a DataFrame now)
                if isinstance(df, pd.DataFrame) and df.empty:
                    tf_valid = False
                    tf_details['error'] = "Empty DataFrame"
                elif isinstance(df, pd.DataFrame):
                    # Check minimum number of candles
                    min_candles = self.validation_config.get('min_ohlcv_candles', 20)
                    if len(df) < min_candles:
                        tf_valid = False
                        tf_details['candle_count_issue'] = f"Only {len(df)} candles, minimum {min_candles} required"
                    
                    # Check freshness of newest candle
                    if isinstance(df.index, pd.DatetimeIndex):
                        latest_ts = df.index.max()
                        # Ensure latest_ts has timezone info if it doesn't already
                        if latest_ts.tzinfo is None:
                            latest_ts = latest_ts.tz_localize('UTC')
                    else:
                        # If index is not datetime, try to use last row's timestamp
                        latest_ts = pd.to_datetime(df.iloc[-1].name, unit='ms').tz_localize('UTC')
                    
                    max_age_seconds = self.validation_config.get('max_ohlcv_age_seconds', 300)
                    age_seconds = (pd.Timestamp.now(tz='UTC') - latest_ts).total_seconds()
                    
                    if age_seconds > max_age_seconds:
                        tf_valid = False
                        tf_details['freshness_issue'] = f"Newest candle is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                
                ohlcv_details[tf_key] = {
                    'valid': tf_valid,
                    'details': tf_details
                }
                
                if not tf_valid:
                    ohlcv_valid = False
            
            result['ohlcv_valid'] = ohlcv_valid
            details['ohlcv'] = ohlcv_details
            
            # Validate orderbook
            orderbook_valid = True
            orderbook_details = {}
            
            if market_data['orderbook'] is None:
                orderbook_valid = False
                orderbook_details['error'] = "No orderbook data"
            else:
                # Check the structure of orderbook data which might be nested in result
                orderbook_data = market_data['orderbook']
                
                # Handle case where orderbook is in result.b (bids) and result.a (asks) format
                if 'result' in orderbook_data and isinstance(orderbook_data['result'], dict):
                    result_data = orderbook_data['result']
                    if 'b' in result_data and 'a' in result_data:
                        # Extract bids and asks from the result structure
                        orderbook_data['bids'] = result_data.get('b', [])
                        orderbook_data['asks'] = result_data.get('a', [])
                
                # Now check for bids and asks
                if 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                    orderbook_valid = False
                    orderbook_details['structure_issue'] = f"Missing bids or asks fields. Keys: {list(orderbook_data.keys())}"
                else:
                    # Check minimum number of levels
                    min_levels = self.validation_config.get('min_orderbook_levels', 5)
                    bid_length = len(orderbook_data['bids']) if isinstance(orderbook_data['bids'], list) else 0
                    ask_length = len(orderbook_data['asks']) if isinstance(orderbook_data['asks'], list) else 0
                    
                    if (bid_length < min_levels or ask_length < min_levels):
                        orderbook_valid = False
                        orderbook_details['depth_issue'] = (
                            f"Insufficient depth: {bid_length} bids, "
                            f"{ask_length} asks, minimum {min_levels} required"
                        )
                
                # Check freshness if timestamp is available
                if 'timestamp' in orderbook_data:
                    max_age_seconds = self.validation_config.get('max_orderbook_age_seconds', 60)
                    age_seconds = (time.time() * 1000 - orderbook_data['timestamp']) / 1000
                    
                    if age_seconds > max_age_seconds:
                        orderbook_valid = False
                        orderbook_details['freshness_issue'] = f"Orderbook is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
            
            result['orderbook_valid'] = orderbook_valid
            details['orderbook'] = orderbook_details
            
            # Validate trades
            trades_valid = True
            trades_details = {}
            
            if market_data['trades'] is None:
                trades_valid = False
                trades_details['error'] = "No trades data"
            else:
                # Handle different trades data structures
                trades_data = market_data['trades']
                
                # If trades is a dict, it might have the actual trades under 'list' or 'result'
                if isinstance(trades_data, dict):
                    # Try to extract trades list from common nested structures
                    if 'result' in trades_data and isinstance(trades_data['result'], dict) and 'list' in trades_data['result']:
                        trades_data = trades_data['result']['list']
                    elif 'list' in trades_data:
                        trades_data = trades_data['list']
                    elif 'result' in trades_data and isinstance(trades_data['result'], list):
                        # Sometimes result itself might be the list
                        trades_data = trades_data['result']
                
                # Now check if trades is a list
                if not isinstance(trades_data, list):
                    trades_valid = False
                    trades_details['error'] = f"Trades data must be a list, got {type(trades_data)}. Keys: {list(market_data['trades'].keys()) if isinstance(market_data['trades'], dict) else 'N/A'}"
                else:
                    # Check minimum number of trades
                    min_trades = self.validation_config.get('min_trades_count', 5)
                    if len(trades_data) < min_trades:
                        trades_valid = False
                        trades_details['count_issue'] = f"Only {len(trades_data)} trades, minimum {min_trades} required"
                    
                    # Check freshness of newest trade, but only if there are trades
                    if trades_data and len(trades_data) > 0:
                        # First make sure we have valid trade objects
                        valid_trades = [trade for trade in trades_data 
                                      if isinstance(trade, dict) and 'timestamp' in trade]
                        
                        if valid_trades:
                            newest_ts = max(trade['timestamp'] for trade in valid_trades)
                            max_age_seconds = self.validation_config.get('max_trades_age_seconds', 300)
                            age_seconds = (time.time() * 1000 - newest_ts) / 1000
                            
                            if age_seconds > max_age_seconds:
                                trades_valid = False
                                trades_details['freshness_issue'] = f"Newest trade is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                        else:
                            trades_valid = False
                            trades_details['format_issue'] = "No valid trade objects with timestamp found"
            
            result['trades_valid'] = trades_valid
            details['trades'] = trades_details
            
            # Set overall validity
            result['overall_valid'] = ohlcv_valid and orderbook_valid and trades_valid
            result['details'] = details
            
            # Log validation results if verbose
            if verbose:
                if result['overall_valid']:
                    self.logger.debug(f"Market data validation passed for {self.symbol}")
                else:
                    self.logger.warning(f"Market data validation failed for {self.symbol}: {details}")
            
            # Record metrics
            self.metrics_manager.record_metric('validation_passed', int(result['overall_valid']))
            self.metrics_manager.record_metric('ohlcv_valid', int(result['ohlcv_valid']))
            self.metrics_manager.record_metric('orderbook_valid', int(result['orderbook_valid']))
            self.metrics_manager.record_metric('trades_valid', int(result['trades_valid']))
            
            self.metrics_manager.end_operation(operation)
            
            # If validation failed and health monitor is available, consider creating alerts
            if not result['overall_valid'] and self.health_monitor:
                # Only create alerts for persistent validation failures
                # We could track these failures in a history to only alert after multiple failures
                invalid_components = []
                if not result['ohlcv_valid']:
                    invalid_components.append("OHLCV")
                if not result['orderbook_valid']:
                    invalid_components.append("Orderbook")
                if not result['trades_valid']:
                    invalid_components.append("Trades")
                
                if invalid_components:
                    self.health_monitor._create_alert(
                        level="warning",
                        source=f"validation:{self.exchange_id}:{self.symbol_str}",
                        message=f"Market data validation failed for {self.symbol}: {', '.join(invalid_components)}"
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            if 'operation' in locals():
                self.metrics_manager.end_operation(operation, success=False)
            
            return {
                'overall_valid': False,
                'error': str(e),
                'details': {}
            }

    async def _fetch_with_retry(self, method_name: str, *args, **kwargs) -> Any:
        """Execute an exchange API method with retry logic.
        
        Args:
            method_name: Name of the ccxt method to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
        
        Returns:
            API response data
        
        Raises:
            Exception: If all retries fail
        """
        # Setup retry configuration
        max_retries = self.retry_config.get('max_retries', 3)
        retry_delay = self.retry_config.get('retry_delay_seconds', 2)
        exponential_backoff = self.retry_config.get('retry_exponential_backoff', True)
        
        # Apply rate limiting if enabled
        if self.rate_limit_config.get('enabled', True):
            await self._apply_rate_limiting()
        
        # Get the method to call
        if not hasattr(self.exchange, method_name):
            raise AttributeError(f"Exchange {self.exchange_id} does not have method {method_name}")
        
        method = getattr(self.exchange, method_name)
        
        # Try the call with retries
        last_error = None
        retry_count = 0
        
        operation = self.metrics_manager.start_operation(f"api_call_{method_name}")
        
        while retry_count <= max_retries:
            try:
                # Execute the API call
                self.logger.debug(f"Calling {method_name} (attempt {retry_count + 1}/{max_retries + 1})")
                
                # Measure the time taken
                start_time = time.time()
                response = await method(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record metrics
                self.metrics_manager.record_metric(f'api_duration_{method_name}', duration)
                self.metrics_manager.record_metric('api_success', 1)
                
                # Log the success
                self.logger.debug(f"{method_name} completed in {duration:.2f}s")
                
                # End operation
                self.metrics_manager.end_operation(operation)
                
                return response
                
            except Exception as e:
                # Record the error
                error_type = type(e).__name__
                error_message = str(e)
                
                # Log the error
                self.logger.warning(f"{method_name} failed (attempt {retry_count + 1}/{max_retries + 1}): {error_type}: {error_message}")
                
                # Record metrics
                self.metrics_manager.record_metric('api_error', 1)
                self.metrics_manager.record_metric(f'api_error_{error_type}', 1)
                
                # Store last error
                last_error = e
                
                # Check if we should retry
                if retry_count >= max_retries:
                    self.logger.error(f"All {max_retries + 1} attempts for {method_name} failed")
                    self.metrics_manager.end_operation(operation, success=False)
                    raise last_error
                
                # Calculate delay for next retry
                if exponential_backoff:
                    current_delay = retry_delay * (2 ** retry_count)
                else:
                    current_delay = retry_delay
                
                self.logger.debug(f"Retrying in {current_delay:.1f}s...")
                await asyncio.sleep(current_delay)
                
                retry_count += 1
        
        # This should never be reached due to the raise in the loop
        self.metrics_manager.end_operation(operation, success=False)
        raise last_error if last_error else RuntimeError(f"Failed to execute {method_name}")

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting based on configuration."""
        try:
            # Simple rate limiting implementation
            max_requests = self.rate_limit_config.get('max_requests_per_second', 5)
            
            # Track request time directly in the object instead of using metrics manager
            current_time = time.time()
            
            # Initialize _last_request_time attribute if it doesn't exist
            if not hasattr(self, '_last_request_time'):
                self._last_request_time = 0
            
            if self._last_request_time > 0:
                time_since_last = current_time - self._last_request_time
                min_interval = 1.0 / max_requests
                
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)
            
            # Update last request time
            self._last_request_time = current_time
            
            # Still record the metric if metrics manager is available
            if self.metrics_manager:
                self.metrics_manager.record_metric('last_api_request_time', current_time)
        except Exception as e:
            self.logger.warning(f"Error applying rate limiting: {str(e)}")
            # Continue without rate limiting if there's an error

    def _get_utc_timestamp(self, as_ms: bool = True) -> int:
        """Get current UTC timestamp.
        
        Args:
            as_ms: If True, return millisecond timestamp, else seconds
        
        Returns:
            Current UTC timestamp in milliseconds or seconds
        """
        ts = dt.datetime.now(dt.timezone.utc).timestamp()
        return int(ts * 1000) if as_ms else int(ts)

    def _format_analysis_results(self, analysis_result, symbol_str):
        """
        Format analysis results with enhanced visualization options:
        1. Structured dashboard with tables
        2. Color coding for scores (terminal colors)
        3. Visual gauges using ASCII art
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
            
        Returns:
            str: Formatted analysis output
        """
        if not analysis_result:
            return f"No analysis results available for {symbol_str}"
        
        score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
        reliability = analysis_result.get('reliability', 0)
        components = analysis_result.get('components', {})
        
        # Function to determine color based on score
        def get_color_code(value):
            if value >= 70:
                return "\033[92m"  # Green for bullish
            elif value >= 45:
                return "\033[93m"  # Yellow for neutral
            else:
                return "\033[91m"  # Red for bearish
        
        # Function to create ASCII gauge
        def create_gauge(value):
            gauge_width = 20
            filled = int((value / 100) * gauge_width)
            gauge = "["
            for i in range(gauge_width):
                if i < filled:
                    if value >= 70:
                        gauge += "█"  # Green area (filled)
                    elif value >= 45:
                        gauge += "▒"  # Yellow area (filled)
                    else:
                        gauge += "░"  # Red area (filled)
                else:
                    gauge += " "
            gauge += "]"
            return gauge
        
        # Format headers for dashboard
        header = f"\n{'=' * 60}\n"
        header += f"ANALYSIS DASHBOARD FOR {symbol_str} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"{'=' * 60}\n"
        
        # Format main confluence score
        color_code = get_color_code(score)
        reset_code = "\033[0m"
        main_score = f"CONFLUENCE SCORE: {color_code}{score:.2f}{reset_code}/100 "
        main_score += f"(Reliability: {reliability:.2f})\n"
        main_score += create_gauge(score) + "\n"
        
        # Format component scores table
        component_table = "\nCOMPONENT SCORES:\n"
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        component_table += f"| {'Component':<23} | {'Score':<8} | {'Visual':<20} |\n"
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        
        # Add components to table
        if components:
            for name, value in components.items():
                if isinstance(value, dict) and 'score' in value:
                    comp_score = value['score']
                elif isinstance(value, (int, float)):
                    comp_score = value
                else:
                    continue
                    
                color = get_color_code(comp_score)
                component_table += f"| {name:<23} | {color}{comp_score:<8.2f}{reset_code} | {create_gauge(comp_score):<20} |\n"
        
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        
        # Combine all sections
        formatted_output = header + main_score + component_table
        
        # Add interpretation if available
        interpretation = analysis_result.get('overall_interpretation', '')
        if interpretation:
            formatted_output += f"\nINTERPRETATION: {interpretation}\n"
        
        formatted_output += f"{'=' * 60}\n"
        
        return formatted_output
        
    def log_analysis_result(self, analysis_result, symbol_str):
        """
        Log analysis results with enhanced formatting.
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
        """
        if not analysis_result:
            self.logger.warning(f"No analysis results available for {symbol_str}")
            return
            
        # Use the new formatted output
        formatted_analysis = self._format_analysis_results(analysis_result, symbol_str)
        self.logger.info(formatted_analysis)

class ErrorHandler:
    """Centralized error handling class to standardize error handling throughout the code."""
    
    def __init__(self, logger, metrics_manager=None):
        """Initialize the error handler.
        
        Args:
            logger: Logger instance for error logging
            metrics_manager: Optional metrics manager for tracking errors
        """
        self.logger = logger
        self.metrics_manager = metrics_manager
    
    def handle_error(self, error: Exception, operation: str, component: str = "market_monitor", 
                    severity: str = "ERROR", extra_data: Dict[str, Any] = None) -> None:
        """Handle an error with standardized logging and metrics.
        
        Args:
            error: The exception that occurred
            operation: The operation that failed
            component: The component where the error occurred
            severity: Error severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            extra_data: Additional data to log with the error
        """
        # Determine log level
        log_level = getattr(logging, severity, logging.ERROR)
        
        # Prepare error message
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the error with appropriate level
        self.logger.log(log_level, f"{component}.{operation} failed: {error_type}: {error_message}")
        
        # Log traceback for errors and criticals
        if log_level >= logging.ERROR:
            self.logger.debug(traceback.format_exc())
        
        # Log extra data if provided
        if extra_data:
            self.logger.debug(f"Additional error context: {extra_data}")
        
        # Record metrics if metrics manager is available
        if self.metrics_manager:
            self.metrics_manager.record_metric(f"errors.{component}.{operation}", 1)
            self.metrics_manager.record_metric(f"errors.{error_type}", 1)
            self.metrics_manager.record_error(f"{component}.{operation}", error_message)
    
    async def handle_async_operation(self, operation_func, operation_name: str, *args, 
                                    component: str = "market_monitor", severity: str = "ERROR", 
                                    **kwargs) -> Any:
        """Execute an async operation with standardized error handling.
        
        Args:
            operation_func: Async function to execute
            operation_name: Name of the operation for logging and metrics
            *args: Positional arguments for the operation function
            component: The component executing the operation
            severity: Error severity if operation fails
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            The result of the operation, or None if it fails
        """
        # Start performance tracking if metrics manager is available
        operation_metric = None
        if self.metrics_manager:
            operation_metric = self.metrics_manager.start_operation(operation_name)
        
        try:
            # Execute the operation
            result = await operation_func(*args, **kwargs)
            
            # End operation metric if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric)
                
            return result
            
        except Exception as e:
            # Handle the error
            self.handle_error(e, operation_name, component, severity)
            
            # End operation metric with failure if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric, success=False)
                
            return None
    
    def handle_sync_operation(self, operation_func, operation_name: str, *args, 
                             component: str = "market_monitor", severity: str = "ERROR", 
                             **kwargs) -> Any:
        """Execute a synchronous operation with standardized error handling.
        
        Args:
            operation_func: Function to execute
            operation_name: Name of the operation for logging and metrics
            *args: Positional arguments for the operation function
            component: The component executing the operation
            severity: Error severity if operation fails
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            The result of the operation, or None if it fails
        """
        # Start performance tracking if metrics manager is available
        operation_metric = None
        if self.metrics_manager:
            operation_metric = self.metrics_manager.start_operation(operation_name)
        
        try:
            # Execute the operation
            result = operation_func(*args, **kwargs)
            
            # End operation metric if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric)
                
            return result
            
        except Exception as e:
            # Handle the error
            self.handle_error(e, operation_name, component, severity)
            
            # End operation metric with failure if started
            if operation_metric and self.metrics_manager:
                self.metrics_manager.end_operation(operation_metric, success=False)
                
            return None

# Update the MarketMonitor.__init__ method to use the ErrorHandler
# Add the following line to the __init__ method
# self.error_handler = ErrorHandler(self.logger, self.metrics_manager)

# Then in methods that use try/except, replace with:
# result = await self.error_handler.handle_async_operation(
#     self._some_operation_func, "operation_name", arg1, arg2, kwarg1=value1
# )

class VisualizationUtility:
    """Utility class for generating visualizations from market data."""
    
    def __init__(self, logger):
        """Initialize visualization utility.
        
        Args:
            logger: Logger instance for logging visualization operations
        """
        self.logger = logger
    
    def visualize_market_data(self, market_data: Dict[str, Any], output_dir: Optional[str] = None) -> Dict[str, str]:
        """Generate visualizations for market data components.
        
        Args:
            market_data: Market data dictionary
            output_dir: Optional directory to save visualizations
            
        Returns:
            Dictionary mapping data types to base64-encoded PNG images
        """
        try:
            visualizations = {}
            symbol = market_data.get('symbol_str', 'unknown')
            
            # Create output directory if specified
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            
            # Visualize OHLCV data if available
            if 'ohlcv' in market_data and market_data['ohlcv']:
                ohlcv_vis = self._visualize_ohlcv(market_data['ohlcv'], symbol)
                visualizations['ohlcv'] = ohlcv_vis
                
                if output_dir:
                    self._save_visualization(ohlcv_vis, output_dir, f"{symbol}_ohlcv.png")
            
            # Visualize orderbook if available
            if 'orderbook' in market_data and market_data['orderbook']:
                orderbook_vis = self._visualize_orderbook(market_data['orderbook'], symbol)
                visualizations['orderbook'] = orderbook_vis
                
                if output_dir:
                    self._save_visualization(orderbook_vis, output_dir, f"{symbol}_orderbook.png")
            
            # Visualize trades if available
            if 'trades' in market_data and market_data['trades']:
                trades_vis = self._visualize_trades(market_data['trades'], symbol)
                visualizations['trades'] = trades_vis
                
                if output_dir:
                    self._save_visualization(trades_vis, output_dir, f"{symbol}_trades.png")
            
            return visualizations
            
        except Exception as e:
            self.logger.error(f"Error visualizing market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}
    
    def _visualize_ohlcv(self, ohlcv_data: Dict[str, Any], symbol: str) -> str:
        """Generate OHLCV visualization.
        
        Args:
            ohlcv_data: OHLCV data dictionary
            symbol: Trading pair symbol
        
        Returns:
            Base64-encoded PNG image
        """
        # Create figure with 2 subplots (price and volume)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f"OHLCV Data for {symbol}", fontsize=16)
        
        # Get the base timeframe data
        df = None
        
        if isinstance(ohlcv_data, dict):
            # Try to get base timeframe first, then any available timeframe
            timeframe_priority = ['base', 'ltf', 'mtf', 'htf']
            
            for tf in timeframe_priority:
                if tf in ohlcv_data:
                    tf_data = ohlcv_data[tf]
                    
                    if isinstance(tf_data, pd.DataFrame) and not tf_data.empty:
                        df = tf_data
                        break
                    elif isinstance(tf_data, dict) and 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                        df = tf_data['data']
                        break
        elif isinstance(ohlcv_data, pd.DataFrame):
            df = ohlcv_data
        
        if df is None or df.empty:
            self.logger.warning(f"No valid OHLCV data for visualization")
            # Create an empty visualization
            fig.text(0.5, 0.5, "No OHLCV data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # Ensure DataFrame has datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                # Convert timestamp column to datetime
                df.set_index('timestamp', inplace=True)
                df.index = pd.to_datetime(df.index, unit='ms')
            else:
                # Create a dummy index
                df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='T')
        
        # Create candlestick chart
        ax1.set_title(f"Price (Timeframe: {getattr(df, 'timeframe', 'unknown')})")
        
        # Calculate candlestick colors
        colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]
        
        # Plot candlesticks
        for i, (timestamp, row) in enumerate(df.iterrows()):
            # Draw body
            ax1.plot([i, i], [row['open'], row['close']], color=colors[i], linewidth=3)
            # Draw wicks
            ax1.plot([i, i], [row['low'], row['high']], color=colors[i], linewidth=1)
        
        # Set x-axis labels
        ax1.set_xticks(range(0, len(df), max(1, len(df) // 10)))
        ax1.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])
        
        # Add volume subplot
        ax2.set_title("Volume")
        ax2.bar(range(len(df)), df['volume'], color=colors, alpha=0.7)
        
        # Set x-axis labels for volume chart
        ax2.set_xticks(range(0, len(df), max(1, len(df) // 10)))
        ax2.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _visualize_orderbook(self, orderbook_data: Dict[str, Any], symbol: str) -> str:
        """Generate orderbook visualization.
        
        Args:
            orderbook_data: Orderbook data dictionary
            symbol: Trading pair symbol
        
        Returns:
            Base64-encoded PNG image
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.suptitle(f"Orderbook for {symbol}", fontsize=16)
        
        # Check if orderbook data is valid
        if not isinstance(orderbook_data, dict) or 'bids' not in orderbook_data or 'asks' not in orderbook_data:
            self.logger.warning(f"Invalid orderbook data for visualization")
            # Create an empty visualization
            fig.text(0.5, 0.5, "No orderbook data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        bids = orderbook_data['bids']
        asks = orderbook_data['asks']
        
        if not bids or not asks:
            self.logger.warning(f"Empty bids or asks in orderbook")
            # Create an empty visualization
            fig.text(0.5, 0.5, "Empty orderbook data", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # Extract price and quantity
        bid_prices = [bid[0] for bid in bids[:20]]  # Limit to 20 levels
        bid_quantities = [bid[1] for bid in bids[:20]]
        ask_prices = [ask[0] for ask in asks[:20]]
        ask_quantities = [ask[1] for ask in asks[:20]]
        
        # Cumulative quantities - use numpy's cumsum for efficiency
        bid_cumulative = np.cumsum(bid_quantities).tolist()
        ask_cumulative = np.cumsum(ask_quantities).tolist()
        
        # Plot bids (cumulative)
        ax.step(bid_prices, bid_cumulative, where='post', color='green', label='Bids')
        ax.fill_between(bid_prices, bid_cumulative, step='post', alpha=0.2, color='green')
        
        # Plot asks (cumulative)
        ax.step(ask_prices, ask_cumulative, where='post', color='red', label='Asks')
        ax.fill_between(ask_prices, ask_cumulative, step='post', alpha=0.2, color='red')
        
        # Set labels and legend
        ax.set_xlabel('Price')
        ax.set_ylabel('Cumulative Quantity')
        ax.legend()
        
        # Calculate and show spread
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid
        spread_pct = (spread / best_bid) * 100
        
        ax.axvline(x=best_bid, color='green', linestyle='--', alpha=0.7)
        ax.axvline(x=best_ask, color='red', linestyle='--', alpha=0.7)
        
        ax.text(0.5, 0.02, f"Spread: {spread:.8f} ({spread_pct:.4f}%)", 
                transform=ax.transAxes, ha='center', fontsize=10, 
                bbox=dict(facecolor='white', alpha=0.8))
        
        # Format y-axis with comma separators for large numbers
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _visualize_trades(self, trades_data: Any, symbol: str) -> str:
        """Generate trades visualization.
        
        Args:
            trades_data: Trades data
            symbol: Trading pair symbol
            
        Returns:
            Base64-encoded PNG image
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10))
        fig.suptitle(f"Recent Trades for {symbol}", fontsize=16)
        
        # Convert trades to DataFrame if needed
        if isinstance(trades_data, list):
            try:
                # Extract relevant fields
                trade_list = []
                for trade in trades_data:
                    trade_dict = {
                        'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),
                        'price': float(trade.get('price', 0)),
                        'amount': float(trade.get('amount', trade.get('quantity', 0))),
                        'side': trade.get('side', 'unknown')
                    }
                    trade_list.append(trade_dict)
                
                df = pd.DataFrame(trade_list)
                
                # Sort by timestamp
                if 'timestamp' in df.columns:
                    df.sort_values('timestamp', inplace=True)
            except Exception as e:
                self.logger.warning(f"Error converting trades to DataFrame: {str(e)}")
                fig.text(0.5, 0.5, "Error processing trades data", ha='center', va='center')
                return self._fig_to_base64(fig)
        elif isinstance(trades_data, pd.DataFrame):
            df = trades_data.copy()
            
            # Ensure columns exist
            required_cols = ['timestamp', 'price', 'amount', 'side']
            for col in required_cols:
                if col not in df.columns:
                    self.logger.warning(f"Missing column {col} in trades DataFrame")
                    fig.text(0.5, 0.5, f"Missing required column: {col}", ha='center', va='center')
                    return self._fig_to_base64(fig)
        else:
            self.logger.warning(f"Invalid trades data type: {type(trades_data)}")
            fig.text(0.5, 0.5, "Invalid trades data format", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        if df.empty:
            fig.text(0.5, 0.5, "No trades data available", ha='center', va='center')
            return self._fig_to_base64(fig)
        
        # 1. Price over time
        ax1.set_title("Price over time")
        ax1.plot(df['timestamp'], df['price'], marker='.', linestyle='-', alpha=0.7)
        
        # Color points by trade side if available
        if 'side' in df.columns:
            buy_mask = df['side'] == 'buy'
            sell_mask = df['side'] == 'sell'
            
            ax1.scatter(df.loc[buy_mask, 'timestamp'], df.loc[buy_mask, 'price'], 
                        color='green', s=20, alpha=0.7, label='Buy')
            ax1.scatter(df.loc[sell_mask, 'timestamp'], df.loc[sell_mask, 'price'], 
                        color='red', s=20, alpha=0.7, label='Sell')
            ax1.legend()
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        # 2. Trade sizes
        ax2.set_title("Trade Sizes")
        ax2.bar(range(len(df)), df['amount'], color='blue', alpha=0.7)
        ax2.set_ylabel("Amount")
        ax2.set_xlabel("Trade Number")
        
        # 3. Buy vs Sell volumes
        ax3.set_title("Buy vs Sell Volume")
        
        if 'side' in df.columns:
            # Group by side and sum amounts
            volume_by_side = df.groupby('side')['amount'].sum()
            
            # Create pie chart
            colors = {'buy': 'green', 'sell': 'red'}
            pie_colors = [colors.get(side, 'gray') for side in volume_by_side.index]
            
            ax3.pie(volume_by_side, labels=volume_by_side.index, autopct='%1.1f%%', 
                   startangle=90, colors=pie_colors)
            ax3.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        else:
            ax3.text(0.5, 0.5, "No side information available", ha='center', va='center', transform=ax3.transAxes)
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convert Matplotlib figure to base64-encoded string.
        
        Args:
            fig: Matplotlib figure
            
        Returns:
            Base64-encoded PNG image
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return img_str
    
    def _save_visualization(self, base64_img: str, output_dir: str, filename: str) -> None:
        """Save base64-encoded visualization to file.
        
        Args:
            base64_img: Base64-encoded image
            output_dir: Output directory
            filename: Output filename
        """
        try:
            img_data = base64.b64decode(base64_img)
            output_path = Path(output_dir) / filename
            
            with open(output_path, 'wb') as f:
                f.write(img_data)
                
            self.logger.debug(f"Saved visualization to {output_path}")
            
        except Exception as e:
            self.logger.warning(f"Error saving visualization: {str(e)}")

    def validate_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate market data for completeness and freshness.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Validation result dictionary
        """
        result = {
            'overall_valid': True,
            'ohlcv_valid': True,
            'orderbook_valid': True,
            'trades_valid': True,
            'details': {}
        }
        
        # Record validation operation
        operation = self.metrics_manager.start_operation("validate_market_data")
        
        try:
            # Configure logging verbosity
            verbose = self.debug_config.get('verbose_validation', False)
            details = {}
            
            # Validate OHLCV data
            ohlcv_valid = True
            ohlcv_details = {}
            
            for tf_key, df in market_data['ohlcv'].items():
                tf_valid = True
                tf_details = {}
                
                # Check if data is a valid DataFrame
                if not isinstance(df, pd.DataFrame):
                    # Try to convert to DataFrame if it's a list
                    if isinstance(df, list):
                        if not df:  # Empty list
                            tf_valid = False
                            tf_details['error'] = "Empty data list"
                        else:
                            try:
                                # Try to convert list to DataFrame
                                df = pd.DataFrame(df)
                                # Update the market data with the DataFrame
                                market_data['ohlcv'][tf_key] = df
                            except Exception as e:
                                tf_valid = False
                                tf_details['error'] = f"Could not convert list to DataFrame: {str(e)}"
                    else:
                        tf_valid = False
                        tf_details['error'] = f"Invalid data type: {type(df)}"
                
                # Now check if DataFrame is empty (only if it's a DataFrame now)
                if isinstance(df, pd.DataFrame) and df.empty:
                    tf_valid = False
                    tf_details['error'] = "Empty DataFrame"
                elif isinstance(df, pd.DataFrame):
                    # Check minimum number of candles
                    min_candles = self.validation_config.get('min_ohlcv_candles', 20)
                    if len(df) < min_candles:
                        tf_valid = False
                        tf_details['candle_count_issue'] = f"Only {len(df)} candles, minimum {min_candles} required"
                    
                    # Check freshness of newest candle
                    if isinstance(df.index, pd.DatetimeIndex):
                        latest_ts = df.index.max()
                        # Ensure latest_ts has timezone info if it doesn't already
                        if latest_ts.tzinfo is None:
                            latest_ts = latest_ts.tz_localize('UTC')
                    else:
                        # If index is not datetime, try to use last row's timestamp
                        latest_ts = pd.to_datetime(df.iloc[-1].name, unit='ms').tz_localize('UTC')
                    
                    max_age_seconds = self.validation_config.get('max_ohlcv_age_seconds', 300)
                    age_seconds = (pd.Timestamp.now(tz='UTC') - latest_ts).total_seconds()
                    
                    if age_seconds > max_age_seconds:
                        tf_valid = False
                        tf_details['freshness_issue'] = f"Newest candle is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                
                ohlcv_details[tf_key] = {
                    'valid': tf_valid,
                    'details': tf_details
                }
                
                if not tf_valid:
                    ohlcv_valid = False
            
            result['ohlcv_valid'] = ohlcv_valid
            details['ohlcv'] = ohlcv_details
            
            # Validate orderbook
            orderbook_valid = True
            orderbook_details = {}
            
            if market_data['orderbook'] is None:
                orderbook_valid = False
                orderbook_details['error'] = "No orderbook data"
            else:
                # Check the structure of orderbook data which might be nested in result
                orderbook_data = market_data['orderbook']
                
                # Handle case where orderbook is in result.b (bids) and result.a (asks) format
                if 'result' in orderbook_data and isinstance(orderbook_data['result'], dict):
                    result_data = orderbook_data['result']
                    if 'b' in result_data and 'a' in result_data:
                        # Extract bids and asks from the result structure
                        orderbook_data['bids'] = result_data.get('b', [])
                        orderbook_data['asks'] = result_data.get('a', [])
                
                # Now check for bids and asks
                if 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                    orderbook_valid = False
                    orderbook_details['structure_issue'] = f"Missing bids or asks fields. Keys: {list(orderbook_data.keys())}"
                else:
                    # Check minimum number of levels
                    min_levels = self.validation_config.get('min_orderbook_levels', 5)
                    bid_length = len(orderbook_data['bids']) if isinstance(orderbook_data['bids'], list) else 0
                    ask_length = len(orderbook_data['asks']) if isinstance(orderbook_data['asks'], list) else 0
                    
                    if (bid_length < min_levels or ask_length < min_levels):
                        orderbook_valid = False
                        orderbook_details['depth_issue'] = (
                            f"Insufficient depth: {bid_length} bids, "
                            f"{ask_length} asks, minimum {min_levels} required"
                        )
                
                # Check freshness if timestamp is available
                if 'timestamp' in orderbook_data:
                    max_age_seconds = self.validation_config.get('max_orderbook_age_seconds', 60)
                    age_seconds = (time.time() * 1000 - orderbook_data['timestamp']) / 1000
                    
                    if age_seconds > max_age_seconds:
                        orderbook_valid = False
                        orderbook_details['freshness_issue'] = f"Orderbook is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
            
            result['orderbook_valid'] = orderbook_valid
            details['orderbook'] = orderbook_details
            
            # Validate trades
            trades_valid = True
            trades_details = {}
            
            if market_data['trades'] is None:
                trades_valid = False
                trades_details['error'] = "No trades data"
            else:
                # Handle different trades data structures
                trades_data = market_data['trades']
                
                # If trades is a dict, it might have the actual trades under 'list' or 'result'
                if isinstance(trades_data, dict):
                    # Try to extract trades list from common nested structures
                    if 'result' in trades_data and isinstance(trades_data['result'], dict) and 'list' in trades_data['result']:
                        trades_data = trades_data['result']['list']
                    elif 'list' in trades_data:
                        trades_data = trades_data['list']
                    elif 'result' in trades_data and isinstance(trades_data['result'], list):
                        # Sometimes result itself might be the list
                        trades_data = trades_data['result']
                
                # Now check if trades is a list
                if not isinstance(trades_data, list):
                    trades_valid = False
                    trades_details['error'] = f"Trades data must be a list, got {type(trades_data)}. Keys: {list(market_data['trades'].keys()) if isinstance(market_data['trades'], dict) else 'N/A'}"
                else:
                    # Check minimum number of trades
                    min_trades = self.validation_config.get('min_trades_count', 5)
                    if len(trades_data) < min_trades:
                        trades_valid = False
                        trades_details['count_issue'] = f"Only {len(trades_data)} trades, minimum {min_trades} required"
                    
                    # Check freshness of newest trade, but only if there are trades
                    if trades_data and len(trades_data) > 0:
                        # First make sure we have valid trade objects
                        valid_trades = [trade for trade in trades_data 
                                      if isinstance(trade, dict) and 'timestamp' in trade]
                        
                        if valid_trades:
                            newest_ts = max(trade['timestamp'] for trade in valid_trades)
                            max_age_seconds = self.validation_config.get('max_trades_age_seconds', 300)
                            age_seconds = (time.time() * 1000 - newest_ts) / 1000
                            
                            if age_seconds > max_age_seconds:
                                trades_valid = False
                                trades_details['freshness_issue'] = f"Newest trade is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                        else:
                            trades_valid = False
                            trades_details['format_issue'] = "No valid trade objects with timestamp found"
            
            result['trades_valid'] = trades_valid
            details['trades'] = trades_details
            
            # Set overall validity
            result['overall_valid'] = ohlcv_valid and orderbook_valid and trades_valid
            result['details'] = details
            
            # Log validation results if verbose
            if verbose:
                if result['overall_valid']:
                    self.logger.debug(f"Market data validation passed for {self.symbol}")
                else:
                    self.logger.warning(f"Market data validation failed for {self.symbol}: {details}")
            
            # Record metrics
            self.metrics_manager.record_metric('validation_passed', int(result['overall_valid']))
            self.metrics_manager.record_metric('ohlcv_valid', int(result['ohlcv_valid']))
            self.metrics_manager.record_metric('orderbook_valid', int(result['orderbook_valid']))
            self.metrics_manager.record_metric('trades_valid', int(result['trades_valid']))
            
            self.metrics_manager.end_operation(operation)
            
            # If validation failed and health monitor is available, consider creating alerts
            if not result['overall_valid'] and self.health_monitor:
                # Only create alerts for persistent validation failures
                # We could track these failures in a history to only alert after multiple failures
                invalid_components = []
                if not result['ohlcv_valid']:
                    invalid_components.append("OHLCV")
                if not result['orderbook_valid']:
                    invalid_components.append("Orderbook")
                if not result['trades_valid']:
                    invalid_components.append("Trades")
                
                if invalid_components:
                    self.health_monitor._create_alert(
                        level="warning",
                        source=f"validation:{self.exchange_id}:{self.symbol_str}",
                        message=f"Market data validation failed for {self.symbol}: {', '.join(invalid_components)}"
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            if 'operation' in locals():
                self.metrics_manager.end_operation(operation, success=False)
            
            return {
                'overall_valid': False,
                'error': str(e),
                'details': {}
            }

    async def _fetch_with_retry(self, method_name: str, *args, **kwargs) -> Any:
        """Execute an exchange API method with retry logic.
        
        Args:
            method_name: Name of the ccxt method to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
        
        Returns:
            API response data
        
        Raises:
            Exception: If all retries fail
        """
        # Setup retry configuration
        max_retries = self.retry_config.get('max_retries', 3)
        retry_delay = self.retry_config.get('retry_delay_seconds', 2)
        exponential_backoff = self.retry_config.get('retry_exponential_backoff', True)
        
        # Apply rate limiting if enabled
        if self.rate_limit_config.get('enabled', True):
            await self._apply_rate_limiting()
        
        # Get the method to call
        if not hasattr(self.exchange, method_name):
            raise AttributeError(f"Exchange {self.exchange_id} does not have method {method_name}")
        
        method = getattr(self.exchange, method_name)
        
        # Try the call with retries
        last_error = None
        retry_count = 0
        
        operation = self.metrics_manager.start_operation(f"api_call_{method_name}")
        
        while retry_count <= max_retries:
            try:
                # Execute the API call
                self.logger.debug(f"Calling {method_name} (attempt {retry_count + 1}/{max_retries + 1})")
                
                # Measure the time taken
                start_time = time.time()
                response = await method(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record metrics
                self.metrics_manager.record_metric(f'api_duration_{method_name}', duration)
                self.metrics_manager.record_metric('api_success', 1)
                
                # Log the success
                self.logger.debug(f"{method_name} completed in {duration:.2f}s")
                
                # End operation
                self.metrics_manager.end_operation(operation)
                
                return response
                
            except Exception as e:
                # Record the error
                error_type = type(e).__name__
                error_message = str(e)
                
                # Log the error
                self.logger.warning(f"{method_name} failed (attempt {retry_count + 1}/{max_retries + 1}): {error_type}: {error_message}")
                
                # Record metrics
                self.metrics_manager.record_metric('api_error', 1)
                self.metrics_manager.record_metric(f'api_error_{error_type}', 1)
                
                # Store last error
                last_error = e
                
                # Check if we should retry
                if retry_count >= max_retries:
                    self.logger.error(f"All {max_retries + 1} attempts for {method_name} failed")
                    self.metrics_manager.end_operation(operation, success=False)
                    raise last_error
                
                # Calculate delay for next retry
                if exponential_backoff:
                    current_delay = retry_delay * (2 ** retry_count)
                else:
                    current_delay = retry_delay
                
                self.logger.debug(f"Retrying in {current_delay:.1f}s...")
                await asyncio.sleep(current_delay)
                
                retry_count += 1
        
        # This should never be reached due to the raise in the loop
        self.metrics_manager.end_operation(operation, success=False)
        raise last_error if last_error else RuntimeError(f"Failed to execute {method_name}")

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting based on configuration."""
        try:
            # Simple rate limiting implementation
            max_requests = self.rate_limit_config.get('max_requests_per_second', 5)
            
            # Track request time directly in the object instead of using metrics manager
            current_time = time.time()
            
            # Initialize _last_request_time attribute if it doesn't exist
            if not hasattr(self, '_last_request_time'):
                self._last_request_time = 0
            
            if self._last_request_time > 0:
                time_since_last = current_time - self._last_request_time
                min_interval = 1.0 / max_requests
                
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)
            
            # Update last request time
            self._last_request_time = current_time
            
            # Still record the metric if metrics manager is available
            if self.metrics_manager:
                self.metrics_manager.record_metric('last_api_request_time', current_time)
        except Exception as e:
            self.logger.warning(f"Error applying rate limiting: {str(e)}")
            # Continue without rate limiting if there's an error

    def _get_utc_timestamp(self, as_ms: bool = True) -> int:
        """Get current UTC timestamp.
        
        Args:
            as_ms: If True, return millisecond timestamp, else seconds
        
        Returns:
            Current UTC timestamp in milliseconds or seconds
        """
        ts = dt.datetime.now(dt.timezone.utc).timestamp()
        return int(ts * 1000) if as_ms else int(ts)

    def _format_analysis_results(self, analysis_result, symbol_str):
        """
        Format analysis results with enhanced visualization options:
        1. Structured dashboard with tables
        2. Color coding for scores (terminal colors)
        3. Visual gauges using ASCII art
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
            
        Returns:
            str: Formatted analysis output
        """
        if not analysis_result:
            return f"No analysis results available for {symbol_str}"
        
        score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
        reliability = analysis_result.get('reliability', 0)
        components = analysis_result.get('components', {})
        
        # Function to determine color based on score
        def get_color_code(value):
            if value >= 70:
                return "\033[92m"  # Green for bullish
            elif value >= 45:
                return "\033[93m"  # Yellow for neutral
            else:
                return "\033[91m"  # Red for bearish
        
        # Function to create ASCII gauge
        def create_gauge(value):
            gauge_width = 20
            filled = int((value / 100) * gauge_width)
            gauge = "["
            for i in range(gauge_width):
                if i < filled:
                    if value >= 70:
                        gauge += "█"  # Green area (filled)
                    elif value >= 45:
                        gauge += "▒"  # Yellow area (filled)
                    else:
                        gauge += "░"  # Red area (filled)
                else:
                    gauge += " "
            gauge += "]"
            return gauge
        
        # Format headers for dashboard
        header = f"\n{'=' * 60}\n"
        header += f"ANALYSIS DASHBOARD FOR {symbol_str} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"{'=' * 60}\n"
        
        # Format main confluence score
        color_code = get_color_code(score)
        reset_code = "\033[0m"
        main_score = f"CONFLUENCE SCORE: {color_code}{score:.2f}{reset_code}/100 "
        main_score += f"(Reliability: {reliability:.2f})\n"
        main_score += create_gauge(score) + "\n"
        
        # Format component scores table
        component_table = "\nCOMPONENT SCORES:\n"
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        component_table += f"| {'Component':<23} | {'Score':<8} | {'Visual':<20} |\n"
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        
        # Add components to table
        if components:
            for name, value in components.items():
                if isinstance(value, dict) and 'score' in value:
                    comp_score = value['score']
                elif isinstance(value, (int, float)):
                    comp_score = value
                else:
                    continue
                    
                color = get_color_code(comp_score)
                component_table += f"| {name:<23} | {color}{comp_score:<8.2f}{reset_code} | {create_gauge(comp_score):<20} |\n"
        
        component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
        
        # Combine all sections
        formatted_output = header + main_score + component_table
        
        # Add interpretation if available
        interpretation = analysis_result.get('overall_interpretation', '')
        if interpretation:
            formatted_output += f"\nINTERPRETATION: {interpretation}\n"
        
        formatted_output += f"{'=' * 60}\n"
        
        return formatted_output
        
    def log_analysis_result(self, analysis_result, symbol_str):
        """
        Log analysis results with enhanced formatting.
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
        """
        if not analysis_result:
            self.logger.warning(f"No analysis results available for {symbol_str}")
            return
            
        # Use the new formatted output
        formatted_analysis = self._format_analysis_results(analysis_result, symbol_str)
        self.logger.info(formatted_analysis)