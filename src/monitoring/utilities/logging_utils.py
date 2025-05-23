"""
Logging utilities for market monitoring.

This module provides centralized logging functionality for standardizing
and consolidating logging operations across the monitoring system.
"""

import logging
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional


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
                    self.logger.debug(f"  Average: {avg_price:.6f}")
                    self.logger.debug(f"  Min: {min_price:.6f}")
                    self.logger.debug(f"  Max: {max_price:.6f}")
                
                if volumes:
                    volumes_array = np.array(volumes)
                    total_volume = np.sum(volumes_array)
                    avg_volume = np.mean(volumes_array)
                    
                    self.logger.debug(f"\nVolume statistics:")
                    self.logger.debug(f"  Total: {total_volume:.6f}")
                    self.logger.debug(f"  Average: {avg_volume:.6f}")
                    
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