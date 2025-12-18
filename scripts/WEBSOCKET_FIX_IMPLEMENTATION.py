"""
WebSocket Fix Implementation - Ready-to-Use Code

This file contains the exact code changes needed to fix the
"Cannot write to closing transport" issue in Bybit liquidation subscriptions.

Choose ONE of the solutions below based on your requirements.
"""

# ============================================================================
# SOLUTION 1: USE EXISTING WEBSOCKET (RECOMMENDED - MINIMAL RISK)
# ============================================================================
# This reuses the working WebSocket infrastructure already in BybitExchange

async def subscribe_liquidations(self, symbols: List[str]) -> bool:
    """
    Subscribe to liquidation feed using the main WebSocket infrastructure.

    REPLACE the existing subscribe_liquidations() method (line ~1429) with this.
    """
    try:
        # Ensure main WebSocket is initialized and connected
        if not self.ws or not self.ws_connected:
            self.logger.info("Initializing main WebSocket for liquidations...")

            # Use the WORKING _initialize_ws_connection() method
            # This starts the message handler and keepalive loops
            if not await self._initialize_ws_connection():
                self.logger.error("Failed to initialize WebSocket")
                return False

            self.logger.info("✅ Main WebSocket initialized successfully")

        # Verify connection is actually ready
        if not self.ws:
            self.logger.error("WebSocket object is None after initialization")
            return False

        # Format liquidation channels (Bybit format)
        channels = [f"allLiquidation.{symbol}" for symbol in symbols]

        self.logger.info(f"Sending subscription for {len(channels)} liquidation channels...")

        # Send subscription via the WORKING WebSocket
        # This uses the same ws.send_json() that works for other subscriptions
        msg = {
            "op": "subscribe",
            "args": channels
        }
        await self.ws.send_json(msg)

        self.logger.info(f"✅ Liquidation subscription sent: {channels}")

        # Store subscribed symbols for reconnection handling
        if not hasattr(self, '_liquidation_subscriptions'):
            self._liquidation_subscriptions = set()
        self._liquidation_subscriptions.update(symbols)

        return True

    except Exception as e:
        self.logger.error(f"Liquidation subscription failed: {e}", exc_info=True)
        return False


# Then ADD this to the existing handle_websocket_message() method
# to route liquidation messages to the handler:

async def handle_websocket_message(self, data: str) -> None:
    """
    Handle incoming WebSocket messages.

    ADD the liquidation routing to the EXISTING method (around line 1350).
    """
    try:
        message = json.loads(data)
        topic = message.get('topic', '')

        # ... KEEP ALL EXISTING CODE HERE ...

        # ✅ ADD THIS SECTION: Route liquidation messages
        if topic.startswith('allLiquidation.'):
            self.logger.debug(f"Routing liquidation message for: {topic}")
            await self._handle_liquidation_message(message)
            return

        # ... REST OF EXISTING CODE ...

    except json.JSONDecodeError as e:
        self.logger.error(f"Failed to decode WebSocket message: {str(e)}")


# ============================================================================
# SOLUTION 2: FIX THE BYBITWEBSOCKET CLASS (IF YOU MUST KEEP IT)
# ============================================================================
# This adds the missing message processing loops to the simplified class

