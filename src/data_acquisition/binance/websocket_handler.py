from src.utils.task_tracker import create_tracked_task
"""
Binance WebSocket Handler

Implements WebSocket connections for real-time Binance market data.
Provides comprehensive streaming capabilities for market analysis.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime
import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

class BinanceWebSocketHandler:
    """
    WebSocket handler for Binance real-time data streams.
    
    Features:
    - Multiple stream subscriptions
    - Automatic reconnection
    - Connection health monitoring
    - Rate limiting compliance
    - Error handling and recovery
    """
    
    def __init__(self, testnet: bool = False):
        """
        Initialize WebSocket handler.
        
        Args:
            testnet: Whether to use testnet endpoints
        """
        self.testnet = testnet
        self.base_url = (
            'wss://testnet.binance.vision/ws' if testnet 
            else 'wss://stream.binance.com:9443/ws'
        )
        
        # Connection management
        self.websocket = None
        self.connected = False
        self.running = False
        
        # Subscription management
        self.subscriptions = set()
        self.callbacks = {}
        self.stream_handlers = {}
        
        # Connection settings
        self.ping_interval = 30  # Binance requires pings every 60s, we'll do 30s
        self.reconnect_attempts = 3
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        
        # Health monitoring
        self.last_ping = 0
        self.last_pong = 0
        self.message_count = 0
        self.error_count = 0
        
        # Session management
        self.session = None
        
        logger.info(f"Initialized Binance WebSocket handler (testnet: {testnet})")
    
    async def connect(self) -> bool:
        """
        Connect to Binance WebSocket stream.
        
        Returns:
            bool: True if connection successful
        """
        try:
            if self.connected:
                logger.info("WebSocket already connected")
                return True
            
            logger.info(f"Connecting to Binance WebSocket: {self.base_url}")
            
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                self.base_url,
                ping_interval=self.ping_interval,
                ping_timeout=20,
                close_timeout=10,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                compression=None  # Disable compression for better performance
            )
            
            self.connected = True
            self.running = True
            self.last_ping = time.time()
            self.error_count = 0
            
            # Start message handler
            create_tracked_task(self._message_handler(), name="auto_tracked_task")
            
            # Start health monitor
            create_tracked_task(self._health_monitor(), name="auto_tracked_task")
            
            logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            self.connected = False
            return False
    
    async def subscribe(self, streams: List[str], callback: Callable = None) -> bool:
        """
        Subscribe to WebSocket streams.
        
        Args:
            streams: List of stream names to subscribe to
            callback: Optional callback function for handling messages
            
        Returns:
            bool: True if subscription successful
        """
        try:
            if not self.connected:
                logger.error("WebSocket not connected")
                return False
            
            # Build subscription message
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": int(time.time())
            }
            
            # Send subscription request
            await self.websocket.send(json.dumps(subscribe_msg))
            
            # Store subscription info
            for stream in streams:
                self.subscriptions.add(stream)
                if callback:
                    self.callbacks[stream] = callback
            
            logger.info(f"Subscribed to {len(streams)} streams")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket subscription failed: {str(e)}")
            return False
    
    async def unsubscribe(self, streams: List[str]) -> bool:
        """
        Unsubscribe from WebSocket streams.
        
        Args:
            streams: List of stream names to unsubscribe from
            
        Returns:
            bool: True if unsubscription successful
        """
        try:
            if not self.connected:
                logger.error("WebSocket not connected")
                return False
            
            # Build unsubscription message
            unsubscribe_msg = {
                "method": "UNSUBSCRIBE",
                "params": streams,
                "id": int(time.time())
            }
            
            # Send unsubscription request
            await self.websocket.send(json.dumps(unsubscribe_msg))
            
            # Remove from tracking
            for stream in streams:
                self.subscriptions.discard(stream)
                self.callbacks.pop(stream, None)
            
            logger.info(f"Unsubscribed from {len(streams)} streams")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket unsubscription failed: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket stream."""
        try:
            logger.info("Disconnecting WebSocket...")
            
            self.running = False
            
            if self.websocket:
                await self.websocket.close()
            
            self.connected = False
            self.subscriptions.clear()
            self.callbacks.clear()
            
            if self.session:
                await self.session.close()
            
            logger.info("WebSocket disconnected successfully")
            
        except Exception as e:
            logger.error(f"WebSocket disconnection error: {str(e)}")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.message_count += 1
                    
                    # Handle different message types
                    if 'stream' in data and 'data' in data:
                        # Stream data message
                        await self._handle_stream_data(data)
                    elif 'result' in data:
                        # Subscription response
                        await self._handle_subscription_response(data)
                    elif 'error' in data:
                        # Error message
                        await self._handle_error_message(data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {str(e)}")
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {str(e)}")
                    self.error_count += 1
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            await self._handle_disconnection()
        except WebSocketException as e:
            logger.error(f"WebSocket error: {str(e)}")
            await self._handle_disconnection()
        except Exception as e:
            logger.error(f"Unexpected error in message handler: {str(e)}")
            await self._handle_disconnection()
    
    async def _handle_stream_data(self, message: Dict[str, Any]):
        """Handle stream data messages."""
        try:
            stream = message.get('stream')
            data = message.get('data')
            
            if not stream or not data:
                return
            
            # Call registered callback if exists
            callback = self.callbacks.get(stream)
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(stream, data)
                    else:
                        callback(stream, data)
                except Exception as e:
                    logger.error(f"Error in stream callback for {stream}: {str(e)}")
            
            # Call specific stream handlers
            stream_type = self._get_stream_type(stream)
            handler = self.stream_handlers.get(stream_type)
            if handler:
                try:
                    await handler(stream, data)
                except Exception as e:
                    logger.error(f"Error in stream handler for {stream_type}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error handling stream data: {str(e)}")
    
    async def _handle_subscription_response(self, message: Dict[str, Any]):
        """Handle subscription response messages."""
        result = message.get('result')
        msg_id = message.get('id')
        
        if result is None:
            logger.info(f"Subscription successful (ID: {msg_id})")
        else:
            logger.warning(f"Subscription response (ID: {msg_id}): {result}")
    
    async def _handle_error_message(self, message: Dict[str, Any]):
        """Handle error messages."""
        error = message.get('error', {})
        error_code = error.get('code')
        error_msg = error.get('msg')
        
        logger.error(f"WebSocket error {error_code}: {error_msg}")
        self.error_count += 1
    
    async def _health_monitor(self):
        """Monitor connection health and handle reconnections."""
        reconnect_count = 0
        
        while self.running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                if not self.connected:
                    # Attempt reconnection
                    if reconnect_count < self.reconnect_attempts:
                        reconnect_count += 1
                        delay = min(self.reconnect_delay * reconnect_count, self.max_reconnect_delay)
                        
                        logger.info(f"Attempting reconnection {reconnect_count}/{self.reconnect_attempts} in {delay}s")
                        await asyncio.sleep(delay)
                        
                        if await self.connect():
                            # Resubscribe to streams
                            if self.subscriptions:
                                await self.subscribe(list(self.subscriptions))
                            reconnect_count = 0
                    else:
                        logger.error("Max reconnection attempts reached")
                        self.running = False
                        break
                
                # Check for excessive errors
                if self.error_count > 10:
                    logger.warning("Excessive errors detected, may need to restart connection")
                    self.error_count = 0
                    
            except Exception as e:
                logger.error(f"Error in health monitor: {str(e)}")
    
    async def _handle_disconnection(self):
        """Handle unexpected disconnections."""
        self.connected = False
        logger.warning("WebSocket disconnected unexpectedly")
    
    def _get_stream_type(self, stream: str) -> str:
        """Extract stream type from stream name."""
        if '@ticker' in stream:
            return 'ticker'
        elif '@trade' in stream:
            return 'trade'
        elif '@depth' in stream:
            return 'orderbook'
        elif '@kline' in stream:
            return 'kline'
        elif '@markPrice' in stream:
            return 'mark_price'
        elif '@forceOrder' in stream:
            return 'liquidation'
        else:
            return 'unknown'
    
    def register_stream_handler(self, stream_type: str, handler: Callable):
        """Register a handler for a specific stream type."""
        self.stream_handlers[stream_type] = handler
        logger.info(f"Registered handler for stream type: {stream_type}")
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        try:
            return (self.connected and 
                    self.websocket and 
                    self.websocket.state.name == 'OPEN' and
                    self.running)
        except AttributeError:
            # Fallback for different websockets library versions
            return (self.connected and 
                    self.websocket and 
                    not getattr(self.websocket, 'closed', True) and
                    self.running)
    
    def get_active_subscriptions(self) -> List[str]:
        """Get list of active subscriptions."""
        return list(self.subscriptions)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            'connected': self.connected,
            'running': self.running,
            'subscriptions': len(self.subscriptions),
            'message_count': self.message_count,
            'error_count': self.error_count,
            'last_ping': self.last_ping,
            'uptime': time.time() - self.last_ping if self.last_ping else 0
        }

