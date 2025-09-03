#!/usr/bin/env python3
"""
WebSocket Message Deduplication using Memcached
Prevents duplicate message processing in distributed WebSocket systems
"""

import time
import hashlib
import json
from typing import Optional, Dict, Any, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from pymemcache.client.base import Client
from pymemcache import serde
import logging
from collections import deque

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocket message types"""
    TICKER = "ticker"
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    KLINE = "kline"
    ORDER_UPDATE = "order"
    POSITION_UPDATE = "position"
    BALANCE_UPDATE = "balance"
    LIQUIDATION = "liquidation"
    FUNDING_RATE = "funding"
    MARK_PRICE = "mark_price"
    
@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    exchange: str
    channel: str
    message_type: MessageType
    symbol: Optional[str]
    data: Dict[str, Any]
    timestamp: float
    sequence: Optional[int] = None
    
    def get_fingerprint(self) -> str:
        """Generate unique fingerprint for deduplication"""
        # Create fingerprint based on message content
        # Exclude timestamp for deduplication
        fingerprint_data = {
            'exchange': self.exchange,
            'channel': self.channel,
            'type': self.message_type.value,
            'symbol': self.symbol,
            'data': self._normalize_data(self.data)
        }
        
        # Add sequence if available (for ordered messages)
        if self.sequence is not None:
            fingerprint_data['sequence'] = self.sequence
        
        # Create hash
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data for consistent fingerprinting"""
        normalized = {}
        
        # Remove volatile fields that change but don't affect uniqueness
        skip_fields = {'timestamp', 'time', 'datetime', 'received_at', 'local_timestamp'}
        
        for key, value in data.items():
            if key.lower() not in skip_fields:
                if isinstance(value, float):
                    # Round floats to avoid precision issues
                    normalized[key] = round(value, 8)
                elif isinstance(value, dict):
                    normalized[key] = self._normalize_data(value)
                else:
                    normalized[key] = value
        
        return normalized

