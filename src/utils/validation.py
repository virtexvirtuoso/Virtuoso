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
        """Validate market data structure and content.
        
        Args:
            data: Market data dictionary
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Check required keys
            required_keys = ['symbol', 'timestamp', 'price_data', 'metadata']
            if not all(key in data for key in required_keys):
                logger.error(f"Missing required keys in market data: {required_keys}")
                return False
            
            # Validate price data
            if not DataValidator.validate_price_data(data['price_data']):
                return False
            
            # Validate trades if present
            if 'trades' in data and not DataValidator.validate_trades_data(data['trades']):
                return False
            
            # Validate orderbook if present
            if 'orderbook' in data and not DataValidator.validate_orderbook_data(data['orderbook']):
                return False
            
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
    def validate_trades_data(trades: pd.DataFrame) -> bool:
        """Validate trades data structure and content.
        
        Args:
            trades: Trades DataFrame
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            if trades.empty:
                logger.warning("Empty trades data")
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
    def validate_orderbook_data(orderbook: pd.DataFrame) -> bool:
        """Validate orderbook data structure and content.
        
        Args:
            orderbook: Orderbook DataFrame
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            if orderbook.empty:
                logger.warning("Empty orderbook data")
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