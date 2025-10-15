#!/usr/bin/env python3
"""
WebSocket Connectivity Fix
==========================

This script fixes WebSocket connectivity issues by:
1. Enhancing error handling in WebSocket connection creation
2. Adding connection retry logic with exponential backoff
3. Implementing connection health monitoring
4. Adding network connectivity validation
5. Improving connection status reporting

Issues Fixed:
- 'WebSocket not connected' health warning
- Silent connection failures
- Missing error handling in _create_connection method
- No retry logic for failed connections
"""

import os
import sys
import re
import time
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

class WebSocketConnectivityFixer:
    """Fixes WebSocket connectivity issues in the trading system."""

    def __init__(self):
        self.websocket_manager_path = os.path.join(
            project_root,
            'src/core/exchanges/websocket_manager.py'
        )

    def apply_fixes(self):
        """Apply all WebSocket connectivity fixes."""
        print("🔧 Applying WebSocket connectivity fixes...")

        # 1. Enhance WebSocket connection creation with better error handling
        self._enhance_connection_creation()

        # 2. Add connection retry logic
        self._add_retry_logic()

        # 3. Improve connection health monitoring
        self._enhance_health_monitoring()

        # 4. Add network connectivity validation
        self._add_network_validation()

        print("✅ WebSocket connectivity fixes applied successfully!")

    def _enhance_connection_creation(self):
        """Enhance the _create_connection method with better error handling."""
        print("  📡 Enhancing WebSocket connection creation...")

        if not os.path.exists(self.websocket_manager_path):
            print(f"❌ WebSocket manager file not found: {self.websocket_manager_path}")
            return

        with open(self.websocket_manager_path, 'r') as f:
            content = f.read()

        # Enhanced _create_connection method with comprehensive error handling
        enhanced_create_connection = '''    async def _create_connection(self, topics: List[str], connection_id: str) -> Optional[Dict]:
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
                handler_task = asyncio.create_task(
                    self._handle_messages(ws, topics, connection_id, session),
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

        return None'''

        # Find and replace the existing _create_connection method
        pattern = r'    async def _create_connection\(self, topics: List\[str\], connection_id: str\) -> Optional\[Dict\]:.*?(?=\n    async def|\n    def|\nclass|\Z)'

        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, enhanced_create_connection, content, flags=re.DOTALL)
            print("   ✓ Enhanced _create_connection method")
        else:
            print("   ⚠️ Could not find _create_connection method to replace")
            return

        # Save the enhanced file
        with open(self.websocket_manager_path, 'w') as f:
            f.write(content)

    def _add_network_validation(self):
        """Add network connectivity validation method."""
        print("  🌐 Adding network connectivity validation...")

        with open(self.websocket_manager_path, 'r') as f:
            content = f.read()

        # Add network validation method
        network_validation_method = '''
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
            return False'''

        # Insert the method before the existing methods
        if 'def get_status(self):' in content:
            content = content.replace('    def get_status(self):', f'{network_validation_method}\n\n    def get_status(self):')
            print("   ✓ Added network connectivity validation method")

        # Save the file
        with open(self.websocket_manager_path, 'w') as f:
            f.write(content)

    def _add_retry_logic(self):
        """Add connection retry and recovery logic."""
        print("  🔄 Adding connection retry logic...")

        with open(self.websocket_manager_path, 'r') as f:
            content = f.read()

        # Add connection recovery method
        recovery_method = '''
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
            self.logger.error(f"Error cleaning up connection {connection_id}: {str(e)}")'''

        # Insert the method before get_status
        if 'def get_status(self):' in content:
            content = content.replace('    def get_status(self):', f'{recovery_method}\n\n    def get_status(self):')
            print("   ✓ Added connection recovery methods")

        # Save the file
        with open(self.websocket_manager_path, 'w') as f:
            f.write(content)

    def _enhance_health_monitoring(self):
        """Enhance the health monitoring and status reporting."""
        print("  💚 Enhancing health monitoring...")

        with open(self.websocket_manager_path, 'r') as f:
            content = f.read()

        # Enhanced get_status method
        enhanced_get_status = '''    def get_status(self):
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

        return status_copy'''

        # Replace the existing get_status method
        pattern = r'    def get_status\(self\):.*?return self\.status\.copy\(\)'

        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, enhanced_get_status, content, flags=re.DOTALL)
            print("   ✓ Enhanced get_status method")
        else:
            print("   ⚠️ Could not find get_status method to replace")
            return

        # Save the file
        with open(self.websocket_manager_path, 'w') as f:
            f.write(content)

    def test_websocket_connectivity(self):
        """Test WebSocket connectivity after applying fixes."""
        print("\n🧪 Testing WebSocket connectivity...")

        test_script = '''
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.core.exchanges.websocket_manager import WebSocketManager

async def test_connectivity():
    # Test configuration
    config = {
        'websocket': {'enabled': True},
        'exchanges': {'bybit': {'testnet': False}},
        'market_data': {'websocket_logging': {'verbose': True}}
    }

    # Create WebSocket manager
    ws_manager = WebSocketManager(config)

    # Test symbols
    test_symbols = ['BTCUSDT', 'ETHUSDT']

    try:
        print("Testing WebSocket initialization...")
        await ws_manager.initialize(test_symbols)

        # Check status
        status = ws_manager.get_status()
        print(f"Connection status: {status}")

        if status['connected']:
            print("✅ WebSocket connectivity test PASSED")
        else:
            print("❌ WebSocket connectivity test FAILED")

        # Wait a few seconds for messages
        await asyncio.sleep(5)

        # Get final status
        final_status = ws_manager.get_status()
        print(f"Final status: {final_status}")

    except Exception as e:
        print(f"❌ WebSocket test error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connectivity())
'''

        # Save test script
        test_file = os.path.join(project_root, 'test_websocket_fix.py')
        with open(test_file, 'w') as f:
            f.write(test_script)

        print(f"   📝 Created WebSocket connectivity test: {test_file}")
        print("   ℹ️  Run: python test_websocket_fix.py to test the fixes")

def main():
    """Main function to apply WebSocket connectivity fixes."""
    print("🚀 WebSocket Connectivity Fix Script")
    print("=" * 50)

    fixer = WebSocketConnectivityFixer()

    try:
        fixer.apply_fixes()
        fixer.test_websocket_connectivity()

        print("\n✅ ALL FIXES APPLIED SUCCESSFULLY!")
        print("\n📋 Summary of fixes:")
        print("  🔧 Enhanced WebSocket connection creation with comprehensive error handling")
        print("  🔄 Added connection retry logic with exponential backoff")
        print("  🌐 Implemented network connectivity validation")
        print("  💚 Improved connection health monitoring and status reporting")
        print("  🧪 Created WebSocket connectivity test script")

        print("\n🚀 Next Steps:")
        print("  1. Restart the trading system to apply the fixes")
        print("  2. Run: python test_websocket_fix.py to validate connectivity")
        print("  3. Check the health monitoring for 'WebSocket not connected' warnings")

    except Exception as e:
        print(f"\n❌ Error applying fixes: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())