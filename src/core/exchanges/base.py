"""Base exchange class with CCXT standardization."""

import asyncio
import logging
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
from datetime import datetime
import aiohttp
from aiohttp import ClientTimeout
from ...models.market_data import (
    Trade, OrderBook, Ticker, OHLCV, Balance, Position, Order,
    from_exchange_data
)
import pandas as pd

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ExchangeError(Exception):
    """Base class for exchange errors"""
    pass

class NetworkError(ExchangeError):
    """Network related errors"""
    pass

class TimeoutError(NetworkError):
    """Request timeout errors"""
    pass

class AuthenticationError(ExchangeError):
    """Authentication related errors"""
    pass

class RateLimitError(ExchangeError):
    """Rate limiting related errors"""
    pass

def retry_on_error(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (NetworkError, TimeoutError)
) -> Callable:
    """Retry decorator for API requests"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            last_error = None
            delay = initial_delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    continue
                    
            raise last_error
            
        return wrapper
    return decorator

def handle_timeout(timeout: float = 30.0) -> Callable:
    """Timeout decorator for API requests"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Request timed out after {timeout} seconds")
                
        return wrapper
    return decorator

class BaseExchange(ABC):
    """Base exchange class with CCXT standardization"""
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """Initialize base exchange.
        
        Args:
            config: Exchange configuration
            error_handler: Optional error handler
        """
        self.config = config
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        # Get market data config
        market_config = config.get('market_data', {})
        self.update_interval = market_config.get('update_interval', 1.0)
        self.batch_size = market_config.get('batch_size', 100)
        
        # Get validation config
        self.validation_config = config.get('validation', {})
        
        # Get monitoring config
        self.monitoring_config = config.get('monitoring', {})
        
        # Initialize state
        self.initialized = False
        self.session = None
        self.ws = None
        self.exchange_id = None
        self.credentials = {}
        self.options = {
            'timeout': 30000,
            'enableRateLimit': True,
            'rateLimit': 100,
            'verbose': False
        }
        self.markets = {}
        self.symbols = set()
        self.timeframes = {}
        self.fees = {}
        self.precisions = {}
        self.limits = {}
        self.api_urls = {}
        self.ws_endpoints = {}
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time = 0
        self._request_interval = 0.1  # Default 100ms between requests
        self.pagination_limits = {
            'trades': 1000,
            'orders': 500,
            'positions': 200,
            'ohlcv': 1000,
        }
        self._last_health_check = 0
        self._health_check_interval = 60  # Check health every 60 seconds
        self._is_healthy = False
        self.min_required_candles = {
            '1': 1000,   # More data for base timeframe
            '5': 200,
            '30': 200,
            '240': 200
        }
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize exchange connection."""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """Check exchange connection health."""
        pass
        
    async def init(self) -> None:
        """Initialize exchange connection"""
        if not self.session:
            timeout = ClientTimeout(total=self.options['timeout'] / 1000)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
    async def close(self) -> None:
        """Close exchange connection"""
        try:
            # Close HTTP session
            if self.session:
                await self.session.close()
                self.session = None
                
            # Close WebSocket connection
            if self.ws:
                await self.ws.close()
                self.ws = None
                
            # Clear subscriptions and callbacks
            self._ws_subscriptions = {}
            self._ws_callbacks = {}
            
            # Clear market data
            self.markets = {}
            self.symbols = set()
            self.timeframes = {}
            
            # Reset rate limiting
            self._last_request_time = 0
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise
            
    def set_credentials(self, api_key: str, secret: str) -> None:
        """Set API credentials"""
        self.credentials = {
            'apiKey': api_key,
            'secret': secret
        }
        
    @abstractmethod
    def sign(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Tuple[str, Dict, Dict, Dict]:
        """Sign request for private endpoints"""
        pass
        
    @retry_on_error()
    @handle_timeout()
    async def public_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make public API request"""
        if not self.session:
            await self.init()
            
        url = f"{self.api_urls['public']}{path}"
        headers = headers or {}
        params = params or {}
        
        try:
            async with self.session.request(
                method,
                url,
                params=params,
                headers=headers,
                json=body if body else None
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    self.logger.error(f"HTTP {response.status} error: {text} for URL: {url}")
                    raise NetworkError(f"HTTP {response.status}: {text}")
                    
                return await response.json()
                
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during public request to {url}: {str(e)}")
            raise NetworkError(f"Network error: {str(e)}")
            
    @retry_on_error()
    @handle_timeout()
    async def private_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make private API request"""
        if not self.session:
            await self.init()
            
        url, params, headers, body = self.sign(method, path, params, headers, body)
        
        try:
            async with self.session.request(
                method,
                url,
                params=params,
                headers=headers,
                json=body if body else None
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise NetworkError(f"HTTP {response.status}: {text}")
                    
                return await response.json()
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error: {str(e)}")
            
    def validate_symbol(self, symbol: str) -> None:
        """Validate trading symbol"""
        if not symbol:
            raise ValueError("Symbol is required")
            
        if symbol not in self.symbols:
            raise ValueError(f"Symbol {symbol} is not supported")
            
    def validate_timeframe(self, timeframe: str) -> None:
        """Validate timeframe"""
        if not timeframe:
            raise ValueError("Timeframe is required")
            
        if timeframe not in self.timeframes:
            raise ValueError(f"Timeframe {timeframe} is not supported")
            
    def validate_limit(self, limit: Optional[int], max_limit: int = 1000) -> None:
        """Validate pagination limit"""
        if limit is None:
            return
            
        if not isinstance(limit, int):
            raise ValueError("Limit must be an integer")
            
        if limit <= 0:
            raise ValueError("Limit must be positive")
            
        if limit > max_limit:
            raise ValueError(f"Limit cannot exceed {max_limit}")

    def standardize_response(
        self,
        response: Dict[str, Any],
        data_type: str
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Standardize API response to CCXT format"""
        try:
            # First standardize to CCXT format
            if data_type == 'trades':
                standardized = self.parse_trades(response)
            elif data_type == 'orderbook':
                standardized = self.parse_orderbook(response)
            elif data_type == 'ticker':
                standardized = self.parse_ticker(response)
            elif data_type == 'ohlcv':
                standardized = self.parse_ohlcv(response)
            elif data_type == 'balance':
                standardized = self.parse_balance(response)
            elif data_type == 'order':
                standardized = self.parse_order(response)
            else:
                raise ValueError(f"Unknown data type: {data_type}")
                
            # Then convert to model instance
            return from_exchange_data(standardized, data_type)
            
        except Exception as e:
            self.logger.error(f"Error standardizing {data_type} data: {str(e)}")
            raise
            
    @abstractmethod
    def parse_trades(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse trades response to CCXT format"""
        pass
        
    @abstractmethod
    def parse_orderbook(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse orderbook response to CCXT format"""
        pass
        
    @abstractmethod
    def parse_ticker(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ticker response to CCXT format"""
        pass
        
    @abstractmethod
    def parse_ohlcv(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OHLCV response to CCXT format"""
        pass
        
    @abstractmethod
    def parse_balance(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance response to CCXT format"""
        pass
        
    @abstractmethod
    def parse_order(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse order response to CCXT format"""
        pass 
        
    async def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests"""
        async with self._rate_limit_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._request_interval:
                await asyncio.sleep(self._request_interval - elapsed)
            self._last_request_time = time.time()
            
    async def paginate_request(
        self,
        func: Callable,
        limit: int,
        data_key: str,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Handle pagination for large datasets"""
        results = []
        page = 1
        page_size = min(limit, self.pagination_limits.get(data_key, 100))
        
        while len(results) < limit:
            try:
                await self._wait_for_rate_limit()
                
                response = await func(
                    *args,
                    limit=page_size,
                    page=page,
                    **kwargs
                )
                
                items = response.get('result', {}).get(data_key, [])
                if not items:
                    break
                    
                results.extend(items)
                if len(items) < page_size:
                    break
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error in pagination: {str(e)}")
                break
                
        return results[:limit]
        
    @abstractmethod
    async def connect_ws(self) -> bool:
        """Connect to websocket API"""
        pass
        
    @abstractmethod
    async def subscribe_ws(
        self,
        channels: List[str],
        symbols: List[str],
        callback: Callable
    ) -> bool:
        """Subscribe to websocket channels"""
        pass
        
    async def _ws_heartbeat(self):
        """Maintain websocket connection with heartbeat"""
        while True:
            try:
                if self.ws and not self.ws.closed:
                    try:
                        await self.ws.ping()
                        await asyncio.sleep(self.options['ws']['ping_interval'])
                    except Exception as e:
                        self.logger.warning(f"Heartbeat failed: {str(e)}")
                        await self._ws_reconnect()
                else:
                    await self._ws_reconnect()
                    await asyncio.sleep(self.options['ws']['reconnect_delay'])
            except Exception as e:
                self.logger.error(f"Heartbeat error: {str(e)}")
                await asyncio.sleep(self.options['ws']['reconnect_delay'])
                
    async def _ws_reconnect(self):
        """Handle websocket reconnection"""
        if not hasattr(self, '_ws_reconnecting') or not self._ws_reconnecting:
            self._ws_reconnecting = True
            try:
                for attempt in range(self.options['ws']['reconnect_attempts']):
                    try:
                        if self.ws:
                            await self.ws.close()
                        self.ws = None
                        
                        if await self.connect_ws():
                            # Resubscribe to all channels
                            for channel, symbols in getattr(self, '_ws_subscriptions', {}).items():
                                await self.subscribe_ws(
                                    [channel],
                                    symbols,
                                    self._ws_callbacks.get(channel)
                                )
                            self.logger.info("WebSocket reconnection successful")
                            break
                    except Exception as e:
                        self.logger.error(f"Reconnection attempt {attempt + 1} failed: {str(e)}")
                        await asyncio.sleep(self.options['ws']['reconnect_delay'])
            finally:
                self._ws_reconnecting = False
                
    async def _handle_ws_messages(self):
        """Handle incoming websocket messages"""
        while True:
            try:
                if not self.ws or self.ws.closed:
                    break
                    
                msg = await self.ws.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._process_ws_message(data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error handling websocket message: {str(e)}")
                await self._ws_reconnect()
                
    async def _process_ws_message(self, message: Dict[str, Any]):
        """Process websocket message"""
        try:
            # Extract message type and data
            msg_type = message.get('type')
            if not msg_type:
                return
                
            # Standardize data based on type
            if msg_type == 'trade':
                data = self.standardize_response(message['data'], 'trade')
            elif msg_type == 'orderbook':
                data = self.standardize_response(message['data'], 'orderbook')
            elif msg_type == 'ticker':
                data = self.standardize_response(message['data'], 'ticker')
            elif msg_type == 'ohlcv':
                data = self.standardize_response(message['data'], 'ohlcv')
            else:
                return
                
            # Call registered callback
            if msg_type in self._ws_callbacks:
                await self._ws_callbacks[msg_type](data)
                
        except Exception as e:
            self.logger.error(f"Error processing websocket message: {str(e)}")
            
    def validate_market_data(self, market_data: Dict[str, Any]) -> None:
        """Validate market data structure with flexible field detection"""
        # Define core fields vs optional fields
        core_fields = {
            'trades': [],  # No core fields required for trades list
            'orderbook': [],  # No core fields required for orderbook dict
            'ticker': [],  # No core fields required for ticker dict
            'ohlcv': []  # No core fields required for OHLCV
        }
        
        # Define recommended fields (warn if missing but don't fail)
        recommended_fields = {
            'trades': ['timestamp', 'side', 'price', 'amount'],
            'orderbook': ['timestamp', 'bids', 'asks'],
            'ticker': ['timestamp', 'high', 'low'],
            'ohlcv': ['open', 'high', 'low', 'close', 'volume']
        }
        
        for data_type, fields in core_fields.items():
            if data_type in market_data:
                data = market_data[data_type]
                
                # Handle empty data gracefully
                if not data:
                    self.logger.warning(f"Empty {data_type} data - likely due to API fetch failure")
                    continue
                
                if isinstance(data, (list, tuple)):
                    for item in data:
                        # Check core fields only
                        missing_core = [f for f in fields if f not in item]
                        if missing_core:
                            raise ValueError(
                                f"Missing core fields for {data_type}: {missing_core}"
                            )
                        
                        # Check recommended fields (warn only)
                        if data_type in recommended_fields:
                            missing_recommended = [f for f in recommended_fields[data_type] if f not in item]
                            if missing_recommended:
                                self.logger.warning(f"Missing recommended fields for {data_type}: {missing_recommended}")
                else:
                    # Check core fields only
                    missing_core = [f for f in fields if f not in data]
                    if missing_core:
                        raise ValueError(
                            f"Missing core fields for {data_type}: {missing_core}"
                        )
                    
                    # Check recommended fields (warn only)
                    if data_type in recommended_fields:
                        missing_recommended = [f for f in recommended_fields[data_type] if f not in data]
                        if missing_recommended:
                            self.logger.warning(f"Missing recommended fields for {data_type}: {missing_recommended}")
                        
    async def _maintain_ws_connection(self):
        """Maintain websocket connection"""
        while True:
            try:
                if not self.ws or self.ws.closed:
                    await self._ws_reconnect()
                else:
                    try:
                        # Check connection with a ping
                        pong = await self.ws.ping()
                        if not pong:
                            await self._ws_reconnect()
                    except Exception:
                        await self._ws_reconnect()
                await asyncio.sleep(self.options['ws']['ping_interval'])
            except Exception as e:
                self.logger.error(f"Error maintaining websocket connection: {str(e)}")
                await asyncio.sleep(self.options['ws']['reconnect_delay'])
                
    def _init_ws_state(self):
        """Initialize websocket state"""
        self._ws_subscriptions = {}
        self._ws_callbacks = {}
        self._ws_reconnecting = False
        self._ws_connected = asyncio.Event()
        self._ws_tasks = set()
        
    def _cleanup_ws_state(self):
        """Cleanup websocket state"""
        self._ws_subscriptions.clear()
        self._ws_callbacks.clear()
        self._ws_reconnecting = False
        self._ws_connected.clear()
        for task in self._ws_tasks:
            task.cancel()
        self._ws_tasks.clear()
        
    async def _start_ws_tasks(self):
        """Start websocket maintenance tasks"""
        self._ws_tasks.add(
            asyncio.create_task(self._maintain_ws_connection())
        )
        self._ws_tasks.add(
            asyncio.create_task(self._handle_ws_messages())
        )
        
    async def is_healthy(self) -> bool:
        """Check if the exchange connection is healthy
        
        Returns:
            bool: True if the exchange is healthy, False otherwise
        """
        current_time = time.time()
        
        # Only check health status every _health_check_interval seconds
        if current_time - self._last_health_check < self._health_check_interval:
            return self._is_healthy
            
        try:
            # Try to fetch a simple public endpoint
            await self.public_request('GET', '/time')
            
            # Check WebSocket connection if enabled
            if self.ws and not self.ws.closed:
                self._is_healthy = True
            else:
                # If WebSocket is enabled but not connected, try to reconnect
                if self.ws_endpoints:
                    await self._ws_reconnect()
                self._is_healthy = True
                
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            self._is_healthy = False
            
        self._last_health_check = current_time
        return self._is_healthy
        
    @retry_on_error()
    @handle_timeout()
    async def check_health(self) -> bool:
        """Check exchange health by fetching server time"""
        try:
            # Only check health if enough time has passed since last check
            current_time = time.time()
            if current_time - self._last_health_check < self._health_check_interval:
                return self._is_healthy

            # Make request to server time endpoint
            response = await self.public_request('GET', '/v5/market/time')
            
            if not response or 'result' not in response:
                self._is_healthy = False
                self.logger.error("Health check failed: Invalid response format")
                return False

            # Get server timestamp in milliseconds
            server_time = int(response['result']['timeSecond']) * 1000
            local_time = int(time.time() * 1000)
            
            # Allow up to 30 seconds time difference
            time_diff = abs(server_time - local_time)
            self._is_healthy = time_diff <= 30000
            
            if not self._is_healthy:
                self.logger.error(f"Health check failed: Time difference too large ({time_diff}ms)")
            
            self._last_health_check = current_time
            return self._is_healthy

        except Exception as e:
            self._is_healthy = False
            self.logger.error(f"Health check failed: {str(e)}")
            return False
        
    async def fetch_timeframe_data(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for specific timeframe interval"""
        try:
            required_candles = self.min_required_candles.get(interval, 200)
            
            klines = await self.fetch_ohlcv(
                symbol=symbol,
                timeframe=interval,
                limit=required_candles
            )
            
            if not klines or len(klines) < required_candles:
                logger.error(f"Insufficient {interval} data for {symbol}")
                return None
                
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {interval} data: {str(e)}")
            return None
        
    @abstractmethod
    async def get_markets(self) -> List[Dict[str, Any]]:
        """Get all available markets.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        pass
        
    @abstractmethod
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Exchange-specific implementation (adapter pattern)"""
        pass 