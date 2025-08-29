"""
AlertManager Adapter for Breaking Circular Dependencies.

This adapter wraps the existing AlertManager to implement the new interfaces
and eliminate circular dependencies by using the service coordinator.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from ..core.interfaces.signal_processing import IEventSubscriber
from ..core.coordination import ServiceCoordinator, Event, EventType

if TYPE_CHECKING:
    from .alert_manager import AlertManager


class AlertManagerAdapter(IEventSubscriber):
    """
    Adapter that wraps AlertManager to eliminate circular dependencies.
    
    This adapter:
    1. Subscribes to signal generation events
    2. Processes alerts without requiring direct service dependencies
    3. Publishes alert completion events
    """
    
    def __init__(
        self,
        alert_manager: 'AlertManager',
        coordinator: ServiceCoordinator,
        logger: Optional[logging.Logger] = None
    ):
        self.alert_manager = alert_manager
        self.coordinator = coordinator
        self.logger = logger or logging.getLogger(__name__)
    
    # IEventSubscriber implementation
    
    def get_subscribed_events(self) -> List[str]:
        """Get list of event types this subscriber handles."""
        return [
            EventType.SIGNAL_GENERATED.value,
            EventType.ALERT_TRIGGERED.value,
            EventType.HEALTH_CHECK.value
        ]
    
    async def handle_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        source_service: str
    ) -> None:
        """Handle incoming events."""
        try:
            if event_type == EventType.SIGNAL_GENERATED.value:
                await self._handle_signal_generated(event_data, source_service)
            elif event_type == EventType.ALERT_TRIGGERED.value:
                await self._handle_alert_triggered(event_data, source_service)
            elif event_type == EventType.HEALTH_CHECK.value:
                await self._handle_health_check(event_data, source_service)
        except Exception as e:
            self.logger.error(f"Error handling event {event_type}: {e}")
    
    # Event handlers
    
    async def _handle_signal_generated(self, event_data: Dict[str, Any], source_service: str) -> None:\n        \"\"\"Handle signal generated event by processing alerts.\"\"\"\n        symbol = event_data.get('symbol')\n        signal_data = event_data.get('signal_data')\n        \n        if not symbol or not signal_data:\n            self.logger.warning(\"Invalid signal generated event data\")\n            return\n        \n        try:\n            # Process the signal through AlertManager\n            await self._process_signal_alert(symbol, signal_data)\n            \n            # Publish alert processed event\n            await self._publish_alert_processed(symbol, signal_data)\n            \n        except Exception as e:\n            self.logger.error(f\"Error processing signal alert for {symbol}: {e}\")\n    \n    async def _handle_alert_triggered(self, event_data: Dict[str, Any], source_service: str) -> None:\n        \"\"\"Handle manually triggered alert events.\"\"\"\n        message = event_data.get('message')\n        level = event_data.get('level', 'INFO')\n        context = event_data.get('context', 'MANUAL')\n        metadata = event_data.get('metadata', {})\n        \n        if not message:\n            self.logger.warning(\"Invalid alert triggered event - no message\")\n            return\n        \n        try:\n            # Send the alert using AlertManager\n            await self.alert_manager.send_alert(message, level, context, metadata)\n            self.logger.debug(f\"Processed manual alert: {message}\")\n            \n        except Exception as e:\n            self.logger.error(f\"Error processing manual alert: {e}\")\n    \n    async def _handle_health_check(self, event_data: Dict[str, Any], source_service: str) -> None:\n        \"\"\"Handle health check events.\"\"\"\n        # Return basic health status\n        health_data = {\n            'service': 'alert_manager',\n            'status': 'healthy',\n            'timestamp': datetime.now().isoformat(),\n            'handlers_count': len(getattr(self.alert_manager, 'handlers', [])),\n            'last_alert': getattr(self.alert_manager, 'last_alert_time', None)\n        }\n        \n        # Publish health status\n        await self.coordinator.publish_event(Event(\n            event_type=EventType.HEALTH_CHECK,\n            source_service=\"alert_manager\",\n            target_services=[\"health_monitor\"],\n            data=health_data\n        ))\n    \n    # Internal methods\n    \n    async def _process_signal_alert(self, symbol: str, signal_data: Dict[str, Any]) -> None:\n        \"\"\"Process a signal alert using the wrapped AlertManager.\"\"\"\n        \n        signal_type = signal_data.get('signal_type')\n        confluence_score = signal_data.get('confluence_score', 0)\n        confidence = signal_data.get('confidence', 0)\n        \n        if signal_type == 'NEUTRAL':\n            return  # Don't send alerts for neutral signals\n        \n        # Format alert message\n        message = self._format_signal_alert_message(symbol, signal_data)\n        \n        # Determine alert level based on confidence\n        if confidence >= 0.8:\n            level = 'HIGH'\n        elif confidence >= 0.6:\n            level = 'MEDIUM'\n        else:\n            level = 'LOW'\n        \n        # Create metadata\n        metadata = {\n            'symbol': symbol,\n            'signal_type': signal_type,\n            'confluence_score': confluence_score,\n            'confidence': confidence,\n            'timestamp': signal_data.get('timestamp'),\n            'entry_price': signal_data.get('entry_price'),\n            'stop_loss': signal_data.get('stop_loss'),\n            'take_profit': signal_data.get('take_profit')\n        }\n        \n        # Send alert through AlertManager\n        await self.alert_manager.send_alert(\n            message=message,\n            level=level,\n            context='SIGNAL',\n            metadata=metadata\n        )\n        \n        self.logger.info(f\"Processed {signal_type} alert for {symbol} (confidence: {confidence:.2f})\")\n    \n    def _format_signal_alert_message(self, symbol: str, signal_data: Dict[str, Any]) -> str:\n        \"\"\"Format signal data into an alert message.\"\"\"\n        signal_type = signal_data.get('signal_type')\n        confluence_score = signal_data.get('confluence_score', 0)\n        confidence = signal_data.get('confidence', 0)\n        entry_price = signal_data.get('entry_price')\n        \n        # Base message\n        message = f\"🚨 {signal_type} SIGNAL - {symbol}\\n\"\n        message += f\"📊 Confluence Score: {confluence_score:.2f}\\n\"\n        message += f\"🎯 Confidence: {confidence:.1%}\\n\"\n        \n        if entry_price:\n            message += f\"💰 Entry Price: ${entry_price:.4f}\\n\"\n        \n        # Add trade parameters if available\n        stop_loss = signal_data.get('stop_loss')\n        take_profit = signal_data.get('take_profit')\n        \n        if stop_loss and take_profit:\n            message += f\"🛑 Stop Loss: ${stop_loss:.4f}\\n\"\n            message += f\"🎯 Take Profit: ${take_profit:.4f}\\n\"\n            \n            # Calculate risk/reward\n            if entry_price:\n                if signal_type == 'BUY':\n                    risk = abs(entry_price - stop_loss)\n                    reward = abs(take_profit - entry_price)\n                else:\n                    risk = abs(stop_loss - entry_price)\n                    reward = abs(entry_price - take_profit)\n                \n                if risk > 0:\n                    rr_ratio = reward / risk\n                    message += f\"⚖️ Risk/Reward: 1:{rr_ratio:.2f}\\n\"\n        \n        # Add timestamp\n        timestamp = signal_data.get('timestamp')\n        if timestamp:\n            message += f\"🕐 Time: {timestamp}\\n\"\n        \n        # Add emoji based on signal type\n        if signal_type == 'BUY':\n            message = \"📈 \" + message\n        elif signal_type == 'SELL':\n            message = \"📉 \" + message\n        \n        return message\n    \n    async def _publish_alert_processed(self, symbol: str, signal_data: Dict[str, Any]) -> None:\n        \"\"\"Publish alert processed event.\"\"\"\n        await self.coordinator.publish_event(Event(\n            event_type=EventType.ALERT_TRIGGERED,\n            source_service=\"alert_manager\",\n            target_services=[\"metrics_tracker\"],\n            data={\n                \"symbol\": symbol,\n                \"alert_type\": \"signal_alert\",\n                \"signal_data\": signal_data,\n                \"processed_at\": datetime.now().isoformat()\n            }\n        ))\n    \n    # Convenience methods for external API compatibility\n    \n    async def send_manual_alert(\n        self, \n        message: str, \n        level: str = 'INFO',\n        context: str = 'MANUAL', \n        metadata: Optional[Dict[str, Any]] = None\n    ) -> None:\n        \"\"\"Send a manual alert through the event system.\"\"\"\n        await self.coordinator.publish_event(Event(\n            event_type=EventType.ALERT_TRIGGERED,\n            source_service=\"external\",\n            target_services=[\"alert_manager\"],\n            data={\n                \"message\": message,\n                \"level\": level,\n                \"context\": context,\n                \"metadata\": metadata or {}\n            }\n        ))