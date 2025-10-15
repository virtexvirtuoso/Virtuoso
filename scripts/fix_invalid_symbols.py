#!/usr/bin/env python3
"""
CRITICAL: Fix Invalid Symbols in TopSymbolsManager Cache

The system is processing invalid symbols like "10000SATSUSDT" that don't exist on Bybit.
This script forces a refresh of the TopSymbolsManager cache to get valid symbols.
"""

import asyncio
import sys
import os
import logging
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_invalid_symbols():
    """Force refresh TopSymbolsManager to get valid symbols from Bybit."""
    try:
        logger.info("🔧 FIXING: Invalid symbols in TopSymbolsManager cache")

        # Import after path setup
        from config.config import load_config
        from core.di.container import Container

        # Load configuration
        config = load_config()
        logger.info("✅ Configuration loaded")

        # Create DI container
        container = Container()
        await container.init(config)
        logger.info("✅ DI Container initialized")

        # Get TopSymbolsManager
        top_symbols_manager = container.resolve('top_symbols_manager')
        if not top_symbols_manager:
            logger.error("❌ Could not resolve top_symbols_manager from container")
            return False

        logger.info("✅ TopSymbolsManager resolved")

        # Force refresh symbols (bypass cache)
        logger.info("🔄 Force refreshing symbol cache...")
        start_time = time.time()

        symbols = await top_symbols_manager.get_symbols(force_refresh=True, limit=15)

        refresh_time = time.time() - start_time
        logger.info(f"✅ Symbol refresh completed in {refresh_time:.2f}s")

        # Log the new symbols
        logger.info(f"📊 Retrieved {len(symbols)} symbols:")
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"  {i}: {symbol}")

        # Validate symbols don't contain invalid ones
        invalid_symbols = [s for s in symbols if '10000' in s or '1000000' in s]
        if invalid_symbols:
            logger.warning(f"⚠️  Still found potentially invalid symbols: {invalid_symbols}")
            logger.warning("💡 These might be valid on Bybit, checking...")

            # Check if they're actually supported on Bybit
            exchange_manager = container.resolve('exchange_manager')
            if exchange_manager:
                for symbol in invalid_symbols[:3]:  # Check first 3 only
                    try:
                        result = await exchange_manager.get_ticker(symbol)
                        if result and 'error' not in result:
                            logger.info(f"✅ {symbol} is actually valid on Bybit")
                        else:
                            logger.warning(f"⚠️  {symbol} is not supported on Bybit")
                    except Exception as e:
                        logger.warning(f"⚠️  {symbol} validation failed: {str(e)}")
        else:
            logger.info("✅ No obviously invalid symbols found")

        logger.info("🎉 Symbol cache refresh complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Error fixing symbols: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting symbol fix script...")
    success = asyncio.run(fix_invalid_symbols())
    if success:
        logger.info("✅ SYMBOL FIX SUCCESSFUL - Invalid symbols should be cleared")
    else:
        logger.error("❌ SYMBOL FIX FAILED")
        sys.exit(1)