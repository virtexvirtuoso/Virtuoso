"""Data manager module.

This module provides functionality for managing market data.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
import json

from src.core.validation import (
    ValidationService,
    AsyncValidationService,
    ValidationContext,
    ValidationResult,
    TimeSeriesValidator,
    OrderBookValidator,
    TradesValidator
)
from src.core.error.models import ErrorContext, ErrorSeverity

from .data_store import DataStore
from .error_handler import SimpleErrorHandler

logger = logging.getLogger(__name__)

class DataManager:
    """Manages market data processing and storage."""
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """Initialize data manager.
        
        Args:
            config: Configuration dictionary
            error_handler: Optional error handler instance
        """
        self.config = config
        self.error_handler = error_handler or SimpleErrorHandler()
        
        # Initialize data store
        self.data_store = DataStore(
            max_items=config.get('max_items', 1000)
        )
        
        # Initialize data storage
        self._price_data = {}  # Latest price data by symbol
        self._trade_data = {}  # Recent trades by symbol
        self._orderbook_data = {}  # Latest orderbook by symbol
        self._kline_data = {}  # Recent klines by symbol
        self._funding_data = {}  # Latest funding data by symbol
        self._oi_data = {}  # Latest open interest data by symbol
        self._ratio_data = {}  # Latest long/short ratio data by symbol
        
        # Initialize validators
        self.validation_service = AsyncValidationService()
        self.time_series_validator = TimeSeriesValidator()
        self.orderbook_validator = OrderBookValidator()
        self.trades_validator = TradesValidator()
        
        # Register validators
        self.validation_service.register_validator('time_series', self.time_series_validator)
        self.validation_service.register_validator('orderbook', self.orderbook_validator)
        self.validation_service.register_validator('trades', self.trades_validator)
        
        self._market_data: Dict[str, Dict[str, Any]] = {}
        self._ticker_state: Dict[str, Dict[str, Any]] = {}
        
        logger.debug("DataManager initialized")

    async def process_market_data(
        self,
        data: Dict[str, Any],
        data_type: str,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Process market data.
        
        Args:
            data: Market data to process
            data_type: Type of market data
            symbol: Trading symbol
            
        Returns:
            Processed market data if successful, None otherwise
        """
        try:
            # Validate data
            ctx = ValidationContext(data_type=data_type, symbol=symbol)
            if not self.validation_service.validate(data, ctx):
                return None
            
            # Initialize market data structure if needed
            if symbol not in self._market_data:
                logger.debug(f"Initializing market data structure for {symbol}")
                self._market_data[symbol] = {
                    'ticker': None,
                    'trades': [],
                    'orderbook': None,
                    'klines': {
                        'base': [],
                        'ltf': [],
                        'mtf': [],
                        'htf': []
                    },
                    'momentum': {
                        'trades': []
                    },
                    'volume': {
                        'trades': [],
                        'ticker': None
                    },
                    'orderflow': {},
                    'position': {
                        'trades': [],
                        'ticker': None,
                        'orderbook': None
                    },
                    'sentiment': {
                        'trades': [],
                        'ticker': None,
                        'orderbook': None
                    }
                }
            
            # Process based on data type
            if data_type == 'kline':
                # Get timeframe from data
                timeframe = data.get('timeframe', 'base')
                logger.debug(f"[KLINE FLOW] Processing kline for {symbol} @ {timeframe}")
                
                # Ensure klines structure exists
                if 'klines' not in self._market_data[symbol]:
                    self._market_data[symbol]['klines'] = {
                        'base': [],
                        'ltf': [],
                        'mtf': [],
                        'htf': []
                    }
                
                # Add kline to appropriate timeframe
                self._market_data[symbol]['klines'][timeframe].append(data)
                
                # Sort and limit klines
                max_klines = self.config.get('max_klines', 1000)
                self._market_data[symbol]['klines'][timeframe] = sorted(
                    self._market_data[symbol]['klines'][timeframe],
                    key=lambda x: x['timestamp']
                )[-max_klines:]
                
                logger.debug(f"[KLINE FLOW] Added kline to {timeframe} timeframe. Total klines: " + 
                           ", ".join(f"{tf}: {len(self._market_data[symbol]['klines'][tf])}" 
                                   for tf in self._market_data[symbol]['klines']))
                return data
                
            elif data_type == 'ticker':
                self._market_data[symbol]['ticker'] = data
                self._market_data[symbol]['volume']['ticker'] = data
                self._market_data[symbol]['position']['ticker'] = data
                self._market_data[symbol]['sentiment']['ticker'] = data
                return data
                
            elif data_type == 'trade':
                # Add trade to lists
                self._market_data[symbol]['trades'].append(data)
                self._market_data[symbol]['momentum']['trades'].append(data)
                self._market_data[symbol]['volume']['trades'].append(data)
                self._market_data[symbol]['position']['trades'].append(data)
                self._market_data[symbol]['sentiment']['trades'].append(data)
                
                # Limit trade history
                max_trades = self.config.get('max_trades', 1000)
                for key in ['trades', 'momentum.trades', 'volume.trades', 'position.trades', 'sentiment.trades']:
                    parts = key.split('.')
                    target = self._market_data[symbol]
                    for part in parts[:-1]:
                        target = target[part]
                    target[parts[-1]] = target[parts[-1]][-max_trades:]
                return data
                
            elif data_type == 'orderbook':
                self._market_data[symbol]['orderbook'] = data
                self._market_data[symbol]['position']['orderbook'] = data
                self._market_data[symbol]['sentiment']['orderbook'] = data
                return data
                
            else:
                logger.warning(f"Unknown data type: {data_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing market data: {str(e)}")
            logger.debug(f"Failed data: {json.dumps(data, indent=2)}")
            return None
            
    def get_trades(self, symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade data for a symbol."""
        return self.data_store.get_trades(symbol, limit)
        
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest orderbook for a symbol."""
        return self.data_store.get_orderbook(symbol)
        
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest ticker for a symbol."""
        return self.data_store.get_ticker(symbol)
        
    def get_klines(self, symbol: str, timeframe: str = 'base', limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get kline data for a symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe identifier ('base', 'ltf', 'mtf', 'htf')
            limit: Optional limit on number of klines to return
            
        Returns:
            List of kline data dictionaries
        """
        return self.data_store.get_klines(symbol, timeframe=timeframe, limit=limit)
        
    def get_symbols(self) -> List[str]:
        """Get list of all tracked symbols."""
        return self.data_store.get_symbols()
        
    async def get_latest_market_data(self) -> Dict[str, Dict[str, Any]]:
        """Get latest market data for all symbols.
        
        Returns:
            Dictionary mapping symbols to their market data
        """
        try:
            market_data = {}
            symbols = self.data_store.get_symbols()
            
            for symbol in symbols:
                # Get data for each type
                ticker = self.data_store.get_ticker(symbol)
                trades = self.data_store.get_trades(symbol, limit=100)  # Get last 100 trades
                orderbook = self.data_store.get_orderbook(symbol)
                
                # Get klines for each timeframe
                klines = {}
                timeframes = ['base', 'ltf', 'mtf', 'htf']
                for tf in timeframes:
                    tf_klines = self.data_store.get_klines(symbol, timeframe=tf)
                    if tf_klines:  # Only add timeframe if we have data
                        klines[tf] = tf_klines
                
                # Log data availability for debugging
                logger.debug(f"Got market data for {symbol}: "
                           f"ticker={bool(ticker)}, "
                           f"trades={len(trades)}, "
                           f"orderbook={bool(orderbook)}, "
                           f"klines={sum(len(k) for k in klines.values())}")
                
                # Store data if we have any
                if any([ticker, trades, orderbook, klines]):
                    market_data[symbol] = {
                        'ticker': ticker or {},
                        'trades': trades or [],
                        'orderbook': orderbook or {'bids': [], 'asks': []},
                        'klines': klines
                    }
                    
            logger.debug(f"Retrieved market data for {len(market_data)} symbols")
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting latest market data: {str(e)}")
            return {}
        
    async def update_market_data(self, data: Dict[str, Any]) -> None:
        """Update market data state."""
        try:
            if not data:
                return
                
            symbol = data.get('symbol')
            data_type = data.get('type')
            
            if not symbol or not data_type:
                logger.warning("Missing symbol or type in market data")
                return
                
            # Initialize market data structure for symbol if needed
            if symbol not in self._market_data:
                self._market_data[symbol] = {
                    'ticker': None,
                    'trades': [],
                    'orderbook': None,
                    'klines': {
                        'base': [],
                        'ltf': [],
                        'mtf': [],
                        'htf': []
                    },
                    'momentum': {},
                    'volume': {},
                    'orderflow': {},
                    'position': {},
                    'sentiment': {}
                }
                
            # Special handling for ticker delta updates
            if data_type == 'ticker':
                if symbol not in self._ticker_state:
                    self._ticker_state[symbol] = {}
                
                # Update ticker state with new data, preserving existing values
                current_state = self._ticker_state[symbol]
                for key, value in data.items():
                    if key not in ['type', 'symbol'] and value != 0:  # Only update non-zero values
                        current_state[key] = value
                
                # Update market data with complete ticker state
                self._market_data[symbol]['ticker'] = current_state.copy()
                # Store in DataStore
                self.data_store.store_ticker(symbol, current_state)
                
            # Handle other data types
            elif data_type == 'trades':
                self._market_data[symbol]['trades'].append(data)
                # Store in DataStore
                self.data_store.store_trade(symbol, data)
                # Keep only recent trades
                max_trades = self.config.get('max_trades', 1000)
                if len(self._market_data[symbol]['trades']) > max_trades:
                    self._market_data[symbol]['trades'] = self._market_data[symbol]['trades'][-max_trades:]
            elif data_type == 'orderbook':
                self._market_data[symbol]['orderbook'] = data
                # Store in DataStore
                self.data_store.store_orderbook(symbol, data)
            elif data_type == 'kline':
                # Handle single kline or list of klines
                klines_to_store = data if isinstance(data, list) else [data]
                
                for kline in klines_to_store:
                    try:
                        # Get timeframe from kline data or use default
                        timeframe = kline.get('timeframe', 'base')
                        
                        # Initialize timeframe in market data if needed
                        if 'klines' not in self._market_data[symbol]:
                            self._market_data[symbol]['klines'] = {
                                'base': [],
                                'ltf': [],
                                'mtf': [],
                                'htf': []
                            }
                        
                        # Add kline to market data
                        self._market_data[symbol]['klines'][timeframe].append(kline)
                        
                        # Keep only recent klines
                        max_klines = self.config.get('max_klines', 1000)
                        if len(self._market_data[symbol]['klines'][timeframe]) > max_klines:
                            self._market_data[symbol]['klines'][timeframe] = \
                                sorted(self._market_data[symbol]['klines'][timeframe], 
                                      key=lambda x: x['timestamp'])[-max_klines:]
                        
                        logger.debug(f"Updated market data with kline for {symbol} @ {timeframe} - Total klines: {len(self._market_data[symbol]['klines'][timeframe])}")
                        
                    except Exception as e:
                        logger.error(f"Error updating market data with kline for {symbol}: {str(e)}")
                        continue
                
            # Update component-specific data
            if data_type == 'ticker' or data_type == 'trades':
                self._market_data[symbol]['momentum']['trades'] = self._market_data[symbol]['trades']
                self._market_data[symbol]['volume']['trades'] = self._market_data[symbol]['trades']
                self._market_data[symbol]['volume']['ticker'] = self._market_data[symbol]['ticker']
                
            if data_type == 'orderbook' or data_type == 'trades':
                self._market_data[symbol]['orderflow']['trades'] = self._market_data[symbol]['trades']
                self._market_data[symbol]['orderflow']['orderbook'] = self._market_data[symbol]['orderbook']
                
            if data_type in ['ticker', 'trades', 'orderbook']:
                self._market_data[symbol]['position']['trades'] = self._market_data[symbol]['trades']
                self._market_data[symbol]['position']['ticker'] = self._market_data[symbol]['ticker']
                self._market_data[symbol]['position']['orderbook'] = self._market_data[symbol]['orderbook']
                
                self._market_data[symbol]['sentiment']['trades'] = self._market_data[symbol]['trades']
                self._market_data[symbol]['sentiment']['ticker'] = self._market_data[symbol]['ticker']
                self._market_data[symbol]['sentiment']['orderbook'] = self._market_data[symbol]['orderbook']
                
            logger.debug(f"Updated market data for {symbol} - Type: {data_type}")
            
        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")
            if self.error_handler:
                await self.error_handler.handle_error(
                    error=e,
                    operation="update_market_data",
                    data={'symbol': symbol, 'data': data}
                )
            
    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for a symbol."""
        return self._market_data.get(symbol, {})
        
    async def is_healthy(self) -> bool:
        """Check if the data manager is healthy."""
        try:
            # Check if we have any market data
            if not self._market_data:
                return False
                
            # Check if we have recent data for any symbol
            current_time = time.time() * 1000
            for symbol_data in self._market_data.values():
                ticker = symbol_data.get('ticker', {})
                if ticker and current_time - ticker.get('timestamp', 0) < 60000:  # Within last minute
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking health: {str(e)}")
            return False 