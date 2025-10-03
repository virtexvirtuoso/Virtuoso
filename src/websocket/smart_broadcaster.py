from src.utils.task_tracker import create_tracked_task
"""
Smart WebSocket Broadcasting System
Optimized message delivery with subscription management and intelligent filtering.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from fastapi import WebSocket
from enum import Enum
import weakref

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocket message types with priorities"""
    MARKET_UPDATE = "market_update"
    CONFLUENCE_UPDATE = "confluence_update"
    ALERT = "alert"
    DASHBOARD_REFRESH = "dashboard_refresh"
    SYSTEM_STATUS = "system_status"
    HEARTBEAT = "heartbeat"

class Priority(Enum):
    """Message priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class ClientConnection:
    """Represents a WebSocket client connection"""
    websocket: WebSocket
    client_id: str
    subscriptions: Set[str] = field(default_factory=set)
    message_filters: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    connection_time: float = field(default_factory=time.time)
    message_count: int = 0
    is_mobile: bool = False
    bandwidth_limit: Optional[int] = None  # Messages per second

@dataclass
class QueuedMessage:
    """Represents a queued message for delivery"""
    message_type: MessageType
    priority: Priority
    content: Dict[str, Any]
    target_clients: List[str]
    created_at: float = field(default_factory=time.time)
    attempts: int = 0

class SmartWebSocketBroadcaster:
    """Optimized WebSocket message delivery with intelligent routing"""
    
    def __init__(self):
        self.clients: Dict[str, ClientConnection] = {}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # topic -> client_ids
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self._stats = {
            'total_messages': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'clients_connected': 0,
            'clients_disconnected': 0,
            'avg_delivery_time': 0,
            'queue_size': 0
        }
        self._running = False
    
    async def start(self):
        """Start the broadcasting service"""
        if not self._running:
            self._running = True
            self.processing_task = create_tracked_task(self._process_message_queue(), name="auto_tracked_task")
            logger.info("Smart WebSocket broadcaster started")
    
    async def stop(self):
        """Stop the broadcasting service"""
        self._running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Smart WebSocket broadcaster stopped")
    
    async def connect_client(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """Connect a new WebSocket client"""
        if not client_id:
            client_id = f"client_{int(time.time() * 1000)}_{len(self.clients)}"
        
        await websocket.accept()
        
        # Detect if client is mobile based on user agent (if available)
        is_mobile = self._detect_mobile_client(websocket)
        
        client = ClientConnection(
            websocket=websocket,
            client_id=client_id,
            is_mobile=is_mobile,
            bandwidth_limit=10 if is_mobile else 50  # Messages per second limit
        )
        
        self.clients[client_id] = client
        self._stats['clients_connected'] += 1
        
        logger.info(f"Client {client_id} connected (mobile: {is_mobile})")
        
        # Send welcome message
        await self._send_to_client(client_id, {
            "type": "welcome",
            "client_id": client_id,
            "server_time": time.time(),
            "capabilities": {
                "subscriptions": True,
                "filtering": True,
                "prioritization": True,
                "mobile_optimized": is_mobile
            }
        })
        
        return client_id
    
    async def disconnect_client(self, client_id: str):
        """Disconnect a WebSocket client"""
        if client_id in self.clients:
            # Remove from all subscriptions
            for topic, subscribers in self.subscriptions.items():
                subscribers.discard(client_id)
            
            # Remove empty subscriptions
            self.subscriptions = {
                topic: subscribers 
                for topic, subscribers in self.subscriptions.items() 
                if subscribers
            }
            
            del self.clients[client_id]
            self._stats['clients_disconnected'] += 1
            
            logger.info(f"Client {client_id} disconnected")
    
    async def subscribe_client(self, client_id: str, topics: List[str], filters: Optional[Dict[str, Any]] = None):
        """Subscribe client to specific topics with optional filters"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        
        for topic in topics:
            client.subscriptions.add(topic)
            self.subscriptions[topic].add(client_id)
        
        if filters:
            client.message_filters.update(filters)
        
        logger.debug(f"Client {client_id} subscribed to {topics}")
        return True
    
    async def unsubscribe_client(self, client_id: str, topics: List[str]):
        """Unsubscribe client from specific topics"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        
        for topic in topics:
            client.subscriptions.discard(topic)
            self.subscriptions[topic].discard(client_id)
        
        logger.debug(f"Client {client_id} unsubscribed from {topics}")
        return True
    
    async def broadcast_update(self, topic: str, data: Dict[str, Any], 
                            message_type: MessageType = MessageType.MARKET_UPDATE,
                            priority: Priority = Priority.MEDIUM):
        """Broadcast update to subscribed clients"""
        
        # Get subscribed clients
        target_clients = list(self.subscriptions.get(topic, set()))
        
        if not target_clients:
            return
        
        # Apply client-specific filtering
        filtered_clients = await self._filter_clients_for_message(target_clients, topic, data)
        
        if filtered_clients:
            message = QueuedMessage(
                message_type=message_type,
                priority=priority,
                content={
                    'type': message_type.value,
                    'topic': topic,
                    'data': data,
                    'timestamp': time.time()
                },
                target_clients=filtered_clients
            )
            
            await self.message_queue.put(message)
            self._stats['queue_size'] = self.message_queue.qsize()
    
    async def send_alert(self, alert_data: Dict[str, Any], priority: Priority = Priority.HIGH):
        """Send alert to all connected clients"""
        all_clients = list(self.clients.keys())
        
        message = QueuedMessage(
            message_type=MessageType.ALERT,
            priority=priority,
            content={
                'type': MessageType.ALERT.value,
                'data': alert_data,
                'timestamp': time.time()
            },
            target_clients=all_clients
        )
        
        await self.message_queue.put(message)
    
    async def send_dashboard_refresh(self, dashboard_data: Dict[str, Any]):
        """Send dashboard refresh to subscribed clients"""
        dashboard_clients = list(self.subscriptions.get('dashboard', set()))
        
        if dashboard_clients:
            message = QueuedMessage(
                message_type=MessageType.DASHBOARD_REFRESH,
                priority=Priority.MEDIUM,
                content={
                    'type': MessageType.DASHBOARD_REFRESH.value,
                    'data': dashboard_data,
                    'timestamp': time.time()
                },
                target_clients=dashboard_clients
            )
            
            await self.message_queue.put(message)
    
    async def send_heartbeat(self):
        """Send heartbeat to all connected clients"""
        all_clients = list(self.clients.keys())
        
        if all_clients:
            message = QueuedMessage(
                message_type=MessageType.HEARTBEAT,
                priority=Priority.LOW,
                content={
                    'type': MessageType.HEARTBEAT.value,
                    'server_time': time.time(),
                    'connected_clients': len(all_clients)
                },
                target_clients=all_clients
            )
            
            await self.message_queue.put(message)
    
    async def _process_message_queue(self):
        """Process queued messages with priority ordering"""
        while self._running:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                await self._deliver_message(message)
                
                # Update queue size
                self._stats['queue_size'] = self.message_queue.qsize()
                
            except asyncio.TimeoutError:
                # Periodic maintenance
                await self._cleanup_disconnected_clients()
                await self._send_periodic_heartbeat()
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
    
    async def _deliver_message(self, message: QueuedMessage):
        """Deliver message to target clients"""
        start_time = time.time()
        delivered_count = 0
        failed_count = 0
        
        # Create delivery tasks
        delivery_tasks = []
        for client_id in message.target_clients:
            if client_id in self.clients:
                task = self._send_to_client(client_id, message.content)
                delivery_tasks.append((client_id, task))
        
        if delivery_tasks:
            # Execute deliveries in parallel with timeout
            results = await asyncio.gather(
                *[task for _, task in delivery_tasks],
                return_exceptions=True
            )
            
            # Count successes and failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    client_id = delivery_tasks[i][0]
                    logger.warning(f"Failed to deliver message to {client_id}: {result}")
                else:
                    delivered_count += 1
        
        # Update statistics
        self._stats['total_messages'] += 1
        self._stats['messages_delivered'] += delivered_count
        self._stats['messages_failed'] += failed_count
        
        delivery_time = (time.time() - start_time) * 1000
        current_avg = self._stats['avg_delivery_time']
        total_messages = self._stats['total_messages']
        self._stats['avg_delivery_time'] = ((current_avg * (total_messages - 1)) + delivery_time) / total_messages
        
        logger.debug(f"Message delivered to {delivered_count}/{len(message.target_clients)} clients in {delivery_time:.2f}ms")
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific client"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        
        try:
            # Check bandwidth limits for mobile clients
            if client.is_mobile and not await self._check_bandwidth_limit(client):
                return False
            
            # Optimize message for mobile clients
            if client.is_mobile:
                message = self._optimize_message_for_mobile(message)
            
            # Send message
            await client.websocket.send_text(json.dumps(message))
            client.message_count += 1
            client.last_heartbeat = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            # Schedule client for disconnection
            create_tracked_task(self.disconnect_client, name="disconnect_client_task")
            return False
    
    async def _filter_clients_for_message(self, client_ids: List[str], topic: str, data: Dict[str, Any]) -> List[str]:
        """Filter clients based on their subscription preferences and filters"""
        filtered_clients = []
        
        for client_id in client_ids:
            if client_id not in self.clients:
                continue
                
            client = self.clients[client_id]
            
            # Apply message filters
            if await self._should_send_to_client(client, topic, data):
                filtered_clients.append(client_id)
        
        return filtered_clients
    
    async def _should_send_to_client(self, client: ClientConnection, topic: str, data: Dict[str, Any]) -> bool:
        """Determine if message should be sent to specific client"""
        # Check if client is subscribed to topic
        if topic not in client.subscriptions:
            return False
        
        # Apply client-specific filters
        filters = client.message_filters.get(topic, {})
        
        if filters:
            # Example filters
            if 'min_price' in filters and data.get('price', 0) < filters['min_price']:
                return False
            
            if 'symbols' in filters and data.get('symbol') not in filters['symbols']:
                return False
            
            if 'min_score' in filters and data.get('confluence_score', 0) < filters['min_score']:
                return False
        
        return True
    
    async def _check_bandwidth_limit(self, client: ClientConnection) -> bool:
        """Check if client is within bandwidth limits"""
        if not client.bandwidth_limit:
            return True
        
        current_time = time.time()
        time_window = 1.0  # 1 second window
        
        # Simple rate limiting - in production, you'd use a more sophisticated algorithm
        messages_in_window = client.message_count  # Simplified for demo
        
        return messages_in_window < client.bandwidth_limit
    
    def _optimize_message_for_mobile(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize message payload for mobile clients"""
        # Remove unnecessary fields for mobile
        mobile_message = message.copy()
        
        # Reduce precision for mobile
        if 'data' in mobile_message and isinstance(mobile_message['data'], dict):
            data = mobile_message['data']
            
            # Round numerical values
            for key, value in data.items():
                if isinstance(value, float):
                    data[key] = round(value, 2)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, float):
                            value[sub_key] = round(sub_value, 2)
        
        return mobile_message
    
    def _detect_mobile_client(self, websocket: WebSocket) -> bool:
        """Detect if client is mobile based on available headers"""
        try:
            # This is a simplified detection - in production, you'd check User-Agent
            headers = getattr(websocket, 'headers', {})
            user_agent = headers.get('user-agent', '').lower()
            
            mobile_indicators = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
            return any(indicator in user_agent for indicator in mobile_indicators)
        except:
            return False
    
    async def _cleanup_disconnected_clients(self):
        """Clean up disconnected clients"""
        current_time = time.time()
        disconnected_clients = []
        
        for client_id, client in self.clients.items():
            # Check if client hasn't sent heartbeat in 60 seconds
            if current_time - client.last_heartbeat > 60:
                try:
                    # Try to send ping
                    await client.websocket.ping()
                except:
                    disconnected_clients.append(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect_client(client_id)
    
    async def _send_periodic_heartbeat(self):
        """Send periodic heartbeat to maintain connections"""
        if len(self.clients) > 0 and int(time.time()) % 30 == 0:  # Every 30 seconds
            await self.send_heartbeat()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get broadcasting statistics"""
        return {
            **self._stats,
            "active_clients": len(self.clients),
            "active_subscriptions": len(self.subscriptions),
            "mobile_clients": sum(1 for c in self.clients.values() if c.is_mobile),
            "desktop_clients": sum(1 for c in self.clients.values() if not c.is_mobile)
        }
    
    def get_client_info(self) -> List[Dict[str, Any]]:
        """Get information about connected clients"""
        return [
            {
                "client_id": client.client_id,
                "is_mobile": client.is_mobile,
                "subscriptions": list(client.subscriptions),
                "message_count": client.message_count,
                "connection_time": client.connection_time,
                "last_heartbeat": client.last_heartbeat,
                "bandwidth_limit": client.bandwidth_limit
            }
            for client in self.clients.values()
        ]

# Global broadcaster instance
smart_broadcaster = SmartWebSocketBroadcaster()