# Helper functions for stream names

def get_ticker_stream(symbol: str) -> str:
    """Get ticker stream name for a symbol."""
    return f"{symbol.lower()}@ticker"

def get_trade_stream(symbol: str) -> str:
    """Get trade stream name for a symbol."""
    return f"{symbol.lower()}@trade"

def get_orderbook_stream(symbol: str, levels: int = 20, speed: str = "100ms") -> str:
    """Get order book stream name for a symbol."""
    return f"{symbol.lower()}@depth{levels}@{speed}"

def get_kline_stream(symbol: str, interval: str) -> str:
    """Get kline stream name for a symbol."""
    return f"{symbol.lower()}@kline_{interval}"

def get_mark_price_stream(symbol: str, speed: str = "1s") -> str:
    """Get mark price stream for futures symbols."""
    return f"{symbol.lower()}@markPrice@{speed}"

def get_liquidation_stream(symbol: str) -> str:
    """Get liquidation stream for futures symbols."""
    return f"{symbol.lower()}@forceOrder"

# Advanced usage example

async def advanced_example():
    """Advanced example showing real WebSocket usage."""
    print("🚀 Binance WebSocket Handler - Advanced Implementation")
    print("=" * 60)
    
    # Create handler
    ws_handler = BinanceWebSocketHandler(testnet=False)
    
    # Example data handlers
    async def handle_ticker_data(stream, data):
        symbol = data.get('s')
        price = data.get('c')
        volume = data.get('v')
        print(f"📊 {symbol}: ${price} (24h vol: {volume})")
    
    async def handle_trade_data(stream, data):
        symbol = data.get('s')
        price = data.get('p')
        quantity = data.get('q')
        side = "🟢 BUY" if data.get('m') else "🔴 SELL"
        print(f"💱 {symbol}: {side} {quantity} @ ${price}")
    
    async def handle_orderbook_data(stream, data):
        symbol = stream.split('@')[0].upper()
        bids = data.get('bids', [])
        asks = data.get('asks', [])
        if bids and asks:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = ((best_ask - best_bid) / best_bid) * 100
            print(f"📈 {symbol}: Spread {spread:.3f}% (${best_bid}-${best_ask})")
    
    try:
        # Connect to WebSocket
        connected = await ws_handler.connect()
        if not connected:
            print("❌ Failed to connect")
            return
        
        print("✅ Connected to Binance WebSocket")
        
        # Register stream handlers
        ws_handler.register_stream_handler('ticker', handle_ticker_data)
        ws_handler.register_stream_handler('trade', handle_trade_data)
        ws_handler.register_stream_handler('orderbook', handle_orderbook_data)
        
        # Subscribe to different streams
        ticker_streams = [
            get_ticker_stream('BTCUSDT'),
            get_ticker_stream('ETHUSDT')
        ]
        
        trade_streams = [
            get_trade_stream('BTCUSDT')
        ]
        
        orderbook_streams = [
            get_orderbook_stream('BTCUSDT', levels=5, speed="100ms")
        ]
        
        # Subscribe to all streams
        await ws_handler.subscribe(ticker_streams)
        await ws_handler.subscribe(trade_streams)
        await ws_handler.subscribe(orderbook_streams)
        
        print(f"📡 Subscribed to {len(ws_handler.get_active_subscriptions())} streams")
        print("🔄 Receiving real-time data... (Ctrl+C to stop)")
        
        # Run for a while to see data
        await asyncio.sleep(30)
        
        # Show connection stats
        stats = ws_handler.get_connection_stats()
        print(f"\n📊 Connection Stats:")
        print(f"   Messages received: {stats['message_count']}")
        print(f"   Active subscriptions: {stats['subscriptions']}")
        print(f"   Error count: {stats['error_count']}")
        print(f"   Uptime: {stats['uptime']:.1f}s")
        
    except KeyboardInterrupt:
        print("\n⚠️  Stopping...")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        # Cleanup
        await ws_handler.disconnect()
        print("👋 WebSocket handler closed")

if __name__ == "__main__":
    asyncio.run(advanced_example()) 