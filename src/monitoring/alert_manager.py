import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable, TYPE_CHECKING, Union, Tuple, Set
from datetime import datetime, timezone, timedelta
import aiohttp
import traceback
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
import requests
import aiofiles
import numpy as np
import pandas as pd
import sqlite3
import math
from src.utils.task_tracker import create_tracked_task

logger = logging.getLogger(__name__)


try:
    from discord import SyncWebhook
except ImportError:
    # Fallback for older discord.py versions
    try:
        from discord import Webhook as SyncWebhook
    except ImportError:
        # If discord.py is not available at all, create dummy class
        class SyncWebhook:
            def __init__(self, *args, **kwargs):
                pass
            def send(self, *args, **kwargs):
                pass
try:
    from src.utils.serializers import serialize_for_json, prepare_data_for_transmission
except ImportError:
    try:
        from utils.serializers import serialize_for_json, prepare_data_for_transmission
    except ImportError:
        # Fallback implementations
        def serialize_for_json(obj):
            return obj
        def prepare_data_for_transmission(obj):
            return obj

try:
    from src.utils.data_utils import resolve_price, format_price_string
except ImportError:
    try:
        from utils.data_utils import resolve_price, format_price_string
    except ImportError:
        # Fallback implementations
        def resolve_price(price):
            return float(price) if price is not None else 0.0
        def format_price_string(price):
            return f"${price:.2f}" if price is not None else "$0.00"

try:
    from src.models.schema import AlertPayload, ConfluenceAlert, SignalDirection
except ImportError:
    try:
        from models.schema import AlertPayload, ConfluenceAlert, SignalDirection
    except ImportError:
        # Create dummy classes if not available
        class AlertPayload:
            pass
        class ConfluenceAlert:
            pass
        class SignalDirection:
            LONG = "LONG"
            SHORT = "SHORT"

try:
    from src.core.reporting.report_manager import ReportManager
except ImportError:
    try:
        from core.reporting.report_manager import ReportManager
    except ImportError:
        # Create dummy class if not available
        class ReportManager:
            pass

# Import our centralized interpretation system
try:
    from src.core.interpretation.interpretation_manager import InterpretationManager
except ImportError:
    try:
        from core.interpretation.interpretation_manager import InterpretationManager
    except ImportError:
        # Create dummy class if not available
        class InterpretationManager:
            def process_interpretations(self, *args, **kwargs):
                return None

# Import our enhanced alert formatter
try:
    from src.monitoring.alert_formatter import AlertFormatter
except ImportError:
    try:
        from monitoring.alert_formatter import AlertFormatter
    except ImportError:
        # Create dummy class if not available
        class AlertFormatter:
            def format_whale_alert(self, *args, **kwargs):
                return {}
            def format_signal_alert(self, *args, **kwargs):
                return {}
            def get_formatted_interpretation(self, *args, **kwargs):
                return ""

if TYPE_CHECKING:
    pass  # No type checking imports needed currently

# Import alert storage
try:
    from src.database.alert_storage import AlertStorage
except ImportError:
    try:
        from database.alert_storage import AlertStorage
    except ImportError:
        AlertStorage = None

# Import alert persistence
try:
    from src.monitoring.alert_persistence import AlertPersistence, Alert, AlertType, AlertStatus
except ImportError:
    try:
        from monitoring.alert_persistence import AlertPersistence, Alert, AlertType, AlertStatus
    except ImportError:
        AlertPersistence = None
        Alert = None
        AlertType = None
        AlertStatus = None

logger = logging.getLogger(__name__)

