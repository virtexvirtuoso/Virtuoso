from src.utils.task_tracker import create_tracked_task
"""WebSocket handler for market data acquisition.

This module provides WebSocket functionality for:
- Connecting to exchanges
- Subscribing to market data
- Handling messages and errors
- Heartbeat monitoring
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Set, Callable
import aiohttp
import time

from src.core.validation.models import ValidationResult, ValidationContext
from src.core.error.models import ErrorContext, ErrorSeverity
from .error_handler import SimpleErrorHandler
from src.core.exchanges.bybit import BybitExchange

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handle WebSocket connections and data."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        error_handler: Optional[Any] = None,
        validation_service: Optional[Any] = None,
        metrics_manager: Optional[Any] = None,
        alert_manager: Optional[Any] = None
    ):
        """Initialize WebSocket handler.
        
        Args:
            config: Configuration dictionary
            error_handler: Optional error handler instance
            validation_service: Optional validation service instance
            metrics_manager: Optional metrics manager instance
            alert_manager: Optional alert manager instance
        """
        self.config = config
        self.error_handler = error_handler
        self.validation_service = validation_service
        self.metrics_manager = metrics_manager
        self.alert_manager = alert_manager
        
        # Get kline configuration
        self.kline_config = self.config['market_data']['klines']
        self.timeframes = self.kline_config['timeframes']
        
        # Initialize state
        self.subscriptions = {}
        self.handlers = {}
        self.last_heartbeat = {}
        self.heartbeat_interval = self.config['websocket']['heartbeat_interval']
        self.heartbeat_timeout = self.config['websocket']['heartbeat_timeout']
        
        # Initialize exchange
        self.exchange = None
        
    async def initialize(self) -> bool:
        """Initialize WebSocket handler."""
        try:
            # Get exchange instance
            self.exchange = await BybitExchange.get_instance(self.config, self.error_handler)
            
            # Connect to WebSocket
            if not await self.exchange.connect_ws():
                logger.error("Failed to connect to WebSocket")
                return False
                
            # Start heartbeat monitoring
            create_tracked_task(self._monitor_heartbeats(), name="auto_tracked_task")
            
            logger.info("WebSocket handler initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket handler: {str(e)}")
            return False
            
    async def _monitor_heartbeats(self):
        """Monitor WebSocket heartbeats."""
        while True:
            try:
                now = time.time()
                for channel, last_beat in self.last_heartbeat.items():
                    if now - last_beat > self.heartbeat_timeout:
                        logger.warning(f"Channel {channel} heartbeat timeout")
                        await self._handle_heartbeat_timeout(channel)
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error monitoring heartbeats: {str(e)}")
                await asyncio.sleep(1)
                
    async def _update_heartbeat(self, channel: str):
        """Update last heartbeat time for a channel."""
        self.last_heartbeat[channel] = time.time()
        
    async def connect(self) -> bool:
        """Connect to WebSocket API."""
        return await self.exchange.connect_ws()
        
    async def disconnect(self) -> None:
        """Disconnect from WebSocket API."""
        if self.exchange:
            await self.exchange.close()
            
    async def subscribe(self, channels: List[str]) -> bool:
        """Subscribe to WebSocket channels.
        
        Args:
            channels: List of channel names to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            success = True
            for channel in channels:
                if not await self.exchange.ws_subscribe(channel, self._message_handler):
                    success = False
                    logger.error(f"Failed to subscribe to channel: {channel}")
                else:
                    self.subscriptions[channel] = True
                    self.last_heartbeat[channel] = time.time()
                    logger.info(f"Subscribed to channel: {channel}")
            return success
        except Exception as e:
            logger.error(f"Error subscribing to channels: {str(e)}")
            return False
            
    async def unsubscribe(self, channels: List[str]) -> bool:
        """Unsubscribe from WebSocket channels.
        
        Args:
            channels: List of channel names to unsubscribe from
            
        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        try:
            success = True
            for channel in channels:
                if not await self.exchange.ws_unsubscribe(channel):
                    success = False
                    logger.error(f"Failed to unsubscribe from channel: {channel}")
                else:
                    if channel in self.subscriptions:
                        del self.subscriptions[channel]
                    if channel in self.last_heartbeat:
                        del self.last_heartbeat[channel]
                    logger.info(f"Unsubscribed from channel: {channel}")
            return success
        except Exception as e:
            logger.error(f"Error unsubscribing from channels: {str(e)}")
            return False
            
    def register_handler(self, channel: str, handler: Callable) -> None:
        """Register a message handler for a channel."""
        self.handlers[channel] = handler
        
    async def _message_handler(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        try:
            if 'topic' in message:
                topic = message['topic']
                if topic in self.handlers:
                    await self.handlers[topic](message)
                await self._update_heartbeat(topic)
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            
    async def _handle_heartbeat_timeout(self, channel: str) -> None:
        """Handle heartbeat timeout for a channel."""
        try:
            logger.warning(f"Attempting to resubscribe to channel {channel}")
            if await self.unsubscribe([channel]) and await self.subscribe([channel]):
                logger.info(f"Successfully resubscribed to channel {channel}")
            else:
                logger.error(f"Failed to resubscribe to channel {channel}")
        except Exception as e:
            logger.error(f"Error handling heartbeat timeout: {str(e)}")
            
    async def subscribe_to_top_symbols(self, number_of_symbols: int) -> bool:
        """Subscribe to top traded symbols.
        
        Args:
            number_of_symbols: Number of top symbols to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            # Get top symbols
            symbols = await self.exchange.fetch_top_symbols(number_of_symbols)
            if not symbols:
                logger.error("Failed to fetch top symbols")
                return False
                
            # Subscribe to channels for each symbol
            channels = []
            for symbol in symbols:
                for timeframe in self.timeframes:
                    channels.append(f"kline.{timeframe}.{symbol}")
                channels.extend([
                    f"orderbook.{symbol}",
                    f"trade.{symbol}",
                    f"ticker.{symbol}"
                ])
                
            return await self.subscribe(channels)
            
        except Exception as e:
            logger.error(f"Error subscribing to top symbols: {str(e)}")
            return False
            
    async def is_healthy(self) -> bool:
        """Check if WebSocket connection is healthy."""
        if not self.exchange:
            return False
            
        try:
            # Check WebSocket connection
            if not self.exchange.ws_connected:
                return False
                
            # Check heartbeats
            now = time.time()
            for channel, last_beat in self.last_heartbeat.items():
                if now - last_beat > self.heartbeat_timeout:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking WebSocket health: {str(e)}")
            return False