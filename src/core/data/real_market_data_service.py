"""
Real Market Data Service

Provides authenticated access to real market data from exchanges.
Replaces synthetic data generation with actual market data fetching.
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import time

from ..resilience import (
    handle_errors, RetryConfig, ErrorContext,
    circuit_breaker, EXCHANGE_API_CONFIG
)

logger = logging.getLogger(__name__)


class RealMarketDataService:
    """
    Service for fetching real market data from exchanges.
    
    Designed to replace synthetic data generation with authenticated
    access to real market data through the exchange manager.
    """
    
    def __init__(self, exchange_manager=None):
        """
        Initialize real market data service.
        
        Args:
            exchange_manager: Exchange manager instance (optional, will get from app if None)
        """
        self.exchange_manager = exchange_manager
        self.logger = logger
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache for price data
        
        # Default symbols for each exchange
        self.default_symbols = {
            'bybit': [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
                "ADAUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT"
            ],
            'binance': [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT",
                "ADAUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT"
            ]
        }
    
    def _get_exchange_manager(self):
        """Get exchange manager from app context if not provided"""
        if self.exchange_manager:
            return self.exchange_manager
        
        try:
            # Try to get from FastAPI app context
            from fastapi import Request
            from src.main import app
            if hasattr(app.state, 'exchange_manager'):
                return app.state.exchange_manager
        except Exception:
            pass
        
        try:
            # Try to get from global state
            from src.core.exchanges.manager import get_exchange_manager
            return get_exchange_manager()
        except Exception:
            pass
        
        raise ValueError("Exchange manager not available - cannot fetch real market data")
    
    def _generate_cache_key(self, symbol: str, timeframe: str, days: int, exchange: str = None) -> str:
        """Generate cache key for market data"""
        return f"market_data:{exchange or 'default'}:{symbol}:{timeframe}:{days}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        timestamp = cache_entry.get('timestamp', 0)
        return (time.time() - timestamp) < self.cache_ttl
    
    @handle_errors(
        operation='fetch_historical_ohlcv',
        component='real_market_data',
        circuit_breaker_name='exchange_api',
        retry_config=RetryConfig(max_attempts=3, base_delay=2.0)
    )
    async def fetch_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1d',
        days: int = 30,
        exchange_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch real historical OHLCV data from exchange.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for data ('1m', '5m', '1h', '1d', etc.)
            days: Number of days of historical data
            exchange_name: Exchange to use (None for default)
        
        Returns:
            DataFrame with OHLCV data including returns column
        
        Raises:
            ValueError: If no real data available
            Exception: For other errors
        """
        # Check cache first
        cache_key = self._generate_cache_key(symbol, timeframe, days, exchange_name)
        cached_data = self.cache.get(cache_key)
        
        if cached_data and self._is_cache_valid(cached_data):
            self.logger.info(f"Returning cached data for {symbol} {timeframe} {days}d")
            return cached_data['data']
        
        # Get exchange manager
        exchange_manager = self._get_exchange_manager()
        
        if not exchange_manager or not exchange_manager.initialized:
            raise ValueError("Exchange manager not initialized - cannot fetch real market data")
        
        # Calculate the since timestamp
        since = datetime.utcnow() - timedelta(days=days)
        since_timestamp = int(since.timestamp() * 1000)
        
        # Try to get data from exchanges
        for exchange_name_attempt in self._get_exchange_priority(exchange_name):
            try:
                exchange = exchange_manager.exchanges.get(exchange_name_attempt)
                if not exchange:
                    continue
                
                self.logger.info(f"Fetching {symbol} {timeframe} data from {exchange_name_attempt}")
                
                # Fetch OHLCV data
                ohlcv_data = await exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since_timestamp,
                    limit=min(days * 24 if timeframe.endswith('h') else days, 1000)
                )
                
                if not ohlcv_data:
                    self.logger.warning(f"No OHLCV data returned from {exchange_name_attempt} for {symbol}")
                    continue
                
                # Convert to DataFrame
                df = self._convert_ohlcv_to_dataframe(ohlcv_data)
                
                if df.empty:
                    self.logger.warning(f"Empty DataFrame from {exchange_name_attempt} for {symbol}")
                    continue
                
                # Cache the result
                self.cache[cache_key] = {
                    'data': df,
                    'timestamp': time.time(),
                    'source': exchange_name_attempt
                }
                
                self.logger.info(f"✅ Successfully fetched {len(df)} records for {symbol} from {exchange_name_attempt}")
                return df
                
            except Exception as e:
                self.logger.error(f"Failed to fetch data from {exchange_name_attempt} for {symbol}: {e}")
                continue
        
        # If we get here, all exchanges failed
        raise ValueError(f"Failed to fetch real market data for {symbol} from any exchange - synthetic data fallback disabled for safety")
    
    def _get_exchange_priority(self, preferred_exchange: Optional[str] = None) -> List[str]:
        """Get list of exchanges in priority order"""
        exchange_manager = self._get_exchange_manager()
        available_exchanges = list(exchange_manager.exchanges.keys()) if exchange_manager else []
        
        if not available_exchanges:
            return ['bybit', 'binance']  # Fallback to common exchanges
        
        if preferred_exchange and preferred_exchange in available_exchanges:
            # Put preferred exchange first
            priority_list = [preferred_exchange]
            priority_list.extend([ex for ex in available_exchanges if ex != preferred_exchange])
            return priority_list
        
        return available_exchanges
    
    def _convert_ohlcv_to_dataframe(self, ohlcv_data: List[List[Any]]) -> pd.DataFrame:
        """
        Convert OHLCV data to pandas DataFrame.
        
        Args:
            ohlcv_data: List of OHLCV records [timestamp, open, high, low, close, volume]
        
        Returns:
            DataFrame with timestamp index and OHLCV columns plus returns
        """
        if not ohlcv_data:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Drop any NaN rows
        df.dropna(inplace=True)
        
        # Sort by timestamp
        df.sort_index(inplace=True)
        
        return df
    
    @handle_errors(
        operation='fetch_current_ticker',
        component='real_market_data',
        circuit_breaker_name='exchange_api',
        retry_config=RetryConfig(max_attempts=2, base_delay=1.0)
    )
    async def fetch_current_ticker(self, symbol: str, exchange_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch current ticker data for symbol.
        
        Args:
            symbol: Trading symbol
            exchange_name: Exchange to use (None for default)
        
        Returns:
            Dictionary with current price and 24h change data
        """
        exchange_manager = self._get_exchange_manager()
        
        if not exchange_manager or not exchange_manager.initialized:
            raise ValueError("Exchange manager not initialized")
        
        for exchange_name_attempt in self._get_exchange_priority(exchange_name):
            try:
                exchange = exchange_manager.exchanges.get(exchange_name_attempt)
                if not exchange:
                    continue
                
                ticker = await exchange.fetch_ticker(symbol)
                
                if ticker and 'last' in ticker:
                    return {
                        'symbol': symbol,
                        'price': float(ticker['last']) if ticker['last'] else 0.0,
                        'change_24h': float(ticker.get('percentage', 0.0)) if ticker.get('percentage') else 0.0,
                        'volume': float(ticker.get('baseVolume', 0.0)) if ticker.get('baseVolume') else 0.0,
                        'timestamp': ticker.get('timestamp', int(time.time() * 1000)),
                        'source': exchange_name_attempt
                    }
                
            except Exception as e:
                self.logger.error(f"Failed to fetch ticker from {exchange_name_attempt} for {symbol}: {e}")
                continue
        
        raise ValueError(f"Failed to fetch ticker data for {symbol} from any exchange")
    
    async def fetch_multiple_tickers(
        self,
        symbols: List[str],
        exchange_name: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch ticker data for multiple symbols efficiently.
        
        Args:
            symbols: List of trading symbols
            exchange_name: Exchange to use (None for default)
        
        Returns:
            Dictionary mapping symbol to ticker data
        """
        results = {}
        
        # Use asyncio.gather for concurrent fetching
        async def fetch_single_ticker(symbol):
            try:
                ticker_data = await self.fetch_current_ticker(symbol, exchange_name)
                return symbol, ticker_data
            except Exception as e:
                self.logger.warning(f"Failed to fetch ticker for {symbol}: {e}")
                return symbol, None
        
        # Fetch all tickers concurrently
        ticker_tasks = [fetch_single_ticker(symbol) for symbol in symbols]
        ticker_results = await asyncio.gather(*ticker_tasks, return_exceptions=True)
        
        # Process results
        for result in ticker_results:
            if isinstance(result, tuple) and len(result) == 2:
                symbol, ticker_data = result
                if ticker_data:
                    results[symbol] = ticker_data
        
        return results
    
    async def validate_symbol(self, symbol: str, exchange_name: Optional[str] = None) -> bool:
        """
        Validate if symbol is available on exchange.
        
        Args:
            symbol: Trading symbol to validate
            exchange_name: Exchange to check (None for any)
        
        Returns:
            True if symbol is valid and available
        """
        try:
            ticker_data = await self.fetch_current_ticker(symbol, exchange_name)
            return ticker_data is not None and ticker_data.get('price', 0) > 0
        except Exception:
            return False
    
    def get_default_symbols(self, exchange_name: Optional[str] = None) -> List[str]:
        """
        Get default symbols for analysis.
        
        Args:
            exchange_name: Exchange name (None for generic)
        
        Returns:
            List of default trading symbols
        """
        if exchange_name in self.default_symbols:
            return self.default_symbols[exchange_name]
        
        # Return most common symbols if exchange not specified
        return [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT"
        ]
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status and health information.
        
        Returns:
            Dictionary with service status and statistics
        """
        try:
            exchange_manager = self._get_exchange_manager()
            
            status = {
                'service': 'real_market_data',
                'status': 'healthy',
                'timestamp': time.time(),
                'cache_size': len(self.cache),
                'exchange_manager_available': exchange_manager is not None,
                'exchange_manager_initialized': (
                    exchange_manager.initialized if exchange_manager else False
                ),
                'available_exchanges': (
                    list(exchange_manager.exchanges.keys()) if exchange_manager else []
                )
            }
            
            # Test connectivity with a simple ticker fetch
            if exchange_manager and exchange_manager.initialized:
                try:
                    test_symbol = "BTCUSDT"
                    ticker_data = await asyncio.wait_for(
                        self.fetch_current_ticker(test_symbol),
                        timeout=10.0
                    )
                    status['connectivity_test'] = {
                        'status': 'success',
                        'test_symbol': test_symbol,
                        'price': ticker_data.get('price')
                    }
                except Exception as e:
                    status['connectivity_test'] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    status['status'] = 'degraded'
            else:
                status['status'] = 'unavailable'
                status['connectivity_test'] = {
                    'status': 'skipped',
                    'reason': 'exchange_manager_not_available'
                }
            
            return status
            
        except Exception as e:
            return {
                'service': 'real_market_data',
                'status': 'error',
                'timestamp': time.time(),
                'error': str(e)
            }


# Global service instance
_real_market_data_service: Optional[RealMarketDataService] = None


def get_real_market_data_service(exchange_manager=None) -> RealMarketDataService:
    """Get or create the real market data service singleton."""
    global _real_market_data_service
    if _real_market_data_service is None:
        _real_market_data_service = RealMarketDataService(exchange_manager)
        logger.info("✅ Real market data service initialized")
    return _real_market_data_service