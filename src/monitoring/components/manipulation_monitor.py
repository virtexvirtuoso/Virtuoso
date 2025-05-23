"""
Manipulation Monitor Component

This module handles market manipulation monitoring functionality including:
- Market manipulation pattern detection
- Alert generation for suspicious activities
- Data storage for analysis
- Statistics and history tracking
"""

import logging
import traceback
from typing import Dict, Any, Optional


class ManipulationMonitor:
    """
    Handles market manipulation monitoring functionality including pattern detection,
    alert generation, and data storage for suspicious market activities.
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
        alert_manager=None,
        manipulation_detector=None,
        database_client=None
    ):
        """
        Initialize ManipulationMonitor.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
            alert_manager: Alert manager instance
            manipulation_detector: Manipulation detector instance
            database_client: Database client instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        self.alert_manager = alert_manager
        self.manipulation_detector = manipulation_detector
        self.database_client = database_client

    async def monitor_manipulation_activity(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """
        Monitor for potential market manipulation patterns.
        
        This method analyzes market data for patterns indicative of coordinated
        or manipulative trading activity using the ManipulationDetector.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data dictionary containing OHLCV, orderbook, trades, etc.
        """
        try:
            # Skip if manipulation detector is not available
            if not self.manipulation_detector:
                self.logger.debug(f"Skipping manipulation monitoring for {symbol}: No manipulation detector")
                return
                
            # Skip if no alert manager available
            if not self.alert_manager:
                self.logger.debug(f"Skipping manipulation monitoring for {symbol}: No alert manager")
                return
                
            # Analyze market data for manipulation patterns
            manipulation_alert = await self.manipulation_detector.analyze_market_data(symbol, market_data)
            
            if manipulation_alert:
                # Send manipulation alert through alert manager
                await self._send_manipulation_alert(symbol, manipulation_alert, market_data)
                
                # Log manipulation detection
                self.logger.warning(f"Manipulation detected for {symbol}: {manipulation_alert.description}")
                
                # Store manipulation activity data if database is available
                if self.database_client:
                    await self._store_manipulation_data(symbol, manipulation_alert)
                    
        except Exception as e:
            self.logger.error(f"Error monitoring manipulation for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _send_manipulation_alert(self, symbol: str, manipulation_alert, market_data: Dict[str, Any]) -> None:
        """
        Send manipulation alert through the alert manager.
        
        Args:
            symbol: Trading pair symbol
            manipulation_alert: ManipulationAlert instance
            market_data: Current market data
        """
        try:
            # Get current price for context
            ticker = market_data.get('ticker', {})
            current_price = float(ticker.get('last', 0))
            
            # Determine alert level based on severity
            alert_level_map = {
                'low': 'info',
                'medium': 'warning', 
                'high': 'warning',
                'critical': 'error'
            }
            alert_level = alert_level_map.get(manipulation_alert.severity, 'info')
            
            # Create severity emoji
            severity_emoji_map = {
                'low': '⚠️',
                'medium': '🔸',
                'high': '🔸',
                'critical': '🚨'
            }
            severity_emoji = severity_emoji_map.get(manipulation_alert.severity, '⚠️')
            
            # Format manipulation type for display
            manipulation_type_display = manipulation_alert.manipulation_type.replace('_', ' ').title()
            
            # Build detailed message
            message_parts = [
                f"{severity_emoji} **Market Manipulation Alert** for {symbol}",
                f"• **Type**: {manipulation_type_display}",
                f"• **Confidence**: {manipulation_alert.confidence_score:.1%}",
                f"• **Severity**: {manipulation_alert.severity.upper()}",
                f"• **Current Price**: ${current_price:,.4f}",
                "",
                f"**Details**:",
                f"• {manipulation_alert.description}",
            ]
            
            # Add specific metrics if available
            metrics = manipulation_alert.metrics
            if metrics:
                if metrics.get('oi_change_15m_pct', 0) != 0:
                    oi_pct = metrics['oi_change_15m_pct'] * 100
                    message_parts.append(f"• OI Change (15m): {oi_pct:+.1f}%")
                    
                if metrics.get('volume_spike_ratio', 0) > 1:
                    volume_ratio = metrics['volume_spike_ratio']
                    message_parts.append(f"• Volume Spike: {volume_ratio:.1f}x average")
                    
                if metrics.get('price_change_15m_pct', 0) != 0:
                    price_pct = metrics['price_change_15m_pct'] * 100
                    message_parts.append(f"• Price Change (15m): {price_pct:+.1f}%")
                    
                if metrics.get('divergence_detected', False):
                    divergence_strength = metrics.get('divergence_strength', 0) * 100
                    message_parts.append(f"• OI-Price Divergence: {divergence_strength:.1f}% strength")
            
            message = "\n".join(message_parts)
            
            # Send alert
            await self.alert_manager.send_alert(
                level=alert_level,
                message=message,
                details={
                    "type": "manipulation_detection",
                    "subtype": manipulation_alert.manipulation_type,
                    "symbol": symbol,
                    "confidence_score": manipulation_alert.confidence_score,
                    "severity": manipulation_alert.severity,
                    "metrics": metrics,
                    "timestamp": manipulation_alert.timestamp
                }
            )
            
            self.logger.info(f"Sent manipulation alert for {symbol}: {manipulation_alert.manipulation_type} "
                           f"(confidence: {manipulation_alert.confidence_score:.1%})")
                           
        except Exception as e:
            self.logger.error(f"Error sending manipulation alert for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _store_manipulation_data(self, symbol: str, manipulation_alert) -> None:
        """
        Store manipulation detection data in database.
        
        Args:
            symbol: Trading pair symbol
            manipulation_alert: ManipulationAlert instance
        """
        try:
            if not self.database_client:
                return
                
            # Prepare data for storage
            manipulation_data = {
                'timestamp': manipulation_alert.timestamp,
                'symbol': symbol,
                'manipulation_type': manipulation_alert.manipulation_type,
                'confidence_score': manipulation_alert.confidence_score,
                'severity': manipulation_alert.severity,
                'description': manipulation_alert.description,
                'metrics': manipulation_alert.metrics
            }
            
            # Store in database
            await self.database_client.store_manipulation_activity(manipulation_data)
            
            self.logger.debug(f"Stored manipulation data for {symbol} in database")
            
        except Exception as e:
            self.logger.error(f"Error storing manipulation data for {symbol}: {str(e)}")

    def get_manipulation_stats(self) -> Dict[str, Any]:
        """
        Get manipulation detection statistics.
        
        Returns:
            Dictionary containing manipulation detection statistics
        """
        try:
            if self.manipulation_detector:
                return self.manipulation_detector.get_stats()
            else:
                return {
                    'total_analyses': 0,
                    'alerts_generated': 0,
                    'manipulation_detected': 0,
                    'false_positives': 0,
                    'avg_confidence': 0.0
                }
        except Exception as e:
            self.logger.error(f"Error getting manipulation stats: {str(e)}")
            return {}

    def get_manipulation_history(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get manipulation detection history.
        
        Args:
            symbol: Optional symbol to filter by
            
        Returns:
            Dictionary containing manipulation detection history
        """
        try:
            if self.manipulation_detector:
                return self.manipulation_detector.get_manipulation_history(symbol)
            else:
                return {}
        except Exception as e:
            self.logger.error(f"Error getting manipulation history: {str(e)}")
            return {}

    def is_manipulation_detector_available(self) -> bool:
        """
        Check if manipulation detector is available.
        
        Returns:
            True if manipulation detector is available, False otherwise
        """
        return self.manipulation_detector is not None

    def is_alert_manager_available(self) -> bool:
        """
        Check if alert manager is available.
        
        Returns:
            True if alert manager is available, False otherwise
        """
        return self.alert_manager is not None

    def is_database_client_available(self) -> bool:
        """
        Check if database client is available.
        
        Returns:
            True if database client is available, False otherwise
        """
        return self.database_client is not None

    def get_component_status(self) -> Dict[str, bool]:
        """
        Get status of all component dependencies.
        
        Returns:
            Dictionary with component availability status
        """
        return {
            'manipulation_detector': self.is_manipulation_detector_available(),
            'alert_manager': self.is_alert_manager_available(),
            'database_client': self.is_database_client_available()
        } 