import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable, TYPE_CHECKING, Union
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
        self.buy_threshold = 60
        self.sell_threshold = 40
        
        # Alert tracking (no longer used for deduplication)
        self._last_alert_times = {}  # Symbol -> timestamp mapping for all alerts 
        self._deduplication_window = 0  # Deduplication disabled (was 5 seconds)
        self._alert_hashes = {}  # Hash -> timestamp mapping for content tracking
        self._last_liquidation_alert = {}  # Dictionary to track last liquidation alerts by symbol
        self._last_large_order_alert = {}  # Dictionary to track last large order alerts by symbol
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
            
            # Discord webhook
            if 'discord' in alert_config and 'webhook_url' in alert_config['discord']:
                self.discord_webhook_url = alert_config['discord']['webhook_url']
                print(f"CRITICAL DEBUG: Webhook URL from config: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            else:
                # Try to get from environment variable
                discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
                if discord_webhook_url:
                    # Fix potential newline issues
                    discord_webhook_url = discord_webhook_url.strip().replace('\n', '')
                    self.discord_webhook_url = discord_webhook_url
                    print(f"CRITICAL DEBUG: Webhook URL from environment: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            
            # Direct discord webhook from config
            if 'discord_network' in alert_config:
                self.discord_webhook_url = alert_config['discord_network']
                print(f"CRITICAL DEBUG: Webhook URL from discord_network: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            else:
                self.logger.warning("No Discord webhook URL found in config or environment")
                
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

    async def send_confluence_alert(
        self, 
        symbol: str, 
        confluence_score: float, 
        components: Dict[str, float], 
        results: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
        reliability: float = 0.0,
        buy_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None
    ) -> None:
        """Send a confluence-based signal alert (improved format with embeds).
        
        Args:
            symbol: Trading pair symbol
            confluence_score: Overall confluence score (0-100)
            components: Component scores dictionary
            results: Detailed result data from indicators
            weights: Optional component weights
            reliability: Signal reliability score (0-1)
            buy_threshold: Buy threshold value (if different from default)
            sell_threshold: Sell threshold value (if different from default)
        """
        try:
            # CRITICAL DEBUG: Starting confluence alert
            self.logger.critical(f"CRITICAL DEBUG: AlertManager.send_confluence_alert called for {symbol} with score {confluence_score:.2f}")
            
            # CRITICAL DEBUG: Verify handler state at start of confluence alert
            self.logger.critical(f"CRITICAL DEBUG: Verifying handler state in send_confluence_alert for {symbol}")
            debug_info = self.verify_handler_state()
            if debug_info["status"] == "NO_HANDLERS":
                self.logger.critical(f"CRITICAL DEBUG: No handlers registered at start of send_confluence_alert for {symbol}!")
                # Force re-register handlers if none found
                self.logger.critical(f"CRITICAL DEBUG: Attempting to force register Discord handler")
                self.register_discord_handler()
                self.logger.critical(f"CRITICAL DEBUG: After force registration, handlers: {self.handlers}")
            
            # CRITICAL DEBUG: Print the webhook URL and handler info
            print(f"CRITICAL DEBUG: Discord webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:] if self.discord_webhook_url else 'None'}")
            print(f"CRITICAL DEBUG: Handlers: {self.handlers}")
            print(f"CRITICAL DEBUG: Alert handlers: {list(self.alert_handlers.keys())}")
            
            # Enhanced debug logging for troubleshooting
            self.logger.info(f"🔔 ALERT ATTEMPT: Sending confluence alert for {symbol} with score {confluence_score:.2f}")
            self.logger.debug(f"Discord webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:] if self.discord_webhook_url else 'None'}")
            self.logger.debug(f"Handlers: {self.handlers}, alert_handlers: {list(self.alert_handlers.keys())}")
            
            # Log thresholds for verification
            if buy_threshold is None:
                buy_threshold = self.buy_threshold
            if sell_threshold is None:
                sell_threshold = self.sell_threshold
                
            self.logger.info(f"Using thresholds - Buy: {buy_threshold}, Sell: {sell_threshold}")
            self.logger.info(f"Score comparison - Score: {confluence_score:.2f}, Buy threshold: {buy_threshold}, Sell threshold: {sell_threshold}")
            
            # Determine signal type based on score and thresholds
            signal_type = "NEUTRAL"
            if confluence_score >= buy_threshold:
                signal_type = "BULLISH"
                self.logger.info(f"✅ Score {confluence_score:.2f} >= Buy threshold {buy_threshold} - Generating BULLISH signal")
                self.logger.critical(f"CRITICAL DEBUG: BUY CONDITION MET - Score {confluence_score:.2f} >= Buy threshold {buy_threshold}")
            elif confluence_score <= sell_threshold:
                signal_type = "BEARISH"
                self.logger.info(f"✅ Score {confluence_score:.2f} <= Sell threshold {sell_threshold} - Generating BEARISH signal")
                self.logger.critical(f"CRITICAL DEBUG: SELL CONDITION MET - Score {confluence_score:.2f} <= Sell threshold {sell_threshold}")
            else:
                self.logger.info(f"❌ Score {confluence_score:.2f} is in neutral zone - No signal generated")
                self.logger.critical(f"CRITICAL DEBUG: NEUTRAL ZONE - Score {confluence_score:.2f} is between thresholds")
                
            # Additional check - forcibly detect if we're above or below thresholds
            if confluence_score >= buy_threshold and signal_type != "BULLISH":
                self.logger.critical(f"CRITICAL DEBUG: INCONSISTENCY DETECTED - Score {confluence_score:.2f} >= Buy threshold {buy_threshold} but signal is {signal_type}")
                signal_type = "BULLISH"
                self.logger.critical(f"CRITICAL DEBUG: CORRECTED signal type to BULLISH")
            elif confluence_score <= sell_threshold and signal_type != "BEARISH":
                self.logger.critical(f"CRITICAL DEBUG: INCONSISTENCY DETECTED - Score {confluence_score:.2f} <= Sell threshold {sell_threshold} but signal is {signal_type}")
                signal_type = "BEARISH"
                self.logger.critical(f"CRITICAL DEBUG: CORRECTED signal type to BEARISH")
                
            # Create a content hash using symbol and signal type
            content_hash = f"{symbol}_{signal_type}_{int(confluence_score)}"
            
            self.logger.debug(f"ALERT TRACKING: Processing confluence alert for {symbol} with score {confluence_score:.2f}, type {signal_type}")
            self.logger.critical(f"CRITICAL DEBUG: Creating alert with hash {content_hash}")
                
            # Try to get the current price
            price = 0
            try:
                self.logger.critical(f"CRITICAL DEBUG: Attempting to get current price for {symbol}")
                price = await self._get_current_price(symbol)
                self.logger.debug(f"ALERT TRACKING: Got current price for {symbol}: {price}")
                self.logger.critical(f"CRITICAL DEBUG: Got price for {symbol}: {price}")
            except Exception as e:
                self.logger.warning(f"Failed to get price for {symbol}: {str(e)}")
                # Use reasonable fallbacks based on symbol
                if 'BTC' in symbol:
                    price = 60000.0
                elif 'ETH' in symbol:
                    price = 3000.0
                elif 'SOL' in symbol:
                    price = 100.0
                elif 'DOGE' in symbol:
                    price = 0.1
                else:
                    price = 50.0  # Generic fallback
                self.logger.warning(f"Using emergency fallback price for {symbol}: ${price}")
                self.logger.critical(f"CRITICAL DEBUG: Using fallback price for {symbol}: ${price}")
                
            # Prepare the signal object for formatting
            signal = {
                'symbol': symbol,
                'signal': signal_type,
                'confluence_score': confluence_score,
                'score': confluence_score,  # Alias for consistency
                'components': components,
                'results': results,
                'reliability': reliability,
                'price': price,
                'timestamp': int(time.time() * 1000),
                'content_hash': content_hash
            }
            
            # CRITICAL DEBUG: Log before sending alert
            self.logger.critical(f"CRITICAL DEBUG: About to call send_signal_alert for {symbol} with score {confluence_score:.2f}, type {signal_type}")
            
            # First try to send using direct enhanced confluence format
            try:
                if self.discord_webhook_url and 'discord' in self.handlers:
                    self.logger.info(f"📊 DIRECT ENHANCED ALERT: Sending directly using enhanced format for {symbol}")
                    
                    # Format the enhanced confluence message
                    webhook_message = self._format_enhanced_confluence_alert(signal)
                    
                    # Add Discord webhook identity details
                    webhook_message["username"] = "Virtuoso Trading Bot"
                    
                    # Send the webhook with the properly formatted embed structure
                    self.logger.info(f"📤 DISCORD SEND: Sending enhanced confluence alert for {symbol}")
                    await self.send_discord_webhook_message(webhook_message)
                    self.logger.info(f"✅ ENHANCED SUCCESS: Successfully sent enhanced Discord alert for {symbol}")
                    return
                else:
                    self.logger.info(f"⚠️ FALLBACK: No direct Discord webhook, will use standard signal_alert for {symbol}")
            except Exception as e:
                self.logger.warning(f"⚠️ ENHANCED ALERT FAILED: {str(e)}, falling back to standard alert method")
                self.logger.debug(traceback.format_exc())
            
            # Fallback: Send alert using the signal_alert method
            self.logger.debug(f"ALERT TRACKING: Calling send_signal_alert for {symbol}")
            success = await self.send_signal_alert(signal)
            
            if success:
                self.logger.info(f"Sent {signal_type} confluence alert for {symbol} with score {confluence_score:.2f}")
                self.logger.critical(f"CRITICAL DEBUG: Successfully sent {signal_type} confluence alert for {symbol}")
            else:
                self.logger.error(f"Failed to send confluence alert for {symbol}")
                self.logger.critical(f"CRITICAL DEBUG: FAILED to send confluence alert for {symbol}")
                
                # If failed but it's a significant alert, try one more time directly
                if (signal_type == "BULLISH" and confluence_score >= buy_threshold) or \
                   (signal_type == "BEARISH" and confluence_score <= sell_threshold):
                    self.logger.critical(f"CRITICAL DEBUG: Trying emergency direct alert for {symbol} due to threshold condition")
                    
                    try:
                        # Format a simple webhook message
                        simple_message = {
                            "content": f"⚠️ EMERGENCY ALERT: {signal_type} signal for {symbol} with score {confluence_score:.2f}",
                            "username": "Virtuoso Alerts"
                        }
                        
                        # Try to send it directly
                        if self.discord_webhook_url:
                            self.logger.critical(f"CRITICAL DEBUG: Sending emergency direct webhook for {symbol}")
                            await self.send_discord_webhook_message(simple_message)
                            self.logger.critical(f"CRITICAL DEBUG: Emergency direct webhook sent for {symbol}")
                    except Exception as e:
                        self.logger.error(f"Error in emergency direct alert: {str(e)}")
                        self.logger.critical(f"CRITICAL DEBUG: Error in emergency direct alert: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error in send_confluence_alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.logger.critical(f"CRITICAL DEBUG: Exception in send_confluence_alert: {str(e)}")
            self.logger.critical(traceback.format_exc())

    async def _init_client_session(self):
        """Initialize aiohttp client session if needed."""
        if self._client_session is None or self._client_session.closed:
            self.logger.info("Initializing aiohttp client session")
            self._client_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)  # 5 second timeout for API calls
            )

    async def _send_notifications(self, alert: Dict[str, Any]) -> None:
        """Send alert notifications through configured channels."""
        try:
            # Store alert in database
            await self._store_alert(alert)
            
            # Send to Discord if configured
            if self.discord_webhook_url:
                await self._send_discord_alert(alert)
            
        except Exception as e:
            self.logger.error(f"Error sending notifications: {str(e)}")

    async def _send_discord_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to Discord webhook."""
        try:
            # Debug log for troubleshooting
            self.logger.debug(f"_send_discord_alert called with level {alert.get('level')}")
            self.logger.debug(f"Discord webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:] if self.discord_webhook_url else 'None'}")
            
            if alert.get('level') == 'DEBUG':
                self.logger.debug("Skipping DEBUG level alert for Discord")
                return
            
            # Filter out ALL memory usage warnings - more comprehensive check
            message = alert.get('message', '').lower()
            if (alert.get('level') in ['WARNING', 'warning'] and 
                ('memory' in message or 'memory_usage' in message)):
                # Only allow critical memory alerts
                if 'critical' not in message.lower():
                    self.logger.debug(f"Skipping non-critical memory alert: {message}")
                    return
            
            # Check if this is a market summary with webhook message
            if alert.get('details', {}).get('type') == 'market_summary':
                webhook_message = alert.get('details', {}).get('webhook_message', {})
                if webhook_message:
                    async with aiohttp.ClientSession() as session:
                        # Add proper content-type header to avoid 405 errors
                        headers = {
                            'Content-Type': 'application/json',
                            'User-Agent': 'VirtuosoTradingBot/1.0'
                        }
                        try:
                            async with session.post(
                                self.discord_webhook_url,
                                json=webhook_message,
                                headers=headers
                            ) as response:
                                if response.status not in (200, 204):
                                    response_text = await response.text()
                                    self.logger.error(f"Discord API error: {response.status} - {response_text}")
                                    # Log more details about the request
                                    self.logger.debug(f"Discord webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:] if self.discord_webhook_url else 'None'}")
                                    self.logger.debug(f"Discord payload structure: {list(webhook_message.keys())}")
                                else:
                                    self.logger.info("Successfully sent Discord market summary")
                        except Exception as e:
                            self.logger.error(f"Error connecting to Discord: {str(e)}")
                    return
            
            # Special handling for confluence alerts to preserve box drawing characters
            if alert.get('details', {}).get('type') == 'confluence':
                # Create proper code block with the formatted table
                formatted_table = alert.get('message')
                if formatted_table:
                    # Make sure to wrap in code block to preserve formatting
                    discord_message = {
                        "content": f"```\n{formatted_table}\n```"
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.discord_webhook_url,
                            json=discord_message
                        ) as response:
                            if response.status not in (200, 204):
                                response_text = await response.text()
                                self.logger.error(f"Discord API error: {response.status} - {response_text}")
                            else:
                                self.logger.info("Successfully sent Discord confluence alert")
                    return
            
            # Handle regular alerts as before
            message = self._format_discord_message(alert)
            
            async with aiohttp.ClientSession() as session:
                # Add proper content-type header to avoid 405 errors
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'VirtuosoTradingBot/1.0'
                }
                try:
                    async with session.post(
                        self.discord_webhook_url,
                        json={"content": message},
                        headers=headers
                    ) as response:
                        if response.status not in (200, 204):
                            response_text = await response.text()
                            self.logger.error(f"Discord API error: {response.status} - {response_text}")
                        else:
                            self.logger.info(f"Successfully sent Discord alert: {alert.get('level')}")
                except Exception as e:
                    self.logger.error(f"Error connecting to Discord: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {str(e)}")

    def _get_level_color(self, level: str) -> int:
        """Get Discord embed color for alert level."""
        colors = {
            'DEBUG': 0x808080,    # Gray
            'INFO': 0x00FF00,     # Green
            'WARNING': 0xFFFF00,  # Yellow
            'ERROR': 0xFF0000,    # Red
            'CRITICAL': 0x7F0000  # Dark Red
        }
        return colors.get(level.upper(), 0x000000)

    async def _store_alert(self, alert: Dict[str, Any]) -> None:
        """Store alert in database."""
        try:
            if not self.database:
                self.logger.warning("No database configured for alert storage")
                return
            
            # Add timestamp if not present
            if 'timestamp' not in alert:
                alert['timestamp'] = int(time.time() * 1000)
            
            # Store in database
            await self.database.write_alert(alert)
            
        except Exception as e:
            self.logger.error(f"Error storing alert: {str(e)}")

    def register_discord_handler(self):
        """Register Discord handler if not already registered."""
        # Check if discord handler is already registered
        if 'discord' not in self.handlers:
            # Debug the webhook URL
            if self.discord_webhook_url:
                print(f"REGISTERING DISCORD: URL starts with {self.discord_webhook_url[:30]}...")
                print(f"REGISTERING DISCORD: URL ends with ...{self.discord_webhook_url[-30:]}")
                print(f"REGISTERING DISCORD: URL length: {len(self.discord_webhook_url)}")
                print(f"REGISTERING DISCORD: URL hex: {' '.join([hex(ord(c))[2:] for c in self.discord_webhook_url[:30]])}")
                # Check if there are any line breaks or other special characters
                special_chars = [c for c in self.discord_webhook_url if ord(c) < 32 or ord(c) > 126]
                if special_chars:
                    print(f"REGISTERING DISCORD: WARNING - URL contains special characters: {special_chars}")
                
                # Try to test the webhook URL is valid
                import re
                if re.match(r'^https://discord\.com/api/webhooks/\d+/.+$', self.discord_webhook_url):
                    print("REGISTERING DISCORD: URL format appears valid")
                else:
                    print("REGISTERING DISCORD: WARNING - URL format doesn't match expected pattern")
                    
                # Clean the URL again just to be sure
                self.discord_webhook_url = self.discord_webhook_url.strip().replace('\n', '')
            else:
                print("REGISTERING DISCORD: No webhook URL available")
            
            self.register_handler('discord')
            self.logger.info("Registered Discord handler via register_discord_handler method")

    def _format_discord_message(self, alert: Dict[str, Any]) -> str:
        """Format alert for Discord message.
        
        Args:
            alert: Alert dictionary containing level, message, and details
            
        Returns:
            Formatted message string
        """
        try:
            level = alert.get('level', 'INFO').upper()
            message = alert.get('message', '')
            details = alert.get('details', {})
            
            # Add emoji based on level
            level_emoji = {
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '🚨',
                'CRITICAL': '💥'
            }
            emoji = level_emoji.get(level, 'ℹ️')
            
            # Format confluence threshold alerts
            if details.get('type') == 'confluence':
                # If we have a formatted table, use it directly in a code block
                if 'formatted_table' in details:
                    return f"```{details['formatted_table']}```"
                
                symbol = details.get('symbol', 'UNKNOWN')
                signal = details.get('signal', 'UNKNOWN')
                score = details.get('score', 0.0)
                reliability = details.get('reliability', 0.0) * 100  # Convert to percentage
                
                # Create formatted message with components
                components = details.get('components', {})
                
                emoji = "🔴" if signal == "BEARISH" else "🟢" if signal == "BULLISH" else "🟡"
                
                return (
                    f"{emoji} **{signal} CONFLUENCE ALERT - {symbol}**\n"
                    f"**Score:** {score:.2f}\n"
                    f"**Reliability:** {reliability:.0f}%\n\n"
                    f"```{message}```\n"
                )
                
            # Format liquidation alerts with enhanced styling
            if details.get('type') == 'liquidation':
                # No need to add extra processing here - the message is already formatted 
                # with Discord markdown in the check_liquidation_threshold method
                return message
            
            # Format signal alerts - ALWAYS use risk management format for consistent alerts
            if details.get('type') == 'signal':
                # Extract details for risk management format
                symbol = details.get('symbol', 'UNKNOWN')
                signal_type = details.get('signal', 'UNKNOWN').upper()
                score = details.get('score', 0.0)
                price = details.get('price', 0.0)
                
                # Create signal dictionary with all needed fields for risk management format
                signal_data = {
                    'symbol': symbol,
                    'signal': signal_type,
                    'score': score, 
                    'confluence_score': score,
                    'price': price,
                    'alert_style': 'risk_management',
                    'components': details.get('components', {}),
                    'interpretations': details.get('interpretations', {}),
                    'timestamp': details.get('timestamp', int(time.time() * 1000))
                }
                
                # Use risk management format
                return self._format_risk_management_alert(signal_data)
            
            # Format market summary alerts
            if details.get('type') == 'market_summary':
                return alert.get('message', '')
            
            # Special formatting for large aggressive orders
            if details.get('type') == 'large_aggressive_order':
                symbol = details.get('symbol', 'UNKNOWN')
                side = details.get('side', 'UNKNOWN')
                size = details.get('size', 0.0)
                usd_value = details.get('usd_value', 0.0)
                price = details.get('price', 0.0)
                base_currency = symbol.split('-')[0] if '-' in symbol else ''
                
                timestamp = datetime.fromtimestamp(
                    details.get('timestamp', time.time())
                ).strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Format aggressive bids/asks counts
                aggressive_bids = len(details.get('aggressive_bids', []))
                aggressive_asks = len(details.get('aggressive_asks', []))
                
                return (
                    f"🚨 **Large {side.upper()} Order Detected**\n"
                    f"**Symbol:** {symbol}\n"
                    f"**Time:** {timestamp}\n\n"
                    f"**Size:** {size:.3f} {base_currency}\n"
                    f"**USD Value:** ${usd_value:,.2f}\n"
                    f"**Price:** ${price:,.2f}\n"
                    f"**Orders:** {aggressive_bids} bids, {aggressive_asks} asks\n\n"
                    f"*This may indicate significant market pressure*"
                )
            
            # Special formatting for memory alerts
            if 'memory usage' in message.lower():
                # Split the message into lines
                lines = message.split('\n')
                
                # Format the first line as a header
                header = lines[0] if lines else "Memory Alert"
                
                # Format the rest as details
                details_text = '\n'.join(lines[1:]) if len(lines) > 1 else ""
                
                return (
                    f"{emoji} **{header}**\n"
                    f"```\n{details_text}```\n"
                    f"*Check system resources and consider restarting if necessary*"
                )
            
            # Default formatting for other alerts
            formatted_msg = f"{emoji} **{level}**\n"
            if alert.get('message', ''):
                formatted_msg += f"```\n{alert.get('message', '')}```"
            
            return formatted_msg
            
        except Exception as e:
            self.logger.error(f"Error formatting Discord message: {str(e)}")
            self.logger.error(traceback.format_exc())
            return f"🚨 Error: Failed to format alert message"

    def _has_discord_config(self) -> bool:
        """Check if Discord webhook is configured."""
        return bool(self.discord_webhook_url)

    async def send_discord_webhook_message(self, webhook_message: Dict[str, Any]) -> None:
        """Send a message directly to Discord webhook.
        
        This method is specifically designed for sending pre-formatted webhook messages
        like those used in the market reporter.
        
        Args:
            webhook_message: A dictionary containing the webhook payload to send to Discord
        """
        try:
            # CRITICAL DEBUG: Starting Discord webhook send
            self.logger.critical(f"CRITICAL DEBUG: Entered send_discord_webhook_message")
            
            # ALERT PIPELINE DEBUG: Verify we have content before attempting to send
            if not webhook_message:
                self.logger.error("ALERT DEBUG: Empty webhook message provided to send_discord_webhook_message")
                return
                
            if not isinstance(webhook_message, dict):
                self.logger.error(f"ALERT DEBUG: Invalid webhook message type: {type(webhook_message)}")
                return
                
            if "content" not in webhook_message and "embeds" not in webhook_message:
                self.logger.error(f"ALERT DEBUG: Webhook message missing both content and embeds: {webhook_message}")
                return
                
            # Verify Discord webhook URL validity
            if not self.discord_webhook_url:
                self.logger.error("DISCORD ERROR: Cannot send Discord webhook message: No webhook URL configured")
                
                # Add to error tracking
                self._discord_errors.append({
                    "timestamp": time.time(),
                    "error": "NO_WEBHOOK_URL",
                    "message_keys": list(webhook_message.keys())
                })
                return
                
            self.logger.info(f"DISCORD WEBHOOK: Starting webhook message to Discord")
            self.logger.debug(f"DISCORD DEBUG: Webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
            self.logger.debug(f"DISCORD DEBUG: Message keys: {list(webhook_message.keys())}")
            
            # ALERT PIPELINE DEBUG: Log message content for debugging
            if "content" in webhook_message:
                self.logger.info(f"ALERT DEBUG: Webhook content: {webhook_message['content'][:100]}{'...' if len(webhook_message['content']) > 100 else ''}")
            if "embeds" in webhook_message:
                embed_titles = [e.get("title", "No title") for e in webhook_message.get("embeds", [])]
                self.logger.info(f"ALERT DEBUG: Webhook embeds: {embed_titles}")
            
            # CRITICAL DEBUG: Log webhook URL and content
            webhook_url = self.discord_webhook_url.strip().replace('\n', '')
            self.logger.critical(f"CRITICAL DEBUG: Using webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
            self.logger.critical(f"CRITICAL DEBUG: Message has keys: {list(webhook_message.keys())}")
            
            # Clean the URL again just to be sure
            webhook_url = self.discord_webhook_url.strip().replace('\n', '')
            
            if not webhook_url:
                self.logger.error("DISCORD ERROR: Webhook URL is empty after cleaning")
                
                # Add to error tracking
                self._discord_errors.append({
                    "timestamp": time.time(),
                    "error": "EMPTY_WEBHOOK_URL_AFTER_CLEANING",
                    "original_url_length": len(self.discord_webhook_url) if self.discord_webhook_url else 0
                })
                return
                
            self.logger.info(f"DISCORD WEBHOOK: URL length after cleaning: {len(webhook_url)}")
            
            # ALERT PIPELINE DEBUG: Verify webhook URL format
            if not webhook_url.startswith("https://discord.com/api/webhooks/"):
                self.logger.error(f"ALERT DEBUG: Webhook URL has invalid format: {webhook_url[:20]}...{webhook_url[-10:]}")
                
                # Add to error tracking
                self._discord_errors.append({
                    "timestamp": time.time(),
                    "error": "INVALID_WEBHOOK_URL_FORMAT",
                    "url_prefix": webhook_url[:30]
                })
            
            # Try to make the HTTP request
            max_retries = 3
            retry_count = 0
            last_error = None

            # CRITICAL DEBUG: Attempting webhook send
            self.logger.critical(f"CRITICAL DEBUG: Starting HTTP request to Discord webhook")
            
            # Implement a retry loop to handle temporary network issues
            while retry_count < max_retries:
                self.logger.critical(f"CRITICAL DEBUG: Discord webhook attempt {retry_count+1}/{max_retries}")
                try:
                    # CRITICAL DEBUG: Creating HTTP session
                    self.logger.critical(f"CRITICAL DEBUG: Creating aiohttp session (attempt {retry_count+1}/{max_retries})")
                    
                    # Create a new session for each attempt
                    async with aiohttp.ClientSession() as session:
                        # Add proper content-type header to avoid 405 errors
                        headers = {
                            'Content-Type': 'application/json',
                            'User-Agent': 'VirtuosoTradingBot/1.0'
                        }
                        
                        self.logger.debug(f"DISCORD DEBUG: Created client session with headers {headers}")
                        
                        # Log the status of the webhook URL
                        webhook_url_masked = f"{webhook_url[:20]}...{webhook_url[-10:]}"
                        self.logger.info(f"DISCORD WEBHOOK: Sending to webhook URL: {webhook_url_masked}")
                        
                        # Prepare the webhook message
                        if isinstance(webhook_message, dict):
                            self.logger.info(f"DISCORD WEBHOOK: Sending webhook request as JSON")
                            
                            # CRITICAL DEBUG: About to send POST request
                            self.logger.critical(f"CRITICAL DEBUG: About to send POST request to Discord webhook")
                            
                            # Dump JSON for debugging - Added for troubleshooting
                            try:
                                import json
                                json_str = json.dumps(webhook_message)
                                self.logger.debug(f"WEBHOOK JSON: {json_str[:200]}...")
                            except Exception as json_err:
                                self.logger.warning(f"Error dumping webhook JSON: {str(json_err)}")
                            
                            # Actually send the webhook
                            self.logger.info(f"DISCORD WEBHOOK: Sending webhook request...")
                            async with session.post(
                                webhook_url,
                                json=webhook_message,
                                headers=headers,
                                timeout=10.0  # Add a timeout to prevent hanging
                            ) as response:
                                response_status = response.status
                                response_text = await response.text()
                                self.logger.info(f"DISCORD WEBHOOK: Got response status {response_status}")
                                self.logger.debug(f"DISCORD DEBUG: Response text: {response_text[:100]}")
                                
                                # CRITICAL DEBUG: Got response
                                self.logger.critical(f"CRITICAL DEBUG: Got Discord API response - status: {response_status}")
                                self.logger.critical(f"CRITICAL DEBUG: Response text: {response_text[:200]}")
                                
                                if response.status in (200, 204):
                                    self.logger.info(f"DISCORD WEBHOOK: Successfully sent Discord webhook message")
                                    self.logger.critical(f"CRITICAL DEBUG: Discord webhook message sent SUCCESSFULLY")
                                    return  # Success! Exit the function
                                else:
                                    self.logger.error(f"DISCORD ERROR: Discord API error ({response.status}): {response_text}")
                                    
                                    # CRITICAL DEBUG: API error details
                                    self.logger.critical(f"CRITICAL DEBUG: Discord API ERROR: {response.status} - {response_text}")
                                    
                                    # Store the error for potential retry
                                    last_error = f"HTTP {response.status}: {response_text}"
                                    
                                    # Don't retry if it's a 4xx error other than 429 (rate limit)
                                    if response.status >= 400 and response.status < 500 and response.status != 429:
                                        self.logger.error(f"DISCORD ERROR: Not retrying due to client error: {response.status}")
                                        break  # Exit the retry loop
                except aiohttp.ClientConnectorError as conn_err:
                    self.logger.error(f"DISCORD ERROR: Connection error: {str(conn_err)}")
                    last_error = f"Connection error: {str(conn_err)}"
                    self.logger.critical(f"CRITICAL DEBUG: Connection error in Discord webhook: {str(conn_err)}")
                except aiohttp.ClientError as client_err:
                    self.logger.error(f"DISCORD ERROR: Client error: {str(client_err)}")
                    last_error = f"Client error: {str(client_err)}"
                    self.logger.critical(f"CRITICAL DEBUG: Client error in Discord webhook: {str(client_err)}")
                except asyncio.TimeoutError:
                    self.logger.error("DISCORD ERROR: Request timed out")
                    last_error = "Request timed out"
                    self.logger.critical("CRITICAL DEBUG: Timeout error in Discord webhook")
                except Exception as e:
                    self.logger.error(f"DISCORD ERROR: Unexpected error: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    last_error = f"Unexpected error: {str(e)}"
                    self.logger.critical(f"CRITICAL DEBUG: Unexpected error in Discord webhook: {str(e)}")
                    self.logger.critical(traceback.format_exc())
                
                # Increment retry counter
                retry_count += 1
                
                # Log the retry attempt
                if retry_count < max_retries:
                    self.logger.info(f"DISCORD WEBHOOK: Retrying webhook request (attempt {retry_count+1}/{max_retries})")
                    await asyncio.sleep(1)  # Short delay before retry
                else:
                    self.logger.error(f"DISCORD ERROR: Failed to send webhook after {max_retries} attempts")
                    
                    # Add to error tracking
                    self._discord_errors.append({
                        "timestamp": time.time(),
                        "error": "MAX_RETRIES_EXCEEDED",
                        "last_error": last_error
                    })
                    
                    # CRITICAL DEBUG: Log failure after max retries
                    self.logger.critical(f"CRITICAL DEBUG: Discord webhook failed after {max_retries} attempts: {last_error}")
            
        except Exception as e:
            self.logger.error(f"DISCORD ERROR: Failed to send Discord webhook: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # CRITICAL DEBUG: Log the critical error
            self.logger.critical(f"CRITICAL DEBUG: Critical error in send_discord_webhook_message: {str(e)}")
            
            # Add to error tracking
            self._discord_errors.append({
                "timestamp": time.time(),
                "error": "CRITICAL_ERROR",
                "exception": str(e)
            })

    async def process_signals(self, signals: List[Dict[str, Any]]) -> None:
        """Process trading signals and send alerts."""
        try:
            if not signals:
                self.logger.warning("📊 PROCESS SIGNALS: No signals provided to process")
                return
                
            self.logger.info(f"📊 PROCESS SIGNALS: Processing {len(signals)} signals")
            
            # Print available handlers
            self.logger.info(f"📊 PROCESS SIGNALS: Available handlers: {self.handlers}")
            
            # Check for Discord webhook URL
            if 'discord' in self.handlers:
                webhook_url = self.discord_webhook_url or ""
                self.logger.info(f"📊 PROCESS SIGNALS: Discord webhook URL available: {bool(webhook_url)}")
                if webhook_url:
                    self.logger.debug(f"📊 PROCESS SIGNALS: Discord webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
            
            # Process each signal
            for i, signal in enumerate(signals):
                try:
                    symbol = signal.get('symbol', 'UNKNOWN')
                    score = signal.get('score', signal.get('confluence_score', 0))
                    signal_type = signal.get('signal', 'UNKNOWN')
                    
                    self.logger.info(f"📊 PROCESS SIGNALS: Processing signal {i+1}/{len(signals)} - {symbol} {signal_type} {score:.2f}")
                    await self.send_signal_alert(signal)
                except Exception as e:
                    self.logger.error(f"📊 PROCESS SIGNALS: Error processing individual signal: {str(e)}")
                    self.logger.error(traceback.format_exc())
        except Exception as e:
            self.logger.error(f"📊 PROCESS SIGNALS: Error processing signals: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def process_signal(self, signal_data: Dict[str, Any]) -> None:
        """Process a trading signal and send alerts if thresholds are met."""
        try:
            # Extract key signal properties with defaults
            symbol = signal_data.get('symbol', 'UNKNOWN')
            
            # Handle different score field names
            score = 0
            for score_field in ['score', 'confluence_score']:
                if score_field in signal_data:
                    score = float(signal_data[score_field])
                    break
            
            # Handle different signal type field names
            signal_type = None
            for signal_field in ['signal', 'direction', 'signal_type']:
                if signal_field in signal_data:
                    signal_type = signal_data[signal_field]
                    break
            
            if signal_type is None:
                # Determine signal type from score
                if 'buy_threshold' in signal_data and 'sell_threshold' in signal_data:
                    buy_threshold = signal_data['buy_threshold']
                    sell_threshold = signal_data['sell_threshold']
                    
                    if score >= buy_threshold:
                        signal_type = 'BUY'
                    elif score <= sell_threshold:
                        signal_type = 'SELL'
                    else:
                        signal_type = 'NEUTRAL'
                else:
                    # Default thresholds
                    if score >= 60:
                        signal_type = 'BUY'
                    elif score <= 40:
                        signal_type = 'SELL'
                    else:
                        signal_type = 'NEUTRAL'
            
            # Normalize signal type to uppercase
            signal_type = str(signal_type).upper()
            
            # Log the signal details
            self.logger.info(f"📈 PROCESS SIGNAL: Processing signal: {symbol} - {signal_type} - {score}")
            
            # Check if we have any handlers registered
            if not self.handlers:
                self.logger.error(f"📈 PROCESS SIGNAL: No alert handlers registered for {symbol}")
                return
                
            self.logger.info(f"📈 PROCESS SIGNAL: Available handlers: {self.handlers}")
            
            # Deduplication is disabled now
            self.logger.info(f"📈 PROCESS SIGNAL: Deduplication disabled - processing all signals for {symbol} (score: {score:.2f}, type: {signal_type})")
            
            # Make a copy to avoid modifying the original
            signal = signal_data.copy()
            
            # Ensure required fields are set
            signal['symbol'] = symbol
            signal['score'] = score
            signal['signal'] = signal_type
            
            # Set timestamp if not present
            if 'timestamp' not in signal:
                signal['timestamp'] = int(time.time() * 1000)
                
            # Determine if signal meets thresholds for alerting
            meets_threshold = False
            if signal_type in ['BUY', 'BULLISH'] and score >= self.buy_threshold:
                meets_threshold = True
                self.logger.info(f"Signal meets thresholds - sending {signal_type} alert for {symbol} (score: {score:.2f})")
            elif signal_type in ['SELL', 'BEARISH'] and score <= self.sell_threshold:
                meets_threshold = True
                self.logger.info(f"Signal meets thresholds - sending {signal_type} alert for {symbol} (score: {score:.2f})")
            else:
                self.logger.info(f"Signal does not meet thresholds - no alert for {symbol} (score: {score:.2f}, type: {signal_type})")
                
            # Send the alert if it meets thresholds
            if meets_threshold:
                await self.send_signal_alert(signal)
                
        except Exception as e:
            self.logger.error(f"Error processing signal: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def send_signal_alert(self, signal: Dict[str, Any]) -> bool:
        """Send signal alert through configured handlers"""
        try:
            symbol = signal.get('symbol', 'Unknown')
            score = signal.get('score', 0)
            signal_type = signal.get('signal', 'unknown').upper()
            
            # CRITICAL DEBUG: Starting signal alert
            self.logger.critical(f"CRITICAL DEBUG: AlertManager.send_signal_alert called for {symbol} with score {score:.2f}, type {signal_type}")
            
            # CRITICAL DEBUG: Verify handler state before processing
            self.logger.critical(f"CRITICAL DEBUG: Verifying handler state before sending alert")
            debug_info = self.verify_handler_state()
            if debug_info["status"] == "NO_HANDLERS":
                self.logger.critical(f"CRITICAL DEBUG: No handlers registered at start of send_signal_alert!")
            
            # Enhanced debug logging for troubleshooting
            self.logger.info(f"🚨 SIGNAL ALERT: Processing signal for {symbol} with score {score:.2f}, type {signal_type}")
            self.logger.debug(f"DISCORD DEBUG: Webhook URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:] if self.discord_webhook_url else 'None'}")
            
            # DETAILED EXECUTION TRACKING - Added for debugging alert flow
            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 1 - Beginning signal processing for {symbol}")
            
            # Check if there are any registered handlers
            if not self.handlers:
                self.logger.error(f"🚨 SIGNAL ALERT: No alert handlers registered! Cannot send alerts for {symbol}")
                
                # CRITICAL DEBUG: Extra debug info on missing handlers
                if self.discord_webhook_url:
                    self.logger.critical(f"CRITICAL DEBUG: Discord webhook URL exists but handlers are empty! URL: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
                    # Try force registering Discord handler
                    self.register_handler('discord')
                    self.logger.critical(f"CRITICAL DEBUG: After force handler registration, handlers: {self.handlers}")
                    
                    # If still no handlers, log critical error
                    if not self.handlers:
                        self.logger.critical(f"CRITICAL DEBUG: Handler registration failed! Still no handlers after attempt.")
                        return False
                else:
                    self.logger.critical("CRITICAL DEBUG: No Discord webhook URL configured!")
                    return False
                
            # Log current handlers for debugging
            self.logger.info(f"🚨 SIGNAL ALERT: Using handlers: {self.handlers}, alert_handlers: {list(self.alert_handlers.keys())}")
            
            # DETAILED EXECUTION TRACKING - Added for debugging alert flow
            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 2 - Handlers validated for {symbol}")
            
            # Create a content hash for compatibility with downstream systems
            # but do not use it for deduplication
            content_hash = signal.get('content_hash')
            if not content_hash:
                # Create a more detailed hash based on symbol, type and score
                content_hash = f"{symbol}_{signal_type}_{int(score)}"
                signal['content_hash'] = content_hash
            
            # Store timing info for debugging but don't use for deduplication
            self._last_alert_times[symbol] = int(time.time())
            
            # Deduplication is disabled - no check for duplicates
            self.logger.info(f"🚨 SIGNAL ALERT: Processing signal for {symbol} (score: {score:.2f}, type: {signal_type})")
            
            # DETAILED EXECUTION TRACKING - Added for debugging alert flow
            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 3 - About to process signal with handlers for {symbol}")
            
            # Still store hash for tracking but don't use for deduplication
            self._alert_hashes[content_hash] = int(time.time())
            
            # Always include risk management format for signals
            self.logger.info(f"🚨 SIGNAL ALERT: Using risk management format for {symbol}")
            
            # Send to all configured handlers
            success = True
            for handler_name in self.handlers:
                self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 4 - Processing handler: {handler_name} for {symbol}")
                self.logger.info(f"🔄 SIGNAL HANDLER: Processing handler: {handler_name}")
                
                if handler_name == 'discord':
                    if self.discord_webhook_url:
                        try:
                            # CRITICAL DEBUG: Log before message formatting
                            self.logger.critical(f"CRITICAL DEBUG: Formatting webhook message for {symbol}")
                            
                            # Format the webhook message with embeds
                            self.logger.info(f"📝 DISCORD FORMAT: Creating Discord embed for {symbol}")
                            
                            # Determine if this is a confluence signal and use the enhanced format if so
                            if 'confluence_score' in signal and 'components' in signal and 'results' in signal:
                                self.logger.info(f"📊 USING ENHANCED CONFLUENCE FORMAT: Detected confluence analysis for {symbol}")
                                webhook_message = self._format_enhanced_confluence_alert(signal)
                            else:
                                # Use the standard risk management format for other signals
                                webhook_message = self._format_risk_management_alert(signal)
                            
                            # CRITICAL DEBUG: Check formatted webhook message
                            self.logger.critical(f"CRITICAL DEBUG: Webhook message keys: {list(webhook_message.keys())}")
                            if 'embeds' in webhook_message:
                                self.logger.critical(f"CRITICAL DEBUG: Webhook has {len(webhook_message['embeds'])} embeds")
                            
                            # Add Discord webhook identity details
                            webhook_message["username"] = "Virtuoso Alerts"
                           
                            # DETAILED EXECUTION TRACKING - Added for debugging alert flow
                            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 5 - Webhook message formatted for {symbol}")
                            
                            # Final check for Discord webhook URL
                            if not self.discord_webhook_url:
                                self.logger.error(f"❌ DISCORD ERROR: Discord webhook URL is empty or invalid")
                                success = False
                                continue
                                
                            # Send the webhook with the properly formatted embed structure
                            self.logger.info(f"📤 DISCORD SEND: Sending webhook message for {symbol}")
                            
                            # CRITICAL DEBUG: Log right before webhook send
                            self.logger.critical(f"CRITICAL DEBUG: About to call send_discord_webhook_message for {symbol}")
                            
                            # DETAILED EXECUTION TRACKING - Added for debugging alert flow
                            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 6 - About to send webhook for {symbol}")
                            
                            await self.send_discord_webhook_message(webhook_message)
                            self.logger.info(f"✅ DISCORD SUCCESS: Successfully sent Discord alert for {symbol}")
                            
                            # CRITICAL DEBUG: Log success after webhook send
                            self.logger.critical(f"CRITICAL DEBUG: Successfully completed send_discord_webhook_message for {symbol}")
                            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 7 - Webhook sent successfully for {symbol}")
                        except Exception as e:
                            self.logger.error(f"❌ DISCORD ERROR: Error sending Discord alert: {str(e)}")
                            self.logger.error(traceback.format_exc())
                            
                            # CRITICAL DEBUG: Log error details
                            self.logger.critical(f"CRITICAL DEBUG: Exception in Discord alert: {str(e)}")
                            self.logger.critical(traceback.format_exc())
                            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 7 - ERROR sending webhook for {symbol}: {str(e)}")
                            
                            success = False
                    else:
                        self.logger.error(f"❌ DISCORD ERROR: No webhook URL configured")
                        success = False
                else:
                    self.logger.warning(f"⚠️ SIGNAL HANDLER: Unknown handler: {handler_name}")
        
            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT 8 - Signal alert processing completed for {symbol} with success={success}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending signal alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.logger.critical(f"CRITICAL DEBUG: EXECUTION POINT ERROR - Exception in send_signal_alert: {str(e)}")
            return False

    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        """Format signal data into alert message"""
        # Check if a specific alert style is requested
        alert_style = signal.get('alert_style', 'default')
        
        # First, ensure we have a valid price
        price = signal.get('price', 0)
        if price <= 0:
            # Try to get the price if it's missing
            symbol = signal.get('symbol', 'Unknown')
            try:
                # Get price using synchronous code (event loop might be running)
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a new loop in a separate thread to get the price
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._get_current_price(symbol))
                        new_price = future.result()
                else:
                    # Use existing event loop
                    new_price = asyncio.run(self._get_current_price(symbol))
                    
                # Update the signal with the fetched price
                if new_price > 0:
                    signal['price'] = new_price
                    self.logger.info(f"Updated price for {symbol}: ${new_price}")
            except Exception as e:
                self.logger.error(f"Error fetching price in _format_signal_message: {str(e)}")
        
        # Use appropriate formatter based on style
        if alert_style == 'risk_management':
            # Force risk management style if explicitly requested, even with zero price
            formatted_message = self._format_risk_management_alert(signal)
            # If the standard format was returned instead, log it
            if "TRADE ALERT" not in formatted_message:
                self.logger.warning("Risk management format requested but standard format returned")
            return formatted_message
            
        # Call standard formatter for default style
        return self._format_standard_alert(signal)
    
    def _format_standard_alert(self, signal: Dict[str, Any]) -> str:
        """Standard format for signal alerts (extracted from original _format_signal_message)"""
        symbol = signal.get('symbol', 'Unknown')
        signal_type = signal.get('signal', 'Unknown').upper()
        score = signal.get('confluence_score', signal.get('score', 0))
        price = signal.get('price', 0)
        timestamp = datetime.fromtimestamp(signal.get('timestamp', int(time.time() * 1000)) / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Determine emoji based on signal
        emoji = "🟢" if signal_type.lower() in ['buy', 'bullish'] else "🔴" if signal_type.lower() in ['sell', 'bearish'] else "🟡"
        
        # Format the base message
        message = (
            f"{emoji} **SIGNAL ALERT** {emoji}\n"
            f"**Symbol:** {symbol}\n"
            f"**Signal:** {signal_type}\n"
            f"**Score:** {score:.2f}\n"
            f"**Price:** ${price:.2f}\n"
            f"**Time:** {timestamp}\n\n"
        )
        
        # Add interpretations if available
        interpretations = signal.get('interpretations', {})
        if interpretations:
            message += "**Analysis:**\n"
            for component, interpretation in interpretations.items():
                # Make component name more readable
                component_name = component.replace('_', ' ').title()
                message += f"• **{component_name}:** {interpretation}\n"
        
        return message

    def _format_risk_management_alert(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Format signal using Risk Management Style alert with Discord embeds
        
        Returns:
            Dict containing the formatted Discord webhook payload with embeds
        """
        symbol = signal.get('symbol', 'Unknown')
        signal_type = signal.get('signal', 'Unknown').upper()
        score = signal.get('confluence_score', signal.get('score', 0))
        price = signal.get('price', 0)
        
        # Determine color based on signal type (in decimal format for Discord)
        if signal_type.lower() in ['buy', 'bullish']:
            color = 3066993  # Green
            emoji = "🟢"
        elif signal_type.lower() in ['sell', 'bearish']:
            color = 15158332  # Red
            emoji = "🔴"
        else:
            color = 16776960  # Yellow
            emoji = "🟡"
            
        # Build Discord embed structure according to Discord API spec
        # https://discord.com/developers/docs/resources/channel#embed-object
        embed = {
            "title": f"{emoji} TRADE ALERT: {symbol} {emoji}",
            "description": f"**{signal_type} SIGNAL | CONFLUENCE SCORE: {score:.1f}**\n\nCurrent Price: ${price:.2f}\n\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "color": color,
            "fields": [],
            "footer": {
                "text": "Virtuoso Trading Bot"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Handle missing price case - use cached price or fallback
        if price <= 0:
            self.logger.warning(f"Invalid price (${price}) for {symbol} in risk management format, using cached or estimated price")
            
            # Try to use cached price if available and recent (last 5 minutes)
            if hasattr(self, '_price_cache') and symbol in self._price_cache:
                cache_time = getattr(self, '_price_cache_time', {}).get(symbol, 0)
                # Use cache if less than 5 minutes old
                if time.time() - cache_time < 300:  
                    price = self._price_cache[symbol]
                    self.logger.info(f"Using cached price for {symbol}: ${price}")
                else:
                    self.logger.info(f"Cached price for {symbol} is too old, using fallback price")
                    price = 100.0
            else:
                # Initialize cache if not exists
                if not hasattr(self, '_price_cache'):
                    self._price_cache = {}
                    self._price_cache_time = {}
                
                # Use a reasonable default for calculations
                self.logger.info(f"No cached price available for {symbol}, using fallback price")
                price = 100.0
            
            # If price is still zero, use placeholder
            if price <= 0:
                price_for_calcs = 100.0  # Generic placeholder for calculations
                price_text = "UNKNOWN (price unavailable)"
            else:
                price_for_calcs = price
                price_text = f"${price:.2f}"
        else:
            price_for_calcs = price
            price_text = f"${price:.2f}"
        
        # Update the description with the proper price text
        embed["description"] = f"**{signal_type} SIGNAL | CONFLUENCE SCORE: {score:.1f}**\n\nCurrent Price: {price_text}\n\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        # FIXED: Handle different timestamp formats
        timestamp_val = signal.get('timestamp', int(time.time() * 1000))
        if isinstance(timestamp_val, str):
            # Try to parse ISO format timestamp
            try:
                if 'T' in timestamp_val:  # ISO format like '2025-03-06T15:31:08.123456'
                    dt = datetime.fromisoformat(timestamp_val.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                else:
                    # Try simple parsing
                    timestamp = timestamp_val
            except Exception as e:
                self.logger.error(f"Error parsing timestamp string '{timestamp_val}': {str(e)}")
                timestamp = datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            # Handle numeric timestamp (milliseconds)
            try:
                timestamp_ms = int(timestamp_val)
                if timestamp_ms > 1e12:  # Likely milliseconds
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                else:  # Likely seconds
                    timestamp = datetime.fromtimestamp(timestamp_ms).strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception as e:
                self.logger.error(f"Error parsing numeric timestamp {timestamp_val}: {str(e)}")
                timestamp = datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Update description with the properly formatted timestamp
        embed["description"] = f"**{signal_type} SIGNAL | CONFLUENCE SCORE: {score:.1f}**\n\nCurrent Price: {price_text}\n\nTimestamp: {timestamp}"
        
        # Risk parameters - use defaults if not provided
        results = signal.get('results', {})
        stop_loss = results.get('stop_loss', price_for_calcs * 0.97 if signal_type.lower() in ['buy', 'bullish'] else price_for_calcs * 1.03)
        
        # Calculate default targets if not provided
        targets = results.get('targets', {})
        if not targets and signal_type.lower() in ['buy', 'bullish']:
            t1_pct = 0.02  # 2%
            t2_pct = 0.045  # 4.5%
            t3_pct = 0.07  # 7%
            targets = {
                "T1": {"price": price_for_calcs * (1 + t1_pct), "size": 0.25},
                "T2": {"price": price_for_calcs * (1 + t2_pct), "size": 0.5},
                "T3": {"price": price_for_calcs * (1 + t3_pct), "size": 0.25}
            }
        elif not targets:
            t1_pct = 0.02  # 2%
            t2_pct = 0.045  # 4.5%
            t3_pct = 0.07  # 7%
            targets = {
                "T1": {"price": price_for_calcs * (1 - t1_pct), "size": 0.25},
                "T2": {"price": price_for_calcs * (1 - t2_pct), "size": 0.5},
                "T3": {"price": price_for_calcs * (1 - t3_pct), "size": 0.25}
            }
        
        # Get components data
        components = signal.get('components', {})
        
        # Format targets text
        targets_text = ""
        for target_name, target_data in targets.items():
            target_price = target_data.get("price", 0)
            target_size = target_data.get("size", 0)
            pct_change = abs((target_price / price_for_calcs) - 1) * 100
            targets_text += f"{target_name}: ${target_price:.2f} ({pct_change:.2f}%) - {target_size * 100:.0f}%\n"
        
        # Add entry and exits field
        embed["fields"].append({
            "name": "📊 ENTRY & EXITS",
            "value": f"**Stop Loss:** ${stop_loss:.2f} ({abs((stop_loss / price_for_calcs) - 1) * 100:.2f}%)\n**Targets:**\n{targets_text}",
            "inline": True
        })
        
        # Format interpretations
        interpretations = self._extract_interpretations(results)
        interpretation_text = ""
        for component, text in interpretations.items():
            if text:
                score_value = components.get(component, 50)
                interpretation_text += f"**{component.upper()} ({score_value:.1f})**: {text}\n"
        
        # Add detailed analysis if available
        if interpretation_text:
            embed["fields"].append({
                "name": "🔍 DETAILED ANALYSIS",
                "value": interpretation_text[:1024]  # Discord has 1024 char limit for field value
            })
        
        # Add cross-component insights and actionable insights if available
        try:
            from src.core.analysis.interpretation_generator import InterpretationGenerator
            interpretation_generator = InterpretationGenerator()
            
            # Generate cross-component insights
            cross_insights = interpretation_generator.generate_cross_component_insights(results)
            if cross_insights:
                cross_insights_text = "• " + "\n• ".join(cross_insights)
                embed["fields"].append({
                    "name": "🔄 CROSS-COMPONENT INSIGHTS",
                    "value": cross_insights_text[:1024]
                })
            
            # Generate actionable trading insights
            buy_threshold = signal.get('buy_threshold', 65)
            sell_threshold = signal.get('sell_threshold', 35)
            actionable_insights = interpretation_generator.generate_actionable_insights(
                results, score, buy_threshold, sell_threshold
            )
            if actionable_insights:
                actionable_insights_text = "• " + "\n• ".join(actionable_insights)
                embed["fields"].append({
                    "name": "🎯 ACTIONABLE INSIGHTS",
                    "value": actionable_insights_text[:1024]
                })
        except Exception as e:
            self.logger.warning(f"Error generating cross-component or actionable insights: {str(e)}")
        
        # Add risk field
        risk_reward = "N/A"
        try:
            t3_price = targets.get("T3", {}).get("price", 0)
            if t3_price > 0 and stop_loss > 0:
                if signal_type.lower() in ['buy', 'bullish']:
                    risk = price_for_calcs - stop_loss
                    reward = t3_price - price_for_calcs
                else:
                    risk = stop_loss - price_for_calcs
                    reward = price_for_calcs - t3_price
                
                if risk > 0:
                    risk_reward = f"{reward / risk:.2f}"
                    
            leverage = signal.get('recommended_leverage', 1.0)
            position_size = signal.get('position_size', 5.0)  # Default 5% of account
            
            embed["fields"].append({
                "name": "⚖️ RISK MANAGEMENT",
                "value": f"**Risk/Reward Ratio:** {risk_reward}\n**Recommended Leverage:** {leverage:.1f}x\n**Position Size:** {position_size:.1f}%",
                "inline": True
            })
        except Exception as e:
            self.logger.error(f"Error calculating risk values: {str(e)}")
        
        # Add component scores if available
        components = signal.get('components', {})
        if components and isinstance(components, dict):
            component_text = ""
            
            # Display key component scores in order of importance
            key_components = [
                ('technical', '📊 Technical'),
                ('price_structure', '🏛️ Price Structure'),
                ('orderbook', '📖 Orderbook'),
                ('sentiment', '🧠 Sentiment'),
                ('orderflow', '🌊 Orderflow'),
                ('volume', '📈 Volume')
            ]
            
            for comp_key, comp_label in key_components:
                if comp_key in components:
                    score = components[comp_key]
                    # Add emojis based on score ranges
                    if score >= 60:
                        emoji = "🟢"  # Strong bullish
                    elif score >= 50:
                        emoji = "🟡"  # Mildly bullish
                    elif score >= 40:
                        emoji = "⚪"  # Neutral
                    elif score >= 30:
                        emoji = "🟠"  # Mildly bearish
                    else:
                        emoji = "🔴"  # Strong bearish
                        
                    component_text += f"{emoji} **{comp_label}:** {score:.2f}\n"
            
            if component_text:
                embed["fields"].append({
                    "name": "🧩 COMPONENT SCORES",
                    "value": component_text[:1024],  # Discord has 1024 char limit for field value
                    "inline": False
                })
        
        # Construct the final webhook message according to Discord API
        webhook_message = {
            "embeds": [embed]
        }
        
        self.logger.debug(f"Created Discord embed for {symbol}: {json.dumps(embed, indent=2)}")
        
        return webhook_message

    def _init_discord_webhook(self):
        """Initialize Discord webhook client"""
        if self.discord_webhook_url:
            self.discord_client = DiscordWebhook(
                url=self.discord_webhook_url,
                rate_limit_retry=True
            )

    def _validate_alert_config(self):
        """Ensure required alert parameters exist"""
        if not self.config.get('monitoring'):
            raise ValueError("Missing monitoring config section")
        if not self.config['monitoring'].get('alerts'):
            raise ValueError("Missing alerts configuration")

    async def start(self):
        """Initialize alert channels"""
        # Add initialization logic here

    def _determine_impact_level(self, usd_value: float) -> str:
        """Determine the impact level based on the USD value."""
        if usd_value >= self.liquidation_threshold * 2:
            return "HIGH"
        elif usd_value >= self.liquidation_threshold:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_impact_bar(self, usd_value: float) -> str:
        """Generate a visual bar representing the impact of a liquidation.
        
        Args:
            usd_value: USD value of the liquidation
            
        Returns:
            String representing a visual bar chart
        """
        # Calculate percentage of high impact threshold (2x base threshold)
        high_threshold = self.liquidation_threshold * 2
        percentage = min(100, int((usd_value / high_threshold) * 100))
        
        # Create a visual bar with 10 segments
        segments = 10
        filled = int((percentage / 100) * segments)
        
        # Use full blocks for the bar
        bar = "█" * filled + "░" * (segments - filled)
        
        # Add percentage
        return f"{bar} {percentage}%"

    def _get_price_action_note(self, position_type: str, impact_level: str) -> str:
        """Generate a note about potential price action based on liquidation details.
        
        Args:
            position_type: The type of position being liquidated (LONG/SHORT)
            impact_level: The impact level (HIGH/MEDIUM/LOW)
            
        Returns:
            String containing price action note
        """
        if position_type == "LONG":
            if impact_level == "HIGH":
                return "Expect significant downward pressure - potential for cascade liquidations"
            elif impact_level == "MEDIUM":
                return "Moderate selling pressure may push price lower in the short term"
            else:
                return "Minor selling pressure, likely limited immediate effect"
        else:  # SHORT
            if impact_level == "HIGH":
                return "Expect significant upward pressure - potential for short squeeze"
            elif impact_level == "MEDIUM":
                return "Moderate buying pressure may drive price higher in the short term"
            else:
                return "Minor buying pressure, likely limited immediate effect"

    def _extract_interpretations(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Extract interpretations from component results."""
        # Try to use the enhanced interpretation generator for richer interpretations
        try:
            from src.core.analysis.interpretation_generator import InterpretationGenerator
            interpretation_generator = InterpretationGenerator()
            enhanced_interpretations = {}
            
            # Generate enhanced interpretations for each component
            for component_name, component_data in results.items():
                if not isinstance(component_data, dict):
                    continue
                    
                try:
                    # Get the enhanced interpretation
                    enhanced_interpretation = interpretation_generator.get_component_interpretation(
                        component_name, component_data
                    )
                    if enhanced_interpretation:
                        enhanced_interpretations[component_name] = enhanced_interpretation
                except Exception as e:
                    self.logger.warning(f"Error generating enhanced interpretation for {component_name}: {str(e)}")
                    # Fall back to basic interpretation below
            
            # If we successfully got enhanced interpretations, return them
            if enhanced_interpretations:
                # Removed the log message that was causing duplicate interpretations
                return enhanced_interpretations
        except Exception as e:
            self.logger.warning(f"Enhanced interpretation generator not available, using basic interpretations: {str(e)}")
            # Fall back to basic interpretation method below
        
        # Legacy interpretation extraction method if enhanced generator is not available
        interpretations = {}
        
        for component_name, component_data in results.items():
            if not isinstance(component_data, dict):
                continue
                
            interpretation = None
            
            # First try to get the interpretation from the interpretation field
            if 'interpretation' in component_data:
                interp = component_data['interpretation']
                if isinstance(interp, dict) and 'summary' in interp:
                    interpretation = interp['summary']
                elif isinstance(interp, str):
                    interpretation = interp
            
            # Check for enhanced_interpretation added by our formatter
            elif 'enhanced_interpretation' in component_data:
                interpretation = component_data['enhanced_interpretation']
            
            # If no interpretation found but we have signals, use those
            if not interpretation and 'signals' in component_data:
                signals = component_data['signals']
                if isinstance(signals, dict):
                    signal_parts = []
                    for signal_name, signal_data in signals.items():
                        if isinstance(signal_data, dict) and 'signal' in signal_data:
                            signal_parts.append(f"{signal_name}={signal_data['signal']}")
                        elif isinstance(signal_data, (str, int, float, bool)):
                            signal_parts.append(f"{signal_name}={signal_data}")
                    
                    if signal_parts:
                        interpretation = ", ".join(signal_parts)
                elif isinstance(signals, list) and signals:
                    interpretation = ", ".join(str(s) for s in signals if s is not None)
                elif signals is not None:
                    interpretation = str(signals)
            
            if interpretation:
                interpretations[component_name] = interpretation
                
        return interpretations
        
    async def _get_current_price(self, symbol: str) -> float:
        """Get the current price for a symbol."""
        try:
            # Try multiple approaches to get the price
            
            # First approach: Use ExchangeManager
            try:
                # Try standard import path
                try:
                    from src.core.exchanges.manager import ExchangeManager
                except ImportError:
                    try:
                        from core.exchanges.manager import ExchangeManager
                    except ImportError:
                        self.logger.warning("Could not import ExchangeManager, trying alternative methods")
                        raise ImportError("ExchangeManager not available")
                    
                # Try different ways to get an ExchangeManager instance
                exchange_manager = None
                
                # Method 1: get_instance
                if hasattr(ExchangeManager, 'get_instance'):
                    self.logger.debug("Using ExchangeManager.get_instance()")
                    exchange_manager = ExchangeManager.get_instance()
                # Method 2: instance (property)
                elif hasattr(ExchangeManager, 'instance'):
                    self.logger.debug("Using ExchangeManager.instance")
                    exchange_manager = ExchangeManager.instance
                # Method 3: getInstance
                elif hasattr(ExchangeManager, 'getInstance'):
                    self.logger.debug("Using ExchangeManager.getInstance()")
                    exchange_manager = ExchangeManager.getInstance()
                # Method 4: try singleton pattern (might be stored in a class variable)
                elif hasattr(ExchangeManager, '_instance') and ExchangeManager._instance is not None:
                    self.logger.debug("Using ExchangeManager._instance")
                    exchange_manager = ExchangeManager._instance
                # Method 5: try to create a new instance
                else:
                    self.logger.debug("Creating new ExchangeManager instance")
                    try:
                        # Try to create ConfigManager first
                        from src.config.manager import ConfigManager
                        # Modified: Create ConfigManager with no arguments first, then set the config
                        config_manager = ConfigManager()
                        # Set the config after initialization
                        if hasattr(config_manager, 'set_config'):
                            config_manager.set_config(self.config)
                        elif hasattr(config_manager, 'config'):
                            config_manager.config = self.config
                        # Now create the ExchangeManager with the config_manager
                        exchange_manager = ExchangeManager(config_manager)
                    except Exception as e:
                        self.logger.warning(f"Failed to create ExchangeManager: {str(e)}")
                        # Add a fallback mechanism to get price without ExchangeManager
                        try:
                            # Try to use the config directly to create a simple exchange connection
                            from src.core.exchanges.bybit import BybitExchange
                            exchange_config = {
                                'exchanges': {
                                    'bybit': self.config.get('exchange', {})
                                }
                            }
                            # Create a simple Bybit exchange instance
                            exchange = BybitExchange(exchange_config)
                            # Just try to call fetch_ticker directly without initialization
                            try:
                                ticker = await exchange.fetch_ticker(symbol)
                                if ticker and 'last' in ticker and ticker['last'] > 0:
                                    return ticker['last']
                            except Exception as ex2:
                                self.logger.warning(f"Direct ticker fetch failed: {str(ex2)}")
                                # Return a fallback value based on the symbol
                                if 'BTC' in symbol.upper():
                                    return 60000.0
                                elif 'ETH' in symbol.upper():
                                    return 3000.0
                                else:
                                    return 100.0
                        except Exception as ex:
                            self.logger.warning(f"Fallback exchange approach also failed: {str(ex)}")
                        raise RuntimeError(f"Could not initialize ExchangeManager: {str(e)}")
                
                if not exchange_manager:
                    self.logger.warning("Failed to get ExchangeManager instance")
                    raise Exception("No valid ExchangeManager instance available")
                
                # Check if exchange_manager is callable
                if callable(exchange_manager):
                    exchange_manager = exchange_manager()
                
                # Fetch market data - handle both method and property patterns
                if hasattr(exchange_manager, 'get_market_data'):
                    if callable(exchange_manager.get_market_data):
                        self.logger.debug(f"Calling exchange_manager.get_market_data({symbol})")
                        market_data = await exchange_manager.get_market_data(symbol)
                    else:
                        # It might be a property or dictionary
                        market_data = exchange_manager.get_market_data.get(symbol, {})
                elif hasattr(exchange_manager, 'market_data'):
                    if callable(exchange_manager.market_data):
                        market_data = await exchange_manager.market_data(symbol)
                    else:
                        market_data = exchange_manager.market_data.get(symbol, {})
                else:
                    self.logger.warning("ExchangeManager doesn't have expected market data methods")
                    raise AttributeError("No market data methods found")
                
                # Return the last price if available
                if market_data and 'last' in market_data and market_data['last'] > 0:
                    # Cache the price before returning
                    self._price_cache[symbol] = market_data['last']
                    self._price_cache_time[symbol] = time.time()
                    self.logger.info(f"Got price from ExchangeManager: ${market_data['last']}")
                    return market_data['last']
                elif market_data and 'price' in market_data and market_data['price'] > 0:
                    # Alternative key for price
                    self._price_cache[symbol] = market_data['price']
                    self._price_cache_time[symbol] = time.time()
                    self.logger.info(f"Got price from ExchangeManager: ${market_data['price']}")
                    return market_data['price']
                elif market_data and isinstance(market_data, (int, float)) and market_data > 0:
                    # Handle case where the function directly returns a price
                    self._price_cache[symbol] = market_data
                    self._price_cache_time[symbol] = time.time()
                    self.logger.info(f"Got price from ExchangeManager: ${market_data}")
                    return market_data
            except Exception as e:
                self.logger.warning(f"ExchangeManager approach failed: {str(e)}")
            
            # Second approach: Use direct API call to configured exchange
            try:
                # Check if we have a client session
                if not self._client_session:
                    await self._init_client_session()
                    
                # Get exchange API url from config or default to a common one
                exchange_url = self.config.get('exchanges', {}).get('default', {}).get(
                    'api_url', 'https://api.binance.com/api/v3/ticker/price?symbol={}')
                
                if '{}' in exchange_url:
                    exchange_url = exchange_url.format(symbol)
                else:
                    exchange_url = f"{exchange_url}?symbol={symbol}"
                    
                self.logger.debug(f"Attempting direct API call to {exchange_url}")
                async with self._client_session.get(exchange_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, dict) and 'price' in data:
                            price = float(data['price'])
                            # Cache the price before returning
                            self._price_cache[symbol] = price
                            self._price_cache_time[symbol] = time.time()
                            self.logger.info(f"Got price from API: ${price}")
                            return price
                        elif isinstance(data, list) and len(data) > 0 and 'price' in data[0]:
                            # Handle case where API returns a list of items
                            price = float(data[0]['price'])
                            self._price_cache[symbol] = price
                            self._price_cache_time[symbol] = time.time()
                            self.logger.info(f"Got price from API (list): ${price}")
                            return price
            except Exception as e:
                self.logger.warning(f"Direct API approach failed: {str(e)}")
            
            # Third approach: Fallback to cached price if available
            if hasattr(self, '_price_cache') and symbol in self._price_cache:
                cached_price = self._price_cache.get(symbol)
                cache_time = self._price_cache_time.get(symbol, 0)
                
                # Use cache if it's less than 5 minutes old
                if time.time() - cache_time < 300 and cached_price > 0:
                    self.logger.info(f"Using cached price for {symbol}: ${cached_price}")
                    return cached_price
            
            # Fourth approach: Try to parse from symbol name (emergency fallback)
            try:
                # For well-known symbols, use rough price estimates
                # This is a last resort and not accurate, but better than $0.00
                symbol_upper = symbol.upper()
                if 'BTC' in symbol_upper:
                    fallback_price = 60000.0  # Rough BTC price
                elif 'ETH' in symbol_upper:
                    fallback_price = 2500.0   # Rough ETH price
                elif 'SOL' in symbol_upper:
                    fallback_price = 100.0    # Rough SOL price
                elif 'BNB' in symbol_upper:
                    fallback_price = 300.0    # Rough BNB price
                else:
                    fallback_price = 50.0     # Generic fallback
                
                self.logger.warning(f"Using emergency fallback price for {symbol}: ${fallback_price}")
                return fallback_price
            except Exception:
                pass
            
            # If all else fails, log a critical error and return a default value
            self.logger.critical(f"All price fetching methods failed for {symbol}")
            return 0.0
                
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return 0.0

    def test_discord_webhook(self):
        """Test Discord webhook connection and print detailed diagnostic information."""
        try:
            print("\n=== DISCORD WEBHOOK TEST ===")
            
            # Check if webhook URL is set
            if not self.discord_webhook_url:
                print("ERROR: Discord webhook URL is not set")
                return
                
            # Print webhook URL info
            webhook_url = self.discord_webhook_url.strip()
            print(f"Webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
            print(f"Webhook URL length: {len(webhook_url)}")
            print(f"Webhook URL starts with https://discord.com/api/webhooks/: {webhook_url.startswith('https://discord.com/api/webhooks/')}")
            
            # Print handler info
            print(f"Handlers: {self.handlers}")
            print(f"Alert handlers: {list(self.alert_handlers.keys())}")
            
            # Try to send a test message using a subprocess
            try:
                import subprocess
                import json
                print("Sending test webhook via curl...")
                
                # Create a test message
                test_message = {
                    "content": "🔄 TEST ALERT: This is a test message to verify the Discord webhook is working",
                    "username": "Virtuoso Alerts",
                    "avatar_url": "https://i.imgur.com/4M34hi2.png"
                }
                
                # Run curl command
                curl_cmd = [
                    'curl', '-X', 'POST',
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps(test_message),
                    webhook_url
                ]
                
                result = subprocess.run(curl_cmd, capture_output=True, text=True)
                print(f"Curl exit code: {result.returncode}")
                print(f"Curl output: {result.stdout}")
                if result.stderr:
                    print(f"Curl error: {result.stderr}")
                    
                print("Test message sent. Please check your Discord channel.")
            except Exception as e:
                print(f"Error sending test message: {str(e)}")
                
            print("=== END OF WEBHOOK TEST ===\n")
        except Exception as e:
            print(f"Error in test_discord_webhook: {str(e)}")

    def verify_handler_state(self) -> Dict[str, Any]:
        """Verify handler registration state and collect debug information.
        
        Returns:
            Dictionary with debug information about handler state
        """
        debug_info = {
            "timestamp": time.time(),
            "elapsed_since_init": time.time() - self._initialization_time,
            "handlers": list(self.handlers),
            "alert_handlers": list(self.alert_handlers.keys()),
            "discord_webhook_url_set": bool(self.discord_webhook_url),
            "webhook_url_valid": bool(self.discord_webhook_url and self.discord_webhook_url.startswith("https://discord.com/api/webhooks/")),
            "handler_registration_attempts": self._handler_registration_attempts,
        }
        
        # Check if handlers are properly registered
        if not self.handlers:
            self.logger.critical("ALERT VERIFICATION: No handlers registered!")
            debug_info["status"] = "NO_HANDLERS"
            
            # If webhook URL is set but no handlers, this is an inconsistent state
            if self.discord_webhook_url:
                self.logger.critical(f"ALERT VERIFICATION: Discord webhook URL is set but no handlers registered: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
                debug_info["issue"] = "WEBHOOK_SET_NO_HANDLERS"
                
                # Attempt to fix this by registering the handler
                self._handler_registration_attempts += 1
                self.register_handler('discord')
                self.logger.info(f"ALERT VERIFICATION: Attempted to register discord handler. Handlers after attempt: {self.handlers}")
                debug_info["attempted_fix"] = True
                debug_info["handlers_after_fix"] = list(self.handlers)
        else:
            debug_info["status"] = "HANDLERS_REGISTERED"
            if 'discord' in self.handlers:
                debug_info["discord_registered"] = True
                
        # Store and log the debug info
        self._debug_info = debug_info
        self.logger.info(f"ALERT VERIFICATION: Handler state: {debug_info}")
        return debug_info

    def _format_enhanced_confluence_alert(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Format signal using Enhanced Confluence Style alert with Discord embeds
        
        Returns:
            Dict containing the formatted Discord webhook payload with embeds
        """
        # Initialize the base embed structure (similar to existing code)
        symbol = signal.get('symbol', 'Unknown')
        signal_type = signal.get('signal', 'Unknown').upper()
        score = signal.get('confluence_score', signal.get('score', 0))
        reliability = signal.get('reliability', 100)
        
        # Ensure reliability is displayed as percentage (not decimal)
        if reliability <= 1.0:
            reliability = reliability * 100
        
        price = signal.get('price', 0)
        
        # Color coding
        if signal_type.lower() in ['buy', 'bullish']:
            color = 3066993  # Green
            emoji = "🟢"
        elif signal_type.lower() in ['sell', 'bearish']:
            color = 15158332  # Red
            emoji = "🔴"
        else:
            color = 16776960  # Yellow
            emoji = "🟡"
        
        # Build enhanced embed with confluence details
        embed = {
            "title": f"{emoji} {symbol} CONFLUENCE ANALYSIS {emoji}",
            "description": (
                f"**OVERALL SCORE: {score:.2f} ({signal_type})**\n"
                f"**RELIABILITY: {reliability:.0f}% (HIGH)**\n\n"
                f"Current Price: ${price:.4f}\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            ),
            "color": color,
            "fields": [],
            "footer": {
                "text": "Virtuoso Trading Bot"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Handle price text formatting similar to risk_management_alert
        if price <= 0:
            self.logger.warning(f"Invalid price (${price}) for {symbol} in enhanced confluence format, using cached or estimated price")
            
            # Try to use cached price if available and recent (last 5 minutes)
            if hasattr(self, '_price_cache') and symbol in self._price_cache:
                cache_time = getattr(self, '_price_cache_time', {}).get(symbol, 0)
                # Use cache if less than 5 minutes old
                if time.time() - cache_time < 300:  
                    price = self._price_cache[symbol]
                    self.logger.info(f"Using cached price for {symbol}: ${price}")
                else:
                    self.logger.info(f"Cached price for {symbol} is too old, using fallback price")
                    price = 100.0
            else:
                # Initialize cache if not exists
                if not hasattr(self, '_price_cache'):
                    self._price_cache = {}
                    self._price_cache_time = {}
                
                # Use a reasonable default for calculations
                self.logger.info(f"No cached price available for {symbol}, using fallback price")
                price = 100.0
            
            # If price is still zero, use placeholder
            if price <= 0:
                price_text = "UNKNOWN (price unavailable)"
            else:
                price_text = f"${price:.4f}"
        else:
            price_text = f"${price:.4f}"
            
        # Update description with correct price
        embed["description"] = (
            f"**OVERALL SCORE: {score:.2f} ({signal_type})**\n"
            f"**RELIABILITY: {reliability:.0f}% (HIGH)**\n\n"
            f"Current Price: {price_text}\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        
        # Extract components and their impact values
        components = signal.get('components', {})
        
        # Look for impact values in both direct format and nested format
        component_impacts = {}
        
        # Check for direct impact values in signal data (component_name_impact format)
        for key in signal:
            if key.endswith('_impact') and key.replace('_impact', '') in components:
                component_name = key.replace('_impact', '')
                component_impacts[component_name] = signal[key]
        
        # Also look for impact values in a dedicated impacts dictionary if it exists
        impacts = signal.get('impacts', signal.get('component_impacts', {}))
        if isinstance(impacts, dict):
            for component_name, impact_value in impacts.items():
                if component_name in components:
                    component_impacts[component_name] = impact_value
                    
        # Add component breakdown field
        if components:
            component_text = "```\n"
            component_text += "COMPONENT          | SCORE  | IMPACT \n"
            component_text += "------------------ | ------ | ------\n"
            
            # Create a list of tuples with component name, score, and impact
            component_list = []
            for comp_name, comp_score in components.items():
                # Get impact from our collected impacts or default to 0
                comp_impact = component_impacts.get(comp_name, 0)
                component_list.append((comp_name, comp_score, comp_impact))
            
            # Sort components by impact (if available) or by score
            sorted_components = sorted(
                component_list,
                key=lambda x: x[2] if x[2] != 0 else x[1],  # Sort by impact if available, otherwise by score
                reverse=True
            )
            
            for comp_name, comp_score, comp_impact in sorted_components:
                # Format the name with proper spacing
                display_name = comp_name.replace('_', ' ').title()
                display_name = display_name.ljust(18)[:18]
                
                # Format score and impact values
                component_text += f"{display_name} | {comp_score:.2f}  | {comp_impact:.1f}\n"
            
            component_text += "```"
            
            embed["fields"].append({
                "name": "🧩 COMPONENT BREAKDOWN",
                "value": component_text,
                "inline": False
            })
            
        # Add top influential components
        results = signal.get('results', {})
        if results:
            influential_text = ""
            
            for comp_name, comp_data in results.items():
                # Add check to ensure comp_data is a dictionary
                if comp_name in components:  # Only process if in components list
                    comp_score = components.get(comp_name, 0)
                    influential_text += f"**{comp_name.replace('_', ' ').title()} ({comp_score:.2f})**\n"
                    
                    # Check if comp_data is a dictionary with components
                    if isinstance(comp_data, dict) and 'components' in comp_data and isinstance(comp_data['components'], dict):
                        # Sort subcomponents by value
                        subcomps = comp_data['components']
                        sorted_subcomps = sorted(subcomps.items(), key=lambda x: abs(float(x[1])) if isinstance(x[1], (int, float)) else 0, reverse=True)
                        
                        # Take top 3
                        for i, (sub_name, sub_value) in enumerate(sorted_subcomps[:3]):
                            if isinstance(sub_value, (int, float)):
                                # Direction indicator
                                if sub_value >= 70:
                                    direction = "↑"
                                elif sub_value >= 50:
                                    direction = "→"
                                else:
                                    direction = "↓"
                                    
                                sub_display = sub_name.replace('_', ' ').title()
                                influential_text += f"• {sub_display}: {sub_value:.2f} {direction}\n"
                    
                    influential_text += "\n"
            
            if influential_text:
                embed["fields"].append({
                    "name": "🔝 TOP INFLUENTIAL COMPONENTS",
                    "value": influential_text[:1024],
                    "inline": False
                })
                
        # Add market interpretations
        interpretations = self._extract_interpretations(results)
        if interpretations:
            interp_text = ""
            for component, text in interpretations.items():
                if text:
                    interp_text += f"**{component.upper()}**: {text}\n\n"
            
            if interp_text:
                embed["fields"].append({
                    "name": "🔍 MARKET INTERPRETATIONS",
                    "value": interp_text[:1024],
                    "inline": False
                })
                
        # Add actionable insights
        try:
            from src.core.analysis.interpretation_generator import InterpretationGenerator
            interpretation_generator = InterpretationGenerator()
            
            # Check if results structure is suitable for interpretation generation
            has_valid_results = False
            if isinstance(results, dict):
                # Check if at least one component has a valid dictionary structure
                for comp_key, comp_value in results.items():
                    if isinstance(comp_value, dict) and 'components' in comp_value:
                        has_valid_results = True
                        break
            
            # Only generate insights if we have valid results structure
            if has_valid_results:
                buy_threshold = signal.get('buy_threshold', 65)
                sell_threshold = signal.get('sell_threshold', 35)
                
                actionable_insights = interpretation_generator.generate_actionable_insights(
                    results, score, buy_threshold, sell_threshold
                )
                
                if actionable_insights:
                    insights_text = "• " + "\n• ".join(actionable_insights)
                    embed["fields"].append({
                        "name": "🎯 ACTIONABLE TRADING INSIGHTS",
                        "value": insights_text[:1024],
                        "inline": False
                    })
            else:
                # Add basic actionable insights based on score
                basic_insights = []
                
                if score >= 65:
                    basic_insights.append(f"BULLISH BIAS: Overall confluence score ({score:.2f}) above buy threshold (65)")
                    basic_insights.append("RISK ASSESSMENT: MODERATE - Standard position sizing recommended with normal stop distances")
                    basic_insights.append("STRATEGY: Consider bullish strategies: swing longs or breakouts with defined risk")
                elif score <= 35:
                    basic_insights.append(f"BEARISH BIAS: Overall confluence score ({score:.2f}) below sell threshold (35)")
                    basic_insights.append("RISK ASSESSMENT: MODERATE - Standard position sizing recommended with normal stop distances")
                    basic_insights.append("STRATEGY: Consider bearish strategies: swing shorts or breakdown entries with defined risk")
                else:
                    basic_insights.append(f"NEUTRAL BIAS: Overall confluence score ({score:.2f}) within neutral zone")
                    basic_insights.append("RISK ASSESSMENT: ELEVATED - Reduced position sizing recommended")
                    basic_insights.append("STRATEGY: Consider range-bound strategies or wait for stronger signals")
                
                insights_text = "• " + "\n• ".join(basic_insights)
                embed["fields"].append({
                    "name": "🎯 ACTIONABLE TRADING INSIGHTS",
                    "value": insights_text[:1024],
                    "inline": False
                })
        except Exception as e:
            self.logger.warning(f"Error generating actionable insights: {str(e)}")
            
            # Fallback to basic actionable insights
            basic_insights = []
            
            if score >= 65:
                basic_insights.append(f"BULLISH BIAS: Overall confluence score ({score:.2f}) above buy threshold (65)")
                basic_insights.append("RISK ASSESSMENT: MODERATE - Standard position sizing recommended with normal stop distances")
                basic_insights.append("STRATEGY: Consider bullish strategies: swing longs or breakouts with defined risk")
            elif score <= 35:
                basic_insights.append(f"BEARISH BIAS: Overall confluence score ({score:.2f}) below sell threshold (35)")
                basic_insights.append("RISK ASSESSMENT: MODERATE - Standard position sizing recommended with normal stop distances")
                basic_insights.append("STRATEGY: Consider bearish strategies: swing shorts or breakdown entries with defined risk")
            else:
                basic_insights.append(f"NEUTRAL BIAS: Overall confluence score ({score:.2f}) within neutral zone")
                basic_insights.append("RISK ASSESSMENT: ELEVATED - Reduced position sizing recommended")
                basic_insights.append("STRATEGY: Consider range-bound strategies or wait for stronger signals")
            
            insights_text = "• " + "\n• ".join(basic_insights)
            embed["fields"].append({
                "name": "🎯 ACTIONABLE TRADING INSIGHTS",
                "value": insights_text[:1024],
                "inline": False
            })
            
        # Add risk management section from existing code
        # Calculate default targets if not provided
        price_for_calcs = price if price > 0 else 100.0
        
        # Risk parameters - use defaults if not provided
        stop_loss = results.get('stop_loss', price_for_calcs * 0.97 if signal_type.lower() in ['buy', 'bullish'] else price_for_calcs * 1.03)
        
        targets = results.get('targets', {})
        if not targets and signal_type.lower() in ['buy', 'bullish']:
            t1_pct = 0.02  # 2%
            t2_pct = 0.045  # 4.5%
            t3_pct = 0.07  # 7%
            targets = {
                "T1": {"price": price_for_calcs * (1 + t1_pct), "size": 0.25},
                "T2": {"price": price_for_calcs * (1 + t2_pct), "size": 0.5},
                "T3": {"price": price_for_calcs * (1 + t3_pct), "size": 0.25}
            }
        elif not targets:
            t1_pct = 0.02  # 2%
            t2_pct = 0.045  # 4.5%
            t3_pct = 0.07  # 7%
            targets = {
                "T1": {"price": price_for_calcs * (1 - t1_pct), "size": 0.25},
                "T2": {"price": price_for_calcs * (1 - t2_pct), "size": 0.5},
                "T3": {"price": price_for_calcs * (1 - t3_pct), "size": 0.25}
            }
        
        # Format targets text
        targets_text = ""
        for target_name, target_data in targets.items():
            target_price = target_data.get("price", 0)
            target_size = target_data.get("size", 0)
            pct_change = abs((target_price / price_for_calcs) - 1) * 100
            targets_text += f"{target_name}: ${target_price:.4f} ({pct_change:.2f}%) - {target_size * 100:.0f}%\n"
        
        # Add entry and exits field
        embed["fields"].append({
            "name": "📊 ENTRY & EXITS",
            "value": f"**Stop Loss:** ${stop_loss:.4f} ({abs((stop_loss / price_for_calcs) - 1) * 100:.2f}%)\n**Targets:**\n{targets_text}",
            "inline": True
        })
        
        # Add risk/reward calculation
        risk_reward = "N/A"
        try:
            t3_price = targets.get("T3", {}).get("price", 0)
            if t3_price > 0 and stop_loss > 0:
                if signal_type.lower() in ['buy', 'bullish']:
                    risk = price_for_calcs - stop_loss
                    reward = t3_price - price_for_calcs
                else:
                    risk = stop_loss - price_for_calcs
                    reward = price_for_calcs - t3_price
                
                if risk > 0:
                    risk_reward = f"{reward / risk:.2f}"
                    
            leverage = signal.get('recommended_leverage', 1.0)
            position_size = signal.get('position_size', 5.0)  # Default 5% of account
            
            embed["fields"].append({
                "name": "⚖️ RISK MANAGEMENT",
                "value": f"**Risk/Reward Ratio:** {risk_reward}\n**Recommended Leverage:** {leverage:.1f}x\n**Position Size:** {position_size:.1f}%",
                "inline": True
            })
        except Exception as e:
            self.logger.error(f"Error calculating risk values: {str(e)}")
        
        # Finalize webhook message
        webhook_message = {
            "username": "Virtuoso Trading Bot",
            "embeds": [embed]
        }
        
        self.logger.debug(f"Created Enhanced Confluence Discord embed for {symbol}")
        
        return webhook_message