#!/usr/bin/env python3
"""
DEBUG: Symbol Mismatch Investigation

TopSymbolsManager selects "10000SATSUSDT" but CCXTExchange rejects it.
This script investigates the mismatch between loaded markets and selected symbols.
"""

import asyncio
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_symbol_mismatch():
    """Debug symbol loading vs symbol selection mismatch."""
    try:
        logger.info("🔍 DEBUGGING: Symbol mismatch between TopSymbolsManager and CCXTExchange")

        # Import CCXT directly to check markets
        import ccxt.async_support as ccxt

        # Create Bybit instance
        bybit = ccxt.bybit({
            'enableRateLimit': True,
            'timeout': 30000
        })

        logger.info("✅ Created Bybit CCXT instance")

        # Load markets
        logger.info("🔄 Loading markets from Bybit...")
        markets = await bybit.load_markets()
        logger.info(f"✅ Loaded {len(markets)} markets from Bybit")

        # Check specific symbols
        test_symbols = ['10000SATSUSDT', '1000BONKUSDT', '10000LADYSUSDT', 'BTCUSDT', 'ETHUSDT']

        logger.info("🔍 Checking specific symbols in loaded markets:")
        for symbol in test_symbols:
            if symbol in markets:
                market = markets[symbol]
                logger.info(f"✅ {symbol}: FOUND - Type: {market.get('type', 'unknown')}, Active: {market.get('active', 'unknown')}")
            else:
                logger.info(f"❌ {symbol}: NOT FOUND in markets")

        # Search for partial matches
        logger.info("🔍 Searching for similar symbols:")
        for symbol in test_symbols:
            if symbol not in markets:
                # Look for similar symbols
                similar = [s for s in markets.keys() if '10000SATS' in s or '1000BONK' in s or '10000LADYS' in s]
                if similar:
                    logger.info(f"💡 Similar to {symbol}: {similar[:3]}")

        # Check market types
        market_types = {}
        for symbol, market in markets.items():
            market_type = market.get('type', 'unknown')
            if market_type not in market_types:
                market_types[market_type] = []
            market_types[market_type].append(symbol)

        logger.info("📊 Market types distribution:")
        for market_type, symbols in market_types.items():
            logger.info(f"  {market_type}: {len(symbols)} symbols")
            if market_type in ['swap', 'future'] and len(symbols) < 10:
                logger.info(f"    Sample: {symbols[:5]}")

        # Check if we need to filter by type
        logger.info("🔍 Checking linear perpetual markets:")
        linear_markets = [s for s, m in markets.items() if m.get('type') == 'swap' and m.get('linear') == True]
        logger.info(f"Found {len(linear_markets)} linear perpetual markets")

        if linear_markets:
            logger.info(f"Sample linear markets: {linear_markets[:10]}")

            # Check our test symbols in linear markets
            for symbol in test_symbols:
                if symbol in linear_markets:
                    logger.info(f"✅ {symbol}: Found in linear markets")
                else:
                    logger.info(f"❌ {symbol}: NOT in linear markets")

        await bybit.close()
        logger.info("✅ Closed Bybit connection")

        return True

    except Exception as e:
        logger.error(f"❌ Error debugging symbols: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting symbol mismatch debug...")
    success = asyncio.run(debug_symbol_mismatch())
    if success:
        logger.info("✅ DEBUG COMPLETE - Check results above")
    else:
        logger.error("❌ DEBUG FAILED")
        sys.exit(1)