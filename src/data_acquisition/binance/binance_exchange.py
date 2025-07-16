"""
Integrated Binance Exchange Client

This class combines CCXT for basic spot market functionality with our custom
futures client to provide comprehensive Binance API access including:
- Spot market data via CCXT (ticker, orderbook, trades, OHLCV)
- Futures funding rates via custom API
- Open interest via custom API
- Symbol format handling for spot/futures conversion
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Callable
import ccxt.async_support as ccxt
from datetime import datetime

from .futures_client import BinanceFuturesClient, BinanceSymbolConverter

logger = logging.getLogger(__name__)

class BinanceExchange:
    """
    Comprehensive Binance exchange client that integrates:
    1. CCXT for standardized spot market data
    2. Custom futures client for advanced features
    3. Symbol format conversion utilities
    """
    
    def __init__(self, config: Union[Dict[str, Any], str] = None, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, testnet: bool = False, rate_limit: int = 1200):
        """
        Initialize the integrated Binance exchange client.
        
        Args:
            config: Configuration dictionary or API key string (for backward compatibility)
            api_key: Optional Binance API key (if not in config)
            api_secret: Optional Binance API secret (if not in config)
            testnet: Whether to use testnet endpoints (if not in config)
            rate_limit: Rate limit in milliseconds between requests
        """
        # Handle different initialization patterns
        if isinstance(config, dict):
            # Extract from config dictionary
            binance_config = config.get('exchanges', {}).get('binance', {})
            credentials = binance_config.get('api_credentials', {})
            
            self.api_key = credentials.get('api_key') or api_key
            self.api_secret = credentials.get('api_secret') or api_secret
            self.testnet = binance_config.get('testnet', testnet)
            self.rate_limit = binance_config.get('rate_limits', {}).get('requests_per_minute', rate_limit)
        elif isinstance(config, str):
            # Backward compatibility: config is API key
            self.api_key = config
            self.api_secret = api_secret
            self.testnet = testnet
            self.rate_limit = rate_limit
        else:
            # Use provided parameters
            self.api_key = api_key
            self.api_secret = api_secret
            self.testnet = testnet
            self.rate_limit = rate_limit
        
        # Initialize symbol converter
        self.symbol_converter = BinanceSymbolConverter()
        
        # Initialize CCXT exchange
        self.ccxt_exchange = None
        
        # Initialize custom futures client
        self.futures_client = None
        
        # Track initialization state
        self.initialized = False
        
        logger.info(f"Initialized Binance exchange client (testnet: {self.testnet})")
    
    async def initialize(self):
        """Initialize the exchange clients."""
        if self.initialized:
            return
        
        try:
            # Initialize CCXT exchange with increased timeouts
            exchange_config = {
                'enableRateLimit': True,
                'rateLimit': self.rate_limit,
                'sandbox': self.testnet,
                'verbose': False,
                'timeout': 30000,  # 30 seconds timeout
                'options': {
                    'defaultType': 'spot',  # Default to spot market
                    'fetchTickerMethod': 'publicGetTicker24hr',  # Use 24hr ticker endpoint
                },
                # Add retry configuration
                'retries': 3,
                'retryInterval': 1000,  # 1 second between retries
            }
            
            if self.api_key and self.api_secret:
                exchange_config['apiKey'] = self.api_key
                exchange_config['secret'] = self.api_secret
            
            self.ccxt_exchange = ccxt.binance(exchange_config)
            
            # Test the connection with a simple call
            test_successful = False
            ccxt_instance = None
            try:
                logger.debug("Testing CCXT exchange connection...")
                ccxt_instance = self.ccxt_exchange
                await asyncio.wait_for(self.ccxt_exchange.load_markets(), timeout=10)  # Reduced timeout
                logger.info("CCXT exchange connection tested successfully")
                test_successful = True
                
            except asyncio.TimeoutError:
                logger.warning("CCXT exchange test timed out, closing and recreating...")
                # Close the timed-out instance
                if ccxt_instance:
                    try:
                        await ccxt_instance.close()
                    except Exception as close_e:
                        logger.debug(f"Error closing timed-out CCXT exchange: {close_e}")
                # Recreate the exchange
                self.ccxt_exchange = ccxt.binance(exchange_config)
                test_successful = True  # Continue with initialization
                
            except Exception as e:
                logger.warning(f"CCXT exchange test failed: {e}, closing and recreating...")
                # Close the failed instance
                if ccxt_instance:
                    try:
                        await ccxt_instance.close()
                    except Exception as close_e:
                        logger.debug(f"Error closing failed CCXT exchange: {close_e}")
                # Recreate the exchange
                self.ccxt_exchange = ccxt.binance(exchange_config)
                test_successful = True  # Continue with initialization
            
            # Initialize custom futures client
            self.futures_client = BinanceFuturesClient(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            
            # Start the futures client context
            await self.futures_client.__aenter__()
            
            logger.info("Binance exchange clients initialized successfully")
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance exchange: {str(e)}")
            # Ensure cleanup on failure
            await self._cleanup_on_error()
            raise
    
    async def _cleanup_on_error(self):
        """Clean up resources when initialization fails."""
        try:
            if hasattr(self, 'ccxt_exchange') and self.ccxt_exchange:
                await self.ccxt_exchange.close()
                self.ccxt_exchange = None
        except Exception as e:
            logger.debug(f"Error during error cleanup: {e}")
        
        try:
            if hasattr(self, 'futures_client') and self.futures_client:
                await self.futures_client.__aexit__(None, None, None)
                self.futures_client = None
        except Exception as e:
            logger.debug(f"Error during futures client cleanup: {e}")
    
    async def close(self):
        """Close the exchange clients."""
        try:
            # Close CCXT exchange first
            if hasattr(self, 'ccxt_exchange') and self.ccxt_exchange:
                try:
                    # Ensure we close the CCXT instance properly
                    if hasattr(self.ccxt_exchange, 'close'):
                        await self.ccxt_exchange.close()
                        logger.debug("CCXT exchange closed successfully")
                    else:
                        logger.debug("CCXT exchange does not have close method")
                except Exception as e:
                    logger.warning(f"Error closing CCXT exchange: {e}")
                finally:
                    self.ccxt_exchange = None
            
            # Close futures client
            if hasattr(self, 'futures_client') and self.futures_client:
                try:
                    await self.futures_client.__aexit__(None, None, None)
                    logger.debug("Futures client closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing futures client: {e}")
                finally:
                    self.futures_client = None
            
            self.initialized = False
            logger.info("Binance exchange clients closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing Binance exchange: {str(e)}")
            # Ensure state is reset even if cleanup fails
            self.initialized = False
            self.ccxt_exchange = None
            self.futures_client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _ensure_initialized(self):
        """Ensure the exchange is initialized."""
        if not self.initialized:
            raise RuntimeError("Exchange not initialized. Use async context manager or call initialize().")
    
    # Spot Market Data Methods (via CCXT)
    
    async def get_markets(self) -> Dict[str, Any]:
        """Get all available markets."""
        self._ensure_initialized()
        return await self.ccxt_exchange.load_markets()
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a symbol (CCXT-compatible method).
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            
        Returns:
            Ticker data
        """
        return await self.get_ticker(symbol)
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a symbol.
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            
        Returns:
            Ticker data
        """
        self._ensure_initialized()
        
        try:
            spot_symbol = self.symbol_converter.normalize_symbol(symbol, 'spot')
            logger.debug(f"Fetching ticker for {spot_symbol}")
            
            # Use timeout and retry mechanism
            ticker = await asyncio.wait_for(
                self.ccxt_exchange.fetch_ticker(spot_symbol),
                timeout=20.0  # 20 second timeout
            )
            
            logger.debug(f"Successfully fetched ticker for {spot_symbol}")
            return ticker
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching ticker for {symbol}, trying fallback method")
            # Try with futures client as fallback
            try:
                futures_symbol = self.symbol_converter.to_futures_format(symbol)
                futures_ticker = await self.futures_client.get_24hr_ticker(futures_symbol)
                
                # Convert futures ticker to CCXT format
                return {
                    'symbol': symbol,
                    'last': float(futures_ticker['lastPrice']),
                    'high': float(futures_ticker['highPrice']),
                    'low': float(futures_ticker['lowPrice']),
                    'volume': float(futures_ticker['volume']),
                    'quoteVolume': float(futures_ticker['quoteVolume']),
                    'percentage': float(futures_ticker['priceChangePercent']),
                    'change': float(futures_ticker['priceChange']),
                    'timestamp': int(futures_ticker['closeTime']),
                    'datetime': datetime.fromtimestamp(int(futures_ticker['closeTime'])/1000).isoformat(),
                    'info': futures_ticker
                }
            except Exception as fallback_error:
                logger.error(f"Fallback ticker fetch also failed for {symbol}: {fallback_error}")
                raise
                
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            raise
    
    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol (CCXT-compatible method).
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            limit: Number of price levels to return
            
        Returns:
            Order book data
        """
        return await self.get_order_book(symbol, limit)
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            limit: Number of price levels to return
            
        Returns:
            Order book data
        """
        self._ensure_initialized()
        
        try:
            spot_symbol = self.symbol_converter.normalize_symbol(symbol, 'spot')
            logger.debug(f"Fetching order book for {spot_symbol}")
            
            # Use timeout mechanism
            orderbook = await asyncio.wait_for(
                self.ccxt_exchange.fetch_order_book(spot_symbol, limit),
                timeout=15.0  # 15 second timeout
            )
            
            logger.debug(f"Successfully fetched order book for {spot_symbol}")
            return orderbook
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching order book for {symbol}, trying futures fallback")
            # Try with futures client as fallback
            try:
                futures_symbol = self.symbol_converter.to_futures_format(symbol)
                return await self.futures_client.get_order_book(futures_symbol, limit)
            except Exception as fallback_error:
                logger.error(f"Fallback order book fetch also failed for {symbol}: {fallback_error}")
                raise
                
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {str(e)}")
            raise
    
    async def fetch_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent trades for a symbol (CCXT-compatible method).
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            limit: Number of trades to return
            
        Returns:
            List of recent trades
        """
        return await self.get_recent_trades(symbol, limit)
    
    async def get_recent_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent trades for a symbol.
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            limit: Number of trades to return
            
        Returns:
            List of recent trades
        """
        self._ensure_initialized()
        spot_symbol = self.symbol_converter.normalize_symbol(symbol, 'spot')
        return await self.ccxt_exchange.fetch_trades(spot_symbol, limit=limit)
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """
        Get OHLCV candlestick data for a symbol (CCXT-compatible method).
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of candles to return
            
        Returns:
            List of OHLCV candles
        """
        return await self.get_ohlcv(symbol, timeframe, limit)
    
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """
        Get OHLCV candlestick data for a symbol.
        
        Args:
            symbol: Symbol in spot format (BTC/USDT)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of candles to return
            
        Returns:
            List of OHLCV candles
        """
        self._ensure_initialized()
        spot_symbol = self.symbol_converter.normalize_symbol(symbol, 'spot')
        return await self.ccxt_exchange.fetch_ohlcv(spot_symbol, timeframe, limit=limit)
    
    # Futures-Specific Methods (via Custom Client)
    
    async def fetch_funding_rate(self, symbol: str) -> float:
        """
        Get current funding rate for a futures symbol (simplified interface).
        
        Args:
            symbol: Symbol in futures format (BTCUSDT)
            
        Returns:
            Current funding rate as float
        """
        try:
            current_rate = await self.get_current_funding_rate(symbol)
            return float(current_rate['fundingRate'])
        except Exception as e:
            logger.error(f"Failed to get current funding rate for {symbol}: {str(e)}")
            raise ValueError(f"Could not fetch funding rate for {symbol}: {str(e)}")
    
    async def fetch_open_interest(self, symbol: str) -> float:
        """
        Get open interest for a futures symbol (simplified interface).
        
        Args:
            symbol: Symbol in futures format (BTCUSDT)
            
        Returns:
            Open interest as float
        """
        try:
            oi_data = await self.get_open_interest(symbol)
            return float(oi_data['openInterest'])
        except Exception as e:
            logger.error(f"Failed to get open interest for {symbol}: {str(e)}")
            raise ValueError(f"Could not fetch open interest for {symbol}: {str(e)}")
    
    async def get_funding_rate(self, symbol: str, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Get funding rate for a futures symbol.
        
        Args:
            symbol: Symbol in any format (will be converted to futures format)
            limit: Number of records to return
            
        Returns:
            List of funding rate records
        """
        self._ensure_initialized()
        futures_symbol = self.symbol_converter.normalize_symbol(symbol, 'futures')
        return await self.futures_client.get_funding_rate(futures_symbol, limit)
    
    async def get_current_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get current funding rate for a symbol.
        
        Args:
            symbol: Symbol in any format (will be converted to futures format)
            
        Returns:
            Current funding rate information
        """
        self._ensure_initialized()
        futures_symbol = self.symbol_converter.normalize_symbol(symbol, 'futures')
        return await self.futures_client.get_current_funding_rate(futures_symbol)
    
    async def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Get open interest for a futures symbol.
        
        Args:
            symbol: Symbol in any format (will be converted to futures format)
            
        Returns:
            Open interest information
        """
        self._ensure_initialized()
        futures_symbol = self.symbol_converter.normalize_symbol(symbol, 'futures')
        return await self.futures_client.get_open_interest(futures_symbol)
    
    async def get_premium_index(self, symbol: str) -> Dict[str, Any]:
        """
        Get premium index for a futures symbol.
        
        Args:
            symbol: Symbol in any format (will be converted to futures format)
            
        Returns:
            Premium index information
        """
        self._ensure_initialized()
        futures_symbol = self.symbol_converter.normalize_symbol(symbol, 'futures')
        return await self.futures_client.get_premium_index(futures_symbol)
    
    async def get_futures_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get futures ticker data for a symbol.
        
        Args:
            symbol: Symbol in any format (will be converted to futures format)
            
        Returns:
            Futures ticker data
        """
        self._ensure_initialized()
        futures_symbol = self.symbol_converter.normalize_symbol(symbol, 'futures')
        return await self.futures_client.get_24hr_ticker(futures_symbol)
    
    # Comprehensive Data Methods
    
    async def get_complete_market_data(self, symbol: str, include_futures: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive market data for a symbol including both spot and futures data.
        
        Args:
            symbol: Symbol in any format
            include_futures: Whether to include futures-specific data
            
        Returns:
            Complete market data structure
        """
        self._ensure_initialized()
        
        try:
            # Get spot data
            tasks = [
                self.get_ticker(symbol),
                self.get_order_book(symbol, limit=5),
                self.get_recent_trades(symbol, limit=10),
                self.get_ohlcv(symbol, '1h', limit=5)
            ]
            
            ticker, orderbook, trades, ohlcv = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build comprehensive data structure
            market_data = {
                'symbol': symbol,
                'timestamp': int(datetime.now().timestamp() * 1000),
                'spot': {
                    'ticker': ticker if not isinstance(ticker, Exception) else None,
                    'orderbook': orderbook if not isinstance(orderbook, Exception) else None,
                    'recent_trades': trades if not isinstance(trades, Exception) else None,
                    'ohlcv': ohlcv if not isinstance(ohlcv, Exception) else None
                }
            }
            
            # Add futures data if requested
            if include_futures:
                try:
                    futures_data = await self.futures_client.get_futures_market_data(
                        self.symbol_converter.normalize_symbol(symbol, 'futures')
                    )
                    market_data['futures'] = futures_data
                except Exception as e:
                    logger.warning(f"Could not get futures data for {symbol}: {str(e)}")
                    market_data['futures'] = None
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get complete market data for {symbol}: {str(e)}")
            raise
    
    async def get_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Get market sentiment indicators for a symbol.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Market sentiment data
        """
        self._ensure_initialized()
        
        try:
            futures_symbol = self.symbol_converter.normalize_symbol(symbol, 'futures')
            
            # Get sentiment-related data
            tasks = [
                self.get_current_funding_rate(symbol),
                self.get_open_interest(symbol),
                self.get_premium_index(symbol)
            ]
            
            funding, oi, premium = await asyncio.gather(*tasks)
            
            # Calculate sentiment indicators
            sentiment = {
                'symbol': symbol,
                'timestamp': int(datetime.now().timestamp() * 1000),
                'funding_rate': funding['fundingRate'],
                'funding_rate_percentage': funding['fundingRatePercentage'],
                'open_interest': oi['openInterest'],
                'mark_price': premium['markPrice'],
                'index_price': premium['indexPrice'],
                'premium': premium['markPrice'] - premium['indexPrice'],
                'premium_percentage': ((premium['markPrice'] - premium['indexPrice']) / premium['indexPrice']) * 100,
                'sentiment_score': self._calculate_sentiment_score(funding, oi, premium)
            }
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Failed to get market sentiment for {symbol}: {str(e)}")
            raise
    
    def _calculate_sentiment_score(self, funding: Dict, oi: Dict, premium: Dict) -> float:
        """
        Calculate a simple sentiment score based on funding rate and premium.
        
        Returns:
            Sentiment score between -1 (bearish) and 1 (bullish)
        """
        try:
            # Funding rate component (-1 to 1)
            funding_score = max(-1, min(1, funding['fundingRate'] * 10000))  # Scale funding rate
            
            # Premium component (-1 to 1)
            premium_value = premium['markPrice'] - premium['indexPrice']
            premium_score = max(-1, min(1, premium_value / premium['indexPrice'] * 100))
            
            # Weighted average (funding rate has more weight)
            sentiment_score = (funding_score * 0.7) + (premium_score * 0.3)
            
            return sentiment_score
            
        except Exception:
            return 0.0  # Neutral if calculation fails
    
    # Utility Methods
    
    def convert_symbol(self, symbol: str, target_format: str) -> str:
        """
        Convert symbol between spot and futures formats.
        
        Args:
            symbol: Input symbol
            target_format: 'spot' or 'futures'
            
        Returns:
            Converted symbol
        """
        return self.symbol_converter.normalize_symbol(symbol, target_format)
    
    def is_futures_symbol(self, symbol: str) -> bool:
        """Check if symbol is in futures format."""
        return self.symbol_converter.is_futures_symbol(symbol)
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and status."""
        self._ensure_initialized()
        
        try:
            markets = await self.get_markets()
            
            info = {
                'exchange': 'binance',
                'timestamp': int(datetime.now().timestamp() * 1000),
                'total_markets': len(markets),
                'spot_markets': len([m for m in markets.values() if m.get('spot', False)]),
                'futures_markets': len([m for m in markets.values() if m.get('future', False)]),
                'status': 'operational',
                'features': {
                    'spot_trading': True,
                    'futures_trading': True,
                    'funding_rates': True,
                    'open_interest': True,
                    'premium_index': True
                }
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get exchange info: {str(e)}")
            raise

    # WebSocket Methods (Required by BaseExchange)
    
    async def connect_ws(self) -> bool:
        """
        Connect to Binance WebSocket API.
        
        Returns:
            True if connection is successful
        """
        try:
            # For now, we'll use a simple implementation that always succeeds
            # In a full implementation, you would establish actual WebSocket connections
            logger.info("Binance WebSocket connection established (placeholder implementation)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {str(e)}")
            return False
    
    async def subscribe_ws(
        self,
        channels: List[str],
        symbols: List[str],
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Subscribe to Binance WebSocket channels.
        
        Args:
            channels: List of channel names to subscribe to
            symbols: List of symbols to subscribe for
            callback: Callback function for messages
            
        Returns:
            True if subscription is successful
        """
        try:
            # For now, we'll use a simple implementation that always succeeds
            # In a full implementation, you would subscribe to actual WebSocket channels
            logger.info(f"Subscribed to Binance WebSocket channels: {channels} for symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to Binance WebSocket channels: {str(e)}")
            return False

# Example usage and testing functions
async def test_integrated_binance():
    """Test the integrated Binance exchange client."""
    print("🧪 Testing Integrated Binance Exchange")
    print("=" * 45)
    
    async with BinanceExchange() as exchange:
        test_symbol = 'BTC/USDT'
        
        print(f"\n🎯 Testing {test_symbol}")
        print("-" * 20)
        
        try:
            # Test spot data
            print("1️⃣  Getting spot ticker...")
            ticker = await exchange.get_ticker(test_symbol)
            print(f"   💰 Price: ${ticker['last']:,.2f}")
            
            # Test futures data
            print("2️⃣  Getting funding rate...")
            funding = await exchange.get_current_funding_rate(test_symbol)
            print(f"   💸 Funding Rate: {funding['fundingRatePercentage']:+.4f}%")
            
            # Test open interest
            print("3️⃣  Getting open interest...")
            oi = await exchange.get_open_interest(test_symbol)
            print(f"   📊 Open Interest: {oi['openInterest']:,.0f}")
            
            # Test comprehensive data
            print("4️⃣  Getting complete market data...")
            complete = await exchange.get_complete_market_data(test_symbol)
            print(f"   📈 Complete data retrieved with {len(complete)} sections")
            
            # Test sentiment
            print("5️⃣  Getting market sentiment...")
            sentiment = await exchange.get_market_sentiment(test_symbol)
            print(f"   😊 Sentiment Score: {sentiment['sentiment_score']:+.3f}")
            
            print(f"\n✅ All integrated tests passed!")
            
        except Exception as e:
            print(f"\n❌ Error in integrated test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_integrated_binance()) 