"""Bybit exchange implementation with CCXT standardization."""

import asyncio
import logging
import json
import hmac
import hashlib
import time
import os
import random
from typing import Dict, Any, List, Optional, Callable, Tuple, ContextManager, Union
from datetime import datetime
import aiohttp
import websockets
from urllib.parse import urlencode
from pybit.unified_trading import HTTP 
from contextlib import contextmanager
from dataclasses import dataclass, field
from src.core.error.models import ErrorSeverity
import pandas as pd
import traceback
from dotenv import load_dotenv
import numpy as np
import re
from collections import defaultdict
from src.core.base_component import BaseComponent

# Load environment variables from .env file
load_dotenv()

from .base import (
    BaseExchange,
    ExchangeError,
    NetworkError,
    TimeoutError,
    AuthenticationError,
    retry_on_error,
    handle_timeout,
    RateLimitError  # Added import
)

logger = logging.getLogger(__name__)

@dataclass
class ErrorContext:
    """Context for error handling"""
    operation: str
    details: Dict[str, Any] = None
    component: str = None
    exchange: str = 'bybit'  # Set default value
    timestamp: float = field(default_factory=time.time)
    error_code: Optional[str] = None
    retry_count: int = 0

class BybitExchangeError(ExchangeError):
    """Bybit-specific exchange error"""
    pass

class InitializationError(ExchangeError):
    """Error during exchange initialization"""
    pass

