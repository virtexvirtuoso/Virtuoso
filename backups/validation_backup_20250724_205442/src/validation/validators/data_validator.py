"""Data validation utilities."""

import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np

from ..core.base import ValidationResult, ValidationContext
from ..core.models import ValidationLevel

logger = logging.getLogger(__name__)

class DataValidator:
    """Class for validating market data structures."""
    
    @staticmethod
    def validate_market_data(data: Dict[str, Any], context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate market data structure and content with flexible validation.
        
        Args:
            data: Market data dictionary
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result with errors/warnings
        """
        result = ValidationResult(success=True)
        
        try:
            # Check core required keys (only symbol is truly required)
            core_keys = ['symbol']
            missing_core = [key for key in core_keys if key not in data]
            if missing_core:
                result.add_error(f"Missing core keys in market data: {missing_core}")
                return result
            
            # Check recommended keys (warn if missing but don't fail)
            recommended_keys = ['timestamp', 'exchange']
            missing_recommended = [key for key in recommended_keys if key not in data]
            if missing_recommended:
                result.add_warning(f"Missing recommended keys in market data: {missing_recommended}")
            
            # Validate price data if present (flexible)
            if 'price_data' in data and data['price_data']:
                price_result = DataValidator.validate_price_data(data['price_data'], context)
                if not price_result.success:
                    result.add_warning("Price data validation failed, but continuing")
            elif 'ohlcv' in data and data['ohlcv']:
                # Alternative OHLCV structure
                logger.debug("Using alternative OHLCV structure for price data")
            
            # Validate trades if present (flexible)
            if 'trades' in data and data['trades']:
                trades_result = DataValidator.validate_trades_data(data['trades'], context)
                if not trades_result.success:
                    result.add_warning("Trades data validation failed, but continuing")
            
            # Validate orderbook if present (flexible)
            if 'orderbook' in data and data['orderbook']:
                orderbook_result = DataValidator.validate_orderbook_data(data['orderbook'], context)
                if not orderbook_result.success:
                    result.add_warning("Orderbook data validation failed, but continuing")
            
            return result
            
        except Exception as e:
            result.add_error(f"Error validating market data: {str(e)}")
            return result

    @staticmethod
    def validate_price_data(price_data: Dict[str, pd.DataFrame], context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate price data structure and content.
        
        Args:
            price_data: Dictionary of price data DataFrames
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(success=True)
        
        try:
            if not price_data:
                result.add_error("Empty price data")
                return result
            
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            
            for timeframe, df in price_data.items():
                # Check DataFrame type
                if not isinstance(df, pd.DataFrame):
                    result.add_error(f"Invalid data type for timeframe {timeframe}")
                    continue
                
                # Check required columns
                if not all(col in df.columns for col in required_columns):
                    result.add_error(f"Missing required columns in timeframe {timeframe}")
                    continue
                
                # Check for NaN values
                if df[required_columns].isna().any().any():
                    result.add_error(f"NaN values found in timeframe {timeframe}")
                    continue
                
                # Check OHLC relationships
                if not DataValidator.validate_ohlc_relationships(df):
                    result.add_error(f"Invalid OHLC relationships in timeframe {timeframe}")
                    continue
                
                # Check for negative values
                if (df[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
                    result.add_error(f"Negative values found in timeframe {timeframe}")
                    continue
            
            return result
            
        except Exception as e:
            result.add_error(f"Error validating price data: {str(e)}")
            return result

    @staticmethod
    def validate_trades_data(trades, context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate trades data structure and content.
        
        Args:
            trades: Trades data (DataFrame, list, or dict)
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(success=True)
        
        try:
            # Handle different input types
            if isinstance(trades, pd.DataFrame):
                if trades.empty:
                    result.add_warning("Empty trades data")
                    return result
            elif isinstance(trades, (list, tuple)):
                if not trades:
                    result.add_warning("Empty trades data")
                    return result
                # Convert to DataFrame for validation if it's a list of dicts
                if all(isinstance(item, dict) for item in trades):
                    trades = pd.DataFrame(trades)
                else:
                    return result  # Can't validate non-dict list items
            elif isinstance(trades, dict):
                if not trades:
                    result.add_warning("Empty trades data")
                    return result
                # Convert single trade to DataFrame
                trades = pd.DataFrame([trades])
            else:
                result.add_warning(f"Unsupported trades data type: {type(trades)}")
                return result
            
            required_columns = ['symbol', 'side', 'price', 'amount']
            
            # Check required columns
            if not all(col in trades.columns for col in required_columns):
                result.add_error("Missing required columns in trades data")
                return result
            
            # Check for NaN values
            if trades[required_columns].isna().any().any():
                result.add_error("NaN values found in trades data")
                return result
            
            # Check for negative values
            if (trades[['price', 'amount']] < 0).any().any():
                result.add_error("Negative values found in trades data")
                return result
            
            # Check side values
            valid_sides = ['buy', 'sell']
            if not trades['side'].isin(valid_sides).all():
                result.add_error("Invalid side values in trades data")
                return result
            
            return result
            
        except Exception as e:
            result.add_error(f"Error validating trades data: {str(e)}")
            return result

    @staticmethod
    def validate_orderbook_data(orderbook, context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate orderbook data structure and content.
        
        Args:
            orderbook: Orderbook data (DataFrame, dict, or list)
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(success=True)
        
        try:
            # Handle different input types
            if isinstance(orderbook, pd.DataFrame):
                if orderbook.empty:
                    result.add_warning("Empty orderbook data")
                    return result
            elif isinstance(orderbook, dict):
                if not orderbook:
                    result.add_warning("Empty orderbook data")
                    return result
                # Common orderbook structure: {'bids': [], 'asks': []}
                if 'bids' in orderbook or 'asks' in orderbook:
                    return result  # Basic structure check passed
                # Convert to DataFrame if it has the right structure
                if 'price' in orderbook and 'size' in orderbook:
                    orderbook = pd.DataFrame([orderbook])
                else:
                    return result  # Can't validate unknown dict structure
            elif isinstance(orderbook, (list, tuple)):
                if not orderbook:
                    result.add_warning("Empty orderbook data")
                    return result
                return result  # Can't validate list orderbook
            else:
                result.add_warning(f"Unsupported orderbook data type: {type(orderbook)}")
                return result
            
            required_columns = ['price', 'size', 'side']
            
            # Check required columns
            if not all(col in orderbook.columns for col in required_columns):
                result.add_error("Missing required columns in orderbook data")
                return result
            
            # Check for NaN values
            if orderbook[required_columns].isna().any().any():
                result.add_error("NaN values found in orderbook data")
                return result
            
            # Check for negative values
            if (orderbook[['price', 'size']] < 0).any().any():
                result.add_error("Negative values found in orderbook data")
                return result
            
            # Check side values
            valid_sides = ['bid', 'ask']
            if not orderbook['side'].isin(valid_sides).all():
                result.add_error("Invalid side values in orderbook data")
                return result
            
            # Check price ordering
            bids = orderbook[orderbook['side'] == 'bid']['price']
            asks = orderbook[orderbook['side'] == 'ask']['price']
            
            if not bids.empty and not asks.empty:
                if bids.max() >= asks.min():
                    result.add_error("Invalid price ordering in orderbook")
                    return result
            
            return result
            
        except Exception as e:
            result.add_error(f"Error validating orderbook data: {str(e)}")
            return result

    @staticmethod
    def validate_ohlc_relationships(df: pd.DataFrame) -> bool:
        """Validate OHLC price relationships.
        
        Args:
            df: OHLC DataFrame
            
        Returns:
            bool: True if relationships are valid, False otherwise
        """
        try:
            # High should be the highest price
            if not ((df['high'] >= df['open']) & (df['high'] >= df['low']) & (df['high'] >= df['close'])).all():
                return False
            
            # Low should be the lowest price
            if not ((df['low'] <= df['open']) & (df['low'] <= df['high']) & (df['low'] <= df['close'])).all():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating OHLC relationships: {str(e)}")
            return False