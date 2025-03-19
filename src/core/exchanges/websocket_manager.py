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
        self.config = config
        self.connections = {}
        self.message_queues = {}
        self.subscriptions = {}
        self.logger = logging.getLogger(__name__)
        self.is_testnet = config.get('exchanges', {}).get('bybit', {}).get('testnet', False)
        
        # WebSocket endpoints
        if self.is_testnet:
            self.ws_url = "wss://stream-testnet.bybit.com/v5/public/linear"
        else:
            self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        
        # Track connection status
        self.status = {
            'connected': False,
            'last_message_time': 0,
            'subscribed_topics': set(),
            'errors': []
        }
        
        # Get WebSocket logging configuration
        ws_logging_config = config.get('market_data', {}).get('websocket_logging', {})
        
        # For rate-limiting log messages
        self._message_counts = defaultdict(Counter)
        self._last_log_time = defaultdict(float)
        self._log_interval = ws_logging_config.get('summary_interval', 60)  
        self._log_message_threshold = ws_logging_config.get('message_threshold', 1)
        self._verbose_logging = ws_logging_config.get('verbose', False)
        self._include_message_content = ws_logging_config.get('include_message_content', False)
        
        # Log the WebSocket logging configuration at INFO level
        self.logger.info(f"WebSocket logging config: verbose={self._verbose_logging}, "
                        f"summary_interval={self._log_interval}s, message_threshold={self._log_message_threshold}")
    
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
            self.subscriptions[symbol] = [
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
        for symbol_topics in self.subscriptions.values():
            all_topics.extend(symbol_topics)
        
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
        self.status['subscribed_topics'] = set(all_topics)
        
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
            topics: List of subscribed topics
            connection_id: Unique identifier for this connection
            session: aiohttp session
        """
        try:
            logger.info(f"Starting message handler for connection {connection_id}")
            
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        
                        # Update last message time
                        self.status['last_message_time'] = time.time()
                        self.connections[connection_id]['last_message_time'] = time.time()
                        
                        # Handle subscription responses
                        if "op" in data and data["op"] == "subscribe":
                            logger.debug(f"Subscription response: {data}")
                            continue
                        
                        # Handle ping/pong
                        if "op" in data and data["op"] == "ping":
                            await ws.send_json({"op": "pong"})
                            continue
                        
                        # Process message based on topic
                        if "topic" in data:
                            topic = data["topic"]
                            # Extract symbol from topic (format varies by channel)
                            
                            # Handle different topic formats
                            if "." in topic:
                                parts = topic.split(".")
                                symbol = parts[-1]  # Last part is usually the symbol
                                
                                # For kline topics, symbol is the last part after removing interval
                                if "kline" in topic:
                                    symbol = parts[-1]
                            else:
                                # Default case
                                symbol = data.get("data", {}).get("symbol")
                            
                            # Add message to symbol's queue if it exists
                            if symbol in self.message_queues:
                                await self.message_queues[symbol].put({
                                    "connection_id": connection_id,
                                    "topic": topic,
                                    "data": data,
                                    "timestamp": int(time.time() * 1000)
                                })
                                
                                # Rate-limited logging with counters
                                self._message_counts[symbol][topic] += 1
                                
                                # Only log the first message for each topic if verbose logging is enabled
                                if self._verbose_logging and self._message_counts[symbol][topic] <= self._log_message_threshold:
                                    if self._include_message_content:
                                        # Log with message content (more verbose)
                                        msg_sample = str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
                                        logger.debug(f"Received {topic} for {symbol}: {msg_sample}")
                                    else:
                                        # Log just the topic (less verbose)
                                        logger.debug(f"Queued message for {symbol}: {topic}")
                                
                                # Periodically log summary
                                now = time.time()
                                if now - self._last_log_time[symbol] >= self._log_interval:
                                    # Log summary of message counts - be more concise
                                    msg_counts = self._message_counts[symbol]
                                    if msg_counts:
                                        count_sum = sum(msg_counts.values())
                                        topic_count = len(msg_counts)
                                        
                                        # Calculate message rate (messages per second)
                                        time_diff = now - self._last_log_time[symbol]
                                        if time_diff > 0:
                                            msg_rate = count_sum / time_diff
                                        else:
                                            msg_rate = 0
                                        
                                        # Log at INFO level for better visibility with reduced frequency
                                        topic_counts = ', '.join([f"{topic.split('.')[0]}:{count}" for topic, count in msg_counts.items() if count > 0])
                                        logger.info(f"WebSocket ({symbol}): {count_sum} msgs, {msg_rate:.1f} msgs/sec ({topic_counts})")
                                        
                                        # Reset counters
                                        self._message_counts[symbol] = Counter()
                                        self._last_log_time[symbol] = now
                            else:
                                logger.warning(f"Received message for unknown symbol: {symbol}")
                        else:
                            logger.warning(f"Received message without topic: {data}")
                    
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse WebSocket message: {msg.data}")
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {str(e)}")
                        logger.debug(traceback.format_exc())
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection error: {ws.exception()}")
                    self.status['errors'].append({
                        'time': time.time(),
                        'error': str(ws.exception()),
                        'connection_id': connection_id
                    })
                    break
                
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning(f"WebSocket connection closed: {connection_id}")
                    break
        
        except Exception as e:
            logger.error(f"Error in WebSocket message handler: {str(e)}")
            logger.debug(traceback.format_exc())
        finally:
            # Mark connection as closed
            if connection_id in self.connections:
                self.connections[connection_id]['connected'] = False
            
            # Attempt to reconnect
            asyncio.create_task(self._reconnect(topics, connection_id, session))
    
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
                await session.close()
                
            # Remove connection from active connections
            if connection_id in self.connections:
                del self.connections[connection_id]
            
            # Reconnect with exponential backoff
            backoff = 1
            max_backoff = 60
            max_retries = 10
            retries = 0
            
            while backoff <= max_backoff and retries < max_retries:
                logger.info(f"Attempting to reconnect {connection_id} in {backoff}s...")
                await asyncio.sleep(backoff)
                retries += 1
                
                try:
                    # Create new connection
                    conn_info = await self._create_connection(topics, connection_id)
                    if conn_info:
                        self.connections[connection_id] = conn_info
                        logger.info(f"Successfully reconnected {connection_id}")
                        return
                    else:
                        logger.error(f"Failed to reconnect {connection_id}")
                except Exception as e:
                    logger.error(f"Error during reconnect attempt: {str(e)}")
                
                # Increase backoff time
                backoff = min(backoff * 2, max_backoff)
            
            logger.error(f"Failed to reconnect {connection_id} after {retries} attempts")
            
            # Update status
            self.status['connected'] = len(self.connections) > 0
        
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
        logger.info("Closing WebSocket connections")
        
        # Cancel all message processing tasks
        tasks = asyncio.all_tasks()
        for task in tasks:
            if task.get_name().startswith("_process_symbol_messages"):
                task.cancel()
        
        # Close all WebSocket connections
        for conn_id, conn in list(self.connections.items()):
            try:
                if "ws" in conn and not conn["ws"].closed:
                    await conn["ws"].close()
                if "session" in conn and not conn["session"].closed:
                    await conn["session"].close()
                logger.info(f"Closed connection {conn_id}")
            except Exception as e:
                logger.error(f"Error closing connection {conn_id}: {str(e)}")
        
        # Clear connections
        self.connections = {}
        
        # Update status
        self.status['connected'] = False
        logger.info("All WebSocket connections closed")
    
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