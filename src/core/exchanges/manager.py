from src.utils.task_tracker import create_tracked_task
"""Exchange manager module for managing exchange connectivity."""

from typing import Dict, List, Optional, Any
import logging
import asyncio
from .factory import ExchangeFactory
from .base import BaseExchange
from src.config.manager import ConfigManager
import time
import pandas as pd

# Import resilience components
from ..resilience import (
    handle_errors, RetryConfig, ErrorContext,
    circuit_breaker, EXCHANGE_API_CONFIG
)

logger = logging.getLogger(__name__)

class ExchangeNotInitializedError(RuntimeError):
    """Raised when accessing exchanges before initialization"""

class ExchangeManager:
    """Manager class for handling multiple exchange instances"""
    
    # Operation-specific timeout configurations (in seconds)
    OPERATION_TIMEOUTS = {
        'ticker': 10,      # Simple ticker fetch
        'orderbook': 15,   # Order book data
        'trades': 15,      # Recent trades
        'ohlcv': 30,       # OHLCV data (can be large)
        'markets': 20,     # Market list
        'risk_limits': 20, # Risk limits data
        'long_short_ratio': 15,
        'funding_rate': 10,
        'default': 15      # Default timeout
    }
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the exchange manager
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.exchanges: Dict[str, BaseExchange] = {}
        self._lock = asyncio.Lock()
        self._start_time = time.time()
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        self.factory = ExchangeFactory()
        self._disposed = False
        
    async def initialize(self) -> bool:
        """Initialize all configured exchanges"""
        try:
            self.logger.info("Initializing exchanges...")
            exchanges_config = self.config.get_value('exchanges', {})
            
            # Track if we found a primary exchange
            primary_found = False
            
            for exchange_id, config in exchanges_config.items():
                if not config.get('enabled', False):
                    self.logger.info(f"Exchange {exchange_id} is disabled in config")
                    continue
                
                try:
                    self.logger.info(f"Initializing {exchange_id} exchange...")
                    exchange = await self.factory.create_exchange(exchange_id, config)
                    
                    if exchange:
                        self.exchanges[exchange_id] = exchange
                        if config.get('primary', False):
                            primary_found = True
                            self.logger.info(f"Set {exchange_id} as primary exchange")
                    else:
                        self.logger.error(f"Failed to initialize {exchange_id} exchange")
                        
                except Exception as e:
                    self.logger.error(f"Error initializing {exchange_id} exchange: {str(e)}")
                    continue
            
            if not self.exchanges:
                self.logger.error("No exchanges could be initialized")
                return False
                
            if not primary_found:
                # If no primary exchange is configured but we have exchanges,
                # set the first one as primary
                first_exchange_id = next(iter(self.exchanges.keys()))
                exchanges_config[first_exchange_id]['primary'] = True
                self.logger.warning(f"No primary exchange configured, setting {first_exchange_id} as primary")
            
            self.initialized = True
            self.logger.info("Exchange initialization completed successfully")
            
            # Force cleanup of any orphaned aiohttp sessions created during initialization
            await self._cleanup_orphaned_sessions()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize exchanges: {str(e)}")
            return False
        
    async def get_primary_exchange(self) -> Optional[BaseExchange]:
        """Get the primary exchange with intelligent fallback

        Returns:
            Optional[BaseExchange]: The primary exchange or None if no exchange is available
        """
        if not self.exchanges:
            self.logger.error("No exchanges available")
            return None

        # First try to find an exchange marked as primary in config
        exchanges_config = self.config.get_value('exchanges', {})
        primary_exchange_id = None

        for exchange_id, exchange_config in exchanges_config.items():
            if exchange_config.get('primary', False) and exchange_id in self.exchanges:
                primary_exchange_id = exchange_id
                break

        # Test primary exchange health if found
        if primary_exchange_id:
            primary_exchange = self.exchanges[primary_exchange_id]
            if await self._test_exchange_health(primary_exchange):
                self.logger.debug(f"Primary exchange {primary_exchange_id} is healthy")
                return primary_exchange
            else:
                self.logger.warning(f"Primary exchange {primary_exchange_id} failed health check, trying fallbacks")

        # Fallback: try all other exchanges in order of preference
        fallback_order = ['binance', 'bybit', 'coinbase', 'hyperliquid']

        for exchange_id in fallback_order:
            if exchange_id in self.exchanges and exchange_id != primary_exchange_id:
                exchange = self.exchanges[exchange_id]
                if await self._test_exchange_health(exchange):
                    self.logger.info(f"Using fallback exchange: {exchange_id}")
                    return exchange

        # Last resort: return any available exchange without health check
        if self.exchanges:
            first_exchange = next(iter(self.exchanges.values()))
            self.logger.warning(f"All health checks failed, using first available without validation: {first_exchange.exchange_id}")
            return first_exchange

        return None

    async def _test_exchange_health(self, exchange: BaseExchange) -> bool:
        """Test if an exchange is responding to API calls

        Args:
            exchange: Exchange instance to test

        Returns:
            bool: True if exchange is healthy, False otherwise
        """
        try:
            # Simple health check - use fetch_status if available
            if hasattr(exchange, 'fetch_status'):
                status = await asyncio.wait_for(exchange.fetch_status(), timeout=5.0)
                return status.get('online', False) if isinstance(status, dict) else True
            else:
                # If no fetch_status, assume healthy (will fail gracefully later if not)
                return True
        except Exception as e:
            self.logger.debug(f"Exchange {exchange.exchange_id} health check failed: {str(e)}")
            return False
        
    async def cleanup(self):
        """Cleanup all exchange connections"""
        cleanup_tasks = []
        
        for exchange_id, exchange in self.exchanges.items():
            cleanup_tasks.append(self._cleanup_single_exchange(exchange_id, exchange))
        
        # Run all cleanup tasks concurrently
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.exchanges.clear()
        logger.info("Exchange manager cleanup completed")
    
    async def _cleanup_single_exchange(self, exchange_id: str, exchange):
        """Cleanup a single exchange with comprehensive error handling"""
        try:
            logger.info(f"Cleaning up {exchange_id} exchange...")
            
            # Close the custom exchange wrapper first
            try:
                await exchange.close()
                logger.info(f"Successfully closed {exchange_id} exchange wrapper")
            except Exception as e:
                logger.warning(f"Error closing {exchange_id} exchange wrapper: {str(e)}")
            
            # Handle integrated Binance client specifically
            if hasattr(exchange, 'integrated_client') and exchange.integrated_client:
                try:
                    await exchange.integrated_client.close()
                    logger.info(f"Successfully closed integrated client for {exchange_id}")
                except Exception as e:
                    logger.warning(f"Error closing integrated client for {exchange_id}: {str(e)}")
            
            # Handle CCXT exchange if it exists directly on the exchange
            if hasattr(exchange, 'ccxt_exchange') and exchange.ccxt_exchange:
                try:
                    await exchange.ccxt_exchange.close()
                    logger.info(f"Successfully closed CCXT exchange for {exchange_id}")
                except Exception as e:
                    logger.warning(f"Error closing CCXT exchange for {exchange_id}: {str(e)}")
            
            # Handle any other CCXT-related attributes
            if hasattr(exchange, 'ccxt') and exchange.ccxt:
                try:
                    await exchange.ccxt.close()
                    logger.info(f"Successfully closed CCXT client for {exchange_id}")
                except Exception as e:
                    logger.warning(f"Error closing CCXT client for {exchange_id}: {str(e)}")
            
            # Handle futures client if it exists
            if hasattr(exchange, 'futures_client') and exchange.futures_client:
                try:
                    if hasattr(exchange.futures_client, '__aexit__'):
                        await exchange.futures_client.__aexit__(None, None, None)
                    elif hasattr(exchange.futures_client, 'close'):
                        await exchange.futures_client.close()
                    logger.info(f"Successfully closed futures client for {exchange_id}")
                except Exception as e:
                    logger.warning(f"Error closing futures client for {exchange_id}: {str(e)}")
            
            # Additional cleanup for any remaining CCXT instances
            await self._cleanup_ccxt_instances(exchange_id, exchange)
                        
        except Exception as e:
            logger.error(f"Error during cleanup of {exchange_id} exchange: {str(e)}")
            # Continue with cleanup of other exchanges
    
    async def _cleanup_ccxt_instances(self, exchange_id: str, exchange):
        """Clean up any remaining CCXT instances for a specific exchange"""
        try:
            import gc
            import weakref
            
            # Look for any CCXT instances that might be associated with this exchange
            ccxt_instances_found = 0
            
            # Use a more conservative approach - only clean up instances we can safely identify
            for obj in gc.get_objects():
                if hasattr(obj, '__class__') and hasattr(obj.__class__, '__module__'):
                    if 'ccxt' in str(obj.__class__.__module__) and hasattr(obj, 'close'):
                        try:
                            # Check if this instance might belong to our exchange
                            if hasattr(obj, 'id') and obj.id == exchange_id.lower():
                                # Additional safety check - ensure it's not currently in use
                                if not getattr(obj, 'closed', True) and not hasattr(obj, '_in_use'):
                                    await obj.close()
                                    ccxt_instances_found += 1
                        except Exception as e:
                            logger.debug(f"Error closing CCXT instance for {exchange_id}: {e}")
            
            if ccxt_instances_found > 0:
                logger.info(f"Cleaned up {ccxt_instances_found} additional CCXT instances for {exchange_id}")
            
            # Force a small garbage collection to help clean up references
            gc.collect()
                
        except Exception as e:
            logger.debug(f"Error during additional CCXT cleanup for {exchange_id}: {e}")
    
    async def _cleanup_orphaned_sessions(self):
        """Clean up any orphaned aiohttp sessions created during initialization"""
        try:
            import gc
            import aiohttp
            
            # Force garbage collection to identify unclosed sessions
            gc.collect()
            
            # Find all aiohttp ClientSession objects
            sessions_found = 0
            connectors_found = 0
            
            for obj in gc.get_objects():
                if isinstance(obj, aiohttp.ClientSession):
                    if not obj.closed:
                        try:
                            await obj.close()
                            sessions_found += 1
                        except Exception as e:
                            logger.debug(f"Error closing orphaned session: {e}")
                elif isinstance(obj, aiohttp.TCPConnector):
                    if not obj.closed:
                        try:
                            await obj.close()
                            connectors_found += 1
                        except Exception as e:
                            logger.debug(f"Error closing orphaned connector: {e}")
            
            if sessions_found > 0 or connectors_found > 0:
                logger.info(f"Cleaned up {sessions_found} orphaned sessions and {connectors_found} connectors")
            else:
                logger.debug("No orphaned sessions or connectors found")
                
        except Exception as e:
            logger.warning(f"Error during orphaned session cleanup: {e}")
        
    async def get_market_data(
        self,
        symbol: str,
        exchange_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fetch market data from specified or all exchanges
        
        Args:
            symbol: Trading pair symbol
            exchange_id: Optional specific exchange to query
            limit: Optional limit for data points
            
        Returns:
            Dictionary containing market data from exchanges
        """
        if exchange_id:
            # First try the requested exchange
            if exchange_id in self.exchanges:
                results = await self._safe_fetch_market_data(
                    exchange_id,
                    self.exchanges[exchange_id],
                    symbol,
                    limit
                )
                return results
            else:
                # Fallback to primary exchange if requested exchange is not available
                self.logger.warning(f"Requested exchange {exchange_id} not available, falling back to primary exchange")
                primary_exchange = await self.get_primary_exchange()
                if primary_exchange:
                    results = await self._safe_fetch_market_data(
                        primary_exchange.exchange_id,
                        primary_exchange,
                        symbol,
                        limit
                    )
                    return results
                else:
                    raise ValueError(f"Exchange {exchange_id} not found and no fallback available")
            
        # Fetch from all exchanges in parallel
        tasks = []
        for ex_id, exchange in self.exchanges.items():
            task = create_tracked_task(
                self._safe_fetch_market_data(ex_id, exchange, symbol, limit, name="auto_tracked_task")
            )
            tasks.append(task)
            
        results = {}
        completed = await asyncio.gather(*tasks)
        for result in completed:
            results.update(result)
                
        return results
        
    async def _safe_fetch_market_data(
        self,
        exchange_id: str,
        exchange: BaseExchange,
        symbol: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Safely fetch market data from an exchange with error handling"""
        try:
            data = await exchange.fetch_market_data(symbol, limit)
            return {exchange_id: data}
        except Exception as e:
            logger.error(f"Error fetching data from {exchange_id}: {str(e)}")
            return {exchange_id: {"error": str(e)}}
            
    async def get_orderbook(
        self,
        symbol: str,
        exchange_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fetch orderbook from a specific exchange
        
        Args:
            symbol: Trading pair symbol
            exchange_id: Exchange to query
            limit: Depth of orderbook to fetch
            
        Returns:
            Orderbook data dictionary
        """
        if exchange_id not in self.exchanges:
            self.logger.warning(f"Requested exchange {exchange_id} not available for orderbook, falling back to primary exchange")
            primary_exchange = await self.get_primary_exchange()
            if primary_exchange:
                exchange_id = primary_exchange.exchange_id
            else:
                raise ValueError(f"Exchange {exchange_id} not found and no fallback available")

        if limit is None:
            limit = self.config.get_value('analysis.orderbook_depth', 50)
            
        # Ensure symbol is a string
        if isinstance(symbol, dict):
            symbol = symbol['symbol']
            
        return await self.exchanges[exchange_id].fetch_order_book(symbol, limit)
        
    async def get_historical_data(
        self,
        symbol: str,
        exchange_id: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical kline data from a specific exchange
        
        Args:
            symbol: Trading pair symbol
            exchange_id: Exchange to query
            interval: Timeframe interval
            start_time: Optional start timestamp
            end_time: Optional end timestamp
            limit: Optional limit of candles to fetch
            
        Returns:
            List of kline data dictionaries
        """
        if exchange_id not in self.exchanges:
            self.logger.warning(f"Requested exchange {exchange_id} not available for klines, falling back to primary exchange")
            primary_exchange = await self.get_primary_exchange()
            if primary_exchange:
                exchange_id = primary_exchange.exchange_id
            else:
                raise ValueError(f"Exchange {exchange_id} not found and no fallback available")

        # Get default limit from config timeframes
        if limit is None:
            for tf_name, tf_config in self.config['timeframes'].items():
                if str(tf_config['interval']) == str(interval):
                    limit = tf_config.get('required', 1000)
                    break
            else:
                # If no matching timeframe found, use default
                limit = 1000
                self.logger.warning(f"No matching timeframe config found for interval {interval}, using default limit {limit}")
        
        return await self.exchanges[exchange_id].fetch_historical_klines(
            symbol,
            interval,
            start_time,
            end_time,
            limit
        )
        
    async def close(self):
        """Close all exchange connections"""
        if self._disposed:
            return
            
        self._disposed = True
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except Exception as e:
                logger.error(f"Error closing exchange connection: {str(e)}")
        
        self.exchanges.clear()
        self.initialized = False
        logger.info("ExchangeManager properly disposed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.initialized:
            await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup"""
        await self.close()
        return False  # Don't suppress exceptions
                
    def get_active_exchanges(self) -> List[str]:
        """Get list of active exchange IDs"""
        return list(self.exchanges.keys())
        
    def get_exchange_info(self, exchange_id: str) -> Dict[str, Any]:
        """Get information about a specific exchange"""
        if exchange_id not in self.exchanges:
            self.logger.warning(f"Exchange {exchange_id} not available, providing generic info")
            # Return generic exchange info for unavailable exchanges
            return {
                'name': exchange_id,
                'enabled': False,
                'status': 'unavailable',
                'features': {},
                'rate_limits': {},
                'error': f"Exchange {exchange_id} not available"
            }

        exchange_config = self.config.get_value(f'exchanges.{exchange_id}', {})
        return {
            'name': exchange_config.get('name', exchange_id),
            'enabled': True,  # If it's in self.exchanges, it's enabled
            'features': exchange_config.get('features', {}),
            'rate_limits': exchange_config.get('rate_limits', {}),
            'websocket': {
                'enabled': exchange_config.get('websocket', {}).get('enabled', False),
                'channels': exchange_config.get('websocket', {}).get('channels', [])
            }
        }

    async def is_healthy(self) -> bool:
        """Check if the exchange manager and its exchanges are healthy."""
        try:
            # Check if at least one exchange is configured
            if not self.exchanges:
                self.logger.error("No exchanges configured")
                return False
            
            # Check if the primary exchange is healthy
            primary_exchange = await self.get_primary_exchange()
            if not primary_exchange:
                self.logger.error("No primary exchange configured")
                return False
            
            # For demo mode, check if API credentials are placeholder values
            api_key = getattr(primary_exchange, 'api_key', '')
            self.logger.info(f"Exchange API key status: {'empty' if not api_key else 'configured'}")
            if api_key in ['', 'demo-key', 'placeholder', None]:
                self.logger.info("Exchange running in demo mode - skipping connection test")
                return True
            
            # Check if the primary exchange can fetch market data
            is_primary_healthy = await primary_exchange.is_healthy()
            if not is_primary_healthy:
                self.logger.error("Primary exchange is not healthy")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking exchange manager health: {str(e)}")
            return False
            
    async def initialize_exchanges(self) -> None:
        """Initialize configured exchanges"""
        initialized = False
        
        for exchange_id, config in self.config['exchanges'].items():
            if not config.get('enabled', False):
                self.logger.info(f"Exchange {exchange_id} is disabled in config")
                continue
            
            try:
                exchange = await self.factory.create_exchange(exchange_id, config)
                if exchange:
                    self.exchanges[exchange_id] = exchange
                    initialized = True
                    self.logger.info(f"Successfully initialized {exchange_id} exchange")
            except Exception as e:
                self.logger.error(f"Failed to initialize {exchange_id} exchange: {str(e)}")
                continue
        
        if not initialized:
            self.logger.warning("No exchanges could be initialized, using mock exchange for testing")
            # Initialize mock exchange for testing
            self.exchanges['mock'] = await self.factory.create_mock_exchange() 

    def get_exchange_name(self) -> str:
        """Get the name of the primary exchange."""
        # Note: This is a sync method, we'll use the stored primary exchange
        if self.primary_exchange:
            if hasattr(self.primary_exchange, 'exchange_id'):
                return self.primary_exchange.exchange_id
            return self.primary_exchange.__class__.__name__.lower().replace('exchange', '')
        return "unknown"

    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Primary interface for market data fetching with enhanced logging"""
        if not self.initialized:
            raise ExchangeNotInitializedError("Access exchanges through manager only")
        
        self.logger.debug(f"Fetching comprehensive market data for {symbol}")
        
        # Fetch via primary exchange with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = await self._fetch_via_primary_exchange(symbol)
                # Log success and return data
                if data and 'ticker' in data and data['ticker']:
                    self.logger.debug(f"Successfully fetched market data for {symbol}")
                    if 'price' in data:
                        self.logger.debug(f"Price data for {symbol}: {data['price']}")
                    return data
                
                # If we didn't get good data but haven't used all retries
                if attempt < max_retries - 1:
                    self.logger.warning(f"Retrying fetch for {symbol} (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(1.0)
                else:
                    self.logger.error(f"Failed to fetch market data for {symbol} after {max_retries} attempts")
                    return {"symbol": symbol, "error": "max_retries_exceeded", "message": f"Failed after {max_retries} attempts"}
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error fetching market data for {symbol}: {error_msg}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)
                else:
                    return {"symbol": symbol, "error": "fetch_failed", "message": error_msg}

        return {"symbol": symbol, "error": "no_data_available", "message": "No data returned from exchange"}

    async def _fetch_via_primary_exchange(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch market data from the primary exchange
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict containing market data
        """
        try:
            primary_exchange = await self.get_primary_exchange()
            if not primary_exchange:
                self.logger.error("No primary exchange available to fetch market data")
                return {}
                
            # Initialize with basic structure
            market_data = {
                "symbol": symbol,
                "timestamp": int(time.time() * 1000)
            }
            
            # Fetch basic market data
            ticker = await primary_exchange.fetch_ticker(symbol)
            if not ticker:
                self.logger.warning(f"Failed to fetch ticker data for {symbol}")
                return {}
            
            # Log the ticker data for debugging
            self.logger.debug(f"Ticker data for {symbol}: volume={ticker.get('baseVolume', 'N/A')}, turnover={ticker.get('quoteVolume', 'N/A')}")
            
            # Include the raw ticker data for full access to all fields
            if 'raw_data' in ticker:
                market_data['raw_ticker'] = ticker['raw_data']
                self.logger.debug(f"Preserved raw ticker data with keys: {list(ticker['raw_data'].keys())}")
            
            # Preserve open interest data explicitly
            ticker_to_use = ticker.copy()
            
            # Remove raw_data to avoid circular references
            if 'raw_data' in ticker_to_use:
                del ticker_to_use['raw_data']
                
            # Add ticker to market data
            market_data["ticker"] = ticker_to_use
            
            # Try to add price structure for easier access
            try:
                market_data['price'] = {
                    'last': float(ticker.get('last', 0)),
                    'high': float(ticker.get('high', 0)),
                    'low': float(ticker.get('low', 0)),
                    'change_24h': float(ticker.get('change', 0)),
                    'volume': float(ticker.get('baseVolume', 0)),
                    'turnover': float(ticker.get('quoteVolume', 0))
                }
                
                # Add open interest to price structure if available
                if 'open_interest' in ticker or 'openInterest' in ticker:
                    oi_value = ticker.get('open_interest', ticker.get('openInterest', 0))
                    market_data['price']['open_interest'] = float(oi_value)
                    self.logger.debug(f"Added open_interest to price structure: {market_data['price']['open_interest']}")
                
                # Log the price structure for debugging
                self.logger.debug(f"Price structure for {symbol}: {market_data['price']}")
            except Exception as e:
                self.logger.debug(f"Failed to add price structure: {str(e)}")
            
            return market_data
            
        except Exception as e:
            error_msg = str(e)
            if "not supported" in error_msg.lower() or "invalid symbol" in error_msg.lower():
                self.logger.warning(f"Symbol {symbol} not supported on exchange: {error_msg}")
                return {"symbol": symbol, "error": "unsupported_symbol", "message": error_msg}
            else:
                self.logger.error(f"Error fetching market data for {symbol}: {error_msg}")
                return {"symbol": symbol, "error": "fetch_error", "message": error_msg}

    async def fetch_all_tickers(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Fetch market data for all symbols or specified symbols in a single API call.
        
        OPTIMIZATION: This method fetches all tickers in one API call instead of 
        making individual calls for each symbol, reducing latency from 30s to <1s.
        
        Args:
            symbols: Optional list of symbols to fetch. If None, fetches all available.
            
        Returns:
            Dict mapping symbol to market data
        """
        try:
            primary_exchange = await self.get_primary_exchange()
            if not primary_exchange:
                self.logger.error("No primary exchange available for bulk ticker fetch")
                return {}
            
            start_time = time.time()
            self.logger.info(f"Fetching all tickers in bulk...")
            
            # Most exchanges support fetching all tickers at once
            # This is much more efficient than individual calls
            all_tickers = {}
            
            try:
                # Try to fetch all tickers at once (most efficient)
                if hasattr(primary_exchange, 'fetch_tickers'):
                    if symbols:
                        # Some exchanges support fetching specific symbols in bulk
                        raw_tickers = await primary_exchange.fetch_tickers(symbols)
                    else:
                        # Fetch all available tickers
                        raw_tickers = await primary_exchange.fetch_tickers()
                    
                    # Process and format the tickers
                    for symbol, ticker in raw_tickers.items():
                        if ticker:
                            all_tickers[symbol] = {
                                'symbol': symbol,
                                'ticker': ticker,
                                'price': {
                                    'last': float(ticker.get('last', 0)),
                                    'high': float(ticker.get('high', 0)),
                                    'low': float(ticker.get('low', 0)),
                                    'change_24h': float(ticker.get('change', ticker.get('percentage', 0))),
                                    'volume': float(ticker.get('baseVolume', 0)),
                                    'turnover': float(ticker.get('quoteVolume', 0))
                                },
                                'timestamp': int(time.time() * 1000)
                            }
                    
                    fetch_duration = time.time() - start_time
                    self.logger.info(f"✅ Bulk ticker fetch completed: {len(all_tickers)} symbols in {fetch_duration:.2f}s")
                    
                else:
                    # Fallback: Exchange doesn't support bulk fetch
                    self.logger.warning("Exchange doesn't support bulk ticker fetch, falling back to individual calls")
                    
                    # If we must fetch individually, at least do it in parallel
                    if not symbols:
                        # Get available symbols from exchange
                        markets = await primary_exchange.load_markets()
                        symbols = list(markets.keys())[:30]  # Limit to top 30 if fetching all
                    
                    # Parallel fetch as fallback
                    tasks = []
                    for symbol in symbols:
                        task = create_tracked_task(self.fetch_market_data(symbol), name="fetch_market_data")
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for symbol, result in zip(symbols, results):
                        if isinstance(result, dict) and result:
                            all_tickers[symbol] = result
                    
                    fetch_duration = time.time() - start_time
                    self.logger.info(f"⚠️ Fallback parallel fetch completed: {len(all_tickers)} symbols in {fetch_duration:.2f}s")
                
            except Exception as e:
                self.logger.error(f"Error in bulk ticker fetch: {str(e)}")
                return {}
            
            return all_tickers
            
        except Exception as e:
            self.logger.error(f"Critical error in fetch_all_tickers: {str(e)}")
            return {}

    async def _fetch_ohlcv(self, symbol: str, timeframe: str = '1m', since: int = None, limit: int = None) -> List[Dict]:
        """
        Fetch OHLCV data through the primary exchange
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe interval
            since: Starting timestamp
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV candles
        """
        try:
            exchange = await self.get_primary_exchange()
            if not exchange:
                raise ValueError("No primary exchange configured")
            
            return await exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {str(e)}", exc_info=True)
            raise

    async def fetch_markets(self) -> Dict[str, List[Dict]]:
        """Fetch markets from all active exchanges"""
        markets = {}
        for exchange_id, exchange in self.exchanges.items():
            try:
                # Use the exchange-specific implementation
                markets[exchange_id] = await exchange.get_markets()
            except AttributeError:
                self.logger.error(f"Exchange {exchange_id} doesn't implement get_markets()")
            except Exception as e:
                self.logger.error(f"Error fetching markets from {exchange_id}: {str(e)}")
        return markets

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int):
        """Fetch OHLCV data through primary exchange"""
        exchange = await self.get_primary_exchange()
        return await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    async def fetch_order_book(self, symbol: str):
        """Fetch order book through primary exchange"""
        exchange = await self.get_primary_exchange()
        return await exchange.fetch_order_book(symbol)

    async def fetch_trades(self, symbol: str, limit: int):
        """Fetch recent trades through primary exchange"""
        exchange = await self.get_primary_exchange()
        return await exchange.fetch_trades(symbol, limit=limit)

    @handle_errors(
        operation='fetch_ticker',
        component='exchange_manager',
        circuit_breaker_name='exchange_api',
        retry_config=RetryConfig(max_attempts=3, base_delay=1.0)
    )
    async def fetch_ticker(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch ticker data for a symbol
        
        Args:
            symbol: The trading pair symbol
            exchange_id: Optional exchange ID (uses primary exchange if not specified)
            
        Returns:
            Ticker data or None if there was an error
        """
        max_retries = 3
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                # Get the appropriate exchange
                exchange = await self._get_exchange_for_operation(exchange_id)
                if not exchange:
                    self.logger.error(f"No exchange available to fetch ticker for {symbol}")
                    return None
                    
                # Format symbol if needed
                api_symbol = self._format_symbol_for_exchange(symbol)
                
                # Fetch the ticker with operation-specific timeout
                timeout = self.OPERATION_TIMEOUTS.get('ticker', 10)
                async with asyncio.timeout(timeout):
                    return await exchange.fetch_ticker(api_symbol)
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout fetching ticker for {symbol} (attempt {attempt+1}/{max_retries})")
            except AttributeError as e:
                if "object has no attribute 'fetch_ticker'" in str(e):
                    self.logger.error(f"Exchange does not support fetch_ticker method: {str(e)}")
                    # Try to reinitialize the exchange if possible
                    if attempt < max_retries - 1:
                        self.logger.info(f"Attempting to reinitialize exchange...")
                        try:
                            # Clear current exchanges
                            if exchange_id and exchange_id in self.exchanges:
                                await self.exchanges[exchange_id].close()
                                del self.exchanges[exchange_id]
                            # Reinitialize
                            if hasattr(self, 'config') and self.config:
                                exchanges_config = self.config.get_value('exchanges', {})
                                if exchange_id and exchange_id in exchanges_config:
                                    new_exchange = await self.factory.create_exchange(exchange_id, exchanges_config[exchange_id])
                                    if new_exchange:
                                        self.exchanges[exchange_id] = new_exchange
                        except Exception as reinit_err:
                            self.logger.error(f"Failed to reinitialize exchange: {str(reinit_err)}")
                else:
                    self.logger.error(f"Error in fetch_ticker for {symbol}: {str(e)}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                self.logger.error(f"Error fetching ticker for {symbol} (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return None
                
            # Wait before retrying
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
        
        return None
    
    async def _get_exchange_for_operation(self, exchange_id: Optional[str] = None) -> Optional[BaseExchange]:
        """
        Get the appropriate exchange for an operation
        
        Args:
            exchange_id: Optional specific exchange ID to use
            
        Returns:
            The exchange instance or None if not available
        """
        if exchange_id and exchange_id in self.exchanges:
            return self.exchanges[exchange_id]
        else:
            return await self.get_primary_exchange()
    
    def _format_symbol_for_exchange(self, symbol: str) -> str:
        """
        Format a symbol to be compatible with exchange API
        
        Args:
            symbol: The symbol in standard format
            
        Returns:
            Formatted symbol string
        """
        if '/' in symbol and ':' not in symbol:
            # Convert traditional format to exchange specific
            base, quote = symbol.split('/')
            return f"{base}{quote}"
        return symbol
    
    async def fetch_orderbook(self, symbol: str, limit: int = 50, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch orderbook data for a symbol.
        
        Args:
            symbol: The trading pair symbol
            limit: Maximum number of orderbook levels to fetch
            exchange_id: Optional exchange ID (uses primary exchange if not specified)
            
        Returns:
            Orderbook data dictionary or None if error
        """
        try:
            # Get the appropriate exchange
            exchange = None
            if exchange_id and exchange_id in self.exchanges:
                exchange = self.exchanges[exchange_id]
            else:
                exchange = await self.get_primary_exchange()
                
            if not exchange:
                self.logger.error(f"No exchange available to fetch orderbook for {symbol}")
                return None
                
            # Fetch orderbook from the exchange
            return await exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            self.logger.error(f"Error fetching orderbook for {symbol}: {str(e)}")
            return None
    
    async def fetch_long_short_ratio(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch the long/short ratio for a symbol from an exchange
        
        Args:
            symbol: Symbol to fetch long/short ratio for
            exchange_id: Optional specific exchange to use
            
        Returns:
            Dict containing long/short ratio data or None if not available
        """
        try:
            exchange = await self._get_exchange_for_operation(exchange_id)
            if not exchange:
                return None
                
            # Standardize the symbol format
            if '/' in symbol and ':' not in symbol:
                # Convert traditional format to exchange specific
                base, quote = symbol.split('/')
                api_symbol = f"{base}{quote}"
            else:
                api_symbol = symbol
                
            # Try to fetch the long/short ratio
            try:
                self.logger.debug(f"Fetching long/short ratio for {api_symbol}")
                ratio_data = await exchange.fetch_long_short_ratio(api_symbol)
                return ratio_data
            except (AttributeError, NotImplementedError):
                self.logger.warning(f"Exchange {exchange.exchange_id} does not support long/short ratio")
                return None
            except Exception as e:
                self.logger.error(f"Error fetching long/short ratio: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in fetch_long_short_ratio: {str(e)}")
            return None
    
    async def fetch_funding_rate(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch the funding rate for a symbol from an exchange
        
        Args:
            symbol: Symbol to fetch funding rate for
            exchange_id: Optional specific exchange to use
            
        Returns:
            Dict containing funding rate data or None if not available
        """
        try:
            exchange = await self._get_exchange_for_operation(exchange_id)
            if not exchange:
                return None
                
            # Standardize the symbol format
            if '/' in symbol and ':' not in symbol:
                # Convert traditional format to exchange specific
                base, quote = symbol.split('/')
                api_symbol = f"{base}{quote}"
            else:
                api_symbol = symbol
                
            # Try to fetch the funding rate
            try:
                self.logger.debug(f"Fetching funding rate for {api_symbol}")
                
                # Check if exchange has ticker with funding rate
                ticker = await exchange.fetch_ticker(api_symbol)
                if ticker and 'fundingRate' in ticker:
                    return {
                        'fundingRate': ticker['fundingRate'],
                        'nextFundingTime': ticker.get('nextFundingTime', None),
                        'timestamp': ticker.get('timestamp', int(time.time() * 1000))
                    }
                
                # Check if exchange has a specific funding rate method
                if hasattr(exchange, 'fetch_funding_rate'):
                    funding_data = await exchange.fetch_funding_rate(api_symbol)
                    return funding_data
                    
                self.logger.warning(f"Exchange {exchange.exchange_id} does not provide funding rate data")
                return {'fundingRate': 0}
                
            except (AttributeError, NotImplementedError):
                self.logger.warning(f"Exchange {exchange.exchange_id} does not support funding rate")
                return {'fundingRate': 0}
            except Exception as e:
                self.logger.error(f"Error fetching funding rate: {str(e)}")
                return {'fundingRate': 0}
                
        except Exception as e:
            self.logger.error(f"Error in fetch_funding_rate: {str(e)}")
            return {'fundingRate': 0}
    
    async def fetch_risk_limits(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch risk limits data for a symbol.
        
        Args:
            symbol: The trading pair symbol
            exchange_id: Optional exchange ID (uses primary exchange if not specified)
            
        Returns:
            Risk limits data or None if not supported/error
        """
        try:
            # Get the appropriate exchange
            exchange = None
            if exchange_id and exchange_id in self.exchanges:
                exchange = self.exchanges[exchange_id]
            else:
                exchange = await self.get_primary_exchange()
                
            if not exchange:
                self.logger.error(f"No exchange available to fetch risk limits for {symbol}")
                return None
                
            # Check if the exchange supports fetching risk limits
            if hasattr(exchange, 'fetch_risk_limits'):
                return await exchange.fetch_risk_limits(symbol)
            elif hasattr(exchange, '_make_request'):
                # Fallback to direct API call if supported
                self.logger.warning(f"Using direct API call for risk limits for {symbol}")
                try:
                    response = await exchange._make_request('GET', '/v5/market/risk-limit', {
                        'category': 'linear',
                        'symbol': symbol
                    })
                    
                    if response and response.get('retCode') == 0:
                        risk_data = response.get('result', {}).get('list', [])
                        return {
                            'symbol': symbol,
                            'riskLimits': risk_data,
                            'timestamp': int(time.time() * 1000)
                        }
                    
                    # If we get here, the API call failed or returned invalid data
                    self.logger.warning(f"Direct API call for risk limits failed: {response}")
                except Exception as e:
                    self.logger.error(f"Error in direct API call for risk limits: {str(e)}")
            else:
                self.logger.warning(f"Risk limits not supported for {symbol}")
            
            # Return a default structure
            return {
                'symbol': symbol,
                'riskLimits': [],
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            self.logger.error(f"Error fetching risk limits for {symbol}: {str(e)}")
            return None

    async def ping(self) -> Dict[str, Any]:
        """Test exchange connectivity and return status.

        This method is used by the health monitoring system to check
        if the exchange manager and its primary exchange are accessible.

        Returns:
            Dict containing connectivity status and response time
        """
        start_time = time.time()

        try:
            # Check if exchange manager is initialized
            if not self.initialized or not self.exchanges:
                return {
                    'status': 'error',
                    'message': 'Exchange manager not initialized',
                    'response_time_ms': (time.time() - start_time) * 1000
                }

            # Get primary exchange
            primary_exchange = await self.get_primary_exchange()
            if not primary_exchange:
                return {
                    'status': 'error',
                    'message': 'No primary exchange available',
                    'response_time_ms': (time.time() - start_time) * 1000
                }

            # Test connectivity with a lightweight operation
            # Use is_healthy method if available, otherwise try a simple operation
            if hasattr(primary_exchange, 'is_healthy'):
                is_healthy = await primary_exchange.is_healthy()
                status = 'healthy' if is_healthy else 'degraded'
                message = 'Exchange connection verified' if is_healthy else 'Exchange connection degraded'
            else:
                # Fallback: try to load markets (lightweight operation for most exchanges)
                try:
                    await asyncio.wait_for(primary_exchange.load_markets(), timeout=5.0)
                    status = 'healthy'
                    message = 'Exchange connection verified'
                except asyncio.TimeoutError:
                    status = 'timeout'
                    message = 'Exchange connection timeout'
                except Exception as e:
                    status = 'error'
                    message = f'Exchange connection error: {str(e)}'

            response_time = (time.time() - start_time) * 1000

            return {
                'status': status,
                'message': message,
                'exchange_id': getattr(primary_exchange, 'exchange_id', 'unknown'),
                'exchange_count': len(self.exchanges),
                'response_time_ms': round(response_time, 2),
                'timestamp': int(time.time() * 1000)
            }

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Error in exchange ping: {str(e)}")

            return {
                'status': 'error',
                'message': f'Ping failed: {str(e)}',
                'response_time_ms': round(response_time, 2),
                'timestamp': int(time.time() * 1000)
            }