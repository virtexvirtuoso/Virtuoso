"""Data validation utilities."""

import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DataValidator:
    """Class for validating market data structures."""
    
    @staticmethod
    def validate_market_data(data: Dict[str, Any]) -> bool:
        """Validate market data structure and content with flexible validation.
        
        Args:
            data: Market data dictionary
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Check core required keys (only symbol is truly required)
            core_keys = ['symbol']
            missing_core = [key for key in core_keys if key not in data]
            if missing_core:
                logger.error(f"Missing core keys in market data: {missing_core}")
                return False
            
            # Check recommended keys (warn if missing but don't fail)
            recommended_keys = ['timestamp', 'exchange']
            missing_recommended = [key for key in recommended_keys if key not in data]
            if missing_recommended:
                logger.warning(f"Missing recommended keys in market data: {missing_recommended}")
            
            # Validate price data if present (flexible)
            if 'price_data' in data and data['price_data']:
                if not DataValidator.validate_price_data(data['price_data']):
                    logger.warning("Price data validation failed, but continuing")
            elif 'ohlcv' in data and data['ohlcv']:
                # Alternative OHLCV structure
                logger.debug("Using alternative OHLCV structure for price data")
            
            # Validate trades if present (flexible)
            if 'trades' in data and data['trades']:
                if not DataValidator.validate_trades_data(data['trades']):
                    logger.warning("Trades data validation failed, but continuing")
            
            # Validate orderbook if present (flexible)
            if 'orderbook' in data and data['orderbook']:
                if not DataValidator.validate_orderbook_data(data['orderbook']):
                    logger.warning("Orderbook data validation failed, but continuing")
            
            # Always return True for flexible validation (warnings instead of failures)
            return True
            
        except Exception as e:
            logger.error(f"Error validating market data: {str(e)}")
            return False

    @staticmethod
    def validate_price_data(price_data: Dict[str, pd.DataFrame]) -> bool:
        """Validate price data structure and content.
        
        Args:
            price_data: Dictionary of price data DataFrames
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            if not price_data:
                logger.error("Empty price data")
                return False
            
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            
            for timeframe, df in price_data.items():
                # Check DataFrame type
                if not isinstance(df, pd.DataFrame):
                    logger.error(f"Invalid data type for timeframe {timeframe}")
                    return False
                
                # Check required columns
                if not all(col in df.columns for col in required_columns):
                    logger.error(f"Missing required columns in timeframe {timeframe}")
                    return False
                
                # Check for NaN values
                if df[required_columns].isna().any().any():
                    logger.error(f"NaN values found in timeframe {timeframe}")
                    return False
                
                # Check OHLC relationships
                if not DataValidator.validate_ohlc_relationships(df):
                    logger.error(f"Invalid OHLC relationships in timeframe {timeframe}")
                    return False
                
                # Check for negative values
                if (df[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
                    logger.error(f"Negative values found in timeframe {timeframe}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating price data: {str(e)}")
            return False

    @staticmethod
    def validate_trades_data(trades) -> bool:
        """Validate trades data structure and content.
        
        Args:
            trades: Trades data (DataFrame, list, or dict)
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Handle different input types
            if isinstance(trades, pd.DataFrame):
                if trades.empty:
                    logger.warning("Empty trades data")
                    return True
            elif isinstance(trades, (list, tuple)):
                if not trades:
                    logger.warning("Empty trades data")
                    return True
                # Convert to DataFrame for validation if it's a list of dicts
                if all(isinstance(item, dict) for item in trades):
                    trades = pd.DataFrame(trades)
                else:
                    return True  # Can't validate non-dict list items
            elif isinstance(trades, dict):
                if not trades:
                    logger.warning("Empty trades data")
                    return True
                # Convert single trade to DataFrame
                trades = pd.DataFrame([trades])
            else:
                logger.warning(f"Unsupported trades data type: {type(trades)}")
                return True
            
            required_columns = ['symbol', 'side', 'price', 'amount']
            
            # Check required columns
            if not all(col in trades.columns for col in required_columns):
                logger.error("Missing required columns in trades data")
                return False
            
            # Check for NaN values
            if trades[required_columns].isna().any().any():
                logger.error("NaN values found in trades data")
                return False
            
            # Check for negative values
            if (trades[['price', 'amount']] < 0).any().any():
                logger.error("Negative values found in trades data")
                return False
            
            # Check side values
            valid_sides = ['buy', 'sell']
            if not trades['side'].isin(valid_sides).all():
                logger.error("Invalid side values in trades data")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating trades data: {str(e)}")
            return False

    @staticmethod
    def validate_orderbook_data(orderbook) -> bool:
        """Validate orderbook data structure and content.
        
        Args:
            orderbook: Orderbook data (DataFrame, dict, or list)
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Handle different input types
            if isinstance(orderbook, pd.DataFrame):
                if orderbook.empty:
                    logger.warning("Empty orderbook data")
                    return True
            elif isinstance(orderbook, dict):
                if not orderbook:
                    logger.warning("Empty orderbook data")
                    return True
                # Common orderbook structure: {'bids': [], 'asks': []}
                if 'bids' in orderbook or 'asks' in orderbook:
                    return True  # Basic structure check passed
                # Convert to DataFrame if it has the right structure
                if 'price' in orderbook and 'size' in orderbook:
                    orderbook = pd.DataFrame([orderbook])
                else:
                    return True  # Can't validate unknown dict structure
            elif isinstance(orderbook, (list, tuple)):
                if not orderbook:
                    logger.warning("Empty orderbook data")
                    return True
                return True  # Can't validate list orderbook
            else:
                logger.warning(f"Unsupported orderbook data type: {type(orderbook)}")
                return True
            
            required_columns = ['price', 'size', 'side']
            
            # Check required columns
            if not all(col in orderbook.columns for col in required_columns):
                logger.error("Missing required columns in orderbook data")
                return False
            
            # Check for NaN values
            if orderbook[required_columns].isna().any().any():
                logger.error("NaN values found in orderbook data")
                return False
            
            # Check for negative values
            if (orderbook[['price', 'size']] < 0).any().any():
                logger.error("Negative values found in orderbook data")
                return False
            
            # Check side values
            valid_sides = ['bid', 'ask']
            if not orderbook['side'].isin(valid_sides).all():
                logger.error("Invalid side values in orderbook data")
                return False
            
            # Check price ordering
            bids = orderbook[orderbook['side'] == 'bid']['price']
            asks = orderbook[orderbook['side'] == 'ask']['price']
            
            if not bids.empty and not asks.empty:
                if bids.max() >= asks.min():
                    logger.error("Invalid price ordering in orderbook")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating orderbook data: {str(e)}")
            return False

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