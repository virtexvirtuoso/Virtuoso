"""
Alert Throttler Component - Manages deduplication and rate limiting
Part of the AlertManager refactoring to reduce complexity from 4,716 to ~600 lines
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertThrottler:
    """
    Manages alert throttling, deduplication, and rate limiting.
    Simplified from the original complex throttling system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AlertThrottler component.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Cooldown periods for different alert types (seconds)
        self.cooldown_periods = config.get('cooldowns', {
            'system': 60,      # System alerts - 1 minute
            'signal': 300,     # Trading signals - 5 minutes  
            'whale': 180,      # Whale alerts - 3 minutes
            'liquidation': 120, # Liquidation alerts - 2 minutes
            'default': 60      # Default cooldown
        })
        
        # Deduplication window (seconds)
        self.dedup_window = config.get('dedup_window', 300)  # 5 minutes
        
        # Maximum entries to prevent memory growth
        self.max_entries = config.get('max_entries', 10000)
        
        # Storage for tracking sent alerts
        self._sent_alerts = {}      # alert_key -> timestamp
        self._content_hashes = {}   # hash -> timestamp
        self._alert_counts = defaultdict(int)  # alert_type -> count
        
        # Cleanup tracking
        self._last_cleanup = time.time()
        self._cleanup_interval = config.get('cleanup_interval', 3600)  # 1 hour
        
    def should_send(self, 
                   alert_key: str, 
                   alert_type: str = 'default',
                   content: Optional[str] = None) -> bool:
        """
        Check if alert should be sent based on throttling rules.
        
        Args:
            alert_key: Unique key for the alert (e.g., 'BTC/USDT_whale_alert')
            alert_type: Type of alert for cooldown lookup
            content: Optional content for deduplication
            
        Returns:
            True if alert should be sent, False if throttled
        """
        current_time = time.time()
        
        # Check cooldown
        if not self._check_cooldown(alert_key, alert_type, current_time):
            logger.debug(f"Alert {alert_key} throttled by cooldown")
            return False
            
        # Check for duplicate content
        if content and self.is_duplicate(content, alert_type):
            logger.debug(f"Alert {alert_key} throttled as duplicate")
            return False
            
        # Periodic cleanup to prevent memory growth
        if current_time - self._last_cleanup > self._cleanup_interval:
            self.cleanup_expired()
            
        return True
        
    def mark_sent(self, 
                 alert_key: str, 
                 alert_type: str = 'default',
                 content: Optional[str] = None):
        """
        Record alert as sent for future throttling decisions.
        
        Args:
            alert_key: Unique key for the alert
            alert_type: Type of alert
            content: Optional content for deduplication
        """
        current_time = time.time()
        
        # Record alert as sent
        self._sent_alerts[alert_key] = current_time
        
        # Record content hash for deduplication
        if content:
            content_hash = self._generate_hash(content)
            self._content_hashes[content_hash] = current_time
            
        # Update counts
        self._alert_counts[alert_type] += 1
        
        logger.debug(f"Marked alert {alert_key} as sent at {current_time}")
        
        # Prevent memory growth
        if len(self._sent_alerts) > self.max_entries:
            self._emergency_cleanup()
            
    def is_duplicate(self, 
                    content: str, 
                    alert_type: str = 'default',
                    window: Optional[int] = None) -> bool:
        """
        Check if content is duplicate within the deduplication window.
        
        Args:
            content: Alert content to check
            alert_type: Type of alert (affects window size)
            window: Optional custom window in seconds
            
        Returns:
            True if content is duplicate within window
        """
        if not content:
            return False
            
        content_hash = self._generate_hash(content)
        current_time = time.time()
        
        # Use custom window or default
        dedup_window = window or self.dedup_window
        
        # Check if this hash was seen recently
        if content_hash in self._content_hashes:
            sent_time = self._content_hashes[content_hash]
            if current_time - sent_time < dedup_window:
                return True
                
        return False
        
    def _check_cooldown(self, 
                       alert_key: str, 
                       alert_type: str, 
                       current_time: float) -> bool:
        """
        Check if alert is within cooldown period.
        
        Args:
            alert_key: Unique alert key
            alert_type: Alert type for cooldown lookup
            current_time: Current timestamp
            
        Returns:
            True if outside cooldown period (can send)
        """
        if alert_key not in self._sent_alerts:
            return True
            
        last_sent = self._sent_alerts[alert_key]
        cooldown = self.cooldown_periods.get(alert_type, self.cooldown_periods['default'])
        
        return (current_time - last_sent) >= cooldown
        
    def _generate_hash(self, content: str) -> str:
        """
        Generate hash for content deduplication.
        
        Args:
            content: Content to hash
            
        Returns:
            Content hash string
        """
        # Normalize content for hashing
        normalized = content.strip().lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
        
    def cleanup_expired(self):
        """
        Remove expired entries to prevent memory growth.
        """
        current_time = time.time()
        
        # Clean up sent alerts
        expired_alerts = []
        for alert_key, sent_time in self._sent_alerts.items():
            # Remove alerts older than the maximum cooldown period
            max_cooldown = max(self.cooldown_periods.values())
            if current_time - sent_time > max_cooldown:
                expired_alerts.append(alert_key)
                
        for alert_key in expired_alerts:
            del self._sent_alerts[alert_key]
            
        # Clean up content hashes
        expired_hashes = []
        for content_hash, sent_time in self._content_hashes.items():
            if current_time - sent_time > self.dedup_window:
                expired_hashes.append(content_hash)
                
        for content_hash in expired_hashes:
            del self._content_hashes[content_hash]
            
        # Update cleanup timestamp
        self._last_cleanup = current_time
        
        if expired_alerts or expired_hashes:
            logger.debug(f"Cleaned up {len(expired_alerts)} alerts and {len(expired_hashes)} hashes")
            
    def _emergency_cleanup(self):
        """
        Emergency cleanup when storage exceeds limits.
        Removes oldest 50% of entries.
        """
        logger.warning("Emergency cleanup triggered - too many stored alerts")
        
        # Sort by timestamp and remove oldest 50%
        sorted_alerts = sorted(self._sent_alerts.items(), key=lambda x: x[1])
        keep_count = len(sorted_alerts) // 2
        
        # Keep only newest 50%
        self._sent_alerts = dict(sorted_alerts[keep_count:])
        
        # Same for content hashes
        sorted_hashes = sorted(self._content_hashes.items(), key=lambda x: x[1])
        keep_count = len(sorted_hashes) // 2
        self._content_hashes = dict(sorted_hashes[keep_count:])
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get throttling statistics.
        
        Returns:
            Dictionary with throttling stats
        """
        return {
            'total_alert_keys': len(self._sent_alerts),
            'total_content_hashes': len(self._content_hashes),
            'alert_counts_by_type': dict(self._alert_counts),
            'last_cleanup': self._last_cleanup,
            'cooldown_periods': self.cooldown_periods.copy(),
            'dedup_window': self.dedup_window
        }
        
    def reset_stats(self):
        """Reset all throttling data (use with caution)."""
        self._sent_alerts.clear()
        self._content_hashes.clear()
        self._alert_counts.clear()
        self._last_cleanup = time.time()
        logger.info("Alert throttling stats reset")
        
    def can_send_alert_type(self, alert_type: str) -> bool:
        """
        Quick check if alert type has any active cooldowns.
        
        Args:
            alert_type: Type of alert to check
            
        Returns:
            True if no alerts of this type are in cooldown
        """
        current_time = time.time()
        cooldown = self.cooldown_periods.get(alert_type, self.cooldown_periods['default'])
        
        # Check if any alerts of this type are still in cooldown
        for alert_key, sent_time in self._sent_alerts.items():
            if alert_type in alert_key and (current_time - sent_time) < cooldown:
                return False
                
        return True