"""WebSocket processing component for real-time market data."""

import asyncio
import json
import logging
import time
import traceback
from typing import Dict, Any, Optional, Callable
import pandas as pd

from ..utilities import TimestampUtility


class WebSocketProcessor:
    """Handles WebSocket connections and real-time data processing."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        metrics_manager=None,
        health_monitor=None
    ):
        """Initialize WebSocket processor.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
            metrics_manager: Metrics manager for performance tracking
            health_monitor: Health monitor for alerts
        """
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.metrics_manager = metrics_manager
        self.health_monitor = health_monitor
        
        # WebSocket configuration
        self.websocket_config = self.config.get('websocket', {})
        
        # WebSocket manager instance
        self.ws_manager = None
        
        # Real-time data storage
        self.ws_data = {
            'ticker': {},
            'kline': {},
            'orderbook': {},
            'trades': [],
            'liquidations': [],
            'last_update_time': {
                'ticker': 0,
                'kline': 0,
                'orderbook': 0,
                'trades': 0,
                'liquidations': 0
            }
        }
        
        # Symbol being monitored
        self.symbol = None
        self.symbol_str = None
        self.exchange_id = None
        
        # Timestamp utility
        self.timestamp_utility = TimestampUtility
        
        # Data change callbacks
        self.data_callbacks = {}
    
    def set_symbol_info(self, symbol: Any, symbol_str: str, exchange_id: str) -> None:
        """Set symbol information for the processor.
        
        Args:
            symbol: Symbol object
            symbol_str: Symbol string representation
            exchange_id: Exchange identifier
        """
        self.symbol = symbol
        self.symbol_str = symbol_str
        self.exchange_id = exchange_id
    
    def register_data_callback(self, data_type: str, callback: Callable) -> None:
        """Register callback for data updates.
        
        Args:
            data_type: Type of data (ticker, kline, etc.)
            callback: Callback function to call on updates
        """
        if data_type not in self.data_callbacks:
            self.data_callbacks[data_type] = []
        self.data_callbacks[data_type].append(callback)
    
    async def _notify_callbacks(self, data_type: str, data: Dict[str, Any]) -> None:
        """Notify registered callbacks of data updates.
        
        Args:
            data_type: Type of data that was updated
            data: Updated data
        """
        if data_type in self.data_callbacks:
            for callback in self.data_callbacks[data_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data_type, data)
                    else:
                        callback(data_type, data)
                except Exception as e:
                    self.logger.error(f"Error in data callback for {data_type}: {str(e)}")
    
    def initialize_websocket(self) -> None:
        """Initialize WebSocket connection for real-time data."""
        try:
            # Skip if no symbol is provided
            if not self.symbol_str:
                self.logger.info("Skipping WebSocket initialization: No symbol provided")
                return
            
            # Import WebSocketManager here to avoid circular imports
            from src.core.websocket.websocket_manager import WebSocketManager
            
            # Initialize WebSocket Manager with the same config
            self.ws_manager = WebSocketManager(self.config)
            
            # Register callback for WebSocket messages
            self.ws_manager.register_message_callback(self._process_websocket_message)
            
            # Create the list of symbols for the WebSocket manager to track
            symbols = [self.symbol_str]
            
            # Initialize asynchronously using create_task
            # Note: This will be executed when the event loop is running
            asyncio.create_task(self.ws_manager.initialize(symbols))
            
            self.logger.info(f"WebSocket integration initialized for {self.symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.ws_manager = None
            
            # Update health status if available
            if self.health_monitor:
                self.health_monitor._create_alert(
                    level="warning",
                    source=f"websocket:{self.exchange_id}",
                    message=f"Failed to initialize WebSocket: {str(e)}"
                )
    
    async def _process_websocket_message(self, symbol: str, topic: str, message: Dict[str, Any]) -> None:
        """Process WebSocket message and update internal data.
        
        Args:
            symbol: Trading pair symbol
            topic: Message topic
            message: WebSocket message data
        """
        try:
            # Start performance tracking
            operation = None
            if self.metrics_manager:
                operation = self.metrics_manager.start_operation(f"process_ws_message_{topic}")
            
            # Check if the message is for the symbol we're monitoring
            if symbol != self.symbol_str:
                if operation and self.metrics_manager:
                    self.metrics_manager.end_operation(operation)
                return
            
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
            if operation and self.metrics_manager:
                self.metrics_manager.end_operation(operation)
                
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message for {topic}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # End operation if it was started
            if operation and self.metrics_manager:
                self.metrics_manager.end_operation(operation, success=False)
    
    async def _process_ticker_update(self, message: Dict[str, Any]) -> None:
        """Process ticker update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
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
            
            # Notify callbacks
            await self._notify_callbacks('ticker', ticker)
            
            # Log update
            self.logger.debug(f"Updated ticker data from WebSocket: Last price: {ticker['last']}")
            
        except Exception as e:
            self.logger.error(f"Error processing ticker update: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def _process_kline_update(self, message: Dict[str, Any]) -> None:
        """Process OHLCV update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract kline data
            kline_data = data.get('data', [])
            if not kline_data:
                return
            
            # Get interval from topic
            topic = message.get('topic', '')
            interval = '1'  # Default to 1 minute
            if '.' in topic:
                parts = topic.split('.')
                if len(parts) > 1:
                    interval = parts[1]  # Extract interval from topic
            
            # Map to standard timeframe key
            timeframe_map = {
                '1': 'base',
                '5': 'ltf',
                '30': 'mtf',
                '60': 'mtf',
                '240': 'htf',
                '1D': 'htf'
            }
            
            tf_key = timeframe_map.get(interval, 'base')
            
            # Format candle data
            candles = []
            for candle in kline_data:
                formatted_candle = {
                    'timestamp': int(candle.get('timestamp', 0) or candle.get('start', 0)),
                    'open': float(candle.get('open', 0)),
                    'high': float(candle.get('high', 0)),
                    'low': float(candle.get('low', 0)),
                    'close': float(candle.get('close', 0)),
                    'volume': float(candle.get('volume', 0))
                }
                candles.append(formatted_candle)
            
            # Create DataFrame
            if candles:
                df = pd.DataFrame(candles)
                if 'timestamp' in df.columns:
                    df.set_index('timestamp', inplace=True)
                    df.index = pd.to_datetime(df.index, unit='ms')
                
                # Update internal state
                if tf_key not in self.ws_data['kline']:
                    self.ws_data['kline'][tf_key] = df
                else:
                    # Merge with existing data
                    existing_df = self.ws_data['kline'][tf_key]
                    merged_df = pd.concat([existing_df, df])
                    
                    # Remove duplicates
                    merged_df = merged_df[~merged_df.index.duplicated(keep='last')]
                    
                    # Sort by index
                    merged_df.sort_index(inplace=True)
                    
                    # Keep only the latest candles (max 1000)
                    if len(merged_df) > 1000:
                        merged_df = merged_df.tail(1000)
                    
                    self.ws_data['kline'][tf_key] = merged_df
                
                self.ws_data['last_update_time']['kline'] = timestamp
                
                # Notify callbacks
                await self._notify_callbacks('kline', {tf_key: df})
                
                # Log update
                self.logger.debug(f"Updated {tf_key} OHLCV data from WebSocket: {len(candles)} candles")
                
        except Exception as e:
            self.logger.error(f"Error processing kline update: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def _process_orderbook_update(self, message: Dict[str, Any]) -> None:
        """Process orderbook update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract orderbook data
            orderbook_data = data.get('data', {})
            if not orderbook_data:
                return
            
            # Format orderbook data
            orderbook = {
                'symbol': self.symbol,
                'timestamp': int(orderbook_data.get('timestamp', timestamp)),
                'bids': orderbook_data.get('bids', []),
                'asks': orderbook_data.get('asks', [])
            }
            
            # Sort bids (desc) and asks (asc)
            if orderbook['bids']:
                orderbook['bids'] = sorted(orderbook['bids'], key=lambda x: float(x[0]), reverse=True)
            if orderbook['asks']:
                orderbook['asks'] = sorted(orderbook['asks'], key=lambda x: float(x[0]))
            
            # Update internal state
            self.ws_data['orderbook'] = orderbook
            self.ws_data['last_update_time']['orderbook'] = timestamp
            
            # Notify callbacks
            await self._notify_callbacks('orderbook', orderbook)
            
            # Log update
            self.logger.debug(f"Updated orderbook from WebSocket: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook update: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def _process_trade_update(self, message: Dict[str, Any]) -> None:
        """Process trade update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Extract trade data
            trade_data = data.get('data', [])
            if not trade_data:
                return
            
            # Format trade data
            trades = []
            for trade in trade_data:
                formatted_trade = {
                    'id': trade.get('tradeId', str(timestamp) + str(len(self.ws_data['trades']))),
                    'timestamp': int(trade.get('timestamp', timestamp)),
                    'price': float(trade.get('price', 0)),
                    'amount': float(trade.get('size', 0)),
                    'side': trade.get('side', 'unknown').lower(),
                    'symbol': self.symbol
                }
                trades.append(formatted_trade)
            
            # Update internal state - keep only most recent 1000 trades
            self.ws_data['trades'] = (trades + self.ws_data['trades'])[:1000]
            self.ws_data['last_update_time']['trades'] = timestamp
            
            # Notify callbacks
            await self._notify_callbacks('trades', trades)
            
            # Log update
            self.logger.debug(f"Added {len(trades)} new trades from WebSocket. Total: {len(self.ws_data['trades'])}")
            
        except Exception as e:
            self.logger.error(f"Error processing trade update: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def _process_liquidation_update(self, message: Dict[str, Any]) -> None:
        """Process liquidation update from WebSocket.
        
        Args:
            message: WebSocket message data
        """
        try:
            data = message.get('data', {})
            timestamp = message.get('timestamp', self.timestamp_utility.get_utc_timestamp())
            
            # Enhanced debug logging for incoming message
            self.logger.debug(f"RECEIVED LIQUIDATION MSG: {json.dumps(message, default=str)[:200]}...")
            
            # Extract liquidation data
            liquidation_data = data.get('data', {})
            if not liquidation_data:
                self.logger.warning("Empty liquidation data received")
                return
            
            # Format liquidation data
            liquidation = {
                'symbol': self.symbol,
                'timestamp': int(liquidation_data.get('timestamp', timestamp)),
                'price': float(liquidation_data.get('price', 0)),
                'size': float(liquidation_data.get('size', 0)),
                'side': liquidation_data.get('side', 'unknown').lower(),
                'source': 'websocket'
            }
            
            # Log liquidation event
            self.logger.warning(f"Liquidation detected: {liquidation['side']} {liquidation['size']} {self.symbol} @ {liquidation['price']}")
            
            # Update internal state
            self.ws_data['liquidations'] = (self.ws_data['liquidations'] + [liquidation])[-100:]  # Keep last 100
            self.ws_data['last_update_time']['liquidations'] = timestamp
            
            # Notify callbacks
            await self._notify_callbacks('liquidations', liquidation)
            
            # If health monitor is available, create alert
            if self.health_monitor:
                self.health_monitor._create_alert(
                    level="info",
                    source=f"liquidation:{self.exchange_id}:{self.symbol_str}",
                    message=f"Liquidation: {liquidation['side']} {liquidation['size']} {self.symbol} @ {liquidation['price']}"
                )
            
        except Exception as e:
            self.logger.error(f"Error processing liquidation update: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def close(self) -> None:
        """Close WebSocket connections and clean up resources."""
        try:
            self.logger.info(f"Closing WebSocket processor for {self.symbol}")
            
            # Close WebSocket connection if available
            if self.ws_manager:
                await self.ws_manager.close()
                self.logger.info("WebSocket connection closed")
            
        except Exception as e:
            self.logger.error(f"Error closing WebSocket processor: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    def get_websocket_status(self) -> Dict[str, Any]:
        """Get current WebSocket status."""
        if self.ws_manager:
            status = self.ws_manager.get_status()
            # Add data freshness
            status['data_freshness'] = {
                data_type: time.time() - timestamp/1000 if timestamp > 0 else float('inf')
                for data_type, timestamp in self.ws_data['last_update_time'].items()
            }
            return status
        else:
            return {
                'connected': False,
                'enabled': self.websocket_config.get('enabled', False)
            }
    
    def get_real_time_data(self, data_type: Optional[str] = None) -> Dict[str, Any]:
        """Get real-time data from WebSocket.
        
        Args:
            data_type: Specific data type to retrieve, or None for all
            
        Returns:
            Real-time data dictionary
        """
        if data_type:
            return self.ws_data.get(data_type, {})
        return self.ws_data.copy()
    
    def is_data_fresh(self, data_type: str, max_age_seconds: float = 30.0) -> bool:
        """Check if data is fresh within the specified age.
        
        Args:
            data_type: Type of data to check
            max_age_seconds: Maximum age in seconds
            
        Returns:
            True if data is fresh, False otherwise
        """
        last_update = self.ws_data['last_update_time'].get(data_type, 0)
        if last_update == 0:
            return False
        
        current_time = self.timestamp_utility.get_utc_timestamp()
        age_seconds = (current_time - last_update) / 1000
        return age_seconds <= max_age_seconds 