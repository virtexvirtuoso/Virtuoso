"""Market data monitoring system.

This module provides monitoring functionality for market data:
- Performance monitoring
- Data quality monitoring
- System health monitoring
- Alert generation

Signal Generation Flow:
- The MarketMonitor analyzes market data and calculates confluence scores
- When a score exceeds the buy threshold (60) or falls below the sell threshold (40),
  the MarketMonitor initiates signal generation
- Signals are passed to the SignalGenerator for further processing and alert dispatch
- All thresholds are defined in the config.yaml file under analysis.confluence_thresholds
"""

import functools
import logging
import time
import asyncio
import traceback
import json
import os
import signal
import sys
import uuid
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Import and apply matplotlib silencing before matplotlib imports
from src.utils.matplotlib_utils import silence_matplotlib_logs
silence_matplotlib_logs()

import matplotlib
import psutil
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from decimal import Decimal

# Import local modules
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.health_monitor import HealthMonitor
# Import the new MarketReporter
from src.monitoring.market_reporter import MarketReporter

from src.core.formatting import AnalysisFormatter, format_analysis_result, LogFormatter

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

# Add import for liquidation cache
from src.utils.liquidation_cache import liquidation_cache

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
    
    async def validate_market_data(self, market_data):
        """Comprehensive validation of entire market data.
        
        This method is asynchronous for consistency with the rest of the codebase,
        although the individual validation methods are synchronous.
        
        Args:
            market_data: The market data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        self.logger.debug("\n=== Starting comprehensive market data validation (async) ===")
        
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
                
                # Run validation - all validators are still synchronous
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
        
        # Add volume field if it's missing but available in raw data
        if 'volume' not in ticker_data and hasattr(self, 'exchange') and self.exchange:
            try:
                # Try to get volume from the exchange's last ticker response
                if hasattr(self.exchange, 'last_ticker_response') and self.exchange.last_ticker_response:
                    raw_ticker = self.exchange.last_ticker_response
                    if isinstance(raw_ticker, dict) and 'volume' in raw_ticker:
                        ticker_data['volume'] = raw_ticker['volume']
                        self.logger.debug(f"Added missing volume field to ticker: {ticker_data['volume']}")
            except Exception as e:
                self.logger.debug(f"Could not add volume field to ticker: {str(e)}")
        
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
            alert_manager: Optional alert manager instance
            signal_generator: Optional signal generator instance
            top_symbols_manager: Optional top symbols manager instance
            market_data_manager: Optional market data manager instance
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
        # Ensure report_times is properly initialized at startup
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
        
        # Initialize MarketReporter
        self.market_reporter = MarketReporter(
            exchange=self.exchange,
            logger=self.logger,
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager
        )

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
            
            # Enhanced debug logging for incoming message
            self.logger.debug(f"RECEIVED LIQUIDATION MSG: {json.dumps(message, default=str)[:200]}...")
            
            # Extract liquidation data
            liquidation_data = data.get('data', {})
            if not liquidation_data:
                self.logger.warning("Empty liquidation data received")
                return
            
            # Format liquidation data
            liquidation = {
                'symbol': self.symbol,
                'timestamp': int(liquidation_data.get('timestamp', timestamp)),
                'price': float(liquidation_data.get('price', 0)),
                'size': float(liquidation_data.get('size', 0)),
                'side': liquidation_data.get('side', 'unknown').lower(),
                'source': 'websocket'
            }
            
            # Log liquidation event
            self.logger.warning(f"Liquidation detected: {liquidation['side']} {liquidation['size']} {self.symbol} @ {liquidation['price']}")
            
            # Save to cache
            symbol_str = self._get_symbol_string(self.symbol)
            self.logger.debug(f"SAVING TO LIQUIDATION CACHE: {symbol_str} -> {liquidation}")
            liquidation_cache.append(liquidation, symbol_str)
            
            # Verify cache immediately after saving
            cached_data = liquidation_cache.load(symbol_str)
            self.logger.debug(f"VERIFICATION - CACHE NOW CONTAINS: {len(cached_data) if cached_data else 0} events")
            
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
                
            # Start the scheduled market reports task if market_reporter is available
            if hasattr(self, 'market_reporter') and self.market_reporter is not None:
                self.logger.info("Starting scheduled market reports service...")
                # Create a background task for the market reporter's scheduled reports
                self._market_report_task = asyncio.create_task(self.market_reporter.run_scheduled_reports())
                self.logger.info("Scheduled market reports service started")
                
            # Generate initial market report on startup, regardless of scheduled times
            self.logger.info("Generating initial market report...")
            try:
                await self._generate_market_report()
                self.last_report_time = datetime.now(timezone.utc)
                self.logger.info("Initial market report generated successfully")
            except Exception as e:
                self.logger.error(f"Error generating initial market report: {str(e)}")
                self.logger.debug(traceback.format_exc())
                
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
                # Generate a report if none has been generated yet
                not self.last_report_time or
                # Or if it's a scheduled report time and enough time has passed
                (self._is_report_time() and 
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
                # Now we can properly await the validate_market_data method since it's async
                validation_result = await self.validate_market_data(market_data)
                if not validation_result:
                    self.logger.error(f"Invalid data for {symbol_str}")
                    return
            except TypeError as e:
                self.logger.error(f"Error validating market data: {str(e)}")
                # Fall back to legacy sync validation method if needed
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
        
        # Cancel the scheduled market reports task if it exists
        if hasattr(self, '_market_report_task') and self._market_report_task is not None:
            self.logger.info("Stopping scheduled market reports service...")
            self._market_report_task.cancel()
            try:
                await self._market_report_task
            except asyncio.CancelledError:
                pass  # Expected behavior when cancelling a task
            self.logger.info("Scheduled market reports service stopped")
        
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
            # Now data_validator.validate_market_data() is an ASYNCHRONOUS method
            if hasattr(self, 'data_validator') and self.data_validator is not None:
                # Call the validator's method asynchronously
                self.logger.debug("Calling data_validator.validate_market_data asynchronously")
                result = await self.data_validator.validate_market_data(market_data)
                
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
                        # Check if validate_timeframes is a coroutine function
                        if asyncio.iscoroutinefunction(self.validate_timeframes):
                            timeframe_results = await self.validate_timeframes(market_data.get('ohlcv', {}))
                        else:
                            # Call directly if it's a regular function
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


    async def validate_market_data_sync(self, market_data: Dict[str, Any]) -> bool:
        """Synchronous version of validate_market_data that delegates to the data validator.
        
        This method is now also asynchronous since the data validator's method is asynchronous,
        but it's kept for backward compatibility.
        
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
            validation_result = await self.data_validator.validate_market_data(processed_market_data)
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
                fallback_result = await self.data_validator.validate_market_data(market_data)
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
        """Process analysis result and generate signals if appropriate."""
        try:
            # Extract key information
            confluence_score = result.get('score', result.get('confluence_score', 0))
            reliability = result.get('reliability', 0)
            components = result.get('components', {})
            
            # Get thresholds from config.confluence section for consistency
            confluence_config = self.config.get('confluence', {})
            threshold_config = confluence_config.get('thresholds', {})
            buy_threshold = float(threshold_config.get('buy', 60))
            sell_threshold = float(threshold_config.get('sell', 40))
            neutral_buffer = float(threshold_config.get('neutral_buffer', 5))
            
            # Log component scores
            self.logger.debug("\n=== Component Scores ===")
            for component, score in components.items():
                self.logger.debug(f"{component}: {score}")
                
            # Display comprehensive confluence score table with top components and interpretations
            from src.core.formatting import LogFormatter
            formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=result.get('results', {}),
                weights=result.get('metadata', {}).get('weights', {}),
                reliability=reliability
            )
            self.logger.info(formatted_table)
            
            # Log detailed market interpretations separately to ensure they appear in the logs
            
            # Generate signal if score meets thresholds
            self.logger.debug(f"=== Generating Signal ===")
            # Store threshold information in result for downstream processing
            result['buy_threshold'] = buy_threshold
            result['sell_threshold'] = sell_threshold
            
            if confluence_score >= buy_threshold:
                await self._generate_signal(symbol, result)
                self.logger.info(f"Generated BUY signal for {symbol} with score {confluence_score:.2f} (threshold: {buy_threshold})")
            elif confluence_score <= sell_threshold:
                await self._generate_signal(symbol, result)
                self.logger.info(f"Generated SELL signal for {symbol} with score {confluence_score:.2f} (threshold: {sell_threshold})")
            else:
                self.logger.debug(f"No signal generated - score {confluence_score:.2f} in neutral zone (buy: {buy_threshold}, sell: {sell_threshold})")

            # Update metrics
            if self.metrics_manager:
                await self.metrics_manager.update_analysis_metrics(symbol, result)

        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _generate_signal(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Generate trading signal based on analysis results with enhanced validation and tracking.
        
        Args:
            symbol: Trading pair symbol
            analysis_result: Analysis results dictionary
        """
        try:
            # Generate unique transaction ID to trace this signal through the system
            transaction_id = str(uuid.uuid4())[:8]
            signal_id = str(uuid.uuid4())[:8]
            
            self.logger.debug(f"\n=== Generating Signal [TXN:{transaction_id}][SIG:{signal_id}] ===")
            self.logger.debug(f"Processing signal for {symbol} with {len(analysis_result.keys())} analysis components")
            
            # Extract and validate core components
            confluence_score = float(analysis_result.get('score', analysis_result.get('confluence_score', 0)))
            reliability = float(analysis_result.get('reliability', 100.0))  # Default to full reliability, keep 0-100 scale
            
            # Get components and results
            components = analysis_result.get('components', {})
            results = analysis_result.get('results', {})
            
            # Get current price with fallbacks
            price = None
            if 'current_price' in analysis_result:
                price = float(analysis_result['current_price'])
            elif 'price' in analysis_result:
                price = float(analysis_result['price'])
            elif 'metadata' in analysis_result and 'price' in analysis_result['metadata']:
                price = float(analysis_result['metadata']['price'])
            
            if price is None and hasattr(self, 'market_data_manager'):
                try:
                    market_data = await self.market_data_manager.get_market_data(symbol)
                    if market_data and 'ticker' in market_data:
                        price = float(market_data['ticker'].get('last', market_data['ticker'].get('close', 0)))
                except Exception as e:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] Error getting price from market data: {str(e)}")
            
            # Get thresholds from config
            config = self.config.get('confluence', {}).get('thresholds', {})
            buy_threshold = float(config.get('buy', 70))
            sell_threshold = float(config.get('sell', 30))
            
            # Create enhanced signal data
            signal_data = {
                'symbol': symbol,
                'confluence_score': confluence_score,
                'components': components,
                'results': results,
                'weights': analysis_result.get('metadata', {}).get('weights', {}),
                'reliability': reliability,
                'price': price,
                'transaction_id': transaction_id,
                'signal_id': signal_id,
                'buy_threshold': buy_threshold,
                'sell_threshold': sell_threshold
            }
            
            # Add enhanced analysis data if available
            if 'market_interpretations' in analysis_result:
                signal_data['market_interpretations'] = analysis_result['market_interpretations']
            
            if 'actionable_insights' in analysis_result:
                signal_data['actionable_insights'] = analysis_result['actionable_insights']
                
            if 'influential_components' in analysis_result:
                signal_data['influential_components'] = analysis_result['influential_components']
                
            if 'top_weighted_subcomponents' in analysis_result:
                signal_data['top_weighted_subcomponents'] = analysis_result['top_weighted_subcomponents']
            
            # Determine signal direction
            if confluence_score >= buy_threshold:
                signal_data['signal'] = 'BUY'
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Generated BUY signal for {symbol} " +
                               f"with score {confluence_score:.2f} (threshold: {buy_threshold})")
                           
                # Process signal through SignalGenerator
                if hasattr(self, 'signal_generator') and self.signal_generator:
                    try:
                        await self.signal_generator.process_signal(signal_data)
                    except Exception as e:
                        self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error in signal_generator: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        
            elif confluence_score <= sell_threshold:
                signal_data['signal'] = 'SELL'
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Generated SELL signal for {symbol} " +
                               f"with score {confluence_score:.2f} (threshold: {sell_threshold})")
                           
                # Process signal through SignalGenerator
                if hasattr(self, 'signal_generator') and self.signal_generator:
                    try:
                        await self.signal_generator.process_signal(signal_data)
                    except Exception as e:
                        self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error in signal_generator: {str(e)}")
                        self.logger.debug(traceback.format_exc())
            else:
                signal_data['signal'] = 'NEUTRAL'
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] No signal generated - " +
                                f"score {confluence_score:.2f} in neutral zone ({sell_threshold}-{buy_threshold})")
                return
                
            # Update metrics if available
            if hasattr(self, 'metrics_manager') and self.metrics_manager:
                try:
                    await self.metrics_manager.update_signal_metrics(symbol, signal_data)
                except Exception as e:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] Error updating metrics: {str(e)}")
            
            # Store signal data if database available
            if hasattr(self, 'database_client') and self.database_client:
                try:
                    await self.database_client.store_signal(symbol, signal_data)
                except Exception as e:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] Error storing signal: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

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
            
            # Validate market data (now asynchronous)
            self.logger.debug("Calling validate_market_data asynchronously for {}".format(symbol))
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
    
    async def _generate_market_report(self) -> None:
        """Generate and send comprehensive market report."""
        start_time = time.time()
        report_generation_metrics = {
            'start_time': datetime.now().isoformat(),
            'steps_completed': [],
            'errors': [],
            'warnings': [],
            'duration_ms': 0
        }
        
        try:
            self.logger.info("=" * 80)
            self.logger.info("MARKET REPORT GENERATION STARTED")
            self.logger.info("=" * 80)
            report_generation_metrics['steps_completed'].append({'step': 'initialization', 'timestamp': datetime.now().isoformat()})
            
            # Check if market_reporter is available
            if not hasattr(self, 'market_reporter') or self.market_reporter is None:
                error_msg = "Market reporter not available, cannot generate report"
                self.logger.error(error_msg)
                report_generation_metrics['errors'].append({'error': error_msg, 'timestamp': datetime.now().isoformat()})
                return
            
            # Log the market reporter details
            self.logger.info("-" * 80)
            self.logger.info("SECTION: Initializing Market Reporter")
            section_start = time.time()
            self.logger.info(f"Using market reporter: {self.market_reporter}")
            self.logger.info(f"Market reporter has top_symbols_manager: {hasattr(self.market_reporter, 'top_symbols_manager') and self.market_reporter.top_symbols_manager is not None}")
            self.logger.info(f"Market reporter has alert_manager: {hasattr(self.market_reporter, 'alert_manager') and self.market_reporter.alert_manager is not None}")
            self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
            
            # Log memory usage before report generation
            self.logger.info("-" * 80)
            self.logger.info("SECTION: Memory Usage Check (Before)")
            section_start = time.time()
            memory_before = self._get_memory_usage() if hasattr(self, '_get_memory_usage') else None
            if memory_before:
                self.logger.info(f"Memory usage before report generation: {memory_before:.2f} MB")
            self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
            
            # Log active symbols that will be processed
            self.logger.info("-" * 80)
            self.logger.info("SECTION: Symbol Check")
            section_start = time.time()
            if hasattr(self.market_reporter, 'symbols') and self.market_reporter.symbols:
                symbol_count = len(self.market_reporter.symbols)
                top_symbols = self.market_reporter.symbols[:5]  # Show first 5 symbols
                self.logger.info(f"Reporting on {symbol_count} symbols. Top symbols: {top_symbols}")
            self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
                
            report_generation_metrics['steps_completed'].append({'step': 'pre_generation_checks', 'timestamp': datetime.now().isoformat()})
            
            # Use the dedicated market reporter to generate the report
            self.logger.info("-" * 80)
            self.logger.info("SECTION: Generating Market Summary")
            section_start = time.time()
            self.logger.info("Calling market_reporter.generate_market_summary()...")
            generation_start = time.time()
            report_result = await self.market_reporter.generate_market_summary()
            generation_duration = time.time() - generation_start
            self.logger.info(f"Market summary generation completed in {generation_duration:.2f}s")
            self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
            
            report_generation_metrics['steps_completed'].append({
                'step': 'report_generation', 
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': generation_duration
            })
            
            # Log memory usage after report generation
            self.logger.info("-" * 80)
            self.logger.info("SECTION: Memory Usage Check (After)")
            section_start = time.time()
            memory_after = self._get_memory_usage() if hasattr(self, '_get_memory_usage') else None
            if memory_after and memory_before:
                memory_diff = memory_after - memory_before
                self.logger.info(f"Memory usage after report generation: {memory_after:.2f} MB (Change: {memory_diff:+.2f} MB)")
                report_generation_metrics['memory_impact_mb'] = memory_diff
            self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
            
            # Update the last report time
            self.last_report_time = datetime.now(timezone.utc)
            
            # Process report results
            self.logger.info("-" * 80)
            self.logger.info("SECTION: Processing Report Results")
            section_start = time.time()
            if report_result:
                self.logger.info(f"Market report generated successfully at {self.last_report_time}")
                
                # Log successful report details
                quality_score = report_result.get('quality_score', 'N/A')
                
                # Check which components are present
                available_components = []
                for component in ['market_overview', 'futures_premium', 'smart_money_index', 'whale_activity']:
                    if component in report_result:
                        available_components.append(component)
                        comp_data = report_result[component]
                        self.logger.info(f"  - {component.replace('_', ' ').title()}: {len(comp_data) if isinstance(comp_data, dict) else 'N/A'} data points")
                
                component_count = len(available_components)
                self.logger.info(f"Report summary: Quality score: {quality_score}, Components: {component_count}/4, Generation time: {generation_duration:.2f}s")
                
                # Log report structure details
                if self.logger.isEnabledFor(logging.DEBUG):
                    report_keys = list(report_result.keys())
                    self.logger.debug(f"Report structure: {report_keys}")
                    
                    # Check for empty components
                    empty_components = [k for k in report_keys 
                                        if isinstance(report_result[k], dict) and not any(report_result[k].values())]
                    if empty_components:
                        self.logger.warning(f"Empty components in report: {empty_components}")
                        report_generation_metrics['warnings'].append({
                            'warning': f"Empty components: {empty_components}", 
                            'timestamp': datetime.now().isoformat()
                        })
            
            # Send report to Discord as a formatted webhook message
            if hasattr(self.market_reporter, 'alert_manager') and self.market_reporter.alert_manager:
                self.logger.info("SECTION: Sending Report to Discord")
                section_start = time.time()
                
                try:
                    # First, send a simple alert notification
                    await self.market_reporter.alert_manager.send_alert(
                        level="info",
                        message="Market report generated",
                        details={"type": "market_report"}
                    )
                    
                    # Then format and send the rich Discord embed
                    if hasattr(self.market_reporter.alert_manager, 'send_discord_webhook_message'):
                        # Extract the data needed for the formatted report
                        market_overview = report_result.get('market_overview', {})
                        top_pairs = self.market_reporter.symbols[:10] if hasattr(self.market_reporter, 'symbols') else []
                        
                        # Format the report with embeds
                        formatted_report = await self.market_reporter.format_market_report(
                            overview=market_overview,
                            top_pairs=top_pairs
                        )
                        
                        # Send the formatted report via webhook
                        self.logger.info("Sending formatted market report via Discord webhook")
                        await self.market_reporter.alert_manager.send_discord_webhook_message(formatted_report)
                        self.logger.info("Formatted market report sent successfully")
                    else:
                        self.logger.warning("Discord webhook message method not available on alert manager")
                        
                    self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
                except Exception as e:
                    error_msg = f"Error sending formatted report to Discord: {str(e)}"
                    self.logger.error(error_msg)
                    self.logger.debug(traceback.format_exc())
                    report_generation_metrics['errors'].append({
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
            else:
                warning_msg = "Market report may not have been fully generated or sent"
                self.logger.warning(warning_msg)
                report_generation_metrics['warnings'].append({
                    'warning': warning_msg, 
                    'timestamp': datetime.now().isoformat()
                })
            self.logger.info(f"SECTION TIME: {time.time() - section_start:.2f}s")
            
            report_generation_metrics['steps_completed'].append({'step': 'completion', 'timestamp': datetime.now().isoformat()})
            
        except Exception as e:
            error_msg = f"Error generating market report: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            report_generation_metrics['errors'].append({
                'error': error_msg, 
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
        finally:
            # Calculate total duration
            total_duration = time.time() - start_time
            report_generation_metrics['duration_seconds'] = total_duration
            report_generation_metrics['end_time'] = datetime.now().isoformat()
            
            # Log the metrics
            self.logger.info("-" * 80)
            self.logger.info(f"MARKET REPORT GENERATION COMPLETED in {total_duration:.2f}s")
            self.logger.info("=" * 80)
            
            # Store metrics for later analysis
            if hasattr(self, 'metrics_manager') and self.metrics_manager:
                try:
                    metrics_key = f"market_report_generation_{int(time.time())}"
                    # Try different methods to store metrics based on what's available
                    if hasattr(self.metrics_manager, 'store_metric'):
                        self.metrics_manager.store_metric(metrics_key, report_generation_metrics)
                    elif hasattr(self.metrics_manager, 'record_metric'):
                        # Fallback to record_metric if available
                        duration = report_generation_metrics.get('duration', 0)
                        self.metrics_manager.record_metric(metrics_key, duration, {
                            "status": report_generation_metrics.get('status', 'unknown'),
                            "error": report_generation_metrics.get('error', None)
                        })
                    elif hasattr(self.metrics_manager, 'update_metric'):
                        # Second fallback to update_metric
                        duration = report_generation_metrics.get('duration', 0)
                        await self.metrics_manager.update_metric(
                            metrics_key, 
                            float(duration), 
                            {"status": report_generation_metrics.get('status', 'unknown')}
                        )
                    else:
                        self.logger.warning("MetricsManager doesn't have a compatible method to store metrics")
                except Exception as e:
                    self.logger.error(f"Failed to store metrics: {str(e)}")
                
            # Log detailed metrics if debug is enabled
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Report generation metrics: {json.dumps(report_generation_metrics, indent=2)}")


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
        
        # Define limits for each timeframe
        timeframe_limits = {
            'base': 1000,  # Increased from default to 1000
            'ltf': 300,    # Increased from default to 300
            'mtf': 200,    # Increased from default to 200
            'htf': 200     # Increased from default to 200
        }
        
        ohlcv_data = {}
        raw_responses = {}  # Store raw responses
        
        for tf_name, interval in timeframes.items():
            # Add delay between requests
            await asyncio.sleep(0.5)
            
            # Get appropriate limit for this timeframe
            limit = timeframe_limits[tf_name]
            self.logger.info(f"Fetching {limit} candles for {symbol} {tf_name} timeframe ({interval})")
            
            # Fetch data with specific limit for this timeframe
            raw_data = await self.exchange_manager._fetch_ohlcv(
                symbol=symbol,
                timeframe=interval,
                limit=limit
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
            self.logger.info(f"🔄 CONFLUENCE: Running confluence analysis for {symbol}")
            
            # Add detailed logging of data structure
            self.logger.debug("=== Market Data Structure ===")
            self.logger.debug(f"Market data keys: {market_data.keys()}")
            self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")
            self.logger.debug(f"Base timeframe type: {type(market_data['ohlcv']['base'])}")
            self.logger.debug(f"Base timeframe structure: {market_data['ohlcv']['base']}")
            
            # Check if alert manager is available
            if not hasattr(self, 'alert_manager') or self.alert_manager is None:
                self.logger.error(f"🔄 CONFLUENCE: Alert manager not available for {symbol} - alerts won't be sent")
            else:
                self.logger.info(f"🔄 CONFLUENCE: Alert manager is available with handlers: {self.alert_manager.handlers}")
            
            # Check if signal generator is available
            if not hasattr(self, 'signal_generator') or self.signal_generator is None:
                self.logger.error(f"🔄 CONFLUENCE: Signal generator not available for {symbol} - signals won't be generated")
                return
            else:
                self.logger.info(f"🔄 CONFLUENCE: Signal generator is available for {symbol}")
            
            # Get analysis from confluence analyzer
            try:
                self.logger.info(f"🔄 CONFLUENCE: Getting analysis from confluence analyzer for {symbol}")
                analysis_result = await self.confluence_analyzer.analyze(market_data)
                self.logger.info(f"🔄 CONFLUENCE: Analysis complete for {symbol}")
            except DataUnavailableError as e:
                self.logger.error(f"🔄 CONFLUENCE: Aborting analysis: {str(e)}")
                return
            except Exception as e:
                self.logger.warning(f"🔄 CONFLUENCE: No confluence analysis result for {symbol}: {str(e)}")
                self.logger.debug(traceback.format_exc())
                analysis_result = self._get_default_scores(symbol)

            # Generate signals based on analysis
            try:
                self.logger.info(f"🔄 CONFLUENCE: Generating signals for {symbol} with analysis result")
                signals = await self.signal_generator.generate_signals(
                    symbol=symbol,
                    market_data=market_data,
                    analysis=analysis_result
                )
                self.logger.info(f"🔄 CONFLUENCE: Signal generation complete for {symbol}")
            except Exception as e:
                self.logger.error(f"🔄 CONFLUENCE: Error generating signals for {symbol}: {str(e)}")
                self.logger.debug(traceback.format_exc())
                return

            # Process any signals through alert manager
            if signals:
                self.logger.info(f"🔄 CONFLUENCE: Generated signals for {symbol}: {signals}")
                try:
                    if self.alert_manager:
                        self.logger.info(f"🔄 CONFLUENCE: Sending signals to alert manager for {symbol}")
                        await self.alert_manager.process_signals(signals)
                        self.logger.info(f"🔄 CONFLUENCE: Signals processed by alert manager for {symbol}")
                    else:
                        self.logger.error(f"🔄 CONFLUENCE: Alert manager not available for {symbol}")
                except Exception as e:
                    self.logger.error(f"🔄 CONFLUENCE: Error processing signals for {symbol}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
            else:
                self.logger.debug(f"🔄 CONFLUENCE: No signals generated for {symbol}")

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
            
            # Fetch OHLCV data with increased limit to ensure enough data for higher timeframes
            # For base timeframe (1m), fetch 1000 points
            raw_ohlcv = await self._fetch_with_retry("fetch_ohlcv", symbol_str, timeframe="1m", limit=1000)
            self.logger.debug(f"\n=== Raw OHLCV Response for {symbol_str} ===")
            
            if isinstance(raw_ohlcv, list):
                self.logger.debug(f"OHLCV data is a list with {len(raw_ohlcv)} items")
            else:
                self.logger.debug(f"OHLCV data type: {type(raw_ohlcv)}")
                if isinstance(raw_ohlcv, dict):
                    self.logger.debug(f"OHLCV keys: {list(raw_ohlcv.keys())}")
            
            self.logger.debug("=== End Raw OHLCV Response ===\n")
            
            # Standardize OHLCV data
            ohlcv_data = self._standardize_ohlcv(raw_ohlcv)
            
            # Count data points in each timeframe after standardization
            for tf, df in ohlcv_data.items():
                if isinstance(df, pd.DataFrame):
                    self.logger.debug(f"Standardized {tf} timeframe has {len(df)} data points")
                    
                    # If higher timeframes don't have enough data points, try to fetch more
                    if tf in ['mtf', 'htf'] and len(df) < 50:  # Minimum 50 data points for higher timeframes
                        timeframe_map = {
                            'mtf': '30m',  # Typical MTF timeframe
                            'htf': '4h'    # Typical HTF timeframe
                        }
                        if tf in timeframe_map:
                            self.logger.info(f"Fetching additional data for {tf} timeframe ({timeframe_map[tf]})")
                            try:
                                # Fetch data directly for this timeframe
                                tf_data = await self._fetch_with_retry(
                                    "fetch_ohlcv", 
                                    symbol_str, 
                                    timeframe=timeframe_map[tf], 
                                    limit=200  # Fetch 200 candles for higher timeframes
                                )
                                
                                if tf_data and len(tf_data) > 0:
                                    # Convert to DataFrame
                                    tf_df = pd.DataFrame(tf_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                                    
                                    # Process timestamp and ensure numeric columns
                                    tf_df['timestamp'] = pd.to_numeric(tf_df['timestamp'])
                                    for col in ['open', 'high', 'low', 'close', 'volume']:
                                        tf_df[col] = pd.to_numeric(tf_df[col])
                                    
                                    # Convert timestamp to datetime
                                    tf_df['datetime'] = pd.to_datetime(tf_df['timestamp'], unit='ms')
                                    
                                    # Use this data for the timeframe
                                    ohlcv_data[tf] = tf_df
                                    self.logger.info(f"Successfully fetched {len(tf_df)} candles for {tf} timeframe")
                            except Exception as e:
                                self.logger.warning(f"Error fetching additional data for {tf}: {str(e)}")
                else:
                    self.logger.debug(f"Standardized {tf} timeframe is not a DataFrame: {type(df)}")
            
            # Fetch orderbook data with increased depth
            orderbook = await self._fetch_with_retry("fetch_order_book", symbol_str, limit=200)
            
            # Add timestamp to orderbook data if missing
            if isinstance(orderbook, dict) and 'timestamp' not in orderbook:
                orderbook['timestamp'] = self.timestamp_utility.get_utc_timestamp()
                self.logger.debug(f"Added missing timestamp to orderbook data: {orderbook['timestamp']}")
                
            # Log orderbook data stats
            if isinstance(orderbook, dict):
                ask_count = len(orderbook.get('asks', []))
                bid_count = len(orderbook.get('bids', []))
                self.logger.debug(f"Orderbook: {ask_count} asks, {bid_count} bids")
            
            # Fetch ticker data
            ticker = await self._fetch_with_retry("fetch_ticker", symbol_str)
            
            # Fetch recent trades with increased limit
            trades = await self._fetch_with_retry("fetch_trades", symbol_str, limit=1000)
            
            # Verify we got enough trades
            if isinstance(trades, list):
                self.logger.debug(f"Fetched {len(trades)} trades")
                
                # If we didn't get enough trades, try again with a different approach
                if len(trades) < 1000:
                    self.logger.info(f"Only fetched {len(trades)} trades, attempting to fetch more")
                    
                    try:
                        # Some exchanges support pagination or since_id
                        # Try to fetch more trades in batches
                        total_trades = trades.copy()
                        
                        # If we have trades, get the oldest timestamp
                        if len(trades) > 0:
                            if isinstance(trades[0], dict) and 'timestamp' in trades[0]:
                                oldest_timestamp = min(t['timestamp'] for t in trades if 'timestamp' in t)
                                
                                # Try to fetch older trades
                                older_trades = await self._fetch_with_retry(
                                    "fetch_trades", 
                                    symbol_str, 
                                    limit=1000,
                                    params={"until": oldest_timestamp - 1}  # Get trades before the oldest we have
                                )
                                
                                if isinstance(older_trades, list) and len(older_trades) > 0:
                                    total_trades.extend(older_trades)
                                    self.logger.info(f"Fetched {len(older_trades)} additional trades, total now: {len(total_trades)}")
                                    
                                    # Update trades with the combined list
                                    trades = total_trades
                        
                    except Exception as e:
                        self.logger.warning(f"Error fetching additional trades: {str(e)}")
                        # Continue with what we have
                        
            elif isinstance(trades, dict):
                self.logger.debug(f"Trades data is a dict with keys: {list(trades.keys())}")
            else:
                self.logger.debug(f"Trades data type: {type(trades)}")
            
            # Try to get liquidation data from cache
            liquidations = liquidation_cache.load(symbol_str)
            
            # Fetch other market data
            ticker = await self._fetch_with_retry("fetch_ticker", symbol_str)
            orderbook = await self._fetch_with_retry("fetch_order_book", symbol_str, limit=100)
            trades = await self._fetch_with_retry("fetch_trades", symbol_str, limit=100)
            
            # Load long/short ratio if available
            long_short_ratio = None
            try:
                long_short_ratio = await self.exchange_manager.fetch_long_short_ratio(symbol_str)
            except Exception as e:
                self.logger.warning(f"Could not fetch long/short ratio: {str(e)}")
            
            # Get funding rate if available
            funding_rate = ticker.get('fundingRate', None)
            if not funding_rate:
                try:
                    funding_info = await self.exchange_manager.fetch_funding_rate(symbol_str)
                    funding_rate = funding_info.get('fundingRate', 0)
                except Exception as e:
                    self.logger.warning(f"Could not fetch funding rate: {str(e)}")
                    funding_rate = 0
            
            # Combine all market data
            market_data = {
                'symbol': symbol_str,
                'ohlcv': ohlcv_data,
                'orderbook': orderbook,
                'ticker': ticker,
                'trades': trades,
                'funding': {'rate': funding_rate},
                'sentiment': {
                    'long_short_ratio': long_short_ratio,
                    'liquidations': liquidations or [],
                    'funding_rate': funding_rate
                },
                'timestamp': self.timestamp_utility.get_utc_timestamp()
            }
            
            # Update cache
            self._market_data_cache[symbol_str] = {
                'data': market_data,
                'timestamp': self.timestamp_utility.get_utc_timestamp()
            }
            
            fetch_end = self.timestamp_utility.get_utc_timestamp()
            fetch_duration = (fetch_end - fetch_start) / 1000.0
            self.logger.debug(f"Market data fetch for {symbol_str} completed in {fetch_duration:.2f}s")
            
            # Log detailed data count before returning
            self.logger.info(f"Market data for {symbol_str} prepared with following data points:")
            for tf, df in ohlcv_data.items():
                if isinstance(df, pd.DataFrame):
                    self.logger.info(f"  - {tf} timeframe: {len(df)} data points")
            
            if liquidations:
                self.logger.info(f"  - Liquidations: {len(liquidations)} events from cache")
            
            return market_data
        
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {}

    def _standardize_ohlcv(self, raw_ohlcv) -> Dict[str, Any]:
        """
        Standardize OHLCV data from the exchange into a consistent format.
        Properly resamples data for different timeframes.
        
        Args:
            raw_ohlcv: The raw OHLCV data from the exchange
            
        Returns:
            Dict containing standardized OHLCV data with timeframes
        """
        try:
            self.logger.debug(f"Starting standardization of OHLCV data")
            
            if not raw_ohlcv or len(raw_ohlcv) == 0:
                self.logger.warning("Empty OHLCV data received")
                return {
                    'base': pd.DataFrame(),
                    'ltf': pd.DataFrame(),
                    'mtf': pd.DataFrame(),
                    'htf': pd.DataFrame()
                }
            
            # Log raw data information    
            if isinstance(raw_ohlcv, list):
                self.logger.debug(f"Raw OHLCV is a list with {len(raw_ohlcv)} entries")
            elif isinstance(raw_ohlcv, dict):
                self.logger.debug(f"Raw OHLCV is a dict with keys: {list(raw_ohlcv.keys())}")
            else:
                self.logger.debug(f"Raw OHLCV has type: {type(raw_ohlcv)}")
                
            # Convert to dataframe if it's a list of lists or dict
            if isinstance(raw_ohlcv, list):
                if len(raw_ohlcv) == 0:
                    return {
                        'base': pd.DataFrame(),
                        'ltf': pd.DataFrame(),
                        'mtf': pd.DataFrame(),
                        'htf': pd.DataFrame()
                    }
                    
                # Handle different formats from exchanges
                if isinstance(raw_ohlcv[0], list):
                    # Format: [timestamp, open, high, low, close, volume]
                    self.logger.debug(f"Processing list of lists format with {len(raw_ohlcv)} entries")
                    df = pd.DataFrame(raw_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    self.logger.debug(f"Created DataFrame with shape {df.shape}")
                elif isinstance(raw_ohlcv[0], dict):
                    # Common dict format from exchanges
                    self.logger.debug(f"Processing list of dicts format with {len(raw_ohlcv)} entries")
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
                    
                    # Log original columns before mapping
                    self.logger.debug(f"Original columns: {df.columns.tolist()}")
                    
                    df = df.rename(columns={col: new_col for col, new_col in column_mapping.items() if col in df.columns})
                    self.logger.debug(f"DataFrame after column mapping: {df.shape}, columns: {df.columns.tolist()}")
            elif isinstance(raw_ohlcv, dict):
                # Some exchanges return dict with timeframes
                self.logger.debug(f"Processing dictionary format with keys: {list(raw_ohlcv.keys())}")
                timeframes = {}
                for tf_key, candles in raw_ohlcv.items():
                    if isinstance(candles, list) and len(candles) > 0:
                        self.logger.debug(f"Processing timeframe {tf_key} with {len(candles)} candles")
                        tf_df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        timeframes[tf_key] = tf_df
                
                if timeframes:
                    return timeframes
                
                # Handle other dict formats
                self.logger.warning(f"Unsupported OHLCV dict format: {list(raw_ohlcv.keys())}")
                return {
                    'base': pd.DataFrame(),
                    'ltf': pd.DataFrame(),
                    'mtf': pd.DataFrame(),
                    'htf': pd.DataFrame()
                }
            else:
                self.logger.warning(f"Unsupported OHLCV data type: {type(raw_ohlcv)}")
                return {
                    'base': pd.DataFrame(),
                    'ltf': pd.DataFrame(),
                    'mtf': pd.DataFrame(),
                    'htf': pd.DataFrame()
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
            
            # Set timestamp as index for resampling
            if 'timestamp' in df.columns:
                # Convert timestamp to datetime for proper resampling
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.set_index('datetime')
            
            # Create timeframe data with proper resampling
            # Get the timeframe configurations from config
            timeframe_config = self.config.get('timeframes', {
                'base': {'interval': '1m'},
                'ltf': {'interval': '5m'},
                'mtf': {'interval': '30m'},
                'htf': {'interval': '4h'}
            })
            
            # Map CCXT timeframe strings to pandas resample rule
            timeframe_map = {
                '1m': '1Min', '5m': '5Min', '15m': '15Min', '30m': '30Min',
                '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',  # Using lowercase 'h' per pandas deprecation warning
                '1d': '1D', '3d': '3D', '1w': '1W', '1M': '1M'
            }
            
            # Function to resample OHLCV data
            def resample_ohlcv(df, rule):
                """
                Resample OHLCV data to a different timeframe with improved handling of edge cases.
                
                Args:
                    df: DataFrame with OHLCV data indexed by datetime
                    rule: Pandas resampling rule string
                    
                Returns:
                    Resampled DataFrame
                """
                if df.empty:
                    self.logger.warning(f"Cannot resample empty DataFrame with rule {rule}")
                    return df
                
                self.logger.debug(f"Resampling with rule: {rule}, input data has {len(df)} rows")
                
                try:
                    # Make sure timestamp is properly set as index
                    if df.index.name != 'datetime' and 'datetime' in df.columns:
                        df = df.set_index('datetime')
                        self.logger.debug("Setting datetime as index before resampling")
                    
                    # Handle columns that might be missing
                    agg_dict = {}
                    for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']:
                        if col in df.columns:
                            if col == 'open':
                                agg_dict[col] = 'first'
                            elif col == 'high':
                                agg_dict[col] = 'max'
                            elif col == 'low':
                                agg_dict[col] = 'min'
                            elif col == 'close':
                                agg_dict[col] = 'last'
                            elif col == 'volume':
                                agg_dict[col] = 'sum'
                            elif col == 'timestamp':
                                agg_dict[col] = 'first'  # Keep original timestamp
                    
                    # Perform the resampling
                    resampled = df.resample(rule).agg(agg_dict)
                    
                    # Fill missing values for OHLC if needed
                    # For volume, we keep NaN as 0
                    if 'volume' in resampled.columns:
                        resampled['volume'] = resampled['volume'].fillna(0)
                    
                    # Forward fill price columns (open, high, low, close)
                    # This helps with continuity when there are gaps
                    for col in ['open', 'high', 'low', 'close']:
                        if col in resampled.columns:
                            resampled[col] = resampled[col].ffill()
                    
                    # Reset index to have datetime as a column
                    resampled = resampled.reset_index()
                    
                    # Log data points before and after resampling
                    self.logger.debug(f"Resampling with rule {rule}: {len(df)} rows -> {len(resampled)} rows")
                    
                    # Drop rows with all NaN values if any
                    if resampled.isna().all(axis=1).any():
                        orig_len = len(resampled)
                        resampled = resampled.dropna(how='all')
                        dropped = orig_len - len(resampled)
                        if dropped > 0:
                            self.logger.debug(f"Dropped {dropped} rows with all NaN values after resampling")
                    
                    return resampled
                    
                except Exception as e:
                    self.logger.error(f"Error during resampling with rule {rule}: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    # Return the original data if resampling fails
                    return df.reset_index() if hasattr(df, 'reset_index') else df
            
            # Create properly resampled timeframes
            result = {}
            
            # Base timeframe (usually the raw data)
            base_tf = timeframe_config.get('base', {}).get('interval', '1m')
            result['base'] = df.copy().reset_index()  # No resampling needed for base
            
            # LTF (Lower TimeFrame)
            ltf = timeframe_config.get('ltf', {}).get('interval', '5m')
            ltf_rule = timeframe_map.get(ltf, '5Min')
            result['ltf'] = resample_ohlcv(df, ltf_rule)
            
            # MTF (Middle TimeFrame)
            mtf = timeframe_config.get('mtf', {}).get('interval', '30m')
            mtf_rule = timeframe_map.get(mtf, '30Min')
            result['mtf'] = resample_ohlcv(df, mtf_rule)
            
            # HTF (Higher TimeFrame)
            htf = timeframe_config.get('htf', {}).get('interval', '4h')
            # Use lowercase 'h' instead of uppercase 'H' (pandas deprecation)
            htf_rule = timeframe_map.get(htf, '4h')
            result['htf'] = resample_ohlcv(df, htf_rule)
            
            # Log the shapes of each timeframe DataFrame
            self.logger.debug(f"Standardized OHLCV data shapes:")
            for tf, tf_df in result.items():
                self.logger.debug(f"  {tf}: {tf_df.shape}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error standardizing OHLCV data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {
                'base': pd.DataFrame(),
                'ltf': pd.DataFrame(),
                'mtf': pd.DataFrame(),
                'htf': pd.DataFrame()
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
            
            if 'orderbook' not in market_data or market_data['orderbook'] is None:
                orderbook_valid = False
                orderbook_details['error'] = "No orderbook data"
            else:
                # Check the structure of orderbook data which might be nested in result
                orderbook_data = market_data['orderbook']
                
                # Handle case where orderbook is in result.b (bids) and result.a (asks) format (Bybit format)
                if 'result' in orderbook_data and isinstance(orderbook_data['result'], dict):
                    result_data = orderbook_data['result']
                    if 'b' in result_data and 'a' in result_data:
                        # Extract bids and asks directly from the Bybit structure
                        bids = result_data['b']
                        asks = result_data['a']
                        timestamp = result_data.get('ts', orderbook_data.get('timestamp', int(time.time() * 1000)))
                        
                        # Update the orderbook data with the extracted values
                        orderbook_data['bids'] = bids
                        orderbook_data['asks'] = asks
                        orderbook_data['timestamp'] = timestamp
                        
                        # Update the original market data
                        market_data['orderbook'] = orderbook_data
                
                # Now check if the extracted or original bids/asks are present
                if 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                    orderbook_valid = False
                    orderbook_details['structure_issue'] = "Missing bids or asks"
                elif not isinstance(orderbook_data['bids'], list) or not isinstance(orderbook_data['asks'], list):
                    orderbook_valid = False
                    orderbook_details['type_issue'] = "Bids and asks must be lists"
                elif not orderbook_data['bids'] or not orderbook_data['asks']:
                    orderbook_valid = False
                    orderbook_details['empty_issue'] = "Empty bids or asks"
                else:
                    # Check minimum depth
                    min_depth = self.validation_config.get('min_orderbook_depth', 5)
                    if len(orderbook_data['bids']) < min_depth or len(orderbook_data['asks']) < min_depth:
                        orderbook_valid = False
                        orderbook_details['depth_issue'] = f"Orderbook depth too shallow (min {min_depth}): bids={len(orderbook_data['bids'])}, asks={len(orderbook_data['asks'])}"
                    
                    # Check freshness if timestamp available
                    if 'timestamp' in orderbook_data:
                        max_age_seconds = self.validation_config.get('max_orderbook_age_seconds', 60)
                        age_seconds = (int(time.time() * 1000) - orderbook_data['timestamp']) / 1000
                        
                        if age_seconds > max_age_seconds:
                            orderbook_valid = False
                            orderbook_details['freshness_issue'] = f"Orderbook is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                
            result['orderbook_valid'] = orderbook_valid
            details['orderbook'] = orderbook_details
            
            # Combine results
            result['overall_valid'] = ohlcv_valid and orderbook_valid
            result['details'] = details
            
            # Log detailed results if verbose
            if verbose:
                self.logger.debug(f"Validation details: {details}")
                
            return result
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            # End the operation with failure status
            self.metrics_manager.end_operation(operation, success=False)
            # Return a failed validation result
            return {
                'overall_valid': False,
                'ohlcv_valid': False,
                'orderbook_valid': False,
                'trades_valid': False,
                'details': {'error': str(e)}
            }
        finally:
            # End the operation with success status
            self.metrics_manager.end_operation(operation, success=result['overall_valid'])

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
    
    # DataAnalyzer implementation of validate_market_data
    async def validate_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate market data for completeness and freshness.
        This asynchronous method returns a detailed validation result dictionary.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Validation result dictionary with details on validation status
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
            
            if 'orderbook' not in market_data or market_data['orderbook'] is None:
                orderbook_valid = False
                orderbook_details['error'] = "No orderbook data"
            else:
                # Check the structure of orderbook data which might be nested in result
                orderbook_data = market_data['orderbook']
                
                # Handle case where orderbook is in result.b (bids) and result.a (asks) format (Bybit format)
                if 'result' in orderbook_data and isinstance(orderbook_data['result'], dict):
                    result_data = orderbook_data['result']
                    if 'b' in result_data and 'a' in result_data:
                        # Extract bids and asks directly from the Bybit structure
                        bids = result_data['b']
                        asks = result_data['a']
                        timestamp = result_data.get('ts', orderbook_data.get('timestamp', int(time.time() * 1000)))
                        
                        # Update the orderbook data with the extracted values
                        orderbook_data['bids'] = bids
                        orderbook_data['asks'] = asks
                        orderbook_data['timestamp'] = timestamp
                        
                        # Update the original market data
                        market_data['orderbook'] = orderbook_data
                
                # Now check if the extracted or original bids/asks are present
                if 'bids' not in orderbook_data or 'asks' not in orderbook_data:
                    orderbook_valid = False
                    orderbook_details['structure_issue'] = "Missing bids or asks"
                elif not isinstance(orderbook_data['bids'], list) or not isinstance(orderbook_data['asks'], list):
                    orderbook_valid = False
                    orderbook_details['type_issue'] = "Bids and asks must be lists"
                elif not orderbook_data['bids'] or not orderbook_data['asks']:
                    orderbook_valid = False
                    orderbook_details['empty_issue'] = "Empty bids or asks"
                else:
                    # Check minimum depth
                    min_depth = self.validation_config.get('min_orderbook_depth', 5)
                    if len(orderbook_data['bids']) < min_depth or len(orderbook_data['asks']) < min_depth:
                        orderbook_valid = False
                        orderbook_details['depth_issue'] = f"Orderbook depth too shallow (min {min_depth}): bids={len(orderbook_data['bids'])}, asks={len(orderbook_data['asks'])}"
                    
                    # Check freshness if timestamp available
                    if 'timestamp' in orderbook_data:
                        max_age_seconds = self.validation_config.get('max_orderbook_age_seconds', 60)
                        age_seconds = (int(time.time() * 1000) - orderbook_data['timestamp']) / 1000
                        
                        if age_seconds > max_age_seconds:
                            orderbook_valid = False
                            orderbook_details['freshness_issue'] = f"Orderbook is {age_seconds:.1f}s old, maximum {max_age_seconds}s"
                
            result['orderbook_valid'] = orderbook_valid
            details['orderbook'] = orderbook_details
            
            # Combine results
            result['overall_valid'] = ohlcv_valid and orderbook_valid
            result['details'] = details
            
            # Log detailed results if verbose
            if verbose:
                self.logger.debug(f"Validation details: {details}")
                
            return result
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            # End the operation with failure status
            self.metrics_manager.end_operation(operation, success=False)
            # Return a failed validation result
            return {
                'overall_valid': False,
                'ohlcv_valid': False,
                'orderbook_valid': False,
                'trades_valid': False,
                'details': {'error': str(e)}
            }
        finally:
            # End the operation with success status
            self.metrics_manager.end_operation(operation, success=result['overall_valid'])

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
        formatted_times = [f"{t.hour:02d}:{t.minute:02d} UTC" for t in report_times]
        self.logger.info(f"Market reports scheduled for: {', '.join(formatted_times)}")
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

    async def analyze_market(self, formatted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and generate signals.
        
        This method is called from main.py and serves as the entry point for market analysis.
        It delegates to the async analysis pipeline to ensure consistent alert handling.
        
        Args:
            formatted_data: Dictionary containing formatted market data
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            symbol = formatted_data.get('symbol', 'UNKNOWN')
            self.logger.info(f"ANALYZE_MARKET: Starting analysis for {symbol}")
            
            # Create task for async analysis pipeline
            import asyncio
            loop = asyncio.get_event_loop()
            try:
                task = loop.create_task(self.analyze_confluence_and_generate_signals(formatted_data))
                self.logger.info(f"ANALYZE_MARKET: Created analysis task for {symbol}")
            except Exception as e:
                self.logger.error(f"ANALYZE_MARKET: Error creating analysis task: {str(e)}")
            
            # Return the formatted data as the analysis result
            # The actual signal generation and alerts happen asynchronously
            return formatted_data
            
        except Exception as e:
            self.logger.error(f"ANALYZE_MARKET: Error in analyze_market: {str(e)}")
            self.logger.error(traceback.format_exc())
            return formatted_data  # Return the data even on error to avoid breaking the pipeline

    async def diagnose_report_generation(self) -> Dict[str, Any]:
        """
        Perform a diagnostic test of the market report generation process.
        
        This method tests each component of the report generation process individually,
        measures performance, and identifies potential issues.
        
        Returns:
            Dict containing diagnostic results with detailed metrics for each component.
        """
        diagnostic_results = {
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'overall': {
                'success': False,
                'total_duration_seconds': 0,
                'issues_found': [],
                'recommendations': []
            }
        }
        
        start_time = time.time()
        
        try:
            self.logger.info("Starting market report generation diagnostics...")
            
            # Check if market_reporter is available
            if not hasattr(self, 'market_reporter') or self.market_reporter is None:
                diagnostic_results['overall']['issues_found'].append("Market reporter not available")
                diagnostic_results['overall']['recommendations'].append(
                    "Initialize MarketReporter in the MarketMonitor constructor"
                )
                return diagnostic_results
                
            # Test market_reporter configuration
            reporter_config = {
                'has_top_symbols_manager': hasattr(self.market_reporter, 'top_symbols_manager') and 
                                          self.market_reporter.top_symbols_manager is not None,
                'has_alert_manager': hasattr(self.market_reporter, 'alert_manager') and 
                                    self.market_reporter.alert_manager is not None,
                'symbol_count': len(self.market_reporter.symbols) if hasattr(self.market_reporter, 'symbols') else 0,
                'cache_available': hasattr(self.market_reporter, 'cache') and self.market_reporter.cache is not None
            }
            
            diagnostic_results['components']['reporter_config'] = reporter_config
            
            if not reporter_config['has_top_symbols_manager']:
                diagnostic_results['overall']['issues_found'].append("Missing top_symbols_manager")
                diagnostic_results['overall']['recommendations'].append(
                    "Initialize TopSymbolsManager and pass it to MarketReporter"
                )
                
            if not reporter_config['has_alert_manager']:
                diagnostic_results['overall']['issues_found'].append("Missing alert_manager")
                diagnostic_results['overall']['recommendations'].append(
                    "Initialize AlertManager and pass it to MarketReporter"
                )
                
            if reporter_config['symbol_count'] == 0:
                diagnostic_results['overall']['issues_found'].append("No symbols configured")
                diagnostic_results['overall']['recommendations'].append(
                    "Ensure symbols are properly configured in MarketReporter"
                )
                
            # Test individual component fetching
            components = [
                ('market_overview', self.market_reporter._calculate_market_overview),
                ('futures_premium', self.market_reporter._calculate_futures_premium),
                ('smart_money_index', self.market_reporter._calculate_smart_money_index),
                ('whale_activity', self.market_reporter._calculate_whale_activity),
                ('performance_metrics', self.market_reporter._calculate_performance_metrics)
            ]
            
            # Get a sample of symbols to test with
            test_symbols = self.market_reporter.symbols[:3] if hasattr(self.market_reporter, 'symbols') else []
            
            if not test_symbols:
                diagnostic_results['overall']['issues_found'].append("No symbols available for testing")
                diagnostic_results['overall']['recommendations'].append(
                    "Configure symbols list in MarketReporter"
                )
            else:
                # Test each component
                for component_name, component_func in components:
                    try:
                        self.logger.info(f"Testing {component_name} component...")
                        component_start = time.time()
                        component_result = await component_func(test_symbols)
                        component_duration = time.time() - component_start
                        
                        component_diagnostic = {
                            'success': component_result is not None,
                            'duration_seconds': component_duration,
                            'data_returned': bool(component_result),
                            'result_type': type(component_result).__name__ if component_result else None,
                            'memory_impact_mb': None  # Will calculate if _get_memory_usage available
                        }
                        
                        # Check for component-specific issues
                        if not component_result:
                            component_diagnostic['issues'] = ["No data returned"]
                        elif isinstance(component_result, dict):
                            component_diagnostic['keys_returned'] = list(component_result.keys())
                            
                            # Check for empty or missing required keys
                            expected_keys = {
                                'market_overview': ['regime', 'trend_strength', 'timestamp'],
                                'futures_premium': ['premiums', 'timestamp'],
                                'smart_money_index': ['index', 'timestamp'],
                                'whale_activity': ['whale_activity', 'timestamp'],
                                'performance_metrics': ['metrics', 'timestamp']
                            }
                            
                            if component_name in expected_keys:
                                missing_keys = [key for key in expected_keys[component_name] if key not in component_result]
                                if missing_keys:
                                    if not component_diagnostic.get('issues'):
                                        component_diagnostic['issues'] = []
                                    component_diagnostic['issues'].append(f"Missing required keys: {missing_keys}")
                                
                        diagnostic_results['components'][component_name] = component_diagnostic
                        
                    except Exception as e:
                        self.logger.error(f"Error testing {component_name}: {str(e)}")
                        diagnostic_results['components'][component_name] = {
                            'success': False,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        }
                        diagnostic_results['overall']['issues_found'].append(f"Component {component_name} failed: {str(e)}")
            
            # Test full report generation
            try:
                self.logger.info("Testing full report generation...")
                report_start = time.time()
                full_report = await self.market_reporter.generate_market_summary()
                report_duration = time.time() - report_start
                
                diagnostic_results['full_report'] = {
                    'success': full_report is not None,
                    'duration_seconds': report_duration,
                    'component_count': sum(1 for component in ['market_overview', 'futures_premium', 'smart_money_index', 'whale_activity'] 
                                          if component in full_report),
                    'quality_score': full_report.get('quality_score') if full_report else None,
                    'timestamp': full_report.get('timestamp') if full_report else None
                }
                
                if full_report:
                    diagnostic_results['overall']['success'] = True
                else:
                    diagnostic_results['overall']['issues_found'].append("Full report generation failed")
                    
            except Exception as e:
                self.logger.error(f"Error in full report generation: {str(e)}")
                diagnostic_results['full_report'] = {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                diagnostic_results['overall']['issues_found'].append(f"Full report generation failed: {str(e)}")
            
            # Generate recommendations based on issues found
            if not diagnostic_results['overall']['issues_found']:
                diagnostic_results['overall']['recommendations'].append(
                    "No issues found. Report generation is working correctly."
                )
            else:
                # Add specific recommendations based on detected issues
                if any("timeout" in issue.lower() for issue in diagnostic_results['overall']['issues_found']):
                    diagnostic_results['overall']['recommendations'].append(
                        "Consider increasing timeout values or optimizing network connections"
                    )
                
                if any("memory" in issue.lower() for issue in diagnostic_results['overall']['issues_found']):
                    diagnostic_results['overall']['recommendations'].append(
                        "Optimize memory usage by implementing better caching and garbage collection"
                    )
                    
                if any("missing" in issue.lower() for issue in diagnostic_results['overall']['issues_found']):
                    diagnostic_results['overall']['recommendations'].append(
                        "Ensure all required data sources are properly configured and accessible"
                    )
            
        except Exception as e:
            self.logger.error(f"Error in report diagnostics: {str(e)}")
            diagnostic_results['overall']['issues_found'].append(f"Diagnostic process failed: {str(e)}")
            diagnostic_results['overall']['error'] = str(e)
            diagnostic_results['overall']['traceback'] = traceback.format_exc()
            
        finally:
            # Calculate total duration
            diagnostic_results['overall']['total_duration_seconds'] = time.time() - start_time
            
            # Log results summary
            issue_count = len(diagnostic_results['overall']['issues_found'])
            success_status = diagnostic_results['overall']['success']
            self.logger.info(f"Report generation diagnostics completed in {diagnostic_results['overall']['total_duration_seconds']:.2f}s. " +
                            f"Success: {success_status}, Issues found: {issue_count}")
            
            if diagnostic_results['overall']['recommendations']:
                self.logger.info(f"Recommendations: {diagnostic_results['overall']['recommendations']}")
                
            return diagnostic_results

    async def test_report_component(self, component_name: str, symbol_count: int = 3) -> Dict[str, Any]:
        """
        Test a specific component of the market report generation process.
        
        This method allows testing an individual component of the market reporter
        to isolate issues and measure performance.
        
        Args:
            component_name: Name of the component to test, one of:
                            'market_overview', 'futures_premium', 'smart_money_index',
                            'whale_activity', 'performance_metrics'
            symbol_count: Number of symbols to use for testing
            
        Returns:
            Dict containing test results and metrics
        """
        start_time = time.time()
        test_result = {
            'component': component_name,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'duration_seconds': 0,
            'symbols_tested': [],
            'error': None,
            'data': None,
            'memory_before_mb': None,
            'memory_after_mb': None,
            'memory_diff_mb': None
        }
        
        try:
            self.logger.info(f"Starting test for report component: {component_name}")
            
            # Check if market_reporter is available
            if not hasattr(self, 'market_reporter') or self.market_reporter is None:
                raise ValueError("Market reporter not available, cannot test components")
            
            # Validate component name
            component_funcs = {
                'market_overview': self.market_reporter._calculate_market_overview,
                'futures_premium': self.market_reporter._calculate_futures_premium,
                'smart_money_index': self.market_reporter._calculate_smart_money_index, 
                'whale_activity': self.market_reporter._calculate_whale_activity,
                'performance_metrics': self.market_reporter._calculate_performance_metrics
            }
            
            if component_name not in component_funcs:
                raise ValueError(f"Unknown component: {component_name}. Valid components: {list(component_funcs.keys())}")
                
            # Get component function
            component_func = component_funcs[component_name]
            
            # Get test symbols
            symbols = self.market_reporter.symbols[:symbol_count] if hasattr(self.market_reporter, 'symbols') else []
            if not symbols:
                raise ValueError("No symbols available for testing")
                
            test_result['symbols_tested'] = symbols
            
            # Capture memory usage before test if available
            if hasattr(self, '_get_memory_usage') or hasattr(self.market_reporter, '_get_memory_usage'):
                memory_getter = getattr(self, '_get_memory_usage', None) or getattr(self.market_reporter, '_get_memory_usage')
                test_result['memory_before_mb'] = memory_getter()
            
            # Test with verbose logging
            self.logger.info(f"Testing {component_name} with symbols: {symbols}")
            orig_level = self.logger.level
            self.logger.setLevel(logging.DEBUG)  # Temporarily set to DEBUG for detailed logging
            
            # Set a new memory high water mark before test
            gc.collect()
            
            # Execute the component function
            component_start = time.time()
            result = await component_func(symbols)
            component_duration = time.time() - component_start
            
            # Restore original log level
            self.logger.setLevel(orig_level)
            
            # Capture memory after test
            if test_result['memory_before_mb'] is not None and hasattr(self, '_get_memory_usage'):
                test_result['memory_after_mb'] = self._get_memory_usage()
                test_result['memory_diff_mb'] = test_result['memory_after_mb'] - test_result['memory_before_mb']
            
            # Record results
            test_result['duration_seconds'] = component_duration
            test_result['success'] = result is not None
            
            # Include safe version of data for logging
            if result is not None:
                if isinstance(result, dict):
                    # Include a safe version for logging (limit size)
                    if hasattr(self.market_reporter, '_sanitize_for_logging'):
                        test_result['data'] = self.market_reporter._sanitize_for_logging(result)
                    else:
                        # Simple sanitization if _sanitize_for_logging not available
                        test_result['data'] = {
                            k: (f"[dict with {len(v)} keys]" if isinstance(v, dict) and len(v) > 10 else
                                f"[list with {len(v)} items]" if isinstance(v, list) and len(v) > 10 else
                                v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v)
                            for k, v in result.items()
                        }
                    
                    # Also include keys for easier analysis
                    test_result['result_keys'] = list(result.keys())
                    test_result['result_size'] = len(str(result))
                else:
                    test_result['data'] = str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
            
            # Force garbage collection and report
            collected = gc.collect()
            self.logger.debug(f"Garbage collection after component test: {collected} objects collected")
            
        except Exception as e:
            test_result['error'] = str(e)
            test_result['traceback'] = traceback.format_exc()
            self.logger.error(f"Error testing component {component_name}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
        finally:
            # Set final duration
            test_result['duration_seconds'] = time.time() - start_time
            
            # Log results
            status = "succeeded" if test_result['success'] else "failed"
            self.logger.info(f"Component test for {component_name} {status} in {test_result['duration_seconds']:.2f}s")
            
            if test_result['memory_diff_mb'] is not None:
                self.logger.info(f"Memory impact: {test_result['memory_diff_mb']:.2f} MB")
                
            return test_result
