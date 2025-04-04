import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, List, Any, Optional
import traceback
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    WebSocketManager for handling Bybit WebSocket connections
    Maintains connections and processes messages for real-time data updates
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize WebSocketManager with configuration
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Store WebSocket connections
        self.connections = {}
        
        # Store message queues for each symbol
        self.message_queues = {}
        
        # Store subscribed topics
        self.topics = {}
        
        # Store connection status
        self.status = {
            'connected': False,
            'last_message_time': 0,
            'seconds_since_last_message': 0,
            'messages_received': 0,
            'errors': 0,
            'active_connections': 0
        }
        
        # Message callback
        self.message_callback = None
        
        # Get WebSocket logging configuration
        ws_logging_config = config.get('market_data', {}).get('websocket_logging', {})
        
        # Configure logging throttling
        self._last_log_time = 0
        self._message_count = 0
        self._log_interval = ws_logging_config.get('summary_interval', 60)
        self._log_message_threshold = ws_logging_config.get('message_threshold', 1)
        self._verbose_logging = ws_logging_config.get('verbose', False)
        self._include_message_content = ws_logging_config.get('include_message_content', False)
        
        # Log the WebSocket logging configuration at INFO level
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"WebSocket logging config: verbose={self._verbose_logging}, "
                         f"include_message_content={self._include_message_content}")
        
        # Store reconnect tasks to ensure they're properly cancelled
        self.reconnect_tasks = set()
        
        # WebSocket endpoints
        self.is_testnet = config.get('exchanges', {}).get('bybit', {}).get('testnet', False)
        
        if self.is_testnet:
            self.ws_url = "wss://stream-testnet.bybit.com/v5/public/linear"
        else:
            self.ws_url = "wss://stream.bybit.com/v5/public/linear"
    
    async def initialize(self, symbols: List[str]) -> None:
        """Initialize WebSocket connections and subscriptions
        
        Args:
            symbols: List of trading pair symbols to subscribe to
        """
        # Create message queues and configure subscriptions for each symbol
        for symbol in symbols:
            # Create message queue for this symbol
            self.message_queues[symbol] = asyncio.Queue()
            
            # Define subscriptions for this symbol
            self.topics[symbol] = [
                f"tickers.{symbol}",          # Ticker updates (includes OI)
                f"kline.1.{symbol}",          # 1-minute candlesticks
                f"orderbook.50.{symbol}",     # Orderbook with 50 levels
                f"publicTrade.{symbol}",      # Trades
                f"liquidation.{symbol}"       # Liquidations
            ]
        
        # Connect to WebSocket and subscribe to channels
        await self._connect_and_subscribe()
        
        # Start processing messages
        for symbol in symbols:
            asyncio.create_task(self._process_symbol_messages(symbol))
        
        logger.info(f"WebSocket manager initialized for {len(symbols)} symbols")
    
    async def _connect_and_subscribe(self) -> None:
        """Connect to WebSocket and subscribe to channels"""
        # Group subscriptions to minimize connections
        # Bybit allows max 10 topics per connection - let's use 8 to be safe
        max_topics_per_connection = 8
        connection_topics = []
        current_topics = []
        
        # Group all subscriptions into batches
        all_topics = []
        for topics in self.topics.values():
            all_topics.extend(topics)
        
        # Create batches of topics
        for topic in all_topics:
            if len(current_topics) >= max_topics_per_connection:
                connection_topics.append(current_topics)
                current_topics = []
            current_topics.append(topic)
        
        if current_topics:
            connection_topics.append(current_topics)
        
        # Create connections for each group
        for i, topics in enumerate(connection_topics):
            connection_id = f"conn_{i}"
            conn_info = await self._create_connection(topics, connection_id)
            if conn_info:
                self.connections[connection_id] = conn_info
                logger.info(f"Established connection {connection_id} with {len(topics)} topics")
            else:
                logger.error(f"Failed to establish connection {connection_id}")
        
        # Update status
        self.status['connected'] = len(self.connections) > 0
        self.status['last_message_time'] = time.time()
        self.status['messages_received'] = 0
        self.status['errors'] = 0
        self.status['active_connections'] = len(self.connections)
        
        # Log status
        if self.status['connected']:
            logger.info(f"Successfully connected to {len(self.connections)} WebSocket endpoints")
        else:
            logger.error("Failed to establish any WebSocket connections")
    
    async def _create_connection(self, topics: List[str], connection_id: str) -> Optional[Dict]:
        """Create a WebSocket connection and subscribe to topics
        
        Args:
            topics: List of topics to subscribe to
            connection_id: Unique identifier for this connection
            
        Returns:
            Dict containing connection information or None if connection failed
        """
        try:
            # Connect to Bybit WebSocket
            session = aiohttp.ClientSession()
            ws = await session.ws_connect(self.ws_url, heartbeat=30)
            
            # Subscribe to topics
            subscription_message = {
                "op": "subscribe",
                "args": topics
            }
            await ws.send_json(subscription_message)
            
            # Log subscription
            logger.info(f"Sent subscription for topics: {topics}")
            
            # Start message handler for this connection
            asyncio.create_task(self._handle_messages(ws, topics, connection_id, session))
            
            return {
                "ws": ws,
                "session": session,
                "topics": topics,
                "id": connection_id,
                "connected_time": time.time(),
                "last_message_time": time.time()
            }
        except Exception as e:
            logger.error(f"Error creating WebSocket connection: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    async def _handle_messages(self, ws, topics, connection_id, session):
        """Handle incoming WebSocket messages
        
        Args:
            ws: WebSocket connection
            topics: Subscribed topics
            connection_id: Connection identifier
            session: aiohttp session
        """
        try:
            async for msg in ws:
                # Track message received time
                self.status['last_message_time'] = time.time()
                self.status['messages_received'] += 1
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Log the message if verbose logging is enabled
                    try:
                        self._log_message(connection_id, msg.data)
                    except AttributeError:
                        # Fallback logging if _log_message isn't available
                        if self._verbose_logging:
                            self.logger.debug(f"WebSocket message received on connection {connection_id}")
                    
                    try:
                        # Parse data
                        data = json.loads(msg.data)
                        
                        # Get topic and symbol
                        topic = data.get('topic', None)
                        if not topic:
                            continue  # Skip messages without a topic (e.g., responses to ping)
                        
                        # Extract symbol from topic (format: "channel.symbol" or "channel.timeframe.symbol")
                        parts = topic.split('.')
                        if len(parts) >= 2:
                            symbol = parts[-1]  # Last part should be the symbol
                        else:
                            continue  # Skip messages with unexpected topic format
                        
                        # Queue message for processing
                        if symbol in self.message_queues:
                            await self.message_queues[symbol].put(data)
                        
                    except json.JSONDecodeError:
                        self.logger.error(f"Invalid JSON in WebSocket message: {msg.data[:200]}...")
                        self.status['errors'] += 1
                    except Exception as e:
                        self.logger.error(f"Error processing WebSocket message: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        self.status['errors'] += 1
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket connection error: {connection_id}")
                    self.status['errors'] += 1
                    break
                
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.warning(f"WebSocket connection closed: {connection_id}")
                    break
        
        except asyncio.CancelledError:
            self.logger.info(f"WebSocket message handler for {connection_id} cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in WebSocket message handler: {str(e)}")
            self.logger.debug(traceback.format_exc())
        finally:
            # Mark connection as closed
            if connection_id in self.connections:
                self.connections[connection_id]['connected'] = False
            
            # Attempt to reconnect
            reconnect_task = asyncio.create_task(self._reconnect(topics, connection_id, session))
            reconnect_task.set_name(f"reconnect_{connection_id}")
            self.reconnect_tasks.add(reconnect_task)
            reconnect_task.add_done_callback(self.reconnect_tasks.discard)
            
    async def _reconnect(self, topics, connection_id, session):
        """Reconnect WebSocket with exponential backoff
        
        Args:
            topics: List of topics to resubscribe to
            connection_id: Connection identifier
            session: aiohttp session to close
        """
        try:
            # Close existing session if it's still open
            if not session.closed:
                try:
                    await session.close()
                except Exception as e:
                    self.logger.warning(f"Error closing session: {str(e)}")
                
            # Remove connection from active connections
            if connection_id in self.connections:
                del self.connections[connection_id]
            
            # Reconnect with exponential backoff
            backoff = 1
            max_backoff = 60
            max_retries = 10
            retries = 0
            
            while backoff <= max_backoff and retries < max_retries:
                try:
                    logger.info(f"Attempting to reconnect {connection_id} in {backoff}s...")
                    await asyncio.sleep(backoff)
                    retries += 1
                    
                    # Check if task was cancelled
                    if asyncio.current_task().cancelled():
                        logger.info(f"Reconnect task for {connection_id} was cancelled")
                        return
                    
                    # Create new connection
                    conn_info = await self._create_connection(topics, connection_id)
                    if conn_info:
                        self.connections[connection_id] = conn_info
                        logger.info(f"Successfully reconnected {connection_id}")
                        return
                    else:
                        logger.error(f"Failed to reconnect {connection_id}")
                except asyncio.CancelledError:
                    logger.info(f"Reconnect task for {connection_id} was cancelled")
                    return
                except Exception as e:
                    logger.error(f"Error during reconnect attempt: {str(e)}")
                
                # Increase backoff time
                backoff = min(backoff * 2, max_backoff)
            
            logger.error(f"Failed to reconnect {connection_id} after {retries} attempts")
            
            # Update status
            self.status['connected'] = len(self.connections) > 0
        
        except asyncio.CancelledError:
            logger.info(f"Reconnect task for {connection_id} was cancelled")
            return
        except Exception as e:
            logger.error(f"Error in reconnect process: {str(e)}")
            
    async def _process_symbol_messages(self, symbol):
        """Process queued messages for a specific symbol
        
        Args:
            symbol: Trading pair symbol
        """
        while True:
            try:
                # Get message queue
                queue = self.message_queues.get(symbol)
                if not queue:
                    logger.error(f"No message queue found for {symbol}")
                    return
                
                # Get message from queue (blocking)
                message = await queue.get()
                
                # Process message based on topic
                topic = message.get("topic", "")
                
                # Emit message to interested subscribers
                if hasattr(self, 'message_callback') and callable(self.message_callback):
                    await self.message_callback(symbol, topic, message)
                
                # Mark task as done
                queue.task_done()
            
            except asyncio.CancelledError:
                logger.info(f"Message processing for {symbol} cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing message for {symbol}: {str(e)}")
                logger.debug(traceback.format_exc())
                # Sleep briefly to avoid CPU spinning on errors
                await asyncio.sleep(0.1)
    
    async def close(self):
        """Close all WebSocket connections and cleanup resources"""
        self.logger.info("Closing WebSocket connections")
        
        # Cancel all message processing tasks
        tasks = asyncio.all_tasks()
        for task in tasks:
            if task.get_name().startswith("_process_symbol_messages"):
                task.cancel()
        
        # Cancel all reconnect tasks first
        for task in list(self.reconnect_tasks):
            task.cancel()
            
        # Wait for reconnect tasks to complete
        if self.reconnect_tasks:
            pending_tasks = list(self.reconnect_tasks)
            self.logger.info(f"Waiting for {len(pending_tasks)} reconnect tasks to complete")
            done, pending = await asyncio.wait(pending_tasks, timeout=5)
            for task in pending:
                task.cancel()
                
        self.reconnect_tasks.clear()
        
        # Close all WebSocket connections
        for conn_id, conn in list(self.connections.items()):
            try:
                if "ws" in conn and not conn["ws"].closed:
                    await conn["ws"].close()
                if "session" in conn and not conn["session"].closed:
                    await conn["session"].close()
                self.logger.info(f"Closed connection {conn_id}")
            except Exception as e:
                self.logger.error(f"Error closing connection {conn_id}: {str(e)}")
        
        # Clear connections
        self.connections = {}
        
        # Update status
        self.status['connected'] = False
        self.logger.info("All WebSocket connections closed")
    
    def register_message_callback(self, callback):
        """Register a callback function to process WebSocket messages
        
        Args:
            callback: Async function to call with (symbol, topic, message) parameters
        """
        self.message_callback = callback
    
    def get_status(self):
        """Get current WebSocket connection status
        
        Returns:
            Dict containing status information
        """
        # Update connected status
        self.status['connected'] = len(self.connections) > 0
        
        # Calculate time since last message
        if self.status['last_message_time'] > 0:
            self.status['seconds_since_last_message'] = time.time() - self.status['last_message_time']
        
        # Count active connections
        self.status['active_connections'] = len(self.connections)
        
        # Return copy of status
        return self.status.copy()

    def _extract_symbol(self, data):
        """Extract symbol from WebSocket message
        
        Args:
            data: WebSocket message
            
        Returns:
            Symbol extracted from the message or None if no symbol found
        """
        try:
            # Check for topic field first
            if "topic" in data:
                topic = data["topic"]
                
                # Common format: "channel.symbol" or "channel.timeframe.symbol"
                if "." in topic:
                    parts = topic.split(".")
                    
                    # Handle different topic formats based on channel
                    channel = parts[0]
                    
                    if channel in ["tickers", "orderbook", "publicTrade", "liquidation"]:
                        # Format: "channel.symbol" (e.g., "tickers.BTCUSDT")
                        return parts[1]
                    elif channel == "kline":
                        # Format: "kline.timeframe.symbol" (e.g., "kline.1.BTCUSDT")
                        return parts[2]
                
            # Try to extract from data field
            if "data" in data and isinstance(data["data"], dict):
                if "symbol" in data["data"]:
                    return data["data"]["symbol"]
            
            # Special case for specific message types
            if "ret_msg" in data and data.get("ret_msg") == "pong":
                return None  # Ignore pong messages
            
            return None
        except Exception as e:
            self.logger.error(f"Error extracting symbol from message: {str(e)}")
            return None
            
    def _log_message(self, connection_id, message_data):
        """Log a WebSocket message based on verbose settings
        
        Args:
            connection_id: Connection identifier
            message_data: Raw message data
        """
        try:
            # Log message count
            now = time.time()
            self._message_count += 1
            
            # Log summary periodically
            if now - self._last_log_time > self._log_interval:
                self.logger.info(f"WebSocket messages received: {self._message_count} in the last {self._log_interval} seconds")
                self._message_count = 0
                self._last_log_time = now
                
            # Log individual messages if verbose is enabled
            if self._verbose_logging:
                if self._include_message_content:
                    try:
                        # Try to parse as JSON for pretty logging
                        data = json.loads(message_data)
                        self.logger.debug(f"WebSocket message on {connection_id}: {json.dumps(data)[:200]}...")
                    except:
                        # Fall back to raw message if not JSON
                        self.logger.debug(f"WebSocket message on {connection_id}: {str(message_data)[:200]}...")
                else:
                    self.logger.debug(f"WebSocket message received on connection {connection_id}")
        except Exception as e:
            # Don't let logging errors interrupt the message handler
            self.logger.error(f"Error logging WebSocket message: {str(e)}")
    
    def _init_ws_state(self):
        """Initialize websocket state"""
        self._ws_subscriptions = {}
        self._ws_callbacks = {}
        self._ws_reconnecting = False
        self._ws_connected = asyncio.Event()
        self._ws_tasks = set() 