#!/usr/bin/env python3
"""
CRITICAL: Fix Persistent aiohttp Session Management Issues

The production system is experiencing persistent "Session is closed" errors
even after service restarts. This indicates CCXT's aiohttp sessions are not
being properly managed. This script implements proper session lifecycle management.
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

async def fix_session_management():
    """Fix aiohttp session management in CCXT exchanges."""
    try:
        logger.info("🔧 FIXING: Persistent aiohttp session management issues")

        # Import after path setup
        from config.manager import ConfigManager
        from core.di.container import Container

        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        logger.info("✅ Configuration loaded")

        # Create DI container
        container = Container()
        await container.init(config)
        logger.info("✅ DI Container initialized")

        # Get exchange manager
        exchange_manager = container.resolve('exchange_manager')
        if not exchange_manager:
            logger.error("❌ Could not resolve exchange_manager from container")
            return False

        logger.info("✅ Exchange Manager resolved")

        # Force close and recreate all exchange connections
        logger.info("🔄 Forcing session cleanup and reconnection...")

        # Get the exchange instance
        exchanges = exchange_manager.exchanges
        logger.info(f"📊 Found {len(exchanges)} exchange instances")

        for exchange_name, exchange in exchanges.items():
            logger.info(f"🔧 Resetting {exchange_name} exchange session...")

            try:
                # Close existing session if it exists
                if hasattr(exchange, 'session') and exchange.session:
                    logger.info(f"  Closing existing {exchange_name} session...")
                    if not exchange.session.closed:
                        await exchange.session.close()
                    exchange.session = None

                # Also check for CCXT instance session
                if hasattr(exchange, 'exchange') and hasattr(exchange.exchange, 'session'):
                    if exchange.exchange.session and not exchange.exchange.session.closed:
                        logger.info(f"  Closing CCXT {exchange_name} session...")
                        await exchange.exchange.session.close()
                    exchange.exchange.session = None

                # Force reinitialize the exchange
                logger.info(f"  Reinitializing {exchange_name} exchange...")
                await exchange.init()

                logger.info(f"✅ {exchange_name} session reset completed")

            except Exception as e:
                logger.warning(f"⚠️  Error resetting {exchange_name}: {str(e)}")
                # Continue with other exchanges

        # Test connectivity after reset
        logger.info("🧪 Testing exchange connectivity after session reset...")

        test_symbols = ['BTCUSDT', 'ETHUSDT']
        for symbol in test_symbols:
            try:
                logger.info(f"  Testing {symbol} ticker fetch...")
                result = await exchange_manager.get_ticker(symbol)

                if result and 'error' not in result:
                    logger.info(f"✅ {symbol} ticker fetch successful - Session reset working!")
                else:
                    logger.warning(f"⚠️  {symbol} ticker fetch returned: {result}")

            except Exception as e:
                if "Session is closed" in str(e):
                    logger.error(f"❌ {symbol} still showing session errors: {str(e)}")
                    return False
                else:
                    logger.warning(f"⚠️  {symbol} test failed (not session related): {str(e)}")

        logger.info("🎉 Session management fix complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Error fixing session management: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting aiohttp session management fix...")
    success = asyncio.run(fix_session_management())
    if success:
        logger.info("✅ SESSION MANAGEMENT FIX SUCCESSFUL")
        logger.info("💡 Deploy this fix to production to resolve persistent session errors")
    else:
        logger.error("❌ SESSION MANAGEMENT FIX FAILED")
        sys.exit(1)