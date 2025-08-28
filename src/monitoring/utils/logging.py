"""
Logging utilities for the monitoring system.

This module provides centralized logging functionality with standardized formatting
and structured logging capabilities for different data types.
"""

import logging
import json
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from datetime import datetime, timezone


class LoggingUtility:
    """Centralized logging utility to standardize and consolidate logging operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the logging utility.
        
        Args:
            logger: Logger instance to use for logging. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def log_raw_response(self, data_type: str, symbol: str, data: Any) -> None:
        """Log raw API responses with detailed structure analysis.
        
        This method provides structured logging for different types of market data,
        making debugging and analysis easier by formatting the data appropriately
        for each type.
        
        Args:
            data_type: Type of data (OHLCV, Orderbook, Trades, Ticker, etc.)
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
            elif data_type == 'Ticker':
                self._log_ticker_data(data)
            else:
                # Generic logging for other data types
                self._log_generic_data(data)
            
            self.logger.debug(f"=== End {data_type} Response ===\n")
            
        except Exception as e:
            self.logger.error(f"Error logging raw response for {data_type}: {str(e)}")
    
    def _log_ohlcv_data(self, data: Any) -> None:
        """Log OHLCV data with proper formatting.
        
        Args:
            data: OHLCV data to log
        """
        if isinstance(data, pd.DataFrame):
            self.logger.debug(f"DataFrame shape: {data.shape}")
            self.logger.debug(f"Columns: {list(data.columns)}")
            if not data.empty:
                self.logger.debug(f"First row: {data.iloc[0].to_dict()}")
                self.logger.debug(f"Last row: {data.iloc[-1].to_dict()}")
                self.logger.debug(f"Date range: {data.index.min()} to {data.index.max()}")
        elif isinstance(data, list):
            self.logger.debug(f"List length: {len(data)}")
            if data:
                self.logger.debug(f"First candle: {data[0]}")
                self.logger.debug(f"Last candle: {data[-1]}")
        elif isinstance(data, dict):
            self.logger.debug(f"Dictionary keys: {list(data.keys())}")
            for key, value in data.items():
                if isinstance(value, pd.DataFrame):
                    self.logger.debug(f"  {key}: DataFrame({value.shape})")
                elif isinstance(value, list):
                    self.logger.debug(f"  {key}: List({len(value)} items)")
                else:
                    self.logger.debug(f"  {key}: {type(value).__name__}")
        else:
            self.logger.debug(f"Data type: {type(data).__name__}")
            self.logger.debug(f"Data: {str(data)[:500]}")
    
    def _log_orderbook_data(self, data: Any) -> None:
        """Log orderbook data with proper formatting.
        
        Args:
            data: Orderbook data to log
        """
        if isinstance(data, dict):
            self.logger.debug(f"Orderbook keys: {list(data.keys())}")
            
            # Log bids
            if 'bids' in data:
                bids = data['bids']
                if isinstance(bids, list) and bids:
                    self.logger.debug(f"Bids: {len(bids)} levels")
                    self.logger.debug(f"  Best bid: {bids[0]}")
                    if len(bids) > 1:
                        self.logger.debug(f"  2nd bid: {bids[1]}")
                else:
                    self.logger.debug(f"Bids: {type(bids).__name__}")
            
            # Log asks
            if 'asks' in data:
                asks = data['asks']
                if isinstance(asks, list) and asks:
                    self.logger.debug(f"Asks: {len(asks)} levels")
                    self.logger.debug(f"  Best ask: {asks[0]}")
                    if len(asks) > 1:
                        self.logger.debug(f"  2nd ask: {asks[1]}")
                else:
                    self.logger.debug(f"Asks: {type(asks).__name__}")
            
            # Log timestamp if available
            if 'timestamp' in data:
                self.logger.debug(f"Timestamp: {data['timestamp']}")
            
            # Log any other keys
            other_keys = [k for k in data.keys() if k not in ['bids', 'asks', 'timestamp']]
            if other_keys:
                self.logger.debug(f"Other keys: {other_keys}")
        else:
            self.logger.debug(f"Orderbook type: {type(data).__name__}")
            self.logger.debug(f"Data: {str(data)[:500]}")
    
    def _log_trades_data(self, data: Any) -> None:
        """Log trades data with proper formatting.
        
        Args:
            data: Trades data to log
        """
        if isinstance(data, list):
            self.logger.debug(f"Trades: {len(data)} trades")
            if data:
                # Log first trade
                first_trade = data[0]
                if isinstance(first_trade, dict):
                    self.logger.debug(f"First trade keys: {list(first_trade.keys())}")
                    self.logger.debug(f"First trade: {first_trade}")
                else:
                    self.logger.debug(f"First trade: {first_trade}")
                
                # Log last trade
                if len(data) > 1:
                    last_trade = data[-1]
                    self.logger.debug(f"Last trade: {last_trade}")
        elif isinstance(data, pd.DataFrame):
            self.logger.debug(f"Trades DataFrame shape: {data.shape}")
            self.logger.debug(f"Columns: {list(data.columns)}")
            if not data.empty:
                self.logger.debug(f"First trade: {data.iloc[0].to_dict()}")
                self.logger.debug(f"Last trade: {data.iloc[-1].to_dict()}")
        elif isinstance(data, dict):
            self.logger.debug(f"Trades dict keys: {list(data.keys())}")
            # Check for nested structure
            if 'result' in data:
                self._log_trades_data(data['result'])
            elif 'list' in data:
                self._log_trades_data(data['list'])
            else:
                for key, value in data.items():
                    self.logger.debug(f"  {key}: {type(value).__name__}")
        else:
            self.logger.debug(f"Trades type: {type(data).__name__}")
            self.logger.debug(f"Data: {str(data)[:500]}")
    
    def _log_ticker_data(self, data: Any) -> None:
        """Log ticker data with proper formatting.
        
        Args:
            data: Ticker data to log
        """
        if isinstance(data, dict):
            important_fields = ['symbol', 'bid', 'ask', 'last', 'volume', 'timestamp']
            
            self.logger.debug("Ticker data:")
            for field in important_fields:
                if field in data:
                    self.logger.debug(f"  {field}: {data[field]}")
            
            # Log other fields
            other_fields = [k for k in data.keys() if k not in important_fields]
            if other_fields:
                self.logger.debug(f"  Other fields: {other_fields[:10]}")
        else:
            self.logger.debug(f"Ticker type: {type(data).__name__}")
            self.logger.debug(f"Data: {str(data)[:500]}")
    
    def _log_generic_data(self, data: Any) -> None:
        """Log generic data with basic formatting.
        
        Args:
            data: Generic data to log
        """
        data_type = type(data).__name__
        self.logger.debug(f"Data type: {data_type}")
        
        if hasattr(data, '__len__'):
            self.logger.debug(f"Length: {len(data)}")
        
        if isinstance(data, dict):
            self.logger.debug(f"Keys: {list(data.keys())}")
            # Log first few key-value pairs
            for i, (key, value) in enumerate(data.items()):
                if i >= 5:
                    break
                value_type = type(value).__name__
                if hasattr(value, '__len__') and not isinstance(value, str):
                    self.logger.debug(f"  {key}: {value_type}(len={len(value)})")
                else:
                    self.logger.debug(f"  {key}: {value_type}")
        elif isinstance(data, (list, tuple)):
            if data:
                self.logger.debug(f"First item type: {type(data[0]).__name__}")
                self.logger.debug(f"First item: {str(data[0])[:200]}")
        else:
            # For other types, show string representation (limited)
            self.logger.debug(f"Data: {str(data)[:500]}")
    
    def log_operation(
        self,
        operation: str,
        symbol: Optional[str] = None,
        success: bool = True,
        duration: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an operation with structured context.
        
        Args:
            operation: Name of the operation
            symbol: Optional symbol being processed
            success: Whether the operation was successful
            duration: Optional duration in seconds
            details: Optional additional details
        """
        log_level = logging.INFO if success else logging.ERROR
        
        message_parts = [operation]
        if symbol:
            message_parts.append(f"for {symbol}")
        
        if success:
            message_parts.append("completed successfully")
        else:
            message_parts.append("failed")
        
        if duration is not None:
            message_parts.append(f"in {duration:.2f}s")
        
        message = " ".join(message_parts)
        
        if details:
            message += f" - {json.dumps(details, default=str)}"
        
        self.logger.log(log_level, message)
    
    def log_error_with_context(
        self,
        error: Exception,
        operation: str,
        symbol: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error with full context.
        
        Args:
            error: The exception that occurred
            operation: Operation that was being performed
            symbol: Optional symbol being processed
            context: Optional additional context
        """
        error_info = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
        }
        
        if symbol:
            error_info['symbol'] = symbol
        
        if context:
            error_info['context'] = context
        
        self.logger.error(f"Error in {operation}: {str(error)}")
        self.logger.debug(f"Error details: {json.dumps(error_info, default=str)}")
        
        # Log stack trace in debug mode
        import traceback
        self.logger.debug(f"Stack trace:\n{traceback.format_exc()}")
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "ms",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Log a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            tags: Optional tags for categorization
        """
        message = f"Performance: {metric_name}={value:.2f}{unit}"
        
        if tags:
            tag_str = ", ".join([f"{k}={v}" for k, v in tags.items()])
            message += f" [{tag_str}]"
        
        self.logger.debug(message)
    
    def create_child_logger(self, name: str) -> 'LoggingUtility':
        """Create a child logger with a specific name.
        
        Args:
            name: Name for the child logger
            
        Returns:
            New LoggingUtility instance with child logger
        """
        child_logger = self.logger.getChild(name)
        return LoggingUtility(child_logger)