class AlertManager:
    """Alert manager for monitoring system."""

    def __init__(self, config: Dict[str, Any], database: Optional[Any] = None, cache_adapter: Optional[Any] = None):
        """Initialize AlertManager.

        Args:
            config: Configuration dictionary
            database: Optional database client
            cache_adapter: Optional async cache adapter for dashboard caching
        """
        self.config = config
        self.database = database
        self.cache_adapter = cache_adapter  # Async cache for dashboard alerts
        self.alerts = []
        self.logger = logging.getLogger(__name__)
        self.handlers = []
        self.alert_handlers = {}
        self.webhook = None
        self.discord_webhook_url = None
        self._client_session = None
        self.long_threshold = 60.0
        self.short_threshold = 40.0
        
        # Alert tracking (no longer used for deduplication)
        self._last_alert_times = {}  # Symbol -> timestamp mapping for all alerts
        
        # Initialize enhanced alert formatter
        self.alert_formatter = AlertFormatter() 
        self._deduplication_window = 0  # Deduplication disabled (was 5 seconds)
        self._alert_hashes = {}  # Hash -> timestamp mapping for content tracking
        
        # Initialize improved throttling system
        self._init_improved_throttling()
        self._last_liquidation_alert = {}  # Dictionary to track last liquidation alerts by symbol
        self._last_large_order_alert = {}  # Dictionary to track last large order alerts by symbol
        self._last_whale_activity_alert = {}  # Dictionary to track last whale activity alerts by symbol
        self._last_alert = {}  # Dictionary to track last alerts by alert key
        
        # Mock mode for testing
        self.mock_mode = False  # Mock mode disabled in production
        self.capture_alerts = config.get('monitoring', {}).get('alerts', {}).get('capture_alerts', False)
        if self.capture_alerts:
            self.captured_alerts = []
            self.logger.info("Alert capture enabled for testing")
        
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
        self.liquidation_threshold = 500000  # Default $500k threshold for liquidation alerts (matches config.yaml)
        self.liquidation_cooldown = 300  # Default 5 minutes cooldown between liquidation alerts for the same symbol
        self.large_order_cooldown = 300  # Default 5 minutes cooldown between large order alerts for the same symbol

        # Aggregate liquidation tracking - alerts when cumulative liquidations exceed threshold within time window
        self._liquidation_buffer = {}  # Symbol -> list of (timestamp, usd_value, side, price, size) tuples
        self._liquidation_buffer_global = []  # Global list of (timestamp, symbol, usd_value, side, price, size) for cross-symbol aggregation
        self._last_aggregate_alert = {}  # Symbol -> timestamp of last aggregate alert
        self._last_global_aggregate_alert = 0  # Timestamp of last global aggregate alert
        self.aggregate_liquidation_threshold = 1000000  # $1M aggregate threshold (Conservative - filters bottom 28% noise)
        self.aggregate_liquidation_window = 300  # 5 minute window for aggregation
        self.aggregate_liquidation_cooldown = 600  # 10 minute cooldown between aggregate alerts
        self.global_aggregate_threshold = 2000000  # $2M for cross-symbol aggregate alerts (Conservative)
        self.global_aggregate_cooldown = 900  # 15 minute cooldown for global alerts
        self.whale_activity_cooldown = 900  # Default 15 minutes cooldown between whale activity alerts for the same symbol

        # QUICK WIN ENHANCEMENT: OI, Liquidation, and LSR tracking for manipulation alerts
        self._oi_history = {}  # Symbol -> deque of (timestamp, oi_value) tuples
        self._oi_history_limit = 100  # Keep last 100 OI readings per symbol (~30 min at 20s intervals)
        self.liquidation_cache = None  # Will be set externally if available

        # Manipulation detection configuration
        self.manipulation_thresholds = {
            'volume': {
                'critical': 10_000_000,  # $10M+
                'high': 5_000_000,       # $5M+
                'moderate': 2_000_000,   # $2M+
                'low': 0                 # < $2M
            },
            'trades': {
                'critical': 10,  # 10+ trades
                'high': 5,       # 5+ trades
                'moderate': 3,   # 3+ trades
                'low': 0         # < 3 trades
            },
            'ratio': {
                'critical_high': 10,   # 10:1+ ratio
                'critical_low': 0.1,   # 1:10+ ratio (inverse)
                'high_high': 5,        # 5:1+ ratio
                'high_low': 0.2,       # 1:5+ ratio (inverse)
                'moderate_high': 3,    # 3:1+ ratio
                'moderate_low': 0.33,  # 1:3+ ratio (inverse)
            }
        }
        self.manipulation_severity_weights = {
            'volume': 0.4,    # 40% weight
            'trades': 0.3,    # 30% weight
            'ratio': 0.3      # 30% weight
        }
        self.manipulation_severity_score_thresholds = {
            'extreme': 3.5,    # Score >= 3.5
            'high': 2.5,       # Score >= 2.5
            'moderate': 1.5    # Score >= 1.5
        }
        
        # Discord configuration
        self.discord_client = None
        
        # Enhanced webhook configuration with retry logic
        self.webhook_max_retries = config.get('monitoring', {}).get('alerts', {}).get('webhook_max_retries', 3)
        self.webhook_initial_retry_delay = config.get('monitoring', {}).get('alerts', {}).get('webhook_retry_delay', 1.0)
        self.webhook_exponential_backoff = config.get('monitoring', {}).get('alerts', {}).get('webhook_exponential_backoff', True)
        self.webhook_timeout = config.get('monitoring', {}).get('alerts', {}).get('webhook_timeout', 30.0)
        
        # File attachment limits
        self.max_file_size = config.get('monitoring', {}).get('alerts', {}).get('max_file_size', 25 * 1024 * 1024)  # 25MB default
        
        # Initialize alert storage for persistence
        self.alert_storage = None
        if AlertStorage:
            try:
                db_path = config.get('database', {}).get('url', 'sqlite:///./data/virtuoso.db')
                if db_path.startswith('sqlite:///'):
                    db_path = db_path.replace('sqlite:///', '')
                self.alert_storage = AlertStorage(db_path)
                self.logger.info("Alert storage initialized for persistence")
            except Exception as e:
                self.logger.error(f"Failed to initialize alert storage: {e}")
                self.alert_storage = None
        
        # Initialize new alert persistence system
        self.alert_persistence = None
        if AlertPersistence:
            try:
                # MIGRATION 2025-12-06: Consolidated to virtuoso.db (was alerts.db)
                # All alerts now go to a single database for unified dashboard access
                alerts_db_path = config.get('monitoring', {}).get('alerts', {}).get('db_path', 'data/virtuoso.db')
                self.alert_persistence = AlertPersistence(alerts_db_path, logger=self.logger)
                self.logger.info(f"Alert persistence system initialized at {alerts_db_path}")
            except Exception as e:
                self.logger.error(f"Failed to initialize alert persistence: {e}")
                self.alert_persistence = None
        self.allowed_file_types = config.get('monitoring', {}).get('alerts', {}).get('allowed_file_types', ['.pdf', '.png', '.jpg', '.jpeg'])
        
        # Delivery tracking
        self._delivery_stats = {
            'total_attempts': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'retries': 0,
            'file_attachments': 0,
            'file_attachment_failures': 0
        }
        
        # Metrics tracking
        self._ohlcv_cache = {}  # Cache for OHLCV data
        self._market_data_cache = {}  # Cache for market data
        
        # Initialize the centralized interpretation manager
        self.interpretation_manager = InterpretationManager()
        self.logger.info("Initialized centralized InterpretationManager for alerts")
        self._last_ohlcv_update = {}  # Last update time for OHLCV data
        
        # Log initialization
        self.logger.debug("Initializing AlertManager")
        
        # Initialize Discord webhook URL as empty - will be populated from config or environment
        self.discord_webhook_url = ""
        self.logger.debug("Discord webhook URL will be loaded from config or environment variables")
        
        # System webhook URL (for system alerts)
        self.system_webhook_url = ""

        # Whale alerts webhook URL (dedicated channel for whale trade alerts)
        self.whale_webhook_url = ""

        # Liquidation alerts webhook URL (dedicated channel for liquidation alerts)
        self.liquidation_webhook_url = ""

        # Predictive alerts webhook URL (dedicated channel for predictive liquidation alerts)
        self.predictive_webhook_url = ""

        # Development webhook URL (for testing alerts before production)
        self.development_webhook_url = ""
        self.use_development_mode = False  # Toggle to route all alerts to development webhook

        # Additional configurations from config file
        if 'monitoring' in self.config and 'alerts' in self.config['monitoring']:
            alert_config = self.config['monitoring']['alerts']
            self.logger.info(f"DEBUG: alert_config keys: {list(alert_config.keys())}")

            # Discord webhook - first check from direct path in config
            if 'discord_webhook_url' in alert_config:
                self.logger.info(f"DEBUG: discord_webhook_url in config: {repr(alert_config['discord_webhook_url'])}")
                if alert_config['discord_webhook_url']:
                    self.discord_webhook_url = alert_config['discord_webhook_url'].strip()
                    if self.discord_webhook_url:
                            pass  # logger.debug(f" Webhook URL from direct config: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")  # Disabled verbose config dump
                    else:
                        self.logger.debug(" Discord webhook URL from direct config is empty after stripping")
            # Then check nested discord > webhook_url path (old format)
            elif 'discord' in alert_config and 'webhook_url' in alert_config['discord'] and alert_config['discord']['webhook_url']:
                self.discord_webhook_url = alert_config['discord']['webhook_url'].strip()
                if self.discord_webhook_url:
                        pass  # logger.debug(f" Webhook URL from nested config: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")  # Disabled verbose config dump
                else:
                    self.logger.debug(" Discord webhook URL from nested config is empty after stripping")

            # Always check environment variable as fallback if config is empty
            if not self.discord_webhook_url:
                env_webhook = os.getenv('DISCORD_WEBHOOK_URL', '')
                self.logger.info(f"DEBUG: Checking environment for DISCORD_WEBHOOK_URL: {bool(env_webhook)}")
                if env_webhook:
                    self.logger.info(f"DEBUG: Raw env value length: {len(env_webhook)}")
                self.discord_webhook_url = env_webhook  # Use environment variable instead of hardcoded value
                if self.discord_webhook_url:
                    # Fix potential newline issues
                    self.discord_webhook_url = self.discord_webhook_url.strip().replace('\n', '')
                    if self.discord_webhook_url:
                            self.logger.info(f"✅ Webhook URL loaded from environment: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
                    else:
                        self.logger.debug(" Discord webhook URL from environment is empty after cleaning")
                else:
                    self.logger.warning("No Discord webhook URL found in config or environment")
            
            # Load system webhook URL
            if 'system_alerts_webhook_url' in alert_config:
                system_webhook_raw = alert_config['system_alerts_webhook_url']
                # Handle environment variable substitution
                if system_webhook_raw and system_webhook_raw.startswith('${') and system_webhook_raw.endswith('}'):
                    env_var_name = system_webhook_raw[2:-1]  # Remove ${ and }
                    self.system_webhook_url = os.getenv(env_var_name, '')
                    if self.system_webhook_url:
                        self.system_webhook_url = self.system_webhook_url.strip().replace('\n', '')
                        if self.system_webhook_url:
                            self.logger.info(f"✅ System webhook URL loaded from ${{{env_var_name}}}: {self.system_webhook_url[:30]}...{self.system_webhook_url[-15:]}")
                        else:
                            self.logger.warning(f"⚠️  System webhook URL from ${{{env_var_name}}} is empty after cleaning")
                    else:
                        self.logger.warning(f"⚠️  Environment variable ${{{env_var_name}}} not set or empty - system alerts will fail")
                        self.system_webhook_url = ''
                else:
                    # Direct value from config
                    self.system_webhook_url = system_webhook_raw or ''
                    if self.system_webhook_url:
                        self.logger.info(f"✅ System webhook URL from config: {self.system_webhook_url[:30]}...{self.system_webhook_url[-15:]}")
                    else:
                        self.logger.warning("⚠️  System webhook URL from config is None or empty")
            else:
                # Fallback to environment variable
                self.logger.warning("⚠️  'system_alerts_webhook_url' not in config, trying fallback environment variable")
                self.system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL', '')
                if self.system_webhook_url:
                    self.system_webhook_url = self.system_webhook_url.strip().replace('\n', '')
                    if self.system_webhook_url:
                        self.logger.info(f"✅ System webhook URL from fallback environment: {self.system_webhook_url[:30]}...{self.system_webhook_url[-15:]}")
                    else:
                        self.logger.warning("⚠️  System webhook URL from fallback environment is empty after cleaning")
                else:
                    self.logger.error("❌ SYSTEM_ALERTS_WEBHOOK_URL not found anywhere - system alerts will NOT work")

            # Load whale alerts webhook URL from environment
            whale_webhook_url = os.getenv('WHALE_ALERTS_WEBHOOK_URL', '')
            if whale_webhook_url:
                self.whale_webhook_url = whale_webhook_url.strip().replace('\n', '')
                if self.whale_webhook_url:
                    self.logger.info(f"✅ Whale alerts webhook URL loaded: {self.whale_webhook_url[:30]}...{self.whale_webhook_url[-15:]}")
                else:
                    self.logger.debug("Whale alerts webhook URL empty after cleaning")
            else:
                self.logger.info("ℹ️  No dedicated whale webhook URL - whale alerts will use main webhook")

            # Load liquidation alerts webhook URL from environment
            liquidation_webhook_url = os.getenv('LIQUIDATION_ALERTS_WEBHOOK_URL', '')
            if liquidation_webhook_url:
                self.liquidation_webhook_url = liquidation_webhook_url.strip().replace('\n', '')
                if self.liquidation_webhook_url:
                    self.logger.info(f"✅ Liquidation alerts webhook URL loaded: {self.liquidation_webhook_url[:30]}...{self.liquidation_webhook_url[-15:]}")
                else:
                    self.logger.debug("Liquidation alerts webhook URL empty after cleaning")
            else:
                self.logger.info("ℹ️  No dedicated liquidation webhook URL - liquidation alerts will use main webhook")

            # Load predictive alerts webhook URL from environment
            predictive_webhook_url = os.getenv('DISCORD_PREDICTIVE_WEBHOOK_URL', '')
            if predictive_webhook_url:
                self.predictive_webhook_url = predictive_webhook_url.strip().replace('\n', '')
                if self.predictive_webhook_url:
                    self.logger.info(f"✅ Predictive alerts webhook URL loaded: {self.predictive_webhook_url[:30]}...{self.predictive_webhook_url[-15:]}")
                else:
                    self.logger.debug("Predictive alerts webhook URL empty after cleaning")
            else:
                self.logger.info("ℹ️  No dedicated predictive webhook URL - predictive alerts will use main webhook")

            # Load development webhook URL from environment
            development_webhook_url = os.getenv('DEVELOPMENT_WEBHOOK_URL', '')
            if development_webhook_url:
                self.development_webhook_url = development_webhook_url.strip().replace('\n', '')
                if self.development_webhook_url:
                    self.logger.info(f"✅ Development webhook URL loaded: {self.development_webhook_url[:30]}...{self.development_webhook_url[-15:]}")
                    # Check if DEVELOPMENT_MODE environment variable is set
                    dev_mode = os.getenv('DEVELOPMENT_MODE', 'false').lower()
                    if dev_mode in ['true', '1', 'yes']:
                        self.use_development_mode = True
                        self.logger.warning("⚠️  DEVELOPMENT MODE ENABLED - All alerts will route to development webhook!")
                    else:
                        self.logger.info("ℹ️  Development webhook configured but not active (set DEVELOPMENT_MODE=true to enable)")
                else:
                    self.logger.debug("Development webhook URL empty after cleaning")
            else:
                self.logger.debug("ℹ️  No development webhook URL configured")

            # Direct discord webhook from config (alternative path) - only override if not already set
            if 'discord_network' in alert_config and alert_config['discord_network'] and not self.discord_webhook_url:
                self.discord_webhook_url = alert_config['discord_network'].strip()
                if self.discord_webhook_url:
                        self.logger.debug(f" Webhook URL from discord_network: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")
                else:
                    self.logger.debug(" Discord webhook URL from discord_network is empty after stripping")
            
            # Thresholds
            if 'thresholds' in alert_config:
                if 'buy' in alert_config['thresholds']:
                    self.long_threshold = alert_config['thresholds'].get('long', alert_config['thresholds'].get('buy', 60))
                if 'short' in alert_config['thresholds'] or 'sell' in alert_config['thresholds']:
                    self.short_threshold = alert_config['thresholds'].get('short', alert_config['thresholds'].get('sell', 40))
            
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
                    self.logger.debug(f" Loaded liquidation threshold from config: ${self.liquidation_threshold:,}")
                    
            # Load whale activity configuration
            if 'whale_activity' in alert_config:
                if 'alert_threshold_usd' in alert_config['whale_activity']:
                    self.whale_activity_threshold = alert_config['whale_activity']['alert_threshold_usd']
                    self.logger.debug(f" Loaded whale activity alert threshold from config: ${self.whale_activity_threshold:,}")
                else:
                    self.whale_activity_threshold = 0  # Default: allow all whale alerts
                if 'cooldown' in alert_config['whale_activity']:
                    self.whale_activity_cooldown = alert_config['whale_activity']['cooldown']
            else:
                self.whale_activity_threshold = 0  # Default: allow all whale alerts
        
        # Discord webhook retry configuration
        monitoring_config = self.config.get('monitoring', {})
        discord_config = monitoring_config.get('alerts', {}).get('discord_webhook', {})
        self.webhook_max_retries = discord_config.get('max_retries', 3)
        self.webhook_initial_retry_delay = discord_config.get('initial_retry_delay', 2)
        self.webhook_timeout = discord_config.get('timeout_seconds', 30)
        self.webhook_exponential_backoff = discord_config.get('exponential_backoff', True)
        self.webhook_fallback_enabled = discord_config.get('fallback_enabled', True)
        self.webhook_recoverable_status_codes = discord_config.get('recoverable_status_codes', [429, 500, 502, 503, 504])
        
        # Fix: Ensure minimum retry attempts
        if self.webhook_max_retries < 1:
            self.webhook_max_retries = 3
            self.logger.warning(f"Discord webhook max_retries was {discord_config.get('max_retries', 'not set')}, setting to minimum of 3")
        
        # Initialize PDF generation capabilities
        self.pdf_generator = None
        self.report_manager = None
        self.pdf_enabled = False
        
        try:
            # Import PDF components with error handling
            from src.core.reporting.pdf_generator import ReportGenerator
            from src.core.reporting.report_manager import ReportManager
            
            # Initialize PDF generator
            self.pdf_generator = ReportGenerator(config)
            self.logger.info("✅ PDF Generator initialized for AlertManager")
            
            # Initialize report manager
            self.report_manager = ReportManager(config)
            self.logger.info("✅ Report Manager initialized for AlertManager")
            
            self.pdf_enabled = True
            self.logger.info("🔧 PDF generation enabled in AlertManager")
            
        except Exception as e:
            self.logger.warning(f"⚠️ PDF generation not available in AlertManager: {str(e)}")
            self.logger.warning("Discord alerts will still work without PDF attachments")
            self.pdf_generator = None
            self.report_manager = None
            self.pdf_enabled = False

        # FINAL FALLBACK: Always check environment variables if webhook URL still not set
        if not self.discord_webhook_url or self.discord_webhook_url.strip() == "":
            env_webhook = os.getenv('DISCORD_WEBHOOK_URL', '')
            if env_webhook and env_webhook.strip():
                self.discord_webhook_url = env_webhook.strip().replace('\n', '')
                self.logger.info(f"✅ Discord webhook loaded from environment variable: {self.discord_webhook_url[:20]}...{self.discord_webhook_url[-10:]}")

        # Force initialize handlers
        try:
            self._initialize_handlers()
            self.logger.debug(f"Handlers after initialization: {self.handlers}")
        except Exception as e:
            self.logger.error(f"Error initializing handlers: {str(e)}")

        # Test Discord webhook
        # self.test_discord_webhook()  # Removed test webhook to prevent startup alerts

        # Log critical information for troubleshooting
        self.logger.info(f"Long threshold: {self.long_threshold}")
        self.logger.info(f"Short threshold: {self.short_threshold}")
        self.logger.info(f"Discord webhook URL is set: {bool(self.discord_webhook_url)}")
        self.logger.info(f"PDF generation enabled: {self.pdf_enabled}")
        
        try:
            # Validate configuration
            self._validate_alert_config()
            
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
                if name in self.handlers:
                    self.logger.debug(f"Handler {name} already registered, skipping")
                    return
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
            
            # Load system webhook configuration early for use in all special handling sections
            system_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('system_alerts', {})
            use_system_webhook = system_alerts_config.get('use_system_webhook', False)
            types_config = system_alerts_config.get('types', {})
            
            # Check if mirroring is enabled globally
            mirror_config = system_alerts_config.get('mirror_alerts', {})
            should_mirror = mirror_config.get('enabled', False)
            
            # Check if this is a market report alert that should be mirrored to system webhook
            is_market_report = False
            if details and details.get('type') == 'market_report':
                is_market_report = True
                # Check if mirroring is enabled for market reports
                should_mirror_market_report = should_mirror and mirror_config.get('types', {}).get('market_report', False)
                
                if should_mirror_market_report and self.system_webhook_url:
                    self.logger.info(f"Mirroring market report alert to system webhook")
                    await self._send_system_webhook_alert(message, details)
                    
                if use_system_webhook and types_config.get('market_report', False) and not should_mirror_market_report:
                    # Send only to system webhook and skip main webhook
                    self.logger.info(f"Routing market report alert to system webhook only")
                    await self._send_system_webhook_alert(message, details)
                    self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                    self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                    return  # Skip sending to main webhook

            # Check if this is a CPU alert that should be routed to system webhook
            is_cpu_alert = False
            if "cpu_usage" in message.lower() or (details and details.get('type') == 'cpu'):
                is_cpu_alert = True
                # Check backward compatibility with cpu_alerts.use_system_webhook
                cpu_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})
                cpu_system_webhook = use_system_webhook and types_config.get('cpu', False)
                cpu_system_webhook = cpu_system_webhook or cpu_alerts_config.get('use_system_webhook', False)
                
                # Check if mirroring is enabled for CPU alerts
                should_mirror_cpu = should_mirror and mirror_config.get('types', {}).get('cpu', False)
                
                if should_mirror_cpu and self.system_webhook_url:
                    # Send to system webhook (will also send to main webhook later)
                    self.logger.info(f"Mirroring CPU alert to system webhook")
                    await self._send_system_webhook_alert(message, details)
                
                elif cpu_system_webhook and self.system_webhook_url:
                    # Send only to system webhook and skip main webhook
                    self.logger.info(f"Routing CPU alert to system webhook only")
                    await self._send_system_webhook_alert(message, details)
                    self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                    self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                    return  # Skip sending to main webhook

            # Generic system alert routing for all configured types
            if details and details.get('type'):
                alert_type = details.get('type')

                # Diagnostic logging for system webhook routing
                self.logger.info(f"🔍 Alert routing check for type '{alert_type}':")
                self.logger.info(f"  - use_system_webhook: {use_system_webhook}")
                self.logger.info(f"  - types_config.get('{alert_type}'): {types_config.get(alert_type, False)}")
                self.logger.info(f"  - system_webhook_url set: {bool(self.system_webhook_url)}")
                self.logger.info(f"  - should_mirror: {should_mirror}")

                # Check if this alert type should use system webhook
                if use_system_webhook and types_config.get(alert_type, False) and self.system_webhook_url:
                    # Check if mirroring is enabled for this type
                    should_mirror_type = should_mirror and mirror_config.get('types', {}).get(alert_type, False)

                    if should_mirror_type:
                        # Mirror to system webhook (will also send to main webhook later)
                        self.logger.info(f"✅ Mirroring {alert_type} alert to system webhook")
                        await self._send_system_webhook_alert(message, details)
                    else:
                        # Send only to system webhook and skip main webhook
                        self.logger.info(f"✅ Routing {alert_type} alert to system webhook ONLY (skipping main webhook)")
                        await self._send_system_webhook_alert(message, details)
                        self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        return  # Skip sending to main webhook
                else:
                    self.logger.info(f"⚠️  {alert_type} alert will use MAIN webhook (condition failed)")

            # Special handling for large order alerts
            if details and details.get('type') == 'large_aggressive_order':
                symbol = details.get('symbol', 'UNKNOWN')
                current_time = time.time()
                
                # Check symbol-specific cooldown
                if throttle and (current_time - self._last_large_order_alert.get(symbol, 0) < self.large_order_cooldown):
                    self.logger.debug(f"Large order alert throttled for {symbol}")
                    return
                
                self._last_large_order_alert[symbol] = current_time
                
                # Check if large order alerts should use system webhook
                large_order_system_webhook = use_system_webhook and types_config.get('large_aggressive_order', False)
                should_mirror_large_order = should_mirror and mirror_config.get('types', {}).get('large_aggressive_order', False)
                
                if large_order_system_webhook and should_mirror_large_order and self.system_webhook_url:
                    # Send to system webhook (mirroring enabled)
                    self.logger.info(f"Mirroring large order alert to system webhook")
                    await self._send_system_webhook_alert(message, details)
                elif large_order_system_webhook and not should_mirror_large_order and self.system_webhook_url:
                    # Send to system webhook only
                    self.logger.info(f"Routing large order alert to system webhook only")
                    await self._send_system_webhook_alert(message, details)
                    self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                    self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                    return  # Skip sending to main webhook
            
                # Send large order Discord embed alert
                if 'discord' in self.handlers:
                    # Extract order data
                    order_data = details.get('data', {})
                    side = order_data.get('side', 'UNKNOWN').upper()
                    size = order_data.get('size', 0)
                    price = order_data.get('price', 0)
                    usd_value = order_data.get('usd_value', size * price)
                    
                    # Determine emoji and color based on side
                    if side == 'BUY':
                        emoji = "🟢"
                        color = 0x00FF00  # Green
                        impact_text = "buying pressure"
                    else:
                        emoji = "🔴"
                        color = 0xFF0000  # Red
                        impact_text = "selling pressure"
                    
                    # Create description
                    description = (
                        f"{emoji} **Large Aggressive Order Detected** for {symbol}\n"
                        f"• **Side:** {side}\n"
                        f"• **Size:** {size:,.4f} units\n"
                        f"• **Price:** ${price:,.4f}\n"
                        f"• **Value:** ${usd_value:,.2f}\n"
                        f"• **Impact:** Immediate {impact_text} on market"
                    )
                    
                    # Create Discord embed
                    embed = DiscordEmbed(
                        title=f"💥 Large Aggressive Order: {symbol}",
                        description=description,
                        color=color
                    )
                    
                    # Add timestamp
                    embed.set_timestamp()
                    
                    # Add order details as fields
                    embed.add_embed_field(
                        name="Order Side",
                        value=side,
                        inline=True
                    )
                    
                    embed.add_embed_field(
                        name="Order Size", 
                        value=f"{size:,.4f}",
                        inline=True
                    )
                    
                    embed.add_embed_field(
                        name="USD Value",
                        value=f"${usd_value:,.2f}",
                        inline=True
                    )
                    
                    # Add footer
                    embed.set_footer(text="Virtuoso Large Order Detection")

                    # Use centralized routing (supports dev mode override)
                    webhook_url, webhook_type = self._get_webhook_url("large_order")
                    if not webhook_url:
                        self.logger.warning("No webhook URL configured for large order alerts")
                        return

                    # Create webhook and send
                    webhook = DiscordWebhook(url=webhook_url)
                    webhook.add_embed(embed)

                    # Execute webhook
                    response = webhook.execute()

                    # Check response status
                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"Sent large order alert to {webhook_type} webhook for {symbol}: {side} ${usd_value:,.2f}")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        return
                    else:
                        self.logger.warning(f"Failed to send large order alert: {response}")
                        # Continue with standard alert as fallback
            
            # Special handling for whale activity alerts
            if details and details.get('type') == 'whale_activity':
                # Debug logging to investigate UNKNOWN symbol issue
                self.logger.debug(f"Whale activity alert details: {details}")
                self.logger.debug(f"Details keys: {list(details.keys()) if details else 'None'}")
                
                symbol = details.get('symbol', 'UNKNOWN')
                current_time = time.time()
                subtype = details.get('subtype', 'unknown')
                
                # Debug logging for extracted values
                self.logger.debug(f"Extracted symbol: '{symbol}', subtype: '{subtype}'")
                
                # Check USD value threshold (filter out alerts below threshold)
                if hasattr(self, 'whale_activity_threshold') and self.whale_activity_threshold > 0:
                    # Get USD value from details
                    activity_data = details.get('data', {})
                    net_usd_value = abs(activity_data.get('net_usd_value', 0))
                    
                    if net_usd_value < self.whale_activity_threshold:
                        self.logger.debug(f"Whale activity alert filtered out: ${net_usd_value:,.0f} < ${self.whale_activity_threshold:,.0f} threshold for {symbol}")
                        return
                    else:
                        self.logger.debug(f"Whale activity alert passed threshold: ${net_usd_value:,.0f} >= ${self.whale_activity_threshold:,.0f} for {symbol}")
                
                # Check symbol-specific cooldown
                if throttle and (current_time - self._last_whale_activity_alert.get(f"{symbol}:{subtype}", 0) < self.whale_activity_cooldown):
                    self.logger.debug(f"Whale activity alert ({subtype}) throttled for {symbol}")
                    return
                
                self._last_whale_activity_alert[f"{symbol}:{subtype}"] = current_time
                
                # Check if whale activity alerts should use system webhook
                whale_system_webhook = use_system_webhook and types_config.get('whale_activity', False)
                should_mirror_whale = should_mirror and mirror_config.get('types', {}).get('whale_activity', False)
                
                if whale_system_webhook and should_mirror_whale and self.system_webhook_url:
                    # Send to system webhook (mirroring enabled)
                    self.logger.info(f"Mirroring whale activity alert to system webhook")
                    await self._send_system_webhook_alert(message, details)
                elif whale_system_webhook and not should_mirror_whale and self.system_webhook_url:
                    # Send to system webhook only
                    self.logger.info(f"Routing whale activity alert to system webhook only")
                    await self._send_system_webhook_alert(message, details)
                    self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                    self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                    return  # Skip sending to main webhook
                
                # Enhanced formatting for Discord with market intelligence
                if 'discord' in self.handlers:
                    # Create enhanced alert with market context
                    emoji = "🐋📈" if subtype == "accumulation" else "🐋📉" if subtype == "distribution" else "🐋"

                    # Extract activity data for enhanced analysis
                    activity_data = details.get('data', {})

                    # CRITICAL FIX: Determine color based on ACTUAL whale action (not fake orderbook)
                    # Handles edge cases: equal volumes, zero volumes, insufficient data
                    whale_buy_volume = activity_data.get('whale_buy_volume', 0)
                    whale_sell_volume = activity_data.get('whale_sell_volume', 0)
                    trade_confirmation = activity_data.get('trade_confirmation', False)
                    whale_trades_count = activity_data.get('whale_trades_count', 0)

                    # Check if this is manipulation (conflicting signals)
                    is_manipulation = (whale_trades_count > 0 and not trade_confirmation)

                    if is_manipulation:
                        # Manipulation detected: Use color based on ACTUAL trade flow
                        # (Orderbook shows one thing, trades show another)
                        total_trade_volume = whale_buy_volume + whale_sell_volume

                        # Edge case: Insufficient trade volume data
                        if total_trade_volume < 1.0:
                            self.logger.warning(f"Manipulation detected but insufficient trade volume for {symbol}: {total_trade_volume:.2f}")
                            color = 0x888888  # Gray - insufficient data for directional signal
                        # Clear buying (fake sell wall)
                        elif whale_buy_volume > whale_sell_volume:
                            color = 0x00FF00  # Green - Whales actually buying (fake sell wall = bullish)
                        # Clear selling (fake buy wall)
                        elif whale_sell_volume > whale_buy_volume:
                            color = 0xFF0000  # Red - Whales actually selling (fake buy wall = bearish)
                        # Edge case: Equal volumes (ambiguous direction)
                        else:
                            color = 0x888888  # Gray - equal volumes, unclear manipulation direction
                            self.logger.debug(f"Equal whale volumes detected for {symbol}: buy={whale_buy_volume:.2f}, sell={whale_sell_volume:.2f}")
                    else:
                        # Normal signal: Color matches orderbook subtype
                        color = 0x00FF00 if subtype == "accumulation" else 0xFF0000 if subtype == "distribution" else 0x888888
                    self.logger.debug(f"Raw activity_data received: {activity_data}")
                    
                    # Core whale data
                    net_volume = activity_data.get('net_whale_volume', 0)
                    net_usd_value = activity_data.get('net_usd_value', 0)
                    whale_bid_orders = activity_data.get('whale_bid_orders', 0)
                    whale_ask_orders = activity_data.get('whale_ask_orders', 0)
                    bid_percentage = activity_data.get('bid_percentage', 0)
                    ask_percentage = activity_data.get('ask_percentage', 0)
                    imbalance = activity_data.get('imbalance', 0)
                    
                    # Trade execution data
                    whale_trades_count = activity_data.get('whale_trades_count', 0)
                    whale_buy_volume = activity_data.get('whale_buy_volume', 0)
                    whale_sell_volume = activity_data.get('whale_sell_volume', 0)
                    trade_imbalance = activity_data.get('trade_imbalance', 0)
                    trade_confirmation = activity_data.get('trade_confirmation', False)
                    
                    # Get current price from activity data
                    current_price = activity_data.get('current_price', 0)
                    # Additional fallback for price
                    if current_price == 0:
                        current_price = details.get('price', 0)
                    if current_price == 0 and 'market_data' in details:
                        current_price = details['market_data'].get('price', 0)
                    
                    # Fallback: calculate from bid/ask if not provided
                    if current_price == 0:
                        bid_usd = activity_data.get('whale_bid_usd', 0)
                        ask_usd = activity_data.get('whale_ask_usd', 0)
                        bid_volume = activity_data.get('whale_bid_volume', 0)
                        ask_volume = activity_data.get('whale_ask_volume', 0)
                        
                        if bid_volume > 0 or ask_volume > 0:
                            total_volume = bid_volume + ask_volume
                            total_usd = bid_usd + ask_usd
                            if total_volume > 0:
                                current_price = total_usd / total_volume
                    
                    # Generate unique alert ID
                    import time as time_module
                    alert_id = f"WA-{int(time_module.time())}-{symbol}"
                    
                    # Enhanced signal strength classification - Only EXECUTING and CONFLICTING
                    if whale_trades_count > 0 and not trade_confirmation:
                        signal_strength = "CONFLICTING"
                        strength_emoji = "🚨"
                        signal_context = "POTENTIAL MANIPULATION DETECTED"
                        manipulation_warning = True
                    elif whale_trades_count > 0:
                        signal_strength = "EXECUTING"
                        strength_emoji = "⚡"
                        signal_context = "Active whale trades happening now"
                        manipulation_warning = False
                    else:
                        # Skip POSITIONING and CONFIRMED alerts
                        return
                    
                    # Essential calculations only
                    volume_multiple = self._calculate_volume_multiple(abs(net_usd_value))

                    # Get market_data for enhanced context (OI, liquidations, LSR)
                    market_data = details.get('market_data', None)

                    # Plain English interpretation with enhanced context
                    interpretation = self._generate_plain_english_interpretation(
                        signal_strength, subtype, symbol, abs(net_usd_value),
                        whale_trades_count, whale_buy_volume, whale_sell_volume, signal_context,
                        market_data=market_data
                    )
                    
                    # Get individual trades/orders for display
                    trades_details = self._format_whale_trades(activity_data.get('top_whale_trades', []))
                    orders_details = self._format_whale_orders(activity_data.get('top_whale_bids', []), 
                                                             activity_data.get('top_whale_asks', []), subtype)
                    
                    # Build description with prominent manipulation warning if needed
                    if manipulation_warning:
                        # Optimized format: Action → Evidence → Context
                        description = (
                            f"🚨 **MANIPULATION ALERT** - {signal_context.upper()}\n"
                            f"{emoji} **{signal_strength} Whale {subtype.capitalize()}** {strength_emoji}\n"
                            f"**{symbol}**: ${current_price:,.2f} | ${abs(net_usd_value):,.0f} volume | {whale_trades_count} trades\n\n"
                            f"📊 **Evidence:**\n{trades_details}\n"
                            f"📋 **Order Book:**\n{orders_details}\n\n"
                            f"⚠️ **Risk Assessment:** {interpretation}"
                        )
                    else:
                        # Optimized format: Signal → Evidence → Context
                        description = (
                            f"{emoji} **{signal_strength} Whale {subtype.capitalize()}** {strength_emoji}\n"
                            f"**{symbol}**: ${current_price:,.2f} | ${abs(net_usd_value):,.0f} volume | {whale_trades_count} trades\n\n"
                            f"📊 **Evidence:**\n{trades_details}\n"
                            f"📋 **Order Book:**\n{orders_details}\n\n"
                            f"💡 **Analysis:** {interpretation}"
                        )
                    
                    # Create Discord embed
                    embed = DiscordEmbed(
                        description=description,
                        color=color
                    )
                    
                    embed.set_timestamp()
                    
                    # Add footer with Alert ID in the format: "Virtuoso Whale Detection • ID: WA-123456-BTCUSDT"
                    embed.set_footer(text=f"Virtuoso Whale Detection • ID: {alert_id}")
                    
                    # Optimized two-panel layout: Trade metrics and Signal info
                    embed.add_embed_field(
                        name="📊 Trade Metrics",
                        value=f"**{whale_buy_volume:.0f}** buy / **{whale_sell_volume:.0f}** sell\n{volume_multiple}",
                        inline=True
                    )

                    embed.add_embed_field(
                        name=f"{strength_emoji} Signal Strength",
                        value=f"**{signal_strength}**\n{signal_context}",
                        inline=True
                    )
                    
                    # Use centralized routing (supports dev mode override)
                    webhook_url, webhook_type = self._get_webhook_url("whale_activity")
                    if not webhook_url:
                        self.logger.warning("No webhook URL configured for enhanced whale activity alerts")
                        return

                    # Create webhook and add embed
                    webhook = DiscordWebhook(url=webhook_url)
                    webhook.add_embed(embed)

                    # Send webhook directly
                    response = webhook.execute()

                    # Check response status
                    webhook_sent = False
                    webhook_response = None
                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"Sent enhanced whale activity alert to {webhook_type} webhook for {symbol} ({subtype}) - {signal_strength}")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        webhook_sent = True
                        webhook_response = f"Status: {response.status_code}"
                    else:
                        self.logger.warning(f"Failed to send whale activity Discord alert: {response}")
                        webhook_response = f"Failed: {response}"
                    
                    # Persist alert to database
                    if self.alert_persistence and Alert and AlertType and AlertStatus:
                        try:
                            alert_obj = Alert(
                                alert_id=alert_id,
                                alert_type=AlertType.WHALE.value,
                                symbol=symbol,
                                timestamp=time.time(),
                                title=f"Whale {subtype.capitalize()} Alert - {symbol}",
                                message=description,
                                data={
                                    'net_usd_value': net_usd_value,
                                    'whale_trades_count': whale_trades_count,
                                    'whale_buy_volume': whale_buy_volume,
                                    'whale_sell_volume': whale_sell_volume,
                                    'signal_strength': signal_strength,
                                    'current_price': current_price,
                                    'volume_multiple': volume_multiple,
                                    'interpretation': interpretation,
                                    'subtype': subtype,
                                    'trades_details': trades_details,
                                    'orders_details': orders_details
                                },
                                status=AlertStatus.SENT.value if webhook_sent else AlertStatus.FAILED.value,
                                webhook_sent=webhook_sent,
                                webhook_response=webhook_response,
                                priority='high' if signal_strength == 'EXECUTING' else 'normal',
                                tags=[subtype, signal_strength, symbol]
                            )
                            create_tracked_task(self.alert_persistence.save_alert, name="save_alert_task")
                            self.logger.debug(f"Alert {alert_id} queued for persistence")
                        except Exception as e:
                            self.logger.error(f"Failed to persist whale alert {alert_id}: {e}")
                    
                    if webhook_sent:
                        return
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
            
            # Persist alert to database if available
            if self.alert_storage:
                try:
                    # Prepare alert data for storage
                    alert_data = {
                        'alert_id': f"alert_{int(time.time() * 1000)}_{hash(message) & 0xFFFF}",
                        'alert_type': details.get('type', 'system') if details else 'system',
                        'symbol': details.get('symbol') if details else None,
                        'severity': level,
                        'title': message[:100],  # First 100 chars as title
                        'message': message,
                        'description': details.get('description', '') if details else '',
                        'confluence_score': details.get('confluence_score', details.get('score')) if details else None,
                        'price': details.get('price', details.get('current_price')) if details else None,
                        'volume': details.get('volume', details.get('volume_24h')) if details else None,
                        'change_24h': details.get('change_24h', details.get('price_change_percent')) if details else None,
                        'timestamp': int(alert['timestamp'] * 1000),  # Convert to milliseconds
                        'details': details,
                        'sent_to_discord': False  # Will be updated after successful send
                    }
                    
                    # Store in database
                    stored = self.alert_storage.store_alert(alert_data)
                    if stored:
                        # Add alert_id to the alert object for tracking
                        alert['alert_id'] = alert_data['alert_id']
                        self.logger.debug(f"Alert persisted to database: {alert_data['alert_id']}")
                except Exception as e:
                    self.logger.error(f"Failed to persist alert to database: {e}")
            
            # Process alert with debug info
            self.logger.debug("Processing alert through handlers")
            await self._process_alert(alert)
            self.logger.debug("Alert processing completed")
            
            # Cache signal for dashboard display
            await self._cache_signal_for_dashboard(message, details)

            # Cache alert for dashboard alerts endpoint
            await self._cache_alert_for_dashboard(level, message, details)

        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats['errors']) + 1
    
    async def _cache_signal_for_dashboard(self, message: str, details: Optional[Dict[str, Any]]) -> None:
        """Cache signal for dashboard display when alerts are sent"""
        try:
            # Only cache trading signals
            if not details or details.get('type') not in ['confluence', 'signal', 'whale_activity', 'large_aggressive_order', 'market_condition']:
                return
                
            # Import memcache client
            try:
                from pymemcache.client.base import Client
                from pymemcache import serde
            except ImportError:
                self.logger.debug("pymemcache not available for signal caching")
                return
            
            cache = Client(('localhost', 11211), serde=serde.pickle_serde)
            
            # Get existing signals
            existing = cache.get('analysis:signals')
            if not existing or not isinstance(existing, dict):
                existing = {'signals': [], 'count': 0, 'timestamp': int(time.time()), 'source': 'alert_manager'}
            
            # Create signal from alert
            symbol = details.get('symbol', 'UNKNOWN')
            score = details.get('confluence_score', details.get('score', 50))
            
            # Determine direction based on score or message content
            direction = 'neutral'
            if score > 60 or 'buy' in message.lower() or 'bullish' in message.lower():
                direction = 'buy'
            elif score < 40 or 'sell' in message.lower() or 'bearish' in message.lower():
                direction = 'sell'
            
            signal = {
                'symbol': symbol,
                'type': details.get('type', 'alert'),
                'direction': direction,
                'score': score,
                'timestamp': time.time(),
                'message': message[:200] if len(message) > 200 else message,
                'strength': 'strong' if abs(score - 50) > 20 else 'medium',
                'price': details.get('price', details.get('current_price', 0)),
                'volume': details.get('volume', details.get('volume_24h', 0)),
                'components': details.get('components', {})
            }
            
            # Add to signals list (keep last 50)
            existing['signals'].insert(0, signal)
            existing['signals'] = existing['signals'][:50]
            existing['count'] = len(existing['signals'])
            existing['timestamp'] = int(time.time())
            
            # Store in cache with 5 minute TTL
            cache.set('analysis:signals', existing, expire=300)
            
            # Also store individual signal for this symbol
            cache.set(f'signal:{symbol}', signal, expire=300)
            
            cache.close()
            
            self.logger.debug(f"Cached signal for {symbol} in dashboard signals (score: {score}, direction: {direction})")

        except Exception as e:
            self.logger.debug(f"Failed to cache signal for dashboard: {e}")

    async def _cache_alert_for_dashboard(self, level: str, message: str, details: Optional[Dict[str, Any]]) -> None:
        """Cache alert for dashboard display when alerts are sent.

        This method populates the 'dashboard:alerts' cache key that is read by
        the /api/dashboard/alerts endpoint.

        FIXED: Now uses async cache_adapter instead of synchronous pymemcache
        to avoid blocking the event loop and connection exhaustion issues.
        """
        try:
            # Create alert object for dashboard
            symbol = details.get('symbol', 'SYSTEM') if details else 'SYSTEM'
            alert_type = details.get('type', 'general') if details else 'general'

            alert = {
                'id': str(uuid.uuid4()),
                'type': alert_type,
                'level': level.lower(),
                'symbol': symbol,
                'message': message[:500] if len(message) > 500 else message,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'unix_timestamp': time.time(),
                'details': {
                    'price': details.get('price', details.get('current_price', 0)) if details else 0,
                    'change': details.get('change_24h', details.get('price_change', 0)) if details else 0,
                    'score': details.get('confluence_score', details.get('score', 0)) if details else 0,
                    'volume': details.get('volume', details.get('volume_24h', 0)) if details else 0
                }
            }

            # PRIMARY: Use async cache adapter if available (recommended)
            if self.cache_adapter:
                try:
                    existing = await self.cache_adapter.get('dashboard:alerts', [])
                    if not isinstance(existing, list):
                        existing = []

                    existing.insert(0, alert)
                    existing = existing[:100]  # Keep last 100 alerts

                    await self.cache_adapter.set('dashboard:alerts', existing, ttl=600)
                    self.logger.info(f"✅ Cached alert for dashboard via async adapter: {alert_type} - {symbol}")
                    return
                except Exception as adapter_error:
                    self.logger.warning(f"Async cache adapter failed: {adapter_error}")

            # FALLBACK: Use pymemcache with proper error handling
            try:
                from pymemcache.client.base import Client
                from pymemcache import serde

                cache = Client(('localhost', 11211), serde=serde.pickle_serde, connect_timeout=2, timeout=2)
                try:
                    existing = cache.get('dashboard:alerts')
                    if not existing or not isinstance(existing, list):
                        existing = []

                    existing.insert(0, alert)
                    existing = existing[:100]

                    cache.set('dashboard:alerts', existing, expire=600)
                    self.logger.info(f"✅ Cached alert for dashboard via pymemcache: {alert_type} - {symbol}")
                finally:
                    cache.close()

            except ImportError:
                self.logger.warning("pymemcache not available for alert caching fallback")
            except Exception as memcache_error:
                self.logger.warning(f"Memcache fallback failed: {memcache_error}")

        except Exception as e:
            # FIXED: Log at WARNING level for visibility, not DEBUG
            self.logger.warning(f"Failed to cache alert for dashboard: {e}", exc_info=True)

    async def _store_and_cache_alert_direct(
        self,
        alert_type: str,
        symbol: str,
        message: str,
        level: str = "INFO",
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Store alert in SQLite and cache for dashboard - for methods bypassing send_alert().

        This helper enables any alert method to persist alerts without going through
        the main send_alert() flow. Use this for aggregate alerts, signal alerts, etc.

        Args:
            alert_type: Type of alert (e.g., 'liquidation_cascade', 'signal', 'retail_pressure')
            symbol: Trading symbol or 'GLOBAL' for market-wide alerts
            message: Alert message/title
            level: Severity level (INFO, WARNING, ERROR, CRITICAL)
            details: Additional alert details

        Returns:
            alert_id if stored successfully, None otherwise
        """
        alert_id = None
        try:
            alert_id = f"alert_{int(time.time() * 1000)}_{hash(message) & 0xFFFF}"
            timestamp_ms = int(time.time() * 1000)

            # Store in SQLite if available
            if self.alert_storage:
                try:
                    alert_data = {
                        'alert_id': alert_id,
                        'alert_type': alert_type,
                        'symbol': symbol,
                        'severity': level,
                        'title': message[:100],
                        'message': message,
                        'description': details.get('description', '') if details else '',
                        'confluence_score': details.get('confluence_score', details.get('score')) if details else None,
                        'price': details.get('price', details.get('current_price')) if details else None,
                        'volume': details.get('volume', details.get('total_value')) if details else None,
                        'change_24h': details.get('change_24h') if details else None,
                        'timestamp': timestamp_ms,
                        'details': details,
                        'sent_to_discord': True  # These are sent directly to Discord
                    }
                    stored = self.alert_storage.store_alert(alert_data)
                    if stored:
                        self.logger.debug(f"✅ Alert stored in SQLite: {alert_type} - {symbol}")
                except Exception as e:
                    self.logger.warning(f"Failed to store alert in SQLite: {e}")

            # Cache for dashboard display
            await self._cache_alert_for_dashboard(level, message, {
                'type': alert_type,
                'symbol': symbol,
                **(details or {})
            })

            return alert_id

        except Exception as e:
            self.logger.warning(f"Failed to store/cache direct alert: {e}")
            return alert_id

    def _mark_alert_sent_to_discord(self, alert_id: str, response: Any = None) -> None:
        """Mark an alert as successfully sent to Discord in the database.
        
        Args:
            alert_id: The alert ID to update
            response: The webhook response object
        """
        if self.alert_storage and alert_id:
            try:
                # Update the existing alert record
                response_str = str(response) if response else "Success"
                with sqlite3.connect(self.alert_storage.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE alerts SET sent_to_discord = 1, webhook_response = ? WHERE alert_id = ?",
                        (response_str, alert_id)
                    )
                    conn.commit()
                    self.logger.debug(f"Marked alert {alert_id} as sent to Discord")
            except Exception as e:
                self.logger.error(f"Failed to update alert status in database: {e}")

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
            # First try to get alerts from database if available
            if self.alert_storage:
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
                            alert['level'] = alert['severity']
                        if 'alert_type' in alert and 'type' not in alert:
                            alert['type'] = alert['alert_type']
                    return alerts
                except Exception as e:
                    self.logger.error(f"Error retrieving alerts from database: {e}")
                    # Fall back to in-memory alerts
            
            # Fall back to in-memory alerts if database not available
            alerts = list(self._alerts)
            
            # Apply filters
            if level:
                level = level.upper()
                if level not in self.alert_levels:
                    logger.error(f"Invalid alert level: {level}")
                    return []
                alerts = [a for a in alerts if a.get('level', a.get('severity')) == level]
                
            if start_time is not None:
                start_time = float(start_time)
                alerts = [a for a in alerts if float(a.get('timestamp', 0)) >= start_time]
                
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
                
                # Create Discord embed for liquidation alert
                title = f"{direction_emoji} {position_type} LIQUIDATION: {symbol}"
                
                # Build description
                description = [
                    f"**{impact_emoji} Large liquidation detected** ({impact_level} impact)",
                    "",
                    f"• **Size:** {liquidation_data['size']:.4f} {base_asset}",
                    f"• **Price:** ${liquidation_data['price']:,.2f}",
                    f"• **Value:** ${usd_value:,.2f} {threshold_indicator}",
                    f"• **Time:** {timestamp} ({time_ago})",
                    "",
                    f"**Market Impact:**",
                    f"• Immediate {'buying 📈' if position_type == 'SHORT' else 'selling 📉'} pressure",
                    f"• Impact Level: **{impact_level}**",
                    f"• Impact Meter: `{impact_bar}`",
                    "",
                    f"**Analysis:** {price_action}"
                ]
                
                # Create Discord embed
                embed = DiscordEmbed(
                    title=title,
                    description="\n".join(description),
                    color=0xFF0000 if position_type == "LONG" else 0x00FF00  # Red for long liq, green for short liq
                )
                
                # Add timestamp
                embed.set_timestamp()
                
                # Add fields for key metrics
                embed.add_embed_field(
                    name="Position Type",
                    value=position_type,
                    inline=True
                )
                
                embed.add_embed_field(
                    name="Liquidation Size",
                    value=f"{liquidation_data['size']:.4f} {base_asset}",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="Impact Level",
                    value=impact_level,
                    inline=True
                )
                
                # Add footer
                embed.set_footer(text=f"Virtuoso Liquidation Monitor • Threshold: ${self.liquidation_threshold:,}")
                
                # Send as Discord embed instead of text alert
                if 'discord' in self.handlers:
                    # Use dedicated liquidation webhook if configured, otherwise fall back to main webhook
                    webhook_url = self.liquidation_webhook_url if self.liquidation_webhook_url else self.discord_webhook_url
                    webhook_type = "dedicated liquidation" if self.liquidation_webhook_url else "main"

                    webhook = DiscordWebhook(url=webhook_url)
                    webhook.add_embed(embed)

                    # Execute webhook
                    response = webhook.execute()

                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"✅ Sent liquidation alert to {webhook_type} webhook for {symbol}: ${usd_value:,.2f}")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        # Update last alert time for cooldown
                        self._last_liquidation_alert[symbol] = current_time
                        return
                    else:
                        self.logger.warning(f"Failed to send liquidation Discord embed to {webhook_type} webhook: {response}")
                
                # Fallback to standard alert if Discord embed fails
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

            # Always track liquidation for aggregate alerts (even if below single threshold)
            await self._track_liquidation_for_aggregate(
                symbol=symbol,
                usd_value=usd_value,
                side=liquidation_data['side'],
                price=liquidation_data['price'],
                size=liquidation_data['size'],
                timestamp=current_time
            )

        except Exception as e:
            self.logger.error(f"Error checking liquidation threshold: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _track_liquidation_for_aggregate(
        self,
        symbol: str,
        usd_value: float,
        side: str,
        price: float,
        size: float,
        timestamp: float
    ) -> None:
        """Track liquidation for aggregate alerts and check if threshold is exceeded.

        This method tracks all liquidations (regardless of size) and triggers alerts when
        the cumulative value within a time window exceeds the aggregate threshold.

        Args:
            symbol: Trading pair symbol
            usd_value: USD value of the liquidation
            side: 'Buy' (long liquidated) or 'Sell' (short liquidated)
            price: Liquidation price
            size: Position size
            timestamp: Unix timestamp of the event
        """
        try:
            current_time = time.time()

            # Clean up old entries from symbol buffer
            if symbol not in self._liquidation_buffer:
                self._liquidation_buffer[symbol] = []

            # Remove entries older than the aggregation window
            cutoff_time = current_time - self.aggregate_liquidation_window

            # Buffer entry format: (timestamp, usd_value, side, price, size)
            self._liquidation_buffer[symbol] = [
                entry for entry in self._liquidation_buffer[symbol]
                if entry[0] > cutoff_time
            ]

            # Add new liquidation to symbol buffer with full details
            self._liquidation_buffer[symbol].append((current_time, usd_value, side.upper(), price, size))

            # Also track in global buffer for cross-symbol aggregation
            # Global format: (timestamp, symbol, usd_value, side, price, size)
            self._liquidation_buffer_global = [
                entry for entry in self._liquidation_buffer_global
                if entry[0] > cutoff_time
            ]
            self._liquidation_buffer_global.append((current_time, symbol, usd_value, side.upper(), price, size))

            # Debug logging for buffer operations (helps verify aggregate tracking without waiting for threshold)
            symbol_buffer_total = sum(entry[1] for entry in self._liquidation_buffer[symbol])
            global_buffer_total = sum(entry[2] for entry in self._liquidation_buffer_global)
            self.logger.debug(
                f"Aggregate buffer update: {symbol} +${usd_value:,.0f} {side.upper()} @ {price:.4f} | "
                f"Symbol buffer: {len(self._liquidation_buffer[symbol])} entries (${symbol_buffer_total:,.0f}) | "
                f"Global buffer: {len(self._liquidation_buffer_global)} entries (${global_buffer_total:,.0f})"
            )

            # Check symbol-specific aggregate
            await self._check_symbol_aggregate_alert(symbol, current_time)

            # Check global aggregate (cross-symbol)
            await self._check_global_aggregate_alert(current_time)

        except Exception as e:
            self.logger.error(f"Error tracking liquidation for aggregate: {str(e)}")

    async def _check_symbol_aggregate_alert(self, symbol: str, current_time: float) -> None:
        """Check if symbol-specific aggregate liquidation threshold is exceeded."""
        try:
            # Check cooldown
            last_alert = self._last_aggregate_alert.get(symbol, 0)
            if current_time - last_alert < self.aggregate_liquidation_cooldown:
                return

            # Calculate aggregate value for this symbol
            # Buffer format: (timestamp, usd_value, side, price, size)
            buffer = self._liquidation_buffer.get(symbol, [])
            if len(buffer) < 3:  # Need at least 3 liquidations to be notable
                return

            total_value = sum(entry[1] for entry in buffer)
            long_value = sum(entry[1] for entry in buffer if entry[2] == 'BUY')
            short_value = sum(entry[1] for entry in buffer if entry[2] == 'SELL')

            # Check threshold
            if total_value >= self.aggregate_liquidation_threshold:
                # CRITICAL: Set cooldown IMMEDIATELY to prevent async race condition
                # Before this fix, the cooldown was set AFTER await _send_aggregate_liquidation_alert()
                # which allowed multiple concurrent calls to pass the cooldown check
                self._last_aggregate_alert[symbol] = current_time

                # Clear buffer IMMEDIATELY to prevent duplicate alerts with stale data
                buffer_copy = list(buffer)  # Copy for processing
                self._liquidation_buffer[symbol] = []

                # Extract additional metrics for improved alert
                # Find largest liquidation
                largest = max(buffer_copy, key=lambda x: x[1])
                largest_value = largest[1]
                largest_side = "LONG" if largest[2] == 'BUY' else "SHORT"
                largest_price = largest[3]

                # Calculate average liquidation price (weighted by value)
                total_weighted_price = sum(entry[1] * entry[3] for entry in buffer_copy)
                avg_liq_price = total_weighted_price / total_value if total_value > 0 else 0

                # Calculate time span and rate
                first_timestamp = min(entry[0] for entry in buffer_copy)
                time_span_seconds = current_time - first_timestamp
                rate_per_minute = (len(buffer_copy) / time_span_seconds * 60) if time_span_seconds > 0 else 0

                # Get current price from cache if available
                current_price = self._price_cache.get(symbol, avg_liq_price)

                await self._send_aggregate_liquidation_alert(
                    symbol=symbol,
                    total_value=total_value,
                    long_value=long_value,
                    short_value=short_value,
                    count=len(buffer_copy),
                    window_minutes=self.aggregate_liquidation_window // 60,
                    is_global=False,
                    largest_value=largest_value,
                    largest_side=largest_side,
                    largest_price=largest_price,
                    avg_liq_price=avg_liq_price,
                    current_price=current_price,
                    rate_per_minute=rate_per_minute
                )
                # NOTE: Cooldown and buffer clear now done at the start of this block
                # to prevent async race conditions

        except Exception as e:
            self.logger.error(f"Error checking symbol aggregate alert: {str(e)}")

    async def _check_global_aggregate_alert(self, current_time: float) -> None:
        """Check if global (cross-symbol) aggregate liquidation threshold is exceeded."""
        try:
            # Check cooldown
            if current_time - self._last_global_aggregate_alert < self.global_aggregate_cooldown:
                return

            # Calculate global aggregate
            # Global format: (timestamp, symbol, usd_value, side, price, size)
            buffer = self._liquidation_buffer_global
            if len(buffer) < 5:  # Need at least 5 liquidations across symbols
                return

            total_value = sum(entry[2] for entry in buffer)
            long_value = sum(entry[2] for entry in buffer if entry[3] == 'BUY')
            short_value = sum(entry[2] for entry in buffer if entry[3] == 'SELL')

            # Get affected symbols
            affected_symbols = list(set(entry[1] for entry in buffer))

            # Check threshold
            if total_value >= self.global_aggregate_threshold:
                # CRITICAL: Set cooldown IMMEDIATELY to prevent async race condition
                self._last_global_aggregate_alert = current_time

                # Clear buffer IMMEDIATELY and take a copy for processing
                buffer_copy = list(buffer)
                self._liquidation_buffer_global = []

                # Find largest liquidation across all symbols
                largest = max(buffer_copy, key=lambda x: x[2])
                largest_value = largest[2]
                largest_symbol = largest[1]
                largest_side = "LONG" if largest[3] == 'BUY' else "SHORT"
                largest_price = largest[4]

                # Calculate time span and rate
                first_timestamp = min(entry[0] for entry in buffer_copy)
                time_span_seconds = current_time - first_timestamp
                rate_per_minute = (len(buffer_copy) / time_span_seconds * 60) if time_span_seconds > 0 else 0

                # Get symbol-wise breakdown for top symbols
                symbol_values = {}
                for entry in buffer_copy:
                    sym = entry[1]
                    symbol_values[sym] = symbol_values.get(sym, 0) + entry[2]

                await self._send_aggregate_liquidation_alert(
                    symbol=", ".join(affected_symbols[:3]) + ("..." if len(affected_symbols) > 3 else ""),
                    total_value=total_value,
                    long_value=long_value,
                    short_value=short_value,
                    count=len(buffer_copy),
                    window_minutes=self.aggregate_liquidation_window // 60,
                    is_global=True,
                    affected_symbols=affected_symbols,
                    largest_value=largest_value,
                    largest_side=largest_side,
                    largest_price=largest_price,
                    largest_symbol=largest_symbol,
                    rate_per_minute=rate_per_minute,
                    symbol_breakdown=symbol_values
                )
                # NOTE: Cooldown and buffer clear now done at the start of this block
                # to prevent async race conditions

        except Exception as e:
            self.logger.error(f"Error checking global aggregate alert: {str(e)}")

    async def _send_aggregate_liquidation_alert(
        self,
        symbol: str,
        total_value: float,
        long_value: float,
        short_value: float,
        count: int,
        window_minutes: int,
        is_global: bool = False,
        affected_symbols: list = None,
        largest_value: float = 0,
        largest_side: str = "",
        largest_price: float = 0,
        largest_symbol: str = None,
        avg_liq_price: float = 0,
        current_price: float = 0,
        rate_per_minute: float = 0,
        symbol_breakdown: dict = None
    ) -> None:
        """Send improved Discord alert for aggregate liquidations with actionable context."""
        try:
            # Determine dominant direction
            if long_value > short_value * 1.5:
                dominant = "LONG"
                direction_emoji = "🔴"
            elif short_value > long_value * 1.5:
                dominant = "SHORT"
                direction_emoji = "🟢"
            else:
                dominant = "MIXED"
                direction_emoji = "⚡"

            # Determine severity based on value
            if total_value >= 1_000_000:
                severity = "🚨 CRITICAL"
                severity_color = 0xFF0000  # Red
            elif total_value >= 500_000:
                severity = "⚠️ HIGH"
                severity_color = 0xFF6600  # Orange
            elif total_value >= 250_000:
                severity = "📊 MODERATE"
                severity_color = 0xFFCC00  # Yellow
            else:
                severity = "ℹ️ NOTABLE"
                severity_color = 0x3399FF  # Blue

            # Build title
            if is_global:
                title = f"{direction_emoji} MARKET-WIDE LIQUIDATION CASCADE {severity}"
            else:
                title = f"{direction_emoji} {symbol} LIQUIDATION CASCADE {severity}"

            # Calculate percentages
            long_pct = (long_value / total_value * 100) if total_value > 0 else 0
            short_pct = 100 - long_pct

            # Build ASCII distribution bar (cleaner than emojis)
            bar_length = 20
            long_bars = int(bar_length * long_pct / 100)
            short_bars = bar_length - long_bars
            distribution_bar = f"`{'█' * long_bars}{'░' * short_bars}`"

            # Calculate rate indicator (compare to "normal" ~0.5/min baseline)
            rate_multiplier = rate_per_minute / 0.5 if rate_per_minute > 0 else 1
            rate_indicator = f"{rate_per_minute:.1f}/min"
            if rate_multiplier >= 3:
                rate_indicator += " 🔥🔥🔥"
            elif rate_multiplier >= 2:
                rate_indicator += " 🔥🔥"
            elif rate_multiplier >= 1.5:
                rate_indicator += " 🔥"

            # Build description with improved format
            description_lines = [
                f"**━━━ {window_minutes}-MINUTE SUMMARY ━━━**",
                f"📊 **Total:** ${total_value:,.0f} ({count} events)",
                f"⚡ **Rate:** {rate_indicator}",
                "",
                "**━━━ BREAKDOWN ━━━**",
                f"🔴 Longs:  ${long_value:,.0f} ({long_pct:.0f}%) {distribution_bar}",
                f"🟢 Shorts: ${short_value:,.0f} ({short_pct:.0f}%)",
            ]

            # Add price context for single-symbol alerts
            if not is_global and current_price > 0 and avg_liq_price > 0:
                price_diff_pct = ((current_price - avg_liq_price) / avg_liq_price) * 100
                price_direction = "above" if price_diff_pct > 0 else "below"
                description_lines.append("")
                description_lines.append("**━━━ KEY LEVELS ━━━**")
                description_lines.append(f"📈 Current: ${current_price:,.2f}")
                description_lines.append(f"📉 Avg Liq: ${avg_liq_price:,.2f} ({abs(price_diff_pct):.1f}% {price_direction})")

            # Add largest liquidation info
            if largest_value > 0:
                if is_global and largest_symbol:
                    description_lines.append(f"🐋 Largest: ${largest_value:,.0f} {largest_side} {largest_symbol} @ ${largest_price:,.2f}")
                elif largest_price > 0:
                    description_lines.append(f"🐋 Largest: ${largest_value:,.0f} {largest_side} @ ${largest_price:,.2f}")

            # Add symbol breakdown for global alerts
            if is_global and symbol_breakdown:
                description_lines.append("")
                description_lines.append(f"**━━━ TOP SYMBOLS ({len(affected_symbols or [])}) ━━━**")
                top_symbols = sorted(symbol_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
                for sym, val in top_symbols:
                    pct_of_total = (val / total_value * 100) if total_value > 0 else 0
                    description_lines.append(f"• {sym}: ${val:,.0f} ({pct_of_total:.0f}%)")

            # Add actionable trading context
            description_lines.append("")
            description_lines.append("**━━━ TRADING CONTEXT ━━━**")

            if dominant == "LONG":
                description_lines.append("• Heavy long liquidations = selling exhaustion")
                description_lines.append("• Watch for: Volume drop → bounce setup")
                if current_price > 0:
                    support = current_price * 0.995  # 0.5% below
                    description_lines.append(f"• Key support: ${support:,.0f}")
            elif dominant == "SHORT":
                description_lines.append("• Heavy short liquidations = buying exhaustion")
                description_lines.append("• Watch for: Volume drop → pullback setup")
                if current_price > 0:
                    resistance = current_price * 1.005  # 0.5% above
                    description_lines.append(f"• Key resistance: ${resistance:,.0f}")
            else:
                description_lines.append("• Mixed liquidations = high volatility")
                description_lines.append("• Consider: Reduce position size, widen stops")
                description_lines.append("• Wait for: Clear direction before entry")

            # Create Discord embed
            embed = DiscordEmbed(
                title=title,
                description="\n".join(description_lines),
                color=severity_color
            )
            embed.set_timestamp()

            # Add footer with threshold info
            threshold_display = self.global_aggregate_threshold if is_global else self.aggregate_liquidation_threshold
            embed.set_footer(text=f"Aggregate Alert • Window: {window_minutes}min • Threshold: ${threshold_display:,.0f}")

            # Send to Discord (use liquidation alert type for routing)
            await self._send_discord_embed(embed, alert_type="liquidation")

            # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
            await self._store_and_cache_alert_direct(
                alert_type='liquidation_cascade',
                symbol='GLOBAL' if is_global else symbol,
                message=title,
                level='CRITICAL' if total_value >= 1_000_000 else 'WARNING',
                details={
                    'total_value': total_value,
                    'long_value': long_value,
                    'short_value': short_value,
                    'count': count,
                    'dominant': dominant,
                    'window_minutes': window_minutes,
                    'rate_per_minute': rate_per_minute,
                    'is_global': is_global,
                    'affected_symbols': affected_symbols,
                    'largest_value': largest_value,
                    'largest_side': largest_side,
                    'current_price': current_price
                }
            )

            # Log the alert
            self.logger.warning(
                f"Aggregate liquidation alert: {'GLOBAL' if is_global else symbol} - "
                f"${total_value:,.0f} total ({count} events @ {rate_per_minute:.1f}/min) - "
                f"Longs: ${long_value:,.0f} / Shorts: ${short_value:,.0f}"
            )

        except Exception as e:
            self.logger.error(f"Error sending aggregate liquidation alert: {str(e)}")
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
            signal_type: The type of signal (LONG, SHORT, NEUTRAL)
            
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
        long_threshold: Optional[float] = None,
        short_threshold: Optional[float] = None,
        price: Optional[float] = None,  # Optional direct price
        transaction_id: Optional[str] = None,  # Transaction ID for tracking
        signal_id: Optional[str] = None,  # Signal ID for tracking within SignalGenerator
        influential_components: Optional[List[Dict[str, Any]]] = None,  # Enhanced data
        market_interpretations: Optional[List[Union[str, Dict[str, Any]]]] = None,  # Enhanced data
        actionable_insights: Optional[List[str]] = None,  # Enhanced data
        top_weighted_subcomponents: Optional[List[Dict[str, Any]]] = None,  # Top weighted sub-components
        signal_type: Optional[str] = None,  # Add explicit signal_type parameter
        pdf_path: Optional[str] = None,  # Path to PDF report
        chart_path: Optional[str] = None,  # Path to chart image
        ohlcv_data: Optional[Any] = None  # OHLCV data for chart generation
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
            long_threshold: Threshold for long signals
            short_threshold: Threshold for short signals
            price: Current price
            transaction_id: Transaction ID for cross-component tracking
            signal_id: Signal ID for tracking within SignalGenerator
            influential_components: List of top influential components with metadata
            market_interpretations: List of market interpretations
            actionable_insights: List of actionable trading insights
            top_weighted_subcomponents: List of sub-components with highest weighted impact
            signal_type: Explicit signal type (LONG, SHORT, NEUTRAL) from caller
        """
        # Use provided transaction_id or generate a new one
        txn_id = transaction_id or str(uuid.uuid4())[:8]
        # Use provided signal_id or generate a new one
        sig_id = signal_id or str(uuid.uuid4())[:8]
        
        # IMPROVED THROTTLING: Generate alert key for throttling
        # Key includes symbol and signal type (LONG/SHORT/NEUTRAL)
        alert_key = f"{symbol}_{signal_type or 'confluence'}_alert"
        # Use rounded score for deduplication - prevents duplicates from tiny score fluctuations
        # Note: Previously used str(components) which caused duplicates when sub-scores changed slightly
        content_for_dedup = f"{symbol}_{signal_type}_{int(confluence_score)}"

        # Check improved throttling
        if not self._check_improved_throttling(alert_key, 'confluence', content_for_dedup):
            self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}] Confluence alert for {symbol} throttled")
            return
        
        # Generate a unique alert ID
        alert_id = str(uuid.uuid4())[:8]
        
        # CALL SOURCE TRACKING: Log alert processing (extract from results if available)
        call_source = results.get('call_source', 'UNKNOWN_SOURCE') if isinstance(results, dict) else 'UNKNOWN_SOURCE'
        call_id = results.get('call_id', 'UNKNOWN_CALL') if isinstance(results, dict) else 'UNKNOWN_CALL'
        cycle_call_source = results.get('cycle_call_source', 'UNKNOWN_CYCLE') if isinstance(results, dict) else 'UNKNOWN_CYCLE'
        cycle_call_id = results.get('cycle_call_id', 'UNKNOWN_CYCLE_CALL') if isinstance(results, dict) else 'UNKNOWN_CYCLE_CALL'
        
        self.logger.info(f"[CALL_TRACKING][ALERT_MGR][{call_source}→{cycle_call_source}][CALL_ID:{call_id}→{cycle_call_id}][TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Processing confluence alert for {symbol}")
        self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Starting confluence alert for {symbol}")
        
        try:
            # Log all parameters for debugging
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Parameters for {symbol}:")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Score: {confluence_score}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Component count: {len(components)}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Results count: {len(results)}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Reliability: {reliability}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Thresholds: long={long_threshold}, short={short_threshold}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Price: {price}")
            if signal_type:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Explicit signal type: {signal_type}")
            
            # Debug log the enhanced data structures
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Market Interpretations: {market_interpretations}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Influential Components: {influential_components}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Top Weighted Subcomponents: {top_weighted_subcomponents}")
            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] - Actionable Insights: {actionable_insights}")

            # Use thresholds from constructor if not provided
            if long_threshold is None:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using default long threshold: {self.long_threshold}")
                long_threshold = self.long_threshold
            if short_threshold is None:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using default short threshold: {self.short_threshold}")
                short_threshold = self.short_threshold
                
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
            
            # Only skip alerts for signals with very low reliability (< 30%)
            # This allows most valid signals through while filtering out unreliable ones
            if reliability < 0.3:
                self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Skipping alert for {symbol} due to low reliability {reliability*100:.1f}% < 30%")
                return
                
            # Use explicit signal_type if provided, otherwise determine based on score and thresholds
            if not signal_type:
                if confluence_score >= long_threshold:
                    signal_type = "LONG"
                elif confluence_score <= short_threshold:
                    signal_type = "SHORT"
                else:
                    signal_type = "NEUTRAL"
                
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Determined signal type by thresholds: {signal_type}")
            else:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Using provided signal type: {signal_type}")
            
            # Set emoji and color based on the signal type
            if signal_type == "LONG":
                emoji = "🟢"
                color = 0x00ff00  # Green
            elif signal_type == "SHORT":
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
                overall_gauge = self._add_threshold_markers(overall_gauge, long_threshold, short_threshold)
                
                # Get overall emoji based on signal
                if signal_type == "LONG":
                    overall_emoji = "🚀"
                elif signal_type == "SHORT":
                    overall_emoji = "📉"
                else:
                    overall_emoji = "⚖️"
                
                description += f"`{'IMPACT':10}` {overall_gauge} `{confluence_score:>5.1f}`% {overall_emoji}\n"
            
            # Save component data as JSON for future reference
            json_path = self._save_component_data(symbol, components, results, signal_type)
            
            # Note: PDF generation is handled by Monitor.py -> send_signal_alert() workflow
            # Disable internal PDF generation to avoid conflicts with the main PDF generation path
            pdf_path = None
            if False:  # Disabled to prevent dual PDF generation
                try:
                    self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] 🔧 Generating PDF for {symbol} {signal_type} signal...")
                    
                    # Prepare report data for PDF generation
                    report_data = {
                        'symbol': symbol,
                        'signal_type': signal_type,
                        'confluence_score': confluence_score,
                        'components': components,
                        'results': results,
                        'price': price,
                        'reliability': reliability,
                        'transaction_id': txn_id,
                        'long_threshold': long_threshold,
                        'short_threshold': short_threshold,
                        'weights': weights or {},
                        'timestamp': datetime.now().isoformat(),
                        'market_interpretations': market_interpretations,
                        'actionable_insights': actionable_insights,
                        'influential_components': influential_components,
                        'top_weighted_subcomponents': top_weighted_subcomponents
                    }
                    
                    # Generate PDF using the report generator
                    pdf_result = await self.pdf_generator.generate_report(
                        signal_data=report_data,
                        ohlcv_data=ohlcv_data,
                        output_path=f"reports/pdf/{symbol.lower()}_{signal_type.lower()}_{confluence_score:.1f}p{int(confluence_score*10)%10}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                    
                    if pdf_result and pdf_result != False:
                        # pdf_result is a tuple (pdf_path, json_path) if successful
                        if isinstance(pdf_result, tuple) and len(pdf_result) >= 1:
                            pdf_path = pdf_result[0]
                            self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] ✅ PDF generated successfully: {pdf_path}")
                        else:
                            pdf_path = pdf_result
                            self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] ✅ PDF generated successfully: {pdf_path}")
                    else:
                        self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] ❌ PDF generation failed: No result returned")
                        
                except Exception as pdf_error:
                    self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] ❌ PDF generation error: {str(pdf_error)}")
                    self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] PDF error traceback: {traceback.format_exc()}")
            else:
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] PDF generation disabled (enabled: {self.pdf_enabled})")
            
            # Add interpretations if available
            if results or market_interpretations:
                # Process detailed interpretations from results
                self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Processing detailed interpretations from results")
                
                # Process market interpretations using centralized InterpretationManager
                if market_interpretations and isinstance(market_interpretations, list) and len(market_interpretations) > 0:
                    try:
                        self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Processing {len(market_interpretations)} interpretations with InterpretationManager")
                        
                        # Use InterpretationManager to process and standardize interpretations
                        interpretation_set = self.interpretation_manager.process_interpretations(
                            market_interpretations, 
                            f"alert_{symbol}",
                            market_data=None,  # No market data available at this point
                            timestamp=datetime.now()
                        )
                        
                        # Format interpretations for Discord alert
                        formatted_for_alert = self.interpretation_manager.get_formatted_interpretation(
                            interpretation_set, 'alert'
                        )
                        
                        description += "\n**MARKET INTERPRETATIONS:**\n"
                        
                        # Add each standardized interpretation
                        for interpretation in interpretation_set.interpretations[:3]:  # Limit to top 3
                            # Extract the proper component name with proper display mapping
                            # Map component types to proper display names
                            component_type_display_map = {
                                'technical_indicator': 'Technical',
                                'volume_analysis': 'Volume',
                                'sentiment_analysis': 'Sentiment',
                                'price_analysis': 'Price Structure',
                                'funding_analysis': 'Funding',
                                'whale_analysis': 'Whale Activity',
                                'general_analysis': 'General Analysis',
                                'unknown': 'Unknown'
                            }
                            
                            # Special handling for orderbook and orderflow components
                            if 'orderbook' in interpretation.component_name.lower():
                                component_name = 'Orderbook'
                            elif 'orderflow' in interpretation.component_name.lower():
                                component_name = 'Orderflow'
                            else:
                                # Use component type mapping for proper display names
                                component_type_value = interpretation.component_type.value
                                component_name = component_type_display_map.get(component_type_value, 
                                                                             interpretation.component_name.replace('_', ' ').title())
                                
                                # Safeguard against typos and ensure proper text
                                if component_name in ['Genral Analyis', 'Genral Analysis']:
                                    component_name = 'General Analysis'
                            
                            interp_text = interpretation.interpretation_text
                            severity_indicator = "🔴" if interpretation.severity.value == "critical" else "🟡" if interpretation.severity.value == "warning" else "🟢"
                            
                            description += f"• {severity_indicator} **{component_name}**: {interp_text}\n"
                            self.logger.debug(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Added standardized interpretation for {component_name}")
                        
                    except Exception as e:
                        self.logger.error(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Error processing interpretations with InterpretationManager: {e}")
                        # Fallback to original processing
                        description += "\n**MARKET INTERPRETATIONS:**\n"
                        for interp_obj in market_interpretations[:3]:
                            if isinstance(interp_obj, dict):
                                component = interp_obj.get('display_name', interp_obj.get('component', 'Unknown'))
                                interp_text = interp_obj.get('interpretation', 'No interpretation available')
                                description += f"• **{component}**: {interp_text}\n"
                            else:
                                description += f"• {interp_obj}\n"
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
                
                # Sort by weighted_impact to ensure we show the most impactful ones first
                subcomps_to_display.sort(key=lambda x: x.get('weighted_impact', 0), reverse=True)
                
                for i, sub_comp in enumerate(subcomps_to_display[:3]):  # Always limit to top 3
                    sub_name = sub_comp.get('display_name', 'Unknown')
                    parent_name = sub_comp.get('parent_display_name', 'Unknown')
                    raw_score = sub_comp.get('score', 0)
                    # Use weighted_impact directly as it's already a percentage value (e.g., 16.67 means 16.67%)
                    impact = sub_comp.get('weighted_impact', 0)
                    indicator = sub_comp.get('indicator', '•')
                    
                    # Build gauge for sub-component
                    sub_gauge = self._build_gauge(raw_score, width=10)
                    
                    # Determine strength description based on impact
                    if impact > 15:
                        strength_desc = "🔥 **MAJOR**"
                    elif impact > 10:
                        strength_desc = "⚡ **HIGH**"
                    elif impact > 5:
                        strength_desc = "📊 **MODERATE**"
                    else:
                        strength_desc = "📉 **LOW**"
                    
                    # Add formatted sub-component with impact percentage and strength indicator
                    description += f"{i+1}. {strength_desc} **{sub_name}** `{raw_score:.1f}` {indicator} ({parent_name}) - Impact: `{impact:.1f}%` {sub_gauge}\n"
                
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
                    
                    if response and response.status_code in [200, 204]:
                        self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Successfully sent confluence alert for {symbol} (status: {response.status_code})")

                        # IMPROVED THROTTLING: Mark alert as sent
                        self._mark_alert_sent_improved(alert_key, 'confluence', content_for_dedup)

                        # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
                        await self._store_and_cache_alert_direct(
                            alert_type='confluence',
                            symbol=symbol,
                            message=title,
                            level='WARNING' if signal_type in ['LONG', 'SHORT'] else 'INFO',
                            details={
                                'confluence_score': confluence_score,
                                'signal_type': signal_type,
                                'price': price,  # Fixed: was 'current_price' which was undefined
                                'reliability': reliability,
                                'components': components,
                                'transaction_id': txn_id,
                                'signal_id': sig_id
                            }
                        )

                        # Note: PDF attachment is handled by send_signal_alert() workflow
                        # Skip PDF attachment here to avoid duplicate PDF messages
                        if pdf_path and os.path.exists(pdf_path):
                            self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] 📎 PDF attachment will be handled by send_signal_alert() workflow")

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
                    logger.error(f"Unhandled exception: {e}", exc_info=True)
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
            if not response or response.status_code not in [200, 204]:
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
                            if resp.status in [200, 204]:
                                self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] Successfully sent alert using fallback method (status: {resp.status})")
                                
                                # Note: PDF attachment is handled by send_signal_alert() workflow
                                # Skip PDF attachment here to avoid duplicate PDF messages
                                if pdf_path and os.path.exists(pdf_path):
                                    self.logger.info(f"[TXN:{txn_id}][SIG:{sig_id}][ALERT:{alert_id}] 📎 PDF attachment will be handled by send_signal_alert() workflow (fallback)")
                                
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
            if (response and response.status_code in [200, 204]):
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
            else:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
                self.logger.error(f"Failed to send confluence alert for {symbol}")
            
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
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

    def _add_threshold_markers(self, gauge_line: str, long_threshold: float, short_threshold: float, width: int = 15) -> str:
        """Add buy and sell threshold markers to a gauge line using Discord-compatible characters.
        
        Args:
            gauge_line: The gauge line to add the markers to
            long_threshold: The long threshold (0-100)
            short_threshold: The short threshold (0-100)
            width: The width of the gauge
            
        Returns:
            The gauge line with threshold markers added
        """
        # Calculate positions in gauge
        long_pos = min(width - 1, max(0, int(round(long_threshold / 100 * width))))
        short_pos = min(width - 1, max(0, int(round(short_threshold / 100 * width))))
        
        # Create threshold indicator lines
        threshold_line = ' ' * width
        threshold_chars = list(threshold_line)
        
        # Add long and short markers
        if 0 <= long_pos < width:
            threshold_chars[long_pos] = '↑'  # Up arrow for long threshold

        if 0 <= short_pos < width and short_pos != long_pos:
            threshold_chars[short_pos] = '↓'  # Down arrow for short threshold
            
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

    def _determine_impact_level(self, usd_value: float) -> str:
        """Determine impact level based on USD value.
        
        Args:
            usd_value: USD value of the liquidation
            
        Returns:
            Impact level string
        """
        if usd_value >= 1000000:  # $1M+
            return "CRITICAL"
        elif usd_value >= 500000:  # $500K+
            return "HIGH"
        elif usd_value >= 250000:  # $250K+
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_impact_bar(self, usd_value: float) -> str:
        """Generate visual impact bar for liquidation.
        
        Args:
            usd_value: USD value of the liquidation
            
        Returns:
            Visual impact bar string
        """
        # Normalize to 0-10 scale based on threshold multiples
        normalized = min(int(usd_value / self.liquidation_threshold * 5), 10)
        filled = "█" * normalized
        empty = "░" * (10 - normalized)
        return f"{filled}{empty}"
    
    def _get_price_action_note(self, position_type: str, impact_level: str) -> str:
        """Get price action note based on position type and impact.
        
        Args:
            position_type: LONG or SHORT position type
            impact_level: Impact level of the liquidation
            
        Returns:
            Price action note string
        """
        if position_type == "LONG":
            if impact_level in ["CRITICAL", "HIGH"]:
                return "Expect immediate downward price pressure as liquidated longs are sold"
            else:
                return "Minor selling pressure expected from liquidated long positions"
        else:  # SHORT
            if impact_level in ["CRITICAL", "HIGH"]:
                return "Expect immediate upward price pressure as liquidated shorts are bought"
            else:
                return "Minor buying pressure expected from liquidated short positions"

    # ========== IMPROVED THROTTLING METHODS FROM REFACTORED VERSION ==========
    def _init_improved_throttling(self):
        """Initialize improved throttling system from refactored version"""
        # Cooldown periods for different alert types (seconds)
        self.throttle_cooldowns = {
            'system': 60,          # System alerts - 1 minute
            'signal': 300,         # Trading signals - 5 minutes  
            'whale': 180,          # Whale alerts - 3 minutes
            'liquidation': 120,    # Liquidation alerts - 2 minutes
            'confluence': 300,     # Confluence alerts - 5 minutes
            'default': 60          # Default cooldown
        }
        
        # Deduplication window (seconds)
        self.throttle_dedup_window = 300  # 5 minutes
        
        # Maximum entries to prevent memory growth
        self.max_throttle_entries = 10000
        
        # Storage for tracking sent alerts
        self._throttle_sent_alerts = {}      # alert_key -> timestamp
        self._throttle_content_hashes = {}   # hash -> timestamp
        self._throttle_alert_counts = defaultdict(int)  # alert_type -> count
        
        # Cleanup tracking
        self._throttle_last_cleanup = time.time()
        self._throttle_cleanup_interval = 3600  # 1 hour
        
        self.logger.info("Improved throttling system initialized")
    
    def _check_improved_throttling(self, alert_key: str, alert_type: str = 'default', 
                                  content: Optional[str] = None) -> bool:
        """
        Enhanced throttling check with content deduplication.
        Returns True if alert should be sent, False if throttled.
        """
        current_time = time.time()
        
        # Get cooldown period for this alert type
        cooldown = self.throttle_cooldowns.get(alert_type, self.throttle_cooldowns['default'])
        
        # Check if alert was recently sent
        if alert_key in self._throttle_sent_alerts:
            time_since_last = current_time - self._throttle_sent_alerts[alert_key]
            if time_since_last < cooldown:
                self.logger.debug(f"Alert {alert_key} throttled: {time_since_last:.1f}s < {cooldown}s cooldown")
                return False
        
        # Check for duplicate content
        if content:
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in self._throttle_content_hashes:
                time_since_duplicate = current_time - self._throttle_content_hashes[content_hash]
                if time_since_duplicate < self.throttle_dedup_window:
                    self.logger.debug(f"Alert throttled as duplicate content (seen {time_since_duplicate:.1f}s ago)")
                    return False
        
        # Periodic cleanup to prevent memory growth
        if current_time - self._throttle_last_cleanup > self._throttle_cleanup_interval:
            self._cleanup_throttle_entries()
        
        return True
    
    def _mark_alert_sent_improved(self, alert_key: str, alert_type: str = 'default', 
                                 content: Optional[str] = None):
        """Record alert as sent for future throttling decisions"""
        current_time = time.time()
        
        # Track by key
        self._throttle_sent_alerts[alert_key] = current_time
        
        # Track by content hash
        if content:
            content_hash = hashlib.md5(content.encode()).hexdigest()
            self._throttle_content_hashes[content_hash] = current_time
        
        # Update counts
        self._throttle_alert_counts[alert_type] += 1
        
        # Enforce max entries limit
        if len(self._throttle_sent_alerts) > self.max_throttle_entries:
            self._cleanup_throttle_entries()
    
    def _cleanup_throttle_entries(self):
        """Remove expired entries to prevent memory growth"""
        current_time = time.time()
        
        # Clean up sent alerts
        expired_keys = [
            key for key, timestamp in self._throttle_sent_alerts.items()
            if current_time - timestamp > max(self.throttle_cooldowns.values())
        ]
        for key in expired_keys:
            del self._throttle_sent_alerts[key]
        
        # Clean up content hashes
        expired_hashes = [
            h for h, timestamp in self._throttle_content_hashes.items()
            if current_time - timestamp > self.throttle_dedup_window
        ]
        for h in expired_hashes:
            del self._throttle_content_hashes[h]
        
        self._throttle_last_cleanup = current_time
        
        if expired_keys or expired_hashes:
            self.logger.debug(f"Cleaned up {len(expired_keys)} alert keys and {len(expired_hashes)} content hashes")

    def _validate_alert_config(self) -> None:
        """Validate the alert configuration.
        
        Ensures that all required alert configurations are set properly.
        """
        try:
            # Validate thresholds
            if self.long_threshold <= self.short_threshold:
                self.logger.warning(f"Invalid threshold configuration: long_threshold ({self.long_threshold}) must be > short_threshold ({self.short_threshold})")
                
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
                if webhook_url and self._validate_discord_webhook_url(webhook_url):
                    self.logger.debug(f"Initializing Discord webhook with URL: {webhook_url[:20]}...{webhook_url[-10:]}")
                    self.webhook = DiscordWebhook(url=webhook_url)
                    self.logger.info("Discord webhook initialized successfully")
                else:
                    self.logger.error("Discord webhook URL validation failed")
            else:
                self.logger.warning("No Discord webhook URL configured")
                
        except Exception as e:
            self.logger.error(f"Error initializing Discord webhook: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _validate_discord_webhook_url(self, url: str) -> bool:
        """Validate Discord webhook URL format.
        
        Args:
            url: Discord webhook URL to validate
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        if not url or not isinstance(url, str):
            self.logger.error("Discord webhook URL is empty or not a string")
            return False
        
        url = url.strip()
        if not url:
            self.logger.error("Discord webhook URL is empty after stripping")
            return False
        
        # Check if URL starts with Discord webhook pattern
        if not url.startswith('https://discord.com/api/webhooks/') and not url.startswith('https://discordapp.com/api/webhooks/'):
            self.logger.error(f"Discord webhook URL does not match expected pattern. URL starts with: {url[:50]}...")
            return False
        
        # Check if URL has the required parts (webhook ID and token)
        parts = url.split('/')
        if len(parts) < 7:  # https://discord.com/api/webhooks/ID/TOKEN
            self.logger.error("Discord webhook URL is missing required components (ID/TOKEN)")
            return False
        
        webhook_id = parts[5] if len(parts) > 5 else ""
        webhook_token = parts[6] if len(parts) > 6 else ""
        
        if not webhook_id or not webhook_token:
            self.logger.error("Discord webhook URL is missing webhook ID or token")
            return False
        
        # Basic format validation
        if not webhook_id.isdigit():
            self.logger.error("Discord webhook ID should be numeric")
            return False
        
        if len(webhook_token) < 10:  # Tokens are typically much longer
            self.logger.error("Discord webhook token appears to be too short")
            return False
        
        self.logger.debug(f"Discord webhook URL validation passed for ID: {webhook_id}")
        return True
    
    async def _send_discord_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to Discord webhook with retry logic and fallback mechanism.
        
        Args:
            alert: Alert data
        """
        # Create unique ID for tracking this alert
        alert_id = str(uuid.uuid4())[:8]

        try:
            # Extract alert data first to determine type for routing
            level = alert.get('level', 'INFO')
            details = alert.get('details', {})
            alert_type = details.get('type', 'general')

            # Use centralized routing (supports dev mode override)
            webhook_url, webhook_type = self._get_webhook_url(alert_type)
            if not webhook_url:
                self.logger.warning(f"[ALERT:{alert_id}] Cannot send Discord alert: no webhook URL configured")
                return

            # Extract remaining alert data
            level = alert.get('level', 'INFO')
            message = alert.get('message', 'No message provided')
            details = alert.get('details', {})
            timestamp = alert.get('timestamp', time.time())
            
            # Check if this is a whale_activity alert and handle specially
            if details.get('type') == 'whale_activity':
                await self._send_whale_activity_discord_alert(alert, alert_id)
                return

            # Check if this is a whale_trade alert and route to dedicated webhook if configured
            if details.get('type') == 'whale_trade':
                await self._send_whale_trade_discord_alert(alert, alert_id)
                return

            # Check if this is a smart_money alert and handle specially
            if details.get('type') == 'smart_money':
                await self._send_smart_money_discord_alert(alert, alert_id)
                return
            
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

            # Override color for specific alert types
            alert_type = details.get('type', '')
            if alert_type == 'health_recovery':
                color = 0x2ecc71  # Green for recovery/success
            
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
            
            # Create webhook and add embed with enhanced error handling
            try:
                self.logger.debug(f"[ALERT:{alert_id}] Routing to {webhook_type} webhook")
                webhook = DiscordWebhook(url=webhook_url)
                webhook.add_embed(embed)
                self.logger.debug(f"[ALERT:{alert_id}] Created Discord webhook with embed")
            except Exception as webhook_err:
                self.logger.error(f"[ALERT:{alert_id}] Failed to create Discord webhook: {type(webhook_err).__name__}: {str(webhook_err)}")
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
                return

            # Retry logic with exponential backoff
            max_retries = self.webhook_max_retries
            retry_delay = self.webhook_initial_retry_delay
            response = None

            # Enhanced debugging for webhook configuration
            self.logger.debug(f"[ALERT:{alert_id}] Webhook configured: {bool(webhook_url)} (type: {webhook_type})")

            self.logger.debug(f"[ALERT:{alert_id}] Attempting to send Discord alert to {webhook_type} webhook (max {max_retries} retries)")

            # Validate webhook URL format (use the routed URL)
            if not self._validate_discord_webhook_url(webhook_url):
                self.logger.error(f"[ALERT:{alert_id}] Discord webhook URL format validation failed for {webhook_type}")
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
                return
            
            for attempt in range(max_retries):
                try:
                    # Attempt to send the webhook
                    self.logger.debug(f"[ALERT:{alert_id}] Executing webhook on attempt {attempt + 1}")
                    response = webhook.execute()
                    
                    # Enhanced response checking
                    self.logger.debug(f"[ALERT:{alert_id}] Webhook response type: {type(response)}")
                    if response:
                        self.logger.debug(f"[ALERT:{alert_id}] Response attributes: {dir(response)}")
                    
                    # Check if successful
                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"[ALERT:{alert_id}] Discord alert sent successfully on attempt {attempt + 1} (status: {response.status_code})")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        return
                    else:
                        status_code = response.status_code if response and hasattr(response, 'status_code') else "N/A"
                        self.logger.warning(f"[ALERT:{alert_id}] Failed to send alert (attempt {attempt+1}/{max_retries}): Status code {status_code}")
                        
                        # Enhanced response logging
                        if response:
                            if hasattr(response, 'text'):
                                self.logger.debug(f"[ALERT:{alert_id}] Response text: {response.text[:500]}")
                            if hasattr(response, 'content'):
                                self.logger.debug(f"[ALERT:{alert_id}] Response content: {str(response.content)[:500]}")
                            if hasattr(response, 'reason'):
                                self.logger.debug(f"[ALERT:{alert_id}] Response reason: {response.reason}")
                        
                        # Check for recoverable status codes
                        if (response and hasattr(response, 'status_code') and 
                            response.status_code in self.webhook_recoverable_status_codes):
                            if attempt < max_retries - 1:
                                self.logger.info(f"[ALERT:{alert_id}] Recoverable error, retrying after {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                if self.webhook_exponential_backoff:
                                    retry_delay *= 2  # Exponential backoff
                                continue
                            
                except (requests.exceptions.ConnectionError, 
                        requests.exceptions.Timeout,
                        requests.exceptions.HTTPError) as req_err:
                    # Handle requests library errors (including RemoteDisconnected)
                    self.logger.error(f"[ALERT:{alert_id}] Network error sending alert (attempt {attempt+1}/{max_retries}): {type(req_err).__name__}: {str(req_err)}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"[ALERT:{alert_id}] Retrying after {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        if self.webhook_exponential_backoff:
                            retry_delay *= 2
                        continue
                    
                except Exception as e:
                    logger.error(f"Unhandled exception: {e}", exc_info=True)
                    # Handle other unexpected errors with full traceback
                    self.logger.error(f"[ALERT:{alert_id}] Unexpected error sending alert (attempt {attempt+1}/{max_retries}): {type(e).__name__}: {str(e)}")
                    self.logger.error(f"[ALERT:{alert_id}] Traceback: {traceback.format_exc()}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        if self.webhook_exponential_backoff:
                            retry_delay *= 2
                        continue
                    else:
                        # Final attempt failed
                        self.logger.error(f"[ALERT:{alert_id}] All attempts failed, trying fallback method...")
                        break
            
            # Fallback mechanism using direct HTTP request
            if self.webhook_fallback_enabled and (not response or 
                (hasattr(response, 'status_code') and response.status_code not in range(200, 300))):
                
                self.logger.info(f"[ALERT:{alert_id}] Attempting fallback using direct HTTP request...")
                
                try:
                    # Create simplified payload for fallback
                    fallback_data = {
                        'content': f"**{level} Alert** - {message}",
                        'embeds': [{
                            'title': f"{level} Alert",
                            'description': message[:2000],  # Truncate to avoid length issues
                            'color': color,
                            'timestamp': dt.isoformat(),
                            'fields': [
                                {
                                    'name': key[:256],  # Discord field name limit
                                    'value': str(value)[:1024],  # Discord field value limit
                                    'inline': True
                                }
                                for key, value in list(details.items())[:10]  # Limit to 10 fields
                            ] if details else []
                        }]
                    }
                    
                    # Use aiohttp for direct request
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.webhook_timeout)) as session:
                        async with session.post(
                            self.discord_webhook_url,
                            json=fallback_data,
                            headers={'Content-Type': 'application/json'}
                        ) as resp:
                            if resp.status in range(200, 300):
                                self.logger.info(f"[ALERT:{alert_id}] Successfully sent alert using fallback method")
                                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                                return
                            else:
                                response_text = await resp.text()
                                self.logger.error(f"[ALERT:{alert_id}] Fallback method failed: {resp.status} - {response_text[:200]}")
                                
                except Exception as fallback_err:
                    self.logger.error(f"[ALERT:{alert_id}] Fallback method error: {str(fallback_err)}")
            
            # If we reach here, all attempts failed
            self.logger.error(f"[ALERT:{alert_id}] Failed to send Discord alert after all retry attempts and fallback")
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
                
        except Exception as e:
            self.logger.error(f"[ALERT:{alert_id}] Error in _send_discord_alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

    async def send_report(self, report: str, title: Optional[str] = None, files: Optional[List[str]] = None) -> bool:
        """Send a periodic market report via configured channels.

        Args:
            report: Plain-text report content
            title: Optional report title
            files: Optional list of file paths to attach (e.g., PDFs)

        Returns:
            True if at least one message was delivered successfully, else False
        """
        try:
            if not isinstance(report, str) or not report.strip():
                self.logger.warning("send_report called with empty report content")
                return False

            # Default title
            report_title = title or "\ud83d\udcca Virtuoso Market Report"

            # Discord content limit is ~2000 chars; keep margin for fencing and header
            max_chunk = 1800
            chunks: List[str] = []
            content = report.strip()
            while content:
                chunks.append(content[:max_chunk])
                content = content[max_chunk:]

            any_success = False
            for idx, chunk in enumerate(chunks):
                heading = report_title if idx == 0 else f"{report_title} (cont. {idx})"
                message: Dict[str, Any] = {
                    "content": f"**{heading}**\n```\n{chunk}\n```",
                    "username": "Virtuoso Monitoring",
                }

                attach_files = files if (idx == 0 and files) else None
                ok, _resp = await self.send_discord_webhook_message(message, files=attach_files, alert_type='market_report')
                any_success = any_success or ok

            if not any_success:
                self.logger.error("send_report: failed to deliver report via Discord webhook")
            else:
                self.logger.info("send_report: report delivered successfully")

            return any_success

        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            self.logger.error(f"send_report error: {type(e).__name__}: {str(e)}")
            return False

    async def send_discord_webhook_message(self, message: Dict[str, Any], files: List[str] = None, alert_type: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Send message to Discord webhook with enhanced error handling and logging.
        
        Args:
            message: Discord webhook message data
            files: Optional list of file paths to attach
            alert_type: Optional alert type for routing (e.g., 'market_report')
            
        Returns:
            Tuple of (success: bool, response_data: Optional[Dict])
        """
        delivery_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._delivery_stats['total_attempts'] += 1
        
        try:
            self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Starting Discord webhook delivery (type: {alert_type or 'general'})")
            
            # Validate files before processing
            validated_files = []
            if files:
                validated_files = self._validate_attachment_files(files, delivery_id)
                if files and not validated_files:
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] All file attachments failed validation")
                    self._delivery_stats['file_attachment_failures'] += 1
            # Determine which webhook URL to use based on alert type and configuration
            webhook_url = self.discord_webhook_url  # Default to main webhook
            
            # Check if this should be routed to system webhook based on alert type
            if alert_type:
                system_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('system_alerts', {})
                use_system_webhook = system_alerts_config.get('use_system_webhook', False)
                types_config = system_alerts_config.get('types', {})
                
                # Check if mirroring is enabled for this alert type
                mirror_config = system_alerts_config.get('mirror_alerts', {})
                should_mirror = mirror_config.get('enabled', False) and mirror_config.get('types', {}).get(alert_type, False)
                
                if should_mirror and self.system_webhook_url:
                    # Mirror to system webhook and continue to main webhook
                    self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Mirroring {alert_type} Discord message to system webhook")
                    
                    # Create system webhook payload
                    content = message.get('content', '')
                    details = {
                        'type': alert_type,
                        'discord_message': message,  # Include original message for reference
                        'report_time': datetime.now(timezone.utc).isoformat()
                    }
                    
                    await self._send_system_webhook_alert(content, details)
                    # Continue to send to main webhook below
                    
                elif use_system_webhook and types_config.get(alert_type, False) and self.system_webhook_url:
                    # Send only to system webhook (no mirroring)
                    webhook_url = self.system_webhook_url
                    self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Routing {alert_type} Discord message to system webhook only")
                    
                    # For system webhook, we need to convert the rich Discord message to system webhook format
                    # Extract the main content and create a system alert
                    content = message.get('content', '')
                    
                    # Create system webhook payload
                    details = {
                        'type': alert_type,
                        'discord_message': message,  # Include original message for reference
                        'report_time': datetime.now(timezone.utc).isoformat()
                    }
                    
                    await self._send_system_webhook_alert(content, details)
                    delivery_time = time.time() - start_time
                    self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] System webhook delivery completed in {delivery_time:.2f}s")
                    self._delivery_stats['successful_deliveries'] += 1
                    return True, {'status': 'sent_to_system_webhook'}
            
            # Send to Discord webhook (original logic)
            if not webhook_url:
                self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] No Discord webhook URL configured")
                self._delivery_stats['failed_deliveries'] += 1
                return False, {'error': 'no_webhook_url'}
                
            webhook_url = webhook_url.strip()
            
            if not webhook_url:
                self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Discord webhook URL is empty after stripping")
                self._delivery_stats['failed_deliveries'] += 1
                return False, {'error': 'empty_webhook_url'}
            
            # Create webhook
            self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Creating Discord webhook for URL: {webhook_url[:50]}...")
            webhook = DiscordWebhook(url=webhook_url)
            
            # Add content if provided
            if 'content' in message and message['content']:
                webhook.content = message['content']
                self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Added content ({len(message['content'])} chars)")
            
            # Add username if provided
            if 'username' in message and message['username']:
                webhook.username = message['username']
                self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Added username: {message['username']}")
            
            # Add avatar URL if provided
            if 'avatar_url' in message and message['avatar_url']:
                webhook.avatar_url = message['avatar_url']
                self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Added avatar URL")
            
            # Add embeds if provided
            embed_count = 0
            if 'embeds' in message and isinstance(message['embeds'], list):
                for embed_data in message['embeds']:
                    if isinstance(embed_data, dict):
                        try:
                            embed = DiscordEmbed()
                            
                            # Set basic embed properties
                            if 'title' in embed_data:
                                embed.set_title(embed_data['title'])
                            if 'description' in embed_data:
                                embed.set_description(embed_data['description'])
                            if 'color' in embed_data:
                                embed.set_color(embed_data['color'])
                            if 'url' in embed_data:
                                embed.set_url(embed_data['url'])
                            
                            # Set author if provided
                            if 'author' in embed_data and isinstance(embed_data['author'], dict):
                                author = embed_data['author']
                                embed.set_author(
                                    name=author.get('name', ''),
                                    url=author.get('url', ''),
                                    icon_url=author.get('icon_url', '')
                                )
                            
                            # Set footer if provided
                            if 'footer' in embed_data and isinstance(embed_data['footer'], dict):
                                footer = embed_data['footer']
                                embed.set_footer(
                                    text=footer.get('text', ''),
                                    icon_url=footer.get('icon_url', '')
                                )
                            
                            # Set thumbnail if provided
                            if 'thumbnail' in embed_data and isinstance(embed_data['thumbnail'], dict):
                                embed.set_thumbnail(url=embed_data['thumbnail'].get('url', ''))
                            
                            # Set image if provided
                            if 'image' in embed_data and isinstance(embed_data['image'], dict):
                                embed.set_image(url=embed_data['image'].get('url', ''))
                            
                            # Set timestamp if provided
                            if 'timestamp' in embed_data:
                                embed.set_timestamp(embed_data['timestamp'])
                            
                            # Add fields if provided
                            if 'fields' in embed_data and isinstance(embed_data['fields'], list):
                                for field in embed_data['fields']:
                                    if isinstance(field, dict) and 'name' in field and 'value' in field:
                                        embed.add_embed_field(
                                            name=field['name'],
                                            value=field['value'],
                                            inline=field.get('inline', False)
                                        )
                            
                            webhook.add_embed(embed)
                            embed_count += 1
                            
                        except Exception as e:
                            self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Failed to process embed {embed_count}: {str(e)}")
                            
            if embed_count > 0:
                self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Added {embed_count} embeds")
            
            # Add files if provided
            file_count = 0
            if validated_files:
                self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Processing {len(validated_files)} file attachments")
                
                for file_info in validated_files:
                    try:
                        file_path = file_info['path']
                        filename = file_info['filename']
                        file_size = file_info['size']
                        
                        self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Attaching file: {filename} ({file_size / 1024:.1f} KB)")
                        
                        # Clean filename to prevent null byte errors
                        clean_filename = filename.replace('\x00', '').strip()
                        if not clean_filename:
                            clean_filename = f"attachment_{file_count}.pdf"
                        
                        # Ensure filename is properly encoded
                        try:
                            clean_filename = clean_filename.encode('ascii', 'ignore').decode('ascii')
                        except Exception:
                            logger.error(f"Unhandled exception: {e}", exc_info=True)
                            clean_filename = f"attachment_{file_count}.pdf"
                        
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                            # Verify file content is not empty and is valid
                            if len(file_content) == 0:
                                self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] File is empty: {filename}")
                                continue
                            
                            # Use discord_webhook's add_file method directly with bytes and filename
                            webhook.add_file(file=file_content, filename=clean_filename)
                            file_count += 1
                            self._delivery_stats['file_attachments'] += 1
                            
                    except Exception as e:
                        self.logger.error(f"[WEBHOOK_DELIVERY:{delivery_id}] Failed to attach file {file_info.get('filename', 'unknown')}: {str(e)}")
                        self._delivery_stats['file_attachment_failures'] += 1
                        
            if file_count > 0:
                self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Successfully attached {file_count} files")
            
            # Send webhook with retry logic
            max_retries = self.webhook_max_retries
            retry_delay = self.webhook_initial_retry_delay
            response = None
            last_error = None
            
            self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Sending webhook message (max retries: {max_retries})")
            
            for attempt in range(max_retries):
                try:
                    attempt_start = time.time()
                    self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Attempt {attempt + 1}/{max_retries}")
                    
                    response = webhook.execute()
                    attempt_time = time.time() - attempt_start
                    
                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        delivery_time = time.time() - start_time
                        webhook_type = 'system webhook' if webhook_url == self.system_webhook_url else 'Discord webhook'
                        
                        self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] {webhook_type} message sent successfully in {delivery_time:.2f}s (attempt {attempt + 1})")
                        self._delivery_stats['successful_deliveries'] += 1
                        
                        if attempt > 0:
                            self._delivery_stats['retries'] += attempt
                            
                        # Return success with response data
                        response_data = {
                            'status_code': response.status_code,
                            'delivery_time': delivery_time,
                            'attempts': attempt + 1,
                            'file_attachments': file_count,
                            'embeds': embed_count
                        }
                        
                        return True, response_data
                        
                    else:
                        status_code = response.status_code if response and hasattr(response, 'status_code') else "N/A"
                        response_text = getattr(response, 'text', 'No response text') if response else 'No response'
                        
                        self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Webhook failed (attempt {attempt+1}/{max_retries}): Status {status_code}")
                        self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Response: {response_text}")
                        
                        last_error = f"HTTP {status_code}: {response_text}"
                        
                except Exception as e:
                    logger.error(f"Unhandled exception: {e}", exc_info=True)
                    attempt_time = time.time() - attempt_start
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Error sending webhook (attempt {attempt+1}/{max_retries}): {str(e)}")
                    self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Attempt {attempt + 1} failed in {attempt_time:.2f}s")
                    last_error = str(e)
                    
                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Retrying in {retry_delay:.1f}s...")
                    await asyncio.sleep(retry_delay)
                    if self.webhook_exponential_backoff:
                        retry_delay *= 2
            
            # If all retries failed, log error and update stats
            total_time = time.time() - start_time
            self.logger.error(f"[WEBHOOK_DELIVERY:{delivery_id}] Failed to send Discord webhook message after {max_retries} attempts in {total_time:.2f}s")
            self.logger.error(f"[WEBHOOK_DELIVERY:{delivery_id}] Last error: {last_error}")
            
            self._delivery_stats['failed_deliveries'] += 1
            self._delivery_stats['retries'] += max_retries - 1
            
            return False, {'error': last_error, 'attempts': max_retries, 'total_time': total_time}
            
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            total_time = time.time() - start_time
            self.logger.error(f"[WEBHOOK_DELIVERY:{delivery_id}] Unexpected error in send_discord_webhook_message: {str(e)}")
            self.logger.error(f"[WEBHOOK_DELIVERY:{delivery_id}] Traceback: {traceback.format_exc()}")
            
            self._delivery_stats['failed_deliveries'] += 1
            
            return False, {'error': f'Unexpected error: {str(e)}', 'total_time': total_time}
    
    # ========== IMPROVED SESSION MANAGEMENT FROM REFACTORED VERSION ==========
    async def _ensure_webhook_session(self):
        """
        Ensure aiohttp session exists and is reusable.
        Improved session management from refactored version.
        """
        if not hasattr(self, '_webhook_session') or self._webhook_session is None or self._webhook_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.webhook_timeout)
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool limit
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300  # DNS cache timeout
            )
            self._webhook_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            self.logger.debug("Created new webhook session with connection pooling")
    
    async def _close_webhook_session(self):
        """Close aiohttp session properly"""
        if hasattr(self, '_webhook_session') and self._webhook_session and not self._webhook_session.closed:
            await self._webhook_session.close()
            self.logger.debug("Closed webhook session")
    
    async def cleanup(self):
        """Clean up resources when shutting down"""
        try:
            # Close client session if it exists
            if self._client_session and not self._client_session.closed:
                await self._client_session.close()
                self.logger.info("Closed HTTP client session")

            # Close webhook session
            await self._close_webhook_session()

            # Clean up throttle entries
            self._cleanup_throttle_entries()

            self.logger.info("AlertManager cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def _validate_attachment_files(self, files: List[Union[str, Dict[str, Any]]], delivery_id: str) -> List[Dict[str, Any]]:
        """
        Validate file attachments before sending.
        
        Args:
            files: List of file paths or file dictionaries
            delivery_id: Delivery ID for logging
            
        Returns:
            List of validated file information dictionaries
        """
        validated_files = []
        
        for file_item in files:
            try:
                # Handle different file formats
                if isinstance(file_item, str):
                    file_path = file_item
                    filename = os.path.basename(file_path)
                elif isinstance(file_item, dict):
                    file_path = file_item.get('path', '')
                    filename = file_item.get('filename', os.path.basename(file_path))
                else:
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Invalid file item type: {type(file_item)}")
                    continue
                
                # Check if file exists
                if not os.path.exists(file_path):
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] File does not exist: {file_path}")
                    continue
                
                # Check if it's actually a file (not a directory)
                if not os.path.isfile(file_path):
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Path is not a file: {file_path}")
                    continue
                
                # Get file size
                try:
                    file_size = os.path.getsize(file_path)
                except OSError as e:
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Cannot get file size for {file_path}: {str(e)}")
                    continue
                
                # Check file size limits
                if file_size == 0:
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] File is empty: {file_path}")
                    continue
                
                if file_size > self.max_file_size:
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] File too large ({file_size / 1024 / 1024:.1f} MB): {filename}")
                    continue
                
                # Check file extension
                file_ext = os.path.splitext(filename)[1].lower()
                if self.allowed_file_types and file_ext not in self.allowed_file_types:
                    self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] File type not allowed ({file_ext}): {filename}")
                    continue
                
                # Additional validation for PDF files
                if file_ext == '.pdf':
                    try:
                        with open(file_path, 'rb') as f:
                            header = f.read(8)
                            if not header.startswith(b'%PDF'):
                                self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Invalid PDF file: {filename}")
                                continue
                    except Exception as e:
                        self.logger.warning(f"[WEBHOOK_DELIVERY:{delivery_id}] Cannot validate PDF file {filename}: {str(e)}")
                        continue
                
                # File passed all validations
                validated_files.append({
                    'path': file_path,
                    'filename': filename,
                    'size': file_size,
                    'extension': file_ext
                })
                
                self.logger.debug(f"[WEBHOOK_DELIVERY:{delivery_id}] Validated file: {filename} ({file_size / 1024:.1f} KB)")
                
            except Exception as e:
                self.logger.error(f"[WEBHOOK_DELIVERY:{delivery_id}] Error validating file {file_item}: {str(e)}")
                continue
        
        self.logger.info(f"[WEBHOOK_DELIVERY:{delivery_id}] Validated {len(validated_files)}/{len(files)} files")
        return validated_files

    def get_delivery_stats(self) -> Dict[str, Any]:
        """
        Get delivery statistics for monitoring.
        
        Returns:
            Dictionary containing delivery statistics
        """
        return {
            **self._delivery_stats,
            'success_rate': (
                self._delivery_stats['successful_deliveries'] / max(1, self._delivery_stats['total_attempts'])
            ) * 100,
            'file_attachment_success_rate': (
                (self._delivery_stats['file_attachments'] - self._delivery_stats['file_attachment_failures']) / 
                max(1, self._delivery_stats['file_attachments'])
            ) * 100 if self._delivery_stats['file_attachments'] > 0 else 100
        }

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
                    logger.error(f"Unhandled exception: {e}", exc_info=True)
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
                - long_threshold: Threshold for long signals
                - short_threshold: Threshold for short signals
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
            long_threshold = signal_data.get('long_threshold', signal_data.get('buy_threshold', self.long_threshold))
            short_threshold = signal_data.get('short_threshold', signal_data.get('sell_threshold', self.short_threshold))
            
            if explicit_signal_type:
                signal_type = explicit_signal_type
            else:
                signal_type = 'LONG' if score > long_threshold else 'SHORT' if score < short_threshold else 'NEUTRAL'
            
            # Skip sending alerts for NEUTRAL signals (regardless of score vs threshold)
            # This prevents alerts for signals labeled as NEUTRAL in the UI
            if signal_type == 'NEUTRAL' or (
                # Also skip any score in the neutral zone (between sell and buy thresholds)
                short_threshold <= score <= long_threshold
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
                signal_type=signal_type,
                # Pass OHLCV data for chart generation
                ohlcv_data=signal_data.get('ohlcv_data')
            )
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][ALERT:{alert_id}] Successfully sent confluence alert for {symbol}")

            # ═══════════════════════════════════════════════════════════════════
            # SIGNAL TRACKING: Record signal for performance validation
            # ═══════════════════════════════════════════════════════════════════
            try:
                from src.database.signal_performance import SignalPerformanceTracker
                from src.database.signal_tracking_helpers import determine_signal_pattern

                # Initialize tracker
                tracker = SignalPerformanceTracker()

                # Determine signal pattern (divergence vs confirmation)
                component_scores = signal_data.get('components', {})
                pattern = determine_signal_pattern(component_scores, signal_type)

                # Extract trade parameters
                trade_params = signal_data.get('trade_params', {})
                entry_price = trade_params.get('entry_price') or signal_data.get('entry_price') or signal_data.get('price')
                stop_loss = trade_params.get('stop_loss') or signal_data.get('stop_loss')
                targets = trade_params.get('targets') or signal_data.get('targets', [])

                # Open signal for tracking
                tracking_id = tracker.open_signal(
                    symbol=symbol,
                    signal_type=signal_type,
                    confluence_score=score,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    targets=targets,
                    signal_pattern=pattern,
                    component_scores=component_scores,
                    metadata={
                        'transaction_id': transaction_id,
                        'signal_id': signal_id,
                        'alert_id': alert_id,
                        'reliability': signal_data.get('reliability', 0.8),
                        'market_interpretations': signal_data.get('market_interpretations'),
                        'actionable_insights': signal_data.get('actionable_insights')
                    }
                )

                if tracking_id:
                    self.logger.info(
                        f"[TXN:{transaction_id}][SIG:{signal_id}][TRACK:{tracking_id}] "
                        f"Opened {signal_type} signal tracking for {symbol} "
                        f"(pattern: {pattern}, score: {score:.2f})"
                    )
                else:
                    self.logger.warning(
                        f"[TXN:{transaction_id}][SIG:{signal_id}] "
                        f"Failed to open signal tracking for {symbol}"
                    )

            except Exception as track_error:
                # Don't let tracking errors break alert sending
                self.logger.error(
                    f"[TXN:{transaction_id}][SIG:{signal_id}] "
                    f"Error recording signal for tracking: {track_error}"
                )
                self.logger.debug(traceback.format_exc())
            # ═══════════════════════════════════════════════════════════════════

            # IMPROVED THROTTLING: Mark alert as sent (using different variable names for this context)
            alert_key_2 = f"{symbol}_{signal_data.get('signal_type', 'signal')}_alert" 
            content_for_dedup_2 = f"{symbol}_{signal_data.get('confluence_score', 0):.2f}"
            self._mark_alert_sent_improved(alert_key_2, 'signal', content_for_dedup_2)
            
            # Send high-resolution chart image first - ALWAYS generate if not present
            # Initialize chart_path from signal_data and normalize any file URI scheme
            chart_path = signal_data.get('chart_path')
            if isinstance(chart_path, str) and chart_path.startswith('file://'):
                chart_path = chart_path[7:]

            # ALWAYS generate chart if not already present (changed from: if not chart_path and pdf_path)
            if not chart_path:
                # Generate chart from signal data
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] No chart_path provided, generating chart from signal data")
                chart_path = await self._generate_chart_from_signal_data(signal_data, transaction_id, signal_id)
            
            if chart_path and os.path.exists(chart_path):
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Sending high-resolution chart: {chart_path}")
                
                # Extract trade parameters for the message
                trade_params = signal_data.get('trade_params', {})
                entry_price = trade_params.get('entry_price') or signal_data.get('entry_price') or signal_data.get('price')
                stop_loss = trade_params.get('stop_loss') or signal_data.get('stop_loss')
                targets = trade_params.get('targets') or signal_data.get('targets', [])
                
                # Format stop loss and targets information
                sl_info = f"**Stop Loss:** ${stop_loss:.4f}" if stop_loss else "**Stop Loss:** Not set"
                
                tp_info = []
                if targets:
                    if isinstance(targets, list):
                        for i, target in enumerate(targets):
                            if isinstance(target, dict):
                                target_price = target.get('price', 0)
                                target_size = target.get('size', 0)
                                if target_price > 0:
                                    tp_info.append(f"**TP{i+1}:** ${target_price:.4f} ({target_size}%)")
                    elif isinstance(targets, dict):
                        for name, target in targets.items():
                            if isinstance(target, dict):
                                target_price = target.get('price', 0)
                                target_size = target.get('size', 0)
                                if target_price > 0:
                                    tp_info.append(f"**{name}:** ${target_price:.4f} ({target_size}%)")
                
                tp_text = "\n".join(tp_info) if tp_info else "**Targets:** Not set"
                
                # Create message for chart
                chart_emoji = "📊"
                chart_message = {
                    "content": f"{chart_emoji} **{symbol} Price Action Chart**\n\n**Entry:** ${entry_price:.4f}\n{sl_info}\n\n{tp_text}",
                    "username": "Virtuoso Trading",
                }
                
                # Send the chart
                try:
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Sending chart with TP/SL details")
                    await self.send_discord_webhook_message(chart_message, files=[chart_path])
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Chart sent successfully")
                except Exception as chart_err:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Error sending chart: {str(chart_err)}")
                    self.logger.error(traceback.format_exc())

            # Component chart generation removed - already included in PDF report
            # The PDF contains comprehensive component analysis visualization
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Component chart included in PDF report, not sending separately")

            # Send PDF attachment as a separate message if available
            if pdf_path:
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][PDF] Sending PDF attachment: {pdf_path}")
                
                # Create title based on signal type and score
                signal_emoji = "📈" if signal_type == "LONG" else "📉" if signal_type == "SHORT" else "📊"
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

            # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
            await self._store_and_cache_alert_direct(
                alert_type='signal',
                symbol=symbol,
                message=f"{signal_type} Signal: {symbol} (Score: {score:.1f})",
                level='INFO' if signal_type == 'NEUTRAL' else 'WARNING',
                details={
                    'confluence_score': score,
                    'signal_type': signal_type,
                    'price': signal_data.get('price'),
                    'components': signal_data.get('components', {}),
                    'reliability': signal_data.get('reliability'),
                    'transaction_id': transaction_id,
                    'signal_id': signal_id
                }
            )

            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Successfully sent signal alert for {symbol}")
            
        except Exception as e:
            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error sending signal alert: {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise

    async def _generate_chart_from_signal_data(self, signal_data: Dict[str, Any], transaction_id: str, signal_id: str) -> Optional[str]:
        """Generate a high-resolution chart from signal data.
        
        Args:
            signal_data: Signal data containing OHLCV data and trade parameters
            transaction_id: Transaction ID for logging
            signal_id: Signal ID for logging
            
        Returns:
            Path to the generated chart image or None if generation fails
        """
        try:
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Attempting to generate chart from signal data")
            
            # Check if we have the PDF generator available
            if not hasattr(self, 'pdf_generator') or not self.pdf_generator:
                self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] PDF generator not available")
                return None
            
            # Extract necessary data
            symbol = signal_data.get('symbol', 'UNKNOWN')
            ohlcv_data = signal_data.get('ohlcv_data')
            trade_params = signal_data.get('trade_params', {})
            
            # Get trade parameters
            entry_price = trade_params.get('entry_price') or signal_data.get('entry_price') or signal_data.get('price')
            stop_loss = trade_params.get('stop_loss') or signal_data.get('stop_loss')
            targets = trade_params.get('targets') or signal_data.get('targets')
            
            # Create output directory for charts
            chart_dir = os.path.join(os.getcwd(), 'reports', 'charts')
            os.makedirs(chart_dir, exist_ok=True)
            
            # Try to create the chart
            if hasattr(self.pdf_generator, '_create_candlestick_chart'):
                if ohlcv_data is not None:
                    # Use real OHLCV data if available
                    chart_path = self.pdf_generator._create_candlestick_chart(
                        symbol=symbol,
                        ohlcv_data=ohlcv_data,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        output_dir=chart_dir
                    )
                else:
                    # Use simulated chart if no OHLCV data
                    if hasattr(self.pdf_generator, '_create_simulated_chart') and entry_price:
                        chart_path = self.pdf_generator._create_simulated_chart(
                            symbol=symbol,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            targets=targets,
                            output_dir=chart_dir
                        )
                    else:
                        self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] No OHLCV data or entry price for chart generation")
                        return None
                
                if chart_path and os.path.exists(chart_path):
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Chart generated successfully: {chart_path}")
                    return chart_path
                else:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Chart generation returned no valid path")
                    return None
            else:
                self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Chart generation methods not available in PDF generator")
                return None
                
        except Exception as e:
            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][CHART] Error generating chart: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    async def send_alpha_opportunity_alert(
        self,
        symbol: str,
        alpha_estimate: float,
        confidence_score: float,
        divergence_type: str,
        risk_level: str,
        trading_insight: str,
        market_data: Dict[str, Any],
        transaction_id: str = None
    ) -> None:
        """Send alpha opportunity alert with enhanced formatting for key patterns.
        
        Args:
            symbol: Trading pair symbol
            alpha_estimate: Estimated alpha (excess return vs Bitcoin)
            confidence_score: Confidence score (0-1)
            divergence_type: Type of divergence detected
            risk_level: Risk level assessment
            trading_insight: Trading insight description
            market_data: Market data context
            transaction_id: Transaction ID for tracking
        """
        try:
            # Use centralized routing (supports dev mode override)
            webhook_url, webhook_type = self._get_webhook_url("alpha")

            if not webhook_url:
                self.logger.warning("No webhook URL configured for alpha alerts")
                return

            # Generate transaction ID if not provided
            transaction_id = transaction_id or str(uuid.uuid4())[:8]
            
            # Handle both string and enum inputs for divergence_type
            divergence_str = divergence_type.value if hasattr(divergence_type, 'value') else str(divergence_type)
            
            # Determine alert urgency and formatting based on pattern type
            if divergence_str == "beta_expansion":
                emoji = "🚀"
                pattern_name = "BETA EXPANSION"
                alert_color = 0xFF4500  # Orange-red for momentum
                urgency = "HIGH MOMENTUM"
                description_prefix = "**📈 AGGRESSIVE MOVEMENT DETECTED**\n"
                
            elif divergence_str == "correlation_breakdown":
                emoji = "🎯"
                pattern_name = "CORRELATION BREAKDOWN"
                alert_color = 0x9932CC  # Purple for independence
                urgency = "INDEPENDENCE OPPORTUNITY"
                description_prefix = "**🔄 INDEPENDENCE DETECTED**\n"
                
            elif divergence_str == "beta_compression":
                emoji = "📉"
                pattern_name = "BETA COMPRESSION"
                alert_color = 0x32CD32  # Green for alpha opportunity
                urgency = "ALPHA GENERATION"
                description_prefix = "**⚡ REDUCED CORRELATION**\n"
                
            else:
                emoji = "⚡"
                pattern_name = divergence_str.upper().replace('_', ' ')
                alert_color = 0x00CED1  # Default cyan
                urgency = "ALPHA OPPORTUNITY"
                description_prefix = "**📊 PATTERN DETECTED**\n"

            # Format confidence with special highlighting
            if confidence_score >= 0.85:
                confidence_emoji = "🔥"
                confidence_text = f"**{confidence_score:.1%}** {confidence_emoji}"
            elif confidence_score >= 0.70:
                confidence_emoji = "✨"
                confidence_text = f"**{confidence_score:.1%}** {confidence_emoji}"
            else:
                confidence_emoji = "📊"
                confidence_text = f"{confidence_score:.1%} {confidence_emoji}"

            # Format alpha with sign and highlighting
            alpha_sign = "+" if alpha_estimate >= 0 else ""
            if abs(alpha_estimate) >= 0.05:  # 5%+ alpha
                alpha_text = f"**{alpha_sign}{alpha_estimate:.1%}** 🎯"
            elif abs(alpha_estimate) >= 0.02:  # 2%+ alpha
                alpha_text = f"**{alpha_sign}{alpha_estimate:.1%}** ⭐"
            else:
                alpha_text = f"{alpha_sign}{alpha_estimate:.1%}"

            # Get market context
            current_price = market_data.get('asset', {}).get('price', 0)
            bitcoin_price = market_data.get('bitcoin', {}).get('price', 0)
            
            # Create enhanced alert embed
            alert_title = f"{emoji} {urgency}: {symbol} vs BTC"
            
            description = [
                description_prefix,
                f"**{pattern_name}** pattern detected for **{symbol}**",
                "",
                f"• **Alpha Estimate:** {alpha_text}",
                f"• **Confidence:** {confidence_text}",
                f"• **Risk Level:** {risk_level}",
                f"• **Pattern:** {pattern_name}",
                "",
                f"**📋 Trading Insight:**",
                f"```{trading_insight}```",
                "",
                f"**💰 Market Context:**",
                f"• {symbol} Price: ${current_price:,.4f}" if current_price else "",
                f"• Bitcoin Price: ${bitcoin_price:,.2f}" if bitcoin_price else "",
                f"• Alert ID: `{transaction_id}`",
            ]
            
            # Add pattern-specific guidance
            # Use the same string conversion for comparisons
            if divergence_str == "beta_expansion":
                description.extend([
                    "",
                    f"**🎯 Beta Expansion Strategy:**",
                    f"• Monitor for sustained momentum above Bitcoin",
                    f"• Consider momentum entries with tight stops",
                    f"• Watch for volume confirmation",
                    f"• Risk: High correlation to Bitcoin moves"
                ])
                
            elif divergence_str == "correlation_breakdown":
                description.extend([
                    "",
                    f"**🎯 Independence Strategy:**",
                    f"• Look for news catalysts driving independence",
                    f"• Consider pure alpha plays",
                    f"• Monitor correlation for reversal",
                    f"• Opportunity: Reduced Bitcoin dependency"
                ])

            # Send Discord alert using centralized routing
            self.logger.debug(f"Routing alpha alert to {webhook_type} webhook")
            webhook = DiscordWebhook(url=webhook_url)

            # Create embed and add fields properly (discord_webhook doesn't support method chaining)
            embed = DiscordEmbed(
                title=alert_title,
                description="\n".join(filter(None, description)),
                color=alert_color
            )
            embed.add_embed_field(
                name=f"{emoji} Quick Stats",
                value=f"Alpha: {alpha_text}\nConfidence: {confidence_text}\nRisk: {risk_level}",
                inline=True
            )
            embed.set_footer(text=f"Virtuoso Alpha Detection • ID: {transaction_id}")
            embed.set_timestamp()
            
            webhook.add_embed(embed)
            
            # Execute webhook with retry logic
            max_retries = self.webhook_max_retries
            retry_delay = self.webhook_initial_retry_delay
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = webhook.execute()
                    
                    if response and response.status_code in [200, 204]:
                        self.logger.info(f"Alpha opportunity alert sent successfully for {symbol}")
                        break
                    else:
                        status_code = response.status_code if response else "N/A"
                        self.logger.warning(f"Failed to send alpha alert (attempt {attempt+1}/{max_retries}): Status code {status_code}")
                        
                        if response and response.status_code in self.webhook_recoverable_status_codes:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                if self.webhook_exponential_backoff:
                                    retry_delay *= 2
                                continue
                        
                except Exception as e:
                    self.logger.error(f"Error executing alpha webhook (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        if self.webhook_exponential_backoff:
                            retry_delay *= 2
                        continue
                    else:
                        raise

            # Update alert statistics using internal tracking
            if response and response.status_code in [200, 204]:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1

                # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
                await self._store_and_cache_alert_direct(
                    alert_type='alpha_opportunity',
                    symbol=symbol,
                    message=alert_title,
                    level='WARNING',
                    details={
                        'alpha_estimate': alpha_estimate,
                        'confidence_score': confidence_score,
                        'divergence_type': divergence_str,
                        'risk_level': risk_level,
                        'trading_insight': trading_insight,
                        'price': market_data.get('current_price'),
                        'bitcoin_price': market_data.get('bitcoin_price'),
                        'transaction_id': transaction_id
                    }
                )
            else:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

        except Exception as e:
            self.logger.error(f"Error sending alpha opportunity alert for {symbol}: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())

    async def send_manipulation_alert(
        self,
        symbol: str,
        manipulation_type: str,
        confidence_score: float,
        severity: str,
        metrics: Dict[str, Any],
        description: str,
        current_price: float = None
    ) -> None:
        """
        Send manipulation detection alert.
        
        Args:
            symbol: Trading pair symbol
            manipulation_type: Type of manipulation detected
            confidence_score: Confidence score (0-1)
            severity: Alert severity ('low', 'medium', 'high', 'critical')
            metrics: Manipulation metrics dictionary
            description: Description of the manipulation
            current_price: Current price of the asset
        """
        try:
            # Use centralized routing (supports dev mode override)
            webhook_url, webhook_type = self._get_webhook_url("manipulation")

            if not webhook_url:
                self.logger.warning("No webhook URL configured for manipulation alerts")
                return

            # Determine alert color and emoji based on severity
            severity_color_map = {
                'low': 0x3498db,      # Blue
                'medium': 0xf39c12,   # Orange  
                'high': 0xe74c3c,     # Red
                'critical': 0x9b59b6  # Purple
            }
            color = severity_color_map.get(severity, 0x95a5a6)  # Default gray
            
            # Create severity emoji
            severity_emoji_map = {
                'low': '⚠️',
                'medium': '🔸',
                'high': '🚨',
                'critical': '💀'
            }
            severity_emoji = severity_emoji_map.get(severity, '⚠️')
            
            # Format manipulation type for display
            manipulation_type_display = manipulation_type.replace('_', ' ').title()
            
            # Create Discord embed title
            title = f"{severity_emoji} Market Manipulation Detected: {symbol}"
            
            # Build description with key metrics
            description = [
                f"**{manipulation_type_display}** pattern detected for **{symbol}**",
                "",
                f"• **Confidence:** {confidence_score:.1%}",
                f"• **Severity:** {severity.upper()}",
                f"• **Current Price:** ${current_price:,.4f}" if current_price else "",
                "",
                f"**📋 Analysis:**",
                f"```{description}```"
            ]
            
            # Add specific metrics as embed fields
            embed = DiscordEmbed(
                title=title,
                description="\n".join(filter(None, description)),
                color=color
            )
            
            # Add timestamp
            embed.set_timestamp()
            
            # Add metrics as inline fields if available
            if metrics:
                if metrics.get('oi_change_15m_pct', 0) != 0:
                    oi_pct = metrics['oi_change_15m_pct'] * 100
                    embed.add_embed_field(
                        name="OI Change (15m)",
                        value=f"{oi_pct:+.1f}%",
                        inline=True
                    )
                    
                if metrics.get('volume_spike_ratio', 0) > 1:
                    volume_ratio = metrics['volume_spike_ratio']
                    embed.add_embed_field(
                        name="Volume Spike",
                        value=f"{volume_ratio:.1f}x avg",
                        inline=True
                    )
                    
                if metrics.get('price_change_15m_pct', 0) != 0:
                    price_pct = metrics['price_change_15m_pct'] * 100
                    embed.add_embed_field(
                        name="Price Change (15m)",
                        value=f"{price_pct:+.1f}%",
                        inline=True
                    )
                    
                if metrics.get('divergence_detected', False):
                    divergence_strength = metrics.get('divergence_strength', 0) * 100
                    embed.add_embed_field(
                        name="OI-Price Divergence",
                        value=f"{divergence_strength:.1f}% strength",
                        inline=True
                    )
            
            # Add footer with tracking info
            embed.set_footer(text=f"Virtuoso Manipulation Detection • {manipulation_type}")

            # Create webhook using centralized routing
            self.logger.debug(f"Routing manipulation alert to {webhook_type} webhook")
            webhook = DiscordWebhook(url=webhook_url)
            webhook.add_embed(embed)
            
            # Execute webhook with retry logic
            max_retries = self.webhook_max_retries
            retry_delay = self.webhook_initial_retry_delay
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = webhook.execute()
                    
                    if response and response.status_code in [200, 204]:
                        self.logger.info(f"Manipulation alert sent successfully for {symbol}: {manipulation_type}")
                        break
                    else:
                        status_code = response.status_code if response else "N/A"
                        self.logger.warning(f"Failed to send manipulation alert (attempt {attempt+1}/{max_retries}): Status code {status_code}")
                        
                        if response and response.status_code in self.webhook_recoverable_status_codes:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                if self.webhook_exponential_backoff:
                                    retry_delay *= 2
                                continue
                        
                except Exception as e:
                    self.logger.error(f"Error executing manipulation webhook (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        if self.webhook_exponential_backoff:
                            retry_delay *= 2
                        continue
                    else:
                        raise

            # Update alert statistics and store
            if response and response.status_code in [200, 204]:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1

                # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
                await self._store_and_cache_alert_direct(
                    alert_type='manipulation',
                    symbol=symbol,
                    message=title,
                    level=severity.upper(),
                    details={
                        'manipulation_type': manipulation_type,
                        'confidence_score': confidence_score,
                        'severity': severity,
                        'price': current_price,
                        'metrics': metrics
                    }
                )
            else:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
                           
        except Exception as e:
            self.logger.error(f"Error sending manipulation alert for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def send_retail_pressure_alert(
        self,
        symbol: str,
        retail_score: float,
        retail_imbalance: float,
        retail_participation: float,
        interpretation: str,
        current_price: float = None,
        signal_strength: str = "moderate"
    ) -> None:
        """
        Send retail pressure alert based on RPI data analysis.

        Args:
            symbol: Trading pair symbol
            retail_score: Retail component score (0-100)
            retail_imbalance: Retail bid/ask imbalance (-1 to 1)
            retail_participation: Retail participation rate (0-1)
            interpretation: Human-readable interpretation
            current_price: Current price of the asset
            signal_strength: Signal strength ('weak', 'moderate', 'strong')
        """
        import time
        start_time = time.time()

        try:
            self.logger.debug(f"🔍 [RPI_DEBUG] Starting retail pressure alert for {symbol}")
            self.logger.debug(f"🔍 [RPI_DEBUG] Alert parameters:")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Retail score: {retail_score:.2f}")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Retail imbalance: {retail_imbalance:.4f}")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Retail participation: {retail_participation:.4f} ({retail_participation*100:.1f}%)")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Signal strength: {signal_strength}")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Current price: {current_price}")
            self.logger.debug(f"🔍 [RPI_DEBUG]   Interpretation: {interpretation}")

            # Skip if no webhook URL configured
            if not self.discord_webhook_url:
                self.logger.warning("Discord webhook URL not configured for retail alerts")
                self.logger.debug(f"🔍 [RPI_DEBUG] Alert skipped - no webhook configured")
                return

            # Check throttling for retail alerts
            alert_key = f"retail_pressure_{symbol}_{int(retail_score/5)*5}"  # Group by 5-point ranges
            self.logger.debug(f"🔍 [RPI_DEBUG] Checking throttling with key: {alert_key}")

            if self._check_improved_throttling(alert_key, "retail_pressure"):
                self._mark_alert_sent_improved(alert_key, "retail_pressure")
                self.logger.debug(f"🔍 [RPI_DEBUG] Throttling check passed - proceeding with alert")
            else:
                self.logger.debug(f"Retail pressure alert throttled for {symbol}")
                self.logger.debug(f"🔍 [RPI_DEBUG] Alert throttled - skipping")
                return

            # Determine alert color and emoji based on retail score
            if retail_score >= 75:
                color = 0x00ff00  # Bright green - strong buying
                emoji = "🚀"
            elif retail_score >= 60:
                color = 0x32cd32  # Green - moderate buying
                emoji = "📈"
            elif retail_score <= 25:
                color = 0xff0000  # Red - strong selling
                emoji = "📉"
            elif retail_score <= 40:
                color = 0xff6b6b  # Light red - moderate selling
                emoji = "⚠️"
            else:
                color = 0xffa500  # Orange - neutral/mixed
                emoji = "🔄"

            # Format participation percentage
            participation_pct = retail_participation * 100

            # Create embed title
            direction = "Bullish" if retail_score > 60 else "Bearish" if retail_score < 40 else "Neutral"
            title = f"{emoji} {direction} Retail Pressure Detected - {symbol}"

            embed_data = {
                "title": title,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fields": [
                    {
                        "name": "📊 Retail Score",
                        "value": f"{retail_score:.1f}/100",
                        "inline": True
                    },
                    {
                        "name": "⚖️ Retail Imbalance",
                        "value": f"{retail_imbalance:+.3f}",
                        "inline": True
                    },
                    {
                        "name": "🎯 Participation Rate",
                        "value": f"{participation_pct:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "🧠 Interpretation",
                        "value": interpretation,
                        "inline": False
                    },
                    {
                        "name": "💪 Signal Strength",
                        "value": signal_strength.title(),
                        "inline": True
                    }
                ]
            }

            # Add price if available
            if current_price:
                embed_data["fields"].append({
                    "name": "💰 Current Price",
                    "value": f"${current_price:,.2f}",
                    "inline": True
                })

            # Add footer with timestamp
            embed_data["footer"] = {
                "text": f"RPI Analysis • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }

            # Send to Discord
            message_data = {
                "embeds": [embed_data]
            }

            success, response = await self.send_discord_webhook_message(
                message_data,
                alert_type="retail_pressure"
            )

            if success:
                self.logger.info(f"Retail pressure alert sent for {symbol}: {interpretation}")

                # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
                await self._store_and_cache_alert_direct(
                    alert_type='retail_pressure',
                    symbol=symbol,
                    message=title,
                    level='WARNING' if retail_score >= 75 or retail_score <= 25 else 'INFO',
                    details={
                        'retail_score': retail_score,
                        'retail_imbalance': retail_imbalance,
                        'retail_participation': retail_participation,
                        'interpretation': interpretation,
                        'price': current_price,
                        'signal_strength': signal_strength,
                        'direction': direction
                    }
                )
            else:
                self.logger.error(f"Failed to send retail pressure alert for {symbol}")

        except Exception as e:
            self.logger.error(f"Error sending retail pressure alert for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def send_retail_extremes_alert(
        self,
        symbol: str,
        retail_score: float,
        alert_type: str,  # 'extreme_buying' or 'extreme_selling'
        retail_metrics: Dict[str, Any],
        current_price: float = None
    ) -> None:
        """
        Send alert for extreme retail activity (above 80 or below 20).

        Args:
            symbol: Trading pair symbol
            retail_score: Retail component score
            alert_type: Type of extreme activity
            retail_metrics: Additional retail metrics
            current_price: Current price of the asset
        """
        try:
            # Skip if no webhook URL configured
            if not self.discord_webhook_url:
                self.logger.warning("Discord webhook URL not configured for extreme retail alerts")
                return

            # Check throttling for extreme alerts (more restrictive)
            alert_key = f"retail_extreme_{symbol}_{alert_type}"
            if self._check_improved_throttling(alert_key, "retail_extreme", content=f"{retail_score:.1f}"):
                self._mark_alert_sent_improved(alert_key, "retail_extreme", content=f"{retail_score:.1f}")
            else:
                self.logger.debug(f"Extreme retail alert throttled for {symbol}")
                return

            # Configure alert based on type
            if alert_type == "extreme_buying":
                color = 0x00ff00  # Bright green
                emoji = "🚀"
                title_action = "EXTREME RETAIL BUYING"
                description = "Unusually high retail buying pressure detected. Institutional interest may follow."
            else:  # extreme_selling
                color = 0xff0000  # Bright red
                emoji = "💥"
                title_action = "EXTREME RETAIL SELLING"
                description = "Severe retail selling pressure detected. Possible capitulation scenario."

            title = f"{emoji} {title_action} - {symbol}"

            embed_data = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fields": [
                    {
                        "name": "🎯 Retail Score",
                        "value": f"{retail_score:.1f}/100",
                        "inline": True
                    },
                    {
                        "name": "📊 Participation Rate",
                        "value": f"{retail_metrics.get('participation', 0)*100:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "⚖️ Imbalance",
                        "value": f"{retail_metrics.get('imbalance', 0):+.3f}",
                        "inline": True
                    }
                ]
            }

            # Add price if available
            if current_price:
                embed_data["fields"].append({
                    "name": "💰 Price",
                    "value": f"${current_price:,.2f}",
                    "inline": True
                })

            # Add additional metrics if available
            if retail_metrics.get('total_volume'):
                embed_data["fields"].append({
                    "name": "📈 Total Retail Volume",
                    "value": f"{retail_metrics['total_volume']:,.2f}",
                    "inline": True
                })

            # Add trading implications
            if alert_type == "extreme_buying":
                implications = "• Watch for institutional follow-through\n• Potential momentum continuation\n• Monitor for profit-taking"
            else:
                implications = "• Possible reversal opportunity\n• Watch for institutional accumulation\n• Monitor support levels"

            embed_data["fields"].append({
                "name": "💡 Trading Implications",
                "value": implications,
                "inline": False
            })

            embed_data["footer"] = {
                "text": f"RPI Extreme Alert • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }

            # Send to Discord
            message_data = {
                "embeds": [embed_data]
            }

            success, response = await self.send_discord_webhook_message(
                message_data,
                alert_type="retail_extreme"
            )

            if success:
                self.logger.info(f"Extreme retail alert sent for {symbol}: {title_action}")

                # Store in SQLite and cache for dashboard (CRITICAL FIX: was bypassing storage)
                await self._store_and_cache_alert_direct(
                    alert_type='retail_extreme',
                    symbol=symbol,
                    message=title,
                    level='CRITICAL' if retail_score >= 90 or retail_score <= 10 else 'WARNING',
                    details={
                        'retail_score': retail_score,
                        'extreme_type': alert_type,
                        'description': description,
                        'price': current_price,
                        'participation': retail_metrics.get('participation'),
                        'imbalance': retail_metrics.get('imbalance'),
                        'total_volume': retail_metrics.get('total_volume')
                    }
                )
            else:
                self.logger.error(f"Failed to send extreme retail alert for {symbol}")

        except Exception as e:
            self.logger.error(f"Error sending extreme retail alert for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _generate_retail_alerts(self, analysis_result: Dict[str, Any], symbol: str) -> List[str]:
        """
        Generate retail-specific alerts based on analysis results.

        Args:
            analysis_result: Orderbook analysis result containing retail component
            symbol: Trading symbol

        Returns:
            List of retail alert messages
        """
        self.logger.debug(f"🔍 [RPI_DEBUG] Generating retail alerts for {symbol}")
        self.logger.debug(f"🔍 [RPI_DEBUG] Analysis result keys: {list(analysis_result.keys())}")

        alerts = []
        components = analysis_result.get('components', {})
        retail_score = components.get('retail', 50.0)

        self.logger.debug(f"🔍 [RPI_DEBUG] Components available: {list(components.keys())}")
        self.logger.debug(f"🔍 [RPI_DEBUG] Retail score: {retail_score:.2f}")

        # Define thresholds and their corresponding alerts
        alert_thresholds = [
            (80, "🔥 Extreme Retail Buying Pressure - Institutional interest likely", "extreme_buying"),
            (70, "📈 Strong Retail Buying - Monitor for momentum", "strong_buying"),
            (30, "📉 Strong Retail Selling - Watch for reversal", "strong_selling", "<="),
            (20, "❄️ Extreme Retail Selling Pressure - Possible capitulation", "extreme_selling", "<=")
        ]

        # Generate alerts based on retail score thresholds
        self.logger.debug(f"🔍 [RPI_DEBUG] Evaluating {len(alert_thresholds)} threshold conditions")

        for i, threshold_config in enumerate(alert_thresholds):
            threshold = threshold_config[0]
            message = threshold_config[1]
            category = threshold_config[2]
            operator = threshold_config[3] if len(threshold_config) > 3 else ">="

            condition_met = False
            if operator == ">=":
                condition_met = retail_score >= threshold
            elif operator == "<=":
                condition_met = retail_score <= threshold

            self.logger.debug(f"🔍 [RPI_DEBUG]   Threshold {i+1}: {retail_score:.2f} {operator} {threshold} = {condition_met} ({category})")

            if condition_met:
                alerts.append(message)
                self.logger.debug(f"🔍 [RPI_DEBUG]   Alert triggered: {category}")
                break  # Only trigger the first matching condition

        # Log retail sentiment analysis
        if retail_score > 60:
            sentiment = "Bullish"
            strength = "Strong" if retail_score > 75 else "Moderate"
        elif retail_score < 40:
            sentiment = "Bearish"
            strength = "Strong" if retail_score < 25 else "Moderate"
        else:
            sentiment = "Neutral"
            strength = "Weak"

        self.logger.debug(f"🔍 [RPI_DEBUG] Retail sentiment: {strength} {sentiment} (score: {retail_score:.2f})")
        self.logger.debug(f"🔍 [RPI_DEBUG] Generated {len(alerts)} retail alerts for {symbol}")

        if alerts:
            for i, alert in enumerate(alerts):
                self.logger.debug(f"🔍 [RPI_DEBUG]   Alert {i+1}: {alert}")
        else:
            self.logger.debug(f"🔍 [RPI_DEBUG] No retail alerts generated (neutral conditions)")

        return alerts

    async def send_trade_execution_alert(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float,
        trade_type: str = "entry",  # 'entry' or 'exit'
        order_id: str = None,
        transaction_id: str = None,
        confluence_score: float = None,
        stop_loss_pct: float = None,
        take_profit_pct: float = None,
        position_size_usd: float = None,
        exchange: str = None
    ) -> None:
        """Send an alert when a trade is executed.
        
        Args:
            symbol: Trading pair symbol
            side: Trade side ('buy' or 'sell')
            quantity: Trade quantity
            price: Execution price
            trade_type: Type of trade ('entry' or 'exit')
            order_id: Exchange order ID
            transaction_id: Internal transaction ID
            confluence_score: Confluence score that triggered the trade
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            position_size_usd: Position size in USD
            exchange: Exchange name
        """
        # Generate IDs for tracking if not provided
        txn_id = transaction_id or str(uuid.uuid4())[:8]
        alert_id = str(uuid.uuid4())[:8]
        
        self.logger.debug(f"[TXN:{txn_id}][ALERT:{alert_id}] Sending trade execution alert for {symbol}")
        
        try:
            # Skip if no webhook URL configured and not in mock mode
            if not self.discord_webhook_url and not self.mock_mode:
                self.logger.warning(f"[TXN:{txn_id}][ALERT:{alert_id}] Cannot send trade alert: webhook URL not set")
                return
                
            # Normalize side to uppercase
            side = side.upper()
            trade_type = trade_type.lower()
            
            # Calculate USD value
            usd_value = quantity * price
            
            # Determine emoji and color based on side and trade type
            if trade_type == "entry":
                if side == "BUY":
                    emoji = "🟢"
                    color = 0x00FF00  # Green
                    title = f"{emoji} LONG POSITION OPENED: {symbol}"
                else:
                    emoji = "🔴"
                    color = 0xFF0000  # Red
                    title = f"{emoji} SHORT POSITION OPENED: {symbol}"
            else:  # exit
                if side == "BUY":  # Buying to close a short
                    emoji = "⚪"
                    color = 0xCCCCCC  # Light gray
                    title = f"{emoji} SHORT POSITION CLOSED: {symbol}"
                else:  # Selling to close a long
                    emoji = "⚪"
                    color = 0xCCCCCC  # Light gray
                    title = f"{emoji} LONG POSITION CLOSED: {symbol}"
            
            # Format price with appropriate precision
            price_str = format_price_string(price)
            
            # Build description with all trade details
            description = [
                f"**Price:** {price_str}",
                f"**Quantity:** {quantity:.8f}",
                f"**Value:** ${usd_value:.2f}"
            ]
            
            # Add exchange if provided
            if exchange:
                description.append(f"**Exchange:** {exchange}")
                
            # Add order ID if provided
            if order_id:
                description.append(f"**Order ID:** {order_id}")
                
            # Add position size in USD if provided
            if position_size_usd:
                description.append(f"**Position Size:** ${position_size_usd:.2f}")
                
            # Add risk management parameters if provided
            risk_params = []
            if stop_loss_pct:
                # Calculate stop price
                if side == "BUY":  # Long position
                    stop_price = price * (1 - stop_loss_pct)
                else:  # Short position
                    stop_price = price * (1 + stop_loss_pct)
                stop_price_str = format_price_string(stop_price)
                risk_params.append(f"**Stop Loss:** {stop_loss_pct*100:.2f}% ({stop_price_str})")
                
            if take_profit_pct:
                # Calculate take profit price
                if side == "BUY":  # Long position
                    tp_price = price * (1 + take_profit_pct)
                else:  # Short position
                    tp_price = price * (1 - take_profit_pct)
                tp_price_str = format_price_string(tp_price)
                risk_params.append(f"**Take Profit:** {take_profit_pct*100:.2f}% ({tp_price_str})")
                
            # Add risk parameters if any are provided
            if risk_params:
                description.append("\n**Risk Management:**")
                description.extend(risk_params)
                
            # Add confluence score if provided
            if confluence_score is not None:
                # Determine confidence level based on score
                if confluence_score >= 85:
                    confidence = "Very High"
                elif confluence_score >= 70:
                    confidence = "High"
                elif confluence_score >= 60:
                    confidence = "Medium"
                else:
                    confidence = "Low"
                    
                description.append(f"\n**Signal Confidence:** {confidence} ({confluence_score:.1f}/100)")
                
            # Join description parts
            description_text = "\n".join(description)
            
            # Create Discord embed
            embed = DiscordEmbed(
                title=title,
                description=description_text,
                color=color
            )
            
            # Add timestamp
            embed.set_timestamp()
            
            # Add footer with tracking ID
            embed.set_footer(text=f"TXN:{txn_id} | ALERT:{alert_id}")
            
            # Create webhook
            webhook = DiscordWebhook(url=self.discord_webhook_url or "https://mock.discord.webhook.url", username="Virtuoso Trading")
            
            # Add embed
            webhook.add_embed(embed)
            
            # Prepare for alert capture if enabled
            alert_data = {
                'title': title,
                'message': {
                    'content': description_text,
                    'embed': {
                        'title': title,
                        'description': description_text,
                        'color': color
                    }
                },
                'timestamp': time.time(),
                'type': 'trade_execution',
                'symbol': symbol,
                'side': side,
                'price': price,
                'quantity': quantity,
                'trade_type': trade_type,
                'txn_id': txn_id,
                'alert_id': alert_id
            }
            
            # Store in captured alerts if capture is enabled
            if self.capture_alerts:
                if not hasattr(self, 'captured_alerts'):
                    self.captured_alerts = []
                self.captured_alerts.append(alert_data)
                self.logger.info(f"[TXN:{txn_id}][ALERT:{alert_id}] Captured trade execution alert for {symbol}")
            
            # Mock mode removed - always send real alerts in production
            # (Mock mode should only be controlled via environment variables in test environments)
            
            # Execute webhook with retry logic (only if not in mock mode)
            max_retries = 3
            retry_delay = 2  # seconds
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = webhook.execute()
                    
                    if response and response.status_code in [200, 204]:
                        self.logger.info(f"[TXN:{txn_id}][ALERT:{alert_id}] Successfully sent trade execution alert for {symbol}")
                        break
                    else:
                        status_code = response.status_code if response else "N/A"
                        self.logger.warning(f"[TXN:{txn_id}][ALERT:{alert_id}] Failed to send alert (attempt {attempt+1}/{max_retries}): Status code {status_code}")
                        
                        if response and response.status_code in [429, 500, 502, 503, 504]:
                            # These are potentially recoverable with retry
                            if attempt < max_retries - 1:
                                self.logger.info(f"[TXN:{txn_id}][ALERT:{alert_id}] Retrying after {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                        
                except Exception as e:
                    self.logger.error(f"[TXN:{txn_id}][ALERT:{alert_id}] Error executing webhook (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise
            
            # Update alert stats
            if response and response.status_code in [200, 204]:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
            else:
                self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
            
        except Exception as e:
            self.logger.error(f"[TXN:{txn_id}][ALERT:{alert_id}] Error sending trade execution alert for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

    async def _send_smart_money_discord_alert(self, alert: Dict[str, Any], alert_id: str) -> None:
        """Send smart money alert to Discord with enhanced formatting."""
        try:
            details = alert.get('details', {})
            event_type = details.get('event_type', '')
            symbol = details.get('symbol', '')
            event_data = details.get('data', {})
            
            # Get sophistication and confidence scores
            sophistication_score = event_data.get('sophistication_score', 0)
            confidence = event_data.get('confidence', 0)
            
            # Determine color and sophistication text based on sophistication level
            if sophistication_score >= 9:
                color = 0x8B00FF  # Purple for expert level
                sophistication_text = "🎯 EXPERT"
                sophistication_emoji = "🎯"
            elif sophistication_score >= 7:
                color = 0xFF4500  # Orange for high level
                sophistication_text = "🔥 HIGH"
                sophistication_emoji = "🔥"
            elif sophistication_score >= 4:
                color = 0xFFD700  # Gold for medium level
                sophistication_text = "⚡ MEDIUM"
                sophistication_emoji = "⚡"
            else:
                color = 0x32CD32  # Green for low level
                sophistication_text = "📊 LOW"
                sophistication_emoji = "📊"

            # Create embed for smart money alert
            embed = DiscordEmbed(
                title=f"🧠 Smart Money Alert - {event_type.replace('_', ' ').title()}",
                description=f"**Sophisticated trading pattern detected**\n{alert.get('message', '')}",
                color=color
            )
            
            # Add timestamp
            embed.set_timestamp()
            
            # Add main fields
            embed.add_embed_field(
                name="📈 Symbol",
                value=f"**{symbol}**",
                inline=True
            )
            
            embed.add_embed_field(
                name="🎯 Sophistication",
                value=f"{sophistication_text}\n{sophistication_score:.1f}/10",
                inline=True
            )
            
            embed.add_embed_field(
                name="🎲 Confidence",
                value=f"**{confidence*100:.1f}%**",
                inline=True
            )

            # Add event-specific fields
            if event_type == 'orderflow_imbalance':
                side = event_data.get('side', '').upper()
                imbalance = event_data.get('imbalance', 0)
                side_emoji = "🟢" if side == "BUY" else "🔴"
                
                embed.add_embed_field(
                    name=f"{side_emoji} Imbalance Side",
                    value=f"**{side}**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="📊 Imbalance Ratio",
                    value=f"**{abs(imbalance)*100:.1f}%**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="🎯 Execution Quality",
                    value=f"{event_data.get('execution_quality', 0)*100:.0f}%",
                    inline=True
                )
                
            elif event_type == 'volume_spike':
                spike_ratio = event_data.get('spike_ratio', 0)
                timing_score = event_data.get('timing_score', 0)
                
                embed.add_embed_field(
                    name="📈 Spike Ratio",
                    value=f"**{spike_ratio:.1f}x**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="⏰ Timing Score",
                    value=f"{timing_score*100:.0f}%",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="🤝 Coordination",
                    value=f"{event_data.get('coordination_evidence', 0)*100:.0f}%",
                    inline=True
                )
                
            elif event_type == 'depth_change':
                side = event_data.get('side', '').upper()
                change_ratio = event_data.get('change_ratio', 0)
                side_emoji = "📗" if side == "BID" else "📕"
                
                embed.add_embed_field(
                    name=f"{side_emoji} Order Book Side",
                    value=f"**{side}**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="📊 Depth Change",
                    value=f"**{change_ratio*100:+.1f}%**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="🥷 Stealth Score",
                    value=f"{event_data.get('stealth_score', 0)*100:.0f}%",
                    inline=True
                )
                
            elif event_type == 'position_change':
                direction = event_data.get('direction', '').title()
                change_value = event_data.get('change_value', 0)
                direction_emoji = "📈" if direction == "Increase" else "📉"
                
                embed.add_embed_field(
                    name=f"{direction_emoji} Direction",
                    value=f"**{direction}**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="💰 Change Value",
                    value=f"**{change_value:,.0f}**",
                    inline=True
                )
                
                embed.add_embed_field(
                    name="🏛️ Institutional Pattern",
                    value=f"{event_data.get('institutional_pattern', 0)*100:.0f}%",
                    inline=True
                )

            # Add footer with additional context
            embed.set_footer(text=f"Smart Money Detection • Pattern: {event_type.replace('_', ' ').title()} • Alert ID: {alert_id}")

            # Use centralized routing (supports dev mode override + whale webhook for smart money)
            webhook_url, webhook_type = self._get_webhook_url("smart_money")

            if not webhook_url:
                self.logger.warning(f"[{alert_id}] Cannot send smart money alert: no webhook URL configured")
                return

            # Create webhook and send
            webhook = DiscordWebhook(url=webhook_url)
            webhook.add_embed(embed)

            # Execute webhook
            response = webhook.execute()

            # Check response status
            if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                self.logger.info(f"[{alert_id}] Smart money Discord alert sent to {webhook_type} webhook for {symbol}: {event_type}")
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
            else:
                self.logger.warning(f"[{alert_id}] Failed to send smart money Discord alert: {response}")
                
        except Exception as e:
            self.logger.error(f"[{alert_id}] Error sending smart money Discord alert: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def _send_whale_activity_discord_alert(self, alert: Dict[str, Any], alert_id: str) -> None:
        """Send whale activity alert with improved formatting.
        
        Args:
            alert: Alert data containing whale activity information
            alert_id: Unique alert identifier for tracking
        """
        try:
            details = alert.get('details', {})
            whale_data = details.get('data', {})
            
            # Prepare data for formatter
            formatter_data = {
                'symbol': details.get('symbol', 'Unknown'),
                'subtype': details.get('subtype', 'activity'),
                'whale_trades': whale_data.get('whale_trades', []),
                'large_orders': whale_data.get('large_orders', []),
                'net_usd_value': whale_data.get('net_usd_value', 0),
                'current_price': whale_data.get('current_price', details.get('price', 0)),
                'signal_strength': whale_data.get('signal_strength', 'UNKNOWN'),
                'alert_id': alert_id,
                'whale_bid_orders': whale_data.get('whale_bid_orders', 0),
                'whale_ask_orders': whale_data.get('whale_ask_orders', 0),
                'bid_usd': whale_data.get('whale_bid_usd', 0),
                'ask_usd': whale_data.get('whale_ask_usd', 0),
                'imbalance': whale_data.get('imbalance', 0)
            }
            
            # Use the improved formatter
            embed_data = self.alert_formatter.format_whale_alert(formatter_data)
            
            # Create Discord embed from formatted data
            embed = DiscordEmbed(
                title=embed_data.get('title', 'Whale Activity Alert'),
                description=embed_data.get('description', ''),
                color=embed_data.get('color', 0x3498db)
            )
            
            # Add timestamp
            if 'timestamp' in embed_data:
                embed.set_timestamp(embed_data['timestamp'])
            else:
                embed.set_timestamp()
            
            # Add fields from formatter
            for field in embed_data.get('fields', []):
                embed.add_embed_field(
                    name=field['name'],
                    value=field['value'],
                    inline=field.get('inline', True)
                )
            
            # Add footer
            if 'footer' in embed_data:
                embed.set_footer(text=embed_data['footer'].get('text', ''))
            else:
                embed.set_footer(text="")

            # Use centralized routing (supports dev mode override + whale webhook)
            webhook_url, webhook_type = self._get_webhook_url("whale_activity")

            if not webhook_url:
                self.logger.warning(f"[ALERT:{alert_id}] Cannot send whale activity alert: no webhook URL configured")
                return

            # Send Discord webhook
            webhook = DiscordWebhook(url=webhook_url)
            webhook.add_embed(embed)

            # Retry logic with exponential backoff
            max_retries = self.webhook_max_retries
            retry_delay = self.webhook_initial_retry_delay
            response = None

            self.logger.debug(f"[ALERT:{alert_id}] Routing whale activity alert to {webhook_type} webhook")
            
            for attempt in range(max_retries):
                try:
                    response = webhook.execute()
                    
                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"[ALERT:{alert_id}] Whale activity Discord alert sent successfully")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        return
                    else:
                        status_code = response.status_code if response and hasattr(response, 'status_code') else "N/A"
                        self.logger.warning(f"[ALERT:{alert_id}] Failed whale activity alert (attempt {attempt+1}/{max_retries}): Status {status_code}")
                        
                except Exception as e:
                    self.logger.warning(f"[ALERT:{alert_id}] Error sending whale activity alert (attempt {attempt+1}/{max_retries}): {str(e)}")
                    
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            
            # If all retries failed, log error
            self.logger.error(f"[ALERT:{alert_id}] Failed to send whale activity Discord alert after all retries")
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1
            
        except Exception as e:
            self.logger.error(f"[ALERT:{alert_id}] Error in _send_whale_activity_discord_alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

    async def _send_whale_trade_discord_alert(self, alert: Dict[str, Any], alert_id: str) -> None:
        """Send whale trade execution alert to dedicated whale webhook if configured, otherwise main webhook.

        Args:
            alert: Alert data containing whale trade execution information
            alert_id: Unique alert identifier for tracking
        """
        try:
            # Use centralized routing (supports dev mode override)
            webhook_url, webhook_type = self._get_webhook_url("whale_trade")

            if not webhook_url:
                self.logger.warning(f"[ALERT:{alert_id}] Cannot send whale trade alert: no webhook URL configured")
                return

            self.logger.info(f"[ALERT:{alert_id}] Routing whale trade alert to {webhook_type} webhook")

            details = alert.get('details', {})
            whale_data = details.get('data', {})
            level = alert.get('level', 'warning')
            symbol = details.get('symbol', 'Unknown')
            threshold = whale_data.get('alert_threshold_usd', 750000)

            # Extract key data
            direction = whale_data.get('direction', 'UNKNOWN').upper()
            largest_trade_usd = whale_data.get('largest_trade_usd', 0)
            largest_trade_side = whale_data.get('largest_trade_side', 'UNKNOWN').upper()
            net_usd = abs(whale_data.get('net_usd', 0))
            total_trades = whale_data.get('total_whale_trades', 0)
            priority = details.get('priority', 'WHALE')

            # Format value helper
            def format_value(value: float) -> str:
                if value >= 1_000_000:
                    return f"${value/1_000_000:.2f}M"
                elif value >= 1_000:
                    return f"${value/1_000:.0f}K"
                return f"${value:,.0f}"

            # Color based on direction
            if direction == 'BUY':
                color = 0x00d26a  # Vibrant green
                direction_emoji = "📈"
                action_word = "ACCUMULATION"
            elif direction == 'SELL':
                color = 0xff4757  # Vibrant red
                direction_emoji = "📉"
                action_word = "DISTRIBUTION"
            else:
                color = 0xffa502  # Orange for mixed
                direction_emoji = "📊"
                action_word = "MIXED FLOW"

            # Calculate magnitude tier and visual bar
            mega_threshold = 1_500_000  # $1.5M for mega whale
            large_threshold = 1_000_000  # $1M for large whale

            if largest_trade_usd >= mega_threshold:
                magnitude_tier = "🔱 MEGA WHALE"
                tier_color = "legendary"
            elif largest_trade_usd >= large_threshold:
                magnitude_tier = "🐳 LARGE WHALE"
                tier_color = "epic"
            else:
                magnitude_tier = "🐋 WHALE"
                tier_color = "rare"

            # Visual magnitude bar (relative to mega threshold)
            bar_percentage = min(largest_trade_usd / mega_threshold, 1.0)
            filled_blocks = int(bar_percentage * 10)
            empty_blocks = 10 - filled_blocks
            magnitude_bar = "█" * filled_blocks + "░" * empty_blocks

            # Build premium title
            base_symbol = symbol.replace('USDT', '').replace('USD', '')
            title = f"{direction_emoji}  {base_symbol} {action_word}"

            # Build structured description
            description_lines = [
                f"```",
                f"{'─' * 32}",
                f"  TRADE SIZE     {format_value(largest_trade_usd):>14}",
                f"  {magnitude_bar}  {int(bar_percentage * 100)}%",
                f"{'─' * 32}",
                f"```",
            ]
            description = "\n".join(description_lines)

            # Create embed
            embed = DiscordEmbed(
                title=title,
                description=description,
                color=color
            )

            # Add fields in a clean 2-column layout
            embed.add_embed_field(name="Direction", value=f"`{largest_trade_side}`", inline=True)
            embed.add_embed_field(name="Classification", value=magnitude_tier, inline=True)

            # Net flow field (especially useful for multiple trades)
            if total_trades > 1:
                embed.add_embed_field(name="Net Flow", value=f"`{format_value(net_usd)}` ({total_trades} trades)", inline=True)
            else:
                embed.add_embed_field(name="Pair", value=f"`{symbol}`", inline=True)

            # Add timestamp
            embed.set_timestamp()

            # Footer with context
            embed.set_footer(text=f"Threshold: {format_value(threshold)} │ ID: {alert_id[:8]}")

            # Send to appropriate webhook
            webhook = DiscordWebhook(url=webhook_url)
            webhook.add_embed(embed)

            # Retry logic
            max_retries = self.webhook_max_retries
            retry_delay = self.webhook_initial_retry_delay

            self.logger.debug(f"[ALERT:{alert_id}] Attempting to send whale trade alert to {webhook_type} webhook")

            for attempt in range(max_retries):
                try:
                    response = webhook.execute()

                    if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                        self.logger.info(f"[ALERT:{alert_id}] ✅ Whale trade alert sent successfully to {webhook_type} webhook")
                        self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
                        return
                    else:
                        status_code = response.status_code if response and hasattr(response, 'status_code') else "N/A"
                        self.logger.warning(f"[ALERT:{alert_id}] Failed whale trade alert to {webhook_type} webhook (attempt {attempt+1}/{max_retries}): Status {status_code}")

                except Exception as e:
                    self.logger.warning(f"[ALERT:{alert_id}] Whale trade alert send attempt {attempt+1}/{max_retries} failed: {str(e)}")

                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= self.webhook_exponential_backoff_multiplier

            self.logger.error(f"[ALERT:{alert_id}] ❌ Failed to send whale trade alert to {webhook_type} webhook after {max_retries} attempts")
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

        except Exception as e:
            self.logger.error(f"[ALERT:{alert_id}] Error in _send_whale_trade_discord_alert: {str(e)}")
            self.logger.error(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

    def _get_webhook_url(self, alert_type: str) -> tuple:
        """Centralized webhook routing for Discord alerts.

        This method provides a single source of truth for webhook URL selection,
        ensuring consistent routing behavior across all alert types.

        Routing Priority:
            1. Dedicated webhook (if configured) → type-specific webhook
            2. Main webhook (fallback) → DISCORD_WEBHOOK_URL

        Args:
            alert_type: Type of alert. Supported types:
                - 'liquidation': Routes to liquidation webhook
                - 'whale', 'whale_trade', 'whale_activity': Routes to whale webhook
                - 'smart_money': Routes to whale webhook (related alerts)
                - 'predictive': Routes to predictive webhook (predictive liquidation alerts)
                - 'system': Routes to system webhook
                - 'alpha': Routes to main webhook (alpha detection alerts)
                - 'manipulation': Routes to main webhook (market manipulation alerts)
                - 'large_order': Routes to main webhook (large order alerts)
                - 'general': Routes to main webhook (generic alerts)
                - Any other type: Routes to main webhook (fallback)

        Returns:
            tuple: (webhook_url, webhook_type_description)

        Note:
            Development webhook (DEVELOPMENT_WEBHOOK_URL) is available for manual testing
            but does NOT auto-intercept alerts. Use it explicitly when testing new features.
        """
        # Dedicated webhooks by alert type
        if alert_type == "liquidation" and self.liquidation_webhook_url:
            return self.liquidation_webhook_url, "dedicated liquidation"
        elif alert_type in ("whale", "whale_trade", "whale_activity") and self.whale_webhook_url:
            return self.whale_webhook_url, "dedicated whale"
        elif alert_type == "smart_money" and self.whale_webhook_url:
            return self.whale_webhook_url, "dedicated whale (smart money)"
        elif alert_type == "predictive" and self.predictive_webhook_url:
            return self.predictive_webhook_url, "dedicated predictive"
        elif alert_type == "system" and self.system_webhook_url:
            return self.system_webhook_url, "dedicated system"

        # Priority 3: Main webhook fallback
        return self.discord_webhook_url, "main"

    async def _send_discord_embed(self, embed: DiscordEmbed, alert_type: str = "liquidation") -> None:
        """Send a Discord embed to the appropriate webhook based on alert type.

        Args:
            embed: Discord embed object to send
            alert_type: Type of alert ('liquidation', 'whale', 'main') determines which webhook to use
        """
        try:
            # Use centralized routing
            webhook_url, webhook_type = self._get_webhook_url(alert_type)

            if not webhook_url:
                self.logger.warning(f"Cannot send {alert_type} embed: no webhook URL configured")
                return

            self.logger.debug(f"Sending {alert_type} embed to {webhook_type} webhook")

            # Create and execute webhook
            webhook = DiscordWebhook(url=webhook_url)
            webhook.add_embed(embed)
            response = webhook.execute()

            if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                self.logger.info(f"✅ {alert_type.capitalize()} embed sent to {webhook_type} webhook")
                self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1
            else:
                status_code = response.status_code if response and hasattr(response, 'status_code') else "N/A"
                self.logger.warning(f"Failed to send {alert_type} embed to {webhook_type} webhook: Status {status_code}")
                self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

        except Exception as e:
            self.logger.error(f"Error sending {alert_type} Discord embed: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1

    async def _send_system_webhook_alert(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Send alert to system webhook for monitoring."""
        # Use centralized routing (supports dev mode override)
        webhook_url, webhook_type = self._get_webhook_url("system")

        if not webhook_url:
            self.logger.debug("No webhook URL configured for system alert, skipping")
            return

        # Check if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.logger.error("❌ ERROR: _send_system_webhook_alert called outside of async context")
            return

        try:
            # Discord webhook expects "content" field, not "text"
            payload = {
                "content": message[:2000],  # Discord has a 2000 character limit
                "username": "Virtuoso System Alerts"
            }

            # If we have details, add them as an embed
            if details:
                embed = {
                    "title": "Alert Details",
                    "fields": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "color": 16776960  # Yellow color for system alerts
                }

                # Add details as fields (limit to first 25 due to Discord limits)
                for key, value in list(details.items())[:25]:
                    if key not in ['timestamp', 'source']:  # Skip redundant fields
                        embed["fields"].append({
                            "name": str(key).replace('_', ' ').title()[:256],
                            "value": str(value)[:1024],
                            "inline": True
                        })

                payload["embeds"] = [embed]

            self.logger.debug(f"Routing system alert to {webhook_type} webhook...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 204]:  # Discord returns 204 for successful webhook posts
                        self.logger.debug("System webhook alert sent successfully")
                    else:
                        response_text = await response.text()
                        self.logger.warning(f"System webhook failed with status {response.status}: {response_text[:200]}")
                        
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            error_msg = str(e) if str(e) else repr(e)
            error_type = type(e).__name__
            self.logger.error(f"❌ ERROR: Error sending system webhook alert - {error_type}: {error_msg}")
            if hasattr(e, '__cause__') and e.__cause__:
                self.logger.error(f"  Caused by: {type(e.__cause__).__name__}: {str(e.__cause__)}")
            import traceback
            self.logger.debug(f"  Traceback: {traceback.format_exc()}")

    # Enhanced whale alert helper methods
    def _calculate_volume_multiple(self, usd_value: float) -> str:
        """Calculate volume multiple compared to normal whale activity."""
        # Base threshold for normal whale activity (configurable)
        base_whale_threshold = 1000000  # $1M base
        
        if usd_value >= base_whale_threshold * 5:
            return "5.0x+ above normal"
        elif usd_value >= base_whale_threshold * 3:
            return "3.0x+ above normal"
        elif usd_value >= base_whale_threshold * 2:
            return "2.0x+ above normal"
        elif usd_value >= base_whale_threshold * 1.5:
            return "1.5x above normal"
        else:
            return "Normal level"

    def _calculate_liquidity_stress(self, total_orders: int, imbalance: float) -> str:
        """Calculate market liquidity stress level."""
        # Combine order count and imbalance to assess liquidity stress
        order_stress = min(total_orders / 20.0, 1.0)  # Normalize to 0-1
        imbalance_stress = abs(imbalance)
        
        combined_stress = (order_stress * 0.4) + (imbalance_stress * 0.6)
        
        if combined_stress > 0.7:
            return "HIGH"
        elif combined_stress > 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def _get_market_session(self) -> str:
        """Determine current market session based on UTC time."""
        import datetime
        utc_hour = datetime.datetime.now(timezone.utc).hour
        
        # Market sessions (UTC):
        # Asian: 00:00-09:00 UTC
        # European: 07:00-16:00 UTC  
        # US: 13:00-22:00 UTC
        
        if 0 <= utc_hour < 7:
            return "Asian (Lower liquidity)"
        elif 7 <= utc_hour < 13:
            return "European overlap"
        elif 13 <= utc_hour < 16:
            return "US-EU overlap (High liquidity)"
        elif 16 <= utc_hour < 22:
            return "US session"
        else:
            return "Asian session"

    def _assess_volatility_context(self) -> str:
        """Assess current volatility context."""
        # This could be enhanced with actual volatility calculations
        # For now, return a basic assessment
        import datetime
        current_hour = datetime.datetime.now(timezone.utc).hour
        
        # Higher volatility during session opens and closes
        if current_hour in [0, 1, 7, 8, 13, 14, 22, 23]:
            return "Elevated (session transition)"
        elif 13 <= current_hour <= 16:
            return "High (overlapping sessions)"
        else:
            return "Normal"

    def _calculate_execution_efficiency(self, trades_count: int, orders_count: int) -> str:
        """Calculate whale execution efficiency."""
        if orders_count == 0:
            return "N/A"
        
        efficiency_ratio = trades_count / orders_count if orders_count > 0 else 0
        
        if efficiency_ratio > 0.5:
            return "High"
        elif efficiency_ratio > 0.2:
            return "Medium"
        elif efficiency_ratio > 0:
            return "Low"
        else:
            return "None"

    def _get_liquidity_note(self, stress_level: str) -> str:
        """Get explanatory note for liquidity stress level."""
        if stress_level == "HIGH":
            return "significant slippage risk"
        elif stress_level == "MEDIUM":
            return "moderate slippage expected"
        else:
            return "normal execution conditions"

    def _calculate_signal_confidence(self, signal_strength: str, trade_confirmation: bool) -> int:
        """Calculate confidence percentage for signal strength."""
        base_confidence = {
            "POSITIONING": 60,
            "EXECUTING": 75,
            "CONFIRMED": 90,
            "CONFLICTING": 30
        }
        
        confidence = base_confidence.get(signal_strength, 50)
        
        # Adjust based on trade confirmation
        if trade_confirmation and signal_strength != "CONFLICTING":
            confidence = min(confidence + 10, 95)
        elif not trade_confirmation and signal_strength != "POSITIONING":
            confidence = max(confidence - 15, 25)
            
        return confidence

    def _analyze_historical_patterns(self, symbol: str, subtype: str, usd_value: float) -> str:
        """Analyze historical patterns for context."""
        # This could be enhanced with actual historical analysis
        # For now, provide basic pattern insights

        if usd_value > 10000000:  # > $10M
            return f"Pattern: Large {subtype} - historically leads to 2-5% moves"
        elif usd_value > 5000000:  # > $5M
            return f"Pattern: Significant {subtype} - typically 1-3% impact"
        else:
            return f"Pattern: Moderate {subtype} - usually 0.5-1.5% movement"

    # ========================================================================
    # QUICK WIN #1: Open Interest Context
    # ========================================================================

    def _track_oi_change(self, symbol: str, oi_value: float) -> None:
        """Track Open Interest changes over time.

        Args:
            symbol: Trading pair symbol
            oi_value: Current Open Interest value
        """
        current_time = time.time()

        if symbol not in self._oi_history:
            self._oi_history[symbol] = deque(maxlen=self._oi_history_limit)

        self._oi_history[symbol].append((current_time, oi_value))

    def _calculate_oi_change(self, symbol: str, current_oi: float, timeframe: int = 900) -> Optional[float]:
        """Calculate Open Interest percentage change over timeframe.

        Args:
            symbol: Trading pair symbol
            current_oi: Current OI value
            timeframe: Lookback period in seconds (default 15 min)

        Returns:
            Percentage change or None if insufficient data
        """
        if symbol not in self._oi_history or not self._oi_history[symbol]:
            return None

        current_time = time.time()
        cutoff_time = current_time - timeframe

        # Find oldest OI value within timeframe
        for timestamp, oi_value in self._oi_history[symbol]:
            if timestamp >= cutoff_time:
                if oi_value > 0:
                    change = (current_oi - oi_value) / oi_value
                    return change
                break

        return None

    def _get_oi_context(self, symbol: str, current_oi: float) -> str:
        """Generate Open Interest context string for alerts.

        Args:
            symbol: Trading pair symbol
            current_oi: Current OI value

        Returns:
            Formatted OI context string or empty string
        """
        oi_change = self._calculate_oi_change(symbol, current_oi, timeframe=900)  # 15 min

        if oi_change is None:
            return ""

        if abs(oi_change) < 0.02:  # Less than 2% change
            return ""

        # Format context based on change magnitude
        oi_pct = oi_change * 100
        if oi_change > 0:
            action = "building" if oi_change > 0.05 else "increasing"
            interpretation = f"📊 **OI Change:** +{oi_pct:.1f}% ({action} positions - potential trend continuation)"
        else:
            action = "closing rapidly" if oi_change < -0.05 else "decreasing"
            interpretation = f"📊 **OI Change:** {oi_pct:.1f}% ({action} positions - trend exhaustion signal)"

        return f"\n{interpretation}"

    # ========================================================================
    # QUICK WIN #2: Liquidation Correlation
    # ========================================================================

    def _check_liquidation_correlation(self, symbol: str, timeframe: int = 300) -> Optional[Dict[str, Any]]:
        """Check for recent liquidations that may indicate manipulation.

        Args:
            symbol: Trading pair symbol
            timeframe: Lookback period in seconds (default 5 min)

        Returns:
            Liquidation correlation data or None
        """
        if not self.liquidation_cache:
            return None

        try:
            # Get recent liquidations from LiquidationDataCollector
            # API signature: get_recent_liquidations(symbol, exchange=None, minutes=60)
            minutes = int(timeframe / 60)  # Convert seconds to minutes

            if hasattr(self.liquidation_cache, 'get_recent_liquidations'):
                recent_liqs = self.liquidation_cache.get_recent_liquidations(
                    symbol=symbol,
                    exchange=None,  # Search all exchanges
                    minutes=minutes
                )
            else:
                return None

            if not recent_liqs or len(recent_liqs) == 0:
                return None

            # Calculate liquidation metrics
            total_liq_volume = 0
            long_liqs = 0
            short_liqs = 0

            for liq in recent_liqs:
                # LiquidationEvent has specific attributes (not size/price/side)
                # Get liquidated_amount_usd directly
                liquidated_usd = float(getattr(liq, 'liquidated_amount_usd', 0))

                # If liquidated_amount_usd not available, calculate from trigger_price
                if liquidated_usd == 0:
                    trigger_price = float(getattr(liq, 'trigger_price', 0))
                    # Try to estimate size if available
                    size = float(getattr(liq, 'size', 0))
                    if size > 0 and trigger_price > 0:
                        liquidated_usd = size * trigger_price

                total_liq_volume += liquidated_usd

                # Determine if long or short liquidation from liquidation_type
                liq_type = str(getattr(liq, 'liquidation_type', ''))
                if 'LONG' in liq_type.upper():
                    long_liqs += 1
                elif 'SHORT' in liq_type.upper():
                    short_liqs += 1
                else:
                    # Fallback: try side attribute (for backward compatibility)
                    side = str(getattr(liq, 'side', '')).lower()
                    if side == 'buy':  # Long liquidation
                        long_liqs += 1
                    elif side == 'sell':  # Short liquidation
                        short_liqs += 1

            # Only report if significant liquidations occurred
            if total_liq_volume < 1_000_000:  # Less than $1M
                return None

            return {
                'liquidation_spike': True,
                'volume_usd': total_liq_volume,
                'count': len(recent_liqs),
                'long_liquidations': long_liqs,
                'short_liquidations': short_liqs,
                'timeframe_min': timeframe / 60
            }

        except Exception as e:
            self.logger.debug(f"Error checking liquidation correlation: {e}")
            return None

    def _get_liquidation_context(self, symbol: str) -> str:
        """Generate liquidation context string for alerts.

        Args:
            symbol: Trading pair symbol

        Returns:
            Formatted liquidation context string or empty string
        """
        liq_data = self._check_liquidation_correlation(symbol, timeframe=300)

        if not liq_data:
            return ""

        volume = liq_data['volume_usd']
        count = liq_data['count']
        long_liqs = liq_data['long_liquidations']
        short_liqs = liq_data['short_liquidations']
        timeframe = liq_data['timeframe_min']

        # Determine predominant side
        if long_liqs > short_liqs * 2:
            side_info = f"mostly LONG positions ({long_liqs}/{count})"
            manipulation_hint = "possible LONG SQUEEZE"
        elif short_liqs > long_liqs * 2:
            side_info = f"mostly SHORT positions ({short_liqs}/{count})"
            manipulation_hint = "possible SHORT SQUEEZE"
        else:
            side_info = f"{long_liqs} longs, {short_liqs} shorts"
            manipulation_hint = "cascade event"

        # Format volume
        if volume >= 1_000_000:
            volume_str = f"${volume/1_000_000:.1f}M"
        else:
            volume_str = f"${volume/1_000:.0f}K"

        interpretation = (
            f"🔥 **Liquidation Spike:** {volume_str} across {count} traders in {timeframe:.0f} min\n"
            f"   └─ {side_info} - {manipulation_hint}"
        )

        return f"\n{interpretation}"

    # ========================================================================
    # QUICK WIN #3: Long/Short Ratio Warnings
    # ========================================================================

    def _get_lsr_warning(self, lsr_value: float) -> str:
        """Generate Long/Short Ratio warning string.

        Args:
            lsr_value: Long/Short Ratio (e.g., 2.0 = 67% long)

        Returns:
            Formatted LSR warning string or empty string
        """
        if lsr_value is None:
            return ""

        # Calculate percentages
        long_pct = (lsr_value / (1 + lsr_value)) * 100
        short_pct = 100 - long_pct

        # Generate warnings for crowded positions (> 65% on one side)
        if long_pct > 65:
            emoji = "⚠️"
            if long_pct > 75:
                risk_level = "EXTREME"
                emoji = "🚨"
            elif long_pct > 70:
                risk_level = "HIGH"
            else:
                risk_level = "MODERATE"

            warning = (
                f"{emoji} **Crowd Position:** {long_pct:.0f}% LONG ({risk_level} squeeze risk)\n"
                f"   └─ Over-leveraged longs vulnerable to stop hunts & liquidation cascades"
            )
            return f"\n{warning}"

        elif short_pct > 65:
            emoji = "⚠️"
            if short_pct > 75:
                risk_level = "EXTREME"
                emoji = "🚨"
            elif short_pct > 70:
                risk_level = "HIGH"
            else:
                risk_level = "MODERATE"

            warning = (
                f"{emoji} **Crowd Position:** {short_pct:.0f}% SHORT ({risk_level} squeeze risk)\n"
                f"   └─ Over-leveraged shorts vulnerable to pumps & forced covering"
            )
            return f"\n{warning}"

        return ""

    def _generate_plain_english_interpretation(self, signal_strength: str, subtype: str, symbol: str,
                                             usd_value: float, trades_count: int, buy_volume: float,
                                             sell_volume: float, signal_context: str,
                                             market_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate plain English interpretation of the whale activity with enhanced context.

        Args:
            signal_strength: Signal classification (EXECUTING/CONFLICTING)
            subtype: accumulation or distribution
            symbol: Trading pair
            usd_value: USD volume
            trades_count: Number of trades
            buy_volume: Buy volume
            sell_volume: Sell volume
            signal_context: Context string
            market_data: Optional market data for enhanced context (OI, liquidations, LSR)

        Returns:
            Enhanced interpretation string with market context
        """

        # Volume size context
        if usd_value > 10000000:
            size_context = "massive"
        elif usd_value > 5000000:
            size_context = "large"
        elif usd_value > 2000000:
            size_context = "significant"
        else:
            size_context = "moderate"
        
        if signal_strength == "EXECUTING":
            if subtype == "accumulation":
                interpretation = (
                    f"A whale is actively buying {symbol} with {size_context} volume. "
                    f"They've executed {trades_count} buy trades totaling {buy_volume:.0f} units. "
                    f"This suggests strong bullish conviction and potential upward price pressure."
                )
            else:  # distribution
                interpretation = (
                    f"A whale is actively selling {symbol} with {size_context} volume. "
                    f"They've executed {trades_count} sell trades totaling {sell_volume:.0f} units. "
                    f"This suggests bearish sentiment and potential downward price pressure."
                )
        
        elif signal_strength == "CONFLICTING":
            # Calculate manipulation severity based on volume mismatch
            buy_sell_ratio = buy_volume / max(sell_volume, 1)
            volume_mismatch_severity = self._calculate_manipulation_severity(
                abs(usd_value), trades_count, buy_sell_ratio
            )

            if subtype == "accumulation":
                # Order book shows buy orders but actual trades are sells
                interpretation = self._format_manipulation_alert(
                    pattern="FAKE BUY WALL",
                    orderbook_signal="large BUY orders",
                    actual_trades=f"{sell_volume:.0f} SELL trades",
                    manipulation_tactic="spoofing/fake-walling to create false accumulation",
                    whale_action="selling into the fake demand",
                    risk_scenario="Price may drop suddenly when fake orders are pulled",
                    trader_action="DO NOT FOMO BUY",
                    severity=volume_mismatch_severity,
                    volume=abs(usd_value),
                    trade_count=trades_count
                )
            else:  # distribution
                # Order book shows sell orders but actual trades are buys
                interpretation = self._format_manipulation_alert(
                    pattern="FAKE SELL WALL",
                    orderbook_signal="large SELL orders",
                    actual_trades=f"{buy_volume:.0f} BUY trades",
                    manipulation_tactic="spoofing/fake-walling to create false distribution",
                    whale_action="buying the fake dip",
                    risk_scenario="Price may pump suddenly when fake orders are pulled",
                    trader_action="DO NOT PANIC SELL",
                    severity=volume_mismatch_severity,
                    volume=abs(usd_value),
                    trade_count=trades_count
                )

        # ========================================================================
        # QUICK WIN ENHANCEMENTS: Add market context
        # ========================================================================
        enhanced_context = ""

        if market_data:
            # Track and add Open Interest context
            funding_data = market_data.get('funding', {})
            if funding_data:
                current_oi = float(funding_data.get('openInterest', 0))
                if current_oi > 0:
                    self._track_oi_change(symbol, current_oi)
                    oi_context = self._get_oi_context(symbol, current_oi)
                    if oi_context:
                        enhanced_context += oi_context

            # Add liquidation correlation context
            liq_context = self._get_liquidation_context(symbol)
            if liq_context:
                enhanced_context += liq_context

            # Add Long/Short Ratio warning
            lsr_data = market_data.get('long_short_ratio', {})
            if lsr_data:
                lsr_value = lsr_data.get('longShortRatio')
                if lsr_value:
                    lsr_warning = self._get_lsr_warning(float(lsr_value))
                    if lsr_warning:
                        enhanced_context += lsr_warning

        # Append enhanced context if available
        if enhanced_context:
            interpretation += enhanced_context

        return interpretation

    def _calculate_manipulation_severity(self, volume: float, trade_count: int, buy_sell_ratio: float) -> str:
        """
        Calculate manipulation severity based on volume, trade count, and buy/sell ratio.

        Args:
            volume: Total USD volume involved
            trade_count: Number of whale trades
            buy_sell_ratio: Ratio of buy to sell volume (or vice versa)

        Returns:
            Severity level: "EXTREME", "HIGH", "MODERATE", or "LOW"
        """
        try:
            # Input validation: Check for NaN, infinity, and negative values
            if volume is None or math.isnan(volume) or math.isinf(volume):
                self.logger.warning(f"Invalid volume value: {volume}, using 0")
                volume = 0
            if volume < 0:
                self.logger.warning(f"Negative volume value: {volume}, using absolute value")
                volume = abs(volume)

            if trade_count is None or (isinstance(trade_count, float) and (math.isnan(trade_count) or math.isinf(trade_count))):
                self.logger.warning(f"Invalid trade_count value: {trade_count}, using 0")
                trade_count = 0
            if trade_count < 0:
                self.logger.warning(f"Negative trade_count value: {trade_count}, using 0")
                trade_count = 0
            trade_count = int(trade_count)  # Ensure it's an integer

            if buy_sell_ratio is None or math.isnan(buy_sell_ratio) or math.isinf(buy_sell_ratio):
                self.logger.warning(f"Invalid buy_sell_ratio value: {buy_sell_ratio}, using 1.0")
                buy_sell_ratio = 1.0
            if buy_sell_ratio < 0:
                self.logger.warning(f"Negative buy_sell_ratio value: {buy_sell_ratio}, using 1.0")
                buy_sell_ratio = 1.0

            self.logger.debug(f"Calculating manipulation severity: volume=${volume:,.2f}, trades={trade_count}, ratio={buy_sell_ratio:.2f}")

            # Volume-based severity using configuration constants
            vol_thresholds = self.manipulation_thresholds['volume']
            if volume >= vol_thresholds['critical']:
                volume_severity = 4
            elif volume >= vol_thresholds['high']:
                volume_severity = 3
            elif volume >= vol_thresholds['moderate']:
                volume_severity = 2
            else:
                volume_severity = 1

            # Trade count severity (more trades = more coordinated)
            trade_thresholds = self.manipulation_thresholds['trades']
            if trade_count >= trade_thresholds['critical']:
                trade_severity = 4
            elif trade_count >= trade_thresholds['high']:
                trade_severity = 3
            elif trade_count >= trade_thresholds['moderate']:
                trade_severity = 2
            else:
                trade_severity = 1

            # Ratio severity (higher imbalance = more manipulation)
            ratio_thresholds = self.manipulation_thresholds['ratio']
            if buy_sell_ratio >= ratio_thresholds['critical_high'] or buy_sell_ratio <= ratio_thresholds['critical_low']:
                ratio_severity = 4
            elif buy_sell_ratio >= ratio_thresholds['high_high'] or buy_sell_ratio <= ratio_thresholds['high_low']:
                ratio_severity = 3
            elif buy_sell_ratio >= ratio_thresholds['moderate_high'] or buy_sell_ratio <= ratio_thresholds['moderate_low']:
                ratio_severity = 2
            else:
                ratio_severity = 1

            # Calculate weighted average using configuration constants
            weights = self.manipulation_severity_weights
            total_severity = (
                volume_severity * weights['volume'] +
                trade_severity * weights['trades'] +
                ratio_severity * weights['ratio']
            )

            # Determine severity level using configuration thresholds
            score_thresholds = self.manipulation_severity_score_thresholds
            if total_severity >= score_thresholds['extreme']:
                severity = "EXTREME"
            elif total_severity >= score_thresholds['high']:
                severity = "HIGH"
            elif total_severity >= score_thresholds['moderate']:
                severity = "MODERATE"
            else:
                severity = "LOW"

            self.logger.debug(
                f"Severity calculation complete: score={total_severity:.2f}, level={severity} "
                f"(vol_sev={volume_severity}, trade_sev={trade_severity}, ratio_sev={ratio_severity})"
            )

            return severity

        except Exception as e:
            # Safe fallback if calculation fails
            self.logger.error(f"Severity calculation failed with exception: {e}", exc_info=True)
            self.logger.error(f"Input values: volume={volume}, trade_count={trade_count}, buy_sell_ratio={buy_sell_ratio}")
            return "MODERATE"  # Safe fallback severity

    def _format_manipulation_alert(
        self,
        pattern: str,
        orderbook_signal: str,
        actual_trades: str,
        manipulation_tactic: str,
        whale_action: str,
        risk_scenario: str,
        trader_action: str,
        severity: str,
        volume: float,
        trade_count: int
    ) -> str:
        """
        Format a detailed manipulation alert with severity-based messaging.

        Args:
            pattern: Manipulation pattern type (e.g., "FAKE SELL WALL")
            orderbook_signal: What the order book is showing
            actual_trades: What trades are actually happening
            manipulation_tactic: The manipulation technique being used
            whale_action: What whales are actually doing
            risk_scenario: What could happen to price
            trader_action: What traders should NOT do
            severity: Severity level from _calculate_manipulation_severity
            volume: Total volume in USD
            trade_count: Number of trades

        Returns:
            Formatted manipulation alert string
        """
        try:
            # Input validation
            if volume is None or (isinstance(volume, float) and (math.isnan(volume) or math.isinf(volume))):
                self.logger.warning(f"Invalid volume in alert formatting: {volume}, using 0")
                volume = 0
            if volume < 0:
                volume = abs(volume)

            if trade_count is None or (isinstance(trade_count, float) and (math.isnan(trade_count) or math.isinf(trade_count))):
                self.logger.warning(f"Invalid trade_count in alert formatting: {trade_count}, using 0")
                trade_count = 0
            if trade_count < 0:
                trade_count = 0
            trade_count = int(trade_count)

            # Severity-based emoji and risk level
            severity_config = {
                "EXTREME": {"emoji": "🚨🚨🚨", "risk": "CRITICAL", "urgency": "IMMEDIATE ATTENTION REQUIRED"},
                "HIGH": {"emoji": "🚨🚨", "risk": "HIGH", "urgency": "Use extreme caution"},
                "MODERATE": {"emoji": "🚨", "risk": "MODERATE", "urgency": "Exercise caution"},
                "LOW": {"emoji": "⚠️", "risk": "LOW", "urgency": "Be aware"}
            }

            config = severity_config.get(severity, severity_config["MODERATE"])

            # Format volume and trade metrics with safe fallbacks
            try:
                if volume >= 1_000_000:
                    volume_str = f"${volume/1_000_000:.1f}M"
                elif volume >= 1_000:
                    volume_str = f"${volume/1_000:.0f}K"
                else:
                    volume_str = f"${volume:.0f}"
            except Exception as e:
                self.logger.warning(f"Error formatting volume {volume}: {e}")
                volume_str = "$0"

            trade_plural = "trade" if trade_count == 1 else "trades"

            # Build structured alert
            alert_parts = [
                f"{config['emoji']} **{pattern} DETECTED** {config['emoji']}",
                f"",
                f"**Severity:** {severity} ({config['risk']} RISK)",
                f"**Evidence:** {volume_str} across {trade_count} {trade_plural}",
                f"",
                f"**Orderbook Signal:** {orderbook_signal}",
                f"**Actual Trades:** {actual_trades}",
                f"",
                f"**Manipulation Tactic:** {manipulation_tactic}",
                f"**What Whales Are Doing:** {whale_action}",
                f"",
                f"⚠️ **RISK:** {risk_scenario}",
                f"🛑 **ACTION:** {trader_action}",
                f"",
                f"_{config['urgency']}_"
            ]

            return "\n".join(alert_parts)

        except Exception as e:
            # Safe fallback if formatting fails
            self.logger.error(f"Alert formatting failed with exception: {e}", exc_info=True)
            self.logger.error(f"Input values: pattern={pattern}, severity={severity}, volume={volume}, trade_count={trade_count}")
            # Return a basic alert message as fallback
            return (
                f"🚨 **{pattern} DETECTED** 🚨\n\n"
                f"**Severity:** {severity}\n"
                f"**Evidence:** Alert formatting error - see logs\n\n"
                f"**Action:** {trader_action}"
            )

    def _format_whale_trades(self, top_trades: list) -> str:
        """Format the top whale trades for display."""
        if not top_trades:
            return "• No significant trades detected"
        
        formatted_trades = []
        for i, trade in enumerate(top_trades[:3], 1):  # Show top 3 trades
            side = trade['side'].upper()
            side_emoji = "🟢" if side == "BUY" else "🔴"
            size = trade['size']
            price = trade['price']
            value = trade['value']
            
            formatted_trades.append(f"• {side_emoji} {side} {size:.2f} @ ${price:.2f} = ${value:,.0f}")
        
        return "\n".join(formatted_trades)

    def _format_whale_orders(self, top_bids: list, top_asks: list, subtype: str) -> str:
        """Format the top whale orders for display."""
        formatted_orders = []
        
        # Focus on relevant orders based on signal type
        if subtype == "accumulation" and top_bids:
            formatted_orders.append("**🟢 Large Buy Orders:**")
            for i, (price, size, usd_value) in enumerate(top_bids[:3], 1):
                formatted_orders.append(f"• BID {size:.2f} @ ${price:.2f} = ${usd_value:,.0f}")
        
        if subtype == "distribution" and top_asks:
            formatted_orders.append("**🔴 Large Sell Orders:**")
            for i, (price, size, usd_value) in enumerate(top_asks[:3], 1):
                formatted_orders.append(f"• ASK {size:.2f} @ ${price:.2f} = ${usd_value:,.0f}")
        
        # For conflicting signals, show both sides
        if not formatted_orders:
            if top_bids:
                formatted_orders.append("**🟢 Buy Orders:**")
                for price, size, usd_value in top_bids[:2]:
                    formatted_orders.append(f"• BID {size:.2f} @ ${price:.2f} = ${usd_value:,.0f}")
            if top_asks:
                formatted_orders.append("**🔴 Sell Orders:**")
                for price, size, usd_value in top_asks[:2]:
                    formatted_orders.append(f"• ASK {size:.2f} @ ${price:.2f} = ${usd_value:,.0f}")
        
        return "\n".join(formatted_orders) if formatted_orders else "• No large orders detected"



# Trade Parameters Patch for AlertManager
# This patch adds stop loss and take profit calculation to all signals

def add_trade_parameters_to_signal(self, signal_data):
    """Add trade parameters (stop_loss, take_profit, position_size) to signal data."""

    # Skip if trade_params already exist
    if 'trade_params' in signal_data and signal_data['trade_params']:
        return signal_data

    try:
        # Get signal details
        signal_type = signal_data.get('signal_type', 'NEUTRAL')
        price = signal_data.get('price') or signal_data.get('entry_price', 0)
        confluence_score = signal_data.get('confluence_score', 50)
        reliability = signal_data.get('reliability', 0.5)

        # Skip neutral signals
        if signal_type == 'NEUTRAL' or not price:
            return signal_data

        # Use unified stop loss calculator for consistency with trade execution
        try:
            from src.core.risk.stop_loss_calculator import get_stop_loss_calculator, StopLossMethod

            # Initialize stop loss calculator if not already done
            try:
                stop_calc = get_stop_loss_calculator()
            except ValueError:
                # First initialization
                stop_calc = get_stop_loss_calculator(self.config)

            # Get sophisticated stop loss calculation based on confluence score
            stop_info = stop_calc.get_stop_loss_info(signal_data, StopLossMethod.CONFIDENCE_BASED)

            if 'error' in stop_info:
                # Fallback to simple calculation
                risk_config = self.config.get('risk', {})
                stop_loss_pct = risk_config.get('long_stop_percentage', 3.5) if signal_type == 'LONG' else risk_config.get('short_stop_percentage', 3.5)
                stop_loss_pct = stop_loss_pct / 100  # Convert to decimal
            else:
                stop_loss_pct = stop_info['stop_loss_percentage']

        except ImportError:
            # Fallback if unified calculator not available
            risk_config = self.config.get('risk', {})
            stop_loss_pct = risk_config.get('long_stop_percentage', 3.5) if signal_type == 'LONG' else risk_config.get('short_stop_percentage', 3.5)
            stop_loss_pct = stop_loss_pct / 100  # Convert to decimal

        # Calculate take profit based on risk/reward ratio
        risk_config = self.config.get('risk', {})
        risk_reward_ratio = risk_config.get('risk_reward_ratio', 2.0)
        take_profit_pct = risk_reward_ratio * stop_loss_pct

        if signal_type == 'LONG':
            stop_loss = price * (1 - stop_loss_pct)
            take_profit = price * (1 + take_profit_pct)
        elif signal_type == 'SHORT':
            stop_loss = price * (1 + stop_loss_pct)
            take_profit = price * (1 - take_profit_pct)
        else:
            return signal_data

        # Calculate position size (simplified)
        account_balance = risk_config.get('account_balance', 10000)  # Default account balance from config
        default_risk_pct = risk_config.get('default_risk_percentage', 2.0)  # Risk percentage from config
        risk_amount = account_balance * (default_risk_pct / 100)
        stop_distance = abs(price - stop_loss)
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0

        # Calculate multiple target levels for partial exits (TP1, TP2, TP3)
        targets = []
        if signal_type == 'LONG':
            # Target 1: 1.5R (30% position)
            tp1 = price * (1 + (stop_loss_pct * 1.5))
            targets.append({'price': round(tp1, 8), 'size': 30, 'name': 'Target 1'})
            # Target 2: 2.5R (30% position)
            tp2 = price * (1 + (stop_loss_pct * 2.5))
            targets.append({'price': round(tp2, 8), 'size': 30, 'name': 'Target 2'})
            # Target 3: 3.5R (40% position - let winners run)
            tp3 = price * (1 + (stop_loss_pct * 3.5))
            targets.append({'price': round(tp3, 8), 'size': 40, 'name': 'Target 3'})
        else:  # SHORT
            # Target 1: 1.5R (30% position)
            tp1 = price * (1 - (stop_loss_pct * 1.5))
            targets.append({'price': round(tp1, 8), 'size': 30, 'name': 'Target 1'})
            # Target 2: 2.5R (30% position)
            tp2 = price * (1 - (stop_loss_pct * 2.5))
            targets.append({'price': round(tp2, 8), 'size': 30, 'name': 'Target 2'})
            # Target 3: 3.5R (40% position - let winners run)
            tp3 = price * (1 - (stop_loss_pct * 3.5))
            targets.append({'price': round(tp3, 8), 'size': 40, 'name': 'Target 3'})

        # Add trade parameters
        signal_data['trade_params'] = {
            'entry_price': price,
            'stop_loss': round(stop_loss, 8),
            'take_profit': round(take_profit, 8),
            'targets': targets,  # Multiple target levels
            'position_size': round(position_size, 8),
            'risk_reward_ratio': 2.0,
            'risk_percentage': 2.0,
            'confidence': min(confluence_score / 100, 1.0) if confluence_score else 0.5
        }

        # Also add at root level for backward compatibility
        signal_data['stop_loss'] = round(stop_loss, 8)
        signal_data['take_profit'] = round(take_profit, 8)
        signal_data['targets'] = targets  # Add targets at root level too

        self.logger.debug(f"Added trade parameters to {signal_type} signal for {signal_data.get('symbol')}")

    except Exception as e:
        self.logger.error(f"Error adding trade parameters: {str(e)}")

    return signal_data

# Monkey-patch the method
AlertManager.add_trade_parameters_to_signal = add_trade_parameters_to_signal

# Wrap the original send_signal_alert method
original_send_signal_alert = AlertManager.send_signal_alert

async def patched_send_signal_alert(self, signal_data):
    """Patched send_signal_alert that adds trade parameters."""
    # Add trade parameters before sending
    signal_data = self.add_trade_parameters_to_signal(signal_data)
    # Call original method with self
    return await original_send_signal_alert(self, signal_data)

# Apply the patch
AlertManager.send_signal_alert = patched_send_signal_alert

print("✅ Trade parameters patch applied to AlertManager")
