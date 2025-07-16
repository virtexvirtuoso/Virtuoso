"""
Binance Exchange Implementation for Virtuoso Trading System

This module provides Binance-specific extensions to the BaseExchange framework,
optimized for market data analysis and sentiment indicators.

Integrates with:
- ExchangeManager as secondary data source  
- MarketDataManager for automatic failover
- Market Prism Analysis Stack for confluence scoring
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from decimal import Decimal

# Import the base exchange class we'll extend
from .base import BaseExchange
from ...data_acquisition.binance import BinanceFuturesClient, BinanceSymbolConverter, BinanceExchange as IntegratedBinanceExchange

# Set up logging
logger = logging.getLogger(__name__)

class BinanceExchange(BaseExchange):
    """
    Binance-specific implementation extending BaseExchange.
    
    This class adds Binance-specific features while maintaining compatibility
    with Virtuoso's exchange management architecture:
    - Enhanced futures market support
    - Funding rate analysis  
    - Open interest tracking
    - Binance-specific rate limiting
    - Integration with ExchangeManager and MarketDataManager
    """
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """
        Initialize Binance exchange.
        
        Args:
            config: Configuration dictionary from config.yaml
            error_handler: Optional error handler for logging/alerts
        """
        # Call the parent class constructor first
        super().__init__(config, error_handler)
        
        # Set the exchange ID so the system knows this is Binance
        self.exchange_id = 'binance'
        
        # Get Binance-specific configuration
        exchanges_config = config.get('exchanges', {})
        self.binance_config = exchanges_config.get('binance', {})
        
        # Rate limiting settings
        rate_limits = self.binance_config.get('rate_limits', {})
        self.max_requests_per_minute = rate_limits.get('requests_per_minute', 1200)
        self.max_weight_per_minute = rate_limits.get('weight_per_minute', 6000)
        
        # API credentials
        api_config = self.binance_config.get('api_credentials', {})
        self.api_key = api_config.get('api_key', '') or None
        self.api_secret = api_config.get('api_secret', '') or None
        
        # Exchange configuration
        self.testnet = self.binance_config.get('testnet', False)
        self.data_only = self.binance_config.get('data_only', True)
        
        # Initialize integrated Binance client
        self.integrated_client = None
        
        self.logger.info("Binance exchange initialized for Virtuoso integration")
    
    async def initialize(self) -> bool:
        """
        Initialize the Binance exchange connection.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing Binance exchange for Virtuoso...")
            
            # Initialize the integrated Binance client
            self.integrated_client = IntegratedBinanceExchange(
                api_key=self.api_key if self.api_key else None,
                api_secret=self.api_secret if self.api_secret else None,
                testnet=self.testnet,
                rate_limit=1200  # Conservative rate limiting
            )
            
            # Initialize the integrated client
            await self.integrated_client.initialize()
            
            # Set up market data
            markets = await self.integrated_client.get_markets()
            self.markets = markets
            self.symbols = set(markets.keys()) if isinstance(markets, dict) else set()
            
            # Set up timeframes (Binance standard timeframes)
            self.timeframes = {
                '1m': '1m',
                '3m': '3m', 
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '2h': '2h',
                '4h': '4h',
                '6h': '6h',
                '8h': '8h',
                '12h': '12h',
                '1d': '1d',
                '3d': '3d',
                '1w': '1w',
                '1M': '1M'
            }
            
            # Set API URLs
            self.api_urls = {
                'public': 'https://api.binance.com' if not self.testnet else 'https://testnet.binance.vision',
                'private': 'https://api.binance.com' if not self.testnet else 'https://testnet.binance.vision'
            }
            
            # Set WebSocket endpoints
            self.ws_endpoints = {
                'public': 'wss://stream.binance.com:9443/ws' if not self.testnet else 'wss://testnet.binance.vision/ws',
                'private': 'wss://stream.binance.com:9443/ws' if not self.testnet else 'wss://testnet.binance.vision/ws'
            }
            
            # Mark as initialized
            self.initialized = True
            self._is_healthy = True
            self._last_health_check = time.time()
            
            self.logger.info("Binance exchange initialized successfully for Virtuoso")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance exchange: {str(e)}")
            return False
    
    async def health_check(self) -> bool:
        """Check exchange connection health."""
        try:
            if not self.integrated_client:
                return False
            
            # Simple connectivity test
            await self.integrated_client.get_exchange_info()
            self._is_healthy = True
            self._last_health_check = time.time()
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            self._is_healthy = False
            return False
    
    async def close(self) -> None:
        """Close exchange connection."""
        try:
            if self.integrated_client:
                await self.integrated_client.close()
            await super().close()
        except Exception as e:
            self.logger.error(f"Error closing Binance exchange: {str(e)}")
    
    # Implementation of required abstract methods from BaseExchange
    
    def sign(self, method: str, path: str, params: Optional[Dict] = None, 
            headers: Optional[Dict] = None, body: Optional[Dict] = None):
        """Sign request for private endpoints."""
        # The integrated client handles signing
        url = f"{self.api_urls['private']}{path}"
        return url, params or {}, headers or {}, body or {}
    
    def parse_trades(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse trades response to CCXT format."""
        return response  # Integrated client returns standardized format
    
    def parse_orderbook(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse orderbook response to CCXT format.""" 
        return response  # Integrated client returns standardized format
    
    def parse_ticker(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ticker response to CCXT format."""
        return response  # Integrated client returns standardized format
    
    def parse_ohlcv(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OHLCV response to CCXT format."""
        return response  # Integrated client returns standardized format
    
    def parse_balance(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance response to CCXT format."""
        return response  # Integrated client returns standardized format
    
    def parse_order(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse order response to CCXT format."""
        return response  # Integrated client returns standardized format
    
    # Market data methods that interface with integrated client
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data for a symbol."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        return await self.integrated_client.get_ticker(symbol)
    
    async def fetch_order_book(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch order book data."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        return await self.integrated_client.get_order_book(symbol, limit or 20)
    
    async def fetch_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch recent trades."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        return await self.integrated_client.get_recent_trades(symbol, limit or 50)
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', since: Optional[int] = None, limit: Optional[int] = None) -> List[List]:
        """Fetch OHLCV candlestick data."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        return await self.integrated_client.get_ohlcv(symbol, timeframe, limit or 100)
    
    # Binance-specific methods for enhanced market analysis
    
    async def fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Fetch current funding rate for futures symbol."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        return await self.integrated_client.get_current_funding_rate(symbol)
    
    async def fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """Fetch open interest for futures symbol with improved error handling."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            # The futures client now handles 400 errors gracefully
            return await self.integrated_client.get_open_interest(symbol)
        except Exception as e:
            # Log as warning instead of error since some symbols don't have OI
            self.logger.warning(f"Could not fetch open interest for {symbol}: {str(e)}")
            # Return empty structure for compatibility
            return {
                'symbol': symbol,
                'openInterest': 0.0,
                'timestamp': int(time.time() * 1000)
            }
    
    async def fetch_open_interest_history(self, symbol: str, interval: str = "5min", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch open interest history for futures symbol.
        
        Args:
            symbol: Symbol to fetch open interest history for
            interval: Time interval (e.g., "5min", "1h") - currently ignored for Binance
            limit: Number of historical records to fetch
            
        Returns:
            List of open interest historical data
            
        Note:
            Binance doesn't provide historical open interest with intervals like Bybit.
            This method returns current open interest as a single data point for compatibility.
        """
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            # Use the futures client to get open interest data
            # For now, return current open interest as a single point since Binance 
            # doesn't provide historical open interest intervals like Bybit
            current_oi = await self.integrated_client.get_open_interest(symbol)
            
            # Format as historical data (single point for now)
            history = [{
                'symbol': symbol,
                'openInterest': current_oi['openInterest'],
                'timestamp': current_oi['timestamp']
            }]
            
            self.logger.debug(f"Fetched open interest history for {symbol}: {len(history)} records (interval: {interval})")
            return history
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch open interest history for {symbol}: {str(e)}")
            return []
    
    async def fetch_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Fetch market sentiment indicators."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        return await self.integrated_client.get_market_sentiment(symbol)
    
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch comprehensive market data for Virtuoso analysis.
        
        This method provides all the data needed for the Market Prism Analysis Stack.
        """
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            # Get comprehensive market data including both spot and futures
            complete_data = await self.integrated_client.get_complete_market_data(symbol, include_futures=True)
            
            # Transform to format expected by Virtuoso's Market Prism Analysis
            virtuoso_data = {
                'symbol': symbol,
                'timestamp': complete_data['timestamp'],
                'ticker': complete_data['spot']['ticker'],
                'orderbook': complete_data['spot']['orderbook'], 
                'trades': complete_data['spot']['recent_trades'],
                'ohlcv': complete_data['spot']['ohlcv'],
                'exchange': 'binance'
            }
            
            # Add futures-specific sentiment data if available
            if complete_data.get('futures'):
                futures = complete_data['futures']
                virtuoso_data['sentiment'] = {
                    'funding_rate': futures['funding']['fundingRate'],
                    'funding_rate_percentage': futures['funding']['fundingRatePercentage'],
                    'open_interest': futures['openInterest']['openInterest'],
                    'premium_index': futures['premiumIndex']['markPrice'] - futures['premiumIndex']['indexPrice']
                }
            
            return virtuoso_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            raise
    
    # Market listing methods
    
    async def get_markets(self) -> List[Dict[str, Any]]:
        """Get list of available markets."""
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        markets = await self.integrated_client.get_markets()
        return list(markets.values()) if isinstance(markets, dict) else markets
    
    # Symbol format utilities
    
    def normalize_symbol(self, symbol: str, target_format: str = 'spot') -> str:
        """Convert symbol between spot and futures formats."""
        if not self.integrated_client:
            return symbol
        return self.integrated_client.convert_symbol(symbol, target_format)
    
    def is_futures_symbol(self, symbol: str) -> bool:
        """Check if symbol is in futures format."""
        if not self.integrated_client:
            return False
        return self.integrated_client.is_futures_symbol(symbol)
    
    # WebSocket Methods (Required by BaseExchange)
    
    async def connect_ws(self) -> bool:
        """
        Connect to Binance WebSocket API.
        
        Returns:
            True if connection is successful
        """
        try:
            # Use the integrated client's WebSocket connection
            if self.integrated_client:
                result = await self.integrated_client.connect_ws()
                self.logger.info(f"Binance WebSocket connection: {'successful' if result else 'failed'}")
                return result
            else:
                self.logger.error("Integrated client not available for WebSocket connection")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Binance WebSocket: {str(e)}")
            return False
    
    async def subscribe_ws(self, channels: List[str]) -> bool:
        """
        Subscribe to WebSocket channels.
        
        Args:
            channels: List of channels to subscribe to
            
        Returns:
            True if subscription is successful
        """
        try:
            # Use the integrated client's WebSocket subscription
            if self.integrated_client:
                result = await self.integrated_client.subscribe_ws(channels)
                self.logger.info(f"Binance WebSocket subscription: {'successful' if result else 'failed'}")
                return result
            else:
                # Placeholder implementation for when integrated client is not available
                self.logger.info(f"Binance WebSocket subscription to {len(channels)} channels (placeholder implementation)")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to WebSocket channels: {str(e)}")
            return False
    
    async def fetch_market_tickers(self) -> List[Dict[str, Any]]:
        """
        Fetch market tickers for all symbols.
        
        Returns:
            List of ticker dictionaries containing market data
        """
        try:
            self.logger.debug("Fetching market tickers from Binance API...")
            
            # Use the integrated client if available
            if self.integrated_client:
                # Try to get 24hr ticker stats directly without exchange info first
                tickers = []
                try:
                    self.logger.debug("Attempting to fetch 24hr ticker data directly...")
                    # Use the futures client to get 24hr ticker stats for all symbols
                    ticker_data = await self.integrated_client.futures_client.get_all_24hr_tickers()
                    
                    if isinstance(ticker_data, list):
                        self.logger.debug(f"Successfully received {len(ticker_data)} ticker records")
                        for ticker in ticker_data:
                            # Normalize the ticker data to match expected format
                            normalized_ticker = {
                                'symbol': ticker.get('symbol', ''),
                                'lastPrice': ticker.get('lastPrice', '0'),
                                'volume': ticker.get('volume', '0'),
                                'quoteVolume': ticker.get('quoteVolume', '0'),
                                'priceChangePercent': ticker.get('priceChangePercent', '0'),
                                'highPrice': ticker.get('highPrice', '0'),
                                'lowPrice': ticker.get('lowPrice', '0'),
                                'openPrice': ticker.get('openPrice', '0'),
                                'count': ticker.get('count', 0),
                                'timestamp': int(time.time() * 1000)
                            }
                            # Only include USDT perpetual futures
                            if ticker.get('symbol', '').endswith('USDT'):
                                tickers.append(normalized_ticker)
                   
                    self.logger.debug(f"Successfully fetched {len(tickers)} market tickers from Binance")
                    return tickers
                    
                except Exception as e:
                    self.logger.error(f"Error fetching 24hr ticker data directly: {str(e)}")
                    # Continue to try the exchange info approach as fallback
                
                # Fallback: Try to get exchange info to get all symbols (original approach)
                try:
                    self.logger.debug("Trying fallback approach with exchange info...")
                    exchange_info = await self.integrated_client.get_exchange_info()
                    if exchange_info and 'symbols' in exchange_info:
                        symbols = [s['symbol'] for s in exchange_info['symbols'] 
                                  if s.get('status') == 'TRADING' and s.get('contractType') == 'PERPETUAL']
                        self.logger.debug(f"Found {len(symbols)} trading symbols from exchange info")
                        
                        # If we got symbols, try to fetch ticker data again
                        ticker_data = await self.integrated_client.futures_client.get_all_24hr_tickers()
                        if isinstance(ticker_data, list):
                            for ticker in ticker_data:
                                normalized_ticker = {
                                    'symbol': ticker.get('symbol', ''),
                                    'lastPrice': ticker.get('lastPrice', '0'),
                                    'volume': ticker.get('volume', '0'),
                                    'quoteVolume': ticker.get('quoteVolume', '0'),
                                    'priceChangePercent': ticker.get('priceChangePercent', '0'),
                                    'highPrice': ticker.get('highPrice', '0'),
                                    'lowPrice': ticker.get('lowPrice', '0'),
                                    'openPrice': ticker.get('openPrice', '0'),
                                    'count': ticker.get('count', 0),
                                    'timestamp': int(time.time() * 1000)
                                }
                                tickers.append(normalized_ticker)
                        
                        self.logger.debug(f"Fallback approach fetched {len(tickers)} market tickers")
                        return tickers
                    else:
                        self.logger.warning("Exchange info approach also failed")
                        
                except Exception as e:
                    self.logger.error(f"Fallback exchange info approach failed: {str(e)}")
                
                return []
            else:
                self.logger.warning("Integrated client not available for fetching market tickers")
                return []
            
        except Exception as e:
            self.logger.error(f"Failed to fetch market tickers: {str(e)}")
            return []
    
    # Binance-specific methods for market analysis and risk management
    
    async def fetch_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch Long/Short Ratio data for a futures symbol.
        
        This method is required by the ExchangeManager to avoid "not supported" warnings.
        
        Args:
            symbol: Symbol to fetch ratio for
            period: Period interval ("5m","15m","30m","1h","2h","4h","6h","12h","1d")
            limit: Number of records to return
            
        Returns:
            List of long/short ratio data
        """
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            # Use the futures client to get long/short ratio data
            return await self.integrated_client.futures_client.get_long_short_ratio(symbol, period, limit)
        except Exception as e:
            self.logger.warning(f"Failed to fetch long/short ratio for {symbol}: {str(e)}")
            return []
    
    async def fetch_risk_limits(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch risk limits (leverage bracket) for a futures symbol.
        
        This method is required by the ExchangeManager to avoid "not supported" warnings.
        
        Args:
            symbol: Symbol to fetch risk limits for
            
        Returns:
            Risk limits information including max leverage and position limits
        """
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            # Use the futures client to get leverage bracket data
            leverage_data = await self.integrated_client.futures_client.get_leverage_bracket(symbol)
            
            if leverage_data:
                # Transform to format expected by the system (similar to Bybit's risk-limit)
                risk_limits = {
                    'symbol': symbol,
                    'maxLeverage': leverage_data.get('maxLeverage', 1),
                    'minNotional': leverage_data.get('minNotional', 0),
                    'maxNotional': leverage_data.get('maxNotional', float('inf')),
                    'brackets': leverage_data.get('brackets', []),
                    'timestamp': int(time.time() * 1000)
                }
                
                self.logger.info(f"Risk limits for {symbol}: max leverage {risk_limits['maxLeverage']}x")
                return risk_limits
            else:
                self.logger.warning(f"No risk limits data found for {symbol}")
                return {}
                
        except Exception as e:
            self.logger.warning(f"Failed to fetch risk limits for {symbol}: {str(e)}")
            return {}
    
    async def fetch_top_trader_ratio(self, symbol: str, period: str = "5m", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch Top Trader Long/Short Position Ratio.
        
        Args:
            symbol: Symbol to fetch ratio for
            period: Period interval
            limit: Number of records to return
            
        Returns:
            List of top trader position ratio data
        """
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            return await self.integrated_client.futures_client.get_top_trader_long_short_ratio(symbol, period, limit)
        except Exception as e:
            self.logger.warning(f"Failed to fetch top trader ratio for {symbol}: {str(e)}")
            return []
    
    async def fetch_taker_volume(self, symbol: str, period: str = "5m", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch Taker Buy/Sell Volume data.
        
        Args:
            symbol: Symbol to fetch volume data for
            period: Period interval
            limit: Number of records to return
            
        Returns:
            List of taker volume data
        """
        if not self.integrated_client:
            raise RuntimeError("Exchange not initialized")
        
        try:
            return await self.integrated_client.futures_client.get_taker_buy_sell_volume(symbol, period, limit)
        except Exception as e:
            self.logger.warning(f"Failed to fetch taker volume for {symbol}: {str(e)}")
            return []

    async def fetch_status(self) -> Dict[str, Any]:
        """Fetch Binance exchange status for system health monitoring."""
        try:
            if not self.integrated_client:
                return {
                    'online': False,
                    'has_trading': False,
                    'status': 'error',
                    'error': 'Exchange not initialized',
                    'timestamp': int(time.time() * 1000)
                }
            
            # Check connectivity with a simple API call
            try:
                # Try to get server time to verify connectivity
                server_info = await self.integrated_client.get_server_time()
                
                if server_info and 'serverTime' in server_info:
                    server_time = int(server_info['serverTime'])
                    local_time = int(time.time() * 1000)
                    time_diff = abs(server_time - local_time)
                    
                    # Check if time difference is reasonable (less than 30 seconds)
                    is_online = time_diff <= 30000
                    
                    return {
                        'online': is_online,
                        'has_trading': True,  # Binance supports trading
                        'status': 'ok' if is_online else 'time_sync_error',
                        'timestamp': int(time.time() * 1000),
                        'server_time': server_time,
                        'time_diff_ms': time_diff,
                        'rate_limit': {
                            'remaining': 1200,  # Default rate limit info
                            'limit': 1200,
                            'reset_time': int(time.time() + 60)
                        }
                    }
                else:
                    return {
                        'online': False,
                        'has_trading': False,
                        'status': 'error',
                        'error': 'Invalid server response',
                        'timestamp': int(time.time() * 1000)
                    }
                    
            except Exception as e:
                return {
                    'online': False,
                    'has_trading': False,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': int(time.time() * 1000)
                }
                
        except Exception as e:
            self.logger.error(f"Error fetching Binance status: {str(e)}")
            return {
                'online': False,
                'has_trading': False,
                'status': 'error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }

    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from Binance (required by system status endpoint)."""
        try:
            if not self.integrated_client:
                self.logger.error("Exchange not initialized")
                return []
            
            # Get exchange info which contains market data
            exchange_info = await self.integrated_client.get_exchange_info()
            if not exchange_info or 'symbols' not in exchange_info:
                self.logger.error("Failed to get exchange info")
                return []
            
            # Convert to CCXT-compatible format
            formatted_markets = []
            for symbol_info in exchange_info['symbols']:
                try:
                    if symbol_info.get('status') != 'TRADING':
                        continue  # Skip non-trading symbols
                        
                    # Parse base and quote currencies
                    symbol = symbol_info['symbol']
                    base_asset = symbol_info['baseAsset']
                    quote_asset = symbol_info['quoteAsset']
                    
                    formatted_market = {
                        'id': symbol,
                        'symbol': f"{base_asset}/{quote_asset}",
                        'base': base_asset,
                        'quote': quote_asset,
                        'baseId': base_asset,
                        'quoteId': quote_asset,
                        'active': symbol_info.get('status') == 'TRADING',
                        'type': 'spot' if symbol_info.get('contractType') is None else 'swap',
                        'spot': symbol_info.get('contractType') is None,
                        'margin': symbol_info.get('isMarginTradingAllowed', False),
                        'future': symbol_info.get('contractType') == 'PERPETUAL',
                        'swap': symbol_info.get('contractType') == 'PERPETUAL',
                        'option': False,
                        'contract': symbol_info.get('contractType') is not None,
                        'linear': True if symbol_info.get('contractType') else None,
                        'inverse': False,
                        'contractSize': 1,
                        'precision': {
                            'amount': len(str(symbol_info.get('filters', [{}])[1].get('stepSize', '0.00000001')).split('.')[-1].rstrip('0')),
                            'price': len(str(symbol_info.get('filters', [{}])[0].get('tickSize', '0.00000001')).split('.')[-1].rstrip('0'))
                        },
                        'limits': {
                            'amount': {
                                'min': float(symbol_info.get('filters', [{}])[1].get('minQty', 0)),
                                'max': float(symbol_info.get('filters', [{}])[1].get('maxQty', 1000000))
                            },
                            'price': {
                                'min': float(symbol_info.get('filters', [{}])[0].get('minPrice', 0)),
                                'max': float(symbol_info.get('filters', [{}])[0].get('maxPrice', 1000000))
                            },
                            'cost': {
                                'min': float(symbol_info.get('filters', [{}])[2].get('minNotional', 0)),
                                'max': float('inf')
                            }
                        },
                        'info': symbol_info
                    }
                    formatted_markets.append(formatted_market)
                    
                except Exception as e:
                    self.logger.warning(f"Error formatting market {symbol_info.get('symbol', 'unknown')}: {e}")
                    continue
                    
            self.logger.debug(f"Formatted {len(formatted_markets)} markets for CCXT compatibility")
            return formatted_markets
            
        except Exception as e:
            self.logger.error(f"Error fetching markets: {str(e)}")
            return [] 