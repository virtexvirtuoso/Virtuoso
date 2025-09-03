#!/usr/bin/env python3
"""
Alert Throttling System using Memcached
Prevents alert spam and manages alert frequency intelligently
"""

import time
import hashlib
import json
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from pymemcache.client.base import Client
from pymemcache import serde
import logging

logger = logging.getLogger(__name__)

class AlertPriority(Enum):
    """Alert priority levels"""
    CRITICAL = 5    # Always send
    HIGH = 4        # Minimal throttling
    MEDIUM = 3      # Standard throttling
    LOW = 2         # Heavy throttling
    INFO = 1        # Maximum throttling

class AlertType(Enum):
    """Types of alerts"""
    PRICE_ALERT = "price"
    VOLUME_ALERT = "volume"
    TECHNICAL_INDICATOR = "technical"
    RISK_WARNING = "risk"
    SYSTEM_STATUS = "system"
    TRADE_EXECUTION = "trade"
    ERROR_ALERT = "error"
    OPPORTUNITY = "opportunity"
    LIQUIDATION = "liquidation"
    FUNDING_RATE = "funding"

@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    symbol: Optional[str]
    message: str
    data: Dict[str, Any]
    timestamp: float
    user_id: Optional[str] = None
    channel: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.value,
            'priority': self.priority.value,
            'symbol': self.symbol,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'channel': self.channel
        }
    
    def get_fingerprint(self) -> str:
        """Generate unique fingerprint for deduplication"""
        # Create fingerprint from type, symbol, and message pattern
        fingerprint_data = f"{self.alert_type.value}:{self.symbol}:{self.message[:50]}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

