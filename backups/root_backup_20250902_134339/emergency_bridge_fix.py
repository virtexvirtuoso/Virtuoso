#!/usr/bin/env python3
"""
Emergency Bridge Fix - Force start cache bridge directly
"""
import asyncio
import sys
import logging

# Add path for imports
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt/src')

from core.cache_data_bridge import CacheDataBridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def emergency_start_bridge():
    """Emergency bridge startup"""
    try:
        logger.info("🚨 Emergency: Starting cache bridge directly...")
        
        # Initialize bridge with empty components (will use fallback)
        cache_bridge = CacheDataBridge()
        
        # Start bridge cycle manually
        await cache_bridge._bridge_signals_data()
        
        logger.info("✅ Emergency bridge cycle completed!")
        
    except Exception as e:
        logger.error(f"❌ Emergency bridge failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(emergency_start_bridge())