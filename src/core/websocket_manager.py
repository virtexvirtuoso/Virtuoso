"""
WebSocket Connection Manager
Provides clean lifecycle management, automatic cleanup, and memory leak prevention
"""

import asyncio
import json
import time
import logging
from typing import Dict, Set, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import weakref
from contextlib import asynccontextmanager
import traceback

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    websocket: WebSocket
    client_id: str
    connected_at: datetime
    last_activity: datetime
    subscriptions: Set[str]
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    @property
    def connection_duration(self) -> timedelta:
        """Get connection duration"""
        return datetime.now() - self.connected_at
    
    @property
    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if connection is stale (no activity)"""
        return (datetime.now() - self.last_activity).seconds > timeout_seconds


class WebSocketConnectionManager:
    """
    WebSocket connection manager with automatic cleanup and memory leak prevention
    Features:
    - Automatic connection cleanup
    - Memory leak prevention
    - Connection timeouts
    - Subscription management
    - Message broadcasting
    - Health monitoring
    """
    
    def __init__(self, cleanup_interval: int = 30, connection_timeout: int = 300):
        """
        Initialize WebSocket connection manager
        
        Args:
            cleanup_interval: Seconds between cleanup runs
            connection_timeout: Seconds before marking connection as stale
        """
        # Active connections
        self._connections: Dict[str, ConnectionInfo] = {}
        self._connections_lock = asyncio.Lock()
        
        # Subscription management
        self._subscriptions: Dict[str, Set[str]] = {}  # topic -> set of client_ids
        self._subscriptions_lock = asyncio.Lock()
        
        # Configuration
        self.cleanup_interval = cleanup_interval
        self.connection_timeout = connection_timeout
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._stats = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'connections_closed': 0,
            'cleanup_runs': 0,
            'memory_leaks_prevented': 0
        }
        
        # Message handlers
        self._message_handlers: Dict[str, Callable] = {}
        
        # Weak references for memory safety
        self._weak_connections = weakref.WeakValueDictionary()
    
    async def start(self):
        """Start the connection manager"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("WebSocket connection manager started")
    
    async def stop(self):
        """Stop the connection manager and cleanup all connections"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        await self.close_all_connections()
        
        logger.info("WebSocket connection manager stopped")
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Accept a new WebSocket connection
        
        Args:
            websocket: WebSocket instance
            client_id: Unique client identifier
            
        Returns:
            True if connection successful
        """
        try:
            await websocket.accept()
            
            # Create connection info
            now = datetime.now()
            connection_info = ConnectionInfo(
                websocket=websocket,
                client_id=client_id,
                connected_at=now,
                last_activity=now,
                subscriptions=set()
            )
            
            # Store connection
            async with self._connections_lock:
                # Close existing connection with same client_id
                if client_id in self._connections:
                    await self._disconnect_client(client_id, close_websocket=True)
                
                self._connections[client_id] = connection_info
                self._weak_connections[client_id] = connection_info
            
            # Update statistics
            self._stats['total_connections'] += 1
            self._stats['current_connections'] = len(self._connections)
            
            logger.info(f"WebSocket client {client_id} connected")
            return True
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection for {client_id}: {e}")
            return False
    
    async def disconnect(self, client_id: str):
        """
        Disconnect a client
        
        Args:
            client_id: Client identifier to disconnect
        """
        await self._disconnect_client(client_id, close_websocket=True)
    
    async def _disconnect_client(self, client_id: str, close_websocket: bool = False):
        """Internal method to disconnect a client"""
        async with self._connections_lock:
            if client_id not in self._connections:
                return
            
            connection_info = self._connections[client_id]
            
            # Remove from subscriptions
            async with self._subscriptions_lock:
                for topic in connection_info.subscriptions:
                    if topic in self._subscriptions:
                        self._subscriptions[topic].discard(client_id)
                        if not self._subscriptions[topic]:
                            del self._subscriptions[topic]
            
            # Close WebSocket if requested and still open
            if close_websocket:
                try:
                    if (connection_info.websocket.client_state == WebSocketState.CONNECTED):
                        await connection_info.websocket.close(code=1000, reason="Disconnecting")
                except:
                    pass  # Connection might already be closed
            
            # Remove connection
            del self._connections[client_id]
            
            # Update statistics
            self._stats['current_connections'] = len(self._connections)
            self._stats['connections_closed'] += 1
            
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to a specific client
        
        Args:
            client_id: Client identifier
            message: Message to send
            
        Returns:
            True if message sent successfully
        """
        async with self._connections_lock:
            if client_id not in self._connections:
                return False
            
            connection_info = self._connections[client_id]
            
            try:
                # Check if connection is still valid
                if connection_info.websocket.client_state != WebSocketState.CONNECTED:
                    await self._disconnect_client(client_id, close_websocket=False)
                    return False
                
                # Send message
                message_str = json.dumps(message)
                await connection_info.websocket.send_text(message_str)
                
                # Update statistics
                connection_info.message_count += 1
                connection_info.bytes_sent += len(message_str.encode())
                connection_info.update_activity()
                
                self._stats['messages_sent'] += 1
                self._stats['bytes_sent'] += len(message_str.encode())
                
                return True
                
            except WebSocketDisconnect:
                await self._disconnect_client(client_id, close_websocket=False)
                return False
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self._disconnect_client(client_id, close_websocket=True)
                return False
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]) -> int:
        """
        Broadcast message to all clients subscribed to a topic
        
        Args:
            topic: Topic name
            message: Message to broadcast
            
        Returns:
            Number of clients message was sent to
        """
        async with self._subscriptions_lock:
            if topic not in self._subscriptions:
                return 0
            
            client_ids = list(self._subscriptions[topic])
        
        # Send to all subscribers
        sent_count = 0
        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                sent_count += 1
        
        return sent_count
    
    async def subscribe_client(self, client_id: str, topic: str) -> bool:
        """
        Subscribe a client to a topic
        
        Args:
            client_id: Client identifier
            topic: Topic to subscribe to
            
        Returns:
            True if subscription successful
        """
        async with self._connections_lock:
            if client_id not in self._connections:
                return False
            
            connection_info = self._connections[client_id]
            connection_info.subscriptions.add(topic)
        
        async with self._subscriptions_lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(client_id)
        
        logger.debug(f"Client {client_id} subscribed to topic {topic}")
        return True
    
    async def unsubscribe_client(self, client_id: str, topic: str) -> bool:
        """
        Unsubscribe a client from a topic
        
        Args:
            client_id: Client identifier
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscription successful
        """
        async with self._connections_lock:
            if client_id in self._connections:
                self._connections[client_id].subscriptions.discard(topic)
        
        async with self._subscriptions_lock:
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(client_id)
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]
        
        logger.debug(f"Client {client_id} unsubscribed from topic {topic}")
        return True
    
    async def handle_client_message(self, client_id: str, message: str):
        """
        Handle incoming message from client
        
        Args:
            client_id: Client identifier
            message: Raw message string
        """
        async with self._connections_lock:
            if client_id not in self._connections:
                return
            
            connection_info = self._connections[client_id]
            connection_info.bytes_received += len(message.encode())
            connection_info.update_activity()
            
            self._stats['messages_received'] += 1
            self._stats['bytes_received'] += len(message.encode())
        
        try:
            # Parse message
            data = json.loads(message)
            message_type = data.get('type', 'unknown')
            
            # Handle different message types
            if message_type == 'subscribe':
                topic = data.get('topic')
                if topic:
                    await self.subscribe_client(client_id, topic)
                    await self.send_to_client(client_id, {
                        'type': 'subscription_confirmed',
                        'topic': topic
                    })
            
            elif message_type == 'unsubscribe':
                topic = data.get('topic')
                if topic:
                    await self.unsubscribe_client(client_id, topic)
                    await self.send_to_client(client_id, {
                        'type': 'unsubscription_confirmed',
                        'topic': topic
                    })
            
            elif message_type == 'ping':
                await self.send_to_client(client_id, {'type': 'pong'})
            
            else:
                # Custom message handler
                if message_type in self._message_handlers:
                    await self._message_handlers[message_type](client_id, data)
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message from client {client_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """
        Register a custom message handler
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self._message_handlers[message_type] = handler
    
    async def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a connection
        
        Args:
            client_id: Client identifier
            
        Returns:
            Connection information or None if not found
        """
        async with self._connections_lock:
            if client_id not in self._connections:
                return None
            
            connection_info = self._connections[client_id]
            return {
                'client_id': client_id,
                'connected_at': connection_info.connected_at.isoformat(),
                'last_activity': connection_info.last_activity.isoformat(),
                'connection_duration': str(connection_info.connection_duration),
                'subscriptions': list(connection_info.subscriptions),
                'message_count': connection_info.message_count,
                'bytes_sent': connection_info.bytes_sent,
                'bytes_received': connection_info.bytes_received
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        async with self._connections_lock:
            active_connections = len(self._connections)
        
        async with self._subscriptions_lock:
            active_topics = len(self._subscriptions)
            total_subscriptions = sum(len(clients) for clients in self._subscriptions.values())
        
        return {
            **self._stats,
            'current_connections': active_connections,
            'active_topics': active_topics,
            'total_subscriptions': total_subscriptions,
            'memory_references': len(self._weak_connections)
        }
    
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_connections()
                self._stats['cleanup_runs'] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_stale_connections(self):
        """Clean up stale connections and prevent memory leaks"""
        stale_clients = []
        
        async with self._connections_lock:
            for client_id, connection_info in self._connections.items():
                # Check for stale connections
                if connection_info.is_stale(self.connection_timeout):
                    stale_clients.append(client_id)
                    continue
                
                # Check if WebSocket is still connected
                try:
                    if connection_info.websocket.client_state != WebSocketState.CONNECTED:
                        stale_clients.append(client_id)
                except:
                    stale_clients.append(client_id)
        
        # Clean up stale connections
        for client_id in stale_clients:
            await self._disconnect_client(client_id, close_websocket=True)
            self._stats['memory_leaks_prevented'] += 1
        
        if stale_clients:
            logger.info(f"Cleaned up {len(stale_clients)} stale WebSocket connections")
        
        # Clean up orphaned subscriptions
        async with self._subscriptions_lock:
            orphaned_topics = []
            for topic, client_ids in self._subscriptions.items():
                valid_clients = set()
                for client_id in client_ids:
                    if client_id in self._connections:
                        valid_clients.add(client_id)
                
                if valid_clients != client_ids:
                    if valid_clients:
                        self._subscriptions[topic] = valid_clients
                    else:
                        orphaned_topics.append(topic)
            
            for topic in orphaned_topics:
                del self._subscriptions[topic]
        
        # Force garbage collection of weak references
        self._weak_connections = weakref.WeakValueDictionary()
        for client_id, connection_info in self._connections.items():
            self._weak_connections[client_id] = connection_info
    
    async def close_all_connections(self):
        """Close all active connections"""
        async with self._connections_lock:
            client_ids = list(self._connections.keys())
        
        for client_id in client_ids:
            await self._disconnect_client(client_id, close_websocket=True)
        
        # Clear all subscriptions
        async with self._subscriptions_lock:
            self._subscriptions.clear()
        
        logger.info("All WebSocket connections closed")
    
    @asynccontextmanager
    async def connection_context(self, websocket: WebSocket, client_id: str):
        """
        Context manager for WebSocket connections
        Ensures proper cleanup even if exceptions occur
        """
        try:
            connected = await self.connect(websocket, client_id)
            if not connected:
                return
            
            yield client_id
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket client {client_id} disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self.disconnect(client_id)


# Global connection manager instance
_connection_manager: Optional[WebSocketConnectionManager] = None

def get_connection_manager() -> WebSocketConnectionManager:
    """Get the global WebSocket connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = WebSocketConnectionManager()
    return _connection_manager