class BybitWebSocket:
    """
    WebSocket client for Bybit exchange with proper lifecycle management.

    REPLACE the entire BybitWebSocket class (lines 5919-6010) with this version.
    """

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.ws = None
        self.session = None
        self.connected = False
        self._message_handlers = {}

        # ✅ NEW: Add lifecycle management
        self._running = False
        self._tasks = []

    async def connect(self) -> bool:
        """Connect to WebSocket and start processing loops."""
        try:
            if self.connected:
                return True

            # Get WebSocket URL from config
            ws_config = self.config.get('websocket', {})
            if self.config.get("data_unavailable", False):
                ws_url = ws_config.get("data_unavailable", 'wss://stream-testnet.bybit.com/v5/public/linear')
            else:
                ws_url = ws_config.get('mainnet_endpoint', 'wss://stream.bybit.com/v5/public/linear')

            # Ensure protocol prefix
            if not ws_url.startswith('wss://'):
                ws_url = f"wss://{ws_url.lstrip('/')}"

            self.logger.debug(f"Connecting to WebSocket URL: {ws_url}")

            # Create session and connect
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.ws = await self.session.ws_connect(
                ws_url,
                autoclose=False,
                heartbeat=30
            )

            self.connected = True
            self._running = True

            # ✅ CRITICAL FIX: Start background processing tasks
            from src.utils.task_tracker import create_tracked_task

            self._tasks.append(
                create_tracked_task(
                    self._message_loop(),
                    name="bybit_liquidation_ws_message_loop"
                )
            )
            self._tasks.append(
                create_tracked_task(
                    self._keepalive_loop(),
                    name="bybit_liquidation_ws_keepalive"
                )
            )

            self.logger.info("✅ WebSocket connected with message processing loops started")
            return True

        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {str(e)}")
            await self._cleanup()
            return False

    # ✅ NEW: Message processing loop
    async def _message_loop(self):
        """Process incoming messages continuously."""
        self.logger.info("Message loop started")

        while self._running and self.connected:
            try:
                # Wait for messages with timeout
                msg = await asyncio.wait_for(self.ws.receive(), timeout=30.0)

                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)

                elif msg.type == aiohttp.WSMsgType.BINARY:
                    self.logger.debug("Received binary message (ignored)")

                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.warning("WebSocket closed by server")
                    break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {self.ws.exception()}")
                    break

            except asyncio.TimeoutError:
                # No message for 30s - connection idle, that's OK
                continue

            except Exception as e:
                self.logger.error(f"Error in message loop: {e}", exc_info=True)
                break

        self.logger.info("Message loop stopped")
        await self._cleanup()

    # ✅ NEW: Keepalive loop
    async def _keepalive_loop(self):
        """Send periodic pings to maintain connection."""
        self.logger.info("Keepalive loop started")

        while self._running and self.connected:
            try:
                await asyncio.sleep(20)  # Ping every 20 seconds

                if self.ws and not self.ws.closed:
                    await self.ws.ping()
                    self.logger.debug("Sent keepalive ping")
                else:
                    self.logger.warning("WebSocket closed, stopping keepalive")
                    break

            except Exception as e:
                self.logger.error(f"Keepalive error: {e}")
                break

        self.logger.info("Keepalive loop stopped")

    # ✅ NEW: Message handler
    async def _handle_message(self, data: str):
        """Handle incoming message and dispatch to handlers."""
        try:
            msg = json.loads(data)

            # Check for subscription confirmation
            if msg.get('op') == 'subscribe':
                if msg.get('success'):
                    self.logger.info(f"✅ Subscription confirmed: {msg.get('ret_msg')}")
                else:
                    self.logger.error(f"❌ Subscription failed: {msg}")
                return

            # Route to handlers
            topic = msg.get('topic', '')
            if topic:
                self.logger.debug(f"Received message for topic: {topic}")

                # Call matching handlers
                for pattern, callback in self._message_handlers.items():
                    if pattern in topic:
                        await callback(msg)
            else:
                self.logger.debug(f"Received message without topic: {msg}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)

    async def subscribe(self, channels: List[str]) -> bool:
        """Subscribe to channels."""
        try:
            if not self.connected:
                self.logger.info("Not connected, connecting now...")
                if not await self.connect():
                    return False

            # Give connection a moment to stabilize
            await asyncio.sleep(0.5)

            # Send subscription message
            msg = {
                "op": "subscribe",
                "args": channels
            }
            await self.ws.send_json(msg)

            self.logger.info(f"✅ Subscription request sent for {len(channels)} channels")
            return True

        except Exception as e:
            self.logger.error(f"Subscription failed: {e}", exc_info=True)
            return False

    def on_message(self, channel_pattern: str, callback: Callable) -> None:
        """Register message handler for channel pattern."""
        self._message_handlers[channel_pattern] = callback
        self.logger.info(f"Registered handler for pattern: {channel_pattern}")

    # ✅ NEW: Cleanup method
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up WebSocket resources...")

        self._running = False
        self.connected = False

        # Cancel background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Close connections
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

        self.ws = None
        self.session = None
        self._tasks.clear()

        self.logger.info("Cleanup complete")

    async def close(self) -> None:
        """Close WebSocket connection."""
        await self._cleanup()


# ============================================================================
# TESTING CODE
# ============================================================================

async def test_solution_1():
    """Test Solution 1 - Using existing WebSocket."""
    from src.core.exchanges.bybit import BybitExchange
    import logging

    logging.basicConfig(level=logging.INFO)

    config = {
        'websocket': {
            'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear'
        }
    }

    exchange = BybitExchange(config=config)

    print("Testing liquidation subscription...")
    symbols = ['BTCUSDT', 'ETHUSDT']
    result = await exchange.subscribe_liquidations(symbols)

    print(f"Subscription result: {result}")
    print(f"WebSocket connected: {exchange.ws_connected}")

    # Wait and check connection is maintained
    print("Waiting 10 seconds to verify connection stays alive...")
    await asyncio.sleep(10)

    print(f"WebSocket still connected: {exchange.ws_connected}")

    # Try another subscription - should work without error
    print("Testing second subscription...")
    result2 = await exchange.subscribe_liquidations(['SOLUSDT'])
    print(f"Second subscription result: {result2}")


async def test_solution_2():
    """Test Solution 2 - Fixed BybitWebSocket class."""
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    config = {
        'websocket': {
            'mainnet_endpoint': 'wss://stream.bybit.com/v5/public/linear'
        }
    }

    # Create WebSocket
    ws = BybitWebSocket(config=config, logger=logger)

    # Define message handler
    async def handle_liquidation(msg):
        print(f"Received liquidation: {msg.get('topic')}")

    # Register handler
    ws.on_message('allLiquidation', handle_liquidation)

    # Connect
    print("Connecting...")
    result = await ws.connect()
    print(f"Connected: {result}")

    # Subscribe
    print("Subscribing to liquidations...")
    channels = ['allLiquidation.BTCUSDT', 'allLiquidation.ETHUSDT']
    result = await ws.subscribe(channels)
    print(f"Subscribed: {result}")

    # Wait for messages
    print("Waiting for messages (30 seconds)...")
    await asyncio.sleep(30)

    # Cleanup
    await ws.close()


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================
"""
SOLUTION 1 (Recommended):
1. Open: src/core/exchanges/bybit.py
2. Find: subscribe_liquidations() method (line ~1429)
3. Replace with: The subscribe_liquidations() from Solution 1 above
4. Find: handle_websocket_message() method (line ~1350)
5. Add: The liquidation routing section to it
6. Save and restart

SOLUTION 2 (If needed):
1. Open: src/core/exchanges/bybit.py
2. Find: class BybitWebSocket (line ~5919)
3. Replace entire class with: The BybitWebSocket from Solution 2 above
4. Save and restart

TESTING:
Run either test function:
    python -c "import asyncio; from WEBSOCKET_FIX_IMPLEMENTATION import test_solution_1; asyncio.run(test_solution_1())"

Or:
    python -c "import asyncio; from WEBSOCKET_FIX_IMPLEMENTATION import test_solution_2; asyncio.run(test_solution_2())"

VERIFICATION:
Check logs for:
    ✅ WebSocket connected with message processing loops started
    ✅ Subscription request sent
    ✅ Subscription confirmed
    Received message for topic: allLiquidation.BTCUSDT

Should NOT see:
    ❌ Cannot write to closing transport
    ❌ Connection closed
    ❌ WebSocket connection lost
"""
