import logging
from typing import Dict, Any, Optional, List
import asyncio
import time
import pandas as pd
from src.core.error.decorators import handle_errors
from src.core.error.utils import ConfigurationError
from src.core.exchanges.manager import ExchangeManager
from src.core.exchanges.base import BaseExchange

logger = logging.getLogger(__name__)

class DataManager:
    """Manages market data collection and processing."""
    
    def __init__(self, exchange_manager: ExchangeManager, config: Dict[str, Any]):
        """Initialize the DataManager.
        
        Args:
            exchange_manager (ExchangeManager): Exchange manager instance
            config (Dict[str, Any]): Configuration dictionary
        """
        self.exchange_manager = exchange_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize data storage
        self._market_data = {}
        self._last_update = {}
        
        # Load timeframes from config
        self.timeframes = {}
        for tf_name, tf_config in config['timeframes'].items():
            self.timeframes[tf_name] = {
                'interval': str(tf_config['interval']),
                'required': int(tf_config['required']),
                'weight': float(tf_config.get('weight', 0.25)),  # Default equal weights
                'validation': tf_config.get('validation', {
                    'min_candles': 50,
                    'max_gap': 300
                })
            }
        
        # Validate and normalize timeframe weights
        total_weight = sum(tf['weight'] for tf in self.timeframes.values())
        if abs(total_weight - 1.0) > 0.001:
            self.logger.warning(f"Timeframe weights sum to {total_weight}, normalizing to 1.0")
            weight_factor = 1.0 / total_weight
            for tf in self.timeframes.values():
                tf['weight'] *= weight_factor
        
        # Get update intervals from config
        self.update_intervals = config.get('data_collection', {}).get('update_intervals', {
            'ticker': 1,
            'trades': 5,
            'orderbook': 1,
            'ohlcv': 60,
            'sentiment': 60
        })

    def _initialize_timeframes(self):
        """Initialize timeframes from configuration."""
        try:
            # Get timeframes from root config
            timeframes_config = self.config.get('timeframes', {})
            
            if not timeframes_config:
                raise ConfigurationError("No timeframes configuration found")
            
            # Initialize timeframe weights
            self.timeframe_weights = {}
            
            # Process each timeframe category
            for category, tf_config in timeframes_config.items():
                interval = str(tf_config.get('interval'))  # Convert to string for consistency
                weight = float(tf_config.get('weight', 0.0))
                required = int(tf_config.get('required', 1000))
                
                # Store timeframe info
                self.timeframe_weights[interval] = {
                    'weight': weight,
                    'required': required,
                    'category': category
                }
                
                # Validate timeframe interval is numeric
                if not interval.isdigit():
                    raise ConfigurationError(f"Invalid timeframe interval: {interval}. Must be numeric minutes.")
            
            # Normalize weights
            total_weight = sum(tf['weight'] for tf in self.timeframe_weights.values())
            if total_weight > 0:
                for tf in self.timeframe_weights:
                    self.timeframe_weights[tf]['weight'] /= total_weight
            
            self.logger.info(f"Initialized timeframes: {self.timeframe_weights}")
            
        except Exception as e:
            self.logger.error(f"Error initializing timeframes: {str(e)}")
            raise ConfigurationError(f"Failed to initialize timeframes: {str(e)}")

    async def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data for a symbol."""
        try:
            # Get exchange instance
            exchange = self.exchange_manager.get_exchange()
            if not exchange:
                raise ValueError("No exchange available")

            # Use centralized market data fetching
            market_data = await exchange.fetch_market_data(symbol)
            if not market_data:
                raise ValueError(f"Failed to fetch market data for {symbol}")

            # Extract OHLCV data for configured timeframes
            ohlcv_data = {}
            for tf_name, tf_config in self.timeframes.items():
                timeframe = tf_config['interval']
                if timeframe in market_data.get('ohlcv', {}):
                    ohlcv_data[tf_name] = market_data['ohlcv'][timeframe]

            # Structure the final data
            return {
                'symbol': symbol,
                'timestamp': market_data['timestamp'],
                'ticker': market_data['ticker'],
                'orderbook': market_data['orderbook'],
                'trades': market_data['trades'],
                'ohlcv': ohlcv_data,
                'metadata': market_data['metadata']
            }

        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            raise

    async def get_market_data(self, symbol: str, exchange: BaseExchange) -> Dict[str, Any]:
        """Get comprehensive market data"""
        try:
            market_data = {
                'symbol': symbol,
                'timestamp': int(time.time() * 1000),
                'timeframes': {},
                'orderbook': None,
                'sentiment': {}
            }
            
            # Fetch timeframe data using standard intervals
            for tf_name, tf_config in self.timeframes.items():
                interval = tf_config['interval']
                data = await exchange.fetch_timeframe_data(symbol, interval)
                if data is not None:
                    market_data['timeframes'][interval] = data
                else:
                    logger.error(f"Failed to fetch {interval} timeframe data for {symbol}")
                    return None
                    
            # Fetch orderbook
            orderbook = await exchange.fetch_order_book(symbol)
            if orderbook:
                market_data['orderbook'] = orderbook
                
            # Fetch sentiment data
            sentiment = await self.fetch_sentiment_data(exchange, symbol)
            if sentiment:
                market_data['sentiment'] = sentiment
                
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return None

    async def update_market_data(self, symbols: List[str]) -> None:
        """Update market data for multiple symbols.
        
        Args:
            symbols (List[str]): List of trading pair symbols
        """
        try:
            # Update data for each symbol
            tasks = [self.get_market_data(symbol, force_update=True) for symbol in symbols]
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.error(f"Error updating market data: {str(e)}")

    def get_cached_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached market data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            Optional[Dict[str, Any]]: Cached market data or None
        """
        return self._market_data.get(symbol)

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear cached market data.
        
        Args:
            symbol (Optional[str]): Symbol to clear cache for, or None for all
        """
        if symbol:
            self._market_data.pop(symbol, None)
            self._last_update.pop(symbol, None)
        else:
            self._market_data.clear()
            self._last_update.clear() 

    def update_ohlcv(self, symbol: str, ohlcv_data: Dict[str, Any]) -> None:
        """Update OHLCV data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            ohlcv_data (Dict[str, Any]): OHLCV data with timeframes and weights
        """
        try:
            if not ohlcv_data:
                self.logger.warning(f"No OHLCV data provided for {symbol}")
                return

            # Store raw OHLCV data
            if symbol in self._market_data:
                self._market_data[symbol]['ohlcv'] = ohlcv_data
                self._last_update[symbol]['ohlcv'] = time.time()
                self.logger.debug(f"Updated OHLCV data for {symbol}")
            else:
                self._market_data[symbol] = {'ohlcv': ohlcv_data}
                self._last_update[symbol] = {'ohlcv': time.time()}
                self.logger.debug(f"Created new OHLCV data entry for {symbol}")

            # Convert to DataFrames for each timeframe
            ohlcv_dfs = {}
            for timeframe, tf_data in ohlcv_data.items():
                try:
                    df = pd.DataFrame(
                        tf_data['data'],
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    ohlcv_dfs[timeframe] = {
                        'data': df,
                        'weight': tf_data['weight']
                    }
                    self.logger.debug(f"Converted OHLCV data to DataFrame for {symbol} on {timeframe} timeframe")
                except Exception as e:
                    self.logger.error(f"Error converting OHLCV data to DataFrame for {symbol} on {timeframe} timeframe: {str(e)}")
                    ohlcv_dfs[timeframe] = {
                        'data': pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']),
                        'weight': tf_data['weight']
                    }

            self._market_data[symbol]['ohlcv_df'] = ohlcv_dfs

        except Exception as e:
            self.logger.error(f"Error updating OHLCV data for {symbol}: {str(e)}")

    def get_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get OHLCV data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            Optional[pd.DataFrame]: OHLCV data as DataFrame or None
        """
        try:
            market_data = self._market_data.get(symbol, {})
            return market_data.get('ohlcv_df')
        except Exception as e:
            self.logger.error(f"Error getting OHLCV data for {symbol}: {str(e)}")
            return None

    def get_raw_ohlcv(self, symbol: str) -> Optional[List[List[float]]]:
        """Get raw OHLCV data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            Optional[List[List[float]]]: Raw OHLCV data or None
        """
        try:
            market_data = self._market_data.get(symbol, {})
            return market_data.get('ohlcv')
        except Exception as e:
            self.logger.error(f"Error getting raw OHLCV data for {symbol}: {str(e)}")
            return None

    def update_orderbook(self, symbol: str, orderbook: Dict[str, Any]) -> None:
        """Update orderbook data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            orderbook (Dict[str, Any]): Orderbook data
        """
        try:
            if not orderbook:
                self.logger.warning(f"No orderbook data provided for {symbol}")
                return

            # Update market data
            if symbol in self._market_data:
                self._market_data[symbol]['orderbook'] = orderbook
                self._last_update[symbol]['orderbook'] = time.time()
                self.logger.debug(f"Updated orderbook for {symbol}")
            else:
                self._market_data[symbol] = {'orderbook': orderbook}
                self._last_update[symbol] = {'orderbook': time.time()}
                self.logger.debug(f"Created new orderbook entry for {symbol}")

        except Exception as e:
            self.logger.error(f"Error updating orderbook for {symbol}: {str(e)}")

    def update_trades(self, symbol: str, trades: List[Dict[str, Any]]) -> None:
        """Update trades data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            trades (List[Dict[str, Any]]): List of trades
        """
        try:
            if not trades:
                self.logger.warning(f"No trades data provided for {symbol}")
                return

            # Update market data
            if symbol in self._market_data:
                self._market_data[symbol]['trades'] = trades
                self._last_update[symbol]['trades'] = time.time()
                self.logger.debug(f"Updated trades for {symbol}")
            else:
                self._market_data[symbol] = {'trades': trades}
                self._last_update[symbol] = {'trades': time.time()}
                self.logger.debug(f"Created new trades entry for {symbol}")

        except Exception as e:
            self.logger.error(f"Error updating trades for {symbol}: {str(e)}")

    def update_ticker(self, symbol: str, ticker: Dict[str, Any]) -> None:
        """Update ticker data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            ticker (Dict[str, Any]): Ticker data
        """
        try:
            if not ticker:
                self.logger.warning(f"No ticker data provided for {symbol}")
                return

            # Update market data
            if symbol in self._market_data:
                self._market_data[symbol]['ticker'] = ticker
                self._last_update[symbol]['ticker'] = time.time()
                self.logger.debug(f"Updated ticker for {symbol}")
            else:
                self._market_data[symbol] = {'ticker': ticker}
                self._last_update[symbol] = {'ticker': time.time()}
                self.logger.debug(f"Created new ticker entry for {symbol}")

        except Exception as e:
            self.logger.error(f"Error updating ticker for {symbol}: {str(e)}")

    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get orderbook data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            Optional[Dict[str, Any]]: Orderbook data or None
        """
        try:
            market_data = self._market_data.get(symbol, {})
            return market_data.get('orderbook')
        except Exception as e:
            self.logger.error(f"Error getting orderbook for {symbol}: {str(e)}")
            return None

    def get_trades(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """Get trades data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            Optional[List[Dict[str, Any]]]: List of trades or None
        """
        try:
            market_data = self._market_data.get(symbol, {})
            return market_data.get('trades')
        except Exception as e:
            self.logger.error(f"Error getting trades for {symbol}: {str(e)}")
            return None

    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            Optional[Dict[str, Any]]: Ticker data or None
        """
        try:
            market_data = self._market_data.get(symbol, {})
            return market_data.get('ticker')
        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            return None

    def validate_trade_data(self, trades: List[Dict[str, Any]]) -> bool:
        """Validate trade data structure"""
        try:
            if not isinstance(trades, list):
                self.logger.error("Trades must be a list")
                return False
            
            required_fields = ['id', 'price', 'size', 'side', 'time']
            for trade in trades:
                missing_fields = [f for f in required_fields if f not in trade]
                if missing_fields:
                    self.logger.error(f"Missing required trade fields: {missing_fields}")
                    return False
                
                # Type validation
                if not isinstance(trade['id'], str):
                    self.logger.error(f"Trade id must be string, got {type(trade['id'])}")
                    return False
                if not isinstance(trade['price'], (int, float)):
                    self.logger.error(f"Trade price must be numeric, got {type(trade['price'])}")
                    return False
                if not isinstance(trade['size'], (int, float)):
                    self.logger.error(f"Trade size must be numeric, got {type(trade['size'])}")
                    return False
                if not isinstance(trade['side'], str):
                    self.logger.error(f"Trade side must be string, got {type(trade['side'])}")
                    return False
                if not isinstance(trade['time'], int):
                    self.logger.error(f"Trade time must be integer, got {type(trade['time'])}")
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating trade data: {str(e)}")
            return False 