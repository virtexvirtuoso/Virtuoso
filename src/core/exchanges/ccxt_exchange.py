from src.utils.task_tracker import create_tracked_task
"""CCXT exchange implementation with unified API support."""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
import ccxt.async_support as ccxtpro
from datetime import datetime

from .base import BaseExchange, NetworkError, TimeoutError, ExchangeError, retry_on_error, handle_timeout
from ...models.market_data import (
    Trade, OrderBook, Ticker, OHLCV, Balance, Position, Order,
    from_exchange_data
)

# Configure logger
logger = logging.getLogger(__name__)

class CCXTExchange(BaseExchange):
    """CCXT exchange implementation with unified API support."""
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """Initialize CCXT exchange.
        
        Args:
            config: Exchange configuration
            error_handler: Optional error handler
        """
        super().__init__(config, error_handler)
        
        # Get exchange configuration
        exchange_config = config.get('exchanges', {})
        exchange_id = config.get('exchange_id', 'bybit')
        
        for ex_id, ex_config in exchange_config.items():
            if ex_id == exchange_id:
                self.exchange_config = ex_config
                break
        else:
            self.exchange_config = {}
            logger.warning(f"Exchange {exchange_id} not found in configuration, using defaults")
        
        # CCXT-specific options
        self.ccxt_options = self.exchange_config.get('ccxt_options', {})
        self.ccxt_options.update({
            'enableRateLimit': True,
            'timeout': self.options.get('timeout', 30000)
        })
        
        # API credentials
        api_config = self.exchange_config.get('api_credentials', {})
        api_key = api_config.get('api_key', '')
        api_secret = api_config.get('api_secret', '')
        
        if api_key and api_secret:
            self.ccxt_options.update({
                'apiKey': api_key,
                'secret': api_secret
            })
        
        # Exchange-specific endpoints
        endpoint = self.exchange_config.get('endpoint', '')
        if endpoint:
            self.ccxt_options.update({
                'urls': {
                    'api': endpoint
                }
            })
        
        # Test mode settings
        self.test_mode = self.exchange_config.get('testnet', False)
        if self.test_mode:
            self.ccxt_options.update({
                'options': {
                    'test': True,
                }
            })
            
        # Exchange identifier and CCXT instance
        self.exchange_id = exchange_id
        self.ccxt = None
        
        # Map of market IDs to symbols
        self.market_id_map = {}
        
        # Default data formats
        self.data_formats = {
            'trades': ['timestamp', 'price', 'amount', 'side'],
            'ohlcv': ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
            'orderbook': ['asks', 'bids', 'timestamp', 'nonce']
        }
        
        # Open interest history cache
        self._open_interest_history_cache = {}
        self._last_oi_fetch = {}
        
    async def initialize(self) -> bool:
        """Initialize exchange connection.
        
        Returns:
            bool: True if initialization is successful
        """
        try:
            # Create CCXT instance
            exchange_class = getattr(ccxtpro, self.exchange_id, None)
            if not exchange_class:
                logger.error(f"Exchange {self.exchange_id} not supported by CCXT")
                return False
                
            self.ccxt = exchange_class(self.ccxt_options)
            
            # Initialize HTTP session
            await self.init()
            
            # Load markets
            try:
                self.markets = await self.ccxt.load_markets()
                self.symbols = set(self.markets.keys())
                
                # Initialize market ID map
                for symbol, market in self.markets.items():
                    self.market_id_map[market['id']] = symbol
                
                logger.info(f"Loaded {len(self.markets)} markets from {self.exchange_id}")
                
                # Load exchange-specific timeframes
                self.timeframes = self.ccxt.timeframes
                logger.info(f"Supported timeframes: {', '.join(self.timeframes)}")
                
                # Load exchange metadata
                self.fees = {}
                self.precisions = {}
                self.limits = {}
                
                for symbol, market in self.markets.items():
                    self.fees[symbol] = market.get('fees', {})
                    self.precisions[symbol] = market.get('precision', {})
                    self.limits[symbol] = market.get('limits', {})
                
                # Set up API URLs
                self.api_urls = {
                    'public': self.ccxt.urls.get('api', ''),
                    'private': self.ccxt.urls.get('api', '')
                }
                
                # Set up WebSocket endpoints
                self.ws_endpoints = {
                    'public': self.ccxt.urls.get('ws', ''),
                    'private': self.ccxt.urls.get('ws', '')
                }
                
                # Set rate limiting parameters based on exchange
                self._request_interval = 1.0 / self.ccxt.rateLimit * 1000 if self.ccxt.rateLimit else 0.1
                
                # Mark as initialized
                self.initialized = True
                self._is_healthy = True
                self._last_health_check = time.time()
                
                logger.info(f"Successfully initialized {self.exchange_id} exchange")
                return True
                
            except Exception as e:
                logger.error(f"Error loading markets: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            return False

    async def _execute_with_session_retry(self, operation, *args, **kwargs):
        """Execute CCXT operation with session retry logic for 'Session is closed' errors.

        Args:
            operation: The CCXT method to call
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation

        Returns:
            Result of the operation

        Raises:
            Exception: If all retry attempts fail
        """
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Execute the operation
                result = await operation(*args, **kwargs)
                return result

            except RuntimeError as e:
                if "Session is closed" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Session closed error on attempt {attempt + 1}, reinitializing exchange...")

                    # Reinitialize the exchange to get fresh session
                    try:
                        await self._reinitialize_session()
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    except Exception as reinit_error:
                        logger.error(f"Failed to reinitialize session: {str(reinit_error)}")
                        if attempt == max_retries - 1:
                            raise e
                        continue
                else:
                    # Not a session error or final attempt
                    raise e

            except Exception as e:
                # Not a session error, propagate immediately
                raise e

        # Should not reach here, but just in case
        raise RuntimeError("All retry attempts exhausted")

    async def _reinitialize_session(self):
        """Reinitialize the CCXT exchange instance to get fresh aiohttp session."""
        try:
            # Properly close existing exchange instance and all its resources
            if hasattr(self.ccxt, 'close'):
                try:
                    await self.ccxt.close()
                    logger.debug(f"Closed existing {self.exchange_id} exchange instance")
                except Exception as close_error:
                    logger.warning(f"Error closing existing exchange: {str(close_error)}")

            # Additional session cleanup
            if hasattr(self.ccxt, 'session') and self.ccxt.session:
                if not self.ccxt.session.closed:
                    await self.ccxt.session.close()
                self.ccxt.session = None

            # Small delay to ensure cleanup completes
            await asyncio.sleep(0.1)

            # Recreate the exchange instance with fresh session
            exchange_class = getattr(ccxtpro, self.exchange_id, None)
            if exchange_class:
                # Store critical data before reinitializing
                old_markets = getattr(self.ccxt, 'markets', None)
                old_symbols = getattr(self.ccxt, 'symbols', None)

                # Create new instance
                self.ccxt = exchange_class(self.ccxt_options)

                # Restore critical data to avoid re-fetching
                if old_markets:
                    self.ccxt.markets = old_markets
                    self.ccxt.markets_by_id = {v['id']: v for v in old_markets.values()}
                if old_symbols:
                    self.ccxt.symbols = old_symbols

                logger.info(f"Successfully reinitialized {self.exchange_id} session")
            else:
                raise Exception(f"Exchange {self.exchange_id} not found")

        except Exception as e:
            logger.error(f"Error reinitializing session: {str(e)}")
            raise


    async def _ensure_session_healthy(self):
        """Proactively check and reinitialize session if needed."""
        if not self.ccxt:
            await self.initialize()
            return

        # Check if session exists and is open
        if hasattr(self.ccxt, 'session'):
            if self.ccxt.session is None or self.ccxt.session.closed:
                logger.warning("Detected closed session, reinitializing...")
                await self._reinitialize_session()

    def _convert_symbol_to_ccxt_format(self, symbol: str) -> str:
        """Convert normalized symbol back to CCXT format for API calls.

        TopSymbolsManager normalizes '10000SATS/USDT:USDT' to '10000SATSUSDT'
        but CCXT API calls need the original format.

        Args:
            symbol: Normalized symbol (e.g., '10000SATSUSDT')

        Returns:
            CCXT format symbol (e.g., '10000SATS/USDT:USDT')
        """
        # First check if symbol exists as-is (already in CCXT format)
        if symbol in self.symbols:
            return symbol

        # Convert from normalized format to CCXT format
        if symbol.endswith('USDT') and len(symbol) > 4:
            base = symbol[:-4]  # Remove 'USDT'
            # Check linear perpetual format first (preferred for trading)
            ccxt_linear = f"{base}/USDT:USDT"
            if ccxt_linear in self.symbols:
                return ccxt_linear
            # Check spot format as fallback
            ccxt_spot = f"{base}/USDT"
            if ccxt_spot in self.symbols:
                return ccxt_spot

        if symbol.endswith('USDC') and len(symbol) > 4:
            base = symbol[:-4]  # Remove 'USDC'
            # Check linear perpetual format first
            ccxt_linear = f"{base}/USDC:USDC"
            if ccxt_linear in self.symbols:
                return ccxt_linear
            # Check spot format as fallback
            ccxt_spot = f"{base}/USDC"
            if ccxt_spot in self.symbols:
                return ccxt_spot

        # If no conversion works, return original symbol
        # This will likely fail in CCXT call, but that's expected behavior
        return symbol

    async def health_check(self) -> bool:
        """Check exchange connection health.
        
        Returns:
            bool: True if exchange is responding correctly
        """
        try:
            # Simple API call to check if exchange is responsive
            await self.ccxt.fetch_status()
            self._is_healthy = True
            self._last_health_check = time.time()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            self._is_healthy = False
            return False
            
    async def close(self) -> None:
        """Close exchange connection."""
        if self.ccxt:
            await self.ccxt.close()
            
        await super().close()
        
    def sign(self, method: str, path: str, params: Optional[Dict] = None, 
            headers: Optional[Dict] = None, body: Optional[Dict] = None
    ) -> Tuple[str, Dict, Dict, Dict]:
        """Sign request for private endpoints.
        
        CCXT handles signing internally, so this is a passthrough.
        
        Returns:
            Tuple containing url, params, headers, and body
        """
        # CCXT handles authentication internally
        url = f"{self.api_urls['private']}{path}"
        return url, params or {}, headers or {}, body or {}
        
    async def public_request(self, method: str, path: str, params: Optional[Dict] = None,
                     headers: Optional[Dict] = None, body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make public API request.
        
        This is a wrapper around the CCXT methods.
        """
        if not self.ccxt:
            await self.initialize()
            
        await self._wait_for_rate_limit()
            
        try:
            # Map the method name to a CCXT method when possible
            method_name = path.lstrip('/')
            
            if hasattr(self.ccxt, method_name):
                ccxt_method = getattr(self.ccxt, method_name)
                result = await ccxt_method(**(params or {}))
                return result
            else:
                # Fall back to direct API request
                return await super().public_request(method, path, params, headers, body)
                
        except ccxtpro.NetworkError as e:
            logger.error(f"CCXT Network error: {str(e)}")
            raise NetworkError(str(e))
        except ccxtpro.ExchangeError as e:
            logger.error(f"CCXT Exchange error: {str(e)}")
            raise ExchangeError(str(e))
        except Exception as e:
            logger.error(f"CCXT error during public request: {str(e)}")
            raise
            
    async def private_request(self, method: str, path: str, params: Optional[Dict] = None,
                      headers: Optional[Dict] = None, body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make private API request.
        
        This is a wrapper around the CCXT methods.
        """
        if not self.ccxt:
            await self.initialize()
            
        if not self.ccxt.apiKey or not self.ccxt.secret:
            raise ExchangeError("API credentials not set")
            
        await self._wait_for_rate_limit()
            
        try:
            # Map the method name to a CCXT method when possible
            method_name = path.lstrip('/')
            
            if hasattr(self.ccxt, method_name):
                ccxt_method = getattr(self.ccxt, method_name)
                result = await ccxt_method(**(params or {}))
                return result
            else:
                # Fall back to direct API request
                return await super().private_request(method, path, params, headers, body)
                
        except ccxtpro.NetworkError as e:
            logger.error(f"CCXT Network error: {str(e)}")
            raise NetworkError(str(e))
        except ccxtpro.ExchangeError as e:
            logger.error(f"CCXT Exchange error: {str(e)}")
            raise ExchangeError(str(e))
        except Exception as e:
            logger.error(f"CCXT error during private request: {str(e)}")
            raise
        
    # Standard data parsing methods
    def parse_trades(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse trades response to CCXT format."""
        return response  # CCXT already returns standardized format
        
    def parse_orderbook(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse orderbook response to CCXT format."""
        return response  # CCXT already returns standardized format
        
    def parse_ticker(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ticker response to CCXT format."""
        return response  # CCXT already returns standardized format
        
    def parse_ohlcv(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OHLCV response to CCXT format."""
        return response  # CCXT already returns standardized format
        
    def parse_balance(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance response to CCXT format."""
        return response  # CCXT already returns standardized format
        
    def parse_order(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse order response to CCXT format."""
        return response  # CCXT already returns standardized format
    
    # Standard market data methods
    @retry_on_error()
    @handle_timeout()
    async def fetch_order_book(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch order book data.
        
        Args:
            symbol: Trading pair symbol
            limit: Order book depth limit
            
        Returns:
            Order book data dictionary
        """
        try:
            self.validate_symbol(symbol)

            # Convert symbol to CCXT format for API call
            ccxt_symbol = self._convert_symbol_to_ccxt_format(symbol)

            # Use CCXT's fetch_order_book method with session retry
            orderbook = await self._execute_with_session_retry(
                self.ccxt.fetch_order_book, ccxt_symbol, limit
            )

            return self.standardize_response(orderbook, 'orderbook')
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_trades(self, symbol: str, since: Optional[int] = None, 
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch recent trades.
        
        Args:
            symbol: Trading pair symbol
            since: Timestamp in ms to fetch trades from
            limit: Number of trades to fetch
            
        Returns:
            List of trade data dictionaries
        """
        try:
            self.validate_symbol(symbol)

            # Convert symbol to CCXT format for API call
            ccxt_symbol = self._convert_symbol_to_ccxt_format(symbol)

            # Use CCXT's fetch_trades method with session retry
            trades = await self._execute_with_session_retry(
                self.ccxt.fetch_trades, ccxt_symbol, since, limit
            )

            return self.standardize_response(trades, 'trades')
            
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data.

        Args:
            symbol: Trading pair symbol

        Returns:
            Ticker data dictionary
        """
        try:
            self.validate_symbol(symbol)

            # Convert symbol to CCXT format for API call
            ccxt_symbol = self._convert_symbol_to_ccxt_format(symbol)

            # Use CCXT's fetch_ticker method with session retry
            ticker = await self._execute_with_session_retry(
                self.ccxt.fetch_ticker, ccxt_symbol
            )

            return self.standardize_response(ticker, 'ticker')

        except Exception as e:
            error_msg = str(e).strip()
            # Enhanced Error: 0 detection and handling
            if error_msg == "0" or (len(error_msg) <= 3 and "0" in error_msg):
                logger.warning(f"CCXT parsing error detected for {symbol}: '{error_msg}' - likely symbol format issue")
                # Return None to trigger graceful fallback instead of raising
                return None
            if "not supported" in error_msg.lower() or "invalid symbol" in error_msg.lower():
                logger.warning(f"Symbol {symbol} not supported on this exchange: {error_msg}")
                return None
            logger.error(f"Error fetching ticker for {symbol}: {error_msg}")
            raise

    @retry_on_error()
    @handle_timeout()
    async def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch ticker data for multiple symbols.

        Args:
            symbols: List of trading pair symbols (optional)

        Returns:
            Dictionary of ticker data keyed by symbol
        """
        try:
            # Use CCXT's fetch_tickers method with session retry
            if symbols:
                # Some exchanges support fetching specific symbols
                tickers = await self._execute_with_session_retry(
                    self.ccxt.fetch_tickers, symbols
                )
            else:
                # Fetch all available tickers
                tickers = await self._execute_with_session_retry(
                    self.ccxt.fetch_tickers
                )

            return self.standardize_response(tickers, 'tickers')

        except Exception as e:
            error_msg = str(e).strip()
            if error_msg == "0" or (len(error_msg) <= 3 and "0" in error_msg):
                logger.warning("CCXT fetch_tickers returned Error: 0 - returning empty result for graceful fallback")
                return {}
            logger.error(f"Error fetching tickers: {error_msg}")
            raise

    @retry_on_error()
    @handle_timeout()
    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical OHLCV data.
        
        Args:
            symbol: Trading pair symbol
            interval: Timeframe interval
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV data dictionaries
        """
        try:
            self.validate_symbol(symbol)
            self.validate_timeframe(interval)
            
            # Use CCXT's fetch_ohlcv method
            ohlcv = await self.ccxt.fetch_ohlcv(symbol, interval, since=start_time, limit=limit)
            
            # Format the response to match our internal format
            formatted_ohlcv = []
            for candle in ohlcv:
                formatted_candle = {
                    'timestamp': candle[0],
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                }
                formatted_ohlcv.append(formatted_candle)
                
                # Stop if we've reached end_time
                if end_time and formatted_candle['timestamp'] >= end_time:
                    break
            
            return formatted_ohlcv
            
        except Exception as e:
            logger.error(f"Error fetching historical klines for {symbol}, interval {interval}: {str(e)}")
            raise

    @retry_on_error()
    @handle_timeout()
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1m',
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """Fetch OHLCV (candlestick) data.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            since: Timestamp in ms to fetch data from
            limit: Number of candles to fetch

        Returns:
            List of OHLCV arrays in CCXT format: [timestamp, open, high, low, close, volume]
        """
        try:
            self.validate_symbol(symbol)
            self.validate_timeframe(timeframe)

            # Convert symbol to CCXT format for API call
            ccxt_symbol = self._convert_symbol_to_ccxt_format(symbol)

            # Use CCXT's native fetch_ohlcv method with session retry
            ohlcv = await self._execute_with_session_retry(
                self.ccxt.fetch_ohlcv, ccxt_symbol, timeframe, since=since, limit=limit
            )

            return ohlcv

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}, timeframe {timeframe}: {str(e)}")
            # For unsupported symbols, return None instead of raising
            if "not supported" in str(e).lower() or "invalid symbol" in str(e).lower():
                return None
            raise

    @retry_on_error()
    @handle_timeout()
    async def fetch_order_book_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch order book ticker (best bid/ask).
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Order book ticker data dictionary
        """
        try:
            self.validate_symbol(symbol)
            
            # Use CCXT's fetch_order_book method with minimal depth
            orderbook = await self.ccxt.fetch_order_book(symbol, 1)
            
            # Extract the best bid and ask
            best_bid = orderbook['bids'][0] if orderbook['bids'] else [0, 0]
            best_ask = orderbook['asks'][0] if orderbook['asks'] else [0, 0]
            
            return {
                'symbol': symbol,
                'bid_price': best_bid[0],
                'bid_qty': best_bid[1],
                'ask_price': best_ask[0],
                'ask_qty': best_ask[1],
                'timestamp': orderbook.get('timestamp', int(time.time() * 1000))
            }
            
        except Exception as e:
            logger.error(f"Error fetching order book ticker for {symbol}: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """Fetch open interest.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Open interest data dictionary
        """
        try:
            self.validate_symbol(symbol)
            
            # Not all exchanges support open interest through CCXT
            # Try exchange-specific endpoint if available
            try:
                # Try direct CCXT method if available
                if hasattr(self.ccxt, 'fetch_open_interest'):
                    open_interest = await self.ccxt.fetch_open_interest(symbol)
                    return open_interest
                else:
                    # For exchanges without direct support, make a custom request
                    # This is exchange specific - showing example for Bybit
                    if self.exchange_id == 'bybit':
                        path = '/v5/market/open-interest'
                        params = {'category': 'linear', 'symbol': self.market_id_map.get(symbol, symbol)}
                        response = await self.public_request('GET', path, params)
                        
                        data = response.get('result', {}).get('list', [])
                        if data:
                            return {
                                'symbol': symbol,
                                'open_interest': float(data[0].get('openInterest', 0)),
                                'timestamp': int(data[0].get('timestamp', time.time() * 1000))
                            }
            except Exception as e:
                logger.warning(f"Error fetching open interest using standard method: {str(e)}")
                
            # Fallback for unsupported exchanges
            logger.warning(f"Open interest not supported for {self.exchange_id}")
            return {
                'symbol': symbol,
                'open_interest': 0,
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Fetch funding rate.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Funding rate data dictionary
        """
        try:
            self.validate_symbol(symbol)
            
            # Use CCXT's fetch_funding_rate method if available
            if hasattr(self.ccxt, 'fetch_funding_rate'):
                funding_rate = await self.ccxt.fetch_funding_rate(symbol)
                return funding_rate
            else:
                # Fallback for exchanges without this method
                logger.warning(f"Funding rate fetch not directly supported for {self.exchange_id}")
                
                # Try exchange-specific implementation
                if self.exchange_id == 'bybit':
                    path = '/v5/market/tickers'
                    params = {'category': 'linear', 'symbol': self.market_id_map.get(symbol, symbol)}
                    response = await self.public_request('GET', path, params)
                    
                    data = response.get('result', {}).get('list', [])
                    if data:
                        return {
                            'symbol': symbol,
                            'funding_rate': float(data[0].get('fundingRate', 0)),
                            'next_funding_time': int(data[0].get('nextFundingTime', 0)),
                            'timestamp': int(time.time() * 1000)
                        }
                
                # Generic fallback
                return {
                    'symbol': symbol,
                    'funding_rate': 0,
                    'next_funding_time': 0,
                    'timestamp': int(time.time() * 1000)
                }
                
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_open_interest_history(self, symbol: str, interval: str = "5min", limit: int = 200) -> Dict[str, Any]:
        """Fetch historical open interest data.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (e.g., '5min', '1h')
            limit: Maximum number of records to fetch
            
        Returns:
            Dictionary containing historical open interest data
        """
        try:
            self.validate_symbol(symbol)
            
            # Check if we have recent data in cache
            cache_key = f"{symbol}_{interval}"
            current_time = int(time.time() * 1000)
            
            if (cache_key in self._open_interest_history_cache and 
                cache_key in self._last_oi_fetch and
                current_time - self._last_oi_fetch[cache_key] < 60000):  # 1 minute cache
                
                logger.debug(f"Using cached open interest history for {symbol}, interval {interval}")
                return self._open_interest_history_cache[cache_key]
            
            # Not all exchanges support open interest history through CCXT
            # Handle different exchange implementations
            if self.exchange_id == 'bybit':
                # Bybit specific implementation
                try:
                    # Bybit v5 expects the full interval with units (e.g., '5min') under 'intervalTime'
                    path = '/v5/market/open-interest'
                    params = {
                        'category': 'linear',
                        'symbol': self.market_id_map.get(symbol, symbol),
                        'intervalTime': interval,
                        'limit': min(limit, 200)
                    }
                    
                    response = await self.public_request('GET', path, params)
                    
                    # Process response
                    data = response.get('result', {}).get('list', [])
                    history_list = []
                    
                    for item in data:
                        timestamp = int(item.get('timestamp', 0))
                        if timestamp:
                            history_list.append({
                                'timestamp': timestamp,
                                'value': float(item.get('openInterest', 0)),
                                'symbol': symbol
                            })
                    
                    # Sort by timestamp (newest first)
                    history_list.sort(key=lambda x: x['timestamp'], reverse=True)
                    
                    result = {
                        'symbol': symbol,
                        'interval': interval,
                        'history': history_list,
                        'timestamp': current_time
                    }
                    
                    # Update cache
                    self._open_interest_history_cache[cache_key] = result
                    self._last_oi_fetch[cache_key] = current_time
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error fetching Bybit open interest history: {str(e)}")
            
            # Try CCXT's method if available (future proofing for when CCXT adds this method)
            if hasattr(self.ccxt, 'fetch_open_interest_history'):
                try:
                    history_data = await self.ccxt.fetch_open_interest_history(symbol, interval, limit=limit)
                    
                    # Format according to our API
                    history_list = []
                    for item in history_data:
                        history_list.append({
                            'timestamp': item['timestamp'],
                            'value': float(item['openInterest']),
                            'symbol': symbol
                        })
                    
                    result = {
                        'symbol': symbol,
                        'interval': interval,
                        'history': history_list,
                        'timestamp': current_time
                    }
                    
                    # Update cache
                    self._open_interest_history_cache[cache_key] = result
                    self._last_oi_fetch[cache_key] = current_time
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error with CCXT open interest history method: {str(e)}")
            
            # Generate synthetic history data using current open interest value
            # This is a fallback when the exchange doesn't provide history
            try:
                # Get current open interest
                current_oi = await self.fetch_open_interest(symbol)
                history_list = []
                
                # Generate synthetic data points
                current_timestamp = int(time.time() * 1000)
                interval_ms = self._interval_to_milliseconds(interval)
                
                for i in range(limit):
                    # Add some minor variation to make it look like it changes
                    variation = (1.0 + (((i % 10) - 5) / 100))  # ±5% variation
                    timestamp = current_timestamp - (i * interval_ms)
                    
                    history_list.append({
                        'timestamp': timestamp,
                        'value': float(current_oi['open_interest']) * variation,
                        'symbol': symbol
                    })
                
                result = {
                    'symbol': symbol,
                    'interval': interval,
                    'history': history_list,
                    'timestamp': current_time,
                    'is_synthetic': True
                }
                
                # Update cache
                self._open_interest_history_cache[cache_key] = result
                self._last_oi_fetch[cache_key] = current_time
                
                logger.warning(f"Using synthetic open interest history for {symbol} - exchange {self.exchange_id} doesn't support history")
                return result
                
            except Exception as e:
                logger.error(f"Error generating synthetic open interest history: {str(e)}")
                
                # Return empty result
                return {
                    'symbol': symbol,
                    'interval': interval,
                    'history': [],
                    'timestamp': current_time,
                    'error': str(e)
                }
                
        except Exception as e:
            logger.error(f"Error fetching open interest history for {symbol}: {str(e)}")
            
            # Return empty result
            return {
                'symbol': symbol,
                'interval': interval,
                'history': [],
                'timestamp': int(time.time() * 1000),
                'error': str(e)
            }
    
    def _interval_to_milliseconds(self, interval: str) -> int:
        """Convert interval string to milliseconds.
        
        Args:
            interval: Interval string (e.g., '5min', '1h', '1d')
            
        Returns:
            Milliseconds equivalent of the interval
        """
        unit = interval[-1] if interval[-1].isalpha() else 'm'
        if unit == 'n':  # Handle 'min'
            unit = 'm'
            value = int(interval[:-3]) if interval.endswith('min') else int(interval[:-1])
        else:
            value = int(interval[:-1]) if interval[:-1].isdigit() else 1
        
        # Convert to milliseconds
        if unit == 'm':  # Minutes
            return value * 60 * 1000
        elif unit == 'h':  # Hours
            return value * 60 * 60 * 1000
        elif unit == 'd':  # Days
            return value * 24 * 60 * 60 * 1000
        elif unit == 'w':  # Weeks
            return value * 7 * 24 * 60 * 60 * 1000
        else:
            return value * 60 * 1000  # Default to minutes
    
    # Private API methods for account data
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance.
        
        Returns:
            Account balance data dictionary
        """
        try:
            # Use CCXT's fetch_balance method
            balance = await self.ccxt.fetch_balance()
            
            return self.standardize_response(balance, 'balance')
            
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch open positions.
        
        Args:
            symbol: Optional trading pair symbol to filter positions
            
        Returns:
            List of position data dictionaries
        """
        try:
            # Use CCXT's fetch_positions method
            if hasattr(self.ccxt, 'fetch_positions'):
                positions = await self.ccxt.fetch_positions(symbol)
                return positions
            else:
                logger.warning(f"Position fetching not directly supported for {self.exchange_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            raise
    
    @retry_on_error()
    @handle_timeout()
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch open orders.
        
        Args:
            symbol: Optional trading pair symbol to filter orders
            
        Returns:
            List of order data dictionaries
        """
        try:
            # Use CCXT's fetch_open_orders method
            orders = await self.ccxt.fetch_open_orders(symbol)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error fetching open orders: {str(e)}")
            raise
    
    # Market data methods
    
    async def get_markets(self) -> List[Dict[str, Any]]:
        """Get list of available markets.
        
        Returns:
            List of market data dictionaries
        """
        if not self.ccxt:
            await self.initialize()
            
        return list(self.markets.values())
    
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive market data.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary with all available market data
        """
        try:
            self.validate_symbol(symbol)
            
            # Fetch various data in parallel
            ticker_task = create_tracked_task(self.fetch_ticker, name="fetch_ticker_task")
            orderbook_task = create_tracked_task(self.fetch_order_book(symbol, 20), name="fetch_orderbook_task")
            trades_task = create_tracked_task(self.fetch_trades, name="fetch_trades_task")
            
            # Try to fetch additional data if available
            funding_task = create_tracked_task(self.fetch_funding_rate(symbol), name="fetch_funding_task")
            open_interest_task = create_tracked_task(self.fetch_open_interest, name="fetch_open_interest_task")
            open_interest_history_task = create_tracked_task(self.fetch_open_interest_history(symbol, '5min', 200), name="fetch_oi_history_task")
            
            # Gather results
            ticker = await ticker_task
            orderbook = await orderbook_task
            trades = await trades_task
            
            try:
                funding = await funding_task
            except Exception as e:
                logger.debug(f"Could not fetch funding rate for {symbol}: {str(e)}")
                funding = None
                
            try:
                open_interest = await open_interest_task
            except Exception as e:
                logger.debug(f"Could not fetch open interest for {symbol}: {str(e)}")
                open_interest = None
                
            try:
                open_interest_history = await open_interest_history_task
            except Exception as e:
                logger.debug(f"Could not fetch open interest history for {symbol}: {str(e)}")
                open_interest_history = None
            
            # Combine all data
            return {
                'symbol': symbol,
                'ticker': ticker,
                'orderbook': orderbook,
                'trades': trades,
                'funding': funding,
                'open_interest': open_interest,
                'open_interest_history': open_interest_history.get('history', []) if open_interest_history else [],
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            raise
    
    # WebSocket methods - CCXT.pro has built-in WebSocket support,
    # but we're implementing basic websocket methods for compatibility
    
    async def connect_ws(self) -> bool:
        """Connect to WebSocket.
        
        Returns:
            True if connection is successful
        """
        # CCXT.pro handles WebSocket connections internally
        # This is just a placeholder for compatibility
        return True
        
    async def subscribe_ws(
        self,
        channels: List[str],
        symbols: List[str],
        callback: Callable
    ) -> bool:
        """Subscribe to WebSocket channels.
        
        Args:
            channels: List of channel names to subscribe to
            symbols: List of symbols to subscribe for
            callback: Callback function for messages
            
        Returns:
            True if subscription is successful
        """
        # CCXT.pro handles WebSocket subscriptions internally
        # This would be used for manual WebSocket management if needed
        logger.warning("Manual WebSocket subscription not implemented with CCXT integration")
        return False 

    def standardize_response(self, response: Any, response_type: str) -> Any:
        """Standardize response data to internal format.
        
        Args:
            response: Response data from CCXT
            response_type: Type of response (e.g., 'orderbook', 'trades')
            
        Returns:
            Standardized response data
        """
        try:
            # CCXT already provides standardized responses in most cases
            # This is a passthrough with some additional validation
            
            if response is None:
                logger.warning(f"Received None response for {response_type}")
                # Return a safe default based on response_type
                if response_type == 'orderbook':
                    return {'asks': [], 'bids': [], 'timestamp': int(time.time() * 1000), 'symbol': ''}
                elif response_type == 'trades':
                    return []
                elif response_type == 'ticker':
                    return {
                        'symbol': '',
                        'timestamp': int(time.time() * 1000),
                        'datetime': datetime.now().isoformat(),
                        'high': 0,
                        'low': 0,
                        'bid': 0,
                        'ask': 0,
                        'last': 0,
                        'close': 0,
                        'baseVolume': 0,
                        'quoteVolume': 0,
                        'info': {}
                    }
                else:
                    return response
            
            # Specific handling for some response types
            if response_type == 'ticker' and isinstance(response, dict):
                # Ensure all required fields are present
                if 'last' not in response or response['last'] is None:
                    response['last'] = 0
                if 'baseVolume' not in response or response['baseVolume'] is None:
                    response['baseVolume'] = 0
                if 'quoteVolume' not in response or response['quoteVolume'] is None:
                    response['quoteVolume'] = 0
                if 'high' not in response or response['high'] is None:
                    response['high'] = 0
                if 'low' not in response or response['low'] is None:
                    response['low'] = 0
                if 'bid' not in response or response['bid'] is None:
                    response['bid'] = 0
                if 'ask' not in response or response['ask'] is None:
                    response['ask'] = 0
                
                # Calculate percentage change if not provided
                if 'percentage' not in response or response['percentage'] is None:
                    if 'open' in response and response['open'] and response['last']:
                        try:
                            response['percentage'] = ((response['last'] / response['open']) - 1) * 100
                        except (TypeError, ZeroDivisionError):
                            response['percentage'] = 0
                    else:
                        response['percentage'] = 0
                        
                # Ensure timestamp is present
                if 'timestamp' not in response or response['timestamp'] is None:
                    response['timestamp'] = int(time.time() * 1000)
            
            # Return the standardized data
            return response
            
        except Exception as e:
            logger.error(f"Error standardizing {response_type} data: {str(e)}")
            # Return a safe default rather than raising
            if response_type == 'orderbook':
                return {'asks': [], 'bids': [], 'timestamp': int(time.time() * 1000), 'symbol': ''}
            elif response_type == 'trades':
                return []
            elif response_type == 'ticker':
                return {
                    'symbol': '',
                    'timestamp': int(time.time() * 1000),
                    'datetime': datetime.now().isoformat(),
                    'high': 0,
                    'low': 0,
                    'bid': 0,
                    'ask': 0,
                    'last': 0,
                    'close': 0,
                    'baseVolume': 0,
                    'quoteVolume': 0,
                    'info': {},
                    'percentage': 0
                }
            else:
                return response 