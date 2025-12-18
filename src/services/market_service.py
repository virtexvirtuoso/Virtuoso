"""
Phase 2A: Independent Market Data Service
Continuously fetches market data and stores in cache
Runs independently of other services - failures don't cascade
"""
import asyncio
import json
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timezone
import aiohttp
import aiomcache

from src.core.market_data_direct import DirectMarketData

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Independent market data fetcher that runs continuously
    Stores all data in Memcached for other services to consume
    """
    
    def __init__(self, cache_host: str = 'localhost', cache_port: int = 11211):
        """
        Initialize the market data service
        
        Args:
            cache_host: Memcached host
            cache_port: Memcached port
        """
        self.cache_host = cache_host
        self.cache_port = cache_port
        self.cache_client: Optional[aiomcache.Client] = None
        self.running = False
        self.update_interval = 5  # seconds
        self.error_count = 0
        self.last_update = None
        
    async def initialize(self):
        """Initialize cache connection"""
        try:
            self.cache_client = aiomcache.Client(self.cache_host, self.cache_port)
            # Test connection
            await self.cache_client.set(b'service:market:status', b'initializing', exptime=10)
            logger.info(f"✅ Market service connected to Memcached at {self.cache_host}:{self.cache_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Memcached: {e}")
            return False
    
    async def start(self):
        """
        Main service loop - runs independently
        Fetches market data every 5 seconds and stores in cache
        """
        if not await self.initialize():
            logger.error("Failed to initialize market service")
            return
            
        self.running = True
        logger.info("🚀 Market Data Service starting...")
        
        # Set service status
        await self._update_service_status('running')
        
        while self.running:
            try:
                # Fetch market data using Phase 1 DirectMarketData
                start_time = time.time()
                
                # Get different data sets
                tickers = await DirectMarketData.fetch_tickers(50)
                dashboard_data = await DirectMarketData.get_dashboard_data()
                
                fetch_time = (time.time() - start_time) * 1000  # ms
                
                if tickers:
                    # Store in cache with different keys for different consumers
                    await self._store_market_data(tickers, dashboard_data, fetch_time)
                    
                    # Update metrics
                    self.error_count = 0
                    self.last_update = datetime.now(timezone.utc)
                    
                    logger.debug(f"✅ Market data updated: {len(tickers)} symbols in {fetch_time:.0f}ms")
                else:
                    self.error_count += 1
                    logger.warning(f"⚠️ No data received from Bybit (attempt {self.error_count})")
                    
            except asyncio.CancelledError:
                logger.info("Market service cancelled")
                break
            except Exception as e:
                self.error_count += 1
                logger.error(f"❌ Market service error: {e} (error #{self.error_count})")
                
                # If too many errors, wait longer before retry
                if self.error_count > 5:
                    await asyncio.sleep(30)
                    
            # Regular update interval
            await asyncio.sleep(self.update_interval)
        
        await self._cleanup()
    
    async def _store_market_data(self, tickers: Dict, dashboard_data: Dict, fetch_time: float):
        """
        Store market data in cache with multiple keys for different consumers
        
        Keys:
        - market:tickers - Raw ticker data
        - market:dashboard - Dashboard formatted data
        - market:top_gainers - Top 10 gainers
        - market:top_losers - Top 10 losers
        - market:overview - Market overview stats
        - market:updated - Last update timestamp
        - market:health - Service health metrics
        """
        try:
            # Serialize data
            tickers_json = json.dumps(tickers).encode()
            dashboard_json = json.dumps(dashboard_data).encode()
            
            # Store with appropriate TTLs (expire after 30 seconds if not updated)
            await self.cache_client.set(b'market:tickers', tickers_json, exptime=30)
            await self.cache_client.set(b'market:dashboard', dashboard_json, exptime=30)
            
            # Store specific data for quick access
            if dashboard_data.get('status') == 'success':
                if dashboard_data.get('top_gainers'):
                    await self.cache_client.set(
                        b'market:top_gainers', 
                        json.dumps(dashboard_data['top_gainers'][:10]).encode(),
                        exptime=30
                    )
                    
                if dashboard_data.get('top_losers'):
                    await self.cache_client.set(
                        b'market:top_losers',
                        json.dumps(dashboard_data['top_losers'][:10]).encode(),
                        exptime=30
                    )
                    
                if dashboard_data.get('overview'):
                    await self.cache_client.set(
                        b'market:overview',
                        json.dumps(dashboard_data['overview']).encode(),
                        exptime=30
                    )
            
            # Update metadata
            health_data = {
                'status': 'healthy',
                'last_update': time.time(),
                'fetch_time_ms': fetch_time,
                'symbol_count': len(tickers),
                'error_count': self.error_count,
                'update_interval': self.update_interval
            }
            
            await self.cache_client.set(
                b'market:health',
                json.dumps(health_data).encode(),
                exptime=30
            )
            
            await self.cache_client.set(
                b'market:updated',
                str(int(time.time())).encode(),
                exptime=30
            )
            
        except Exception as e:
            logger.error(f"Failed to store market data in cache: {e}")
    
    async def _update_service_status(self, status: str):
        """Update service status in cache"""
        try:
            status_data = {
                'service': 'market_data',
                'status': status,
                'timestamp': time.time(),
                'error_count': self.error_count,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            await self.cache_client.set(
                b'service:market:status',
                json.dumps(status_data).encode(),
                exptime=60
            )
        except Exception as e:
            logger.error(f"Failed to update service status: {e}")
    
    async def stop(self):
        """Gracefully stop the service"""
        logger.info("Stopping Market Data Service...")
        self.running = False
        await self._update_service_status('stopping')
    
    async def _cleanup(self):
        """Clean up resources"""
        try:
            await self._update_service_status('stopped')
            if self.cache_client:
                await self.cache_client.close()
            logger.info("✅ Market Data Service stopped cleanly")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> Dict:
        """Get current service status"""
        return {
            'running': self.running,
            'error_count': self.error_count,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'cache_connected': self.cache_client is not None
        }


async def run_market_service():
    """
    Standalone runner for the market service
    Can be run as a separate process/systemd service
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = MarketDataService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await service.stop()
    except Exception as e:
        logger.error(f"Service crashed: {e}")
        await service.stop()


if __name__ == "__main__":
    # Run as standalone service
    asyncio.run(run_market_service())