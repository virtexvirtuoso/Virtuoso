import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class BybitDataFetcher:
    """Fetches and prepares market data from Bybit for analysis"""
    
    def __init__(self, exchange):
        """Initialize the data fetcher.
        
        Args:
            exchange: Initialized Bybit exchange instance
        """
        self.exchange = exchange
        self.timeframes = {
            'base': '1m',
            'ltf': '5m',
            'mtf': '30m',
            'htf': '4h'
        }
    
    async def fetch_complete_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch complete market data required for confluence analysis.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market data dictionary
        """
        try:
            start_time = time.time()
            logger.info(f"Fetching market data for {symbol}")
            
            # Prepare result container
            market_data = {
                'symbol': symbol,
                'exchange': 'bybit',
                'timestamp': int(time.time() * 1000),
                'ohlcv': {},
                'orderbook': {},
                'trades': []
            }
            
            # Fetch data concurrently
            tasks = [
                self._fetch_ohlcv(symbol),
                self._fetch_orderbook(symbol),
                self._fetch_trades(symbol),
                self._fetch_ticker(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching data: {str(result)}")
                elif isinstance(result, dict):
                    # Update market data with fetched data
                    for key, value in result.items():
                        market_data[key] = value
            
            elapsed = time.time() - start_time
            logger.info(f"Fetched market data for {symbol} in {elapsed:.2f}s")
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol}: {str(e)}")
            # Return minimal structure to avoid errors
            return {
                'symbol': symbol,
                'exchange': 'bybit',
                'timestamp': int(time.time() * 1000)
            }
    
    async def _fetch_ohlcv(self, symbol: str) -> Dict[str, Any]:
        """Fetch OHLCV data for all required timeframes.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            OHLCV data
        """
        try:
            result = {'ohlcv': {}}
            
            # Fetch each timeframe
            for tf_name, tf_value in self.timeframes.items():
                candles = await self.exchange.fetch_ohlcv(symbol, timeframe=tf_value, limit=100)
                if candles:
                    # Convert to DataFrame
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Store in result
                    result['ohlcv'][tf_name] = df
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {str(e)}")
            return {'ohlcv': {}}
    
    async def _fetch_orderbook(self, symbol: str) -> Dict[str, Any]:
        """Fetch orderbook data.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Orderbook data
        """
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit=50)
            
            # Calculate timestamp if not provided
            if 'timestamp' not in orderbook or not orderbook['timestamp']:
                orderbook['timestamp'] = int(time.time() * 1000)
                
            return {'orderbook': orderbook}
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {str(e)}")
            return {'orderbook': {'bids': [], 'asks': [], 'timestamp': int(time.time() * 1000)}}
    
    async def _fetch_trades(self, symbol: str) -> Dict[str, Any]:
        """Fetch recent trades.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Recent trades
        """
        try:
            trades = await self.exchange.fetch_trades(symbol, limit=100)
            return {'trades': trades}
            
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {str(e)}")
            return {'trades': []}
    
    async def _fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {'ticker': ticker}
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            return {'ticker': {}} 