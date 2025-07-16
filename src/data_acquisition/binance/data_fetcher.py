"""
Binance Data Fetcher - Coordinator for All Binance Data Operations

This module provides a comprehensive data fetching coordinator that integrates
with Virtuoso's MarketDataManager and provides automatic failover capabilities.

Features:
- Parallel data collection for multiple symbols
- Automatic failover between spot and futures data
- Integration with Market Prism Analysis Stack
- Rate limiting and error handling
- Performance monitoring and optimization
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .binance_exchange import BinanceExchange
from .futures_client import BinanceFuturesClient, BinanceSymbolConverter

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """Types of data sources available."""
    SPOT = "spot"
    FUTURES = "futures"
    COMBINED = "combined"

@dataclass
class DataFetchRequest:
    """Request for fetching market data."""
    symbol: str
    data_types: List[str]  # ['ticker', 'orderbook', 'trades', 'ohlcv', 'funding', 'open_interest']
    source_preference: DataSourceType = DataSourceType.COMBINED
    timeout: float = 30.0
    retry_count: int = 3

@dataclass
class DataFetchResult:
    """Result of data fetch operation."""
    symbol: str
    success: bool
    data: Dict[str, Any]
    source_used: DataSourceType
    fetch_time_ms: float
    error: Optional[str] = None

class BinanceDataFetcher:
    """
    Coordinator class for all Binance data operations.
    
    This class provides:
    - Unified interface for fetching all types of market data
    - Automatic failover between different data sources
    - Integration with Virtuoso's MarketDataManager
    - Parallel processing capabilities
    - Performance monitoring and optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data fetcher.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.binance_config = config.get('exchanges', {}).get('binance', {})
        
        # Initialize clients
        self.exchange = None
        self.futures_client = None
        self.symbol_converter = BinanceSymbolConverter()
        
        # Performance tracking
        self.fetch_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'last_reset': time.time()
        }
        
        # Failover configuration
        self.failover_config = {
            'max_retries': 3,
            'retry_delay': 1.0,
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60.0
        }
        
        # Circuit breaker state
        self.circuit_breaker = {
            'failures': 0,
            'last_failure': 0,
            'is_open': False
        }
        
        self.logger = logger
        self.logger.info("Binance Data Fetcher initialized")
    
    async def initialize(self) -> bool:
        """Initialize the data fetcher and all clients."""
        try:
            self.logger.info("Initializing Binance Data Fetcher...")
            
            # Initialize the main Binance exchange
            exchange_config = {
                'exchanges': {
                    'binance': self.binance_config
                }
            }
            
            self.exchange = BinanceExchange(exchange_config)
            await self.exchange.initialize()
            
            # Initialize futures client for advanced features
            api_credentials = self.binance_config.get('api_credentials', {})
            self.futures_client = BinanceFuturesClient(
                api_key=api_credentials.get('api_key'),
                api_secret=api_credentials.get('api_secret'),
                testnet=self.binance_config.get('testnet', False)
            )
            
            self.logger.info("Binance Data Fetcher initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance Data Fetcher: {str(e)}")
            return False
    
    async def fetch_market_data(self, symbol: str, data_types: List[str] = None) -> DataFetchResult:
        """
        Fetch comprehensive market data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            data_types: List of data types to fetch
            
        Returns:
            DataFetchResult with fetched data
        """
        start_time = time.time()
        
        if data_types is None:
            data_types = ['ticker', 'orderbook', 'trades', 'ohlcv']
        
        request = DataFetchRequest(
            symbol=symbol,
            data_types=data_types,
            source_preference=DataSourceType.COMBINED
        )
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                return DataFetchResult(
                    symbol=symbol,
                    success=False,
                    data={},
                    source_used=DataSourceType.SPOT,
                    fetch_time_ms=0,
                    error="Circuit breaker is open"
                )
            
            # Fetch data with failover
            result = await self._fetch_with_failover(request)
            
            # Update statistics
            fetch_time_ms = (time.time() - start_time) * 1000
            self._update_stats(result.success, fetch_time_ms)
            
            if result.success:
                self._reset_circuit_breaker()
            else:
                self._record_failure()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            self._record_failure()
            
            return DataFetchResult(
                symbol=symbol,
                success=False,
                data={},
                source_used=DataSourceType.SPOT,
                fetch_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def fetch_multiple_symbols(self, symbols: List[str], data_types: List[str] = None) -> List[DataFetchResult]:
        """
        Fetch market data for multiple symbols in parallel.
        
        Args:
            symbols: List of trading pair symbols
            data_types: List of data types to fetch
            
        Returns:
            List of DataFetchResult objects
        """
        self.logger.info(f"Fetching data for {len(symbols)} symbols in parallel")
        
        # Create tasks for parallel execution
        tasks = [
            self.fetch_market_data(symbol, data_types)
            for symbol in symbols
        ]
        
        # Execute in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=60.0  # 60 second timeout for all symbols
            )
            
            # Process results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        DataFetchResult(
                            symbol=symbols[i],
                            success=False,
                            data={},
                            source_used=DataSourceType.SPOT,
                            fetch_time_ms=0,
                            error=str(result)
                        )
                    )
                else:
                    processed_results.append(result)
            
            successful = sum(1 for r in processed_results if r.success)
            self.logger.info(f"Parallel fetch completed: {successful}/{len(symbols)} successful")
            
            return processed_results
            
        except asyncio.TimeoutError:
            self.logger.error("Timeout during parallel symbol fetch")
            return [
                DataFetchResult(
                    symbol=symbol,
                    success=False,
                    data={},
                    source_used=DataSourceType.SPOT,
                    fetch_time_ms=0,
                    error="Timeout"
                )
                for symbol in symbols
            ]
    
    async def _fetch_with_failover(self, request: DataFetchRequest) -> DataFetchResult:
        """Fetch data with automatic failover between sources."""
        symbol = request.symbol
        data_types = request.data_types
        
        # Try primary source first (exchange)
        try:
            if self.exchange and self.exchange.initialized:
                data = await self._fetch_from_exchange(symbol, data_types)
                if data:
                    return DataFetchResult(
                        symbol=symbol,
                        success=True,
                        data=data,
                        source_used=DataSourceType.COMBINED,
                        fetch_time_ms=0  # Will be updated by caller
                    )
        except Exception as e:
            self.logger.warning(f"Primary source failed for {symbol}: {str(e)}")
        
        # Fallback to futures client for advanced data
        try:
            if self.futures_client:
                data = await self._fetch_from_futures_client(symbol, data_types)
                if data:
                    return DataFetchResult(
                        symbol=symbol,
                        success=True,
                        data=data,
                        source_used=DataSourceType.FUTURES,
                        fetch_time_ms=0  # Will be updated by caller
                    )
        except Exception as e:
            self.logger.warning(f"Futures client failed for {symbol}: {str(e)}")
        
        # All sources failed
        return DataFetchResult(
            symbol=symbol,
            success=False,
            data={},
            source_used=DataSourceType.SPOT,
            fetch_time_ms=0,
            error="All data sources failed"
        )
    
    async def _fetch_from_exchange(self, symbol: str, data_types: List[str]) -> Dict[str, Any]:
        """Fetch data from the main Binance exchange."""
        data = {}
        
        # Convert symbol to appropriate format
        spot_symbol = self.symbol_converter.to_spot_format(symbol)
        futures_symbol = self.symbol_converter.to_futures_format(symbol)
        
        for data_type in data_types:
            try:
                if data_type == 'ticker':
                    data['ticker'] = await self.exchange.fetch_ticker(spot_symbol)
                elif data_type == 'orderbook':
                    data['orderbook'] = await self.exchange.fetch_order_book(spot_symbol, 20)
                elif data_type == 'trades':
                    data['trades'] = await self.exchange.fetch_trades(spot_symbol, limit=50)
                elif data_type == 'ohlcv':
                    data['ohlcv'] = await self.exchange.fetch_ohlcv(spot_symbol, '1h', limit=100)
                elif data_type == 'funding' and hasattr(self.exchange, 'fetch_funding_rate'):
                    data['funding_rate'] = await self.exchange.fetch_funding_rate(futures_symbol)
                elif data_type == 'open_interest' and hasattr(self.exchange, 'fetch_open_interest'):
                    data['open_interest'] = await self.exchange.fetch_open_interest(futures_symbol)
                    
            except Exception as e:
                self.logger.warning(f"Failed to fetch {data_type} for {symbol}: {str(e)}")
        
        return data
    
    async def _fetch_from_futures_client(self, symbol: str, data_types: List[str]) -> Dict[str, Any]:
        """Fetch data from the futures client."""
        data = {}
        futures_symbol = self.symbol_converter.to_futures_format(symbol)
        
        for data_type in data_types:
            try:
                if data_type == 'funding':
                    funding_data = await self.futures_client.get_funding_rate(futures_symbol)
                    data['funding_rate'] = funding_data
                elif data_type == 'open_interest':
                    oi_data = await self.futures_client.get_open_interest(futures_symbol)
                    data['open_interest'] = oi_data
                    
            except Exception as e:
                self.logger.warning(f"Failed to fetch {data_type} from futures client for {symbol}: {str(e)}")
        
        return data
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self.circuit_breaker['is_open']:
            return False
        
        # Check if timeout has passed
        time_since_failure = time.time() - self.circuit_breaker['last_failure']
        if time_since_failure > self.failover_config['circuit_breaker_timeout']:
            self.circuit_breaker['is_open'] = False
            self.circuit_breaker['failures'] = 0
            self.logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def _record_failure(self):
        """Record a failure for circuit breaker logic."""
        self.circuit_breaker['failures'] += 1
        self.circuit_breaker['last_failure'] = time.time()
        
        if self.circuit_breaker['failures'] >= self.failover_config['circuit_breaker_threshold']:
            self.circuit_breaker['is_open'] = True
            self.logger.warning("Circuit breaker opened due to repeated failures")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful operation."""
        if self.circuit_breaker['failures'] > 0:
            self.circuit_breaker['failures'] = 0
            self.logger.debug("Circuit breaker failures reset")
    
    def _update_stats(self, success: bool, fetch_time_ms: float):
        """Update performance statistics."""
        self.fetch_stats['total_requests'] += 1
        
        if success:
            self.fetch_stats['successful_requests'] += 1
        else:
            self.fetch_stats['failed_requests'] += 1
        
        # Update average response time
        current_avg = self.fetch_stats['avg_response_time']
        total_requests = self.fetch_stats['total_requests']
        self.fetch_stats['avg_response_time'] = (
            (current_avg * (total_requests - 1) + fetch_time_ms) / total_requests
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        stats = self.fetch_stats.copy()
        stats['success_rate'] = (
            stats['successful_requests'] / max(stats['total_requests'], 1)
        )
        stats['circuit_breaker_status'] = {
            'is_open': self.circuit_breaker['is_open'],
            'failures': self.circuit_breaker['failures']
        }
        return stats
    
    async def close(self):
        """Close all connections and cleanup resources."""
        try:
            if self.exchange:
                await self.exchange.close()
            
            if self.futures_client:
                await self.futures_client.close()
                
            self.logger.info("Binance Data Fetcher closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing Binance Data Fetcher: {str(e)}")

# Integration helpers for MarketDataManager

async def create_binance_data_fetcher(config: Dict[str, Any]) -> BinanceDataFetcher:
    """Create and initialize a Binance data fetcher."""
    fetcher = BinanceDataFetcher(config)
    await fetcher.initialize()
    return fetcher

def get_supported_data_types() -> List[str]:
    """Get list of supported data types."""
    return [
        'ticker',       # Spot price data
        'orderbook',    # Order book depth
        'trades',       # Recent trades
        'ohlcv',        # Candlestick data
        'funding',      # Futures funding rates
        'open_interest' # Futures open interest
    ] 