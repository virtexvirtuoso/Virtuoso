"""Exchange manager module for managing exchange connectivity."""

from typing import Dict, List, Optional, Any
import logging
import asyncio
from .factory import ExchangeFactory
from .base import BaseExchange
from src.config.manager import ConfigManager
import time
import pandas as pd

logger = logging.getLogger(__name__)

class ExchangeNotInitializedError(RuntimeError):
    """Raised when accessing exchanges before initialization"""

class ExchangeManager:
    """Manager class for handling multiple exchange instances"""
    
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
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize exchanges: {str(e)}")
            return False
        
    async def get_primary_exchange(self) -> Optional[BaseExchange]:
        """Get the primary exchange
        
        Returns:
            Optional[BaseExchange]: The primary exchange or None if no primary exchange is available
        """
        if not self.exchanges:
            self.logger.error("No exchanges available")
            return None
            
        # First try to find an exchange marked as primary in config
        exchanges_config = self.config.get_value('exchanges', {})
        for exchange_id, exchange_config in exchanges_config.items():
            if exchange_config.get('primary', False) and exchange_id in self.exchanges:
                self.logger.debug(f"Found primary exchange: {exchange_id}")
                return self.exchanges[exchange_id]
                
        # If no primary exchange is configured, return the first available exchange
        first_exchange = next(iter(self.exchanges.values()))
        self.logger.warning(f"No primary exchange configured, using first available: {first_exchange.exchange_id}")
        return first_exchange
        
    async def cleanup(self):
        """Cleanup all exchange connections"""
        for exchange_id, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Successfully closed {exchange_id} exchange connection")
            except Exception as e:
                logger.error(f"Error closing {exchange_id} exchange connection: {str(e)}")
        
        self.exchanges.clear()
        
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
            if exchange_id not in self.exchanges:
                raise ValueError(f"Exchange {exchange_id} not found")
            results = await self._safe_fetch_market_data(
                exchange_id,
                self.exchanges[exchange_id],
                symbol,
                limit
            )
            return results
            
        # Fetch from all exchanges in parallel
        tasks = []
        for ex_id, exchange in self.exchanges.items():
            task = asyncio.create_task(
                self._safe_fetch_market_data(ex_id, exchange, symbol, limit)
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
            raise ValueError(f"Exchange {exchange_id} not found")
            
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
            raise ValueError(f"Exchange {exchange_id} not found")
            
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
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except Exception as e:
                logger.error(f"Error closing exchange connection: {str(e)}")
                
    def get_active_exchanges(self) -> List[str]:
        """Get list of active exchange IDs"""
        return list(self.exchanges.keys())
        
    def get_exchange_info(self, exchange_id: str) -> Dict[str, Any]:
        """Get information about a specific exchange"""
        if exchange_id not in self.exchanges:
            raise ValueError(f"Exchange {exchange_id} not found")
            
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
        exchange = self.get_primary_exchange()
        if exchange:
            return exchange.exchange_id  # Bybit exchange has this property
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
                    return {}
            except Exception as e:
                self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)
                else:
                    return {}
        
        return {}

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
            self.logger.debug(f"Ticker data for {symbol}: volume={ticker.get('volume', 'N/A')}, turnover={ticker.get('turnover', 'N/A')}")
            
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
                    'volume': float(ticker.get('volume', 0)),
                    'turnover': float(ticker.get('turnover', 0))
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
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
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
            exchange = self.get_primary_exchange()
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

    async def fetch_ticker(self, symbol: str, exchange_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch ticker data for a symbol.
        
        Args:
            symbol: The trading pair symbol
            exchange_id: Optional exchange ID (uses primary exchange if not specified)
            
        Returns:
            Ticker data dictionary or None if error
        """
        try:
            # Get the appropriate exchange
            exchange = None
            if exchange_id and exchange_id in self.exchanges:
                exchange = self.exchanges[exchange_id]
            else:
                exchange = await self.get_primary_exchange()
                
            if not exchange:
                self.logger.error(f"No exchange available to fetch ticker for {symbol}")
                return None
                
            # Fetch ticker from the exchange
            return await exchange.fetch_ticker(symbol)
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            return None
    
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
        """Fetch long/short ratio data for a symbol.
        
        Args:
            symbol: The trading pair symbol
            exchange_id: Optional exchange ID (uses primary exchange if not specified)
            
        Returns:
            Long/short ratio data or None if not supported/error
        """
        try:
            # Get the appropriate exchange
            exchange = None
            if exchange_id and exchange_id in self.exchanges:
                exchange = self.exchanges[exchange_id]
            else:
                exchange = await self.get_primary_exchange()
                
            if not exchange:
                self.logger.error(f"No exchange available to fetch long/short ratio for {symbol}")
                return None
                
            # Check if the exchange supports fetching long/short ratio
            if hasattr(exchange, 'fetch_long_short_ratio'):
                return await exchange.fetch_long_short_ratio(symbol)
            elif hasattr(exchange, '_make_request'):
                # Fallback to direct API call if supported
                self.logger.warning(f"Using direct API call for long/short ratio for {symbol}")
                try:
                    response = await exchange._make_request('GET', '/v5/market/account-ratio', {
                        'category': 'linear',
                        'symbol': symbol,
                        'period': '5min',
                        'limit': 1
                    })
                    
                    if response and response.get('retCode') == 0:
                        ratio_data = response.get('result', {}).get('list', [])
                        if ratio_data:
                            latest = ratio_data[0]
                            return {
                                'symbol': symbol,
                                'long': float(latest.get('longAccount', 50.0)),
                                'short': float(latest.get('shortAccount', 50.0)),
                                'timestamp': int(time.time() * 1000)
                            }
                    
                    # If we get here, the API call failed or returned invalid data
                    self.logger.warning(f"Direct API call for long/short ratio failed: {response}")
                except Exception as e:
                    self.logger.error(f"Error in direct API call for long/short ratio: {str(e)}")
            else:
                self.logger.warning(f"Long/short ratio not supported for {symbol}")
                
            # Return a default structure
            return {
                'symbol': symbol,
                'longShortRatio': 1.0,  # Default to balanced
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            self.logger.error(f"Error fetching long/short ratio for {symbol}: {str(e)}")
            return None
    
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