"""
Data validation module for the monitoring system.

This module consolidates all validation logic for market data, ensuring data quality,
completeness, and consistency. It includes validation rules for different data types
and provides comprehensive validation statistics.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
import pandas as pd
import json

from .base import MonitoringComponent, DataValidator, ValidationRule
from .utils.timestamp import TimestampUtility
from .utils.decorators import measure_performance


class TimeRangeValidationRule(ValidationRule):
    """Validation rule for checking time ranges."""
    
    def __init__(self, max_age_seconds: int = 86400, future_tolerance_seconds: int = 60):
        """Initialize the time range validation rule.
        
        Args:
            max_age_seconds: Maximum age for valid data (default: 24 hours)
            future_tolerance_seconds: Tolerance for future timestamps (default: 60 seconds)
        """
        super().__init__("time_range")
        self.max_age_seconds = max_age_seconds
        self.future_tolerance_seconds = future_tolerance_seconds
    
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
            
            # Convert to milliseconds if needed
            if isinstance(timestamp, (int, float)):
                if timestamp < 1e10:  # Likely in seconds
                    timestamp = timestamp * 1000
            elif isinstance(timestamp, datetime):
                timestamp = TimestampUtility.datetime_to_milliseconds(timestamp)
            else:
                return False
            
            # Check if timestamp is fresh
            return TimestampUtility.is_timestamp_fresh(
                timestamp,
                self.max_age_seconds,
                self.future_tolerance_seconds
            )
            
        except Exception:
            return False


class SymbolValidationRule(ValidationRule):
    """Validation rule for checking symbol format."""
    
    def __init__(self, valid_symbols: Optional[List[str]] = None):
        """Initialize the symbol validation rule.
        
        Args:
            valid_symbols: Optional list of valid symbols
        """
        super().__init__("symbol")
        self.valid_symbols = set(valid_symbols) if valid_symbols else None
    
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate symbol in data.
        
        Args:
            data: Data dictionary containing symbol
            
        Returns:
            bool: True if symbol is valid
        """
        symbol = data.get('symbol')
        if not symbol:
            return False
        
        # Check if symbol is a string
        if not isinstance(symbol, str):
            return False
        
        # Check against valid symbols if provided
        if self.valid_symbols:
            return symbol in self.valid_symbols
        
        # Basic format check (contains / or is alphanumeric)
        return '/' in symbol or symbol.isalnum()


