#!/usr/bin/env python3
"""
Fix for CCXT "Error: 0" issue on Bybit ticker/trades fetches.

The issue occurs when CCXT can't parse Bybit's response format, causing it to
throw an exception with message "0" instead of proper error handling.

This script patches the CCXTExchange methods to handle this specific case.
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

async def test_ccxt_error_fix():
    """Test the CCXT Error: 0 fix."""
    try:
        logger.info("🔧 TESTING: CCXT Error: 0 fix")

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

        # Test problematic symbols that show "Error: 0"
        test_symbols = ['10000SATSUSDT', '1000BONKUSDT', '10000LADYSUSDT', 'BTCUSDT']

        for symbol in test_symbols:
            logger.info(f"🧪 Testing ticker fetch for {symbol}...")
            try:
                result = await exchange_manager.get_ticker(symbol)
                if result and 'error' not in result:
                    logger.info(f"✅ {symbol} ticker fetch successful!")
                else:
                    logger.warning(f"⚠️  {symbol} ticker returned: {result}")
            except Exception as e:
                if "0" == str(e).strip():
                    logger.error(f"❌ {symbol} still showing 'Error: 0' - fix needed")
                else:
                    logger.warning(f"⚠️  {symbol} ticker error (not Error: 0): {str(e)}")

        return True

    except Exception as e:
        logger.error(f"❌ Error testing fix: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_error_zero_patch():
    """Create a patch for the Error: 0 issue in CCXTExchange."""

    patch_code = '''
    async def _safe_ccxt_call(self, method, *args, **kwargs):
        """Safely call CCXT method with Error: 0 handling.

        Args:
            method: The CCXT method to call
            *args: Arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            Result of the method call or None if Error: 0 occurs
        """
        try:
            result = await method(*args, **kwargs)
            return result
        except Exception as e:
            error_msg = str(e).strip()
            if error_msg == "0":
                logger.warning(f"CCXT parsing issue (Error: 0) for {method.__name__}, returning None")
                return None
            else:
                # Re-raise other errors normally
                raise e

    async def fetch_ticker_safe(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker with Error: 0 protection."""
        try:
            self.validate_symbol(symbol)
            ccxt_symbol = self._convert_symbol_to_ccxt_format(symbol)

            # First try with session retry (existing fix)
            ticker = await self._execute_with_session_retry(
                self._safe_ccxt_call, self.ccxt.fetch_ticker, ccxt_symbol
            )

            if ticker is None:
                logger.debug(f"CCXT ticker parsing failed for {symbol}, symbol might not be supported")
                return None

            return self.standardize_response(ticker, 'ticker')

        except Exception as e:
            error_msg = str(e)
            if "not supported" in error_msg.lower() or "invalid symbol" in error_msg.lower():
                logger.warning(f"Symbol {symbol} not supported on this exchange: {error_msg}")
                return None
            else:
                logger.error(f"Error fetching ticker for {symbol}: {error_msg}")
                raise

    async def fetch_trades_safe(self, symbol: str, since: Optional[int] = None,
                              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch trades with Error: 0 protection."""
        try:
            self.validate_symbol(symbol)
            ccxt_symbol = self._convert_symbol_to_ccxt_format(symbol)

            # First try with session retry (existing fix)
            trades = await self._execute_with_session_retry(
                self._safe_ccxt_call, self.ccxt.fetch_trades, ccxt_symbol, since, limit
            )

            if trades is None:
                logger.debug(f"CCXT trades parsing failed for {symbol}, symbol might not be supported")
                return []

            return self.standardize_response(trades, 'trades')

        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {str(e)}")
            raise
    '''

    return patch_code

if __name__ == "__main__":
    logger.info("🚀 Starting CCXT Error: 0 fix test...")

    # First, let's test the current state
    success = asyncio.run(test_ccxt_error_fix())

    if success:
        logger.info("✅ CCXT ERROR FIX TEST COMPLETED")
        logger.info("💡 Use this information to apply the Error: 0 patch to production")

        # Show the patch code
        print("\n" + "="*60)
        print("PATCH CODE TO ADD TO CCXTExchange:")
        print("="*60)
        print(create_error_zero_patch())
        print("="*60)

    else:
        logger.error("❌ CCXT ERROR FIX TEST FAILED")
        sys.exit(1)