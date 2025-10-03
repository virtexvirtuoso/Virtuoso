from src.utils.task_tracker import create_tracked_task
"""
Mobile-Optimized Real-time Streaming Manager
Phase 3: Transforms request-response to real-time streaming architecture
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import weakref

logger = logging.getLogger(__name__)

class StreamChannel(Enum):
    """Mobile-optimized streaming channels"""
    CONFLUENCE_LIVE = "confluence_live"      # Real-time confluence scores
    MARKET_PULSE = "market_pulse"            # Critical market movements  
    SIGNAL_STREAM = "signal_stream"          # New trading signals
    ALERT_PRIORITY = "alert_priority"        # High-priority alerts
    DASHBOARD_SYNC = "dashboard_sync"        # Dashboard state synchronization

class MessageType(Enum):
    """WebSocket message types"""
    CONFLUENCE_UPDATE = "confluence_update"
    MARKET_UPDATE = "market_update"
    SIGNAL_ALERT = "signal_alert"
    SYSTEM_ALERT = "system_alert"
    DASHBOARD_SYNC = "dashboard_sync"
    HEARTBEAT = "heartbeat"

class Priority(Enum):
    """Message priority levels"""
    CRITICAL = 1    # Immediate delivery
    HIGH = 2        # High priority
    NORMAL = 3      # Standard priority
    LOW = 4         # Background updates

@dataclass
class MobileClient:
    """Represents a connected mobile client"""
    client_id: str
    websocket: Any
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    subscribed_channels: Set[str] = field(default_factory=set)
    message_filters: Dict[str, Dict] = field(default_factory=dict)
    connection_quality: str = "unknown"  # excellent, good, fair, slow, poor
    messages_sent: int = 0
    bytes_sent: int = 0

class MobileStreamManager:
    """
    Mobile-optimized streaming manager for Phase 3 real-time features
    Integrates with Phase 2 cache system for intelligent data streaming
    """
    
    def __init__(self):
        self.clients: Dict[str, MobileClient] = {}
        self.channels: Dict[str, Set[str]] = {channel.value: set() for channel in StreamChannel}
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._streaming_tasks: List[asyncio.Task] = []
        self._market_volatility = 0.5  # 0.0 to 1.0
        self._active = False
        
        # Adaptive update rates based on volatility
        self.base_update_rates = {
            StreamChannel.CONFLUENCE_LIVE.value: 5,    # 5 seconds base
            StreamChannel.MARKET_PULSE.value: 3,       # 3 seconds base
            StreamChannel.SIGNAL_STREAM.value: 1,      # 1 second base
            StreamChannel.ALERT_PRIORITY.value: 0.5,   # 0.5 seconds base
            StreamChannel.DASHBOARD_SYNC.value: 10     # 10 seconds base
        }
        
    async def start(self):
        """Start the mobile streaming manager"""
        if self._active:
            logger.debug("Mobile stream manager already active")
            return
            
        self._active = True
        logger.info("🚀 Starting Phase 3 Mobile Stream Manager")
        
        # Start core streaming tasks
        self._streaming_tasks = [
            create_tracked_task(self._process_message_queue(), name="auto_tracked_task"),
            create_tracked_task(self._monitor_client_health(), name="auto_tracked_task"),
            create_tracked_task(self._adaptive_market_monitoring(), name="auto_tracked_task"),
            create_tracked_task(self._stream_confluence_updates(), name="auto_tracked_task"),
            create_tracked_task(self._stream_market_pulse(), name="auto_tracked_task")
        ]
        
        logger.info("✅ Phase 3 Mobile Streaming Manager started with 5 background tasks")
        
    async def stop(self):
        """Stop the streaming manager and cleanup"""
        self._active = False
        
        # Cancel all tasks
        for task in self._streaming_tasks:
            task.cancel()
        
        # Disconnect all clients
        for client_id in list(self.clients.keys()):
            await self.disconnect_client(client_id)
        
        logger.info("🛑 Mobile Stream Manager stopped")
        
    async def connect_client(self, websocket, client_info: Dict = None) -> str:
        """Connect a mobile client to the streaming system"""
        client_id = f"mobile_{int(time.time() * 1000)}_{id(websocket)}"
        
        client = MobileClient(
            client_id=client_id,
            websocket=websocket,
            connection_quality=client_info.get('quality', 'unknown') if client_info else 'unknown'
        )
        
        self.clients[client_id] = client
        
        # Accept WebSocket connection
        await websocket.accept()
        
        # Send welcome message
        welcome = {
            'type': 'connection_established',
            'client_id': client_id,
            'phase': 3,
            'streaming_enabled': True,
            'available_channels': [channel.value for channel in StreamChannel],
            'timestamp': time.time()
        }
        
        await self._send_to_client(client_id, welcome)
        
        logger.info(f"📱 Mobile client {client_id} connected (quality: {client.connection_quality})")
        return client_id
        
    async def disconnect_client(self, client_id: str):
        """Disconnect a mobile client"""
        if client_id not in self.clients:
            return
            
        client = self.clients[client_id]
        
        # Remove from all channels
        for channel_clients in self.channels.values():
            channel_clients.discard(client_id)
        
        # Close WebSocket if still open
        try:
            if not client.websocket.client_state.DISCONNECTED:
                await client.websocket.close()
        except Exception as e:
            logger.debug(f"Error closing WebSocket for {client_id}: {e}")
        
        # Remove client
        del self.clients[client_id]
        
        logger.info(f"📱 Mobile client {client_id} disconnected (sent {client.messages_sent} messages)")
        
    async def subscribe_client(self, client_id: str, channels: List[str], filters: Dict = None):
        """Subscribe client to specific channels with optional filters"""
        if client_id not in self.clients:
            logger.warning(f"Cannot subscribe unknown client {client_id}")
            return
            
        client = self.clients[client_id]
        
        for channel in channels:
            if channel in [c.value for c in StreamChannel]:
                client.subscribed_channels.add(channel)
                self.channels[channel].add(client_id)
                
                # Apply filters if provided
                if filters and channel in filters:
                    client.message_filters[channel] = filters[channel]
        
        # Send subscription confirmation
        confirmation = {
            'type': 'subscription_confirmed',
            'channels': list(client.subscribed_channels),
            'filters': client.message_filters,
            'timestamp': time.time()
        }
        
        await self._send_to_client(client_id, confirmation)
        
        logger.info(f"📱 Client {client_id} subscribed to {len(channels)} channels")
        
    async def broadcast_update(self, channel: str, data: Dict, message_type: MessageType, priority: Priority = Priority.NORMAL):
        """Broadcast update to all clients subscribed to a channel"""
        if channel not in [c.value for c in StreamChannel]:
            logger.warning(f"Invalid channel for broadcast: {channel}")
            return
            
        message = {
            'type': message_type.value,
            'channel': channel,
            'priority': priority.value,
            'data': data,
            'timestamp': time.time()
        }
        
        # Add to message queue for processing
        try:
            await self._message_queue.put((channel, message, priority))
        except asyncio.QueueFull:
            logger.warning(f"Message queue full, dropping {message_type.value} message")
            
    async def _process_message_queue(self):
        """Process the message queue and send to appropriate clients"""
        while self._active:
            try:
                # Get message from queue (wait up to 1 second)
                try:
                    channel, message, priority = await asyncio.wait_for(
                        self._message_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Get clients subscribed to this channel
                subscribed_clients = self.channels.get(channel, set())
                
                if not subscribed_clients:
                    continue
                
                # Send to all subscribed clients
                send_tasks = []
                for client_id in subscribed_clients.copy():  # Copy to avoid modification during iteration
                    if client_id in self.clients:
                        # Apply client-specific filters
                        if self._message_passes_filter(client_id, channel, message):
                            send_tasks.append(self._send_to_client(client_id, message))
                
                # Send messages concurrently
                if send_tasks:
                    await asyncio.gather(*send_tasks, return_exceptions=True)
                    
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
                
    def _message_passes_filter(self, client_id: str, channel: str, message: Dict) -> bool:
        """Check if message passes client-specific filters"""
        client = self.clients.get(client_id)
        if not client or channel not in client.message_filters:
            return True  # No filters = pass all
            
        filters = client.message_filters[channel]
        data = message.get('data', {})
        
        # Apply various filter types
        if 'min_score' in filters:
            score = data.get('confluence_score', data.get('score', 0))
            if score < filters['min_score']:
                return False
                
        if 'symbols' in filters:
            symbol = data.get('symbol', data.get('pair'))
            if symbol and symbol not in filters['symbols']:
                return False
                
        if 'severity' in filters:
            severity = data.get('severity', 'normal')
            if severity not in filters['severity']:
                return False
                
        return True
        
    async def _send_to_client(self, client_id: str, message: Dict):
        """Send message to a specific client"""
        if client_id not in self.clients:
            return
            
        client = self.clients[client_id]
        
        try:
            # Convert to JSON
            json_message = json.dumps(message)
            
            # Send via WebSocket
            await client.websocket.send_text(json_message)
            
            # Update client stats
            client.messages_sent += 1
            client.bytes_sent += len(json_message)
            
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            # Schedule client for disconnection
            create_tracked_task(self.disconnect_client, name="disconnect_client_task")
            
    async def _monitor_client_health(self):
        """Monitor health of connected clients"""
        while self._active:
            try:
                current_time = time.time()
                
                # Check each client
                for client_id, client in list(self.clients.items()):
                    # Check for stale connections (no heartbeat for 2 minutes)
                    if current_time - client.last_heartbeat > 120:
                        logger.warning(f"Client {client_id} heartbeat timeout, disconnecting")
                        await self.disconnect_client(client_id)
                        continue
                    
                    # Send periodic heartbeat
                    if current_time - client.last_heartbeat > 30:  # Every 30 seconds
                        heartbeat = {
                            'type': 'heartbeat',
                            'server_time': current_time,
                            'client_stats': {
                                'messages_sent': client.messages_sent,
                                'bytes_sent': client.bytes_sent,
                                'uptime': current_time - client.connected_at
                            }
                        }
                        await self._send_to_client(client_id, heartbeat)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring client health: {e}")
                await asyncio.sleep(30)
                
    async def _adaptive_market_monitoring(self):
        """Monitor market conditions to adjust streaming rates"""
        while self._active:
            try:
                # Calculate current market volatility
                volatility = await self._calculate_market_volatility()
                
                if abs(volatility - self._market_volatility) > 0.1:  # Significant change
                    self._market_volatility = volatility
                    
                    # Log volatility change
                    if volatility > 0.8:
                        level = "HIGH"
                    elif volatility > 0.5:
                        level = "MEDIUM"
                    else:
                        level = "LOW"
                        
                    logger.info(f"📊 Market volatility: {volatility:.2f} ({level})")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring market volatility: {e}")
                await asyncio.sleep(60)
                
    async def _calculate_market_volatility(self) -> float:
        """Calculate current market volatility (0.0 to 1.0)"""
        try:
            # Get market data from Phase 2 cache
            from src.api.services.mobile_optimization_service import mobile_optimization_service
            
            mobile_data = await mobile_optimization_service.get_optimized_mobile_data()
            
            if mobile_data and 'confluence_scores' in mobile_data:
                scores = mobile_data['confluence_scores']
                if scores:
                    # Calculate volatility from confluence score variations
                    score_values = [s.get('confluence_score', 50) for s in scores if isinstance(s, dict)]
                    if score_values:
                        avg_score = sum(score_values) / len(score_values)
                        variance = sum((s - avg_score) ** 2 for s in score_values) / len(score_values)
                        volatility = min(1.0, variance / 1000.0)  # Normalize
                        return volatility
            
            return 0.5  # Default medium volatility
            
        except Exception as e:
            logger.error(f"Error calculating market volatility: {e}")
            return 0.5
            
    def _get_adaptive_update_rate(self, channel: str) -> float:
        """Get adaptive update rate based on market volatility"""
        base_rate = self.base_update_rates.get(channel, 5.0)
        
        # Adjust based on volatility
        if self._market_volatility > 0.8:  # High volatility
            return base_rate * 0.5  # Update 2x faster
        elif self._market_volatility > 0.5:  # Medium volatility
            return base_rate * 0.75  # Update 1.33x faster
        else:  # Low volatility
            return base_rate * 1.5  # Update slower
            
    async def _stream_confluence_updates(self):
        """Stream real-time confluence score updates"""
        last_update = {}
        
        while self._active:
            try:
                update_rate = self._get_adaptive_update_rate(StreamChannel.CONFLUENCE_LIVE.value)
                
                # Get latest confluence data
                from src.api.services.mobile_optimization_service import mobile_optimization_service
                mobile_data = await mobile_optimization_service.get_optimized_mobile_data()
                
                if mobile_data and mobile_data.get('confluence_scores'):
                    # Check for significant changes
                    current_scores = {
                        s.get('symbol', ''): s.get('confluence_score', 0) 
                        for s in mobile_data['confluence_scores'] 
                        if isinstance(s, dict)
                    }
                    
                    if current_scores != last_update:
                        # Broadcast confluence update
                        await self.broadcast_update(
                            channel=StreamChannel.CONFLUENCE_LIVE.value,
                            data={
                                'confluence_scores': mobile_data['confluence_scores'],
                                'market_overview': mobile_data.get('market_overview', {}),
                                'update_source': mobile_data.get('cache_source', 'unknown'),
                                'volatility_level': 'high' if self._market_volatility > 0.8 else 'medium' if self._market_volatility > 0.5 else 'low'
                            },
                            message_type=MessageType.CONFLUENCE_UPDATE,
                            priority=Priority.HIGH if self._market_volatility > 0.7 else Priority.NORMAL
                        )
                        
                        last_update = current_scores
                        logger.debug(f"📊 Streamed confluence update to {len(self.channels[StreamChannel.CONFLUENCE_LIVE.value])} clients")
                
                await asyncio.sleep(update_rate)
                
            except Exception as e:
                logger.error(f"Error streaming confluence updates: {e}")
                await asyncio.sleep(10)
                
    async def _stream_market_pulse(self):
        """Stream critical market pulse updates"""
        while self._active:
            try:
                update_rate = self._get_adaptive_update_rate(StreamChannel.MARKET_PULSE.value)
                
                # Monitor for critical market events
                market_events = await self._detect_market_events()
                
                for event in market_events:
                    await self.broadcast_update(
                        channel=StreamChannel.MARKET_PULSE.value,
                        data=event,
                        message_type=MessageType.MARKET_UPDATE,
                        priority=Priority.CRITICAL if event.get('severity') == 'critical' else Priority.HIGH
                    )
                
                await asyncio.sleep(update_rate)
                
            except Exception as e:
                logger.error(f"Error streaming market pulse: {e}")
                await asyncio.sleep(5)
                
    async def _detect_market_events(self) -> List[Dict]:
        """Detect critical market events"""
        # Placeholder implementation
        # In real implementation, this would analyze:
        # - Large price movements (>5% in short time)
        # - Volume spikes
        # - New signals with high confidence
        # - System alerts
        
        return []  # No events for now
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get streaming manager statistics"""
        return {
            'active': self._active,
            'connected_clients': len(self.clients),
            'channels': {
                channel: len(clients) for channel, clients in self.channels.items()
            },
            'market_volatility': self._market_volatility,
            'message_queue_size': self._message_queue.qsize(),
            'total_messages_sent': sum(client.messages_sent for client in self.clients.values()),
            'total_bytes_sent': sum(client.bytes_sent for client in self.clients.values()),
            'uptime': time.time() - (min(client.connected_at for client in self.clients.values()) if self.clients else time.time())
        }

# Global mobile stream manager
mobile_stream_manager = MobileStreamManager()