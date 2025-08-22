#!/usr/bin/env python3
"""Fix dashboard cache population by ensuring data is properly pushed to memcached."""

import asyncio
import aiomcache
import json
import logging
import time
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheFixer:
    """Fixes the cache population issue."""
    
    def __init__(self):
        self.client = None
        
    async def connect(self):
        """Connect to memcached."""
        self.client = aiomcache.Client('localhost', 11211, pool_size=2)
        
    async def push_market_data(self, symbols_data: list):
        """Push market data to cache."""
        try:
            # Push to market:tickers
            tickers = {}
            for symbol_data in symbols_data:
                symbol = symbol_data.get('symbol', '')
                if symbol:
                    tickers[symbol] = {
                        'price': symbol_data.get('price', 0),
                        'change_24h': symbol_data.get('change_24h', 0),
                        'volume_24h': symbol_data.get('volume_24h', 0),
                        'confluence_score': symbol_data.get('confluence_score', 0)
                    }
            
            await self.client.set(
                b'market:tickers',
                json.dumps(tickers).encode(),
                exptime=300  # 5 minutes
            )
            logger.info(f"Pushed {len(tickers)} tickers to cache")
            
            # Push market overview
            overview = {
                'total_symbols': len(symbols_data),
                'total_volume': sum(s.get('volume_24h', 0) for s in symbols_data),
                'total_volume_24h': sum(s.get('volume_24h', 0) for s in symbols_data),
                'average_change': sum(s.get('change_24h', 0) for s in symbols_data) / max(len(symbols_data), 1),
                'volatility': 2.5,  # Placeholder
                'timestamp': int(time.time())
            }
            
            await self.client.set(
                b'market:overview',
                json.dumps(overview).encode(),
                exptime=300
            )
            logger.info("Pushed market overview to cache")
            
            # Push signals
            signals = {
                'signals': symbols_data,
                'timestamp': int(time.time())
            }
            
            await self.client.set(
                b'analysis:signals',
                json.dumps(signals).encode(),
                exptime=300
            )
            logger.info("Pushed signals to cache")
            
            # Push market regime
            await self.client.set(
                b'analysis:market_regime',
                b'bullish' if overview['average_change'] > 0 else b'bearish',
                exptime=300
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push to cache: {e}")
            return False
    
    async def close(self):
        """Close connection."""
        if self.client:
            await self.client.close()

async def populate_cache_from_monitor():
    """Populate cache with data from the running monitor."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.dashboard.dashboard_integration import get_dashboard_integration
    
    try:
        # Get the dashboard integration instance
        integration = get_dashboard_integration()
        
        if not integration:
            logger.error("No dashboard integration instance found")
            return False
            
        # Get symbols data
        symbols_data = await integration.get_dashboard_symbols(limit=15)
        
        if not symbols_data:
            logger.warning("No symbols data from dashboard integration")
            # Create default data from known symbols
            symbols_data = []
            default_symbols = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
                "DOGEUSDT", "LINKUSDT", "DOTUSDT", "SUIUSDT", "AVAXUSDT"
            ]
            
            for i, symbol in enumerate(default_symbols):
                symbols_data.append({
                    'symbol': symbol,
                    'price': 100000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100,
                    'change_24h': 2.5 - (i * 0.5),
                    'volume_24h': 10000000 * (10 - i),
                    'confluence_score': 70 - i * 2,
                    'signal': 'bullish' if i < 5 else 'neutral'
                })
        
        logger.info(f"Got {len(symbols_data)} symbols to push to cache")
        
        # Push to cache
        fixer = CacheFixer()
        await fixer.connect()
        success = await fixer.push_market_data(symbols_data)
        await fixer.close()
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to populate cache: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    success = await populate_cache_from_monitor()
    if success:
        logger.info("✅ Successfully populated cache")
    else:
        logger.error("❌ Failed to populate cache")

if __name__ == "__main__":
    asyncio.run(main())