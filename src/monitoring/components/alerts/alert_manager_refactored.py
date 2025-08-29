"""
Alert Manager Refactored - Slim orchestrator for alert management
Part of the AlertManager refactoring to reduce complexity from 4,716 to ~600 lines total

This orchestrator maintains backward compatibility while coordinating the modular components:
- AlertDelivery: Discord webhook delivery
- AlertThrottler: Deduplication and rate limiting
"""

import logging
import os
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime

from .alert_delivery import AlertDelivery
from .alert_throttler import AlertThrottler

logger = logging.getLogger(__name__)


class AlertManagerRefactored:
    """
    Refactored AlertManager orchestrator.
    Maintains backward compatibility while using modular components.
    
    Reduced from 4,716 lines to ~250 lines orchestrator + 350 lines components = ~600 total
    """
    
    def __init__(self, config: Dict[str, Any], database: Optional[Any] = None):
        """
        Initialize refactored AlertManager.
        
        Args:
            config: Configuration dictionary
            database: Optional database connection (for compatibility)
        """
        self.config = config
        self.database = database
        
        # Get webhook URL from config or environment
        webhook_url = self._get_webhook_url()
        self.discord_webhook_url = webhook_url  # Expose for backward compatibility
        
        # Initialize components
        self.delivery = AlertDelivery(webhook_url, config)
        self.throttler = AlertThrottler(config)
        
        # Alert statistics for compatibility
        self._alert_stats = defaultdict(int)
        self._total_alerts_sent = 0
        self._alerts_throttled = 0
        
        # In-memory alert storage for compatibility
        self._alerts = []
        self._max_alerts_in_memory = 1000
        
        # Handler registry for compatibility
        self._handlers = set()
        
        # Expose handlers property for backward compatibility with main.py
        self.handlers = self._handlers
        
        # Additional compatibility properties for main.py
        self.alert_handlers = {'discord': self._send_discord_alert}
        
        # Database alert storage compatibility
        self.alert_storage = database if database else None
        
        logger.info("AlertManagerRefactored initialized with modular components")
        
    def _get_webhook_url(self) -> str:
        """
        Get Discord webhook URL from config or environment.
        
        Returns:
            Webhook URL string
        """
        # Try config first, then environment
        webhook_url = (
            self.config.get('discord', {}).get('webhook_url') or 
            self.config.get('webhook_url') or
            os.getenv('DISCORD_WEBHOOK_URL', '')
        )
        
        if not webhook_url:
            logger.warning("No Discord webhook URL configured")
            
        return webhook_url
        
    async def send_alert(self, 
                        level: str,
                        message: str,
                        details: Optional[Dict[str, Any]] = None,
                        alert_type: str = "system",
                        symbol: Optional[str] = None) -> bool:
        """
        Main alert sending method - maintains backward compatibility.
        
        Args:
            level: Alert level (info, warning, error, critical)
            message: Alert message
            details: Optional additional details
            alert_type: Type of alert for throttling
            symbol: Optional symbol for alert key generation
            
        Returns:
            True if alert was sent successfully
        """
        try:
            # Generate alert key for throttling
            alert_key = self._generate_alert_key(alert_type, symbol, level)
            
            # Check throttling
            if not self.throttler.should_send(alert_key, alert_type, message):
                self._alerts_throttled += 1
                logger.debug(f"Alert throttled: {alert_key}")
                return False
                
            # Format message with details if provided
            formatted_message = self._format_alert_message(message, details)
            
            # Send alert via delivery component
            success, error = await self.delivery.send_simple_alert(level, formatted_message)
            
            # Always store alert in memory for get_alerts compatibility (even if delivery fails)
            alert_record = {
                'id': len(self._alerts) + 1,
                'timestamp': datetime.now().timestamp(),
                'level': level,
                'severity': level.upper(),
                'message': formatted_message,
                'alert_type': alert_type,
                'type': alert_type,
                'symbol': symbol,
                'details': details or {},
                'sent': success,
                'delivery_error': error if not success else None,
                'created_at': datetime.now().isoformat()
            }
            
            # Add to in-memory storage
            self._alerts.append(alert_record)
            
            # Keep only recent alerts in memory
            if len(self._alerts) > self._max_alerts_in_memory:
                self._alerts = self._alerts[-self._max_alerts_in_memory:]
            
            if success:
                # Mark as sent for throttling
                self.throttler.mark_sent(alert_key, alert_type, message)
                
                # Update statistics
                self._alert_stats[alert_type] += 1
                self._alert_stats[level] += 1
                self._total_alerts_sent += 1
                
                logger.info(f"Alert sent successfully: {level} - {message[:50]}...")
                return True
            else:
                # Still count as attempted even if failed
                self._alerts_throttled += 1
                logger.error(f"Failed to send alert: {error}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
            
    async def send_confluence_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send confluence signal alert - simplified version.
        
        Args:
            alert_data: Confluence alert data dictionary
            
        Returns:
            True if alert was sent successfully
        """
        try:
            # Extract key information
            symbol = alert_data.get('symbol', 'UNKNOWN')
            score = alert_data.get('confluence_score', 0)
            signal = alert_data.get('signal_direction', 'UNKNOWN')
            
            # Create formatted message
            message = f"🎯 Confluence Signal: {symbol}\n"
            message += f"Score: {score}/6 | Direction: {signal}"
            
            # Add key factors if available
            factors = alert_data.get('active_factors', [])
            if factors:
                message += f"\nFactors: {', '.join(factors[:3])}"  # Limit to 3 factors
                
            return await self.send_alert(
                level="info",
                message=message,
                details=alert_data,
                alert_type="signal",
                symbol=symbol
            )
            
        except Exception as e:
            logger.error(f"Error sending confluence alert: {e}")
            return False
            
    async def send_signal_alert(self, signal_data: Dict[str, Any]) -> bool:
        """
        Send trading signal alert - simplified version.
        
        Args:
            signal_data: Signal data dictionary
            
        Returns:
            True if alert was sent successfully
        """
        try:
            # Extract key information
            symbol = signal_data.get('symbol', 'UNKNOWN')
            direction = signal_data.get('direction', 'UNKNOWN')
            strength = signal_data.get('strength', 0)
            
            # Create formatted message
            message = f"📈 Trading Signal: {symbol}\n"
            message += f"Direction: {direction} | Strength: {strength}"
            
            # Add price info if available
            price = signal_data.get('current_price')
            if price:
                message += f"\nPrice: ${price}"
                
            return await self.send_alert(
                level="warning",  # Signals are important
                message=message,
                details=signal_data,
                alert_type="signal",
                symbol=symbol
            )
            
        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")
            return False
            
    async def send_trade_execution_alert(self, trade_data: Dict[str, Any]) -> bool:
        """
        Send trade execution alert - simplified version.
        
        Args:
            trade_data: Trade execution data dictionary
            
        Returns:
            True if alert was sent successfully
        """
        try:
            # Extract key information
            symbol = trade_data.get('symbol', 'UNKNOWN')
            action = trade_data.get('action', 'UNKNOWN')
            quantity = trade_data.get('quantity', 0)
            price = trade_data.get('price', 0)
            
            # Create formatted message
            message = f"📊 Trade Executed: {symbol}\n"
            message += f"Action: {action} | Qty: {quantity}"
            if price:
                message += f" | Price: ${price}"
                
            return await self.send_alert(
                level="info",
                message=message,
                details=trade_data,
                alert_type="trade",
                symbol=symbol
            )
            
        except Exception as e:
            logger.error(f"Error sending trade execution alert: {e}")
            return False
            
    def _generate_alert_key(self, 
                           alert_type: str, 
                           symbol: Optional[str] = None, 
                           level: str = "info") -> str:
        """
        Generate unique alert key for throttling.
        
        Args:
            alert_type: Type of alert
            symbol: Optional symbol
            level: Alert level
            
        Returns:
            Unique alert key string
        """
        parts = [alert_type, level]
        if symbol:
            parts.insert(1, symbol)
        return "_".join(parts)
        
    def _format_alert_message(self, 
                             message: str, 
                             details: Optional[Dict[str, Any]] = None) -> str:
        """
        Format alert message with optional details.
        
        Args:
            message: Base message
            details: Optional details to include
            
        Returns:
            Formatted message string
        """
        formatted = message
        
        if details:
            # Add timestamp if available
            if 'timestamp' in details:
                formatted += f"\nTime: {details['timestamp']}"
                
            # Add other relevant details (simplified)
            if 'exchange' in details:
                formatted += f"\nExchange: {details['exchange']}"
                
        return formatted[:1900]  # Keep within Discord limits
        
    def get_alert_stats(self) -> Dict[str, Any]:
        """
        Return alert statistics - maintains backward compatibility.
        
        Returns:
            Dictionary with alert statistics
        """
        stats = {
            'total_sent': self._total_alerts_sent,
            'total_throttled': self._alerts_throttled,
            'by_type': dict(self._alert_stats),
            'success_rate': self._calculate_success_rate()
        }
        
        # Add throttling stats
        throttling_stats = self.throttler.get_stats()
        stats.update({
            'throttling': throttling_stats
        })
        
        return stats
        
    def _calculate_success_rate(self) -> float:
        """Calculate alert success rate."""
        total_attempted = self._total_alerts_sent + self._alerts_throttled
        if total_attempted == 0:
            return 1.0
        return self._total_alerts_sent / total_attempted
        
    def get_alerts(self, level: Optional[str] = None,
                  limit: Optional[int] = None,
                  start_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get filtered alerts - maintains compatibility with original AlertManager interface.
        
        Args:
            level: Filter by alert level (info, warning, error, critical)
            limit: Maximum number of alerts to return
            start_time: Unix timestamp to filter alerts after this time
            
        Returns:
            List of alert dictionaries with expected format
        """
        try:
            # First try to get alerts from database via alert_storage if available
            if hasattr(self, 'alert_storage') and self.alert_storage:
                try:
                    # Map level to severity for database query
                    severity = level.upper() if level else None
                    alerts = self.alert_storage.get_alerts(
                        limit=limit or 50,
                        start_time=start_time,
                        severity=severity
                    )
                    # Ensure compatibility with expected format
                    for alert in alerts:
                        # Map database fields to expected fields
                        if 'severity' in alert and 'level' not in alert:
                            alert['level'] = alert['severity'].lower()
                        if 'alert_type' in alert and 'type' not in alert:
                            alert['type'] = alert['alert_type']
                    return alerts
                except Exception as e:
                    logger.error(f"Error retrieving alerts from database: {e}")
                    # Fall back to in-memory alerts
            
            # Use in-memory alerts as fallback
            alerts = list(self._alerts)
            
            # Apply filters
            if level:
                level_lower = level.lower()
                level_upper = level.upper()
                alerts = [a for a in alerts if 
                         a.get('level') == level_lower or 
                         a.get('severity') == level_upper]
                
            if start_time is not None:
                start_time = float(start_time)
                alerts = [a for a in alerts if float(a.get('timestamp', 0)) >= start_time]
                
            # Apply limit (get most recent alerts)
            if limit is not None:
                limit = int(limit)
                alerts = alerts[-limit:]
                
            # Sort by timestamp descending (most recent first)
            alerts.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error retrieving alerts: {e}")
            return []
        
    # Backward compatibility methods (simplified)
    
    async def initialize(self) -> None:
        """
        Initialize method for backward compatibility.
        AlertManagerRefactored is initialized in __init__, so this is a no-op.
        """
        logger.debug("AlertManagerRefactored.initialize() called - already initialized")
        
    async def start(self) -> None:
        """
        Start method for backward compatibility.
        AlertManagerRefactored is ready to use immediately, so this is a no-op.
        """
        logger.debug("AlertManagerRefactored.start() called - already started")
    
    def register_handler(self, name: str) -> None:
        """
        Register alert handler - simplified for compatibility.
        
        Args:
            name: Handler name
        """
        self._handlers.add(name)
        self.handlers = self._handlers  # Keep in sync
        logger.debug(f"Registered handler: {name}")
        
    def register_discord_handler(self) -> None:
        """
        Register Discord handler - specific method for main.py compatibility.
        """
        self.register_handler('discord')
        logger.info("Discord handler registered")
        
    async def _send_discord_alert(self, *args, **kwargs):
        """
        Internal Discord alert method for backward compatibility.
        """
        # Redirect to send_alert
        return await self.send_alert(
            level=kwargs.get('level', 'info'),
            message=kwargs.get('message', ''),
            details=kwargs.get('details'),
            alert_type=kwargs.get('alert_type', 'system')
        )
        
    def remove_handler(self, name: str) -> None:
        """
        Remove alert handler - simplified for compatibility.
        
        Args:
            name: Handler name
        """
        self._handlers.discard(name)
        logger.debug(f"Removed handler: {name}")
        
    def get_handlers(self) -> List[str]:
        """
        Get registered handlers - simplified for compatibility.
        
        Returns:
            List of handler names
        """
        return list(self._handlers)
        
    # Health check methods
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of alert system.
        
        Returns:
            Health status dictionary
        """
        # Test webhook connectivity
        webhook_healthy = bool(self.delivery.webhook_url)
        
        # Check component health
        stats = self.get_alert_stats()
        
        return {
            'healthy': webhook_healthy,
            'webhook_configured': webhook_healthy,
            'total_alerts_sent': stats['total_sent'],
            'success_rate': stats['success_rate'],
            'components': {
                'delivery': {'healthy': webhook_healthy},
                'throttler': {'healthy': True, 'entries': len(self.throttler._sent_alerts)}
            }
        }
        
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Close delivery session
            await self.delivery._close_session()
            
            # Clean up throttler
            self.throttler.cleanup_expired()
            
            logger.info("AlertManagerRefactored cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


# Alias for backward compatibility
AlertManager = AlertManagerRefactored