class WebSocketDeduplicator:
    """
    WebSocket message deduplication system using Memcached
    Ensures messages are processed only once across distributed systems
    """
    
    # Deduplication windows by message type (seconds)
    DEDUPE_WINDOWS = {
        MessageType.TICKER: 1,         # Very short for real-time data
        MessageType.TRADE: 5,          # Slightly longer for trades
        MessageType.ORDERBOOK: 1,      # Short for orderbook updates
        MessageType.KLINE: 60,         # Longer for candle data
        MessageType.ORDER_UPDATE: 10,  # Medium for order updates
        MessageType.POSITION_UPDATE: 10,
        MessageType.BALANCE_UPDATE: 30,
        MessageType.LIQUIDATION: 60,   # Longer to avoid duplicate alerts
        MessageType.FUNDING_RATE: 300, # Very long for funding rates
        MessageType.MARK_PRICE: 5,
    }
    
    # Sequence tracking for ordered channels
    SEQUENCED_TYPES = {
        MessageType.ORDERBOOK,
        MessageType.TRADE,
        MessageType.ORDER_UPDATE
    }
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11211):
        """Initialize WebSocket deduplicator"""
        try:
            self.mc = Client(
                (host, port),
                serializer=serde.python_memcache_serializer,
                deserializer=serde.python_memcache_deserializer,
                connect_timeout=1,
                timeout=0.5
            )
            # Test connection
            self.mc.set(b'ws:test', b'1', expire=1)
            self.available = True
            logger.info(f"WebSocket deduplicator connected to Memcached at {host}:{port}")
        except Exception as e:
            logger.warning(f"Memcached not available for WebSocket deduplication: {e}")
            self.available = False
            self.mc = None
            # Fallback to local deduplication
            self.local_seen = {}
            self.local_sequences = {}
            self.local_buffer = deque(maxlen=10000)  # Circular buffer
        
        # Metrics
        self.metrics = {
            'processed': 0,
            'duplicates': 0,
            'out_of_order': 0,
            'gaps_detected': 0,
            'by_type': {},
            'by_exchange': {}
        }
        
        # Cleanup tracking
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    async def is_duplicate(self, message: WebSocketMessage) -> Tuple[bool, str]:
        """
        Check if message is a duplicate
        
        Args:
            message: WebSocket message to check
            
        Returns:
            Tuple of (is_duplicate, reason)
        """
        self.metrics['processed'] += 1
        self._update_metrics(message)
        
        # Get deduplication window
        window = self.DEDUPE_WINDOWS.get(message.message_type, 5)
        
        # Check sequence if applicable
        if message.message_type in self.SEQUENCED_TYPES and message.sequence is not None:
            seq_check = await self._check_sequence(message)
            if not seq_check[0]:
                return True, seq_check[1]
        
        # Generate fingerprint
        fingerprint = message.get_fingerprint()
        dedupe_key = f"ws:dedupe:{fingerprint}"
        
        # Check for duplicate
        is_dup = await self._check_duplicate(dedupe_key, window)
        
        if is_dup:
            self.metrics['duplicates'] += 1
            self._update_type_metrics(message.message_type.value, 'duplicates')
            return True, "Duplicate message"
        
        return False, "New message"
    
    async def _check_duplicate(self, key: str, window: int) -> bool:
        """Check if message fingerprint has been seen"""
        if self.available and self.mc:
            try:
                # Check if exists
                exists = self.mc.get(key.encode())
                if exists:
                    return True
                
                # Mark as seen
                self.mc.set(key.encode(), 1, expire=window)
                return False
                
            except Exception as e:
                logger.error(f"Deduplication check error: {e}")
                # On error, assume not duplicate to avoid data loss
                return False
        else:
            # Local fallback
            current_time = time.time()
            
            # Cleanup old entries periodically
            if current_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_local()
            
            # Check if seen
            if key in self.local_seen:
                entry = self.local_seen[key]
                if current_time - entry['timestamp'] < window:
                    return True
            
            # Mark as seen
            self.local_seen[key] = {'timestamp': current_time}
            
            # Add to buffer for cleanup tracking
            self.local_buffer.append((key, current_time))
            
            return False
    
    async def _check_sequence(self, message: WebSocketMessage) -> Tuple[bool, str]:
        """Check message sequence for ordered channels"""
        seq_key = f"ws:seq:{message.exchange}:{message.channel}:{message.symbol or 'global'}"
        
        if self.available and self.mc:
            try:
                # Get last sequence
                last_seq = self.mc.get(seq_key.encode())
                last_seq = int(last_seq) if last_seq else 0
                
                # Check sequence
                if message.sequence <= last_seq:
                    self.metrics['out_of_order'] += 1
                    return False, f"Out of order: {message.sequence} <= {last_seq}"
                
                # Check for gaps
                if last_seq > 0 and message.sequence > last_seq + 1:
                    gap = message.sequence - last_seq - 1
                    self.metrics['gaps_detected'] += 1
                    logger.warning(f"Sequence gap detected: {gap} messages missing")
                
                # Update sequence
                self.mc.set(seq_key.encode(), message.sequence, expire=3600)
                return True, "Sequence OK"
                
            except Exception as e:
                logger.error(f"Sequence check error: {e}")
                return True, "Sequence check failed - allowing"
        else:
            # Local sequence tracking
            if seq_key not in self.local_sequences:
                self.local_sequences[seq_key] = 0
            
            last_seq = self.local_sequences[seq_key]
            
            if message.sequence <= last_seq:
                self.metrics['out_of_order'] += 1
                return False, f"Out of order: {message.sequence} <= {last_seq}"
            
            if last_seq > 0 and message.sequence > last_seq + 1:
                gap = message.sequence - last_seq - 1
                self.metrics['gaps_detected'] += 1
                logger.warning(f"Sequence gap detected: {gap} messages missing")
            
            self.local_sequences[seq_key] = message.sequence
            return True, "Sequence OK"
    
    async def batch_check(self, messages: List[WebSocketMessage]) -> List[Tuple[WebSocketMessage, bool]]:
        """
        Batch check multiple messages for efficiency
        
        Args:
            messages: List of messages to check
            
        Returns:
            List of (message, is_duplicate) tuples
        """
        results = []
        
        for message in messages:
            is_dup, _ = await self.is_duplicate(message)
            results.append((message, is_dup))
        
        return results
    
    def _cleanup_local(self):
        """Clean up old local deduplication entries"""
        current_time = time.time()
        max_window = max(self.DEDUPE_WINDOWS.values())
        cutoff_time = current_time - max_window
        
        # Clean up old entries
        keys_to_remove = []
        for key, entry in self.local_seen.items():
            if entry['timestamp'] < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.local_seen[key]
        
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} old deduplication entries")
        
        self.last_cleanup = current_time
    
    def _update_metrics(self, message: WebSocketMessage):
        """Update processing metrics"""
        # By type
        msg_type = message.message_type.value
        if msg_type not in self.metrics['by_type']:
            self.metrics['by_type'][msg_type] = {
                'processed': 0,
                'duplicates': 0,
                'out_of_order': 0
            }
        self.metrics['by_type'][msg_type]['processed'] += 1
        
        # By exchange
        exchange = message.exchange
        if exchange not in self.metrics['by_exchange']:
            self.metrics['by_exchange'][exchange] = {
                'processed': 0,
                'duplicates': 0,
                'gaps': 0
            }
        self.metrics['by_exchange'][exchange]['processed'] += 1
    
    def _update_type_metrics(self, msg_type: str, metric: str):
        """Update type-specific metrics"""
        if msg_type in self.metrics['by_type']:
            self.metrics['by_type'][msg_type][metric] = \
                self.metrics['by_type'][msg_type].get(metric, 0) + 1
    
    async def get_channel_status(self, 
                                exchange: str, 
                                channel: str,
                                symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of a specific channel
        
        Args:
            exchange: Exchange name
            channel: Channel name
            symbol: Optional symbol
            
        Returns:
            Channel status information
        """
        seq_key = f"ws:seq:{exchange}:{channel}:{symbol or 'global'}"
        
        status = {
            'exchange': exchange,
            'channel': channel,
            'symbol': symbol,
            'last_sequence': None,
            'backend': 'memcached' if self.available else 'local'
        }
        
        if self.available and self.mc:
            try:
                last_seq = self.mc.get(seq_key.encode())
                status['last_sequence'] = int(last_seq) if last_seq else 0
            except Exception as e:
                logger.error(f"Failed to get channel status: {e}")
        else:
            status['last_sequence'] = self.local_sequences.get(seq_key, 0)
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get deduplicator metrics"""
        dedup_rate = (self.metrics['duplicates'] / self.metrics['processed'] * 100) \
            if self.metrics['processed'] > 0 else 0
        
        return {
            'processed': self.metrics['processed'],
            'duplicates': self.metrics['duplicates'],
            'deduplication_rate': dedup_rate,
            'out_of_order': self.metrics['out_of_order'],
            'gaps_detected': self.metrics['gaps_detected'],
            'by_type': self.metrics['by_type'],
            'by_exchange': self.metrics['by_exchange'],
            'backend': 'memcached' if self.available else 'local',
            'local_cache_size': len(self.local_seen) if not self.available else 0
        }
    
    def reset_channel(self, 
                     exchange: str, 
                     channel: str,
                     symbol: Optional[str] = None):
        """Reset deduplication for a specific channel"""
        seq_key = f"ws:seq:{exchange}:{channel}:{symbol or 'global'}"
        
        if self.available and self.mc:
            try:
                self.mc.delete(seq_key.encode())
                logger.info(f"Reset channel: {seq_key}")
            except Exception as e:
                logger.error(f"Failed to reset channel: {e}")
        elif seq_key in self.local_sequences:
            del self.local_sequences[seq_key]
            logger.info(f"Reset local channel: {seq_key}")
    
    def close(self):
        """Close connection to Memcached"""
        if self.mc:
            try:
                self.mc.close()
            except:
                pass

# Global instance
_ws_deduplicator = None

def get_websocket_deduplicator() -> WebSocketDeduplicator:
    """Get or create global WebSocket deduplicator instance"""
    global _ws_deduplicator
    if _ws_deduplicator is None:
        _ws_deduplicator = WebSocketDeduplicator()
    return _ws_deduplicator