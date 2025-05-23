"""Market data validation utilities."""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd


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
            return False
        
        # Validate bids and asks
        for side in ['bids', 'asks']:
            levels = orderbook_data[side]
            
            if not isinstance(levels, list):
                self.logger.error(f"Orderbook {side} must be a list, got {type(levels)}")
                return False
            
            if len(levels) == 0:
                self.logger.warning(f"Orderbook {side} list is empty")
                continue
            
            # Check each level
            for i, level in enumerate(levels[:10]):  # Check first 10 levels
                if not isinstance(level, (list, tuple)) or len(level) < 2:
                    self.logger.error(f"Orderbook {side} level {i} must be a list/tuple with at least 2 elements")
                    return False
                
                price, quantity = level[0], level[1]
                
                # Check that price and quantity are positive numbers
                try:
                    price_val = float(price)
                    qty_val = float(quantity)
                    
                    if price_val <= 0:
                        self.logger.error(f"Orderbook {side} level {i} has invalid price: {price_val}")
                        return False
                    
                    if qty_val <= 0:
                        self.logger.error(f"Orderbook {side} level {i} has invalid quantity: {qty_val}")
                        return False
                        
                except (ValueError, TypeError):
                    self.logger.error(f"Orderbook {side} level {i} has non-numeric values: price={price}, qty={quantity}")
                    return False
        
        # Check that bids are sorted descending and asks ascending
        if orderbook_data['bids']:
            bid_prices = [float(bid[0]) for bid in orderbook_data['bids']]
            if bid_prices != sorted(bid_prices, reverse=True):
                self.logger.warning("Bid prices are not sorted in descending order")
        
        if orderbook_data['asks']:
            ask_prices = [float(ask[0]) for ask in orderbook_data['asks']]
            if ask_prices != sorted(ask_prices):
                self.logger.warning("Ask prices are not sorted in ascending order")
        
        # Check for crossed market
        if orderbook_data['bids'] and orderbook_data['asks']:
            best_bid = float(orderbook_data['bids'][0][0])
            best_ask = float(orderbook_data['asks'][0][0])
            
            if best_bid >= best_ask:
                self.logger.error(f"Crossed market detected: best_bid ({best_bid}) >= best_ask ({best_ask})")
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