class MarketDataValidator(MonitoringComponent, DataValidator):
    """Comprehensive validation system for market data.
    
    This class provides validation for different types of market data including
    OHLCV, orderbook, trades, ticker, and other market information. It maintains
    validation statistics and can be configured with custom validation rules.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the market data validator.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        super().__init__(logger)
        
        self.config = config or {}
        
        # Validation rules for different data types
        self.validation_rules = {
            'ohlcv': self._validate_ohlcv,
            'orderbook': self._validate_orderbook,
            'trades': self._validate_trades,
            'ticker': self._validate_ticker,
            'funding': self._validate_funding
        }
        
        # Custom validation rules
        self.custom_rules: List[ValidationRule] = []
        self._initialize_default_rules()
        
        # Track validation statistics
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'warnings': 0,
            'data_types': {},
            'last_validation_time': None,
            'average_validation_time': 0
        }
        
        # Validation configuration
        self.strict_mode = self.config.get('strict_validation', False)
        self.log_failures = self.config.get('log_validation_failures', True)
        self.max_price_change = self.config.get('max_price_change_percent', 50)  # 50% max change
    
    def _initialize_default_rules(self) -> None:
        """Initialize default validation rules."""
        # Add time range validation
        max_age = self.config.get('max_data_age_seconds', 3600)  # 1 hour default
        self.custom_rules.append(TimeRangeValidationRule(max_age))
        
        # Add symbol validation if valid symbols are configured
        valid_symbols = self.config.get('valid_symbols')
        if valid_symbols:
            self.custom_rules.append(SymbolValidationRule(valid_symbols))
    
    async def _perform_initialization(self) -> None:
        """Perform component-specific initialization."""
        self.logger.info(f"MarketDataValidator initialized in {'strict' if self.strict_mode else 'normal'} mode")
    
    @measure_performance()
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate market data.
        
        This is the main entry point for validation. It applies both built-in
        and custom validation rules to the data.
        
        Args:
            data: Market data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        start_time = TimestampUtility.get_utc_timestamp()
        self.validation_stats['total_validations'] += 1
        
        try:
            # Apply custom rules first
            for rule in self.custom_rules:
                if not await rule.validate(data):
                    if self.log_failures:
                        self.logger.warning(f"Validation rule '{rule.name}' failed")
                    if self.strict_mode:
                        self.validation_stats['failed_validations'] += 1
                        return False
                    else:
                        self.validation_stats['warnings'] += 1
            
            # Validate specific data types
            validation_passed = await self._validate_market_data_comprehensive(data)
            
            # Update statistics
            if validation_passed:
                self.validation_stats['passed_validations'] += 1
            else:
                self.validation_stats['failed_validations'] += 1
            
            # Update timing statistics
            elapsed = TimestampUtility.get_age_seconds(start_time) * 1000  # Convert to ms
            self._update_timing_stats(elapsed)
            
            return validation_passed
            
        except Exception as e:
            self.logger.error(f"Error during validation: {str(e)}")
            self.validation_stats['failed_validations'] += 1
            return False
    
    async def _validate_market_data_comprehensive(self, market_data: Dict[str, Any]) -> bool:
        """Comprehensive validation of entire market data.
        
        Args:
            market_data: The market data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        self.logger.debug("Starting comprehensive market data validation")
        
        # Check if market_data is a dictionary
        if not isinstance(market_data, dict):
            self.logger.error(f"Market data must be a dictionary, got {type(market_data)}")
            return False
        
        # Check for required base fields
        required_fields = ['symbol', 'timestamp']
        missing_fields = [field for field in required_fields if field not in market_data]
        if missing_fields:
            self.logger.error(f"Missing required fields in market data: {missing_fields}")
            return False
        
        # Validate each data type present
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
                    if self.strict_mode:
                        overall_result = False
        
        self.logger.debug(f"Validation results: {validation_results}")
        self.logger.debug(f"Overall validation result: {'PASS' if overall_result else 'FAIL'}")
        
        return overall_result
    
    def _validate_ohlcv(self, ohlcv_data: Any) -> bool:
        """Validate OHLCV data for all timeframes.
        
        Args:
            ohlcv_data: OHLCV data to validate
            
        Returns:
            bool: True if valid
        """
        if not isinstance(ohlcv_data, dict):
            self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv_data)}")
            return False
        
        # Check for at least one timeframe
        if len(ohlcv_data) == 0:
            self.logger.warning("No timeframes in OHLCV data")
            return False if self.strict_mode else True
        
        # Validate each timeframe
        valid_timeframes = 0
        for timeframe, data in ohlcv_data.items():
            if isinstance(data, pd.DataFrame):
                if self._validate_ohlcv_dataframe(data, timeframe):
                    valid_timeframes += 1
            elif isinstance(data, list):
                if self._validate_ohlcv_list(data, timeframe):
                    valid_timeframes += 1
        
        # Return True if at least one timeframe is valid
        if valid_timeframes > 0:
            self.logger.debug(f"OHLCV validation passed with {valid_timeframes} valid timeframes")
            return True
        
        self.logger.error("No valid timeframes found in OHLCV data")
        return False
    
    def _validate_ohlcv_dataframe(self, df: pd.DataFrame, timeframe: str) -> bool:
        """Validate OHLCV DataFrame.
        
        Args:
            df: DataFrame to validate
            timeframe: Timeframe identifier
            
        Returns:
            bool: True if valid
        """
        if df.empty:
            self.logger.warning(f"Empty DataFrame for timeframe {timeframe}")
            return not self.strict_mode
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            self.logger.warning(f"Timeframe {timeframe} missing columns: {missing_columns}")
            return False
        
        # Check for NaN values
        nan_counts = df[required_columns].isna().sum()
        if nan_counts.sum() > 0:
            self.logger.warning(f"NaN values found in timeframe {timeframe}: {nan_counts.to_dict()}")
            if self.strict_mode:
                return False
        
        # Validate OHLC relationships
        invalid_hl = df[df['high'] < df['low']]
        if not invalid_hl.empty:
            self.logger.error(f"Found {len(invalid_hl)} candles where high < low in {timeframe}")
            return False
        
        # Check that high >= open/close and low <= open/close
        invalid_high = df[(df['high'] < df['open']) | (df['high'] < df['close'])]
        invalid_low = df[(df['low'] > df['open']) | (df['low'] > df['close'])]
        
        if not invalid_high.empty or not invalid_low.empty:
            self.logger.error(f"Found candles with invalid high/low values in {timeframe}")
            return False
        
        # Check for negative values
        negative_values = df[(df[required_columns] < 0).any(axis=1)]
        if not negative_values.empty:
            self.logger.error(f"Found {len(negative_values)} candles with negative values in {timeframe}")
            return False
        
        # Check chronological order if index is datetime
        if isinstance(df.index, pd.DatetimeIndex):
            if not df.index.is_monotonic_increasing:
                self.logger.warning(f"Timestamps in {timeframe} are not in chronological order")
                if self.strict_mode:
                    return False
            
            # Check for duplicates
            if len(df.index) != len(df.index.unique()):
                self.logger.error(f"Duplicate timestamps found in {timeframe}")
                return False
        
        return True
    
    def _validate_ohlcv_list(self, data: List, timeframe: str) -> bool:
        """Validate OHLCV data in list format.
        
        Args:
            data: List of OHLCV candles
            timeframe: Timeframe identifier
            
        Returns:
            bool: True if valid
        """
        if not data:
            self.logger.warning(f"Empty OHLCV list for timeframe {timeframe}")
            return not self.strict_mode
        
        # Check first candle structure
        if len(data[0]) < 6:
            self.logger.error(f"Invalid OHLCV candle structure in {timeframe}")
            return False
        
        # Basic validation on sample candles
        for i, candle in enumerate(data[:10]):  # Check first 10 candles
            if len(candle) < 6:
                self.logger.error(f"Invalid candle structure at index {i} in {timeframe}")
                return False
            
            # Check OHLC relationships
            _, open_price, high, low, close, volume = candle[:6]
            
            if high < low:
                self.logger.error(f"Invalid candle at index {i}: high < low")
                return False
            
            if high < open_price or high < close:
                self.logger.error(f"Invalid candle at index {i}: high < open/close")
                return False
            
            if low > open_price or low > close:
                self.logger.error(f"Invalid candle at index {i}: low > open/close")
                return False
            
            if any(v < 0 for v in [open_price, high, low, close, volume]):
                self.logger.error(f"Negative values in candle at index {i}")
                return False
        
        return True
    
    def _validate_orderbook(self, orderbook_data: Any) -> bool:
        """Validate orderbook data.
        
        Args:
            orderbook_data: Orderbook data to validate
            
        Returns:
            bool: True if valid
        """
        # Handle nested orderbook structure
        if isinstance(orderbook_data, dict):
            # Check for common nested structures
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
            return False
        
        # Validate bids and asks
        bids = orderbook_data['bids']
        asks = orderbook_data['asks']
        
        if not isinstance(bids, list) or not isinstance(asks, list):
            self.logger.error("Bids and asks must be lists")
            return False
        
        # Check that at least one side has data
        if len(bids) == 0 and len(asks) == 0:
            self.logger.warning("Both bids and asks are empty in orderbook")
            return not self.strict_mode
        
        # Validate bid/ask format
        if bids and not self._validate_orderbook_side(bids, 'bids'):
            return False
        
        if asks and not self._validate_orderbook_side(asks, 'asks'):
            return False
        
        # Check for crossed book
        if bids and asks:
            highest_bid = float(bids[0][0]) if isinstance(bids[0], (list, tuple)) else float(bids[0].get('price', 0))
            lowest_ask = float(asks[0][0]) if isinstance(asks[0], (list, tuple)) else float(asks[0].get('price', float('inf')))
            
            if highest_bid >= lowest_ask:
                self.logger.error(f"Crossed orderbook detected: highest bid {highest_bid} >= lowest ask {lowest_ask}")
                return False
        
        return True
    
    def _validate_orderbook_side(self, orders: List, side: str) -> bool:
        """Validate one side of the orderbook.
        
        Args:
            orders: List of orders
            side: 'bids' or 'asks'
            
        Returns:
            bool: True if valid
        """
        if not orders:
            return True
        
        # Check format of first order
        first_order = orders[0]
        if isinstance(first_order, (list, tuple)):
            if len(first_order) < 2:
                self.logger.error(f"Invalid {side} format: need at least [price, amount]")
                return False
        elif isinstance(first_order, dict):
            if 'price' not in first_order or 'amount' not in first_order:
                self.logger.error(f"Invalid {side} format: need 'price' and 'amount' keys")
                return False
        else:
            self.logger.error(f"Invalid {side} format: unknown structure")
            return False
        
        # Check order (descending for bids, ascending for asks)
        prev_price = None
        for i, order in enumerate(orders[:20]):  # Check first 20 levels
            if isinstance(order, (list, tuple)):
                price = float(order[0])
            else:
                price = float(order.get('price', 0))
            
            if prev_price is not None:
                if side == 'bids' and price >= prev_price:
                    self.logger.error(f"Bids not in descending order at index {i}")
                    return False
                elif side == 'asks' and price <= prev_price:
                    self.logger.error(f"Asks not in ascending order at index {i}")
                    return False
            
            prev_price = price
        
        return True
    
    def _validate_trades(self, trades_data: Any) -> bool:
        """Validate trades data.
        
        Args:
            trades_data: Trades data to validate
            
        Returns:
            bool: True if valid
        """
        # Handle nested structures
        if isinstance(trades_data, dict):
            if 'result' in trades_data and isinstance(trades_data['result'], dict):
                if 'list' in trades_data['result']:
                    trades_data = trades_data['result']['list']
            elif 'list' in trades_data:
                trades_data = trades_data['list']
            elif 'result' in trades_data and isinstance(trades_data['result'], list):
                trades_data = trades_data['result']
        
        if not isinstance(trades_data, (list, pd.DataFrame)):
            self.logger.error(f"Trades data must be a list or DataFrame, got {type(trades_data)}")
            return False
        
        # Empty trades are valid
        if isinstance(trades_data, list) and len(trades_data) == 0:
            return True
        if isinstance(trades_data, pd.DataFrame) and trades_data.empty:
            return True
        
        # Validate structure
        if isinstance(trades_data, list):
            return self._validate_trades_list(trades_data)
        else:
            return self._validate_trades_dataframe(trades_data)
    
    def _validate_trades_list(self, trades: List) -> bool:
        """Validate trades in list format.
        
        Args:
            trades: List of trades
            
        Returns:
            bool: True if valid
        """
        if not trades:
            return True
        
        # Check first trade structure
        first_trade = trades[0]
        
        required_fields = []
        if isinstance(first_trade, dict):
            # Check for required fields in dict format
            required_fields = ['price', 'timestamp']
            size_fields = ['amount', 'size', 'quantity', 'qty']
            
            has_required = all(field in first_trade for field in required_fields)
            has_size = any(field in first_trade for field in size_fields)
            
            if not (has_required and has_size):
                self.logger.error("Trades missing required fields")
                return False
        
        # Validate sample trades
        for i, trade in enumerate(trades[:10]):
            if isinstance(trade, dict):
                price = trade.get('price', 0)
                if price <= 0:
                    self.logger.error(f"Invalid trade price at index {i}: {price}")
                    return False
        
        return True
    
    def _validate_trades_dataframe(self, df: pd.DataFrame) -> bool:
        """Validate trades DataFrame.
        
        Args:
            df: DataFrame of trades
            
        Returns:
            bool: True if valid
        """
        # Check required columns
        required_columns = ['price', 'timestamp']
        size_columns = ['amount', 'size', 'quantity', 'qty']
        
        missing_required = [col for col in required_columns if col not in df.columns]
        has_size = any(col in df.columns for col in size_columns)
        
        if missing_required or not has_size:
            self.logger.error(f"Trades DataFrame missing required columns")
            return False
        
        # Check for invalid prices
        if (df['price'] <= 0).any():
            self.logger.error("Found trades with invalid prices")
            return False
        
        return True
    
    def _validate_ticker(self, ticker_data: Any) -> bool:
        """Validate ticker data.
        
        Args:
            ticker_data: Ticker data to validate
            
        Returns:
            bool: True if valid
        """
        if ticker_data is None:
            return not self.strict_mode
        
        if not isinstance(ticker_data, dict):
            self.logger.error(f"Ticker must be a dictionary, got {type(ticker_data)}")
            return False
        
        # Check for basic fields
        important_fields = ['symbol', 'last', 'timestamp']
        missing = [field for field in important_fields if field not in ticker_data]
        
        if missing:
            self.logger.warning(f"Ticker missing fields: {missing}")
            if self.strict_mode:
                return False
        
        # Validate price fields
        price_fields = ['last', 'bid', 'ask', 'high', 'low', 'open', 'close']
        for field in price_fields:
            if field in ticker_data:
                value = ticker_data[field]
                if value is not None:
                    try:
                        price = float(value)
                        if price < 0:
                            self.logger.error(f"Negative {field} price in ticker: {price}")
                            return False
                    except (ValueError, TypeError):
                        self.logger.error(f"Invalid {field} price in ticker: {value}")
                        return False
        
        return True
    
    def _validate_funding(self, funding_data: Any) -> bool:
        """Validate funding data.
        
        Args:
            funding_data: Funding data to validate
            
        Returns:
            bool: True if valid
        """
        if funding_data is None:
            return True
        
        if not isinstance(funding_data, dict):
            self.logger.error(f"Funding data must be a dictionary, got {type(funding_data)}")
            return False
        
        # Check for required fields
        required_fields = ['rate', 'timestamp']
        missing = [field for field in required_fields if field not in funding_data]
        
        if missing:
            self.logger.warning(f"Funding data missing fields: {missing}")
            return not self.strict_mode
        
        return True
    
    def _update_timing_stats(self, elapsed_ms: float) -> None:
        """Update timing statistics.
        
        Args:
            elapsed_ms: Elapsed time in milliseconds
        """
        current_avg = self.validation_stats['average_validation_time']
        total_validations = self.validation_stats['total_validations']
        
        # Calculate new average
        new_avg = ((current_avg * (total_validations - 1)) + elapsed_ms) / total_validations
        self.validation_stats['average_validation_time'] = new_avg
        self.validation_stats['last_validation_time'] = TimestampUtility.get_utc_timestamp()
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics.
        
        Returns:
            Dictionary of validation statistics
        """
        return {
            **self.validation_stats,
            'success_rate': (
                self.validation_stats['passed_validations'] / 
                max(self.validation_stats['total_validations'], 1) * 100
            ),
            'strict_mode': self.strict_mode,
            'custom_rules_count': len(self.custom_rules)
        }
    
    async def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data - compatibility method.
        
        This method provides backward compatibility with the original interface.
        
        Args:
            market_data: Market data to validate
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        return await self.validate(market_data)
    
    def add_custom_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule.
        
        Args:
            rule: ValidationRule instance to add
        """
        self.custom_rules.append(rule)
        self.logger.info(f"Added custom validation rule: {rule.name}")
    
    def remove_custom_rule(self, rule_name: str) -> bool:
        """Remove a custom validation rule by name.
        
        Args:
            rule_name: Name of the rule to remove
            
        Returns:
            bool: True if rule was removed
        """
        initial_count = len(self.custom_rules)
        self.custom_rules = [r for r in self.custom_rules if r.name != rule_name]
        
        if len(self.custom_rules) < initial_count:
            self.logger.info(f"Removed custom validation rule: {rule_name}")
            return True
        return False
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'warnings': 0,
            'data_types': {},
            'last_validation_time': None,
            'average_validation_time': 0
        }
        self.logger.info("Validation statistics reset")