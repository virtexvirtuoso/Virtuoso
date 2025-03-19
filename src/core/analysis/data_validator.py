import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional, Union, List, Tuple, Callable
from ..logger import Logger
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when market data validation fails."""
    pass

class DataValidator:
    """Centralized data validation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.required_fields = {
            'market_data': ['symbol', 'timestamp', 'ohlcv', 'orderbook', 'trades'],
            'ohlcv': ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
            'orderbook': ['bids', 'asks'],
            'trades': ['timestamp', 'price', 'amount', 'side']
        }
        
        self.min_requirements = {
            'trades': 10,  # Minimum trades
            'orderbook_levels': 5,  # Minimum orderbook levels
            'candles': {
                'base': 100,
                'ltf': 50,
                'mtf': 50,
                'htf': 50
            }
        }

    async def validate_market_data(self, market_data: Dict[str, Any], required_sections: List[str] = None) -> bool:
        """
        Validate complete market data structure asynchronously.
        
        Args:
            market_data: Dictionary containing market data sections
            required_sections: List of sections that must be present (defaults to self.required_fields['market_data'])
            
        Returns:
            bool: True if the market data is valid, False otherwise
        """
        try:
            if not isinstance(market_data, dict):
                self.logger.error("Market data must be a dictionary")
                return False
                
            # Use provided sections or default to all
            sections = required_sections or self.required_fields['market_data']
            
            # Check required sections
            missing = [s for s in sections if s not in market_data]
            if missing:
                self.logger.error(f"Missing data sections: {missing}")
                return False
                
            # Validate each section
            validators = {
                'ohlcv': self.validate_ohlcv,
                'orderbook': self.validate_orderbook,
                'trades': self.validate_trades
            }
            
            for section, validator in validators.items():
                if section in sections and section in market_data:
                    if not validator(market_data[section]):
                        return False
                        
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            return False

    def validate_ohlcv(self, ohlcv_data: Dict[str, Any]) -> bool:
        """Validate OHLCV data structure."""
        try:
            # Check timeframe structure
            required_timeframes = ['base', 'ltf', 'mtf', 'htf']
            
            if not all(tf in ohlcv_data for tf in required_timeframes):
                self.logger.error(f"Missing timeframes: {[tf for tf in required_timeframes if tf not in ohlcv_data]}")
                return False
                
            # Validate each timeframe
            for tf in required_timeframes:
                tf_data = ohlcv_data[tf]
                
                # Check data structure
                if not isinstance(tf_data, dict) or 'data' not in tf_data:
                    self.logger.error(f"Invalid {tf} timeframe structure")
                    return False
                    
                # Check minimum candles
                data = tf_data['data']
                # Make sure we safely convert string to int for comparison
                min_candles = self.min_requirements['candles'][tf]
                data_length = len(data)

                if data_length < min_candles:
                    self.logger.error(f"Insufficient {tf} candles: {data_length} < {min_candles}")
                    return False
                    
                # Validate required columns
                if isinstance(data, pd.DataFrame):
                    missing_cols = [col for col in self.required_fields['ohlcv'] if col not in data.columns]
                    if missing_cols:
                        self.logger.error(f"Missing columns in {tf}: {missing_cols}")
                        return False
                        
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating OHLCV data: {str(e)}")
            return False

    def validate_orderbook(self, orderbook: Dict[str, List]) -> bool:
        """Validate orderbook structure."""
        try:
            if not isinstance(orderbook, dict):
                self.logger.error("Orderbook must be a dictionary")
                return False
                
            # Check required fields
            if not all(side in orderbook for side in ['bids', 'asks']):
                self.logger.error("Missing orderbook sides")
                return False
                
            # Check minimum levels
            min_levels = self.min_requirements['orderbook_levels']
            bids_len = len(orderbook['bids'])
            asks_len = len(orderbook['asks'])
            
            if bids_len < min_levels or asks_len < min_levels:
                self.logger.error(f"Insufficient orderbook levels: bids={bids_len}, asks={asks_len}, minimum={min_levels}")
                return False
                
            # Validate price/size format
            for side in ['bids', 'asks']:
                for level in orderbook[side][:5]:  # Check first 5 levels
                    if not isinstance(level, (list, tuple)) or len(level) != 2:
                        self.logger.error(f"Invalid {side} level format: {level}")
                        return False
                    
                    # Convert string values to float before validation
                    try:
                        price = self._safe_float_convert(level[0])
                        size = self._safe_float_convert(level[1])
                        if not (isinstance(price, (int, float)) and isinstance(size, (int, float))):
                            self.logger.error(f"Invalid {side} level values after conversion: {price}, {size}")
                            return False
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Invalid {side} level values: {level}, error: {str(e)}")
                        return False
                        
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating orderbook: {str(e)}")
            return False

    def validate_trades(self, trades: List[Dict]) -> bool:
        """Validate trades structure."""
        try:
            if not isinstance(trades, list):
                self.logger.error("Trades must be a list")
                return False
                
            # Check minimum trades
            if len(trades) < self.min_requirements['trades']:
                self.logger.error(f"Insufficient trades: {len(trades)} < {self.min_requirements['trades']}")
                return False
                
            # Validate required fields in each trade
            for trade in trades[:10]:  # Check first 10 trades
                missing_fields = [f for f in self.required_fields['trades'] if f not in trade]
                if missing_fields:
                    self.logger.error(f"Missing trade fields: {missing_fields}")
                    return False
                    
                # Validate data types
                if not isinstance(trade['price'], (int, float)):
                    self.logger.error("Invalid trade price type")
                    return False
                if not isinstance(trade['amount'], (int, float)):
                    self.logger.error("Invalid trade amount type")
                    return False
                if not isinstance(trade['side'], str):
                    self.logger.error("Invalid trade side type")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating trades: {str(e)}")
            return False

    @staticmethod
    def validate_market_data_decorator(func):
        """Decorator for validating market data."""
        @wraps(func)
        async def wrapper(self, market_data: Dict[str, Any], *args, **kwargs):
            validator = DataValidator()
            if not await validator.validate_market_data(market_data):
                raise ValidationError("Invalid market data structure")
            return await func(self, market_data, *args, **kwargs)
        return wrapper

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> bool:
        """
        Validate OHLCV DataFrame structure and content.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if df is None or df.empty:
                logger.warning("Empty DataFrame")
                return False
                
            # Check required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return False
                
            # Check for NaN values
            nan_counts = df[required_cols].isna().sum()
            if nan_counts.any():
                logger.warning(f"NaN values found:\n{nan_counts[nan_counts > 0]}")
                return False
                
            # Check for zero/negative values
            if (df[['high', 'low', 'close', 'volume']] <= 0).any().any():
                logger.warning("Found zero or negative values in price/volume data")
                return False
                
            # Check high/low consistency
            if (df['high'] < df['low']).any():
                logger.error("Found high price less than low price")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating OHLCV data: {str(e)}")
            return False

    @staticmethod
    def validate_trades(trades_data: Union[pd.DataFrame, list]) -> pd.DataFrame:
        """Convert and validate trades data"""
        try:
            # Convert list to DataFrame if needed
            if isinstance(trades_data, list):
                df = pd.DataFrame(trades_data)
            else:
                df = trades_data.copy()
                
            # Check required columns
            required_cols = ['timestamp', 'price', 'amount', 'side']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return pd.DataFrame()
                
            # Convert numeric columns
            numeric_cols = ['price', 'amount']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            # Drop rows with NaN values
            df = df.dropna(subset=numeric_cols)
            
            # Sort by timestamp
            if 'timestamp' in df.columns:
                df = df.sort_values('timestamp')
                
            return df
            
        except Exception as e:
            logger.error(f"Error validating trades data: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def validate_orderbook(orderbook_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Validate and standardize orderbook data"""
        try:
            result = {}
            
            for side in ['bids', 'asks']:
                data = orderbook_data.get(side, [])
                
                if not data:
                    logger.warning(f"Empty {side} data")
                    result[side] = pd.DataFrame()
                    continue
                    
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=['price', 'amount'])
                
                # Convert to numeric
                for col in ['price', 'amount']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                # Drop invalid rows
                df = df.dropna()
                
                # Sort appropriately
                df = df.sort_values('price', ascending=(side == 'bids'))
                
                result[side] = df
                
            return result
            
        except Exception as e:
            logger.error(f"Error validating orderbook data: {str(e)}")
            return {'bids': pd.DataFrame(), 'asks': pd.DataFrame()}

    @staticmethod
    def validate_ticker(ticker_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Validate and normalize ticker data.
        
        Args:
            ticker_data: Dictionary containing ticker information
            
        Returns:
            Dict[str, float]: Normalized ticker data
        """
        try:
            required_fields = ['last', 'bid', 'ask', 'volume']
            result = {}
            
            for field in required_fields:
                try:
                    value = float(ticker_data.get(field, 0))
                    result[field] = value
                except (TypeError, ValueError):
                    logger.warning(f"Invalid {field} value in ticker")
                    result[field] = 0.0
                    
            return result
            
        except Exception as e:
            logger.error(f"Error validating ticker data: {str(e)}")
            return {field: 0.0 for field in ['last', 'bid', 'ask', 'volume']}

    def validate_ohlcv_timeframe(data: dict) -> bool:
        """Validate individual timeframe data structure"""
        required_fields = {'timestamp', 'interval', 'data', 'start', 'end'}
        
        if not all(field in data for field in required_fields):
            return False
            
        if not isinstance(data['data'], list) or not data['data']:
            return False
            
        return True

    def _validate_ohlcv(self, ohlcv_data: Dict[str, Any]) -> bool:
        """Validate OHLCV data structure with timeframes."""
        try:
            # Check for timeframe structure
            required_timeframes = ['base', 'ltf', 'mtf', 'htf']
            if not all(tf in ohlcv_data for tf in required_timeframes):
                self.logger.error(f"Missing required timeframes: {[tf for tf in required_timeframes if tf not in ohlcv_data]}")
                return False

            # Required columns for each timeframe
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

            # Validate each timeframe
            for tf in required_timeframes:
                tf_data = ohlcv_data[tf]
                
                # Check timeframe structure
                if not isinstance(tf_data, dict):
                    self.logger.error(f"Invalid type for timeframe {tf}: expected dict, got {type(tf_data)}")
                    return False
                    
                # Check required fields
                if not all(k in tf_data for k in self.required_fields['ohlcv']):
                    self.logger.error(f"Missing required fields in timeframe {tf}")
                    return False

                # Get DataFrame
                df = tf_data['data']
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(f"Invalid data type in {tf}: expected DataFrame, got {type(df)}")
                    return False

                # Check minimum candles requirement
                if len(df) < self.min_requirements['candles'][tf]:
                    self.logger.error(f"Insufficient candles in {tf}: {len(df)} < {self.min_requirements['candles'][tf]}")
                    return False

                # Check columns
                missing_cols = [col for col in required_columns if col not in df.columns]
                if missing_cols:
                    self.logger.error(f"Missing required columns in {tf}: {missing_cols}")
                    return False

                # Validate data types
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    if not np.issubdtype(df[col].dtype, np.number):
                        self.logger.error(f"Column {col} in {tf} must be numeric, got {df[col].dtype}")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating OHLCV data: {str(e)}")
            return False

    def _validate_trades(self, trades: List[Dict[str, Any]]) -> bool:
        """Validate trades data structure."""
        try:
            if not isinstance(trades, list):
                self.logger.error("Trades must be a list")
                return False

            # Check minimum trades requirement
            if len(trades) < self.min_requirements['trades']:
                self.logger.error(f"Insufficient trades: {len(trades)} < {self.min_requirements['trades']}")
                return False

            # Required fields for each trade
            required_fields = ['timestamp', 'price', 'size', 'side']
            
            for trade in trades:
                if not all(field in trade for field in required_fields):
                    self.logger.error(f"Missing trade fields: {[f for f in required_fields if f not in trade]}")
                    return False
                    
                # Validate numeric fields
                try:
                    float(trade['price'])
                    float(trade['size'])
                except (ValueError, TypeError):
                    self.logger.error(f"Invalid numeric values in trade: {trade}")
                    return False
                    
                # Validate side
                if trade['side'] not in ['buy', 'sell']:
                    self.logger.error(f"Invalid trade side: {trade['side']}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating trades: {str(e)}")
            return False

    def _validate_orderbook(self, orderbook: Dict[str, Any]) -> bool:
        """Validate orderbook data structure according to Bybit spec."""
        try:
            # Bybit specific fields
            required_fields = ['s', 'b', 'a', 'ts', 'u']
            
            if not all(field in orderbook for field in required_fields):
                self.logger.error(f"Missing required orderbook fields: {[f for f in required_fields if f not in orderbook]}")
                return False

            # Validate bids/asks format
            for side in ['b', 'a']:  # b=bids, a=asks in Bybit
                if not isinstance(orderbook[side], list):
                    self.logger.error(f"Invalid {side} type")
                    return False
                    
                for level in orderbook[side]:
                    if not isinstance(level, list) or len(level) != 2:
                        self.logger.error(f"Invalid {side} level format: {level}")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating orderbook: {str(e)}")
            return False

    def _validate_sentiment(self, sentiment_data: Dict[str, Any]) -> bool:
        """Validate sentiment data structure."""
        try:
            required_fields = ['funding_rate', 'long_short_ratio', 'market_sentiment']
            
            if not all(field in sentiment_data for field in required_fields):
                self.logger.error(f"Missing required sentiment fields: {[f for f in required_fields if f not in sentiment_data]}")
                return False
                
            # Validate numeric fields
            numeric_fields = ['funding_rate', 'long_short_ratio']
            for field in numeric_fields:
                try:
                    value = float(sentiment_data[field])
                    if field == 'long_short_ratio' and not 0 <= value <= 1:
                        self.logger.error(f"Invalid {field} value: {value} (must be between 0 and 1)")
                        return False
                except (ValueError, TypeError):
                    self.logger.error(f"Invalid numeric value for {field}: {sentiment_data[field]}")
                    return False
                    
            # Validate market sentiment value
            valid_sentiments = ['bullish', 'bearish', 'neutral']
            if sentiment_data['market_sentiment'] not in valid_sentiments:
                self.logger.error(f"Invalid market sentiment: {sentiment_data['market_sentiment']}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating sentiment data: {str(e)}")
            return False

    def validate_timeframe_base(self, data):
        """Validate timeframe base data structure"""
        if not data or not isinstance(data, dict):
            raise ValueError("Invalid timeframe data format")
            
        missing_fields = [field for field in self.required_fields['ohlcv'] 
                         if field not in data]
        
        if missing_fields:
            raise ValueError(f"Missing required timeframe fields: {missing_fields}")
            
        return True

    def debug_data_structure(self, data: Any, prefix: str = "", max_depth: int = 3) -> None:
        """Recursively debug data structure with detailed logging."""
        if max_depth <= 0:
            return

        if isinstance(data, dict):
            self.logger.debug(f"{prefix}Dict with keys: {list(data.keys())}")
            for key, value in data.items():
                self.logger.debug(f"{prefix}Key '{key}':")
                self.debug_data_structure(value, prefix + "  ", max_depth - 1)
            
        elif isinstance(data, (list, tuple)):
            self.logger.debug(f"{prefix}List/Tuple with {len(data)} items")
            if data:
                self.logger.debug(f"{prefix}First item type: {type(data[0])}")
                if len(data) > 1:
                    self.logger.debug(f"{prefix}Sample items: {data[:2]}")
            
        else:
            self.logger.debug(f"{prefix}Value type: {type(data)}")
            if isinstance(data, (int, float, str, bool)):
                self.logger.debug(f"{prefix}Value: {data}")

    def _validate_long_short_ratio(self, ratio_data: Dict[str, Any]) -> bool:
        """Validate long/short ratio structure"""
        try:
            required_fields = ['buy_ratio', 'sell_ratio', 'timestamp']
            if not all(field in ratio_data for field in required_fields):
                self.logger.error(f"Missing ratio fields: {[f for f in required_fields if f not in ratio_data]}")
                return False

            if not (0 <= ratio_data['buy_ratio'] <= 1 and 0 <= ratio_data['sell_ratio'] <= 1):
                self.logger.error(f"Invalid ratio values: {ratio_data}")
                return False

            if abs(1.0 - (ratio_data['buy_ratio'] + ratio_data['sell_ratio'])) > 0.0001:
                self.logger.error(f"Ratios don't sum to 1: {ratio_data}")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Ratio validation failed: {str(e)}")
            return False

    def _safe_float_convert(self, value):
        """Safely convert a value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            return float(value)
        else:
            raise TypeError(f"Cannot convert {type(value)} to float") 