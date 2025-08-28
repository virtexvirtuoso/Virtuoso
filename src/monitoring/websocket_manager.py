"""
WebSocket Manager Module for Monitoring

Handles WebSocket connections and message processing for real-time market data
updates in the Virtuoso CCXT trading system.

This module is responsible for:
- Managing WebSocket connections and lifecycle
- Processing different types of WebSocket messages
- Updating internal data stores with real-time data
- Providing connection status and health monitoring
"""

import asyncio
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from src.core.exchanges.websocket_manager import WebSocketManager as CoreWebSocketManager
from src.core.cache.liquidation_cache import liquidation_cache


class MonitoringWebSocketManager:
    """
    WebSocket manager for monitoring system.
    
    Handles real-time data updates for market monitoring including tickers,
    OHLCV data, orderbook updates, trades, and liquidation events.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        symbol: str,
        exchange_id: str,
        timestamp_utility,
        metrics_manager=None,
        health_monitor=None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the WebSocket manager.
        
        Args:
            config: Configuration dictionary with WebSocket settings
            symbol: Trading symbol to monitor
            exchange_id: Exchange identifier
            timestamp_utility: Utility for timestamp handling
            metrics_manager: Metrics manager for tracking
            health_monitor: Health monitor for status reporting
            logger: Logger instance
        """
        self.config = config
        self.symbol = symbol
        self.symbol_str = symbol
        self.exchange_id = exchange_id
        self.timestamp_utility = timestamp_utility
        self.metrics_manager = metrics_manager
        self.health_monitor = health_monitor
        self.logger = logger or logging.getLogger(__name__)
        
        # WebSocket configuration
        self.websocket_config = config.get('websocket_config', {
            'enabled': True,
            'use_ws_for_orderbook': True,
            'use_ws_for_trades': True,
            'use_ws_for_tickers': True
        })
        
        # Core WebSocket manager
        self.ws_manager = None
        
        # Data storage for WebSocket updates
        self.ws_data = {
            'ticker': {},
            'orderbook': {},
            'trades': [],
            'liquidations': [],
            'kline': {},
            'last_update_time': {
                'ticker': None,
                'orderbook': None,
                'trades': None,
                'liquidations': None,
                'kline': None
            }
        }
        
        # Connection status
        self.is_connected = False
        self.last_message_time = None
        
        self.logger.info(f"Monitoring WebSocket Manager initialized for {symbol}")

    async def initialize(self) -> None:
        """Initialize WebSocket connection for real-time data."""
        if not self.websocket_config.get('enabled', True):
            self.logger.info("WebSocket disabled in configuration")
            return
            
        if not self.symbol_str:
            self.logger.info("Skipping WebSocket initialization: No symbol provided")
            return
            
        try:
            # Initialize core WebSocket Manager
            self.ws_manager = CoreWebSocketManager(self.config)
            
            # Register callback for WebSocket messages
            self.ws_manager.register_message_callback(self._process_websocket_message)
            
            # Create the list of symbols for the WebSocket manager to track
            symbols = [self.symbol_str]
            
            # Initialize asynchronously
            await self.ws_manager.initialize(symbols)
            self.is_connected = True
            
            self.logger.info(f"WebSocket integration initialized for {self.symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.ws_manager = None
            self.is_connected = False
            
            # Update health status if available
            if self.health_monitor:
                self.health_monitor._create_alert(
                    level="warning",
                    source=f"websocket:{self.exchange_id}",
                    message=f"Failed to initialize WebSocket: {str(e)}"
                )

    async def _process_websocket_message(self, symbol: str, topic: str, message: Dict[str, Any]) -> None:
        """Process WebSocket message and update internal data."""
        try:
            # Start performance tracking
            operation = None
            if self.metrics_manager:
                operation = self.metrics_manager.start_operation(f"process_ws_message_{topic}")
            
            # Check if the message is for the symbol we're monitoring
            if symbol != self.symbol_str:
                if self.metrics_manager and operation:
                    self.metrics_manager.end_operation(operation)
                return
                
            # Update last message time
            self.last_message_time = datetime.utcnow()
            
            # Process based on topic type
            if "tickers" in topic:
                await self._process_ticker_update(message)
            elif "kline" in topic:
                await self._process_kline_update(message)
            elif "orderbook" in topic:
                await self._process_orderbook_update(message)
            elif "publicTrade" in topic:
                await self._process_trade_update(message)
            elif "liquidation" in topic:
                await self._process_liquidation_update(message)
            else:
                self.logger.debug(f"Received unhandled topic: {topic}")
                
            # Record metrics
            if self.metrics_manager:
                self.metrics_manager.record_metric("websocket_messages_processed", 1)
                self.metrics_manager.record_metric(f"websocket_messages_{topic}", 1)
            
            # End operation
            if self.metrics_manager and operation:
                self.metrics_manager.end_operation(operation)
            
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message for {topic}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # End operation if it was started
            if self.metrics_manager and 'operation' in locals() and operation:
                self.metrics_manager.end_operation(operation, success=False)

    async def _process_ticker_update(self, message: Dict[str, Any]) -> None:
        """Process ticker update from WebSocket."""
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract ticker data
            ticker_data = data.get('data', {})
            if not ticker_data:
                return
                
            # Format ticker data
            ticker = {
                'symbol': self.symbol,
                'last': float(ticker_data.get('lastPrice', 0)),
                'bid': float(ticker_data.get('bid1Price', 0)),
                'ask': float(ticker_data.get('ask1Price', 0)),
                'high': float(ticker_data.get('highPrice24h', 0)),
                'low': float(ticker_data.get('lowPrice24h', 0)),
                'volume': float(ticker_data.get('volume24h', 0)),
                'timestamp': int(ticker_data.get('time', timestamp))
            }
            
            # Add additional data if available
            if 'openInterest' in ticker_data:
                ticker['openInterest'] = float(ticker_data['openInterest'])
            if 'fundingRate' in ticker_data:
                ticker['fundingRate'] = float(ticker_data['fundingRate'])
            if 'nextFundingTime' in ticker_data:
                ticker['nextFundingTime'] = int(ticker_data['nextFundingTime'])
            
            # Update internal state
            self.ws_data['ticker'] = ticker
            self.ws_data['last_update_time']['ticker'] = timestamp
            
            # Log update
            self.logger.debug(f"Updated ticker data from WebSocket: Last price: {ticker['last']}")
            
        except Exception as e:
            self.logger.error(f"Error processing ticker update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_kline_update(self, message: Dict[str, Any]) -> None:
        """Process OHLCV update from WebSocket."""
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract kline data
            kline_data = data.get('data', [])
            if not kline_data:
                return
                
            # Get interval from topic (if available)
            topic = message.get('topic', '')
            interval = '1m'  # Default interval
            
            # Extract interval from topic string if possible
            if 'kline.' in topic:
                parts = topic.split('.')
                if len(parts) > 1:
                    interval = parts[1]
            
            # Process kline data
            for kline in kline_data:
                ohlcv = {
                    'timestamp': int(kline.get('start', timestamp)),
                    'open': float(kline.get('open', 0)),
                    'high': float(kline.get('high', 0)),
                    'low': float(kline.get('low', 0)),
                    'close': float(kline.get('close', 0)),
                    'volume': float(kline.get('volume', 0)),
                    'interval': interval
                }
                
                # Update internal state
                if interval not in self.ws_data['kline']:
                    self.ws_data['kline'][interval] = []
                
                self.ws_data['kline'][interval].append(ohlcv)
                self.ws_data['last_update_time']['kline'] = timestamp
                
                # Keep only recent kline data (last 1000 candles)
                if len(self.ws_data['kline'][interval]) > 1000:
                    self.ws_data['kline'][interval] = self.ws_data['kline'][interval][-1000:]
                
                self.logger.debug(f"Updated {interval} kline data: OHLCV={ohlcv['open']:.2f}/{ohlcv['high']:.2f}/{ohlcv['low']:.2f}/{ohlcv['close']:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error processing kline update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_orderbook_update(self, message: Dict[str, Any]) -> None:
        """Process orderbook update from WebSocket."""
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract orderbook data
            ob_data = data.get('data', {})
            if not ob_data:
                return
                
            # Format orderbook data
            orderbook = {
                'symbol': self.symbol,
                'bids': [[float(bid[0]), float(bid[1])] for bid in ob_data.get('b', [])],
                'asks': [[float(ask[0]), float(ask[1])] for ask in ob_data.get('a', [])],
                'timestamp': int(ob_data.get('u', timestamp))
            }
            
            # Update internal state
            self.ws_data['orderbook'] = orderbook
            self.ws_data['last_update_time']['orderbook'] = timestamp
            
            # Log update
            best_bid = orderbook['bids'][0][0] if orderbook['bids'] else 0
            best_ask = orderbook['asks'][0][0] if orderbook['asks'] else 0
            self.logger.debug(f"Updated orderbook: Best bid: {best_bid:.2f}, Best ask: {best_ask:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_trade_update(self, message: Dict[str, Any]) -> None:
        """Process trade update from WebSocket."""
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract trade data
            trade_data = data.get('data', [])
            if not trade_data:
                return
                
            # Process each trade
            for trade in trade_data:
                trade_info = {
                    'symbol': self.symbol,
                    'id': str(trade.get('i', '')),
                    'price': float(trade.get('p', 0)),
                    'amount': float(trade.get('v', 0)),
                    'side': trade.get('S', 'unknown').lower(),
                    'timestamp': int(trade.get('T', timestamp))
                }
                
                # Add to trades list
                self.ws_data['trades'].append(trade_info)
                self.ws_data['last_update_time']['trades'] = timestamp
                
                # Keep only recent trades (last 1000)
                if len(self.ws_data['trades']) > 1000:
                    self.ws_data['trades'] = self.ws_data['trades'][-1000:]
                
                self.logger.debug(f"New trade: {trade_info['side']} {trade_info['amount']:.4f} @ {trade_info['price']:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error processing trade update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _process_liquidation_update(self, message: Dict[str, Any]) -> None:
        """Process liquidation update from WebSocket."""
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract liquidation data
            liquidation_data = data.get('data', {})
            if not liquidation_data:
                return
            
            # Format liquidation data
            liquidation = {
                'symbol': liquidation_data.get('symbol', self.symbol),
                'side': liquidation_data.get('side', 'unknown').lower(),
                'size': float(liquidation_data.get('size', 0)),
                'price': float(liquidation_data.get('price', 0)),
                'timestamp': int(liquidation_data.get('updatedTime', timestamp)),
                'source': 'websocket'
            }
            
            # Add to liquidations list
            self.ws_data['liquidations'].append(liquidation)
            self.ws_data['last_update_time']['liquidations'] = timestamp
            
            # Keep only recent liquidations (last 100)
            if len(self.ws_data['liquidations']) > 100:
                self.ws_data['liquidations'] = self.ws_data['liquidations'][-100:]
            
            # Update liquidation cache
            try:
                liquidation_cache.update_liquidation(
                    symbol=liquidation['symbol'],
                    side=liquidation['side'],
                    size=liquidation['size'],
                    price=liquidation['price'],
                    timestamp=liquidation['timestamp']
                )
            except Exception as cache_error:
                self.logger.error(f"Error updating liquidation cache: {str(cache_error)}")
            
            # Log liquidation event
            self.logger.warning(f"Liquidation detected: {liquidation['side']} {liquidation['size']} {liquidation['symbol']} @ {liquidation['price']}")
            
        except Exception as e:
            self.logger.error(f"Error processing liquidation update: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def get_websocket_status(self) -> Dict[str, Any]:
        """Get current WebSocket status."""
        status = {
            'connected': self.is_connected,
            'last_message_time': None,
            'seconds_since_last_message': None,
            'data_freshness': {},
            'enabled': self.websocket_config.get('enabled', False)
        }
        
        if self.last_message_time:
            status['last_message_time'] = self.last_message_time.isoformat()
            status['seconds_since_last_message'] = (datetime.utcnow() - self.last_message_time).total_seconds()
        
        # Add data freshness information
        current_time = self.timestamp_utility.get_utc_timestamp()
        for data_type, last_update in self.ws_data['last_update_time'].items():
            if last_update:
                age_seconds = (current_time - last_update) / 1000  # Convert ms to seconds
                status['data_freshness'][data_type] = {
                    'last_update': last_update,
                    'age_seconds': age_seconds
                }
        
        # Add core WebSocket manager status if available
        if self.ws_manager:
            core_status = self.ws_manager.get_status()
            status.update(core_status)
        
        return status

    def get_ticker_data(self) -> Optional[Dict[str, Any]]:
        """Get latest ticker data from WebSocket."""
        return self.ws_data['ticker'] if self.ws_data['ticker'] else None

    def get_orderbook_data(self) -> Optional[Dict[str, Any]]:
        """Get latest orderbook data from WebSocket."""
        return self.ws_data['orderbook'] if self.ws_data['orderbook'] else None

    def get_trades_data(self) -> List[Dict[str, Any]]:
        """Get recent trades data from WebSocket."""
        return self.ws_data['trades']

    def get_kline_data(self, interval: str = '1m') -> List[Dict[str, Any]]:
        """Get kline/OHLCV data for specified interval."""
        return self.ws_data['kline'].get(interval, [])

    def get_liquidations_data(self) -> List[Dict[str, Any]]:
        """Get recent liquidations data from WebSocket."""
        return self.ws_data['liquidations']

    async def close(self) -> None:
        """Close WebSocket connections and clean up resources."""
        try:
            if self.ws_manager:
                await self.ws_manager.close()
                self.ws_manager = None
            
            self.is_connected = False
            self.last_message_time = None
            
            # Clear data
            self.ws_data = {
                'ticker': {},
                'orderbook': {},
                'trades': [],
                'liquidations': [],
                'kline': {},
                'last_update_time': {
                    'ticker': None,
                    'orderbook': None,
                    'trades': None,
                    'liquidations': None,
                    'kline': None
                }
            }
            
            self.logger.info("WebSocket manager closed and cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error closing WebSocket manager: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def is_data_fresh(self, data_type: str, max_age_seconds: int = 60) -> bool:
        """Check if data type is fresh within the specified age limit."""
        last_update = self.ws_data['last_update_time'].get(data_type)
        if not last_update:
            return False
        
        current_time = self.timestamp_utility.get_utc_timestamp()
        age_seconds = (current_time - last_update) / 1000
        
        return age_seconds <= max_age_seconds