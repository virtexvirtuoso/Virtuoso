import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable, TYPE_CHECKING, Union, Tuple, Set
from datetime import datetime, timezone, timedelta
import aiohttp
import traceback
from logging import getLogger
import time
from collections import defaultdict, deque
import os
import yaml
import sys
import coloredlogs
from dotenv import load_dotenv
from discord_webhook import DiscordWebhook, DiscordEmbed
import asyncio
import json
import uuid
import subprocess
import hashlib
import textwrap
import random
import requests
import aiofiles
import numpy as np
import pandas as pd

from discord import SyncWebhook, File
from src.utils.serializers import serialize_for_json, prepare_data_for_transmission
from src.utils.data_utils import resolve_price, format_price_string
from src.models.schema import AlertPayload, ConfluenceAlert, SignalDirection
from src.core.reporting.report_manager import ReportManager

if TYPE_CHECKING:
    from monitoring.metrics_manager import MetricsManager

logger = getLogger(__name__)

class AlertManager:
    """Alert manager for monitoring system."""

    def __init__(self, config: Dict[str, Any], database: Optional[Any] = None):
        """Initialize AlertManager.
        
        Args:
            config: Configuration dictionary
            database: Optional database client
        """
        self.config = config
        self.database = database
        self.alerts = []
        self.logger = getLogger(__name__)
        self.handlers = []
        self.alert_handlers = {}
        self.webhook = None
        self.discord_webhook_url = None
        self._client_session = None
        self.buy_threshold = 60.0
        self.sell_threshold = 40.0
        
        # Alert tracking (no longer used for deduplication)
        self._last_alert_times = {}  # Symbol -> timestamp mapping for all alerts 
        self._deduplication_window = 0  # Deduplication disabled (was 5 seconds)
        self._alert_hashes = {}  # Hash -> timestamp mapping for content tracking
        self._last_liquidation_alert = {}  # Dictionary to track last liquidation alerts by symbol
        self._last_large_order_alert = {}  # Dictionary to track last large order alerts by symbol
        self._last_whale_activity_alert = {}  # Dictionary to track last whale activity alerts by symbol
        self._last_alert = {}  # Dictionary to track last alerts by alert key
        
        # DEBUG: New attributes for tracking handler registration issues
        self._initialization_time = time.time()
        self._handler_registration_attempts = 0
        self._discord_errors = []
        self._debug_info = {}
        
        # Price caching
        self._price_cache = {}  # Symbol -> price mapping for caching prices
        self._price_cache_time = {}  # Symbol -> timestamp mapping for cache expiration
        
        # Alert storage and stats
        self._alerts = deque(maxlen=1000)  # Store last 1000 alerts
        self._alert_count = 0  # Total number of alerts generated
        self._alert_count_by_level = {
            'info': 0,
            'warning': 0,
            'error': 0,
            'critical': 0
        }
        self._alert_count_by_type = {}  # Type -> count mapping for alerts
        self._alert_stats = {
            'total': 0,
            'sent': 0,
            'throttled': 0,
            'duplicates': 0,
            'errors': 0,
            'handler_errors': 0,
            'handler_success': 0,  # Add missing key
            'processing_errors': 0,
            'info': 0,
            'warning': 0,
            'error': 0,
            'critical': 0
        }
        
        # Alert configuration
        self.alert_levels = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.alert_throttle = 60  # Default throttle of 60 seconds
        self.liquidation_threshold = 100000  # Default $100k threshold for liquidation alerts
        self.liquidation_cooldown = 300  # Default 5 minutes cooldown between liquidation alerts for the same symbol
        self.large_order_cooldown = 300  # Default 5 minutes cooldown between large order alerts for the same symbol
        self.whale_activity_cooldown = 900  # Default 15 minutes cooldown between whale activity alerts for the same symbol
        
        # Discord configuration
        self.discord_client = None
        
        # Metrics tracking
        self._ohlcv_cache = {}  # Cache for OHLCV data
        self._market_data_cache = {}  # Cache for market data
        self._last_ohlcv_update = {}  # Last update time for OHLCV data
        
        # CRITICAL DEBUG: Print initialization
        print("CRITICAL DEBUG: Initializing AlertManager")
        
        # CRITICAL FIX: Hardcoded Discord webhook URL as last resort
        # This will be overridden if found in config or environment
        self.discord_webhook_url = "https://discord.com/api/webhooks/1197011710268162159/V_Gfq66qtfJGiZMxnIwC7pb20HwHqVCRMoU_kubPetn_ikB5F8NTw81_goGLoSQ3q3Vw"
        print(f"CRITICAL DEBUG: Backup webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
        
        # Additional configurations from config file
        if 'monitoring' in self.config and 'alerts' in self.config['monitoring']:
            alert_config = self.config['monitoring']['alerts']
            
            # Discord webhook - first check from direct path in config
            if 'discord_webhook_url' in alert_config:
                self.discord_webhook_url = alert_config['discord_webhook_url']
                print(f"CRITICAL DEBUG: Webhook URL from direct config: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            # Then check nested discord > webhook_url path (old format)
            elif 'discord' in alert_config and 'webhook_url' in alert_config['discord']:
                self.discord_webhook_url = alert_config['discord']['webhook_url']
                print(f"CRITICAL DEBUG: Webhook URL from nested config: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            # Try to get from environment variable
            else:
                discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
                if discord_webhook_url:
                    # Fix potential newline issues
                    discord_webhook_url = discord_webhook_url.strip().replace('\n', '')
                    self.discord_webhook_url = discord_webhook_url
                    print(f"CRITICAL DEBUG: Webhook URL from environment: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
                else:
                    self.logger.warning("No Discord webhook URL found in config or environment")
            
            # Direct discord webhook from config (alternative path)
            if 'discord_network' in alert_config:
                self.discord_webhook_url = alert_config['discord_network']
                print(f"CRITICAL DEBUG: Webhook URL from discord_network: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            
            # Thresholds
            if 'thresholds' in alert_config:
                if 'buy' in alert_config['thresholds']:
                    self.buy_threshold = alert_config['thresholds']['buy']
                if 'sell' in alert_config['thresholds']:
                    self.sell_threshold = alert_config['thresholds']['sell']
            
            # Cooldowns
            if 'cooldowns' in alert_config:
                if 'liquidation' in alert_config['cooldowns']:
                    self.liquidation_cooldown = alert_config['cooldowns']['liquidation']
                if 'large_order' in alert_config['cooldowns']:
                    self.large_order_cooldown = alert_config['cooldowns']['large_order']
                if 'alert' in alert_config['cooldowns']:
                    self.alert_throttle = alert_config['cooldowns']['alert']
                    
            # Load liquidation configuration
            if 'liquidation' in alert_config:
                if 'threshold' in alert_config['liquidation']:
                    self.liquidation_threshold = alert_config['liquidation']['threshold']
                    print(f"CRITICAL DEBUG: Loaded liquidation threshold from config: ${self.liquidation_threshold:,}")
        
        # Force initialize handlers
        try:
            self._initialize_handlers()
            print(f"CRITICAL DEBUG: Handlers after initialization: {self.handlers}")
        except Exception as e:
            print(f"CRITICAL DEBUG: Error initializing handlers: {str(e)}")
        
        # Test Discord webhook
        # self.test_discord_webhook()  # Removed test webhook to prevent startup alerts
        
        # Log critical information for troubleshooting
        self.logger.info(f"Buy threshold: {self.buy_threshold}")
        self.logger.info(f"Sell threshold: {self.sell_threshold}")
        self.logger.info(f"Discord webhook URL is set: {bool(self.discord_webhook_url)}")
        
        try:
            # Validate configuration
            self._validate_alert_config()
            
            # Force initialization of handlers
            self._initialize_handlers()
            
            # Print registered handlers
            self.logger.info(f"INIT: Registered handlers: {self.handlers}")
            
            # Initialize Discord webhook client
            self._init_discord_webhook()
            
            # Send a test message to verify Discord webhook (DISABLED)
            # if self.discord_webhook_url:
            #     import asyncio
            #     try:
            #         # Create a simple test message
            #         test_message = {
            #             "content": "🔄 Alert system initialized and webhook test successful!",
            #             "username": "Virtuoso Alerts",
            #             "avatar_url": "https://i.imgur.com/4M34hi2.png"
            #         }
            #         
            #         # Try to send the test webhook asynchronously
            #         loop = asyncio.get_event_loop()
            #         loop.run_until_complete(self.send_discord_webhook_message(test_message))
            #         self.logger.info("INIT: Discord webhook test message sent successfully")
            #     except Exception as e:
            #         self.logger.error(f"INIT: Failed to send test webhook message: {str(e)}")
            #         
            #         # Try a fallback approach using curl
            #         try:
            #             import subprocess
            #             curl_cmd = [
            #                 "curl", "-X", "POST",
            #                 "-H", "Content-Type: application/json",
            #                 "-d", '{"content": "🔄 Alert system initialized (curl fallback)"}',
            #                 self.discord_webhook_url
            #             ]
            #             result = subprocess.run(curl_cmd, capture_output=True, text=True)
            #             self.logger.info(f"INIT: Fallback curl result: {result.returncode}")
            #             if result.stdout:
            #                 self.logger.info(f"INIT: Curl output: {result.stdout[:100]}")
            #             if result.stderr:
            #                 self.logger.error(f"INIT: Curl error: {result.stderr[:100]}")
            #         except Exception as e:
            #             self.logger.error(f"INIT: Fallback curl also failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"INIT: Error initializing AlertManager: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def _is_duplicate_alert(self, symbol: str, content_hash: str = None) -> bool:
        """Check if an alert would be a duplicate based on symbol and/or content.
        
        Args:
            symbol: Trading symbol
            content_hash: Optional hash of alert content for more specific deduplication
            
        Returns:
            Always returns False as deduplication is disabled
        """
        # Deduplication has been disabled - always return False
        self.logger.info(f"Deduplication disabled - allowing alert for {symbol} with content hash {content_hash}")
        return False

    def _initialize_handlers(self):
        """Initialize alert handlers based on configuration."""
        try:
            # Clear existing handlers to prevent duplicates
            self.handlers = []
            self.alert_handlers = {}
            
            # Log the initialization
            self.logger.info("INIT HANDLERS: Initializing alert handlers")
            
            # Initialize Discord handler if configured
            if self.discord_webhook_url:
                webhook_url = self.discord_webhook_url.strip()
                if webhook_url:
                    # Validate webhook URL format
                    self.logger.info(f"INIT HANDLERS: Checking Discord webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
                    
                    # Ensure Discord handler is registered regardless of URL format 
                    # (previous version only registered if it started with correct URL)
                    self.register_handler('discord')
                    self.logger.info(f"INIT HANDLERS: Registered Discord handler with webhook URL")
                else:
                    self.logger.error("INIT HANDLERS: Discord webhook URL is empty after stripping")
            else:
                self.logger.error("INIT HANDLERS: No Discord webhook URL configured")
                
            # Log registered handlers
            self.logger.info(f"INIT HANDLERS: Registered handlers: {self.handlers}")
            
            # Force Discord handler registration if it's not already there
            if 'discord' not in self.handlers and self.discord_webhook_url:
                self.logger.info("INIT HANDLERS: Forcing Discord handler registration")
                self.handlers.append('discord')
                self.alert_handlers['discord'] = self._send_discord_alert
                self.logger.info(f"INIT HANDLERS: Handlers after force registration: {self.handlers}")
                
        except Exception as e:
            self.logger.error(f"INIT HANDLERS: Error initializing handlers: {str(e)}")
            self.logger.error(traceback.format_exc())

    def get_handlers(self) -> List[str]:
        """Get list of registered handler names."""
        return self.handlers
        
    def register_handler(self, name: str) -> None:
        """Register alert handler.
        
        Args:
            name: Handler name
        """
        try:
            if name == 'discord':
                # Check if the handler is already registered
                if name not in self.handlers:
                    # Ensure the Discord webhook URL is set
                    if not self.discord_webhook_url:
                        self.logger.error("REGISTER: Cannot register Discord handler - webhook URL not set")
                        return
                        
                    self.handlers.append(name)
                    self.alert_handlers[name] = self._send_discord_alert
                    self.logger.info(f"REGISTER: Successfully registered alert handler: {name}")
                    
                    # Try to initialize the Discord webhook client
                    self._init_discord_webhook()
                else:
                    self.logger.warning(f"REGISTER: Handler {name} already registered")
            else:
                self.logger.warning(f"REGISTER: Unknown handler type: {name}")
            
        except Exception as e:
            self.logger.error(f"REGISTER: Error registering handler {name}: {str(e)}")
            self.logger.error(traceback.format_exc())
        
    def remove_handler(self, name: str) -> None:
        """Remove alert handler.
        
        Args:
            name: Handler name
        """
        if name in self.alert_handlers:
            self.alert_handlers.pop(name)
            logger.info(f"Removed alert handler: {name}")
            
    async def send_alert(self, level: str,
                        message: str,
                        details: Optional[Dict[str, Any]] = None,
                        throttle: bool = True) -> None:
        """Send alert to registered handlers."""
        try:
            self.logger.debug("=== Alert Request Details ===")
            self.logger.debug(f"Level: {level}")
            self.logger.debug(f"Message: {message[:100]}...")
            self.logger.debug(f"Details type: {details.get('type') if details else 'None'}")
            self.logger.debug(f"Throttle enabled: {throttle}")
            
            # Validate alert level
            level = level.upper()
            if level not in self.alert_levels:
                self.logger.error(f"Invalid alert level: {level}")
                return
                
            # Special handling for large order alerts
            if details and details.get('type') == 'large_aggressive_order':
                symbol = details.get('symbol', 'UNKNOWN')
                current_time = time.time()
                
                # Check symbol-specific cooldown
                if throttle and (current_time - self._last_large_order_alert.get(symbol, 0) < self.large_order_cooldown):
                    self.logger.debug(f"Large order alert throttled for {symbol}")
                    return
                
                self._last_large_order_alert[symbol] = current_time
            
            # Special handling for whale activity alerts
            if details and details.get('type') == 'whale_activity':
                symbol = details.get('symbol', 'UNKNOWN')
                current_time = time.time()
                subtype = details.get('subtype', 'unknown')
                
                # Check symbol-specific cooldown
                if throttle and (current_time - self._last_whale_activity_alert.get(f"{symbol}:{subtype}", 0) < self.whale_activity_cooldown):
                    self.logger.debug(f"Whale activity alert ({subtype}) throttled for {symbol}")
                    return
                
                self._last_whale_activity_alert[f"{symbol}:{subtype}"] = current_time
                
                # Enhanced formatting for Discord
                if 'discord' in self.handlers:
                    # Create a more visually appealing alert
                    emoji = "🐋📈" if subtype == "accumulation" else "🐋📉" if subtype == "distribution" else "🐋"
                    color = 0x00FF00 if subtype == "accumulation" else 0xFF0000 if subtype == "distribution" else 0x888888
                    
                    # Create Discord embed
                    embed = DiscordEmbed(
                        title=f"{emoji} Whale {subtype.capitalize()} Detected for {symbol}",
                        description=message,
                        color=color
                    )
                    
                    # Add timestamp
                    embed.set_timestamp()
                    
                    # Add activity data
                    if 'data' in details:
                        activity_data = details['data']
                        
                        # Format amounts for readability
                        bid_usd = activity_data.get('whale_bid_usd', 0)
                        ask_usd = activity_data.get('whale_ask_usd', 0)
                        net_usd = activity_data.get('net_usd_value', 0)
                        
                        # Add bid information
                        embed.add_embed_field(
                            name="Bid Orders",
                            value=f"{activity_data.get('whale_bid_orders', 0)} orders\n${bid_usd:,.2f}"
                        )
                        
                        # Add ask information
                        embed.add_embed_field(
                            name="Ask Orders",
                            value=f"{activity_data.get('whale_ask_orders', 0)} orders\n${ask_usd:,.2f}"
                        )
                        
                        # Add imbalance information
                        embed.add_embed_field(
                            name="Imbalance",
                            value=f"{activity_data.get('imbalance', 0):.1%}"
                        )
                    
                    # Create webhook and add embed
                    webhook = DiscordWebhook(url=self.discord_webhook_url)
                    webhook.add_embed(embed)
                    
                    # Send webhook directly
                    response = webhook.execute()
                    
                    # Check response status
                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"Sent whale activity Discord alert for {symbol} ({subtype})")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        return
                    else:
                        self.logger.warning(f"Failed to send whale activity Discord alert: {response}")
                        # Continue with standard alert as fallback
            
            # Create alert
            alert = {
                'level': level,
                'message': message,
                'details': details or {},
                'timestamp': float(time.time())
            }
            
            # Check throttling with debug info
            alert_key = f"{level}:{message}"
            if throttle:
                self.logger.debug(f"Checking throttling for key: {alert_key}")
                if self._is_throttled(alert_key):
                    self.logger.warning(f"Alert throttled: {alert_key}")
                    self._alert_stats['throttled'] = int(self._alert_stats['throttled']) + 1
                    return
                else:
                    self.logger.debug("Alert passed throttling check")
            
            # Store alert
            self._alerts.append(alert)
            self._alert_stats['total'] = int(self._alert_stats['total']) + 1
            self._alert_stats[level.lower()] = int(self._alert_stats[level.lower()]) + 1
            self._last_alert[alert_key] = float(time.time())
            
            # Process alert with debug info
            self.logger.debug("Processing alert through handlers")
            await self._process_alert(alert)
            self.logger.debug("Alert processing completed")
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats['errors']) + 1

    def get_alerts(self, level: Optional[str] = None,
                  limit: Optional[int] = None,
                  start_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get filtered alerts.
        
        Args:
            level: Filter by alert level
            limit: Maximum number of alerts
            start_time: Filter by start time
            
        Returns:
            List[Dict[str, Any]]: Filtered alerts
        """
        try:
            alerts = list(self._alerts)
            
            # Apply filters
            if level:
                level = level.upper()
                if level not in self.alert_levels:
                    logger.error(f"Invalid alert level: {level}")
                    return []
                alerts = [a for a in alerts if a['level'] == level]
                
            if start_time is not None:
                start_time = float(start_time)
                alerts = [a for a in alerts if float(a['timestamp']) >= start_time]
                
            # Apply limit
            if limit is not None:
                limit = int(limit)
                alerts = alerts[-limit:]
                
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            return []
            
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics.
            
        Returns:
            Dict[str, Any]: Alert statistics
        """
        try:
            stats = dict(self._alert_stats)
            stats['active_handlers'] = int(len(self.alert_handlers))
            
            # Calculate level percentages
            total = int(stats.get('total', 0)) or 1  # Avoid division by zero
            for level in self.alert_levels:
                level_count = int(stats.get(level.lower(), 0))
                stats[f"{level.lower()}_percent"] = float((level_count / total) * 100)
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting alert stats: {str(e)}")
            return {}
            
    def clear_alerts(self) -> None:
        """Clear all stored alerts."""
        try:
            self._alerts.clear()
            self._alert_stats.clear()
            self._last_alert.clear()
            logger.info("Cleared all alerts")
            
        except Exception as e:
            logger.error(f"Error clearing alerts: {str(e)}")

    def _is_throttled(self, alert_key: str) -> bool:
        """Check if alert should be throttled.
        
        Args:
            alert_key: Alert key for throttling
            
        Returns:
            bool: True if alert should be throttled
        """
        last_time = float(self._last_alert.get(alert_key, 0))
        return (float(time.time()) - last_time) < float(self.alert_throttle)
        
    async def _process_alert(self, alert: Dict[str, Any]) -> None:
        """Process alert through registered handlers."""
        try:
            # Check if we have any handlers
            if not self.alert_handlers:
                self.logger.warning("No alert handlers registered!")
                return
            
            # Process through each handler
            for name, handler in self.alert_handlers.items():
                self.logger.debug(f"Processing alert through handler: {name}")
                try:
                    await handler(alert)
                    self._alert_stats['handler_success'] += 1
                    self.logger.debug(f"Handler {name} processed alert successfully")
                except Exception as e:
                    self.logger.error(f"Handler {name} failed: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    self._alert_stats['handler_errors'] += 1
        
        except Exception as e:
            self.logger.error(f"Error processing alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._alert_stats['processing_errors'] += 1

    async def check_liquidation_threshold(self, symbol: str, liquidation_data: Dict[str, Any]) -> None:
        """Check if liquidation exceeds threshold and should trigger alert."""
        try:
            # Debug log the incoming data
            self.logger.debug(f"Received liquidation data for {symbol}: {liquidation_data}")
            
            # Get last alert time for this symbol
            last_alert = self._last_liquidation_alert.get(symbol, 0)
            current_time = time.time()
            
            # Check cooldown
            if current_time - last_alert < self.liquidation_cooldown:
                return
                
            # Calculate USD value
            usd_value = liquidation_data['size'] * liquidation_data['price']
            
            # Check against configured threshold
            if usd_value >= self.liquidation_threshold:
                # Determine direction and impact
                side = liquidation_data['side'].upper()
                
                # CORRECTED INTERPRETATION:
                # When side is "BUY", it means LONG positions are being liquidated (forced to sell)
                # When side is "SELL", it means SHORT positions are being liquidated (forced to buy)
                position_type = "LONG" if side == "BUY" else "SHORT"
                
                # Format timestamp
                timestamp = datetime.fromtimestamp(
                    liquidation_data['timestamp'] / 1000 if liquidation_data['timestamp'] > 1e12 
                    else liquidation_data['timestamp'], 
                    tz=timezone.utc
                ).strftime('%H:%M:%S UTC')
                
                # Calculate how recent this liquidation is
                now = datetime.now(timezone.utc)
                event_time = datetime.fromtimestamp(
                    liquidation_data['timestamp'] / 1000 if liquidation_data['timestamp'] > 1e12 
                    else liquidation_data['timestamp'], 
                    tz=timezone.utc
                )
                time_diff_seconds = (now - event_time).total_seconds()
                
                # Format time difference for display
                if time_diff_seconds < 60:
                    time_ago = f"{int(time_diff_seconds)}s ago"
                elif time_diff_seconds < 3600:
                    time_ago = f"{int(time_diff_seconds/60)}m ago"
                else:
                    time_ago = f"{int(time_diff_seconds/3600)}h ago"
                
                # Extract base asset name (e.g., BTC from BTCUSDT)
                base_asset = symbol.split('USDT')[0] if 'USDT' in symbol else symbol.split('USD')[0]
                
                # Direction-specific emojis and formatting
                direction_emoji = "🔴" if position_type == "LONG" else "🟢"
                impact_level = self._determine_impact_level(usd_value)
                impact_emoji = "💥" if impact_level == "HIGH" else "⚠️" if impact_level == "MEDIUM" else "ℹ️"
                
                # Calculate percentage of threshold
                threshold_percentage = min(int((usd_value / self.liquidation_threshold) * 100), 1000)
                threshold_indicator = "!" * min(5, threshold_percentage // 100)
                
                # Generate visual impact bar
                impact_bar = self._generate_impact_bar(usd_value)
                
                # Create a price action note based on position type and impact level
                price_action = self._get_price_action_note(position_type, impact_level)
                
                # Format message with improved visual elements
                message = (
                    f"{direction_emoji} **{position_type} LIQUIDATION** {impact_emoji}\n"
                    f"**Symbol:** {symbol}\n"
                    f"**Time:** {timestamp} ({time_ago})\n"
                    f"**Size:** {liquidation_data['size']:.4f} {base_asset}\n"
                    f"**Price:** ${liquidation_data['price']:,.2f}\n"
                    f"**Value:** ${usd_value:,.2f} {threshold_indicator}\n"
                    f"**Impact:** Immediate {'buying 📈' if position_type == 'SHORT' else 'selling 📉'} pressure on market\n"
                    f"**Severity:** {impact_level}\n"
                    f"**Impact Meter:** `{impact_bar}`\n"
                    f"**Note:** {price_action}"
                )
                
                alert_data = {
                    'type': 'liquidation',
                    'symbol': symbol,
                    'side': side,
                    'direction': position_type,
                    'size': liquidation_data['size'],
                    'price': liquidation_data['price'],
                    'usd_value': usd_value,
                    'timestamp': liquidation_data['timestamp'],
                    'impact': f"Immediate {'buying' if position_type == 'SHORT' else 'selling'} pressure on market",
                    'impact_level': impact_level,
                    'raw_data': liquidation_data  # Include the complete raw data from API
                }
                
                # Send alert with proper parameters
                await self.send_alert(
                    level="WARNING",
                    message=message,
                    details=alert_data
                )
                
                # Update last alert time for cooldown
                self._last_liquidation_alert[symbol] = current_time
        except Exception as e:
            self.logger.error(f"Error checking liquidation threshold: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        try:
            # Get absolute path to project root
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(current_dir, 'src', 'config')
            
            # Check for logging config
            logging_config_path = os.path.join(config_dir, 'logging.yaml')
            if os.path.exists(logging_config_path):
                print(f"Loading logging config from {logging_config_path}")
                with open(logging_config_path, 'r') as f:
                    logging_config = yaml.safe_load(f)
                    logging.config.dictConfig(logging_config)
            else:
                print(f"Loading logging config from main config file")
                # Load level from main config
                config_path = os.path.join(config_dir, 'config.yaml')
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    log_level = config.get('logging', {}).get('root', {}).get('level', 'DEBUG')
                    print(f"Using log level: {log_level}")
                
                # Basic logging configuration using level from config
                coloredlogs.install(
                    level=log_level,
                    fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                )
                
                # Create logs directory if it doesn't exist
                logs_dir = os.path.join(current_dir, 'logs')
                if not os.path.exists(logs_dir):
                    print(f"Creating logs directory: {logs_dir}")
                    os.makedirs(logs_dir)
                
        except Exception as e:
            print(f"Error setting up logging: {e}")
            traceback.print_exc()
            sys.exit(1)

    async def stop(self) -> None:
        """Stop the alert manager."""
        try:
            # Close client session if it exists
            if self._client_session and not self._client_session.closed:
                await self._client_session.close()
                self.logger.info("Closed HTTP client session")
            
            self.logger.info("Alert manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping alert manager: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up resources used by the alert manager.
        
        This method is called during application shutdown.
        """
        try:
            await self.stop()
            self.logger.info("Alert manager cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during alert manager cleanup: {str(e)}")
            
    async def handle_error(
        self,
        error: Union[str, Exception],
        component: Optional[str] = None,
        level: str = "error",
        **kwargs
    ) -> None:
        """Handle error with proper component tracking and severity levels."""
        try:
            error_msg = str(error)
            
            # Format alert message
            alert = {
                'timestamp': int(time.time() * 1000),
                'component': component or 'unknown',
                'level': level,
                'message': error_msg,
                'details': kwargs
            }
            
            # Log error
            if level == "error":
                self.logger.error(f"{component}: {error_msg}")
            else:
                self.logger.warning(f"{component}: {error_msg}")
                
            # Store alert
            await self._store_alert(alert)
            
            # Send notifications if needed
            await self._send_notifications(alert)
            
        except Exception as e:
            self.logger.error(f"Error in alert handling: {str(e)}")

    def _save_component_data(self, symbol: str, components: Dict[str, Any], results: Dict[str, Any], signal_type: str) -> Optional[str]:
        """
        Save component data to a JSON file for debugging and auditing.
        
        Args:
            symbol: The symbol for the alert
            components: The component scores
            results: The detailed results with interpretations
            signal_type: The type of signal (BUY, SELL, NEUTRAL)
            
        Returns:
            Optional[str]: Path to the saved JSON file if successful, None otherwise
        """
        try:
            # Create exports directory if it doesn't exist
            exports_dir = os.path.join(os.getcwd(), 'exports', 'component_data')
            os.makedirs(exports_dir, exist_ok=True)
            
            # Create a filename with timestamp, symbol and signal type
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{symbol}_{signal_type}_{timestamp}.json"
            filepath = os.path.join(exports_dir, filename)
            
            # Prepare data to save
            data = {
                'symbol': symbol,
                'timestamp': timestamp,
                'components': components,
                'results': results,
                'signal_type': signal_type
            }
            
            # Helper function to handle non-serializable objects
            def prepare_for_json(obj):
                if hasattr(obj, 'item') and callable(getattr(obj, 'item')):
                    # Handle numpy types
                    return obj.item()
                elif isinstance(obj, dict):
                    # Process nested dictionaries
                    return {k: prepare_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    # Process lists and tuples
                    return [prepare_for_json(item) for item in obj]
                elif isinstance(obj, (datetime, np.datetime64)):
                    # Handle datetime objects
                    return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
                else:
                    # Return other types as is
                    return obj
            
            # Prepare the data for JSON serialization
            json_ready_data = prepare_for_json(data)
            
            # Write to file with pretty formatting
            with open(filepath, 'w') as f:
                json.dump(json_ready_data, f, indent=2, default=str)
            
            self.logger.info(f"Saved component data to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving component data to JSON: {str(e)}")
            return None

    async def send_confluence_alert(
        self, 
        symbol: str, 
        confluence_score: float, 
        components: Dict[str, float], 
        results: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
        reliability: float = 0.0,
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None,
        price: Optional[float] = None,  # Optional direct price
        transaction_id: Optional[str] = None,  # Transaction ID for tracking
        signal_id: Optional[str] = None,  # Signal ID for tracking within SignalGenerator
        influential_components: Optional[List[Dict[str, Any]]] = None,  # Enhanced data
        market_interpretations: Optional[List[Union[str, Dict[str, Any]]]] = None,  # Enhanced data
        actionable_insights: Optional[List[str]] = None,  # Enhanced data
        top_weighted_subcomponents: Optional[List[Dict[str, Any]]] = None,  # Top weighted sub-components
        signal_type: Optional[str] = None  # Add explicit signal_type parameter
    ) -> None:
        """Send formatted confluence alert to Discord with components breakdown.
        
        This is the primary method for sending trading signal alerts with 
        detailed component analysis in a nicely formatted message.
        
        Args:
            symbol: Trading pair symbol
            confluence_score: The overall confluence score
            components: Dictionary of component scores
            results: Dictionary of detailed component results
            weights: Optional dictionary of component weights
            reliability: Confidence level (0-1)
            buy_threshold: Threshold for buy signals
            sell_threshold: Threshold for sell signals
            price: Current price
            transaction_id: Transaction ID for cross-component tracking
            signal_id: Signal ID for tracking within SignalGenerator
            influential_components: List of top influential components with metadata
            market_interpretations: List of market interpretations
            actionable_insights: List of actionable trading insights
            top_weighted_subcomponents: List of sub-components with highest weighted impact
            signal_type: Explicit signal type (BUY, SELL, NEUTRAL) from caller
        """
        # Use provided transaction_id or generate a new one
        txn_id = transaction_id or str(uuid.uuid4())[:8]
        # Use provided signal_id or generate a new one
        sig_id = signal_id or str(uuid.uuid4())[:8]
        # Generate a unique alert ID
        alert_id = str(uuid.uuid4())[:8]
        
        self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Starting confluence alert for {symbol}")
        
        try:
            # Log all parameters for debugging
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Parameters for {symbol}:")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Score: {confluence_score}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Component count: {len(components)}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Results count: {len(results)}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Reliability: {reliability}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Thresholds: buy={buy_threshold}, sell={sell_threshold}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Price: {price}")
            if signal_type:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Explicit signal type: {signal_type}")
            
            # Debug log the enhanced data structures
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Market Interpretations: {market_interpretations}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Influential Components: {influential_components}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Top Weighted Subcomponents: {top_weighted_subcomponents}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Actionable Insights: {actionable_insights}")

            # Use thresholds from constructor if not provided
            if buy_threshold is None:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using default buy threshold: {self.buy_threshold}")
                buy_threshold = self.buy_threshold
            if sell_threshold is None:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using default sell threshold: {self.sell_threshold}")
                sell_threshold = self.sell_threshold
                
            # Prevent errors from weights formatting
            if weights is None:
                weights = {}
                
            # Add default weight labels if needed
            weight_labels = {
                'momentum': 'Momentum',
                'technical': 'Technical',
                'volume': 'Volume',
                'orderflow': 'Orderflow',
                'orderbook': 'Orderbook',
                'sentiment': 'Sentiment', 
                'price_structure': 'Structure'
            }
            
            # Debug: Log components received
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Components received: {components}")
            
            # Use explicit signal_type if provided, otherwise determine based on score and thresholds
            if not signal_type:
                if confluence_score >= buy_threshold:
                    signal_type = "BUY"
                elif confluence_score <= sell_threshold:
                    signal_type = "SELL"
                else:
                    signal_type = "NEUTRAL"
                
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Determined signal type by thresholds: {signal_type}")
            else:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using provided signal type: {signal_type}")
            
            # Set emoji and color based on the signal type
            if signal_type == "BUY":
                emoji = "🟢"
                color = 0x00ff00  # Green
            elif signal_type == "SELL":
                emoji = "🔴"
                color = 0xff0000  # Red
            else:
                emoji = "⚪"
                color = 0x888888  # Gray
            
            # Format the price string
            price_str = format_price_string(price) if price else "N/A"
            
            # If price not provided, try to resolve it
            if price is None:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] No price provided, attempting to resolve")
                
                try:
                    # Try to get price from cache
                    if symbol in self._price_cache and time.time() - self._price_cache_time.get(symbol, 0) < 60:
                        price = self._price_cache[symbol]
                        price_str = format_price_string(price)
                        self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using cached price: {price_str}")
                    else:
                        # DEBUG PRICE ERROR - This shouldn't happen, price should be provided
                        self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] DEBUG PRICE ERROR: Price should be set in monitor.py:_generate_signal (lines ~2650-2679)")
                        
                except Exception as price_err:
                    self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Error resolving price: {price_err}")
            
            # Build title with emojis
            title = f"{emoji} {signal_type} SIGNAL: {symbol}"
            # Build description with score and price
            # Ensure reliability is between 0 and 1 to avoid percentage display issues
            if reliability > 1:
                # If reliability is already expressed as a percentage (e.g., 85 instead of 0.85)
                normalized_reliability = reliability / 100
            else:
                # If reliability is already a decimal between 0-1
                normalized_reliability = reliability
                
            # Format as percentage
            reliability_pct = int(normalized_reliability * 100)
            
            description = (
                f"**Confluence Score:** {confluence_score:.2f}/100\n"
                f"**Current Price:** {price_str}\n"
                f"**Reliability:** {reliability_pct}%\n"
            )
            
            # Only add component gauge section if we have components
            if components:
                # Build component gauges for visualization
                description += "\n**Component Analysis:**\n"
                
                # Get sorted component items by score
                sorted_components = sorted(
                    components.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                
                # Build a gauge for each component
                for component_name, score in sorted_components:
                    # Skip components with NaN scores
                    if pd.isna(score):
                        continue
                    
                    # Use friendly name if available
                    display_name = weight_labels.get(component_name, component_name.capitalize())
                    
                    # Calculate gauge width
                    MAX_WIDTH = 15
                    filled = int(round(score / 100 * MAX_WIDTH))
                    filled = min(max(filled, 0), MAX_WIDTH)  # Clamp between 0 and MAX_WIDTH
                    
                    # Build gauge
                    gauge = self._build_gauge(score)
                    
                    # Get emoji based on score
                    if score >= 70:
                        emoji = "🟢"  # Green (very positive)
                    elif score >= 55:
                        emoji = "🟡"  # Yellow (positive)
                    elif score >= 45:
                        emoji = "⚪"  # White (neutral)
                    elif score >= 30:
                        emoji = "🟠"  # Orange (negative)
                    else:
                        emoji = "🔴"  # Red (very negative)
                        
                    # Add component to description
                    description += f"`{display_name:10}` {gauge} `{score:>5.1f}`% {emoji}\n"
                
                # Add gauge for overall confluence
                description += "\n**Overall Confluence:**\n"
                overall_gauge = self._build_gauge(confluence_score, is_impact=True)
                # Add threshold markers
                overall_gauge = self._add_threshold_markers(overall_gauge, buy_threshold, sell_threshold)
                
                # Get overall emoji based on signal
                if signal_type == "BUY":
                    overall_emoji = "🚀"
                elif signal_type == "SELL":
                    overall_emoji = "📉"
                else:
                    overall_emoji = "⚖️"
                
                description += f"`{'IMPACT':10}` {overall_gauge} `{confluence_score:>5.1f}`% {overall_emoji}\n"
            
            # Save component data as JSON for future reference
            json_path = self._save_component_data(symbol, components, results, signal_type)
            
            # Add interpretations if available
            if results or market_interpretations:
                # Process detailed interpretations from results
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Processing detailed interpretations from results")
                
                # Check for enhanced formatted data first - Add fallback market interpretations if none provided
                if market_interpretations and isinstance(market_interpretations, list) and len(market_interpretations) > 0:
                    self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using enhanced market interpretations: {len(market_interpretations)} items")
                    description += "\n**MARKET INTERPRETATIONS:**\n"
                    
                    # Log the received interpretations for debugging
                    for i, interp in enumerate(market_interpretations[:5]):
                        self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Interpretation {i}: {type(interp)} - {interp}")
                    
                    # Add each interpretation - properly extract from objects
                    for interp_idx, interp_obj in enumerate(market_interpretations[:3]):
                        # Debug the current interpretation object
                        self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Processing interpretation {interp_idx}: {type(interp_obj)}")
                        
                        if isinstance(interp_obj, dict):
                            # Extract component name and interpretation text
                            component = interp_obj.get('display_name', interp_obj.get('component', 'Unknown'))
                            interp_text = interp_obj.get('interpretation', 'No interpretation available')
                            
                            # Handle nested interpretation object
                            if isinstance(interp_text, dict):
                                # Convert dict to string if needed
                                if 'message' in interp_text:
                                    interp_text = interp_text['message']
                                # Special handling for sentiment which has a specific structure
                                elif component.lower() == 'sentiment' and 'sentiment' in interp_text:
                                    # Extract main sentiment message and use it directly
                                    interp_text = interp_text.get('sentiment', '')
                                    # Add other important insights if available
                                    if 'funding_rate' in interp_text:
                                        interp_text += f" with {interp_text['funding_rate'].lower()}"
                                    if 'market_activity' in interp_text:
                                        interp_text += f" and {interp_text['market_activity'].lower()}"
                                else:
                                    # For other dictionary types, format more readably
                                    interp_text = '; '.join([f"{k.replace('_', ' ').title()}: {v}" for k, v in interp_text.items()])
                            
                            # Format with component name and text
                            description += f"• **{component}**: {interp_text}\n"
                            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Added interpretation for {component}")
                        else:
                            # Fallback for string interpretations
                            description += f"• {interp_obj}\n"
                            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Added string interpretation")
                        
                        # No extra spacing after each item to keep formatting compact
                        # description += "\n"
                else:
                    # Use original format if enhanced data not available
                    self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Enhanced market interpretations not available, using fallback")
                    description += "\n**Key Insights:**\n"
                    
                    # Display top 3 component interpretations (highest scores first)
                    top_components = sorted(
                        [(k, v.get('score', 0)) for k, v in results.items() if isinstance(v, dict)], 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:3]
                    
                    for component_name, _ in top_components:
                        # Get interpretation text
                        if component_name in results and 'interpretation' in results[component_name]:
                            interpretation = results[component_name]['interpretation']
                            # Format name with emoji
                            if component_name == 'technical' or component_name == 'momentum':
                                emoji = "📈"
                            elif component_name == 'volume':
                                emoji = "📊"
                            elif component_name == 'orderflow':
                                emoji = "💹"
                            elif component_name == 'orderbook':
                                emoji = "📖"
                            elif component_name == 'sentiment':
                                emoji = "🧠"
                            elif component_name == 'price_structure':
                                emoji = "🏗️"
                            else:
                                emoji = "🔍"
                                
                            # Add formatted interpretation
                            display_name = weight_labels.get(component_name, component_name.capitalize())
                            description += f"{emoji} **{display_name}:** {interpretation}\n"
            
            # Add actionable trading insights if available
            if actionable_insights and isinstance(actionable_insights, list) and len(actionable_insights) > 0:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Adding actionable trading insights: {len(actionable_insights)} items")
                description += "\n**ACTIONABLE TRADING INSIGHTS:**\n"
                
                for insight in actionable_insights[:3]:  # Limit to top 3 for readability
                    description += f"• {insight}\n"
                
                # Add spacing
                description += "\n"
            else:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] No actionable insights available to display")
            
            # Add top weighted sub-components if available
            if top_weighted_subcomponents and isinstance(top_weighted_subcomponents, list) and len(top_weighted_subcomponents) > 0:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Adding top weighted sub-components: {len(top_weighted_subcomponents)} items")
                description += "\n**TOP INFLUENTIAL INDIVIDUAL COMPONENTS:**\n"
                
                # Filter out "overall" components if we have real subcomponents
                real_subcomps = [s for s in top_weighted_subcomponents if not s.get('name', '').startswith('overall_')]
                
                # If we have real subcomponents, use those
                if real_subcomps:
                    subcomps_to_display = real_subcomps
                else:
                    subcomps_to_display = top_weighted_subcomponents
                
                for i, sub_comp in enumerate(subcomps_to_display[:3]):  # Always limit to top 3
                    sub_name = sub_comp.get('display_name', 'Unknown')
                    parent_name = sub_comp.get('parent_display_name', 'Unknown')
                    raw_score = sub_comp.get('score', 0)
                    # Use weighted_impact directly as it's already a percentage value (e.g., 16.67 means 16.67%)
                    impact = sub_comp.get('weighted_impact', 0)
                    indicator = sub_comp.get('indicator', '•')
                    
                    # Build gauge for sub-component
                    sub_gauge = self._build_gauge(raw_score, width=10)
                    
                    # Add formatted sub-component with impact percentage
                    description += f"{i+1}. **{sub_name}** `{raw_score:.1f}` {indicator} ({parent_name}) - Impact: `{impact:.1f}%` {sub_gauge}\n"
                
                # Add spacing
                description += "\n"
            else:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] No top weighted subcomponents available to display")
            
            # Build Discord embed
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Building Discord embed")
            
            # Check description length and trim if necessary (Discord has ~4000 char limit for embeds)
            description_length = len(description)
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Description length: {description_length} characters")
            
            if description_length > 3800:  # Leave some margin
                self.logger.warning(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Description too long ({description_length} chars), trimming...")
                
                # Keep the essential parts: score, price, reliability, component analysis, and overall confluence
                # Start by finding section markers
                market_interp_index = description.find("**MARKET INTERPRETATIONS:**")
                actionable_index = description.find("**ACTIONABLE TRADING INSIGHTS:**")
                weighted_index = description.find("**TOP INFLUENTIAL INDIVIDUAL COMPONENTS:**")
                
                # First keep the basic info and component analysis which are most critical
                essentials_end = description.find("\n**Overall Confluence:**")
                if essentials_end != -1:
                    essentials_end = description.find("\n\n", essentials_end + 20)  # Find end of Overall Confluence section
                
                if essentials_end != -1:
                    essential_part = description[:essentials_end]
                else:
                    essential_part = description[:min(1500, len(description))]
                
                # Then add the most important additional section based on priority
                additional_text = ""
                remaining_space = 3800 - len(essential_part)
                
                # Priority order: Actionable Insights > Market Interpretations > Weighted > Influential
                if actionable_index != -1 and remaining_space > 200:
                    next_section_index = min(filter(lambda x: x != -1 and x > actionable_index, 
                                               [weighted_index, float('inf')]))
                    actionable_text = description[actionable_index:next_section_index]
                    if len(actionable_text) <= remaining_space:
                        additional_text += actionable_text
                        remaining_space -= len(actionable_text)
                    else:
                        additional_text += actionable_text[:remaining_space-3] + "..."
                        remaining_space = 0
                
                if market_interp_index != -1 and remaining_space > 200:
                    next_section_index = min(filter(lambda x: x != -1 and x > market_interp_index, 
                                               [weighted_index, actionable_index, float('inf')]))
                    market_text = description[market_interp_index:next_section_index]
                    if len(market_text) <= remaining_space:
                        additional_text += market_text
                        remaining_space -= len(market_text)
                    else:
                        additional_text += market_text[:remaining_space-3] + "..."
                        remaining_space = 0
                
                # Combine essential parts with additional text
                trimmed_description = essential_part + "\n\n" + additional_text + "\n\n**Note:** Alert trimmed due to length limits"
                
                # Update description
                description = trimmed_description
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Trimmed description to {len(description)} characters")
            
            embed = DiscordEmbed(
                title=title,
                description=description,
                color=color
            )
            
            # Add timestamp
            embed.set_timestamp()
            
            # Add footer with tracking IDs
            embed.set_footer(text=f"TXN:{txn_id} | SIG:{sig_id} | ALERT:{alert_id}")
            
            # Create webhook
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Creating Discord webhook")
            webhook = DiscordWebhook(url=self.discord_webhook_url, username="Virtuoso Signals")
            
            # Add embed
            webhook.add_embed(embed)
            
            # Add chart if available
            if json_path:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] JSON path saved: {json_path}")
            
            # Execute webhook
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Executing webhook")
            
            # Add retry logic for webhook execution
            max_retries = 3
            retry_delay = 2  # seconds
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = webhook.execute()
                    
                    if response and response.status_code == 200:
                        self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Successfully sent confluence alert for {symbol}")
                        break
                    else:
                        status_code = response.status_code if response else "N/A"
                        self.logger.warning(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Failed to send alert (attempt {attempt+1}/{max_retries}): Status code {status_code}")
                        
                        # Check for specific error types that might be recoverable
                        if response and response.status_code in [429, 500, 502, 503, 504]:
                            # These are potentially recoverable with retry
                            if attempt < max_retries - 1:
                                self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Retrying after {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                        
                        if response and response.text:
                            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Response: {response.text[:200]}")
                        
                except aiohttp.ClientError as ce:
                    # Network errors are recoverable
                    self.logger.warning(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Network error sending alert (attempt {attempt+1}/{max_retries}): {str(ce)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                except Exception as e:
                    # Other unexpected errors
                    self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Unexpected error sending alert (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        # Final attempt failed with unexpected error
                        self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] All attempts failed, giving up after {max_retries} retries")
                        raise
            
            # Fallback attempt with alternative mechanism if all webhook attempts failed
            if not response or response.status_code != 200:
                self.logger.warning(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Trying fallback alert mechanism...")
                try:
                    # Fallback to regular HTTP post
                    fallback_data = {
                        'content': f"ALERT - {symbol} confluence score: {confluence_score:.2f}",
                        'embeds': [{
                            'title': title,
                            'description': description[:2000],  # Truncate to avoid length issues
                            'color': int(color, 16) if isinstance(color, str) else color
                        }]
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.discord_webhook_url,
                            json=fallback_data,
                            timeout=30
                        ) as resp:
                            if resp.status == 200:
                                self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Successfully sent alert using fallback method")
                                # Update success stats
                                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                                return
                            else:
                                self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Fallback method also failed: {resp.status}")
                except Exception as fallback_err:
                    self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Fallback method error: {str(fallback_err)}")
                    # Don't raise here, continue to update stats
            
            # Alert stats tracking (only if we didn't return early from fallback)
            # Count as success if either primary or fallback method succeeded
            if (response and response.status_code == 200):
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
            else:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
                self.logger.error(f"Failed to send confluence alert for {symbol}")
            
        except Exception as e:
            # Error handling 
            self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Error sending confluence alert for {symbol}: {str(e)}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] {traceback.format_exc()}")
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

    def _build_gauge(self, score: float, is_impact: bool = False, width: int = 15) -> str:
        """Build a gauge visualization for a component score or impact using Discord-compatible characters.
        
        Args:
            score: The score value (0-100)
            is_impact: If True, treat this as an impact gauge (different character set)
            width: The width of the gauge in characters
            
        Returns:
            A string containing the gauge visualization
        """
        # Normalize score to gauge width
        filled_width = int(round(score / 100 * width))
        unfilled_width = width - filled_width
        
        # Use different block characters based on the score ranges
        if is_impact:
            # For impact gauges, use different character based on impact level
            if score >= 80:
                filled_char = "█"  # Full block for high impact
            elif score >= 60:
                filled_char = "▓"  # Dark shade for medium-high impact
            elif score >= 40:
                filled_char = "▒"  # Medium shade for medium impact
            else:
                filled_char = "░"  # Light shade for low impact
        else:
            # For score gauges, use a full block regardless of score
            filled_char = "█"  # Full block
            
        # Use a light shade for unfilled portions
        unfilled_char = "░"
        
        # Build the gauge
        filled_part = filled_char * filled_width
        unfilled_part = unfilled_char * unfilled_width
        
        # Return the gauge without ANSI coloring
        return f"{filled_part}{unfilled_part}"

    def _add_gauge_indicator(self, gauge_line: str, position: float, indicator: str = "○", width: int = 15) -> str:
        """Add an indicator to a gauge line at the specified position using Discord-compatible characters.
        
        Args:
            gauge_line: The gauge line to add the indicator to
            position: The position to add the indicator at (0-100)
            indicator: The indicator character to add
            width: The width of the gauge
            
        Returns:
            The gauge line with the indicator added
        """
        # Calculate position in gauge
        pos = min(width - 1, max(0, int(round(position / 100 * width))))
        
        # Convert gauge line to list for easier character replacement
        gauge_chars = list(gauge_line)
        
        # Replace character at position with indicator
        if 0 <= pos < len(gauge_chars):
            gauge_chars[pos] = indicator
            
        # Convert back to string
        return ''.join(gauge_chars)

    def _add_threshold_markers(self, gauge_line: str, buy_threshold: float, sell_threshold: float, width: int = 15) -> str:
        """Add buy and sell threshold markers to a gauge line using Discord-compatible characters.
        
        Args:
            gauge_line: The gauge line to add the markers to
            buy_threshold: The buy threshold (0-100)
            sell_threshold: The sell threshold (0-100)
            width: The width of the gauge
            
        Returns:
            The gauge line with threshold markers added
        """
        # Calculate positions in gauge
        buy_pos = min(width - 1, max(0, int(round(buy_threshold / 100 * width))))
        sell_pos = min(width - 1, max(0, int(round(sell_threshold / 100 * width))))
        
        # Create threshold indicator lines
        threshold_line = ' ' * width
        threshold_chars = list(threshold_line)
        
        # Add buy and sell markers
        if 0 <= buy_pos < width:
            threshold_chars[buy_pos] = '↑'  # Up arrow for buy threshold
            
        if 0 <= sell_pos < width and sell_pos != buy_pos:
            threshold_chars[sell_pos] = '↓'  # Down arrow for sell threshold
            
        # Add thresholds to gauge
        threshold_indicator = ''.join(threshold_chars)
        
        # Return combined gauge with threshold indicators
        return f"{gauge_line}\n{threshold_indicator}"

    def _hash_signal_content(self, signal_data: Dict[str, Any]) -> str:
        """Generate a hash of the signal content to detect duplicates.
        
        Args:
            signal_data: Signal data to hash
            
        Returns:
            String hash to identify this signal content
        """
        try:
            # Extract key fields for hashing
            symbol = signal_data.get('symbol', '')
            signal_type = signal_data.get('signal', '')
            score = signal_data.get('confluence_score', 0)  # Use confluence_score consistently
            
            # Create a string to hash
            content_str = f"{symbol}_{signal_type}_{score:.2f}_{int(time.time() / 300)}"  # Group by 5-minute intervals
            
            # Generate hash
            hash_obj = hashlib.md5(content_str.encode('utf-8'))
            return hash_obj.hexdigest()
        except Exception as e:
            self.logger.error(f"Error generating signal content hash: {str(e)}")
            # Fallback to a simple timestamp-based identifier
            return f"{signal_data.get('symbol', 'unknown')}_{int(time.time())}"

    def _validate_alert_config(self) -> None:
        """Validate the alert configuration.
        
        Ensures that all required alert configurations are set properly.
        """
        try:
            # Validate thresholds
            if self.buy_threshold <= self.sell_threshold:
                self.logger.warning(f"Invalid threshold configuration: buy_threshold ({self.buy_threshold}) must be > sell_threshold ({self.sell_threshold})")
                
            # Validate cooldowns
            if self.alert_throttle < 0:
                self.logger.warning(f"Invalid alert_throttle: {self.alert_throttle}")
                
            if self.liquidation_cooldown < 0:
                self.logger.warning(f"Invalid liquidation_cooldown: {self.liquidation_cooldown}")
                
            # Validate Discord webhook URL if handlers require it
            if 'discord' in self.handlers and not self.discord_webhook_url:
                self.logger.warning("Discord handler is registered but webhook URL is not set")
                
            self.logger.debug("Alert configuration validated successfully")
            
        except Exception as e:
            self.logger.error(f"Error validating alert config: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _init_discord_webhook(self) -> None:
        """Initialize Discord webhook client."""
        try:
            if self.discord_webhook_url:
                # Clean up the URL in case there are any whitespace or newlines
                webhook_url = self.discord_webhook_url.strip()
                if webhook_url:
                    self.logger.debug(f"Initializing Discord webhook with URL: {webhook_url[:20]}...{webhook_url[-10:]}")
                    self.webhook = DiscordWebhook(url=webhook_url)
                    self.logger.info("Discord webhook initialized successfully")
                else:
                    self.logger.error("Discord webhook URL is empty after stripping")
            else:
                self.logger.warning("No Discord webhook URL configured")
                
        except Exception as e:
            self.logger.error(f"Error initializing Discord webhook: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    async def _send_discord_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to Discord webhook.
        
        Args:
            alert: Alert data
        """
        try:
            if not self.discord_webhook_url:
                self.logger.warning("Cannot send Discord alert: webhook URL not set")
                return
                
            # Extract alert data
            level = alert.get('level', 'INFO')
            message = alert.get('message', 'No message provided')
            details = alert.get('details', {})
            timestamp = alert.get('timestamp', time.time())
            
            # Format timestamp
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Determine alert color based on level
            color_map = {
                'INFO': 0x3498db,      # Blue
                'WARNING': 0xf39c12,   # Orange
                'ERROR': 0xe74c3c,     # Red
                'CRITICAL': 0x9b59b6   # Purple
            }
            color = color_map.get(level, 0x95a5a6)  # Default to gray
            
            # Create an embed for the alert
            embed = DiscordEmbed(
                title=f"{level} Alert",
                description=message,
                color=color
            )
            
            # Add timestamp
            embed.set_timestamp(dt.timestamp())
            
            # Add fields for details
            if details:
                # Limit to 10 fields to avoid Discord limits
                for i, (key, value) in enumerate(details.items()):
                    if i >= 10:
                        break
                    
                    # Format value and limit length
                    if isinstance(value, dict):
                        formatted_value = json.dumps(value, indent=2)[:1000]
                    else:
                        formatted_value = str(value)[:1000]
                    
                    embed.add_embed_field(
                        name=key,
                        value=f"```{formatted_value}```" if len(formatted_value) > 100 else formatted_value,
                        inline=False if len(formatted_value) > 100 else True
                    )
            
            # Create webhook and add embed
            webhook = DiscordWebhook(url=self.discord_webhook_url)
            webhook.add_embed(embed)
            
            # Send the webhook
            response = webhook.execute()
            
            # Log the result
            if response and hasattr(response, 'status_code'):
                if 200 <= response.status_code < 300:
                    self.logger.debug(f"Discord alert sent successfully with status code {response.status_code}")
                else:
                    self.logger.error(f"Failed to send Discord alert. Status code: {response.status_code}")
                    if hasattr(response, 'text'):
                        self.logger.error(f"Response text: {response.text}")
            else:
                self.logger.warning("No response received from Discord webhook")
                
        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    async def send_discord_webhook_message(self, message: Dict[str, Any], files: List[str] = None) -> None:
        """Send a message to Discord webhook.
        
        Args:
            message: Message data to send
            files: Optional list of file paths to attach
        """
        try:
            # Create a unique ID for this webhook message for tracking
            webhook_id = str(uuid.uuid4())[:8]
            
            if not self.discord_webhook_url:
                self.logger.warning(f"[WH:{webhook_id}] Cannot send Discord webhook message: webhook URL not set")
                return
                
            # Log message being sent (limit content preview to 50 chars)
            content_preview = message.get('content', '')[:50]
            self.logger.debug(f"[WH:{webhook_id}] Sending webhook with content: {content_preview}...")
            
            # Create webhook object
            webhook = DiscordWebhook(
                url=self.discord_webhook_url,
                content=message.get('content', ''),
                username=message.get('username', 'Virtuoso Alert')
            )
            
            # Process file attachments if provided
            if files:
                self.logger.info(f"[WH:{webhook_id}][FILES] Processing {len(files)} file attachment(s)")
                
                # Normalize file list to handle both string paths and dicts with file info
                normalized_files = []
                
                for i, file_item in enumerate(files):
                    self.logger.debug(f"[WH:{webhook_id}][FILES] Processing file {i+1}/{len(files)}: {file_item}")
                    
                    if isinstance(file_item, str):
                        # Simple path string
                        file_path = file_item
                        file_name = os.path.basename(file_path)
                        file_desc = None
                    elif isinstance(file_item, dict):
                        # Dictionary with file details
                        file_path = file_item.get('path')
                        file_name = file_item.get('filename', os.path.basename(file_path))
                        file_desc = file_item.get('description')
                    else:
                        self.logger.warning(f"[WH:{webhook_id}][FILES] Skipping invalid file item type: {type(file_item).__name__}")
                        continue
                    
                    # Check if file exists and is actually a file (not a directory)
                    if not file_path:
                        self.logger.warning(f"[WH:{webhook_id}][FILES] Invalid file path: {file_path}")
                        continue
                    
                    if not os.path.exists(file_path):
                        self.logger.warning(f"[WH:{webhook_id}][FILES] File not found: {file_path}")
                        continue
                    
                    if os.path.isdir(file_path):
                        self.logger.error(f"[WH:{webhook_id}][FILES] Error attaching file {file_path}: Is a directory")
                        continue
                        
                    # Check if file is empty or too large
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size == 0:
                            self.logger.warning(f"[WH:{webhook_id}][FILES] File is empty: {file_path}")
                            continue
                        
                        if file_size > 8 * 1024 * 1024:  # 8MB (Discord limit)
                            self.logger.warning(f"[WH:{webhook_id}][FILES] File too large ({file_size/1024/1024:.2f} MB): {file_path}")
                            continue
                            
                        self.logger.debug(f"[WH:{webhook_id}][FILES] File {file_path} validated, size: {file_size/1024:.2f} KB")
                    except Exception as size_err:
                        self.logger.warning(f"[WH:{webhook_id}][FILES] Error checking file size: {str(size_err)}")
                        
                    # Verify file type/headers for common formats
                    try:
                        with open(file_path, 'rb') as f:
                            header = f.read(8)  # Read first 8 bytes for file signature
                            
                        if file_path.lower().endswith('.pdf') and not header.startswith(b'%PDF'):
                            self.logger.warning(f"[WH:{webhook_id}][FILES] File has .pdf extension but doesn't have PDF header: {file_path}")
                        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')) and not any([
                            header.startswith(b'\x89PNG'),  # PNG
                            header.startswith(b'\xff\xd8\xff'),  # JPEG
                        ]):
                            self.logger.warning(f"[WH:{webhook_id}][FILES] File has image extension but doesn't have image header: {file_path}")
                            
                    except Exception as header_err:
                        self.logger.debug(f"[WH:{webhook_id}][FILES] Error checking file header: {str(header_err)}")
                        
                    normalized_files.append({
                        'path': file_path,
                        'name': file_name,
                        'description': file_desc
                    })
                
                # Add each file to the webhook
                successful_attachments = 0
                for file_info in normalized_files:
                    try:
                        self.logger.debug(f"[WH:{webhook_id}][FILES] Reading file: {file_info['path']}")
                        with open(file_info['path'], 'rb') as f:
                            file_content = f.read()
                            
                        self.logger.info(f"[WH:{webhook_id}][FILES] Attaching file: {file_info['name']} ({len(file_content)/1024:.2f} KB)")
                        webhook.add_file(file=file_content, filename=file_info['name'])
                        successful_attachments += 1
                    except Exception as e:
                        self.logger.error(f"[WH:{webhook_id}][FILES] Error attaching file {file_info['path']}: {str(e)}")
                        
                # Log summary of attachments
                self.logger.info(f"[WH:{webhook_id}][FILES] Successfully attached {successful_attachments}/{len(normalized_files)} files to webhook")
            
            # Send the webhook
            self.logger.debug(f"[WH:{webhook_id}] Executing webhook")
            response = webhook.execute()
            
            # Check response
            if response and hasattr(response, 'status_code'):
                if 200 <= response.status_code < 300:
                    self.logger.info(f"[WH:{webhook_id}] Discord webhook message sent successfully with status code {response.status_code}")
                else:
                    self.logger.warning(f"[WH:{webhook_id}] Discord webhook response with unexpected status: {response.status_code}")
                    if hasattr(response, 'text'):
                        self.logger.debug(f"[WH:{webhook_id}] Response text: {response.text}")
            else:
                self.logger.warning(f"[WH:{webhook_id}] No valid response from Discord webhook")
                
        except Exception as e:
            self.logger.error(f"Error sending Discord webhook message: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    def register_discord_handler(self) -> None:
        """Register Discord alert handler.
        
        This is a convenience method for registering the Discord handler.
        """
        try:
            self.logger.info("Registering Discord handler...")
            
            # Check if the Discord webhook URL is set
            if not self.discord_webhook_url:
                self.logger.error("Cannot register Discord handler: webhook URL not set")
                return
                
            # Register the handler
            self.register_handler('discord')
            self.logger.info("Discord handler registered successfully")
            
        except Exception as e:
            self.logger.error(f"Error registering Discord handler: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def start(self) -> None:
        """Start the alert manager.
        
        This method is called when the monitoring system starts.
        It initializes any necessary resources or connections.
        """
        try:
            self.logger.info("Starting AlertManager...")
            
            # Initialize HTTP client session if needed
            if not self._client_session or self._client_session.closed:
                self._client_session = aiohttp.ClientSession()
                self.logger.debug("Created new HTTP client session")
            
            # Re-initialize handlers to ensure they're properly set up
            self._initialize_handlers()
            
            # Re-initialize Discord webhook client
            self._init_discord_webhook()
            
            # Send startup notification (disabled to avoid noise)
            # await self.send_alert(
            #     level="INFO",
            #     message="🔄 Alert system started",
            #     details={"timestamp": time.time(), "startup": True}
            # )
            
            self.logger.info("AlertManager started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting AlertManager: {str(e)}")
            self.logger.error(traceback.format_exc())

    def ensure_handlers_registered(self) -> Dict[str, Any]:
        """
        Ensure that alert handlers are properly registered before attempting to send alerts.
        
        This is a defensive method that verifies handlers are available, and attempts
        to register them if they're not.
        
        Returns:
            Dict containing success status and any errors encountered
        """
        result = {"success": True, "errors": [], "handlers": []}
        
        # Check if handlers list exists and is not empty
        if not hasattr(self, 'handlers') or not self.handlers:
            self.logger.warning("No alert handlers registered")
            # Initialize handlers if not done yet
            if not hasattr(self, '_initialized_handlers') or not self._initialized_handlers:
                self.logger.info("Initializing handlers now")
                self._initialize_handlers()
            
            # Try to register Discord handler as fallback
            if 'discord' not in self.handlers and hasattr(self, 'discord_webhook_url') and self.discord_webhook_url:
                self.logger.info("Auto-registering Discord handler")
                try:
                    self.register_handler('discord')
                except Exception as e:
                    error_msg = f"Failed to register Discord handler: {str(e)}"
                    self.logger.error(error_msg)
                    result["errors"].append(error_msg)
                    result["success"] = False
        
        # Verify webhook URL if Discord handler is registered
        if 'discord' in self.handlers and (
                not hasattr(self, 'discord_webhook_url') or 
                not self.discord_webhook_url or 
                not isinstance(self.discord_webhook_url, str)
            ):
            error_msg = "Discord handler registered but webhook URL is invalid"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)
            result["success"] = False
        
        # Add registered handlers to result
        result["handlers"] = list(self.handlers.keys()) if hasattr(self, 'handlers') else []
        
        return result

    async def send_signal_alert(self, signal_data: Dict[str, Any]) -> None:
        """Send signal alert using the confluence alert mechanism.
        
        This is a wrapper around send_confluence_alert to maintain compatibility
        with the monitor.py implementation.
        
        Args:
            signal_data: Dictionary containing signal data with the following keys:
                - symbol: Trading pair symbol
                - confluence_score: The overall confluence score
                - components: Dictionary of component scores
                - results: Dictionary of detailed component results
                - weights: Dictionary of component weights
                - reliability: Confidence level (0-1)
                - buy_threshold: Threshold for buy signals
                - sell_threshold: Threshold for sell signals
                - price: Current price
        """
        # Extract transaction and signal IDs for logging
        transaction_id = signal_data.get('transaction_id', str(uuid.uuid4())[:8])
        signal_id = signal_data.get('signal_id', str(uuid.uuid4())[:8])
        
        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Preparing to send signal alert")
        
        # Check if PDF attachment is included in signal data
        pdf_path = signal_data.get('pdf_path')
        if pdf_path:
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Found PDF path in signal data: {pdf_path}")
            
            # Detailed PDF validation
            if not isinstance(pdf_path, str):
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Invalid PDF path type: {type(pdf_path).__name__}")
                pdf_path = None
            elif not os.path.exists(pdf_path):
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] PDF file does not exist: {pdf_path}")
                pdf_path = None
            elif os.path.isdir(pdf_path):
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] PDF path is a directory, not a file: {pdf_path}")
                pdf_path = None
            else:
                try:
                    file_size = os.path.getsize(pdf_path)
                    if file_size == 0:
                        self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] PDF file is empty (0 bytes): {pdf_path}")
                        pdf_path = None
                    elif file_size > 8 * 1024 * 1024:  # 8MB
                        self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] PDF file exceeds Discord limit ({file_size/1024/1024:.2f} MB): {pdf_path}")
                    else:
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Verified PDF file exists: {pdf_path}, size: {file_size/1024:.2f} KB")
                        
                        # Verify PDF header
                        try:
                            with open(pdf_path, 'rb') as f:
                                header = f.read(5)
                                if header[:4] != b'%PDF':
                                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] File does not appear to be a valid PDF: {pdf_path}")
                        except Exception as e:
                            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Error checking PDF header: {str(e)}")
                except Exception as e:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Error validating PDF file: {str(e)}")
                    pdf_path = None
                    
            # Update signal_data if PDF path was invalidated
            if pdf_path is None and 'pdf_path' in signal_data:
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Removing invalid PDF path from signal data")
                signal_data.pop('pdf_path', None)
        else:
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] No PDF path in signal data")
        
        # Process signal data and component scores
        try:
            # Save component data for future reference
            symbol = signal_data.get('symbol', 'UNKNOWN')
            
            # Use confluence_score consistently
            score = signal_data.get('confluence_score', 0)
            
            # Check the explicit signal_type from monitor.py if provided
            explicit_signal_type = signal_data.get('signal_type')
            
            # Determine the signal type based on thresholds if not explicitly provided
            buy_threshold = signal_data.get('buy_threshold', self.buy_threshold)
            sell_threshold = signal_data.get('sell_threshold', self.sell_threshold)
            
            if explicit_signal_type:
                signal_type = explicit_signal_type
            else:
                signal_type = 'BUY' if score > buy_threshold else 'SELL' if score < sell_threshold else 'NEUTRAL'
            
            # Skip sending alerts for NEUTRAL signals (regardless of score vs threshold)
            # This prevents alerts for signals labeled as NEUTRAL in the UI
            if signal_type == 'NEUTRAL' or (
                # Also skip any score in the neutral zone (between sell and buy thresholds)
                sell_threshold <= score <= buy_threshold
            ):
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Skipping alert for NEUTRAL signal on {symbol} (score: {score:.2f})")
                return
            
            # Save components to JSON file
            try:
                os.makedirs(os.path.join('exports', 'component_data', *symbol.split('/')), exist_ok=True)
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_path = os.path.join('exports', 'component_data', *symbol.split('/')) + f"_{signal_type}_{timestamp_str}.json"
                
                with open(json_path, 'w') as f:
                    json.dump(signal_data, f, indent=2, default=str)
                    
                self.logger.info(f"Saved component data to {os.path.abspath(json_path)}")
            except Exception as e:
                self.logger.error(f"Error saving component data to JSON: {str(e)}")
                
            # Send the main confluence alert
            alert_id = str(uuid.uuid4())[:8]
            await self.send_confluence_alert(
                symbol=symbol,
                confluence_score=score,  # Use the properly retrieved score
                components=signal_data.get('components', {}),
                results=signal_data.get('results', {}),
                weights=signal_data.get('weights', {}),
                reliability=signal_data.get('reliability', 0.8),
                price=signal_data.get('price'),
                # Add the missing enhanced data parameters
                market_interpretations=signal_data.get('market_interpretations'),
                actionable_insights=signal_data.get('actionable_insights'),
                influential_components=signal_data.get('influential_components'),
                top_weighted_subcomponents=signal_data.get('top_weighted_subcomponents'),
                # Also pass transaction_id and signal_id for tracking
                transaction_id=signal_data.get('transaction_id'),
                signal_id=signal_data.get('signal_id'),
                # Pass the explicit signal_type we determined
                signal_type=signal_type
            )
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][ALERT:{alert_id}] Successfully sent confluence alert for {symbol}")
            
            # Send PDF attachment as a separate message if available
            if pdf_path:
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Sending PDF attachment: {pdf_path}")
                
                # Create title based on signal type and score
                signal_emoji = "📈" if signal_type == "BUY" else "📉" if signal_type == "SELL" else "📊"
                title = f"{signal_emoji} {symbol} {signal_type} Signal Report (Score: {score:.1f})"
                
                # Create a message for the PDF attachment
                message = {
                    "content": f"{title}\nDetailed analysis report attached.",
                    "username": "Virtuoso Trading",
                }
                
                # Send the webhook with PDF file
                try:
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Calling send_discord_webhook_message with file: {pdf_path}")
                    await self.send_discord_webhook_message(message, files=[pdf_path])
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] PDF attachment sent successfully")
                except Exception as pdf_send_err:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Error sending PDF attachment: {str(pdf_send_err)}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] No valid PDF to attach")
            
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Successfully sent signal alert for {symbol}")
            
        except Exception as e:
            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error sending signal alert: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise