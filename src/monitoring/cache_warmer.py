#!/usr/bin/env python3
"""
Continuous cache warming service for dashboard data
Ensures cache is always populated with fresh data
"""

import asyncio
import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.dashboard.dashboard_integration import DashboardIntegrationService
from src.api.cache_adapter_direct import DirectCacheAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class CacheWarmer:
    def __init__(self):
        self.cache = DirectCacheAdapter()
        self.dashboard = None
        self.running = True
        
    async def initialize(self):
        """Initialize services"""
        logger.info("Initializing cache warmer...")
        
        # Initialize dashboard integration
        self.dashboard = DashboardIntegrationService()
        if hasattr(self.dashboard, 'initialize'):
            await self.dashboard.initialize()
        
        logger.info("Cache warmer initialized")
    
    async def warm_cache(self):
        """Warm the cache with dashboard data"""
        try:
            # Get dashboard data
            dashboard_data = await self.dashboard.get_dashboard_data()
            
            if dashboard_data:
                # Update market overview
                market_overview = dashboard_data.get('market_overview', {})
                if not market_overview:
                    # Calculate from top movers if empty
                    top_movers = dashboard_data.get('top_movers', {})
                    gainers = top_movers.get('gainers', [])
                    losers = top_movers.get('losers', [])
                    
                    market_overview = {
                        'gainers': len(gainers),
                        'losers': len(losers),
                        'total_symbols': 15,
                        'active_signals': len(dashboard_data.get('signals', [])),
                        'market_regime': 'BULLISH' if len(gainers) > len(losers) else 'BEARISH' if len(losers) > len(gainers) else 'NEUTRAL',
                        'timestamp': int(time.time() * 1000)
                    }
                    dashboard_data['market_overview'] = market_overview
                
                # Cache the data with appropriate TTLs
                await self.cache.set('market:overview', market_overview, ttl=30)
                await self.cache.set('analysis:signals', dashboard_data.get('signals', []), ttl=60)
                await self.cache.set('market:movers', dashboard_data.get('top_movers', {}), ttl=45)
                await self.cache.set('dashboard:data', dashboard_data, ttl=45)
                
                # Mobile data
                mobile_data = {
                    'market_overview': market_overview,
                    'signals': dashboard_data.get('signals', [])[:5],  # Top 5 for mobile
                    'alerts': dashboard_data.get('alerts', [])[:3]     # Top 3 alerts
                }
                await self.cache.set('dashboard:mobile-data', mobile_data, ttl=60)
                
                logger.info(f"Cache warmed: {market_overview.get('gainers', 0)} gainers, {market_overview.get('losers', 0)} losers, {len(dashboard_data.get('signals', []))} signals")
                return True
                
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return False
    
    async def run(self):
        """Run continuous cache warming"""
        await self.initialize()
        
        logger.info("Starting continuous cache warming...")
        consecutive_failures = 0
        
        while self.running:
            try:
                success = await self.warm_cache()
                
                if success:
                    consecutive_failures = 0
                    # Wait 15 seconds between updates
                    await asyncio.sleep(15)
                else:
                    consecutive_failures += 1
                    # Back off on failures
                    wait_time = min(60, 5 * consecutive_failures)
                    logger.warning(f"Cache warming failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
            except KeyboardInterrupt:
                logger.info("Stopping cache warmer...")
                self.running = False
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(10)

async def main():
    """Main entry point"""
    warmer = CacheWarmer()
    await warmer.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Cache warmer stopped")