class BybitExchange(BaseExchange):
    """Bybit exchange implementation with CCXT standardization"""
    
    # Class-level initialization tracking
    _instances: Dict[str, 'BybitExchange'] = {}
    _instance_lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls, config: Dict[str, Any], error_handler: Optional[Any] = None) -> 'BybitExchange':
        """Get or create a singleton instance of BybitExchange.
        
        Args:
            config: Configuration dictionary
            error_handler: Optional error handler
            
        Returns:
            BybitExchange instance
        """
        # Use API endpoint as unique key for different environments
        instance_key = config['exchanges']['bybit']['rest_endpoint']
        
        async with cls._instance_lock:
            if instance_key not in cls._instances:
                instance = cls(config, error_handler)
                cls._instances[instance_key] = instance
                # Initialize the instance
                if not await instance.initialize():
                    logger.error("Failed to initialize BybitExchange instance")
                    del cls._instances[instance_key]
                    raise RuntimeError("Failed to initialize BybitExchange")
            return cls._instances[instance_key]
    
    ERROR_CODES = {
        '10001': 'System error',
        '10002': 'System not available',
        '10003': 'Invalid request',
        '10004': 'Invalid parameter',
        '10005': 'Operation failed',
        '10006': 'Too many requests',
        '10007': 'Authentication required',
        '10008': 'Invalid API key',
        '10009': 'Invalid signature',
    }
    
    WS_ENDPOINTS = {
        'spot': {
            'public': 'wss://stream.bybit.com/v5/public/spot',
            'private': 'wss://stream.bybit.com/v5/private'
        },
        'linear': {
            'public': 'wss://stream.bybit.com/v5/public/linear',
            'private': 'wss://stream.bybit.com/v5/private'
        },
        'inverse': {
            'public': 'wss://stream.bybit.com/v5/public/inverse',
            'private': 'wss://stream.bybit.com/v5/private'
        }
    }
    
    TIMEFRAME_MAP = {
        '1m': '1',
        '3m': '3',
        '5m': '5',
        '15m': '15',
        '30m': '30',
        '1h': '60',
        '2h': '120',
        '4h': '240',
        '6h': '360',
        '12h': '720',
        '1d': 'D',
        '1w': 'W',
        '1M': 'M'
    }
    
    # Add reverse mapping
    _reverse_timeframe_map = {v: k for k, v in TIMEFRAME_MAP.items()}
    
    # Add rate limit constants
    RATE_LIMITS = {
        'category': {
            'linear': {'requests': 120, 'per_second': 1},  # Category-level limit
            'spot': {'requests': 120, 'per_second': 1}
        },
        'endpoints': {
            'kline': {'requests': 120, 'per_second': 1},
            'orderbook': {'requests': 60, 'per_second': 1},
            'trades': {'requests': 60, 'per_second': 1},
            'ticker': {'requests': 60, 'per_second': 1},
            'market_data': {'requests': 120, 'per_second': 1},  # Composite limit
            'long_short_ratio': {'requests': 60, 'per_second': 1},  # New endpoint
            'risk_limits': {'requests': 60, 'per_second': 1},  # New endpoint
            # Add endpoint aliases to fix KeyError issues
            'lsr': {'requests': 60, 'per_second': 1},  # Alias for long_short_ratio
            'ohlcv': {'requests': 120, 'per_second': 1},  # Alias for kline
            'oi_history': {'requests': 60, 'per_second': 1},  # Open interest history
            'volatility': {'requests': 60, 'per_second': 1}  # Historical volatility calculations
        }
    }
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """Initialize Bybit exchange."""
        # Call parent init with both arguments
        super().__init__(config, error_handler)
        
        # Extract exchange specific config
        self.exchange_config = config['exchanges']['bybit']
        
        # Load environment variables first
        load_dotenv()
        
        # Set testnet mode - check environment variable first, then config file
        testnet_env = os.getenv('BYBIT_TESTNET', '').lower() in ('true', '1', 'yes')
        self.testnet = testnet_env or self.exchange_config.get('testnet', False)
        
        # Initialize rate limits
        self.rate_limits = self.RATE_LIMITS.copy()
        
        # Track rate limit status from response headers
        self.rate_limit_status = {
            'remaining': 600,
            'limit': 600,
            'reset_timestamp': None
        }
        
        # Initialize rate limit tracking
        self._rate_limit_timestamps = {}
        
        # Set endpoints based on testnet mode
        if self.testnet:
            self.rest_endpoint = self.exchange_config.get('testnet_endpoint', 'https://api-testnet.bybit.com')
            self.ws_endpoint = self.exchange_config['websocket'].get('testnet_endpoint', 'wss://stream-testnet.bybit.com/v5/public')
        else:
            self.rest_endpoint = self.exchange_config.get('rest_endpoint', 'https://api.bybit.com')
            self.ws_endpoint = self.exchange_config['websocket'].get('mainnet_endpoint', 'wss://stream.bybit.com/v5/public')
        
        # Set api_url to the same value as rest_endpoint
        self.api_url = self.rest_endpoint
            
        # Load API credentials from environment variables
        self.api_key = os.getenv('BYBIT_API_KEY')
        self.api_secret = os.getenv('BYBIT_API_SECRET')
        
        # Log API key status
        self.logger = logging.getLogger(__name__)
        self.logger.info("API credentials status:")
        self.logger.debug(f"API key configured: {bool(self.api_key)}")
        self.logger.debug(f"API secret configured: {bool(self.api_secret)}")
        
        if not self.api_key or not self.api_secret:
            raise AuthenticationError(
                "Missing Bybit API credentials. Please configure via .env file or config file"
            )
        
        # Store credentials in the format expected by other methods
        self.api_credentials = {
            'api_key': self.api_key,
            'api_secret': self.api_secret
        }
        
        # Initialize websocket config
        self.ws_config = self.exchange_config.get('websocket', {})
        self.ws_channels = self.ws_config.get('channels', [])
        self.ws_symbols = self.ws_config.get('symbols', [])
        
        # Set exchange ID
        self.exchange_id = 'bybit'
        
        # Initialize WebSocket state
        self.ws = None
        self.ws_connected = False
        self.ws_subscriptions = {}
        self.ws_callbacks = {}
        self.ws_reconnect_task = None
        self.ws_keepalive_task = None
        
        self.logger.info(f"Bybit exchange initialized with endpoint: {self.rest_endpoint}")
        self.logger.info(f"WebSocket endpoint: {self.ws_endpoint}")
        
        # Mark as not initialized until async init completes
        self.initialized = False
        
        self.market_type = 'linear'  # Add default market type
        
        # Update timeframe map to match standardization
        self.timeframe_map = {
            '1': '1',
            '5': '5',
            '30': '30',
            '240': '240'
        }
        
        # Add reverse mapping
        self._reverse_timeframe_map = {v: k for k, v in self.timeframe_map.items()}
        
        self.logger.info("Bybit exchange initialized successfully")
        
        # Initialize rate limit tracking
        self._rate_limit_buckets = {
            endpoint: [] for endpoint in self.RATE_LIMITS['endpoints'].keys()
        }
        self._rate_limit_lock = asyncio.Lock()
        
        # Initialize connection pooling components
        self.session = None
        self.connector = None
        self.timeout = None
        

    async def initialize(self) -> bool:
        """Initialize exchange connection and verify API credentials.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing {self.exchange_id} exchange...")
            
            # Initialize session if not already done
            if not hasattr(self, 'session') or self.session is None:
                self.session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(
                        limit=100,
                        ttl_dns_cache=300,
                        ssl=False
                    ),
                    timeout=aiohttp.ClientTimeout(
                        total=30,
                        connect=5,
                        sock_read=25
                    )
                )
            
            # Initialize pybit client for authenticated endpoints
            if self.api_key and self.api_secret:
                try:
                    self.pybit_client = HTTP(
                        testnet=self.testnet,
                        api_key=self.api_key,
                        api_secret=self.api_secret
                    )
                    self.logger.info("Pybit client initialized for authenticated endpoints")
                except Exception as e:
                    self.logger.error(f"Failed to initialize pybit client: {e}")
                    self.pybit_client = None
            
            # Test connection with a simple API call
            test_result = await self.health_check()
            
            if test_result:
                self.logger.info(f"✅ {self.exchange_id} exchange initialized successfully")
                self.initialized = True
                return True
            else:
                self.logger.error(f"❌ {self.exchange_id} exchange health check failed")
                self.initialized = False
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.exchange_id}: {str(e)}")
            self.initialized = False
            return False
    
    def _setup_basic_config(self):
        """Setup basic configuration parameters"""
        # Validate required fields
        required_fields = ['name', 'enabled', 'api_credentials']
        missing_fields = [f for f in required_fields if f not in self.exchange_config]
        if missing_fields:
            raise KeyError(f"Missing required fields in config: {missing_fields}")
        
        # Get exchange specific config
        self.market_data_config = self.exchange_config.get('market_data', {})
        
        # Get API paths
        self.market_paths = self.exchange_config.get('market_paths', {})
        
        # Initialize request tracking
        self._request_count = 0
        self._last_request_time = 0
        self.metrics_manager = None
        
        # Initialize state management
        self._initialization_lock = asyncio.Lock()
        self._initializing = False
        self._data_refresh_lock = asyncio.Lock()
        self._last_data_refresh = 0
        
        # Initialize WebSocket
        self.ws = None
        self.ws_connected = False
        self.ws_subscriptions = {}
        self.ws_callbacks = {}
        self.ws_reconnect_task = None
        self.ws_keepalive_task = None
        
        # Market data cache
        self._market_data_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = self.market_data_config.get('cache_ttl', 300)  # 5 minutes default
        
        # Set default options
        self.options.update({
            'defaultType': 'linear',
            'defaultNetwork': 'ETH',
            'networks': {
                'ETH': 'ETH',
                'BSC': 'BSC',
                'ARBITRUM': 'ARBITRUM',
            },
            'ws': {
                'ping_interval': 20,
                'ping_timeout': 10,
                'reconnect_attempts': 3,
                'reconnect_delay': 5,
            },
            'recvWindow': 5000,
            'timeDifference': 0,
            'adjustForTimeDifference': True
        })
        
        self.logger = logger
        
        # Set exchange ID
        self.exchange_id = 'bybit'
        
        # Set API URLs
        self.api_urls = {
            'public': 'https://api.bybit.com',
            'private': 'https://api.bybit.com',
            'v5': 'https://api.bybit.com/v5'
        }
        
        # Initialize supported timeframes
        self.timeframes = {
            '1m': '1',    # 1 minute
            '3m': '3',    # 3 minutes
            '5m': '5',    # 5 minutes
            '15m': '15',  # 15 minutes
            '30m': '30',  # 30 minutes
            '1h': '60',   # 1 hour
            '2h': '120',  # 2 hours
            '4h': '240',  # 4 hours
            '6h': '360',  # 6 hours
            '12h': '720', # 12 hours
            '1d': 'D',    # 1 day
            '1w': 'W',    # 1 week
            '1M': 'M'     # 1 month
        }
        
        # Initialize market type
        self._market_type = 'linear'
        
        self.timeframe_map = {
            '1': 'base',    # 1 minute - store as 'base'
            '5': 'ltf',     # 5 minutes
            '30': 'mtf',    # 30 minutes
            '240': 'htf'    # 4 hours (240 minutes)
        }
        
        # Add reverse mapping
        self._reverse_timeframe_map = {v: k for k, v in self.timeframe_map.items()}
        
        self.logger.info("Bybit exchange initialized successfully")
        
    def _create_websocket(self) -> None:
        """Create WebSocket instance."""
        try:
            if not hasattr(self, 'ws') or self.ws is None:
                self.ws = BybitWebSocket(
                    config=self.config,
                    logger=self.logger
                )
                self.logger.info("Created WebSocket instance")
            return True
        except Exception as e:
            self.logger.error(f"Error creating WebSocket instance: {str(e)}")
            return False
    
    async def _init_websocket(self) -> bool:
        """Initialize WebSocket connection."""
        try:
            if not self._create_websocket():
                return False
                
            # Connect WebSocket
            if not await self.ws.connect():
                self.logger.error("Failed to connect WebSocket")
                return False
                
            self.logger.info("WebSocket initialized successfully")
            
            # Subscribe to default channels
            for symbol in self.ws_symbols:
                await self.subscribe_market_data(symbol)
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket initialization failed: {str(e)}")
            return False
    
    async def _do_initialize(self) -> bool:
        """Perform Bybit-specific initialization."""
        try:
            if not self._validate_config(self.exchange_config):
                self.logger.error("Invalid configuration")
                return False
            
            # Initialize REST client with timeout
            self.logger.info("Initializing REST client...")
            rest_success = await self._init_rest_client_with_timeout()
            if not rest_success:
                return False
            
            # Initialize WebSocket if enabled (with timeout)
            if self.exchange_config.get('websocket', {}).get('enabled'):
                try:
                    async with asyncio.timeout(30.0):
                        await self._init_websocket()
                except asyncio.TimeoutError:
                    self.logger.error("WebSocket initialization timed out")
                    # Continue without WebSocket
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            return False
    
    async def _init_rest_client_with_timeout(self) -> bool:
        """Initialize REST client with proper timeout."""
        try:
            async with asyncio.timeout(10.0):
                return await self._init_rest_client()
        except asyncio.TimeoutError:
            self.logger.error("REST client initialization timed out")
            return False

    def set_market_type(self, market_type: str) -> None:
        """Set and validate market type."""
        if market_type not in self.WS_ENDPOINTS:
            raise ValueError(f"Invalid market type. Must be one of {list(self.WS_ENDPOINTS.keys())}")
        self._market_type = market_type
        self.logger.info(f"Market type set to: {market_type}")

    async def _init_rest_client(self) -> bool:
        """Initialize REST client for API requests with timeout.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Create persistent session with connection pooling
            if not self.session or self.session.closed:
                await self._create_session()
            
            # Test connection with server time endpoint (with shorter timeout)
            try:
                response = await asyncio.wait_for(
                    self._make_request('GET', '/v5/market/time'),
                    timeout=5.0  # 5 second timeout for connection test
                )
                if not response or 'retCode' not in response:
                    self.logger.error("Failed to connect to REST API")
                    return False
            except asyncio.TimeoutError:
                self.logger.error("Connection test timed out after 5s")
                # Try to recreate session
                await self._create_session()
                return False
            
            if response['retCode'] != 0:
                self.logger.error(f"REST API error: {response.get('retMsg', 'Unknown error')}")
                return False
            
            self.logger.info("REST client initialized successfully")
            return True
        except GeneratorExit:
            self.logger.info("REST client initialization cancelled due to GeneratorExit")
            raise
        except asyncio.CancelledError:
            self.logger.info("REST client initialization cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing REST client: {str(e)}", exc_info=True)
            return False
    
    async def _create_session(self) -> None:
        """Create persistent aiohttp session with connection pooling."""
        try:
            # Close existing session if any
            if self.session and not self.session.closed:
                await self.session.close()
                
            # Create TCP connector with connection pooling
            self.connector = aiohttp.TCPConnector(
                limit=150,  # Increased total connection pool limit
                limit_per_host=40,  # Increased per-host connection limit
                ttl_dns_cache=300,  # DNS cache timeout
                enable_cleanup_closed=True,
                force_close=False,  # Don't force close to allow keepalive
                keepalive_timeout=30
                # Note: limit_per_host_queue removed for compatibility
            )
            
            # Configure timeouts with more aggressive settings to prevent hanging
            self.timeout = aiohttp.ClientTimeout(
                total=10,  # Further reduced total timeout
                connect=3,  # Aggressive connection timeout
                sock_read=7,  # Reduced socket read timeout
                sock_connect=3  # Aggressive socket connection timeout
            )
            
            # Create session with connection pooling
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout
            )
            
            self.logger.info("Created persistent session with connection pooling")
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {str(e)}")
            raise
            
    async def _test_rest_connection(self) -> bool:
        """Test REST connection by making a simple request."""
        try:
            # Try to get server time
            response = await self._make_request('GET', '/v5/market/time')
            if response and response.get('retCode') == 0:
                return True
            return False
        except Exception as e:
            self.logger.error(f"REST connection test failed: {str(e)}")
            return False
    async def _make_request_with_retry(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> Dict[str, Any]:
        """Make request with retry logic and exponential backoff."""
        await self._throttle_request()
        for attempt in range(max_retries):
            try:
                return await self._make_request(method, endpoint, params)
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Max retries reached for {endpoint}: {str(e)}")
                    raise
                
                # Exponential backoff with jitter
                wait_time = min(2 ** attempt + random.uniform(0, 1), 10)
                self.logger.warning(f"Retry {attempt + 1}/{max_retries} for {endpoint} after {wait_time:.1f}s: {str(e)}")
                await asyncio.sleep(wait_time)
                
                # Recreate session if connection was reset
                if "Cannot write to closing transport" in str(e):
                    self.logger.info("Recreating session due to connection reset")
                    await self._create_session()
        
        return {}  # Should never reach here
    
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for each endpoint"""
        self.circuit_breakers = {}
        self.circuit_breaker_config = {
            'failure_threshold': 5,  # Open circuit after 5 failures
            'recovery_timeout': 60,  # Try again after 60 seconds
            'expected_exception': asyncio.TimeoutError
        }
    
    def _check_circuit_breaker(self, endpoint: str) -> bool:
        """Check if circuit breaker is open for endpoint"""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = {
                'failures': 0,
                'last_failure': None,
                'state': 'closed'  # closed, open, half-open
            }
        
        breaker = self.circuit_breakers[endpoint]
        
        # If circuit is open, check if we should try half-open
        if breaker['state'] == 'open':
            if breaker['last_failure'] and                (asyncio.get_event_loop().time() - breaker['last_failure']) > self.circuit_breaker_config['recovery_timeout']:
                breaker['state'] = 'half-open'
                self.logger.info(f"Circuit breaker for {endpoint} moved to half-open state")
            else:
                return False  # Circuit still open
        
        return True  # Circuit closed or half-open
    
    def _record_circuit_breaker_success(self, endpoint: str):
        """Record successful request"""
        if endpoint in self.circuit_breakers:
            self.circuit_breakers[endpoint]['failures'] = 0
            self.circuit_breakers[endpoint]['state'] = 'closed'
    
    def _record_circuit_breaker_failure(self, endpoint: str):
        """Record failed request"""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = {
                'failures': 0,
                'last_failure': None,
                'state': 'closed'
            }
        
        breaker = self.circuit_breakers[endpoint]
        breaker['failures'] += 1
        breaker['last_failure'] = asyncio.get_event_loop().time()
        
        if breaker['failures'] >= self.circuit_breaker_config['failure_threshold']:
            breaker['state'] = 'open'
            self.logger.warning(f"Circuit breaker opened for {endpoint} after {breaker['failures']} failures")

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the Bybit API.
        
        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            API response as dictionary
        """
        try:
            # Normalize endpoint format
            endpoint = endpoint.lstrip('/')
            if not endpoint.startswith('v5/'):
                endpoint = f"v5/{endpoint}"
            url = f"{self.rest_endpoint}/{endpoint}"
            
            # Ensure params is a dictionary
            if params is None:
                params = {}
            
            # Check if endpoint requires authentication
            requires_auth = not endpoint.startswith(('v5/market/'))
            
            if requires_auth:
                # Add required auth params
                timestamp = str(int(time.time() * 1000))
                auth_params = {
                    'api_key': self.api_key,
                    'timestamp': timestamp,
                    'recv_window': 5000
                }
                params.update(auth_params)
                
                # Generate signature
                signature = self._generate_signature(params)
                params['sign'] = signature
                
                # Add auth headers
                headers = {
                    'X-BAPI-API-KEY': self.api_key,
                    'X-BAPI-TIMESTAMP': timestamp,
                    'X-BAPI-RECV-WINDOW': '5000',
                    'X-BAPI-SIGN': signature,
                    'Content-Type': 'application/json'
                }
            else:
                headers = {'Content-Type': 'application/json'}
            
            # Log request details safely
            safe_params = {k: '***' if k in ['api_key', 'sign'] else v 
                          for k, v in params.items()}
            self.logger.debug(f"Making request to {url}")
            self.logger.debug(f"Params: {safe_params}")
            
            # Ensure session exists
            if not self.session or self.session.closed:
                await self._create_session()
            
            # Use persistent session with explicit timeout
            try:
                if method.upper() == 'GET':
                    # Use timeout context manager for the entire operation
                    async with asyncio.timeout(30.0):
                        async with self.session.get(url, params=params, headers=headers) as response:
                            return await self._process_response(response, url)
                elif method.upper() == 'POST':
                    # For POST requests, send params as JSON in the body
                    async with asyncio.timeout(30.0):
                        async with self.session.post(url, json=params, headers=headers) as response:
                            return await self._process_response(response, url)
            except asyncio.TimeoutError:
                self.logger.error(f"Request timeout after 10s: {endpoint}")
                return {'retCode': -1, 'retMsg': 'Request timeout'}
            except Exception as e:
                self.logger.error(f"Error during request: {str(e)}")
                return {'retCode': -1, 'retMsg': str(e)}
                    
        except GeneratorExit:
            self.logger.info("Request cancelled due to GeneratorExit")
            raise
        except asyncio.CancelledError:
            self.logger.info("Request cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Request error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {'retCode': -1, 'retMsg': str(e)}

    def _get_auth_headers(self, endpoint: str, params: dict) -> dict:
        """Get authentication headers for request."""
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp, endpoint, params)
        
        return {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-TIMESTAMP': str(timestamp),
            'X-BAPI-SIGN': signature,
        }
        
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate signature for authentication."""
        # Sort parameters alphabetically
        sorted_params = dict(sorted(params.items()))
        
        # Convert parameters to query string
        query_string = urlencode(sorted_params)
        
        # Create signature
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
        
    def _summarize_response(self, response: Union[Dict, List]) -> str:
        """Create a summary of the response for logging purposes.
        
        Args:
            response: The API response to summarize
            
        Returns:
            A concise summary of the response
        """
        try:
            if isinstance(response, dict):
                # For dictionary responses
                ret_code = response.get('retCode', 'N/A')
                ret_msg = response.get('retMsg', 'N/A')
                
                # Check if there's a result field and summarize it
                result = response.get('result', {})
                result_summary = "None"
                
                if isinstance(result, dict):
                    keys = list(result.keys())
                    if 'list' in result and isinstance(result['list'], list):
                        list_len = len(result['list'])
                        sample = str(result['list'][0])[:50] + "..." if list_len > 0 else "[]"
                        result_summary = f"{{list: [{list_len} items, sample: {sample}]}}"
                    else:
                        result_summary = f"{{keys: {keys}}}"
                elif isinstance(result, list):
                    list_len = len(result)
                    sample = str(result[0])[:50] + "..." if list_len > 0 else "[]"
                    result_summary = f"[{list_len} items, sample: {sample}]"
                
                return f"{{retCode: {ret_code}, retMsg: {ret_msg}, result: {result_summary}}}"
            
            elif isinstance(response, list):
                # For list responses
                list_len = len(response)
                sample = str(response[0])[:50] + "..." if list_len > 0 else "[]"
                return f"[{list_len} items, sample: {sample}]"
            
            else:
                return f"{type(response).__name__}: {str(response)[:100]}"
        
        except Exception as e:
            return f"Error summarizing response: {str(e)}"

    
    async def _make_request_with_retry(self, method: str, endpoint: str, params: dict = None, max_retries: int = 3) -> dict:
        """Make request with retry logic and exponential backoff"""
        last_error = None
        base_delay = 1.0  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                result = await self._make_request(method, endpoint, params)
                
                # Check if we got a rate limit error
                if result.get('retCode') == 10006:  # Rate limit error
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Rate limit hit, waiting {delay}s before retry (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                    
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Request failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Request failed after {max_retries} attempts: {str(e)}")
        
        # Return error response after all retries
        return {'retCode': -1, 'retMsg': f'Request failed after {max_retries} attempts: {str(last_error)}'}

    async def _process_response(self, response, url):
        """Process HTTP response and return result with proper logging.
        
        Args:
            response: aiohttp response object
            url: The URL that was queried
            
        Returns:
            Processed API response
        """
        # Extract rate limit headers from response
        try:
            self.rate_limit_status['remaining'] = int(response.headers.get('X-Bapi-Limit-Status', 600))
            self.rate_limit_status['limit'] = int(response.headers.get('X-Bapi-Limit', 600))
            reset_time = response.headers.get('X-Bapi-Limit-Reset-Timestamp')
            if reset_time:
                self.rate_limit_status['reset_timestamp'] = int(reset_time) / 1000  # Convert ms to seconds
            
            # Log rate limit status if getting low
            if self.rate_limit_status['remaining'] < 100:
                self.logger.warning(f"Rate limit warning: {self.rate_limit_status['remaining']}/{self.rate_limit_status['limit']} remaining")
        except Exception as e:
            self.logger.debug(f"Could not parse rate limit headers: {e}")
        
        if response.status != 200:
            error_text = await response.text()
            self.logger.error(f"HTTP {response.status} error for {url}: {error_text}")
            return {'retCode': -1, 'retMsg': f'HTTP {response.status} error: {error_text}'}
            
        try:
            result = await response.json()
            if not result:
                self.logger.error("Empty response received")
                return {'retCode': -1, 'retMsg': 'Empty response'}
                
            # Log concise response summary instead of full response
            response_summary = self._summarize_response(result)
            self.logger.debug(f"Response from {url}: {response_summary}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            return {'retCode': -1, 'retMsg': 'Invalid response format'}

    async def connect_ws(self) -> bool:
        """Connect to Bybit WebSocket with enhanced resilience and proper configuration"""
        try:
            # Get config with protocol validation
            ws_config = self.config.get('websocket', {})
            if not ws_config.get('enabled', False):
                self.logger.info("WebSocket is disabled in config")
                return False

            # Get the correct endpoint from config
            if self.config.get('testnet', False):
                ws_url = ws_config.get('testnet_endpoint')
                self.logger.debug(f"Using testnet WebSocket endpoint: {ws_url}")
            else:
                ws_url = ws_config.get('mainnet_endpoint')
                self.logger.debug(f"Using mainnet WebSocket endpoint: {ws_url}")

            if not ws_url:
                self.logger.error("WebSocket endpoint not configured")
                return False

            # Validate URL format
            if not ws_url.startswith('wss://'):
                ws_url = f"wss://{ws_url.lstrip('/')}"

            # Ensure URL has correct format for v5 API
            if not '/v5/public/linear' in ws_url:
                base_url = ws_url.rstrip('/')
                if base_url.endswith('/v5/public'):
                    ws_url = f"{base_url}/linear"
                elif not base_url.endswith('/v5/public/linear'):
                    ws_url = f"{base_url}/v5/public/linear"

            self.logger.info(f"Connecting to WebSocket URL: {ws_url}")
            
            # Enhanced connection parameters for resilience
            timeout = aiohttp.ClientTimeout(
                total=15,      # Total timeout
                connect=10,    # Connection timeout  
                sock_read=30   # Socket read timeout
            )
            
            # Create session with proper SSL and connection parameters
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            # Use the persistent session created in _create_session
            if not self.session or self.session.closed:
                await self._create_session()
            
            # Connect with enhanced error handling
            try:
                self.ws = await self.session.ws_connect(
                    ws_url,
                    autoclose=False,
                    heartbeat=30,
                    max_msg_size=64 * 1024 * 1024,  # 64MB max message size
                    compress=15,  # Enable compression
                    protocols=['websocket']
                )
                
                # Test the connection with a ping
                await asyncio.wait_for(self.ws.ping(), timeout=5.0)
                
                self.ws_connected = True
                self.logger.info("WebSocket connected and ping test successful")
                
                # Start message and keepalive handlers
                if not hasattr(self, 'ws_tasks') or not self.ws_tasks:
                    self.ws_tasks = []
                    
                self.ws_tasks.append(asyncio.create_task(self._ws_message_handler()))
                self.ws_tasks.append(asyncio.create_task(self._ws_keepalive()))
                
                return True
                
            except asyncio.TimeoutError:
                self.logger.error("WebSocket connection timeout")
                return False
            except aiohttp.ClientConnectionError as e:
                self.logger.error(f"WebSocket client connection error: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {str(e)}")
            self.logger.debug(f"WebSocket connection error details: {traceback.format_exc()}")
            
            # Clean up on failure
            if hasattr(self, 'ws') and self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
                
            if hasattr(self, 'session') and self.session:
                try:
                    await self.session.close()
                except:
                    pass
                self.session = None
                
            self.ws_connected = False
            return False

    async def _ws_keepalive(self):
        """Send periodic ping to keep WebSocket connection alive."""
        while self.ws_connected:
            try:
                if not self.ws:
                    self.logger.error("WebSocket connection lost")
                    break
                    
                await self.ws.ping()
                await asyncio.sleep(self.options['ws']['ping_interval'])
            except Exception as e:
                self.logger.error(f"WebSocket keepalive failed: {str(e)}")
                await self._handle_ws_error()
                break

    async def _ws_message_handler(self):
        """Handle incoming WebSocket messages with enhanced error detection."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        last_message_time = time.time()
        message_timeout = 60  # 60 seconds without messages triggers reconnection
        
        while self.ws_connected:
            try:
                if not self.ws:
                    self.logger.error("WebSocket connection lost - triggering reconnection")
                    await self._handle_ws_error("connection_lost")
                    break
                
                # Check for message timeout
                current_time = time.time()
                if current_time - last_message_time > message_timeout:
                    self.logger.warning(f"No messages received for {message_timeout} seconds - checking connection")
                    try:
                        await self.ws.ping()
                        last_message_time = current_time  # Reset timeout
                    except Exception as ping_error:
                        self.logger.error(f"WebSocket ping failed: {str(ping_error)}")
                        await self._handle_ws_error("ping_timeout")
                        break
                
                try:
                    # Use timeout for message reception
                    message = await asyncio.wait_for(self.ws.receive(), timeout=30.0)
                    last_message_time = time.time()
                    consecutive_errors = 0  # Reset error counter on successful message
                    
                    if message.type == aiohttp.WSMsgType.TEXT:
                        await self.handle_websocket_message(message.data)
                    elif message.type == aiohttp.WSMsgType.BINARY:
                        self.logger.debug("Received binary message (ignored)")
                    elif message.type == aiohttp.WSMsgType.CLOSED:
                        self.logger.warning("WebSocket connection closed by server")
                        await self._handle_ws_error("server_closed")
                        break
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        self.logger.error(f"WebSocket connection error: {str(message.data)}")
                        await self._handle_ws_error("connection_error")
                        break
                    elif message.type == aiohttp.WSMsgType.PONG:
                        self.logger.debug("Received pong from server")
                    else:
                        self.logger.debug(f"Received unknown message type: {message.type}")
                        
                except asyncio.TimeoutError:
                    self.logger.debug("WebSocket message receive timeout (30s)")
                    continue
                    
            except ConnectionResetError:
                self.logger.error("Connection reset by peer")
                await self._handle_ws_error("connection_reset")
                break
            except aiohttp.ClientConnectionError as e:
                self.logger.error(f"WebSocket client connection error: {str(e)}")
                await self._handle_ws_error("client_connection_error")
                break
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error handling WebSocket message (consecutive: {consecutive_errors}): {str(e)}")
                
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error(f"Too many consecutive errors ({consecutive_errors}), triggering reconnection")
                    await self._handle_ws_error("consecutive_errors")
                    break
                    
                # Brief pause before continuing
                await asyncio.sleep(1)

    async def handle_websocket_message(self, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            if 'topic' not in data:
                self.logger.warning(f"Unhandled WebSocket message: {message}")
                return
            
            topic = data['topic']
            
            # Handle liquidation messages
            if topic.startswith('allLiquidation.'):
                await self._handle_liquidation_message(data)
            else:
                self.logger.debug(f"Unhandled topic: {topic}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode WebSocket message: {str(e)}")

    async def _handle_liquidation_message(self, message: dict) -> None:
        """Handle liquidation message from WebSocket."""
        try:
            if message.get('type') != 'snapshot':
                return

            ts = message.get('ts')
            liquidation_data = message.get('data', [])
            
            if not liquidation_data:
                return
                
            # Handle array of liquidation events (official Bybit format)
            for liq in liquidation_data:
                liquidation = {
                    'symbol': liq.get('s'),
                    'side': liq.get('S', '').lower(),
                    'size': float(liq.get('v', 0)),
                    'price': float(liq.get('p', 0)),
                    'timestamp': int(liq.get('T', ts or 0))
                }
                
                self.logger.info(f"Liquidation event: {liquidation}")
                
                # Store liquidation data
                if not hasattr(self, '_liquidations'):
                    self._liquidations = {}
                
                symbol = liquidation['symbol']
                if symbol not in self._liquidations:
                    self._liquidations[symbol] = []
                
                self._liquidations[symbol].append(liquidation)
                
                # Keep only last 24 hours of liquidations
                cutoff = int(time.time() * 1000) - (24 * 60 * 60 * 1000)
                self._liquidations[symbol] = [
                    liq for liq in self._liquidations[symbol]
                    if liq['timestamp'] > cutoff
                ]
                
        except Exception as e:
            self.logger.error(f"Error handling liquidation message: {str(e)}")
            self.logger.debug(f"Message: {message}")
            self.logger.debug(traceback.format_exc())

    async def subscribe_liquidations(self, symbols: List[str]) -> bool:
        """Subscribe to liquidation feed for symbols."""
        try:
            if not self.ws_connected:
                self.logger.error("WebSocket not connected")
                return False

            # Format subscription message
            subscription = {
                "op": "subscribe",
                "args": [f"allLiquidation.{symbol}" for symbol in symbols]
            }
            
            self.logger.info(f"Subscribing to liquidations for symbols: {symbols}")
            
            # Send subscription request
            await self.ws.send_json(subscription)
            
            # Store subscribed symbols
            if not hasattr(self, '_liquidation_subscriptions'):
                self._liquidation_subscriptions = set()
            self._liquidation_subscriptions.update(symbols)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing to liquidations: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def get_recent_liquidations(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent liquidation events for a symbol.
        
        Args:
            symbol: The trading pair symbol
            hours: Number of hours of history to return (default 24)
            
        Returns:
            List of liquidation events
        """
        try:
            if not hasattr(self, '_liquidations') or symbol not in self._liquidations:
                return []
                
            cutoff = int(time.time() * 1000) - (hours * 60 * 60 * 1000)
            return [
                liq for liq in self._liquidations[symbol]
                if liq['timestamp'] > cutoff
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting liquidations for {symbol}: {str(e)}")
            return []

    async def _initialize_subscriptions(self) -> None:
        """Initialize WebSocket subscriptions after connection."""
        try:
            if not self.ws_connected:
                self.logger.error("Cannot initialize subscriptions - WebSocket not connected")
                return

            # Get symbols from config
            symbols = self.config.get('websocket', {}).get('symbols', [])
            if not symbols:
                self.logger.warning("No symbols configured for WebSocket")
                return

            # Subscribe to liquidations
            await self.subscribe_liquidations(symbols)
            
        except Exception as e:
            self.logger.error(f"Error initializing subscriptions: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _handle_ws_error(self, error_type: str = "unknown"):
        """Handle WebSocket errors and attempt reconnection with enhanced resilience."""
        self.logger.error(f"WebSocket error detected: {error_type}")
        self.ws_connected = False
        
        # Clean up existing connection
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                self.logger.debug(f"Error closing WebSocket: {str(e)}")
            self.ws = None
            
        # Store previous subscriptions for resubscription
        previous_subscriptions = getattr(self, 'ws_subscriptions', {}).copy()
        
        # Enhanced reconnection with exponential backoff
        max_attempts = self.options['ws']['reconnect_attempts']
        base_delay = self.options['ws']['reconnect_delay']
        
        for attempt in range(max_attempts):
            delay = min(base_delay * (2 ** attempt), 60)  # Cap at 60 seconds
            
            self.logger.info(f"Attempting WebSocket reconnection ({attempt + 1}/{max_attempts}) in {delay} seconds...")
            await asyncio.sleep(delay)
            
            try:
                # Attempt reconnection
                if await self.connect_ws():
                    self.logger.info(f"WebSocket reconnected successfully on attempt {attempt + 1}")
                    
                    # Wait a moment for connection to stabilize
                    await asyncio.sleep(1)
                    
                    # Resubscribe to previous topics
                    resubscription_success = True
                    for topic in previous_subscriptions:
                        try:
                            await self.ws_subscribe(topic)
                            self.logger.debug(f"Resubscribed to topic: {topic}")
                        except Exception as sub_error:
                            self.logger.error(f"Failed to resubscribe to {topic}: {str(sub_error)}")
                            resubscription_success = False
                    
                    if resubscription_success:
                        self.logger.info("All subscriptions restored successfully")
                    else:
                        self.logger.warning("Some subscriptions failed to restore")
                    
                    return True
                    
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed: {str(e)}")
                continue
                
        self.logger.error("Failed to reconnect WebSocket after all attempts")
        return False

    async def ws_subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to a WebSocket topic."""
        if not self.ws_connected:
            if not await self.connect_ws():
                return False
                
        try:
            subscribe_message = {
                'op': 'subscribe',
                'args': [topic]
            }
            await self.ws.send(json.dumps(subscribe_message))
            
            if callback:
                self.ws_callbacks[topic] = callback
            self.ws_subscriptions[topic] = True
            
            logger.info(f"Subscribed to WebSocket topic: {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {str(e)}")
            return False

    async def ws_unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a WebSocket topic."""
        if not self.ws_connected:
            return True
            
        try:
            unsubscribe_message = {
                'op': 'unsubscribe',
                'args': [topic]
            }
            await self.ws.send(json.dumps(unsubscribe_message))
            
            if topic in self.ws_callbacks:
                del self.ws_callbacks[topic]
            if topic in self.ws_subscriptions:
                del self.ws_subscriptions[topic]
                
            logger.info(f"Unsubscribed from WebSocket topic: {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic {topic}: {str(e)}")
            return False

    async def _initialize_ws_connection(self) -> bool:
        """Initialize WebSocket connection with proper error handling."""
        try:
            if not self._market_type:
                raise ValueError("Market type not set")
            
            ws_url = self.WS_ENDPOINTS[self._market_type]['public']
            self.ws = await self._create_ws_connection(ws_url)
            
            if not self.ws:
                return False
            
            self.ws_connected = True
            self._start_ws_tasks()
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing WebSocket: {str(e)}")
            return False

    def _create_error_context(self, operation: str, details: Dict[str, Any]) -> ErrorContext:
        """Create error context for operations."""
        return ErrorContext(
            exchange='bybit',
            operation=operation,
            details=details,
            timestamp=int(time.time() * 1000)
        )

    def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data structure and types with improved flexibility.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check basic structure
            if not isinstance(market_data, dict):
                self.logger.error(f"Market data must be a dictionary, got {type(market_data)}")
                return False
                
            # Core required fields - be more flexible about structure
            if 'symbol' not in market_data:
                self.logger.error("Missing required field: symbol")
                return False
                
            # Check if we have ticker data in any format
            has_ticker_data = any(key in market_data for key in ['ticker', 'price', 'lastPrice', 'last'])
            
            if not has_ticker_data:
                self.logger.warning("No ticker/price data found in market data")
                # Don't fail validation, just warn
                
            # If we have ticker data, extract key fields
            if 'ticker' in market_data and isinstance(market_data['ticker'], dict):
                ticker = market_data['ticker']
                
                # Check for essential ticker fields with flexible naming
                price_fields = ['lastPrice', 'last', 'price', 'close']
                price_value = None
                
                for field in price_fields:
                    if field in ticker:
                        try:
                            price_value = float(ticker[field])
                            break
                        except (ValueError, TypeError):
                            continue
                            
                if price_value is None or price_value <= 0:
                    self.logger.warning("No valid price data found in ticker")
                    # Don't fail validation, just warn
                    
            # Check sentiment data structure if present
            if 'sentiment' in market_data and isinstance(market_data['sentiment'], dict):
                sentiment = market_data['sentiment']
                
                # Validate long/short ratio if present
                if 'long_short_ratio' in sentiment:
                    lsr = sentiment['long_short_ratio']
                    if isinstance(lsr, dict):
                        required_lsr_fields = ['long', 'short']
                        for field in required_lsr_fields:
                            if field not in lsr:
                                self.logger.debug(f"LSR missing field: {field}")
                            elif not isinstance(lsr[field], (int, float)):
                                self.logger.debug(f"LSR field {field} has invalid type: {type(lsr[field])}")
                                
            # Check OHLCV data structure if present
            if 'ohlcv' in market_data and isinstance(market_data['ohlcv'], dict):
                ohlcv = market_data['ohlcv']
                expected_timeframes = ['base', 'ltf', 'mtf', 'htf']
                
                for tf in expected_timeframes:
                    if tf not in ohlcv:
                        self.logger.debug(f"Missing OHLCV timeframe: {tf}")
                        
            # Always return True for flexible validation - we warn about issues but don't fail
            self.logger.debug("Market data validation completed with warnings logged")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Even on exception, return True to avoid blocking data flow
            return True

    def sign(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Tuple[str, Dict, Dict, Dict]:
        """Sign request for private endpoints"""
        api_key = self.credentials.get('apiKey')
        secret = self.credentials.get('secret')
        
        if not api_key or not secret:
            raise AuthenticationError('Missing API credentials')
            
        # Build request data
        timestamp = int(time.time() * 1000)
        headers = headers or {}
        params = params or {}
        body = body or {}
        
        # Add authentication params
        params.update({
            'api_key': api_key,
            'timestamp': timestamp,
            'recv_window': self.options['recvWindow']
        })
        
        # Build signature string
        if method == 'GET':
            signature_string = '&'.join([
                f"{k}={v}" for k, v in sorted(params.items())
            ])
        else:
            signature_string = str(timestamp) + api_key + str(self.options['recvWindow']) + json.dumps(body)
            
        # Generate signature
        signature = hmac.new(
            secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to params
        params['sign'] = signature
        
        # Build URL
        url = f"{self.api_urls['v5']}{path}"
        
        # Add headers
        headers.update({
            'X-BAPI-API-KEY': api_key,
            'X-BAPI-TIMESTAMP': str(timestamp),
            'X-BAPI-RECV-WINDOW': str(self.options['recvWindow']),
            'X-BAPI-SIGN': signature,
            'Content-Type': 'application/json'
        })
        
        return url, params, headers, body
        
    def _handle_errors(self, response: Dict[str, Any]) -> None:
        """Handle Bybit specific errors"""
        if not isinstance(response, dict):
            return
            
        ret_code = str(response.get('retCode', 0))
        if ret_code != '0':
            error_msg = response.get('retMsg', 'Unknown error')
            error_desc = self.ERROR_CODES.get(ret_code, 'Unknown error code')
            
            error_type = None
            if ret_code in ['10007', '10008', '10009']:
                error_type = AuthenticationError
            elif ret_code == '10006':
                error_type = NetworkError
            else:
                error_type = BybitExchangeError
                
            raise error_type(f"Bybit API error {ret_code}: {error_msg} ({error_desc})")
            
    async def fetch_balance(
        self,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Fetch account balance"""
        try:
            response = await self.private_request(
                'GET',
                '/asset/v3/private/transfer/account-coins/balance/query',
                params=params
            )
            
            self._handle_errors(response)
            
            balances = {}
            for balance in response['result']['balance']:
                currency = balance['coin']
                balances[currency] = {
                    'free': float(balance['availableToWithdraw']),
                    'used': float(balance['locked']),
                    'total': float(balance['walletBalance'])
                }
                
            return {
                'info': response,
                'balances': balances,
                'timestamp': int(time.time() * 1000),
                'datetime': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching balance: {str(e)}")
            raise
            
    async def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create new order"""
        try:
            self.validate_symbol(symbol)
            
            # Prepare order params
            order = {
                'symbol': symbol,
                'side': side.upper(),
                'orderType': type.upper(),
                'qty': str(amount)
            }
            
            if price:
                order['price'] = str(price)
                
            if params:
                order.update(params)
                
            response = await self.private_request(
                'POST',
                '/v5/order/create',
                body=order
            )
            
            self._handle_errors(response)
            
            return self.parse_order(response['result'])
            
        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
            raise
            
    def parse_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Parse order response to standard format"""
        return {
            'id': order['orderId'],
            'symbol': order['symbol'],
            'type': order['orderType'].lower(),
            'side': order['side'].lower(),
            'price': float(order.get('price', 0)),
            'amount': float(order['qty']),
            'filled': float(order.get('cumExecQty', 0)),
            'remaining': float(order.get('leavesQty', order['qty'])),
            'status': self.parse_order_status(order['orderStatus']),
            'timestamp': int(order['createdTime']),
            'datetime': datetime.fromtimestamp(int(order['createdTime']) / 1000).isoformat(),
            'info': order
        }
        
    def parse_order_status(self, status: str) -> str:
        """Parse order status to standard format"""
        statuses = {
            'Created': 'open',
            'New': 'open', 
            'Rejected': 'rejected',
            'PartiallyFilled': 'open',
            'PartiallyFilledCanceled': 'canceled',
            'Filled': 'closed',
            'Cancelled': 'canceled',
            'Untriggered': 'open',
            'Triggered': 'open',
            'Deactivated': 'canceled'
        }
        return statuses.get(status, 'unknown')

    async def subscribe_to_symbol(self, symbol: str):
        """Subscribe to all relevant feeds for a symbol."""
        try:
            # Subscribe to liquidations via WebSocket
            await self.ws.subscribe_liquidations(symbol)
        except Exception as e:
            self.logger.error(f"Error subscribing to symbol feeds: {str(e)}")

    async def get_recent_liquidations(self, symbol: str) -> List[Dict[str, Any]]:
        """Get recent liquidation events from WebSocket buffer."""
        try:
            return self.ws.get_recent_liquidations(symbol)
        except Exception as e:
            self.logger.error(f"Error fetching liquidations: {str(e)}")
            return []

    async def fetch_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Fetch exchange information including trading rules."""
        try:
            # Make request without decorator arguments
            response = await self._make_request('/v5/market/instruments-info', {'category': 'linear'})
            if response and 'result' in response:
                return response['result']
            return None
        except Exception as e:
            self.logger.error(f"Error fetching exchange info: {str(e)}")
            return None

    async def fetch_status(self) -> Dict[str, Any]:
        """Fetch Bybit exchange status for system health monitoring."""
        try:
            # Check server time to verify connectivity
            response = await self._make_request('GET', '/v5/market/time')
            
            if response and 'retCode' in response and response['retCode'] == 0:
                # Exchange is responding correctly
                server_time = int(response['result']['timeSecond']) * 1000
                local_time = int(time.time() * 1000)
                time_diff = abs(server_time - local_time)
                
                # Check if time difference is reasonable (less than 30 seconds)
                is_online = time_diff <= 30000
                
                return {
                    'online': is_online,
                    'has_trading': True,  # Bybit supports trading
                    'status': 'ok' if is_online else 'time_sync_error',
                    'timestamp': int(time.time() * 1000),
                    'server_time': server_time,
                    'time_diff_ms': time_diff,
                    'rate_limit': {
                        'remaining': 119,  # Default rate limit info
                        'limit': 120,
                        'reset_time': int(time.time() + 60)
                    }
                }
            else:
                # API error response
                error_msg = response.get('retMsg', 'Unknown error') if response else 'No response'
                return {
                    'online': False,
                    'has_trading': False,
                    'status': 'error',
                    'error': error_msg,
                    'timestamp': int(time.time() * 1000)
                }
                
        except Exception as e:
            self.logger.error(f"Error fetching Bybit status: {str(e)}")
            return {
                'online': False,
                'has_trading': False,
                'status': 'error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }

    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from Bybit (required by system status endpoint)."""
        try:
            # Use existing get_markets method for consistency
            markets = await self.get_markets()
            
            # Convert to the format expected by CCXT standards
            formatted_markets = []
            for market in markets:
                try:
                    formatted_market = {
                        'id': market.get('symbol', ''),
                        'symbol': market.get('symbol', ''),
                        'base': market.get('symbol', '').replace('USDT', '') if market.get('symbol', '').endswith('USDT') else '',
                        'quote': 'USDT' if market.get('symbol', '').endswith('USDT') else '',
                        'baseId': market.get('symbol', '').replace('USDT', '') if market.get('symbol', '').endswith('USDT') else '',
                        'quoteId': 'USDT' if market.get('symbol', '').endswith('USDT') else '',
                        'active': market.get('active', True),
                        'type': 'swap',
                        'spot': False,
                        'margin': False,
                        'future': False,
                        'swap': True,
                        'option': False,
                        'contract': True,
                        'linear': True,
                        'inverse': False,
                        'contractSize': 1,
                        'precision': {
                            'amount': 8,
                            'price': 8
                        },
                        'limits': {
                            'amount': {
                                'min': 0.001,
                                'max': 1000000
                            },
                            'price': {
                                'min': 0.01,
                                'max': 1000000
                            },
                            'cost': {
                                'min': 5,
                                'max': 10000000
                            }
                        },
                        'info': market
                    }
                    formatted_markets.append(formatted_market)
                except Exception as e:
                    self.logger.warning(f"Error formatting market {market}: {e}")
                    continue
                    
            self.logger.debug(f"Formatted {len(formatted_markets)} markets for CCXT compatibility")
            return formatted_markets
            
        except Exception as e:
            self.logger.error(f"Error fetching markets: {str(e)}")
            return []

    async def refresh_market_data(self, force: bool = False) -> bool:
        """Refresh market data if cache is expired or force is True."""
        if not force and time.time() - self._cache_timestamp < self._cache_ttl:
            return True
            
        async with self._data_refresh_lock:
            logger.info("Refreshing market data...")
            return await self.fetch_market_data()

    async def _cleanup(self):
        """Clean up resources."""
        try:
            # Close session and connector
            if hasattr(self, 'session') and self.session:
                await self.session.close()
                self.session = None
            
            if hasattr(self, 'connector') and self.connector:
                await self.connector.close()
                self.connector = None
            
            if hasattr(self, 'ws') and self.ws:
                await self.ws.close()
                self.ws = None
            
            self.initialized = False
            self.logger.info("Cleaned up Bybit exchange resources")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    async def close(self) -> None:
        """Close exchange connections."""
        try:
            if hasattr(self, 'session') and self.session:
                await self.session.close()
            if hasattr(self, 'ws') and self.ws:
                await self.ws.close()
        except Exception as e:
            self.logger.error(f"Error closing exchange connections: {str(e)}")

    async def test_connection(self) -> bool:
        """Test API connectivity."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Use v5 API endpoint for time
                async with aiohttp.ClientSession() as session:
                    url = f"{self.rest_endpoint}/v5/market/time"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and data.get('retCode') == 0:
                                self.logger.debug("API connection test successful")
                                return True
                            else:
                                error_text = data.get('retMsg', 'Unknown error') if data else 'No response data'
                                self.logger.error(f"API connection test failed: {error_text}")
                        else:
                            self.logger.error(f"API connection test failed: {response.status}")
                            
                        if attempt == max_retries - 1:
                            return False
                            
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                        
            except Exception as e:
                self.logger.error(f"Connection test failed: {str(e)}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
        
        return False

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate signature for authenticated requests."""
        try:
            # Sort parameters alphabetically
            sorted_params = dict(sorted(params.items()))
            
            # Convert parameters to query string
            query_string = urlencode(sorted_params)
            
            # Create signature
            signature = hmac.new(
                self.api_secret.encode(),
                query_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            self.logger.error(f"Error generating signature: {str(e)}")
            raise

    async def validate_credentials(self) -> bool:
        """Validate API credentials are correct and have required permissions."""
        try:
            self.logger.info("Validating Bybit API credentials...")
            
            # Test authentication with a simple API call
            response = await self._make_request('GET', 'v5/account/wallet-balance', {
                'accountType': 'UNIFIED'
            })
            
            if not response or response.get('retCode') != 0:
                self.logger.error(
                    f"API credential validation failed: {response.get('retMsg', 'Unknown error')}"
                )
                return False
            
            self.logger.info("API credentials validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating credentials: {str(e)}")
            return False

    async def parse_balance(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance response"""
        result = {'info': response}
        for balance in response.get('result', {}).get('list', []):
            currency = balance['coin']
            result[currency] = {
                'free': float(balance.get('free', 0)),
                'used': float(balance.get('locked', 0)),
                'total': float(balance.get('total', 0))
            }
        return result

    async def parse_ohlcv(self, response: Dict[str, Any]) -> List[List[float]]:
        """Parse OHLCV data from Bybit API response.
        
        Args:
            response: Raw API response from Bybit
            
        Returns:
            List of processed OHLCV candles
        """
        ohlcv = []
        
        # Check if we have a valid response
        if not response or not isinstance(response, dict):
            self.logger.error(f"Invalid OHLCV response format: {type(response)}")
            return ohlcv
            
        # Get result from response
        result = response.get('result', {})
        if not isinstance(result, dict):
            self.logger.error(f"Invalid result format in OHLCV response: {type(result)}")
            return ohlcv
            
        # Get candle list from result
        candles = result.get('list', [])
        if not candles:
            self.logger.warning("No candles returned in OHLCV response")
            return ohlcv
            
        self.logger.debug(f"Processing {len(candles)} raw candles from API")
        
        # Process each candle with enhanced error handling
        for candle in candles:
            try:
                # Verify we have at least 6 elements (required fields)
                if len(candle) < 6:
                    self.logger.warning(f"Skipping candle with insufficient elements: {candle}")
                    continue
                
                # Bybit returns candles as: [timestamp, open, high, low, close, volume, turnover]
                # Apply explicit conversion and validation
                timestamp = int(candle[0])
                open_price = float(candle[1])
                high_price = float(candle[2])
                low_price = float(candle[3])
                close_price = float(candle[4])
                volume = float(candle[5])
                
                # Basic validation
                if timestamp <= 0:
                    self.logger.warning(f"Skipping candle with invalid timestamp: {candle}")
                    continue
                    
                # Price validation (optional - adjust thresholds as needed)
                if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                    self.logger.warning(f"Skipping candle with invalid price values: {candle}")
                    continue
                    
                if high_price < low_price:
                    self.logger.warning(f"Skipping candle with high < low: {candle}")
                    continue
                
                # Add the processed candle
                ohlcv.append([
                    timestamp,      # timestamp
                    open_price,     # open
                    high_price,     # high
                    low_price,      # low
                    close_price,    # close
                    volume          # volume
                ])
                
            except (IndexError, ValueError, TypeError) as e:
                self.logger.warning(f"Error parsing candle: {e}, candle: {candle}")
                continue
        
        # Final validation and logging        
        if not ohlcv:
            self.logger.error("No valid candles after processing OHLCV data")
        else:
            self.logger.debug(f"Successfully processed {len(ohlcv)} valid candles out of {len(candles)} raw candles")
            
        return ohlcv

    async def parse_orderbook(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse orderbook response into standardized format."""
        try:
            if not response or response.get('retCode') != 0:
                return None
            
            result = response.get('result', {})
            orderbook = {
                'bids': [],
                'asks': [],
                'timestamp': int(result.get('ts', time.time() * 1000))
            }
            
            # Parse bids and asks
            for bid in result.get('b', []):
                orderbook['bids'].append([float(bid[0]), float(bid[1])])
            
            for ask in result.get('a', []):
                orderbook['asks'].append([float(ask[0]), float(ask[1])])
            
            return orderbook
            
        except Exception as e:
            self.logger.error(f"Error parsing orderbook: {str(e)}")
            return None

    async def parse_ticker(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ticker data"""
        ticker = response.get('result', {})
        return {
            'bid': float(ticker.get('bid', 0)),
            'ask': float(ticker.get('ask', 0)),
            'last': float(ticker.get('last', 0)),
            'volume': float(ticker.get('volume', 0)),
            'open_interest': float(ticker.get('openInterest', 0)),
            'open_interest_value': float(ticker.get('openInterestValue', 0)),
            'funding_rate': float(ticker.get('fundingRate', 0)),
            'next_funding_time': int(ticker.get('nextFundingTime', 0)),
            'mark_price': float(ticker.get('markPrice', 0)),
            'index_price': float(ticker.get('indexPrice', 0))
        }

    async def parse_trades(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse trades data from Bybit API response.
        
        Args:
            response: Raw API response from Bybit
            
        Returns:
            List of standardized trade dictionaries
        """
        trades = []
        try:
            trade_list = response.get('result', {}).get('list', [])
            self.logger.debug(f"Processing {len(trade_list)} raw trades")
            
            # Track validation issues
            validation_issues = defaultdict(int)
            
            for trade in trade_list:
                try:
                    # Extract and validate required fields
                    trade_data = {
                        'id': str(trade.get('execId', '')),
                        'price': float(trade.get('price', 0)),
                        'size': float(trade.get('size', 0)),
                        'side': str(trade.get('side', '')).lower(),
                        'time': int(trade.get('time', 0)),
                        'symbol': trade.get('symbol', ''),
                        'isBlockTrade': bool(trade.get('isBlockTrade', False)),
                        'info': trade  # Store raw trade data
                    }
                    
                    # Validate required fields
                    required_fields = ['id', 'price', 'size', 'side', 'time', 'symbol']
                    missing_fields = [f for f in required_fields if not trade_data.get(f)]
                    if missing_fields:
                        validation_issues['missing_fields'] += 1
                        continue
                    
                    # Validate numeric values with precision checks
                    if not (0 < trade_data['price'] <= 1000000):
                        validation_issues['invalid_price'] += 1
                        continue
                        
                    if not (0 < trade_data['size'] <= 1000000000):
                        validation_issues['invalid_size'] += 1
                        continue
                    
                    # Validate side values
                    if trade_data['side'] not in ['buy', 'sell']:
                        validation_issues['invalid_side'] += 1
                        continue
                    
                    # Validate timestamp (assuming milliseconds)
                    min_valid_ts = 1609459200000  # 2021-01-01
                    max_valid_ts = 2147483648000  # 2038-01-01
                    if not (min_valid_ts <= trade_data['time'] <= max_valid_ts):
                        validation_issues['invalid_timestamp'] += 1
                        continue
                    
                    # Validate symbol format
                    if not re.match(r'^[A-Z0-9]{6,12}(USDT|USD|BTC|ETH)$', trade_data['symbol']):
                        validation_issues['invalid_symbol'] += 1
                        continue
                    
                    trades.append(trade_data)
                    
                except (ValueError, TypeError) as e:
                    validation_issues['parse_error'] += 1
                    continue
            
            # Log validation summary
            if validation_issues:
                self.logger.warning(f"Trade validation issues: {dict(validation_issues)}")
            
            # Log sample trade if available
            if trades:
                sample = {k:v for k,v in trades[0].items() if k != 'info'}
                self.logger.debug(f"Successfully processed {len(trades)}/{len(trade_list)} trades. Sample: {sample}")
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Error parsing trades: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return []

    async def subscribe_ws(self, channels: List[str]) -> None:
        """Subscribe to websocket channels"""
        if not self.ws:
            await self.connect_ws()
        for channel in channels:
            await self.ws_subscribe(channel)

    async def health_check(self) -> bool:
        """Verify exchange connection health."""
        try:
            # Test server time endpoint
            response = await self._make_request('GET', '/v5/market/time', {})
            
            if not isinstance(response, dict):
                self.logger.error("Invalid response format")
                return False
            
            if response.get('retCode') == 0:
                self.logger.debug("Health check successful")
                return True
            
            self.logger.error(f"Health check failed with response: {response}")
            return False
            
        except Exception as e:
            self.logger.error(f"Health check failed with exception: {str(e)}")
            self.logger.debug("Full exception details:", exc_info=True)
            return False

    async def is_healthy(self) -> bool:
        """Check if the exchange connection is healthy.
        
        Override the base class method to use Bybit-specific health check.
        
        Returns:
            bool: True if the exchange is healthy, False otherwise
        """
        current_time = time.time()
        
        # Only check health status every _health_check_interval seconds
        if current_time - self._last_health_check < self._health_check_interval:
            return self._is_healthy
            
        try:
            # Use our own health check method instead of the base class
            self._is_healthy = await self.health_check()
            
            # Check WebSocket connection if enabled
            if self.ws and hasattr(self.ws, 'closed') and not self.ws.closed:
                self._is_healthy = self._is_healthy and True
            else:
                # If WebSocket is enabled but not connected, try to reconnect
                if hasattr(self, 'ws_endpoints') and self.ws_endpoints:
                    try:
                        if hasattr(self, '_ws_reconnect'):
                            await self._ws_reconnect()
                    except:
                        pass  # Don't fail health check if WS reconnect fails
                        
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            self._is_healthy = False
            
        self._last_health_check = current_time
        return self._is_healthy

    async def subscribe_market_data(self, symbol: str):
        """Subscribe to market data streams based on config."""
        try:
            if not self.ws_config.get('enabled', False):
                self.logger.warning("WebSocket is not enabled in config")
                return
                
            # Use channels from config
            channels = []
            if 'trade' in self.ws_channels:
                channels.append(f"trades.{symbol}")
            if 'orderbook' in self.ws_channels:
                channels.append(f"orderbook.50.{symbol}")
            if 'kline' in self.ws_channels:
                channels.append(f"kline.1.{symbol}")  # Use '1' instead of '1m'
                
            # Always subscribe to liquidation feed (required for sentiment analysis)
            channels.append(f"allLiquidation.{symbol}")
            
            # Add additional data streams
            channels.extend([
                f"tickers.{symbol}"
            ])
            
            for channel in channels:
                await self.ws_subscribe(channel)
                self.logger.debug(f"Subscribed to {channel}")
                
                # Register specific handler for liquidation data
                if channel.startswith('allLiquidation.'):
                    self.ws.on_message(channel, self._handle_liquidation_update)
                
        except Exception as e:
            self.logger.error(f"Failed to subscribe to market data: {str(e)}")
            raise

    async def _handle_liquidation_update(self, message: Dict[str, Any]) -> None:
        """Handle incoming liquidation data from WebSocket."""
        try:
            # Check if this is an allLiquidation message
            if not message.get('topic', '').startswith('allLiquidation.'):
                return
            
            # Extract liquidation data array (official Bybit format)
            liquidation_data_array = message.get('data', [])
            if not liquidation_data_array:
                return
            
            ts = message.get('ts', int(time.time() * 1000))
            
            # Process each liquidation event in the array
            for data in liquidation_data_array:
                symbol = data.get('s')
                if not symbol:
                    continue
                    
                liquidation = {
                    'symbol': symbol,
                    'side': data.get('S', '').lower(),
                    'price': float(data.get('p', 0)),
                    'size': float(data.get('v', 0)),
                    'timestamp': int(data.get('T', ts))
                }
                
                # Store liquidation data
                if not hasattr(self, 'market_data'):
                    self.market_data = {}
                if symbol not in self.market_data:
                    self.market_data[symbol] = {'sentiment': {'liquidations': []}}
                
                self.market_data[symbol]['sentiment']['liquidations'].append(liquidation)
                
                # Keep only recent liquidations (last 24 hours)
                cutoff = int(time.time() * 1000) - (24 * 60 * 60 * 1000)
                self.market_data[symbol]['sentiment']['liquidations'] = [
                    liq for liq in self.market_data[symbol]['sentiment']['liquidations']
                    if liq['timestamp'] > cutoff
                ]
                
                self.logger.debug(f"Processed liquidation: {liquidation}")
            
        except Exception as e:
            self.logger.error(f"Error processing liquidation update: {str(e)}")
            self.logger.debug(f"Raw message: {message}")

    async def _check_rate_limit(self, endpoint: str, category: str = 'linear') -> None:
        """Check rate limit using sliding window approach matching Bybit's limits."""
        async with self._rate_limit_lock:
            now = time.time()
            
            # Use global rate limit bucket (600 requests per 5 seconds)
            global_bucket = self._rate_limit_buckets.setdefault('global', [])
            window_start = now - 5.0  # 5-second sliding window
            
            # Clean expired timestamps (older than 5 seconds)
            global_bucket[:] = [ts for ts in global_bucket if ts > window_start]
            
            # Check if we've hit the global limit
            if len(global_bucket) >= 600:
                # Calculate wait time until oldest request expires
                wait_time = global_bucket[0] + 5.0 - now
                if wait_time > 0:
                    self.logger.warning(f"Global rate limit reached (600/5s), waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    # Recursive check after waiting
                    await self._check_rate_limit(endpoint, category)
                    return
            
            # Also check endpoint-specific limits for internal throttling
            endpoint_bucket = self._rate_limit_buckets.setdefault(endpoint, [])
            endpoint_limit = self.RATE_LIMITS['endpoints'].get(endpoint, {'requests': 100, 'per_second': 1})
            
            # Clean expired timestamps for endpoint
            endpoint_window = now - endpoint_limit['per_second']
            endpoint_bucket[:] = [ts for ts in endpoint_bucket if ts > endpoint_window]
            
            # Check endpoint limit
            if len(endpoint_bucket) >= endpoint_limit['requests']:
                wait_time = endpoint_bucket[0] + endpoint_limit['per_second'] - now
                if wait_time > 0:
                    self.logger.debug(f"Endpoint {endpoint} rate limit, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    await self._check_rate_limit(endpoint, category)
                    return
            
            # Check dynamic rate limit from headers
            if hasattr(self, 'rate_limit_status') and self.rate_limit_status['remaining'] < 50:
                self.logger.warning(f"Low rate limit remaining: {self.rate_limit_status['remaining']}")
                # Add small delay to be conservative
                await asyncio.sleep(0.1)
            
            # Record the request timestamp
            global_bucket.append(now)
            endpoint_bucket.append(now)

    def _ensure_sentiment_structure(self, market_data: Dict[str, Any], symbol: str) -> None:
        """Ensure sentiment structure exists in market_data to prevent KeyErrors."""
        timestamp = int(time.time() * 1000)
        
        if 'sentiment' not in market_data:
            market_data['sentiment'] = {}
        
        # Ensure all required sentiment sub-structures exist
        if 'long_short_ratio' not in market_data['sentiment']:
            market_data['sentiment']['long_short_ratio'] = {
                'symbol': symbol,
                'long': 50.0,
                'short': 50.0,
                'timestamp': timestamp
            }
        
        if 'volume_sentiment' not in market_data['sentiment']:
            market_data['sentiment']['volume_sentiment'] = {
                'buy_volume': 0.0,
                'sell_volume': 0.0,
                'timestamp': timestamp
            }
        
        if 'market_mood' not in market_data['sentiment']:
            market_data['sentiment']['market_mood'] = {
                'risk_level': 1,
                'max_leverage': 100.0,
                'timestamp': timestamp
            }
        
        if 'funding_rate' not in market_data['sentiment']:
            market_data['sentiment']['funding_rate'] = {
                'rate': 0.0,
                'next_funding_time': timestamp + 28800000  # 8 hours
            }
        
        if 'open_interest' not in market_data['sentiment']:
            market_data['sentiment']['open_interest'] = {
                'current': 0.0,
                'previous': 0.0,
                'change': 0.0,
                'timestamp': timestamp,
                'value': 0.0,
                'history': []
            }

    def _get_default_market_data(self, symbol: str) -> Dict[str, Any]:
        """Return default market data structure with neutral values."""
        timestamp = int(time.time() * 1000)
        return {
            'symbol': symbol,
            'exchange': 'bybit',
            'timestamp': timestamp,
            'ticker': {},
            'orderbook': {
                'bids': [],
                'asks': [],
                'timestamp': timestamp
            },
            'trades': [],
            'sentiment': {
                'long_short_ratio': {
                    'symbol': symbol,
                    'long': 0.5,
                    'short': 0.5,
                    'timestamp': timestamp
                },
                'liquidations': {
                    'long': 0.0,
                    'short': 0.0,
                    'total': 0.0,
                    'timestamp': timestamp
                },
                'funding_rate': {
                    'rate': 0.0,
                    'next_funding_time': timestamp + 8 * 3600 * 1000
                },
                'volatility': {
                    'value': 0.0,
                    'window': 24,
                    'timeframe': '5min',
                    'timestamp': timestamp,
                    'trend': 'unknown',
                    'period_minutes': 5
                },
                'volume_sentiment': {
                    'buy_volume': 0.0,
                    'sell_volume': 0.0,
                    'timestamp': timestamp
                },
                'market_mood': {
                    'risk_level': 1,
                    'max_leverage': 100.0,
                    'timestamp': timestamp
                },
                'open_interest': {
                    'current': 0.0,
                    'previous': 0.0,
                    'change': 0.0,
                    'timestamp': timestamp,
                    'value': 0.0,  # ← Add 'value' field for validation compatibility
                    'history': []
                }
            },
            'ohlcv': {},
            'metadata': {
                'ticker_success': False,
                'orderbook_success': False,
                'trades_success': False,
                'lsr_success': False,
                'risk_limits_success': False,
                'ohlcv_success': False,
                'oi_history_success': False,
                'volatility_success': False
            }
        }

    def _ensure_market_data_structure(self, market_data: Dict[str, Any], symbol: str) -> None:
        """Ensure market_data has all required keys to prevent KeyErrors."""
        timestamp = int(time.time() * 1000)
        
        # Ensure top-level keys exist
        required_keys = ['symbol', 'timestamp', 'ohlcv', 'sentiment', 'metadata']
        for key in required_keys:
            if key not in market_data:
                if key == 'symbol':
                    market_data[key] = symbol
                elif key == 'timestamp':
                    market_data[key] = timestamp
                elif key == 'ohlcv':
                    market_data[key] = {}
                elif key == 'sentiment':
                    market_data[key] = {}
                elif key == 'metadata':
                    market_data[key] = {}
        
        # Ensure sentiment sub-structure exists
        if 'sentiment' not in market_data:
            market_data['sentiment'] = {}
        
        sentiment_keys = ['long_short_ratio', 'volume_sentiment', 'market_mood', 'funding_rate', 'open_interest', 'volatility']
        for key in sentiment_keys:
            if key not in market_data['sentiment']:
                if key == 'long_short_ratio':
                    market_data['sentiment'][key] = {
                        'symbol': symbol,
                        'long': 50.0,
                        'short': 50.0,
                        'timestamp': timestamp
                    }
                elif key == 'volume_sentiment':
                    market_data['sentiment'][key] = {
                        'buy_volume': 0.0,
                        'sell_volume': 0.0,
                        'timestamp': timestamp
                    }
                elif key == 'market_mood':
                    market_data['sentiment'][key] = {
                        'risk_level': 1,
                        'max_leverage': 100.0,
                        'timestamp': timestamp
                    }
                elif key == 'funding_rate':
                    market_data['sentiment'][key] = {
                        'rate': 0.0,
                        'next_funding_time': timestamp + 28800000  # 8 hours
                    }
                elif key == 'open_interest':
                    market_data['sentiment'][key] = {
                        'current': 0.0,
                        'previous': 0.0,
                        'change': 0.0,
                        'timestamp': timestamp,
                        'value': 0.0,
                        'history': []
                    }
                elif key == 'volatility':
                    market_data['sentiment'][key] = {
                        'value': 0.0,
                        'window': 24,
                        'timeframe': '5min',
                        'timestamp': timestamp,
                        'trend': 'unknown',
                        'period_minutes': 5
                    }
        
        # Ensure oi_history key exists (this was causing KeyErrors)
        if 'oi_history' not in market_data:
            market_data['oi_history'] = []

    async def fetch_market_data(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch comprehensive market data for a symbol.
        
        Args:
            symbol: The trading pair symbol (e.g. 'BTCUSDT')
            limit: Optional limit for data points
            
        Returns:
            Dictionary containing all market data
        """
        try:
            # Create async fetch functions with retry logic
            async def fetch_with_retry(endpoint: str, fetch_func: Callable, *args, **kwargs) -> Any:
                """Retry fetching market data with a backoff."""
                max_retries = 3
                retry_delay = 2  # seconds
                last_exception = None
                
                for attempt in range(1, max_retries + 1):
                    try:
                        await self._check_rate_limit(endpoint, category='linear')
                        
                        # Add detailed debugging before function call
                        self.logger.debug(f"🔍 DEBUG: Calling {fetch_func.__name__ if hasattr(fetch_func, '__name__') else str(fetch_func)} "
                                        f"for endpoint '{endpoint}' (attempt {attempt}/{max_retries})")
                        self.logger.debug(f"🔍 DEBUG: Function args: {args}")
                        self.logger.debug(f"🔍 DEBUG: Function kwargs: {kwargs}")
                        
                        result = await fetch_func(*args, **kwargs)
                        
                        # Add detailed debugging after function call
                        self.logger.debug(f"✅ DEBUG: {fetch_func.__name__ if hasattr(fetch_func, '__name__') else str(fetch_func)} "
                                        f"returned successfully for endpoint '{endpoint}'")
                        self.logger.debug(f"✅ DEBUG: Result type: {type(result)}")
                        if isinstance(result, dict):
                            self.logger.debug(f"✅ DEBUG: Result keys: {list(result.keys()) if result else 'None'}")
                        elif isinstance(result, list):
                            self.logger.debug(f"✅ DEBUG: Result length: {len(result) if result else 0}")
                        
                        # If we get a valid result, return it immediately
                        if result is not None:
                            return result
                        # If result is None but no exception, that's a valid "no data" response
                        return None
                        
                    except KeyError as e:
                        # Handle KeyError specifically - this is likely a data structure issue
                        last_exception = e
                        # For LSR and OHLCV, we know the APIs work, so the KeyError is likely from data processing
                        # Let's be more specific about where the error comes from
                        key_missing = str(e).strip("'\"")
                        
                        # Add comprehensive debugging for KeyError
                        self.logger.error(f"🚨 KEYERROR DEBUG: KeyError in {fetch_func.__name__ if hasattr(fetch_func, '__name__') else str(fetch_func)}")
                        self.logger.error(f"🚨 KEYERROR DEBUG: Missing key: '{key_missing}'")
                        self.logger.error(f"🚨 KEYERROR DEBUG: Endpoint: '{endpoint}'")
                        self.logger.error(f"🚨 KEYERROR DEBUG: Args: {args}")
                        self.logger.error(f"🚨 KEYERROR DEBUG: Kwargs: {kwargs}")
                        self.logger.error(f"🚨 KEYERROR DEBUG: Full exception: {str(e)}")
                        self.logger.error(f"🚨 KEYERROR DEBUG: Exception type: {type(e)}")
                        
                        # Get the full traceback to see exactly where the KeyError occurred
                        import traceback
                        tb_lines = traceback.format_exc().split('\n')
                        self.logger.error(f"🚨 KEYERROR DEBUG: Full traceback:")
                        for i, line in enumerate(tb_lines):
                            if line.strip():
                                self.logger.error(f"🚨 KEYERROR DEBUG: TB[{i:02d}]: {line}")
                        
                        # Add more context for debugging
                        self.logger.warning(f"⚠️  WARNING: Attempt {attempt} failed for {endpoint}: KeyError accessing '{key_missing}'. "
                                          f"Function: {fetch_func.__name__ if hasattr(fetch_func, '__name__') else str(fetch_func)}. "
                                          f"This may indicate a data structure mismatch rather than missing API support.")
                        
                        # For LSR and OHLCV endpoints, we know they work, so don't retry as aggressively
                        if endpoint in ['lsr', 'ohlcv'] and attempt >= 2:
                            self.logger.info(f"Stopping retries for {endpoint} early - returning default data")
                            return None
                        
                        if attempt < max_retries:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            self.logger.error(f"❌ ERROR: Failed to fetch {endpoint} after {max_retries} attempts: "
                                            f"KeyError accessing '{key_missing}'. Returning None for graceful degradation.")
                            return None
                            
                    except Exception as e:
                        last_exception = e
                        error_details = {
                            'endpoint': endpoint,
                            'function': fetch_func.__name__ if hasattr(fetch_func, '__name__') else str(fetch_func),
                            'args': str(args)[:100],  # Truncate long args
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                        
                        # Add comprehensive debugging for other exceptions
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Exception in {error_details['function']}")
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Exception type: {error_details['error_type']}")
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Exception message: {error_details['error_message']}")
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Endpoint: '{endpoint}'")
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Args: {args}")
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Kwargs: {kwargs}")
                        
                        # Get the full traceback
                        import traceback
                        tb_lines = traceback.format_exc().split('\n')
                        self.logger.error(f"🚨 EXCEPTION DEBUG: Full traceback:")
                        for i, line in enumerate(tb_lines):
                            if line.strip():
                                self.logger.error(f"🚨 EXCEPTION DEBUG: TB[{i:02d}]: {line}")
                        
                        self.logger.warning(f"⚠️  WARNING: Attempt {attempt} failed for {endpoint}: {error_details['error_type']}: {error_details['error_message']}. Retrying in {retry_delay}s...")
                        
                        if attempt < max_retries:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            detailed_error = f"{error_details['error_type']}: {error_details['error_message']} (function: {error_details['function']}, args: {error_details['args']})"
                            self.logger.error(f"❌ ERROR: Failed to fetch {endpoint} after {max_retries} attempts: {detailed_error}")
                            # Return None instead of raising exception to allow graceful degradation
                            return None
            
            start_time = time.time()
            
            # Initialize market data structure
            market_data = self._get_default_market_data(symbol)
            
            # Ensure complete market data structure is properly initialized to prevent KeyErrors
            self._ensure_market_data_structure(market_data, symbol)
            
            # Define coroutines for parallel fetching
            fetch_tasks = [
                fetch_with_retry('ticker', self._fetch_ticker, symbol),
                fetch_with_retry('orderbook', self.get_orderbook, symbol, 100),
                fetch_with_retry('trades', self.fetch_trades, symbol, limit=100),
                fetch_with_retry('lsr', self._fetch_long_short_ratio, symbol),
                fetch_with_retry('risk_limits', self._fetch_risk_limits, symbol),
            ]
            
            # Run all tasks concurrently
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            
            # Initialize market data with default values
            ticker, orderbook, trades, lsr, risk_limits = [None] * 5
            
            # Process results with safe access
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error fetching data: {str(result)}")
                    continue
                
                # Assign results to variables
                if i == 0: ticker = result
                elif i == 1: orderbook = result
                elif i == 2: trades = result
                elif i == 3: 
                    lsr = result
                    if lsr:
                        self.logger.info(f"LSR data received in fetch_market_data: {lsr}")
                elif i == 4: risk_limits = result
            
            # Try to fetch OHLCV data (this is CPU intensive so we don't parallelize)
            try:
                ohlcv = await fetch_with_retry('ohlcv', self._fetch_all_timeframes, symbol)
                if ohlcv and isinstance(ohlcv, dict):
                    # OHLCV data is already in the correct format from _fetch_all_timeframes
                    market_data['ohlcv'] = ohlcv
                    market_data['metadata']['ohlcv_success'] = True
                    self.logger.debug(f"Successfully stored OHLCV data with timeframes: {list(ohlcv.keys())}")
                else:
                    self.logger.warning("⚠️  WARNING: OHLCV data is None or not in expected format")
                    ohlcv = None
            except Exception as e:
                self.logger.error(f"Failed to fetch OHLCV data: {str(e)}")
                ohlcv = None
                
            # Try to fetch open interest history
            try:
                oi_history = await fetch_with_retry('oi_history', self.fetch_open_interest_history, symbol, '5min')
            except Exception as e:
                self.logger.error(f"Failed to fetch open interest history: {str(e)}")
                oi_history = None
                
            # Try to fetch historical volatility
            try:
                volatility = await fetch_with_retry('volatility', self._calculate_historical_volatility, symbol, '5min')
            except Exception as e:
                self.logger.error(f"Failed to fetch volatility: {str(e)}")
                volatility = None
            
            # Fill market data structure with fetched data using safe access
            if ticker and isinstance(ticker, dict):
                market_data['ticker'] = ticker
                market_data['metadata']['ticker_success'] = True
            
            if orderbook and isinstance(orderbook, dict):
                market_data['orderbook'] = orderbook
                market_data['metadata']['orderbook_success'] = True
            
            if trades and isinstance(trades, list):
                market_data['trades'] = trades
                market_data['metadata']['trades_success'] = True
                
                # Calculate volume sentiment directly from trades
                # Count buy/sell volume
                buy_volume = 0.0
                sell_volume = 0.0
                
                for trade in trades:
                    try:
                        # Convert size to float before adding
                        size = float(trade.get('size', 0))
                        side = trade.get('side', '').lower()
                        
                        if side == 'buy':
                            buy_volume += size
                        elif side == 'sell':
                            sell_volume += size
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Error processing trade size: {e}")
                
                # Update volume sentiment (structure guaranteed to exist)
                market_data['sentiment']['volume_sentiment'] = {
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume,
                    'timestamp': int(time.time() * 1000)
                }
            
            if lsr and isinstance(lsr, dict):
                # The _fetch_long_short_ratio method already returns processed data
                # Check if it's already in our format (with 'long' and 'short' keys)
                if 'long' in lsr and 'short' in lsr:
                    # Already in our format - use directly (structure guaranteed to exist)
                    market_data['sentiment']['long_short_ratio'] = lsr
                    market_data['metadata']['lsr_success'] = True
                    self.logger.info(f"Using pre-formatted LSR in market_data: {lsr}")
                elif 'list' in lsr and lsr.get('list'):
                    # Raw API format - convert to our format
                    latest_lsr = lsr['list'][0]
                    
                    try:
                        # Extract values and convert to float
                        buy_ratio = float(latest_lsr.get('buyRatio', '0.5')) * 100
                        sell_ratio = float(latest_lsr.get('sellRatio', '0.5')) * 100
                        timestamp = int(latest_lsr.get('timestamp', int(time.time() * 1000)))
                        
                        self.logger.info(f"Processing raw LSR in fetch_market_data: buy_ratio={buy_ratio}, sell_ratio={sell_ratio}")
                        
                        # Create structured format
                        lsr_data = {
                            'symbol': symbol,
                            'long': buy_ratio,  # Already converted to percentage (0-100)
                            'short': sell_ratio,
                            'timestamp': timestamp
                        }
                        
                        # Update LSR (structure guaranteed to exist)
                        market_data['sentiment']['long_short_ratio'] = lsr_data
                        market_data['metadata']['lsr_success'] = True
                        self.logger.info(f"Stored converted LSR in market_data: {lsr_data}")
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Error processing long/short ratio: {e}")
                        # Use default values
                        default_lsr = {
                            'symbol': symbol,
                            'long': 50.0,
                            'short': 50.0,
                            'timestamp': int(time.time() * 1000)
                        }
                        try:
                            market_data['sentiment']['long_short_ratio'] = default_lsr
                        except KeyError:
                            if 'sentiment' not in market_data:
                                market_data['sentiment'] = {}
                            market_data['sentiment']['long_short_ratio'] = default_lsr
                else:
                    self.logger.warning(f"Unexpected LSR format: {type(lsr)}, contents: {lsr}")
                    # Use default values
                    default_lsr = {
                        'symbol': symbol,
                        'long': 50.0,
                        'short': 50.0,
                        'timestamp': int(time.time() * 1000)
                    }
                    try:
                        market_data['sentiment']['long_short_ratio'] = default_lsr
                    except KeyError:
                        if 'sentiment' not in market_data:
                            market_data['sentiment'] = {}
                        market_data['sentiment']['long_short_ratio'] = default_lsr
            else:
                self.logger.warning("⚠️  WARNING: No LSR data available, using default neutral values")
                # Ensure we always have LSR data structure even when API fails
                if 'sentiment' not in market_data:
                    market_data['sentiment'] = {}
                market_data['sentiment']['long_short_ratio'] = {
                    'symbol': symbol,
                    'long': 50.0,
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                }
                # Ensure we always have LSR data structure
                default_lsr = {
                    'symbol': symbol,
                    'long': 50.0,
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                }
                try:
                    market_data['sentiment']['long_short_ratio'] = default_lsr
                except KeyError:
                    if 'sentiment' not in market_data:
                        market_data['sentiment'] = {}
                    market_data['sentiment']['long_short_ratio'] = default_lsr
            
            if risk_limits and isinstance(risk_limits, dict):
                market_data['risk_limit'] = risk_limits
                market_data['metadata']['risk_limits_success'] = True
                
                # Create market mood from risk limits
                try:
                    if 'initialMargin' in risk_limits and 'maxLeverage' in risk_limits:
                        market_data['sentiment']['market_mood'] = {
                            'risk_level': 1,  # Default to lowest risk level
                            'max_leverage': float(risk_limits.get('maxLeverage', 100.0)),
                            'timestamp': int(time.time() * 1000)
                        }
                except KeyError as e:
                    self.logger.warning(f"KeyError updating market mood: {e}")
                    # Ensure sentiment structure exists
                    if 'sentiment' not in market_data:
                        market_data['sentiment'] = {}
                    market_data['sentiment']['market_mood'] = {
                        'risk_level': 1,
                        'max_leverage': 100.0,
                        'timestamp': int(time.time() * 1000)
                    }
            
            # Set funding rate in sentiment if ticker data is available
            try:
                if ticker and 'fundingRate' in ticker:
                    market_data['sentiment']['funding_rate'] = {
                        'rate': float(ticker.get('fundingRate', 0.0)),
                        'next_funding_time': int(ticker.get('nextFundingTime', int(time.time() * 1000) + 28800000))  # Default to 8 hours from now
                    }
                    self.logger.debug(f"Set funding_rate in sentiment: {market_data['sentiment']['funding_rate']}")
            except KeyError as e:
                self.logger.warning(f"KeyError updating funding rate: {e}")
                # Ensure sentiment structure exists
                if 'sentiment' not in market_data:
                    market_data['sentiment'] = {}
                if ticker and 'fundingRate' in ticker:
                    market_data['sentiment']['funding_rate'] = {
                        'rate': float(ticker.get('fundingRate', 0.0)),
                        'next_funding_time': int(ticker.get('nextFundingTime', int(time.time() * 1000) + 28800000))
                    }
            
            # Ensure open interest structure exists with safe access
            try:
                if 'open_interest' not in market_data['sentiment']:
                    market_data['sentiment']['open_interest'] = {
                        'current': 0.0,
                        'previous': 0.0,
                        'change': 0.0,
                        'timestamp': int(time.time() * 1000),
                        'value': 0.0,  # ← Ensure 'value' field is always present
                        'history': []
                    }
            except KeyError:
                if 'sentiment' not in market_data:
                    market_data['sentiment'] = {}
                market_data['sentiment']['open_interest'] = {
                    'current': 0.0,
                    'previous': 0.0,
                    'change': 0.0,
                    'timestamp': int(time.time() * 1000),
                    'value': 0.0,  # ← Ensure 'value' field is always present
                    'history': []
                }
            
            if ohlcv:
                market_data['ohlcv'] = ohlcv
                market_data['metadata']['ohlcv_success'] = True
            
            if oi_history and isinstance(oi_history, dict):
                # Extract history list - support both 'list' and 'history' keys
                if 'list' in oi_history:
                    history_list = oi_history.get('list', [])
                elif 'history' in oi_history:
                    history_list = oi_history.get('history', [])
                else:
                    history_list = []
                
                if history_list:
                    try:
                        market_data['sentiment']['open_interest']['history'] = history_list
                        market_data['metadata']['oi_history_success'] = True
                        self.logger.debug(f"Successfully stored OI history with {len(history_list)} entries")
                    except KeyError as e:
                        self.logger.warning(f"KeyError updating OI history: {e}")
                        # Ensure structure exists
                        if 'sentiment' not in market_data:
                            market_data['sentiment'] = {}
                        if 'open_interest' not in market_data['sentiment']:
                            market_data['sentiment']['open_interest'] = {
                                'current': 0.0,
                                'previous': 0.0,
                                'change': 0.0,
                                'timestamp': int(time.time() * 1000),
                                'value': 0.0,
                                'history': []
                            }
                        market_data['sentiment']['open_interest']['history'] = history_list
                        market_data['metadata']['oi_history_success'] = True
                else:
                    self.logger.warning("OI history list is empty")
            else:
                self.logger.warning("⚠️  WARNING: No OI history data available or not in expected format")
            
            if volatility and isinstance(volatility, dict):
                # Update volatility (structure guaranteed to exist)
                market_data['sentiment']['volatility'] = volatility
                market_data['metadata']['volatility_success'] = True
                self.logger.debug(f"Successfully stored volatility data: {volatility.get('value', 'N/A')}")
            else:
                self.logger.warning("⚠️  WARNING: No volatility data available or not in expected format")
            
            end_time = time.time()
            self.logger.debug(f"Market data fetch completed in {end_time - start_time:.3f}s")
            
            # Log market data structure for debugging
            self.logger.debug("Market data structure before validation:")
            self.logger.debug(f"Sentiment data: {market_data['sentiment']}")
            if volatility:
                self.logger.debug(f"Volatility data: {market_data['sentiment']['volatility']}")
            if 'open_interest' in market_data['sentiment']:
                oi = market_data['sentiment']['open_interest']
                self.logger.debug(f"Open interest data: current={oi.get('current', 0)}, previous={oi.get('previous', 0)}, history entries={len(oi.get('history', []))}")
            if risk_limits:
                self.logger.debug(f"Risk limits: {risk_limits}")
            
            # Validate market data
            if not self.validate_market_data(market_data):
                self.logger.warning("Market data validation failed")
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # Return default structure instead of empty dict
            return self._get_default_market_data(symbol)

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status.
        
        Returns:
            Dict with rate limit information
        """
        status = {
            'remaining': self.rate_limit_status.get('remaining', 600),
            'limit': self.rate_limit_status.get('limit', 600),
            'reset_timestamp': self.rate_limit_status.get('reset_timestamp'),
            'percentage_used': 0
        }
        
        if status['limit'] > 0:
            status['percentage_used'] = ((status['limit'] - status['remaining']) / status['limit']) * 100
        
        # Add global bucket info
        global_bucket = self._rate_limit_buckets.get('global', [])
        now = time.time()
        window_start = now - 5.0
        active_requests = len([ts for ts in global_bucket if ts > window_start])
        
        status['active_requests_5s'] = active_requests
        status['capacity_5s'] = 600 - active_requests
        
        return status
    
    async def _fetch_with_rate_limit(self, endpoint: str, fetch_func: Callable, *args, **kwargs) -> Any:
        """Execute fetch function with rate limiting."""
        await self._check_rate_limit(endpoint)
        return await fetch_func(*args, **kwargs)

    async def _fetch_all_timeframes(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for all required timeframes."""
        try:
            # Define timeframe mapping - use Bybit's format but store with standard names
            timeframes = {
                '1': 'base',    # 1 minute - store as 'base'
                '5': 'ltf',     # 5 minutes
                '30': 'mtf',    # 30 minutes
                '240': 'htf'    # 4 hours (240 minutes)
            }
            
            ohlcv_data = {}
            
            # Fetch each timeframe with rate limiting
            for bybit_interval, tf_name in timeframes.items():
                max_retries = 3
                retry_delay = 1.0
                
                for attempt in range(max_retries):
                    try:
                        # Check rate limit before each OHLCV fetch
                        await self._check_rate_limit('kline', category='linear')
                        
                        self.logger.debug(f"Fetching {bybit_interval} interval ({tf_name}) data for {symbol}")
                        candles = await self._fetch_ohlcv(symbol, bybit_interval)
                        
                        if not candles:
                            self.logger.error(f"No candles returned for {symbol} @ {bybit_interval}")
                            if attempt == max_retries - 1:
                                # Create an empty DataFrame with the correct structure instead of raising
                                ohlcv_data[tf_name] = pd.DataFrame(
                                    columns=['open', 'high', 'low', 'close', 'volume']
                                )
                                # Ensure proper column data types even for empty DataFrame
                                ohlcv_data[tf_name] = ohlcv_data[tf_name].astype({
                                    'open': 'float64',
                                    'high': 'float64',
                                    'low': 'float64',
                                    'close': 'float64',
                                    'volume': 'float64'
                                })
                                # Create a proper datetime index
                                ohlcv_data[tf_name].index = pd.DatetimeIndex([])
                                ohlcv_data[tf_name].index.name = 'timestamp'
                                self.logger.warning(f"Created empty DataFrame for {tf_name} timeframe after all retries failed")
                                break
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        
                        # Process the candles
                        processed_candles = []
                        valid_candle_count = 0
                        invalid_candle_count = 0
                        
                        for candle in candles:
                            try:
                                # Verify candle has at least 6 elements
                                if len(candle) < 6:
                                    self.logger.warning(f"Skipping candle with insufficient elements: {candle}")
                                    invalid_candle_count += 1
                                    continue
                                
                                # Apply explicit typecasting with validation
                                timestamp = int(candle[0])
                                open_price = float(candle[1])
                                high_price = float(candle[2])
                                low_price = float(candle[3])
                                close_price = float(candle[4])
                                volume = float(candle[5])
                                
                                # Basic sanity checks
                                if timestamp <= 0 or pd.isna(timestamp):
                                    self.logger.warning(f"Skipping candle with invalid timestamp: {candle}")
                                    invalid_candle_count += 1
                                    continue
                                    
                                if (pd.isna(open_price) or pd.isna(high_price) or 
                                    pd.isna(low_price) or pd.isna(close_price) or pd.isna(volume)):
                                    self.logger.warning(f"Skipping candle with NaN values: {candle}")
                                    invalid_candle_count += 1
                                    continue
                                
                                # Add valid candle
                                processed_candles.append([
                                    timestamp,
                                    open_price,
                                    high_price,
                                    low_price,
                                    close_price,
                                    volume
                                ])
                                valid_candle_count += 1
                                
                            except (IndexError, ValueError, TypeError) as e:
                                self.logger.warning(f"Error processing candle: {str(e)}, candle: {candle}")
                                invalid_candle_count += 1
                                continue
                        
                        # Log candle processing results
                        self.logger.debug(f"Processed {valid_candle_count} valid candles, {invalid_candle_count} invalid for {tf_name}")
                        
                        if not processed_candles:
                            self.logger.error(f"No valid candles after processing for {symbol} @ {bybit_interval}")
                            if attempt == max_retries - 1:
                                # Create an empty DataFrame with the correct structure
                                ohlcv_data[tf_name] = pd.DataFrame(
                                    columns=['open', 'high', 'low', 'close', 'volume']
                                )
                                # Ensure proper column data types even for empty DataFrame
                                ohlcv_data[tf_name] = ohlcv_data[tf_name].astype({
                                    'open': 'float64',
                                    'high': 'float64',
                                    'low': 'float64',
                                    'close': 'float64',
                                    'volume': 'float64'
                                })
                                # Create a proper datetime index
                                ohlcv_data[tf_name].index = pd.DatetimeIndex([])
                                ohlcv_data[tf_name].index.name = 'timestamp'
                                self.logger.warning(f"Created empty DataFrame for {tf_name} timeframe after processing")
                                break
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                            
                        try:
                            # Create DataFrame from processed candles with explicit column names
                            df = pd.DataFrame(
                                processed_candles,
                                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                            )
                            
                            # Convert timestamp to datetime - handle potential errors
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            
                            # Validate timestamp conversion
                            if df['timestamp'].isna().any():
                                self.logger.error(f"Timestamp conversion resulted in NaT values for {tf_name}")
                                df = df[~df['timestamp'].isna()]  # Remove rows with NaT timestamps
                                if df.empty:
                                    raise ValueError("All timestamps were invalid after conversion")
                                    
                            # Set timestamp as index and sort
                            df.set_index('timestamp', inplace=True)
                            df = df.sort_index()
                            
                            # Explicit validation
                            if df.empty:
                                self.logger.error(f"Empty DataFrame after processing for {tf_name}")
                                raise ValueError("Empty DataFrame")
                                
                            if df.isnull().values.any():
                                # Identify which columns have null values
                                null_counts = df.isnull().sum()
                                self.logger.warning(f"DataFrame contains null values for {tf_name}: {null_counts}")
                                
                                # Fill null values or drop rows with nulls based on severity
                                if null_counts.max() > len(df) * 0.5:  # If more than 50% of a column is null
                                    self.logger.error(f"Too many null values in {tf_name} DataFrame")
                                    raise ValueError("DataFrame contains too many null values")
                                else:
                                    # Try to fill nulls with appropriate values or drop those rows
                                    self.logger.warning(f"Filling or dropping null values in {tf_name} DataFrame")
                                    # Forward fill, then backward fill to handle gaps
                                    df = df.fillna(method='ffill').fillna(method='bfill')
                                    
                                    if df.isnull().values.any():
                                        # If still have nulls, drop those rows
                                        df = df.dropna()
                                        if df.empty:
                                            raise ValueError("DataFrame empty after dropping null values")
                                            
                            # Ensure proper data types
                            df = df.astype({
                                'open': 'float64',
                                'high': 'float64',
                                'low': 'float64',
                                'close': 'float64',
                                'volume': 'float64'
                            })
                            
                            ohlcv_data[tf_name] = df
                            self.logger.debug(f"Successfully processed {len(df)} candles for {tf_name}")
                            break
                            
                        except Exception as e:
                            self.logger.error(f"Error creating DataFrame for {symbol} @ {bybit_interval}: {str(e)}")
                            self.logger.debug(f"First few processed candles: {processed_candles[:2] if processed_candles else []}")
                            if attempt == max_retries - 1:
                                # Create a fallback empty DataFrame
                                ohlcv_data[tf_name] = pd.DataFrame(
                                    columns=['open', 'high', 'low', 'close', 'volume']
                                )
                                # Ensure proper column data types even for empty DataFrame
                                ohlcv_data[tf_name] = ohlcv_data[tf_name].astype({
                                    'open': 'float64',
                                    'high': 'float64',
                                    'low': 'float64',
                                    'close': 'float64',
                                    'volume': 'float64'
                                })
                                # Create a proper datetime index
                                ohlcv_data[tf_name].index = pd.DatetimeIndex([])
                                ohlcv_data[tf_name].index.name = 'timestamp'
                                self.logger.warning(f"Created empty fallback DataFrame for {tf_name} after processing errors")
                            else:
                                await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                            
                    except RateLimitError as e:
                        retry_after = getattr(e, 'retry_after', retry_delay * (attempt + 1))
                        if attempt == max_retries - 1:
                            # Create a fallback empty DataFrame
                            ohlcv_data[tf_name] = pd.DataFrame(
                                columns=['open', 'high', 'low', 'close', 'volume']
                            )
                            # Ensure proper column data types even for empty DataFrame
                            ohlcv_data[tf_name] = ohlcv_data[tf_name].astype({
                                'open': 'float64',
                                'high': 'float64',
                                'low': 'float64',
                                'close': 'float64',
                                'volume': 'float64'
                            })
                            # Create a proper datetime index
                            ohlcv_data[tf_name].index = pd.DatetimeIndex([])
                            ohlcv_data[tf_name].index.name = 'timestamp'
                            self.logger.warning(f"Created empty fallback DataFrame for {tf_name} after rate limit errors")
                        else:
                            self.logger.warning(f"Rate limit hit for {bybit_interval}, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                        continue
                        
                    except Exception as e:
                        self.logger.error(f"Error fetching {bybit_interval} interval: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        if attempt == max_retries - 1:
                            # Create a fallback empty DataFrame
                            ohlcv_data[tf_name] = pd.DataFrame(
                                columns=['open', 'high', 'low', 'close', 'volume']
                            )
                            # Ensure proper column data types even for empty DataFrame
                            ohlcv_data[tf_name] = ohlcv_data[tf_name].astype({
                                'open': 'float64',
                                'high': 'float64',
                                'low': 'float64',
                                'close': 'float64',
                                'volume': 'float64'
                            })
                            # Create a proper datetime index
                            ohlcv_data[tf_name].index = pd.DatetimeIndex([])
                            ohlcv_data[tf_name].index.name = 'timestamp'
                            self.logger.warning(f"Created empty fallback DataFrame for {tf_name} after general errors")
                        else:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
            
            # Verify all timeframes were fetched
            expected_timeframes = set(timeframes.values())
            missing_timeframes = expected_timeframes - set(ohlcv_data.keys())
            if missing_timeframes:
                self.logger.error(f"Missing timeframes after fetch: {missing_timeframes}")
                # Create empty DataFrames for missing timeframes
                for tf in missing_timeframes:
                    ohlcv_data[tf] = pd.DataFrame(
                        columns=['open', 'high', 'low', 'close', 'volume']
                    )
                    # Ensure proper column data types even for empty DataFrame
                    ohlcv_data[tf] = ohlcv_data[tf].astype({
                        'open': 'float64',
                        'high': 'float64',
                        'low': 'float64',
                        'close': 'float64',
                        'volume': 'float64'
                    })
                    # Create a proper datetime index
                    ohlcv_data[tf].index = pd.DatetimeIndex([])
                    ohlcv_data[tf].index.name = 'timestamp'
                    self.logger.warning(f"Created empty DataFrame for missing {tf} timeframe")
            
            # Final validation of all dataframes
            for tf, df in ohlcv_data.items():
                self.logger.debug(f"Final {tf} DataFrame shape: {df.shape}, empty: {df.empty}")
                if df.empty:
                    self.logger.warning(f"Final {tf} DataFrame is empty")
                elif len(df) < 10:
                    self.logger.warning(f"Final {tf} DataFrame has only {len(df)} candles, which may be insufficient")
            
            return ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Critical error fetching timeframes for {symbol}: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            # Return empty DataFrames for all timeframes as a fallback
            self.logger.warning("Returning empty DataFrames for all timeframes due to critical error")
            ohlcv_data = {}
            for tf_name in ['base', 'ltf', 'mtf', 'htf']:
                ohlcv_data[tf_name] = pd.DataFrame(
                    columns=['open', 'high', 'low', 'close', 'volume']
                )
                # Ensure proper column data types even for empty DataFrame
                ohlcv_data[tf_name] = ohlcv_data[tf_name].astype({
                    'open': 'float64',
                    'high': 'float64',
                    'low': 'float64',
                    'close': 'float64',
                    'volume': 'float64'
                })
                # Create a proper datetime index
                ohlcv_data[tf_name].index = pd.DatetimeIndex([])
                ohlcv_data[tf_name].index.name = 'timestamp'
            return ohlcv_data

    async def _fetch_ohlcv(self, symbol: str, interval: str) -> List[List[Any]]:
        """Fetch OHLCV data for a specific interval."""
        try:
            self.logger.debug(f"Making OHLCV request for {symbol} @ {interval}")
            
            # Convert timeframe from standard format to Bybit's format if needed
            # First check if the interval is already in Bybit's numeric format
            bybit_interval = interval
            if not interval.isdigit() and interval not in ['D', 'W', 'M']:
                # If not numeric, try to convert from standard format
                bybit_interval = {
                    '1m': '1',
                    '3m': '3',
                    '5m': '5',
                    '15m': '15',
                    '30m': '30',
                    '1h': '60',
                    '2h': '120',
                    '4h': '240',
                    '6h': '360',
                    '12h': '720',
                    '1d': 'D',
                    '1w': 'W',
                    '1M': 'M'
                }.get(interval, interval)  # Keep original if not found
            
            # Get current time in milliseconds
            end_time = int(time.time() * 1000)
            
            # Calculate start time based on timeframe and limit
            # Default limit is 200, so calculate start time accordingly
            limit = 200
            
            # Map interval to minutes for time calculations
            minutes_map = {
                '1': 1,
                '3': 3,
                '5': 5,
                '15': 15,
                '30': 30,
                '60': 60,
                '120': 120,
                '240': 240,
                '360': 360,
                '720': 720,
                'D': 1440,
                'W': 10080,
                'M': 43200
            }
            
            # Get minutes value for the interval (default to 1 if not found)
            timeframe_minutes = minutes_map.get(bybit_interval, 1)
            
            # Calculate milliseconds to go back based on timeframe and limit
            # Add 20% buffer to ensure we get enough data
            minutes_back = timeframe_minutes * limit * 1.2
            start_time = end_time - (minutes_back * 60 * 1000)
            
            response = await self._make_request('GET', '/v5/market/kline', {
                'category': 'linear',  # Always use linear category for market monitor
                'symbol': symbol,
                'interval': bybit_interval,
                'limit': 200,  # Maximum allowed by Bybit
                'start': start_time,
                'end': end_time
            })
            
            if not response or response.get('retCode') != 0:
                self.logger.error(f"Failed to fetch OHLCV data: {response}")
                return []
            
            # Extract and return candles
            candles = response.get('result', {}).get('list', [])
            if not candles:
                self.logger.warning(f"No candles returned for {symbol} @ {interval}")
            else:
                self.logger.debug(f"Fetched {len(candles)} candles for {symbol} @ {interval}")
            
            return candles
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {str(e)}")
            return []

    async def _subscribe_to_liquidations(self, symbol: str) -> None:
        """Subscribe to liquidation feed for a symbol."""
        try:
            # Subscribe to liquidation topic
            topic = f"allLiquidation.{symbol}"
            await self.ws.subscribe([topic])
            self.logger.info(f"Subscribed to liquidation feed for {symbol}")
            
            # Register message handler
            self.ws.on_message(topic, self._handle_liquidation_update)
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to liquidation feed: {str(e)}")

    async def _process_market_data(self, symbol: str) -> Dict[str, Any]:
        """Process and combine all market data.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict containing processed market data including trades and sentiment
        """
        try:
            market_data = {
                'symbol': symbol,
                'exchange': 'bybit',  # Add the exchange identifier
                'timestamp': int(time.time() * 1000),
                'timeframes': {},  # Will be populated with candle data
                'trades': [],
                'orderbook': {},
                'sentiment': {
                    'liquidations': [],
                    'funding_rate': None,
                    'long_short_ratio': None
                },
                'ticker': {},
                'risk_limits': {},  # Required by validation
                'open_interest': {}  # Add an empty open_interest dictionary
            }
            
            # Process trades
            trades = await self._fetch_recent_trades(symbol)
            if trades:
                processed_trades = []
                for trade in trades:
                    if all(k in trade for k in ['execId', 'price', 'size', 'side', 'time']):
                        processed_trades.append({
                            'id': str(trade['execId']),  # Single point of transformation
                            'price': float(trade['price']),
                            'size': float(trade['size']),
                            'side': str(trade['side']).lower(),
                            'time': int(trade['time'])
                        })
                market_data['trades'] = processed_trades
                
            # Get timeframes data - use Bybit's numeric format directly
            intervals = {
                '1': '1',  # 1 minute
                '5': '5',  # 5 minutes
                '30': '30',  # 30 minutes
                '240': '240'  # 4 hours
            }
            for interval_key, interval_value in intervals.items():
                candles = await self._fetch_klines(symbol, interval_value)
                if candles:
                    market_data['timeframes'][interval_key] = candles
                    
            # Get orderbook data
            orderbook = await self.fetch_order_book(symbol)
            if orderbook:
                market_data['orderbook'] = orderbook
                
            # Get ticker data
            ticker = await self._fetch_ticker(symbol) 
            if ticker:
                market_data['ticker'] = ticker
                
            # Get open interest data
            oi_history = await self.fetch_open_interest_history(symbol, interval='5', limit=200)  # Use Bybit's format
            oi_history_list = []
            
            # Get current OI from ticker
            current_oi = 0.0
            previous_oi = 0.0
            
            if ticker and 'openInterest' in ticker:
                current_oi = float(ticker['openInterest'])
            
            # Process OI history if available
            if oi_history and 'history' in oi_history and oi_history['history']:
                oi_history_list = oi_history['history']
                
                # Get the most recent open interest value from history
                if len(oi_history_list) > 0:
                    current_oi = float(oi_history_list[0]['value'])
                
                # Get the previous value (second most recent or 98% of current if not available)
                if len(oi_history_list) > 1:
                    previous_oi = float(oi_history_list[1]['value'])
                    self.logger.debug(f"Using OI history values: current={current_oi}, previous={previous_oi}")
                else:
                    previous_oi = current_oi * 0.98  # Default fallback
                    self.logger.debug(f"Only one OI history entry, estimating previous as 98% of current: {previous_oi}")
            else:
                # If no history available but we have current value from ticker, create synthetic history
                self.logger.debug(f"No OI history available, using ticker OI: {current_oi}")
                previous_oi = current_oi * 0.98  # Estimate previous as 98% of current
                
                # Create synthetic history
                now = int(time.time() * 1000)
                oi_history_list = [
                    {'timestamp': now, 'value': current_oi, 'symbol': symbol},
                    {'timestamp': now - 5*60*1000, 'value': previous_oi, 'symbol': symbol},  # 5 min ago
                    {'timestamp': now - 10*60*1000, 'value': previous_oi * 0.995, 'symbol': symbol},  # 10 min ago
                    {'timestamp': now - 15*60*1000, 'value': previous_oi * 0.99, 'symbol': symbol},  # 15 min ago
                ]
                self.logger.debug(f"Created synthetic OI history with {len(oi_history_list)} entries")
            
            # Add to market data
            market_data['open_interest'] = {
                'current': float(current_oi),
                'previous': float(previous_oi),
                'history': oi_history_list,
                'timestamp': int(time.time() * 1000)
            }
            
            # Add direct reference to history for easier access
            market_data['open_interest_history'] = oi_history_list
            
            # Also add to sentiment for backward compatibility
            market_data['sentiment']['open_interest'] = {
                'current': float(current_oi),
                'previous': float(previous_oi)
            }
            
            return market_data
                
        except Exception as e:
            self.logger.error(f"Error processing market data for {symbol}: {str(e)}", exc_info=True)
            return {}

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate exchange configuration."""
        try:
            # Log the config structure for debugging
            self.logger.debug(f"Config keys: {list(config.keys())}")
            
            # Check required keys directly since we're already getting Bybit config
            required_keys = ['enabled', 'api_credentials', 'rest_endpoint', 'websocket']
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                self.logger.error(f"Missing required Bybit config keys: {missing_keys}")
                return False
            
            # Validate API credentials
            credentials = config.get('api_credentials', {})
            if not credentials.get('api_key') or not credentials.get('api_secret'):
                self.logger.error("Missing API credentials")
                return False
            
            # Validate rate limits
            rate_limits = config.get('rate_limits', {})
            if not rate_limits.get('requests_per_second') or not rate_limits.get('requests_per_minute'):
                self.logger.warning("Missing rate limit configuration, using defaults")
            
            # Validate websocket config if enabled
            ws_config = config.get('websocket', {})
            if ws_config.get('enabled'):
                required_ws_keys = ['mainnet_endpoint', 'channels']
                missing_ws_keys = [key for key in required_ws_keys if key not in ws_config]
                if missing_ws_keys:
                    self.logger.error(f"Missing required websocket config keys: {missing_ws_keys}")
                    return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating config: {str(e)}", exc_info=True)
            return False

    async def get_markets(self) -> List[Dict[str, Any]]:
        """Get comprehensive market information combining static and dynamic data.
        
        Returns:
            List of market dictionaries containing complete market information
        """
        try:
            # Get static market info
            symbols = await self.fetch_market_symbols()
            
            # Get dynamic market info
            tickers = await self.fetch_market_tickers()
            
            # Combine the information
            markets = {}
            
            # Process symbols
            if isinstance(symbols, dict) and 'result' in symbols:
                symbols = symbols['result'].get('list', [])
            elif not isinstance(symbols, list):
                symbols = []
                
            for symbol in symbols:
                if isinstance(symbol, dict):
                    markets[symbol.get('symbol')] = symbol
                    
            # Process tickers
            if isinstance(tickers, dict) and 'result' in tickers:
                tickers = tickers['result'].get('list', [])
            elif not isinstance(tickers, list):
                tickers = []
                
            for ticker in tickers:
                if isinstance(ticker, dict):
                    symbol = ticker.get('symbol')
                    if symbol:
                        if symbol in markets:
                            markets[symbol].update(ticker)
                        else:
                            markets[symbol] = ticker
                    
            # Convert to list and ensure consistent format
            result = []
            for symbol, data in markets.items():
                try:
                    processed_market = {
            'symbol': symbol,
                        'active': True,  # If it's in tickers, it's trading
                        'turnover24h': float(data.get('turnover24h', 0)),
                        'volume24h': float(data.get('volume24h', 0)),
                            'price': {
                            'last': float(data.get('lastPrice', 0)),
                            'high': float(data.get('highPrice24h', 0)),
                            'low': float(data.get('lowPrice24h', 0)),
                            'change_24h': float(data.get('price24hPcnt', 0))
                        },
                        'bid': float(data.get('bid1Price', 0)),
                        'ask': float(data.get('ask1Price', 0)),
                        'info': data
                    }
                    result.append(processed_market)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error processing market {symbol}: {e}")
                    continue
                    
            self.logger.info(f"Successfully fetched {len(result)} complete market records")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting complete market data: {str(e)}")
            return []

    async def fetch_market_symbols(self) -> List[Dict[str, Any]]:
        """Fetch available symbols and their specifications from Bybit API.
        
        Returns:
            List of symbol dictionaries containing symbol specifications
        """
        try:
            self.logger.debug("Fetching market symbols from Bybit V5 API...")
            
            # Make request for linear futures symbols
            response = await self._make_request('GET', '/v5/market/instruments-info', {
                'category': 'linear'
            })
            
            if not response:
                self.logger.error("Empty response from instruments-info endpoint")
                return []
                
            if 'retCode' in response and response['retCode'] != 0:
                self.logger.error(f"API error: {response.get('retMsg', 'Unknown error')}")
                return []
                
            if 'result' not in response or 'list' not in response['result']:
                self.logger.error("Invalid response structure")
                return []
                
            symbols_list = response['result']['list']
            self.logger.debug(f"Fetched {len(symbols_list)} symbols from Bybit API")
            
            return symbols_list
            
        except Exception as e:
            self.logger.error(f"Error fetching market symbols: {str(e)}")
            return []

    async def fetch_market_tickers(self) -> List[Dict[str, Any]]:
        """Fetch market information with current prices and volumes.
        
        Returns:
            List of market dictionaries containing current market data
        """
        try:
            self.logger.debug("Fetching market tickers from Bybit V5 API...")
            response = await self._make_request('GET', '/v5/market/tickers', {
                'category': 'linear'
            })
            
            if not response:
                self.logger.error("Empty response from tickers endpoint")
                return []
                
            if 'retCode' in response and response['retCode'] != 0:
                self.logger.error(f"API error: {response.get('retMsg', 'Unknown error')}")
                return []
                
            if 'result' not in response:
                self.logger.error(f"Missing 'result' in response. Response keys: {list(response.keys())}")
                return []
                
            result = response['result']
            if not isinstance(result, dict):
                self.logger.error(f"Invalid result type: {type(result)}")
                return []
                
            if 'list' not in result:
                self.logger.error(f"Missing 'list' in result. Result keys: {list(result.keys())}")
                return []
                
            ticker_list = result['list']
            if not ticker_list:
                self.logger.warning("Empty ticker list received")
                return []
                
            self.logger.debug(f"Processing {len(ticker_list)} market tickers")
            
            # Initialize quality metrics
            quality_metrics = {
                'total_count': len(ticker_list),
                'processed_count': 0,
                'valid_count': 0,
                'invalid_count': 0,
                'filtered_symbols': [],
                'total_volume': 0.0,
                'total_turnover': 0.0
            }
            
            markets = []
            for idx, market in enumerate(ticker_list):
                try:
                    quality_metrics['processed_count'] += 1
                    
                    if not isinstance(market, dict):
                        self.logger.warning(f"Invalid market data type: {type(market)}")
                        quality_metrics['invalid_count'] += 1
                        continue
                        
                    # Log raw market data for debugging (first few entries)
                    if idx < 3:
                        self.logger.debug(
                            "Market sample:\n"
                            f"Keys: {list(market.keys())}\n"
                            f"Types: {{symbol: {type(market.get('symbol'))}, turnover24h: {type(market.get('turnover24h'))}}}\n"
                            f"Snippet: {{symbol: {market.get('symbol')}, turnover24h: {str(market.get('turnover24h'))[:15]}...}}"
                        )
                    
                    # Safe numeric conversion function
                    def safe_float(value, default=0.0):
                        if value is None:
                            return default
                        try:
                            # Remove any commas and convert to float
                            cleaned = str(value).replace(',', '')
                            return float(cleaned)
                        except (ValueError, TypeError):
                            self.logger.warning(f"Could not convert {value} to float, using default {default}")
                            return default
                    
                    # Process market data with safe conversion
                    processed_market = {
                        'symbol': market['symbol'],
                        'active': True,  # If it's in tickers, it's trading
                        'turnover24h': safe_float(market.get('turnover24h')),
                        'volume24h': safe_float(market.get('volume24h')),
                        # Add the fields expected by market reporter
                        'turnover': safe_float(market.get('turnover24h')),
                        'volume': safe_float(market.get('volume24h')),
                        'price': {
                            'last': safe_float(market.get('lastPrice')),
                            'high': safe_float(market.get('highPrice24h')),
                            'low': safe_float(market.get('lowPrice24h')),
                            'change_24h': safe_float(market.get('price24hPcnt'))
                        },
                        'bid': safe_float(market.get('bid1Price')),
                        'ask': safe_float(market.get('ask1Price')),
                        'info': market
                    }
                    
                    # Add before validation checks:
                    try:
                        processed_market['volume24h'] = float(processed_market['volume24h'])
                        processed_market['turnover24h'] = float(processed_market['turnover24h'])
                        processed_market['volume'] = float(processed_market['volume'])
                        processed_market['turnover'] = float(processed_market['turnover'])
                    except ValueError as e:
                        self.logger.error(f"Invalid numeric value in market data: {e}")
                        quality_metrics['invalid_count'] += 1
                        continue
                    
                    # Then perform validation checks...
                    validation_checks = [
                        ('symbol_format', bool(re.match(r'^[A-Z0-9]{1,}(USDT)$', processed_market['symbol']))),
                        ('volume24h', processed_market['volume24h'] >= self.config.get('market_data', {}).get('validation', {}).get('volume', {}).get('min_value', 0)),
                        ('turnover24h', processed_market['turnover24h'] >= self.config.get('market_data', {}).get('validation', {}).get('turnover', {}).get('min_value', 0))
                    ]
                    
                    # Check all validation criteria
                    is_valid = True
                    for field, check in validation_checks:
                        if not check:
                            is_valid = False
                            self.logger.debug(f"Symbol {processed_market['symbol']} failed validation: {field}")
                            break
                    
                    if not is_valid:
                        quality_metrics['invalid_count'] += 1
                        quality_metrics['filtered_symbols'].append({
                            'symbol': processed_market['symbol'],
                            'turnover24h': processed_market['turnover24h'],
                            'volume24h': processed_market['volume24h']
                        })
                        continue
                    
                    # Update quality metrics
                    quality_metrics['valid_count'] += 1
                    quality_metrics['total_volume'] += processed_market['volume24h']
                    quality_metrics['total_turnover'] += processed_market['turnover24h']
                    
                    # Add to validation_checks
                    symbol_valid = bool(re.match(r'^[A-Z0-9]{1,}(USDT)$', processed_market['symbol']))
                    validation_checks.append(('symbol_format', symbol_valid))
                    
                    markets.append(processed_market)
                    
                except (KeyError, ValueError) as e:
                    self.logger.error(f"Error processing market {market.get('symbol', 'unknown')}: {e}")
                    self.logger.debug(f"Problematic market data: {market}")
                    quality_metrics['invalid_count'] += 1
                    continue
            
            # Log quality metrics
            self.logger.info(
                f"Market Data Quality Report:\n"
                f"Total Markets: {quality_metrics['total_count']}\n"
                f"Valid Markets: {quality_metrics['valid_count']}\n"
                f"Invalid/Filtered: {quality_metrics['invalid_count']}\n"
                f"Total Volume: ${quality_metrics['total_volume']:,.2f}\n"
                f"Total Turnover: ${quality_metrics['total_turnover']:,.2f}"
            )
            
            # Log filtered symbols (up to 10)
            if quality_metrics['filtered_symbols']:
                filtered_sample = quality_metrics['filtered_symbols'][:10]
                filtered_log = "\nFiltered Symbols Sample:\n" + "\n".join(
                    f"{s['symbol']}: Vol=${s['volume24h']:,.2f} Turn=${s['turnover24h']:,.2f}"
                    for s in filtered_sample
                )
                if len(quality_metrics['filtered_symbols']) > 10:
                    filtered_log += f"\n...and {len(quality_metrics['filtered_symbols']) - 10} more"
                self.logger.debug(filtered_log)
            
            self.logger.info(f"Successfully processed {len(markets)} valid market records out of {len(ticker_list)} total")
            return markets
            
        except GeneratorExit:
            self.logger.info("Market tickers fetch cancelled due to GeneratorExit")
            raise
        except asyncio.CancelledError:
            self.logger.info("Market tickers fetch cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching market tickers: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return []

    async def _get_ws_url(self) -> str:
        """Get WebSocket URL based on configuration."""
        try:
            # Get base URL from config
            base_url = self.config.get('ws_url', 'wss://stream.bybit.com')
            
            # Add API version path
            url = f"{base_url}/v5"
            
            # Add public/linear path
            if not url.endswith('/public/linear'):
                url = f"{url}/public/linear"
                
            self.logger.debug(f"Using WebSocket URL: {url}")
            return url
            
        except Exception as e:
            self.logger.error(f"Error constructing WebSocket URL: {str(e)}")
            raise

    def _get_symbol_string(self, symbol: Union[str, dict]) -> str:
        """
        Convert various symbol formats to the proper format for API calls.
        
        Args:
            symbol: Symbol in various formats ('BTC/USDT', 'BTC/USDT:USDT', dict with 'symbol' key)
            
        Returns:
            String in the format expected by the Bybit API
        """
        # If already a string, process directly
        if isinstance(symbol, str):
            # Remove colon segment for API calls (e.g., BTCUSDT:USDT -> BTCUSDT)
            if ':' in symbol:
                # For API calls, we need BTCUSDT without the :USDT suffix
                base_symbol = symbol.split(':')[0]
                return base_symbol
            
            # Handle BTC/USDT format
            if '/' in symbol:
                parts = symbol.split('/')
                if len(parts) == 2:
                    base, quote = parts
                    # Remove any special characters
                    base = base.strip()
                    quote = quote.strip()
                    return f"{base}{quote}"
                
            # Already in correct format (e.g., BTCUSDT)
            return symbol
        
        # If dictionary with 'symbol' key, extract and process
        elif isinstance(symbol, dict) and 'symbol' in symbol:
            return self._get_symbol_string(symbol['symbol'])
        
        # Default case: return as string
        return str(symbol)

    async def fetch_ohlcv(self, symbol: Union[str, dict], timeframe: str = '1m', limit: int = 1000, since: Optional[int] = None) -> List[List[float]]:
        """
        Fetch OHLCV data for a symbol.
        
        Args:
            symbol: Symbol to fetch OHLCV data for
            timeframe: Timeframe to fetch (1m, 5m, 1h, etc.)
            limit: Maximum number of candles to fetch
            since: Timestamp in milliseconds (ignored - Bybit API uses limit rather than timestamp)
            
        Returns:
            List of OHLCV candles
        """
        try:
            # Convert the timeframe to Bybit format if needed
            tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)
            
            # Get the correct symbol format for API
            original_symbol = symbol if isinstance(symbol, str) else symbol.get('symbol', '')
            api_symbol = self._get_symbol_string(symbol)
            
            # Always use linear category for market monitor
            category = 'linear'
            
            self.logger.debug(f"Fetching OHLCV for {original_symbol} (API symbol: {api_symbol}, category: {category}, timeframe: {tf})")
            
            # Make the API request
            response = await self._make_request_with_retry(
                'GET', 
                '/v5/market/kline',
                params={
                    'category': category,
                    'symbol': api_symbol,
                    'interval': tf,
                    'limit': min(limit, 1000)  # Max 1000 per Bybit API docs
                }
            )
            
            if not response or 'result' not in response or 'list' not in response['result']:
                self.logger.error(f"Invalid response format for OHLCV data: {response}")
                return []
            
            # Parse the response
            ohlcv_data = []
            for candle in response['result']['list']:
                if len(candle) >= 7:
                    timestamp = int(candle[0])
                    open_price = float(candle[1])
                    high_price = float(candle[2])
                    low_price = float(candle[3])
                    close_price = float(candle[4])
                    volume = float(candle[5])
                    
                    # Format matches the CCXT standard: [timestamp, open, high, low, close, volume]
                    ohlcv_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
            
            # Sort by timestamp (oldest first)
            ohlcv_data.sort(key=lambda x: x[0])
            
            return ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            return []

    async def get_orderbook(self, symbol: Union[str, dict], limit: Optional[int] = None) -> Dict[str, Any]:
        """Get orderbook with symbol validation.
        
        Args:
            symbol: Symbol string or dictionary
            limit: Orderbook depth limit
            
        Returns:
            Orderbook data
        """
        symbol_str = self._get_symbol_string(symbol)
        params = {
            'category': 'linear',  # Always use linear category
            'symbol': symbol_str
        }
        if limit:
            params['limit'] = limit
        return await self._make_request('GET', '/v5/market/orderbook', params)

    async def fetch_trades(self, symbol: Union[str, dict], since: Optional[int] = None, limit: Optional[int] = None, params={}) -> List[Dict[str, Any]]:
        """Fetch recent trades with symbol validation.
        
        Args:
            symbol: Symbol string or dictionary
            since: Timestamp to fetch trades from
            limit: Number of trades to fetch (default: 1000, which is the maximum allowed by Bybit)
            params: Additional parameters
            
        Returns:
            List of trades extracted from result.list in the response
        """
        symbol_str = self._get_symbol_string(symbol)
        request_params = {
            'category': 'linear',  # Always use linear category
            'symbol': symbol_str,
            'limit': 1000  # Set default limit to maximum allowed by Bybit
        }
        
        # Override limit only if explicitly provided
        if limit is not None:
            request_params['limit'] = min(limit, 1000)  # Ensure it doesn't exceed the max
            
        if since:
            request_params['startTime'] = since
            
        request_params.update(params)
        
        try:
            response = await self._make_request_with_retry('GET', '/v5/market/recent-trade', request_params)
            
            # Verify the response has the expected structure
            if not response or 'result' not in response:
                self.logger.warning(f"Invalid response structure from Bybit trades API: {response}")
                return []
                
            # Extract trades from result.list
            result = response.get('result', {})
            trades_list = result.get('list', [])
            
            # Log the extraction results
            self.logger.debug(f"Successfully extracted {len(trades_list)} trades from Bybit API response")
            
            return trades_list
        except Exception as e:
            self.logger.error(f"Error fetching trades for {symbol_str}: {str(e)}")
            return []

    async def fetch_order_book(self, symbol: str, limit: int = 100) -> dict:
        """
        Fetch the order book for a symbol.
        
        Args:
            symbol: Symbol to fetch order book for
            limit: Number of levels to fetch
            
        Returns:
            Order book data with bids and asks
        """
        try:
            # Process the symbol to get the correct format for the API
            api_symbol = self._get_symbol_string(symbol)
            
            # Always use linear category for market monitor
            category = 'linear'
            
            self.logger.debug(f"Fetching order book for {symbol} (API symbol: {api_symbol}, category: {category})")
            
            response = await self._make_request_with_retry('GET', '/v5/market/orderbook', {
                'category': category,
                'symbol': api_symbol,
                'limit': min(limit, 200)  # Max 200 per Bybit API docs
            })
            
            # Initialize default empty orderbook
            default_orderbook = {
                'symbol': symbol,  # Use original symbol for consistency
                'bids': [],
                'asks': [],
                'timestamp': int(time.time() * 1000),
                'datetime': datetime.now().isoformat(),
                'nonce': None
            }
            
            # Check if response is valid
            if not response or 'result' not in response:
                self.logger.error(f"Invalid response format for order book: {response}")
                return default_orderbook
                
            result = response.get('result', {})
            if not result:
                self.logger.error(f"Empty result in order book response: {response}")
                return default_orderbook
                
            # Parse bids and asks
            bids = []
            asks = []
            
            for bid in result.get('b', []):
                if len(bid) >= 2:
                    price = float(bid[0])
                    amount = float(bid[1])
                    bids.append([price, amount])
                    
            for ask in result.get('a', []):
                if len(ask) >= 2:
                    price = float(ask[0])
                    amount = float(ask[1])
                    asks.append([price, amount])
            
            # Create the orderbook structure
            orderbook = {
                'symbol': symbol,  # Use original symbol for consistency
                'bids': bids,
                'asks': asks,
                'timestamp': int(result.get('ts', time.time() * 1000)),
                'datetime': datetime.fromtimestamp(int(result.get('ts', time.time() * 1000)) / 1000).isoformat(),
                'nonce': result.get('u')
            }
            
            return orderbook
            
        except Exception as e:
            self.logger.error(f"Error fetching order book: {str(e)}")
            
            # Return an empty but properly structured orderbook on error
            return {
                'symbol': symbol,
                'bids': [],
                'asks': [],
                'timestamp': int(time.time() * 1000),
                'datetime': datetime.now().isoformat(),
                'nonce': None
            }

    async def _fetch_long_short_ratio(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch long/short ratio data for a symbol.
        
        Args:
            symbol: The trading pair symbol (e.g. 'BTCUSDT')
            
        Returns:
            Dictionary containing long/short ratio data
        """
        try:
            # Ensure symbol is properly formatted for API
            symbol_str = self._get_symbol_string(symbol)
            self.logger.info(f"[LSR] Fetching long/short ratio for {symbol_str}")
            # Set up request parameters
            params = {
                'category': 'linear',  # Always use linear category
                'symbol': symbol_str,
                'period': '5min',  # Use 5min for more frequent data
                'limit': 1  # We only need the most recent data point
            }
            # Make the API request to account-ratio endpoint
            response = await self._make_request('GET', '/v5/market/account-ratio', params)
            self.logger.info(f"[LSR] Raw API response for {symbol_str}: {response}")
            if not response:
                self.logger.error(f"[LSR] Failed to fetch long/short ratio: Null response")
                # Return default structure
                default_lsr = {
                    'symbol': symbol,
                    'long': 50.0,
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                }
                self.logger.info(f"[LSR] Returning default LSR due to null response: {default_lsr}")
                return default_lsr
            if response.get('retCode') != 0:
                self.logger.error(f"[LSR] Failed to fetch long/short ratio: {response.get('retMsg', 'Unknown error')} (code: {response.get('retCode', 'unknown')})")
                # Return default structure
                default_lsr = {
                    'symbol': symbol,
                    'long': 50.0,
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                }
                self.logger.info(f"[LSR] Returning default LSR due to API error: {default_lsr}")
                return default_lsr
            # Extract data from response
            ratio_data = response.get('result', {}).get('list', [])
            if not ratio_data:
                self.logger.warning(f"[LSR] No long/short ratio data returned for {symbol}")
                # Return default structure
                default_lsr = {
                    'symbol': symbol,
                    'long': 50.0,
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                }
                self.logger.info(f"[LSR] Returning default LSR due to empty result list: {default_lsr}")
                return default_lsr
            # Parse the first entry
            latest = ratio_data[0]
            self.logger.info(f"[LSR] Raw long/short ratio data from API for {symbol}: {latest}")
            # Build result using the correct API fields (buyRatio/sellRatio)
            try:
                # Convert string values to float and multiply by 100 to get percentages
                buy_ratio = float(latest.get('buyRatio', '0.5')) * 100
                sell_ratio = float(latest.get('sellRatio', '0.5')) * 100
                timestamp = int(latest.get('timestamp', time.time() * 1000))
                # Ensure values are valid
                if buy_ratio <= 0 or sell_ratio <= 0:
                    self.logger.warning(f"[LSR] Invalid buyRatio or sellRatio values: {buy_ratio}, {sell_ratio}")
                    buy_ratio = 50.0
                    sell_ratio = 50.0
                result = {
                    'symbol': symbol,
                    'long': buy_ratio,  # Already converted to percentage (0-100)
                    'short': sell_ratio,
                    'timestamp': timestamp
                }
                self.logger.info(f"[LSR] Returning LSR data: {result}")
                return result
            except (ValueError, TypeError) as e:
                self.logger.error(f"[LSR] Error parsing long/short ratio data: {e}, raw data: {latest}")
                # Return default structure
                default_lsr = {
                    'symbol': symbol,
                    'long': 50.0,
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                }
                self.logger.info(f"[LSR] Returning default LSR due to parsing error: {default_lsr}")
                return default_lsr
        except Exception as e:
            self.logger.error(f"[LSR] Error fetching long/short ratio for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Return default structure
            default_lsr = {
                'symbol': symbol,
                'long': 50.0,
                'short': 50.0,
                'timestamp': int(time.time() * 1000)
            }
            self.logger.info(f"[LSR] Returning default LSR due to exception: {default_lsr}")
            return default_lsr
    
    async def _fetch_risk_limits(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch risk limits for a symbol.
        
        Args:
            symbol: The trading pair symbol (e.g. 'BTCUSDT')
            
        Returns:
            Dictionary containing risk limits data
        """
        try:
            self.logger.debug(f"Fetching risk limits for {symbol}")
            
            # Make the API request to risk-limit endpoint
            response = await self._make_request('GET', '/v5/market/risk-limit', {
                'category': 'linear',
                'symbol': symbol
            })
            
            if not response or response.get('retCode') != 0:
                self.logger.error(f"Failed to fetch risk limits: {response}")
                # Return default structure
                return {
                    'symbol': symbol,
                    'riskLimits': [],
                    'initialMargin': 0.01,  # 1% default initial margin
                    'maintenanceMargin': 0.005,  # 0.5% default maintenance margin
                    'currentTier': 1,
                    'maxLeverage': 100.0,
                    'timestamp': int(time.time() * 1000),
                    'levels': []
                }
            
            # Extract data from response
            risk_data = response.get('result', {}).get('list', [])
            if not risk_data:
                self.logger.warning(f"No risk limits data returned for {symbol}")
                # Return default structure
                return {
                    'symbol': symbol,
                    'riskLimits': [],
                    'initialMargin': 0.01, 
                    'maintenanceMargin': 0.005,
                    'currentTier': 1,
                    'maxLeverage': 100.0,
                    'timestamp': int(time.time() * 1000),
                    'levels': []
                }
            
            # Get the first/current tier - generally this is the lowest risk level
            current_tier = 1
            default_tier = None
            for tier in risk_data:
                if tier.get('isLowestRisk', 0) == 1:
                    default_tier = tier
                    break
            
            # If no tier marked as lowest risk, use the first one
            if default_tier is None and risk_data:
                default_tier = risk_data[0]
            
            # Extract key risk metrics from the default tier
            result = {
                'symbol': symbol,
                'riskLimits': risk_data,
                'initialMargin': float(default_tier.get('initialMargin', 0.01)) if default_tier else 0.01,
                'maintenanceMargin': float(default_tier.get('maintenanceMargin', 0.005)) if default_tier else 0.005,
                'currentTier': current_tier,
                'maxLeverage': float(default_tier.get('maxLeverage', 100.0)) if default_tier else 100.0,
                'timestamp': int(time.time() * 1000),
                'levels': risk_data  # Add full risk levels list
            }
            
            self.logger.debug(f"Risk limits extracted: initialMargin={result['initialMargin']}, "
                             f"maintenanceMargin={result['maintenanceMargin']}, "
                             f"maxLeverage={result['maxLeverage']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching risk limits for {symbol}: {str(e)}")
            # Return default structure
            return {
                'symbol': symbol,
                'riskLimits': [],
                'initialMargin': 0.01,
                'maintenanceMargin': 0.005,
                'currentTier': 1,
                'maxLeverage': 100.0,
                'timestamp': int(time.time() * 1000),
                'levels': []
            }

    async def fetch_long_short_ratio(self, symbol: str) -> Dict[str, Any]:
        """
        Public method to fetch long/short ratio for a symbol.
        
        Args:
            symbol: The trading pair symbol (e.g. 'BTCUSDT')
            
        Returns:
            Dictionary containing long/short ratio data
        """
        return await self._fetch_long_short_ratio(symbol)
    
    async def fetch_risk_limits(self, symbol: str) -> Dict[str, Any]:
        """
        Public method to fetch risk limits for a symbol.
        
        Args:
            symbol: The trading pair symbol (e.g. 'BTCUSDT')
            
        Returns:
            Dictionary containing risk limits data
        """
        return await self._fetch_risk_limits(symbol)

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data for a symbol. This is an alias for _fetch_ticker to maintain
        compatibility with other exchange implementations.
        
        Args:
            symbol: Symbol to get ticker for
            
        Returns:
            Dictionary with ticker data
        """
        return await self._fetch_ticker(symbol)

    def _convert_to_exchange_symbol(self, symbol: str) -> str:
        """Convert local symbol format to exchange symbol format
        
        Args:
            symbol: Symbol in local format (e.g., BTC/USDT, BTCUSDT:USDT)
            
        Returns:
            Symbol in exchange format (e.g., BTCUSDT)
        """
        # Handle formats like BTCUSDT:USDT (perpetual contract)
        if ':USDT' in symbol:
            return symbol.replace(':USDT', '')
            
        # Bybit expects symbols without a separator
        if '/' in symbol:
            return symbol.replace('/', '')
            
        return symbol

    async def _fetch_ticker(self, symbol: str) -> dict:
        """
        Fetch ticker data for a specific symbol.
        
        Args:
            symbol: Symbol to fetch ticker for
            
        Returns:
            Ticker data dictionary
        """
        try:
            # Process the symbol to get the correct format for the API
            api_symbol = self._get_symbol_string(symbol)
            
            # Always use linear category for market monitor
            category = 'linear'
            
            self.logger.debug(f"Fetching ticker for {symbol} (API symbol: {api_symbol}, category: {category})")
            
            # Make the API request
            response = await self._make_request('GET', '/v5/market/tickers', {
                'category': category,
                'symbol': api_symbol
            })
            
            # Check if response is valid
            if not response or 'result' not in response:
                self.logger.warning(f"No ticker data in response for {symbol}")
                return self._default_ticker_data(symbol)
                
            # Get the ticker list
            ticker_list = response.get('result', {}).get('list', [])
            
            if not ticker_list or len(ticker_list) == 0:
                self.logger.warning(f"No ticker data in response for {symbol}")
                return self._default_ticker_data(symbol)
                
            # Extract the first ticker
            ticker = ticker_list[0]
            
            # Parse funding rate and next funding time
            funding_rate = self.safe_float(ticker, 'fundingRate')
            next_funding_time = int(ticker.get('nextFundingTime', 0))
            
            # Common fields for both spot and linear
            result = {
                'symbol': symbol,  # Use original symbol for consistency
                'timestamp': int(time.time() * 1000),
                'datetime': datetime.now().isoformat(),
                'high': self.safe_float(ticker, 'highPrice24h'),
                'low': self.safe_float(ticker, 'lowPrice24h'),
                'bid': self.safe_float(ticker, 'bid1Price'),
                'bidVolume': self.safe_float(ticker, 'bid1Size'),
                'ask': self.safe_float(ticker, 'ask1Price'),
                'askVolume': self.safe_float(ticker, 'ask1Size'),
                'vwap': 0,
                'open': 0,
                'close': self.safe_float(ticker, 'lastPrice'),
                'last': self.safe_float(ticker, 'lastPrice'),
                'previousClose': 0,
                'change': 0,
                'percentage': self.safe_float(ticker, 'price24hPcnt') * 100,  # Convert to percentage
                'average': 0,
                'baseVolume': self.safe_float(ticker, 'volume24h'),
                'quoteVolume': self.safe_float(ticker, 'turnover24h'),
                'fundingRate': funding_rate,
                'nextFundingTime': next_funding_time
            }
            
            # Calculate change for consistency
            prevPrice = self.safe_float(ticker, 'prevPrice24h')
            last = self.safe_float(ticker, 'lastPrice')
            
            if prevPrice and last:
                result['open'] = prevPrice
                result['change'] = last - prevPrice
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            return self._default_ticker_data(symbol)
            
    def _default_ticker_data(self, symbol: str) -> dict:
        """
        Create default ticker data with empty values.
        
        Args:
            symbol: Symbol for the ticker
            
        Returns:
            Default ticker data structure
        """
        return {
            'symbol': symbol,  # Use the provided symbol parameter 
            'timestamp': int(time.time() * 1000),
            'datetime': datetime.now().isoformat(),
            'high': 0,
            'low': 0,
            'bid': 0,
            'bidVolume': 0,
            'ask': 0,
            'askVolume': 0,
            'vwap': 0,
            'open': 0,
            'close': 0,
            'last': 0,
            'previousClose': 0,
            'change': 0,
            'percentage': 0,
            'average': 0,
            'baseVolume': 0,
            'quoteVolume': 0
        }

    # Alias for compatibility with other exchange implementations
    async def fetch_ticker(self, symbol: str) -> dict:
        """Alias for _fetch_ticker to maintain compatibility with other exchange implementations."""
        return await self._fetch_ticker(symbol)

    async def fetch_open_interest_history(self, symbol: str, interval: str = '5min', limit: int = 200) -> Dict[str, Any]:
        """Fetch historical open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval ('5min', '15min', '30min', '1h', '4h', '1d')
            limit: Number of records to fetch (max 200)
            
        Returns:
            Dictionary containing historical open interest data
        """
        try:
            # Ensure symbol is properly formatted
            symbol_str = self._convert_to_exchange_symbol(symbol)
            
            # Check rate limit
            await self._check_rate_limit('market_data', category='linear')
            
            # Do NOT convert the interval format for open interest endpoint
            # Bybit expects the full format with time unit (e.g., '5min', not '5')
            
            # Set up request parameters
            params = {
                'category': 'linear',  # Always use linear category
                'symbol': symbol_str,
                'intervalTime': interval,  # Use the original interval format directly
                'limit': min(limit, 200)  # Bybit maximum is 200
            }
            
            self.logger.debug(f"Fetching open interest with params: {params}")
            
            # Make the request
            response = await self._make_request('GET', '/v5/market/open-interest', params=params)
            
            # Log only essential information about the response
            if response:
                self.logger.debug(f"Open interest API response: status={response.get('retCode')}, msg={response.get('retMsg')}")
                if 'result' in response and 'list' in response['result']:
                    record_count = len(response['result']['list'])
                    self.logger.debug(f"Received {record_count} open interest records for {symbol}")
            
            # Parse response
            if not response:
                self.logger.error(f"Null response from open interest API for {symbol}")
                return {'history': []}
                
            if 'retCode' in response and response['retCode'] != 0:
                self.logger.error(f"API error fetching open interest: code={response['retCode']}, msg={response.get('retMsg', 'No message')}")
                return {'history': []}
                
            if 'result' not in response:
                self.logger.error(f"Missing 'result' field in open interest response for {symbol}")
                return {'history': []}
                
            if 'list' not in response['result']:
                self.logger.error(f"Missing 'list' field in open interest result for {symbol}")
                return {'history': []}
            
            oi_list = response['result']['list']
            
            if not oi_list:
                self.logger.warning(f"Empty open interest list for {symbol}")
                return {'history': []}
            
            # Process the open interest data
            history = []
            processed_count = 0
            error_count = 0
            
            for item in oi_list:
                try:
                    # Process without logging each item
                    timestamp = int(item.get('timestamp', 0))
                    openInterest = item.get('openInterest', 0)
                    
                    if not timestamp or not openInterest:
                        self.logger.warning(f"Incomplete OI data item: {item}")
                        error_count += 1
                        continue
                        
                    history.append({
                        'timestamp': timestamp,
                        'value': float(openInterest),
                        'symbol': symbol_str
                    })
                    processed_count += 1
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error processing open interest item: {e}")
                    error_count += 1
                    continue
            
            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x['timestamp'], reverse=True)
            
            self.logger.debug(f"Successfully processed {processed_count} of {len(oi_list)} open interest records. Errors: {error_count}")
            
            result = {
                'history': history,
                'symbol': symbol,
                'interval': interval,
                'timestamp': int(time.time() * 1000)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching open interest history: {e}")
            self.logger.error(traceback.format_exc())
            return {'history': []}

    async def _calculate_historical_volatility(self, symbol: str, timeframe: str = '5min', window: int = 24) -> Dict[str, Any]:
        """
        Calculate historical volatility from OHLCV data.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Time interval for calculations
            window: Number of periods to calculate volatility over
            
        Returns:
            Dictionary containing volatility data
        """
        try:
            self.logger.debug(f"Calculating historical volatility for {symbol}")
            
            # Convert timeframe to minutes
            period_minutes = self._timeframe_to_minutes(timeframe)
            if period_minutes == 0:
                self.logger.error(f"Invalid timeframe format: {timeframe}")
                return self._default_volatility_data(timeframe, window)
            
            # Fetch OHLCV data with extra candles for trend calculation
            candles = await self._fetch_ohlcv(symbol, timeframe, limit=window + 5)
            
            if not candles or len(candles) < window:
                self.logger.warning(f"Insufficient OHLCV data for volatility calculation: {len(candles) if candles else 0} candles")
                return self._default_volatility_data(timeframe, window)
            
            # Convert to DataFrame with correct columns
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            
            # Drop rows with NaN values
            df = df.dropna(subset=['close'])
            if len(df) < window:
                self.logger.warning(f"Insufficient valid data points after cleaning: {len(df)}")
                return self._default_volatility_data(timeframe, window)
            
            # Calculate log returns
            df['returns'] = np.log(df['close'] / df['close'].shift(1))
            
            # Calculate annualized volatility
            minutes_per_year = 365 * 24 * 60
            periods_per_year = minutes_per_year / period_minutes
            volatility = df['returns'].rolling(window=window).std() * np.sqrt(periods_per_year)
            
            # Get the most recent volatility value
            current_vol = float(volatility.iloc[-1]) if not volatility.empty else 0.0
            
            # Calculate volatility trend using exponential moving average
            vol_ema = volatility.ewm(span=5).mean()
            if len(vol_ema) >= 2:
                if vol_ema.iloc[-1] > vol_ema.iloc[-2] * 1.05:
                    trend = 'increasing'
                elif vol_ema.iloc[-1] < vol_ema.iloc[-2] * 0.95:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'unknown'
            
            return {
                'value': current_vol,
                'window': window,
                'timeframe': timeframe,
                'timestamp': int(time.time() * 1000),
                'trend': trend,
                'period_minutes': period_minutes
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating historical volatility: {str(e)}", exc_info=True)
            return self._default_volatility_data(timeframe, window)
    
    def _default_volatility_data(self, timeframe: str, window: int) -> Dict[str, Any]:
        """Return default volatility data structure when calculation fails."""
        period_minutes = self._timeframe_to_minutes(timeframe)
        return {
            'value': 0.0,
            'window': window,
            'timeframe': timeframe,
            'timestamp': int(time.time() * 1000),
            'trend': 'unknown',
            'period_minutes': period_minutes
        }
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes.
        
        Args:
            timeframe (str): Timeframe string (e.g., '1m', '5m', '1h', '1d')
            
        Returns:
            int: Number of minutes in the timeframe
        """
        try:
            if 'min' in timeframe:
                return int(timeframe.replace('min', ''))
            elif 'm' in timeframe:
                return int(timeframe.replace('m', ''))
            elif 'h' in timeframe:
                return int(timeframe.replace('h', '')) * 60
            elif 'd' in timeframe:
                return int(timeframe.replace('d', '')) * 24 * 60
            else:
                self.logger.error(f"Unsupported timeframe format: {timeframe}")
                return 5  # Default to 5 minutes
        
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error parsing timeframe: {str(e)}")
            return 5  # Default to 5 minutes

    async def _fetch_klines(self, symbol: str, interval: str) -> List[List[Any]]:
        """Alias for _fetch_ohlcv to maintain compatibility."""
        return await self._fetch_ohlcv(symbol, interval)

    # Helper utility functions
    def safe_float(self, data, key, default=0.0):
        """
        Safely convert a value to float with fallback to default.
        
        Args:
            data: Dictionary containing the key
            key: Key to extract from dictionary
            default: Default value if conversion fails
            
        Returns:
            Converted float value or default
        """
        value = data.get(key)
        if value is None or value == '':
            return default
        try:
            # Remove any commas and convert to float
            cleaned = str(value).replace(',', '')
            return float(cleaned)
        except (ValueError, TypeError):
            self.logger.warning(f"Could not convert {value} to float, using default {default}")
            return default

    def _debug_function_call(self, func_name: str, *args, **kwargs):
        """Debug wrapper to trace function calls and potential KeyErrors."""
        try:
            self.logger.debug(f"🔧 TRACE: Entering {func_name}")
            self.logger.debug(f"🔧 TRACE: Args: {args}")
            self.logger.debug(f"🔧 TRACE: Kwargs: {kwargs}")
            return True
        except Exception as e:
            self.logger.error(f"🚨 TRACE ERROR: Error in debug wrapper for {func_name}: {e}")
            return False

    def _debug_dict_access(self, data: Any, key: str, context: str = "unknown") -> Any:
        """Debug wrapper for dictionary access to catch KeyErrors."""
        try:
            if not isinstance(data, dict):
                self.logger.error(f"🚨 DICT ACCESS: Attempting to access key '{key}' on non-dict type {type(data)} in context: {context}")
                raise KeyError(f"Cannot access key '{key}' on {type(data)}")
            
            if key not in data:
                self.logger.error(f"🚨 DICT ACCESS: Key '{key}' not found in dict with keys {list(data.keys())} in context: {context}")
                raise KeyError(f"Key '{key}' not found in context: {context}")
            
            self.logger.debug(f"✅ DICT ACCESS: Successfully accessed key '{key}' in context: {context}")
            return data[key]
            
        except Exception as e:
            self.logger.error(f"🚨 DICT ACCESS ERROR: {str(e)} in context: {context}")
            raise

class BybitWebSocket:
    """WebSocket client for Bybit exchange."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.ws = None
        self.session = None
        self.connected = False
        self._message_handlers = {}
        
    async def connect(self) -> bool:
        """Connect to WebSocket."""
        try:
            if self.connected:
                return True
                
            # Get WebSocket URL from config
            ws_config = self.config.get('websocket', {})
            if self.config.get('testnet', False):
                ws_url = ws_config.get('testnet_endpoint', 'wss://stream-testnet.bybit.com/v5/public/linear')
            else:
                ws_url = ws_config.get('mainnet_endpoint', 'wss://stream.bybit.com/v5/public/linear')
                
            # Ensure protocol prefix
            if not ws_url.startswith('wss://'):
                ws_url = f"wss://{ws_url.lstrip('/')}"
                
            self.logger.debug(f"Connecting to WebSocket URL: {ws_url}")
            
            # Create session and connect
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.ws = await self.session.ws_connect(
                ws_url,
                autoclose=False,
                heartbeat=30
            )
            
            self.connected = True
            self.logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {str(e)}")
            if self.session:
                await self.session.close()
            self.session = None
            self.ws = None
            self.connected = False
            return False
            
    async def subscribe(self, channels: List[str]) -> bool:
        """Subscribe to channels."""
        try:
            if not self.connected:
                if not await self.connect():
                    return False
                    
            msg = {
                "op": "subscribe",
                "args": channels
            }
            await self.ws.send_json(msg)
            return True
            
        except Exception as e:
            self.logger.error(f"Subscription failed: {str(e)}")
            return False
            
    def on_message(self, channel: str, callback: Callable) -> None:
        """Register message handler for channel."""
        self._message_handlers[channel] = callback

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        self.connected = False
        self.ws = None
        self.session = None
    
if __name__ == "__main__":
    raise RuntimeError("This module should not be executed directly")
    
def init():
    # Initialization logic here
    pass
    