class AlertThrottler:
    """
    Intelligent alert throttling system using Memcached
    Prevents alert spam while ensuring critical alerts get through
    """
    
    # Throttling configurations by priority
    THROTTLE_CONFIG = {
        AlertPriority.CRITICAL: {
            'min_interval': 0,      # No throttling
            'max_per_hour': 1000,   # Practically unlimited
            'batch_window': 0       # No batching
        },
        AlertPriority.HIGH: {
            'min_interval': 30,     # 30 seconds between similar alerts
            'max_per_hour': 60,     # Max 60 per hour
            'batch_window': 10      # Batch within 10 seconds
        },
        AlertPriority.MEDIUM: {
            'min_interval': 60,     # 1 minute between similar alerts
            'max_per_hour': 30,     # Max 30 per hour
            'batch_window': 30      # Batch within 30 seconds
        },
        AlertPriority.LOW: {
            'min_interval': 300,    # 5 minutes between similar alerts
            'max_per_hour': 10,     # Max 10 per hour
            'batch_window': 60      # Batch within 1 minute
        },
        AlertPriority.INFO: {
            'min_interval': 600,    # 10 minutes between similar alerts
            'max_per_hour': 5,      # Max 5 per hour
            'batch_window': 300     # Batch within 5 minutes
        }
    }
    
    # Type-specific overrides
    TYPE_CONFIG = {
        AlertType.LIQUIDATION: {
            'always_send': True,    # Never throttle liquidation alerts
            'dedupe_window': 1      # But dedupe within 1 second
        },
        AlertType.ERROR_ALERT: {
            'min_interval': 10,     # Allow frequent error alerts
            'max_per_hour': 100
        },
        AlertType.OPPORTUNITY: {
            'min_interval': 120,    # Space out opportunity alerts
            'max_per_hour': 20,
            'batch_similar': True   # Batch similar opportunities
        }
    }
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11211):
        """Initialize alert throttler"""
        try:
            self.mc = Client(
                (host, port),
                serializer=serde.python_memcache_serializer,
                deserializer=serde.python_memcache_deserializer,
                connect_timeout=1,
                timeout=0.5
            )
            # Test connection
            self.mc.set(b'alert:test', b'1', expire=1)
            self.available = True
            logger.info(f"Alert throttler connected to Memcached at {host}:{port}")
        except Exception as e:
            logger.warning(f"Memcached not available for alert throttling: {e}")
            self.available = False
            self.mc = None
            # Fallback to local tracking
            self.local_history = {}
            self.local_batches = {}
        
        # Metrics
        self.metrics = {
            'sent': 0,
            'throttled': 0,
            'batched': 0,
            'deduplicated': 0,
            'by_type': {},
            'by_priority': {}
        }
    
    async def should_send_alert(self, alert: Alert) -> Tuple[bool, str, Optional[List[Alert]]]:
        """
        Check if alert should be sent
        
        Args:
            alert: Alert to check
            
        Returns:
            Tuple of (should_send, reason, batched_alerts)
        """
        # Check type-specific rules first
        type_config = self.TYPE_CONFIG.get(alert.alert_type, {})
        if type_config.get('always_send'):
            # Check only for deduplication
            if not await self._is_duplicate(alert, type_config.get('dedupe_window', 1)):
                self.metrics['sent'] += 1
                self._update_type_metrics(alert.alert_type.value, 'sent')
                return True, "Critical alert - always send", None
            else:
                self.metrics['deduplicated'] += 1
                return False, "Duplicate alert", None
        
        # Get throttle configuration
        config = self._get_throttle_config(alert)
        
        # Check rate limits
        rate_check = await self._check_rate_limit(alert, config)
        if not rate_check[0]:
            self.metrics['throttled'] += 1
            self._update_type_metrics(alert.alert_type.value, 'throttled')
            return False, rate_check[1], None
        
        # Check for duplicates
        if await self._is_duplicate(alert, config['min_interval']):
            self.metrics['deduplicated'] += 1
            self._update_type_metrics(alert.alert_type.value, 'deduplicated')
            return False, "Duplicate alert within throttle window", None
        
        # Check if should batch
        batch_window = config.get('batch_window', 0)
        if batch_window > 0:
            batched = await self._check_batching(alert, batch_window)
            if batched:
                self.metrics['batched'] += 1
                self._update_type_metrics(alert.alert_type.value, 'batched')
                return True, "Sending batched alerts", batched
        
        # Alert can be sent
        await self._record_alert(alert)
        self.metrics['sent'] += 1
        self._update_type_metrics(alert.alert_type.value, 'sent')
        self._update_priority_metrics(alert.priority.value, 'sent')
        
        return True, "Alert passed throttling", None
    
    def _get_throttle_config(self, alert: Alert) -> Dict[str, Any]:
        """Get throttle configuration for alert"""
        # Start with priority-based config
        config = self.THROTTLE_CONFIG[alert.priority].copy()
        
        # Apply type-specific overrides
        type_config = self.TYPE_CONFIG.get(alert.alert_type, {})
        config.update(type_config)
        
        return config
    
    async def _check_rate_limit(self, alert: Alert, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if alert passes rate limiting"""
        # Check hourly limit
        hour_key = f"alert:hour:{alert.user_id or 'system'}:{alert.alert_type.value}:{int(time.time() / 3600)}"
        
        if self.available and self.mc:
            try:
                # Get current count
                current = self.mc.get(hour_key.encode())
                count = int(current) if current else 0
                
                if count >= config['max_per_hour']:
                    return False, f"Exceeded hourly limit ({config['max_per_hour']})"
                
                # Increment counter
                if current:
                    self.mc.incr(hour_key.encode(), 1)
                else:
                    self.mc.set(hour_key.encode(), 1, expire=3600)
                    
            except Exception as e:
                logger.error(f"Rate limit check error: {e}")
        else:
            # Local fallback
            if hour_key not in self.local_history:
                self.local_history[hour_key] = {'count': 0, 'reset': time.time() + 3600}
            
            entry = self.local_history[hour_key]
            if time.time() > entry['reset']:
                entry['count'] = 0
                entry['reset'] = time.time() + 3600
            
            if entry['count'] >= config['max_per_hour']:
                return False, f"Exceeded hourly limit ({config['max_per_hour']})"
            
            entry['count'] += 1
        
        return True, "Within rate limits"
    
    async def _is_duplicate(self, alert: Alert, window: int) -> bool:
        """Check if alert is duplicate within window"""
        if window <= 0:
            return False
        
        fingerprint = alert.get_fingerprint()
        dedupe_key = f"alert:dedupe:{fingerprint}"
        
        if self.available and self.mc:
            try:
                exists = self.mc.get(dedupe_key.encode())
                if exists:
                    return True
                
                # Mark as seen
                self.mc.set(dedupe_key.encode(), 1, expire=window)
                return False
                
            except Exception as e:
                logger.error(f"Deduplication check error: {e}")
                return False
        else:
            # Local fallback
            if dedupe_key in self.local_history:
                entry = self.local_history[dedupe_key]
                if time.time() - entry['timestamp'] < window:
                    return True
            
            self.local_history[dedupe_key] = {'timestamp': time.time()}
            return False
    
    async def _check_batching(self, alert: Alert, window: int) -> Optional[List[Alert]]:
        """Check if alert should be batched"""
        batch_key = f"alert:batch:{alert.alert_type.value}:{alert.symbol or 'global'}"
        
        if self.available and self.mc:
            try:
                # Get existing batch
                batch_data = self.mc.get(batch_key.encode())
                
                if batch_data:
                    # Add to existing batch
                    batch_data['alerts'].append(alert.to_dict())
                    self.mc.set(batch_key.encode(), batch_data, expire=window)
                    return None  # Don't send yet
                else:
                    # Start new batch
                    batch_data = {
                        'started': time.time(),
                        'alerts': [alert.to_dict()]
                    }
                    self.mc.set(batch_key.encode(), batch_data, expire=window)
                    
                    # Check if batch window expired
                    if time.time() - batch_data['started'] >= window:
                        # Send batched alerts
                        alerts = [Alert(**a) for a in batch_data['alerts']]
                        self.mc.delete(batch_key.encode())
                        return alerts
                        
            except Exception as e:
                logger.error(f"Batching error: {e}")
        else:
            # Local batching
            if batch_key not in self.local_batches:
                self.local_batches[batch_key] = {
                    'started': time.time(),
                    'alerts': []
                }
            
            batch = self.local_batches[batch_key]
            batch['alerts'].append(alert)
            
            if time.time() - batch['started'] >= window:
                # Send batch
                alerts = batch['alerts'].copy()
                del self.local_batches[batch_key]
                return alerts
        
        return None
    
    async def _record_alert(self, alert: Alert):
        """Record alert was sent"""
        # Record in history
        history_key = f"alert:history:{alert.alert_id}"
        
        if self.available and self.mc:
            try:
                self.mc.set(
                    history_key.encode(),
                    alert.to_dict(),
                    expire=86400  # Keep for 24 hours
                )
            except Exception as e:
                logger.error(f"Failed to record alert: {e}")
    
    def _update_type_metrics(self, alert_type: str, action: str):
        """Update metrics by alert type"""
        if alert_type not in self.metrics['by_type']:
            self.metrics['by_type'][alert_type] = {
                'sent': 0, 'throttled': 0, 'batched': 0, 'deduplicated': 0
            }
        self.metrics['by_type'][alert_type][action] = \
            self.metrics['by_type'][alert_type].get(action, 0) + 1
    
    def _update_priority_metrics(self, priority: int, action: str):
        """Update metrics by priority"""
        priority_str = f"priority_{priority}"
        if priority_str not in self.metrics['by_priority']:
            self.metrics['by_priority'][priority_str] = {
                'sent': 0, 'throttled': 0
            }
        self.metrics['by_priority'][priority_str][action] = \
            self.metrics['by_priority'][priority_str].get(action, 0) + 1
    
    async def get_alert_history(self, 
                               user_id: Optional[str] = None,
                               alert_type: Optional[AlertType] = None,
                               hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get alert history
        
        Args:
            user_id: Filter by user
            alert_type: Filter by type
            hours: Hours of history to retrieve
            
        Returns:
            List of alert records
        """
        # This would need additional indexing in production
        # For now, return empty list
        return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get throttler metrics"""
        total = self.metrics['sent'] + self.metrics['throttled']
        
        return {
            'total_processed': total,
            'sent': self.metrics['sent'],
            'throttled': self.metrics['throttled'],
            'batched': self.metrics['batched'],
            'deduplicated': self.metrics['deduplicated'],
            'throttle_rate': (self.metrics['throttled'] / total * 100) if total > 0 else 0,
            'by_type': self.metrics['by_type'],
            'by_priority': self.metrics['by_priority'],
            'backend': 'memcached' if self.available else 'local'
        }
    
    async def reset_throttle(self, 
                            user_id: Optional[str] = None,
                            alert_type: Optional[AlertType] = None):
        """Reset throttle for user or type"""
        pattern = f"alert:*"
        if user_id:
            pattern += f":{user_id}"
        if alert_type:
            pattern += f":{alert_type.value}"
        
        # Note: Memcached doesn't support pattern deletion
        # In production, maintain an index of keys
        logger.info(f"Reset throttle requested for pattern: {pattern}")
    
    def close(self):
        """Close connection to Memcached"""
        if self.mc:
            try:
                self.mc.close()
            except:
                pass

# Global instance
_alert_throttler = None

def get_alert_throttler() -> AlertThrottler:
    """Get or create global alert throttler instance"""
    global _alert_throttler
    if _alert_throttler is None:
        _alert_throttler = AlertThrottler()
    return _alert_throttler