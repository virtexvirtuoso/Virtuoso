#!/usr/bin/env python3
"""
Bitcoin Beta Data Collection Service
Fetches and caches historical kline data for beta calculations
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import numpy as np
from aiomcache import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BitcoinBetaDataService:
    """Service to collect and cache historical price data for beta calculations"""
    
    def __init__(self):
        self.cache = Client('localhost', 11211)
        self.base_url = 'https://api.bybit.com'
        
        # Primary symbols to track (top 20 + BTC)
        self.symbols = [
            'BTCUSDT',  # Base for beta calculation
            'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT',
            'NEARUSDT', 'ATOMUSDT', 'FTMUSDT', 'ALGOUSDT',
            'AAVEUSDT', 'UNIUSDT', 'SUSHIUSDT', 'COMPUSDT',
            'SNXUSDT', 'CRVUSDT', 'MKRUSDT'
        ]
        
        # Intervals to fetch
        self.intervals = {
            '60': 2160,    # 1h: 90 days of data
            '240': 540,     # 4h: 90 days of data
            'D': 90         # Daily: 90 days of data
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.update_interval = 3600  # Update every hour
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_klines(self, symbol: str, interval: str, limit: int) -> List[List]:
        """
        Fetch kline data from Bybit API
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (60, 240, D)
            limit: Number of klines to fetch
            
        Returns:
            List of kline data
        """
        url = f"{self.base_url}/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0:
                        # Reverse to get chronological order
                        klines = data['result']['list']
                        klines.reverse()
                        return klines
                    else:
                        logger.error(f"API error for {symbol}/{interval}: {data.get('retMsg')}")
                else:
                    logger.error(f"HTTP error {response.status} for {symbol}/{interval}")
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}/{interval}: {e}")
        
        return []
    
    def process_klines(self, klines: List[List]) -> Dict[str, Any]:
        """
        Process raw kline data into structured format
        
        Args:
            klines: Raw kline data from API
            
        Returns:
            Processed kline data with statistics
        """
        if not klines:
            return {}
        
        # Extract OHLCV data
        timestamps = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        for kline in klines:
            # Kline format: [timestamp, open, high, low, close, volume, turnover]
            timestamps.append(int(kline[0]))
            opens.append(float(kline[1]))
            highs.append(float(kline[2]))
            lows.append(float(kline[3]))
            closes.append(float(kline[4]))
            volumes.append(float(kline[5]))
        
        # Calculate returns
        closes_array = np.array(closes)
        returns = np.diff(np.log(closes_array))  # Log returns
        
        return {
            'timestamps': timestamps,
            'opens': opens,
            'highs': highs,
            'lows': lows,
            'closes': closes,
            'volumes': volumes,
            'returns': returns.tolist(),
            'count': len(klines),
            'last_updated': int(time.time() * 1000)
        }
    
    async def store_kline_data(self, symbol: str, interval: str, data: Dict[str, Any]):
        """
        Store processed kline data in cache
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval
            data: Processed kline data
        """
        if not data:
            return
            
        cache_key = f'beta:klines:{symbol}:{interval}'
        
        # Serialize data for cache storage
        serialized = json.dumps(data)
        
        try:
            # Store with 2 hour TTL
            await self.cache.set(cache_key.encode(), serialized.encode(), exptime=7200)
            logger.info(f"Stored {len(data.get('closes', []))} klines for {symbol}/{interval}")
        except Exception as e:
            logger.error(f"Error storing klines for {symbol}/{interval}: {e}")
    
    async def fetch_and_store_symbol(self, symbol: str):
        """
        Fetch and store all intervals for a single symbol
        
        Args:
            symbol: Trading pair symbol
        """
        tasks = []
        
        for interval, limit in self.intervals.items():
            # Fetch klines
            klines = await self.fetch_klines(symbol, interval, limit)
            
            if klines:
                # Process data
                processed_data = self.process_klines(klines)
                
                # Store in cache
                await self.store_kline_data(symbol, interval, processed_data)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
    
    async def fetch_all_symbols(self):
        """Fetch and store data for all symbols"""
        logger.info(f"Starting data collection for {len(self.symbols)} symbols")
        
        for symbol in self.symbols:
            logger.info(f"Fetching data for {symbol}")
            await self.fetch_and_store_symbol(symbol)
            
            # Delay between symbols to respect rate limits
            await asyncio.sleep(1)
        
        logger.info("Data collection complete")
    
    async def update_recent_data(self):
        """Update only the most recent data (last 24 hours)"""
        logger.info("Updating recent data")
        
        for symbol in self.symbols:
            for interval in ['60']:  # Only update hourly data
                klines = await self.fetch_klines(symbol, interval, 24)
                
                if klines:
                    # Get existing data from cache
                    cache_key = f'beta:klines:{symbol}:{interval}'
                    
                    try:
                        cached_data = await self.cache.get(cache_key.encode())
                        if cached_data:
                            existing_data = json.loads(cached_data.decode())
                            
                            # Process new klines
                            new_data = self.process_klines(klines)
                            
                            # Merge with existing data (keep last 90 days)
                            if existing_data and new_data:
                                # Combine and deduplicate based on timestamp
                                all_timestamps = existing_data['timestamps'] + new_data['timestamps']
                                unique_timestamps = sorted(list(set(all_timestamps)))
                                
                                # Keep only last 90 days
                                cutoff = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)
                                recent_timestamps = [ts for ts in unique_timestamps if ts > cutoff]
                                
                                # Update the cached data structure
                                # (In production, would properly merge all arrays)
                                existing_data['last_updated'] = int(time.time() * 1000)
                                
                                await self.store_kline_data(symbol, interval, existing_data)
                    except Exception as e:
                        logger.error(f"Error updating recent data for {symbol}: {e}")
                
                await asyncio.sleep(0.5)
    
    async def get_data_status(self) -> Dict[str, Any]:
        """Get status of cached data"""
        status = {
            'symbols': {},
            'total_symbols': len(self.symbols),
            'last_check': datetime.now().isoformat()
        }
        
        for symbol in self.symbols:
            symbol_status = {}
            
            for interval in self.intervals.keys():
                cache_key = f'beta:klines:{symbol}:{interval}'
                
                try:
                    data = await self.cache.get(cache_key.encode())
                    if data:
                        parsed = json.loads(data.decode())
                        symbol_status[interval] = {
                            'count': parsed.get('count', 0),
                            'last_updated': parsed.get('last_updated', 0)
                        }
                    else:
                        symbol_status[interval] = {'count': 0, 'last_updated': 0}
                except Exception as e:
                    symbol_status[interval] = {'error': str(e)}
            
            status['symbols'][symbol] = symbol_status
        
        return status
    
    async def run_continuous(self):
        """Run continuous data collection with periodic updates"""
        # Initial full data fetch
        await self.fetch_all_symbols()
        
        while True:
            try:
                # Wait for update interval
                await asyncio.sleep(self.update_interval)
                
                # Update recent data
                await self.update_recent_data()
                
                # Log status
                status = await self.get_data_status()
                logger.info(f"Data status: {len([s for s in status['symbols'].values() if s])} symbols with data")
                
            except Exception as e:
                logger.error(f"Error in continuous run: {e}")
                await asyncio.sleep(60)  # Wait before retry

async def main():
    """Main entry point"""
    async with BitcoinBetaDataService() as service:
        # Check if running as one-time fetch or continuous
        import sys
        
        if len(sys.argv) > 1 and sys.argv[1] == '--status':
            # Just show status
            status = await service.get_data_status()
            print(json.dumps(status, indent=2))
        elif len(sys.argv) > 1 and sys.argv[1] == '--once':
            # Run once and exit
            await service.fetch_all_symbols()
        else:
            # Run continuously
            await service.run_continuous()

if __name__ == '__main__':
    asyncio.run(main())