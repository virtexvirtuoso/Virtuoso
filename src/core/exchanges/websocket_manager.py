import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, List, Any, Optional
import traceback
from collections import defaultdict, Counter
from src.utils.task_tracker import create_tracked_task

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

        # Store background tasks
        self.tasks = {}
        
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
            task = create_tracked_task(self._process_symbol_messages(symbol), name=f"ws_messages_{symbol}")
            self.tasks[symbol] = task
        
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
        """Create a WebSocket connection and subscribe to topics with enhanced error handling

        Args:
            topics: List of topics to subscribe to
            connection_id: Unique identifier for this connection

        Returns:
            Dict containing connection information or None if connection failed
        """
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            session = None
            ws = None

            try:
                self.logger.info(f"Attempting WebSocket connection {connection_id} (attempt {attempt + 1}/{max_retries})")

                # Validate network connectivity first
                if not await self._validate_network_connectivity():
                    self.logger.warning(f"Network connectivity check failed for connection {connection_id}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        return None

                # Create session with proper timeout and SSL settings
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                connector = aiohttp.TCPConnector(
                    ssl=True,
                    limit=100,
                    limit_per_host=10,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )

                session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    headers={'User-Agent': 'VirtuosoTrading/1.0'}
                )

                # Connect to Bybit WebSocket with proper error handling
                try:
                    ws = await session.ws_connect(
                        self.ws_url,
                        heartbeat=30,
                        compress=0,
                        max_msg_size=1024*1024,  # 1MB max message size
                        receive_timeout=5.0
                    )

                    self.logger.info(f"WebSocket connection established for {connection_id}")

                except aiohttp.ClientError as e:
                    self.logger.error(f"WebSocket connection failed for {connection_id}: {str(e)}")
                    if session:
                        await session.close()
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        return None

                # Subscribe to topics with error handling
                subscription_message = {
                    "op": "subscribe",
                    "args": topics
                }

                try:
                    await ws.send_json(subscription_message)
                    self.logger.info(f"Subscription sent for {connection_id}: {len(topics)} topics")

                    # Wait for subscription confirmation
                    try:
                        response = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                        if response.get('success'):
                            self.logger.info(f"Subscription confirmed for {connection_id}")
                        else:
                            self.logger.warning(f"Subscription response for {connection_id}: {response}")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"No subscription confirmation received for {connection_id}")

                except Exception as e:
                    self.logger.error(f"Failed to send subscription for {connection_id}: {str(e)}")
                    if ws:
                        await ws.close()
                    if session:
                        await session.close()
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        return None

                # Start message handler for this connection
                handler_task = create_tracked_task(
                    self._handle_messages(ws, topics, connection_id, session, name="auto_tracked_task"),
                    name=f"ws_handler_{connection_id}"
                )

                # Store connection info
                connection_info = {
                    "ws": ws,
                    "session": session,
                    "topics": topics,
                    "connection_id": connection_id,
                    "handler_task": handler_task,
                    "created_at": time.time(),
                    "last_ping": time.time(),
                    "status": "connected"
                }

                self.logger.info(f"✅ Connection {connection_id} established successfully with {len(topics)} topics")
                return connection_info

            except Exception as e:
                self.logger.error(f"Unexpected error creating connection {connection_id}: {str(e)}")

                # Cleanup on error
                if ws and not ws.closed:
                    try:
                        await ws.close()
                    except:
                        pass

                if session and not session.closed:
                    try:
                        await session.close()
                    except:
                        pass

                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying connection {connection_id} in {retry_delay * (2 ** attempt)} seconds...")
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    self.logger.error(f"❌ Failed to establish connection {connection_id} after {max_retries} attempts")

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
            reconnect_task = create_tracked_task(
                self._reconnect(topics, connection_id, session),
                name=f"reconnect_{connection_id}"
            )
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
    

    async def _recover_failed_connections(self):
        """Recover failed WebSocket connections."""
        try:
            failed_connections = []

            # Check all connections for health
            for conn_id, conn_info in list(self.connections.items()):
                ws = conn_info.get('ws')
                if not ws or ws.closed:
                    self.logger.warning(f"Connection {conn_id} is closed, marking for recovery")
                    failed_connections.append((conn_id, conn_info.get('topics', [])))

                    # Clean up the failed connection
                    await self._cleanup_connection(conn_id)

            # Attempt to recover failed connections
            for conn_id, topics in failed_connections:
                self.logger.info(f"Attempting to recover connection {conn_id}")
                new_conn = await self._create_connection(topics, conn_id)
                if new_conn:
                    self.connections[conn_id] = new_conn
                    self.logger.info(f"✅ Successfully recovered connection {conn_id}")
                else:
                    self.logger.error(f"❌ Failed to recover connection {conn_id}")

            # Update connection status
            self.status['connected'] = len(self.connections) > 0
            self.status['active_connections'] = len(self.connections)

        except Exception as e:
            self.logger.error(f"Error during connection recovery: {str(e)}")

    async def _cleanup_connection(self, connection_id: str):
        """Clean up a failed connection."""
        try:
            if connection_id in self.connections:
                conn_info = self.connections[connection_id]

                # Cancel handler task
                handler_task = conn_info.get('handler_task')
                if handler_task and not handler_task.done():
                    handler_task.cancel()
                    try:
                        await handler_task
                    except asyncio.CancelledError:
                        pass

                # Close WebSocket
                ws = conn_info.get('ws')
                if ws and not ws.closed:
                    await ws.close()

                # Close session
                session = conn_info.get('session')
                if session and not session.closed:
                    await session.close()

                # Remove from connections
                del self.connections[connection_id]

                self.logger.debug(f"Cleaned up connection {connection_id}")

        except Exception as e:
            self.logger.error(f"Error cleaning up connection {connection_id}: {str(e)}")


    async def _validate_network_connectivity(self) -> bool:
        """Validate network connectivity to WebSocket endpoint.

        Returns:
            bool: True if network connectivity is available, False otherwise
        """
        try:
            # Simple connectivity test using aiohttp
            timeout = aiohttp.ClientTimeout(total=5, connect=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test HTTPS connectivity to Bybit
                test_url = "https://api.bybit.com/v5/market/time" if not self.is_testnet else "https://api-testnet.bybit.com/v5/market/time"

                async with session.get(test_url) as response:
                    if response.status == 200:
                        self.logger.debug("Network connectivity validation passed")
                        return True
                    else:
                        self.logger.warning(f"Network connectivity test returned status: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"Network connectivity validation failed: {str(e)}")
            return False

    def get_status(self):
        """Get current WebSocket connection status with enhanced monitoring

        Returns:
            Dict containing comprehensive status information
        """
        current_time = time.time()

        # Count healthy connections
        healthy_connections = 0
        connection_details = {}

        for conn_id, conn_info in self.connections.items():
            ws = conn_info.get('ws')
            is_healthy = ws and not ws.closed

            if is_healthy:
                healthy_connections += 1

            connection_details[conn_id] = {
                'status': 'connected' if is_healthy else 'disconnected',
                'topics_count': len(conn_info.get('topics', [])),
                'created_at': conn_info.get('created_at', 0),
                'age_seconds': current_time - conn_info.get('created_at', current_time),
                'last_ping': conn_info.get('last_ping', 0)
            }

        # Update main status
        self.status['connected'] = healthy_connections > 0
        self.status['healthy_connections'] = healthy_connections
        self.status['total_connections'] = len(self.connections)
        self.status['active_connections'] = healthy_connections

        # Calculate time since last message
        if self.status['last_message_time'] > 0:
            self.status['seconds_since_last_message'] = current_time - self.status['last_message_time']
        else:
            self.status['seconds_since_last_message'] = -1

        # Add connection health details
        self.status['connection_details'] = connection_details
        self.status['last_status_check'] = current_time

        # Determine overall health
        if healthy_connections == 0:
            self.status['health'] = 'disconnected'
        elif healthy_connections < len(self.connections):
            self.status['health'] = 'degraded'
        else:
            self.status['health'] = 'healthy'

        # Return copy of status with additional diagnostics
        status_copy = self.status.copy()
        status_copy['diagnostics'] = {
            'ws_url': self.ws_url,
            'is_testnet': self.is_testnet,
            'total_subscribed_topics': sum(len(topics) for topics in self.topics.values()),
            'unique_symbols': len(self.topics)
        }

        return status_copy

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