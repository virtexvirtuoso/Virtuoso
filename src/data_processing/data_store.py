"""Data storage management for market data."""

from collections import defaultdict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import logging
import traceback

logger = logging.getLogger(__name__)

class DataStore:
    """Manages storage and retrieval of market data."""
    
    def __init__(self, max_items: int = 1000):
        """Initialize data store.
        
        Args:
            max_items: Maximum number of items to store per data type
        """
        self.max_items = max_items
        
        # Initialize data structures
        self._trade_data = defaultdict(list)
        self._orderbook_data = {}
        self._ticker_data = {}
        self._kline_data = defaultdict(lambda: {
            'base': [],
            'ltf': [],
            'mtf': [],
            'htf': []
        })
        
    def store_trade(self, symbol: str, data: Dict[str, Any]) -> None:
        """Store trade data."""
        if not data:
            return
        
        # Format trade data
        trade = {
            'price': float(data.get('price', 0)),
            'size': float(data.get('size', 0)),
            'side': data.get('side', ''),
            'time': int(data.get('time', datetime.now().timestamp() * 1000))
        }
        
        # Store trade
        self._trade_data[symbol].append(trade)
        if len(self._trade_data[symbol]) > self.max_items:
            self._trade_data[symbol] = self._trade_data[symbol][-self.max_items:]
            
    def store_orderbook(self, symbol: str, data: Dict[str, Any]) -> None:
        """Store orderbook data."""
        if not data:
            return
            
        # Format orderbook data
        orderbook = {
            'bids': [[float(p), float(s)] for p, s in data.get('bids', [])],
            'asks': [[float(p), float(s)] for p, s in data.get('asks', [])],
            'timestamp': int(data.get('timestamp', datetime.now().timestamp() * 1000))
        }
        
        # Store orderbook
        self._orderbook_data[symbol] = orderbook
        
    def store_ticker(self, symbol: str, data: Dict[str, Any]) -> None:
        """Store ticker data."""
        if not data:
            return
            
        # Get existing ticker data
        existing_ticker = self._ticker_data.get(symbol, {})
            
        # Format ticker data with all Bybit API fields
        ticker = {
            'lastPrice': float(data.get('lastPrice', data.get('last_price', existing_ticker.get('lastPrice', 0)))),
            'indexPrice': float(data.get('indexPrice', data.get('index_price', existing_ticker.get('indexPrice', 0)))),
            'markPrice': float(data.get('markPrice', data.get('mark_price', existing_ticker.get('markPrice', 0)))),
            'prevPrice24h': float(data.get('prevPrice24h', data.get('prev_price_24h', existing_ticker.get('prevPrice24h', 0)))),
            'price24hPcnt': float(data.get('price24hPcnt', data.get('price_24h_pcnt', existing_ticker.get('price24hPcnt', 0)))),
            'highPrice24h': float(data.get('highPrice24h', data.get('high_price_24h', existing_ticker.get('highPrice24h', 0)))),
            'lowPrice24h': float(data.get('lowPrice24h', data.get('low_price_24h', existing_ticker.get('lowPrice24h', 0)))),
            'prevPrice1h': float(data.get('prevPrice1h', data.get('prev_price_1h', existing_ticker.get('prevPrice1h', 0)))),
            'openInterest': float(data.get('openInterest', data.get('open_interest', existing_ticker.get('openInterest', 0)))),
            'openInterestValue': float(data.get('openInterestValue', data.get('open_interest_value', existing_ticker.get('openInterestValue', 0)))),
            'turnover24h': float(data.get('turnover24h', data.get('turnover_24h', existing_ticker.get('turnover24h', 0)))),
            'volume24h': float(data.get('volume24h', data.get('volume_24h', existing_ticker.get('volume24h', 0)))),
            'fundingRate': float(data.get('fundingRate', data.get('funding_rate', existing_ticker.get('fundingRate', 0)))),
            'nextFundingTime': int(data.get('nextFundingTime', data.get('next_funding_time', existing_ticker.get('nextFundingTime', 0)))),
            'bid1Price': float(data.get('bid1Price', data.get('bid1_price', existing_ticker.get('bid1Price', 0)))),
            'bid1Size': float(data.get('bid1Size', data.get('bid1_size', existing_ticker.get('bid1Size', 0)))),
            'ask1Price': float(data.get('ask1Price', data.get('ask1_price', existing_ticker.get('ask1Price', 0)))),
            'ask1Size': float(data.get('ask1Size', data.get('ask1_size', existing_ticker.get('ask1Size', 0)))),
            'tickDirection': data.get('tickDirection', data.get('tick_direction', existing_ticker.get('tickDirection', ''))),
            'timestamp': int(data.get('timestamp', datetime.now().timestamp() * 1000))
        }
        
        # Store ticker
        self._ticker_data[symbol] = ticker
        
    def store_kline(self, symbol: str, data: Dict[str, Any], timeframe: str = 'base') -> None:
        """Store kline data.
        
        Args:
            symbol: Trading symbol
            data: Kline data dictionary
            timeframe: Timeframe identifier ('base', 'ltf', 'mtf', 'htf')
        """
        if not data:
            logger.warning(f"Empty kline data for {symbol}")
            return
            
        try:
            # Validate timeframe
            if timeframe not in ['base', 'ltf', 'mtf', 'htf']:
                logger.warning(f"Invalid timeframe {timeframe}, defaulting to base")
                timeframe = 'base'
                
            # Format kline data
            kline = {
                'timestamp': int(data.get('timestamp', 0)),
                'open': float(data.get('open', 0)),
                'high': float(data.get('high', 0)),
                'low': float(data.get('low', 0)),
                'close': float(data.get('close', 0)),
                'volume': float(data.get('volume', 0)),
                'turnover': float(data.get('turnover', 0)),
                'timeframe': timeframe
            }
            
            logger.debug(f"Storing kline for {symbol} @ {timeframe}: {kline['timestamp']}")
            
            # Store kline in appropriate timeframe list
            self._kline_data[symbol][timeframe].append(kline)
            
            # Keep only recent klines
            if len(self._kline_data[symbol][timeframe]) > self.max_items:
                self._kline_data[symbol][timeframe] = sorted(
                    self._kline_data[symbol][timeframe],
                    key=lambda x: x['timestamp']
                )[-self.max_items:]
                
            logger.debug(f"Stored kline for {symbol} @ {timeframe} - Total klines: {len(self._kline_data[symbol][timeframe])}")
            
        except Exception as e:
            logger.error(f"Error storing kline for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            
    def get_trades(self, symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade data for a symbol."""
        trades = self._trade_data[symbol]
        if limit:
            return trades[-limit:]
        return trades
        
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest orderbook for a symbol."""
        return self._orderbook_data.get(symbol)
        
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest ticker for a symbol."""
        return self._ticker_data.get(symbol)
        
    def get_klines(self, symbol: str, timeframe: str = 'base', limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get kline data for a symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe identifier ('base', 'ltf', 'mtf', 'htf')
            limit: Optional limit on number of klines to return
            
        Returns:
            List of kline data dictionaries
        """
        try:
            # Get klines for timeframe
            klines = self._kline_data[symbol][timeframe]
            
            # Sort by timestamp and apply limit if specified
            sorted_klines = sorted(klines, key=lambda x: x['timestamp'])
            if limit:
                sorted_klines = sorted_klines[-limit:]
                
            return sorted_klines
            
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return []
        
    def cleanup_old_data(self, max_age: timedelta = timedelta(hours=1)) -> None:
        """Clean up old data from stores."""
        cutoff = int((datetime.now() - max_age).timestamp() * 1000)
        
        # Clean up ticker data
        for symbol in list(self._ticker_data.keys()):
            if self._ticker_data[symbol]['timestamp'] < cutoff:
                del self._ticker_data[symbol]
                
        # Clean up orderbook data
        for symbol in list(self._orderbook_data.keys()):
            if self._orderbook_data[symbol]['timestamp'] < cutoff:
                del self._orderbook_data[symbol]
                
    def get_symbols(self) -> List[str]:
        """Get list of all tracked symbols."""
        symbols = set()
        symbols.update(self._trade_data.keys())
        symbols.update(self._orderbook_data.keys())
        symbols.update(self._ticker_data.keys())
        symbols.update(self._kline_data.keys())
        return sorted(list(symbols)) 