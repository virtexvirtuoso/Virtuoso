#!/usr/bin/env python3
"""Test script to check dashboard integration status."""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8003"

async def test_dashboard_integration():
    """Test dashboard integration and data flow."""
    logger.info("Testing dashboard integration...")
    
    async with aiohttp.ClientSession() as session:
        # Test debug-components endpoint
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/debug-components") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Dashboard Integration Status:")
                    logger.info(f"  - Has integration: {data.get('has_integration', False)}")
                    logger.info(f"  - Has dashboard data: {data.get('has_dashboard_data', False)}")
                    logger.info(f"  - Signal count: {data.get('signal_count', 0)}")
                    logger.info(f"  - Available components: {data.get('available_components', [])}")
        except Exception as e:
            logger.error(f"Error testing debug-components: {e}")
        
        # Test signals endpoint
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/signals") as response:
                if response.status == 200:
                    signals = await response.json()
                    logger.info(f"\nSignals endpoint:")
                    logger.info(f"  - Number of signals: {len(signals)}")
                    if signals:
                        logger.info("  - Sample signal:")
                        logger.info(f"    {json.dumps(signals[0], indent=4)}")
        except Exception as e:
            logger.error(f"Error testing signals: {e}")
        
        # Test market overview
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/market-overview") as response:
                if response.status == 200:
                    market = await response.json()
                    logger.info(f"\nMarket Overview:")
                    logger.info(f"  - Active symbols: {market.get('active_symbols', 0)}")
                    logger.info(f"  - Market regime: {market.get('market_regime', 'unknown')}")
        except Exception as e:
            logger.error(f"Error testing market overview: {e}")
        
        # Test top symbols
        try:
            async with session.get(f"{BASE_URL}/api/top-symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    symbols = data.get('symbols', [])
                    logger.info(f"\nTop Symbols:")
                    logger.info(f"  - Number of symbols: {len(symbols)}")
                    if symbols:
                        logger.info("  - Top 3 symbols:")
                        for i, sym in enumerate(symbols[:3]):
                            logger.info(f"    {i+1}. {sym}")
        except Exception as e:
            logger.error(f"Error testing top symbols: {e}")

async def main():
    """Run all tests."""
    logger.info("Starting dashboard integration tests...")
    logger.info(f"Testing against VPS: {BASE_URL}")
    logger.info("=" * 60)
    
    await test_dashboard_integration()
    
    logger.info("=" * 60)
    logger.info("Integration tests completed.")

if __name__ == "__main__":
    asyncio.run(main())