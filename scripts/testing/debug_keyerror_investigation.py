#!/usr/bin/env python3
"""
Debug script to investigate KeyError issues in Bybit exchange.

This script will trigger the same operations that are causing KeyErrors
and provide detailed debugging information to identify the root cause.

Usage:
    python scripts/testing/debug_keyerror_investigation.py
"""

import sys
import os
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_keyerror_investigation.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main debugging function."""
    logger.info("🔍 Starting KeyError Investigation")
    logger.info("=" * 80)
    
    try:
        # Import required modules
        from core.exchanges.bybit import BybitExchange
        from core.config.config_manager import ConfigManager
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        logger.info("✅ Configuration loaded successfully")
        
        # Initialize Bybit exchange
        logger.info("🔧 Initializing Bybit exchange...")
        exchange = BybitExchange(config)
        
        # Initialize the exchange
        init_success = await exchange.initialize()
        if not init_success:
            logger.error("❌ Failed to initialize Bybit exchange")
            return
            
        logger.info("✅ Bybit exchange initialized successfully")
        
        # Test symbols that are causing issues
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for symbol in test_symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Testing symbol: {symbol}")
            logger.info(f"{'='*60}")
            
            # Test individual functions that are causing KeyErrors
            await test_lsr_function(exchange, symbol)
            await test_ohlcv_function(exchange, symbol)
            await test_oi_history_function(exchange, symbol)
            await test_volatility_function(exchange, symbol)
            
            # Test the main fetch_market_data function
            await test_fetch_market_data(exchange, symbol)
            
            # Add delay between symbols to avoid rate limiting
            await asyncio.sleep(2)
        
        # Close the exchange
        await exchange.close()
        logger.info("✅ Exchange closed successfully")
        
    except Exception as e:
        logger.error(f"❌ Critical error in main: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

async def test_lsr_function(exchange, symbol: str):
    """Test the _fetch_long_short_ratio function."""
    logger.info(f"🔍 Testing LSR function for {symbol}")
    try:
        result = await exchange._fetch_long_short_ratio(symbol)
        logger.info(f"✅ LSR function completed for {symbol}")
        logger.info(f"✅ LSR result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"✅ LSR result keys: {list(result.keys())}")
        logger.info(f"✅ LSR result: {result}")
    except Exception as e:
        logger.error(f"❌ LSR function failed for {symbol}: {str(e)}")
        import traceback
        logger.error(f"❌ LSR traceback: {traceback.format_exc()}")

async def test_ohlcv_function(exchange, symbol: str):
    """Test the _fetch_all_timeframes function."""
    logger.info(f"🔍 Testing OHLCV function for {symbol}")
    try:
        result = await exchange._fetch_all_timeframes(symbol)
        logger.info(f"✅ OHLCV function completed for {symbol}")
        logger.info(f"✅ OHLCV result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"✅ OHLCV result keys: {list(result.keys())}")
        logger.info(f"✅ OHLCV result summary: {len(result) if result else 0} timeframes")
    except Exception as e:
        logger.error(f"❌ OHLCV function failed for {symbol}: {str(e)}")
        import traceback
        logger.error(f"❌ OHLCV traceback: {traceback.format_exc()}")

async def test_oi_history_function(exchange, symbol: str):
    """Test the fetch_open_interest_history function."""
    logger.info(f"🔍 Testing OI History function for {symbol}")
    try:
        result = await exchange.fetch_open_interest_history(symbol, '5min', 200)
        logger.info(f"✅ OI History function completed for {symbol}")
        logger.info(f"✅ OI History result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"✅ OI History result keys: {list(result.keys())}")
        logger.info(f"✅ OI History result summary: {result}")
    except Exception as e:
        logger.error(f"❌ OI History function failed for {symbol}: {str(e)}")
        import traceback
        logger.error(f"❌ OI History traceback: {traceback.format_exc()}")

async def test_volatility_function(exchange, symbol: str):
    """Test the _calculate_historical_volatility function."""
    logger.info(f"🔍 Testing Volatility function for {symbol}")
    try:
        result = await exchange._calculate_historical_volatility(symbol, '5min', 24)
        logger.info(f"✅ Volatility function completed for {symbol}")
        logger.info(f"✅ Volatility result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"✅ Volatility result keys: {list(result.keys())}")
        logger.info(f"✅ Volatility result summary: {result}")
    except Exception as e:
        logger.error(f"❌ Volatility function failed for {symbol}: {str(e)}")
        import traceback
        logger.error(f"❌ Volatility traceback: {traceback.format_exc()}")

async def test_fetch_market_data(exchange, symbol: str):
    """Test the main fetch_market_data function."""
    logger.info(f"🔍 Testing fetch_market_data function for {symbol}")
    try:
        start_time = time.time()
        result = await exchange.fetch_market_data(symbol)
        elapsed = time.time() - start_time
        
        logger.info(f"✅ fetch_market_data completed for {symbol} in {elapsed:.2f}s")
        logger.info(f"✅ Market data result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"✅ Market data result keys: {list(result.keys())}")
            
            # Check specific components
            if 'sentiment' in result:
                logger.info(f"✅ Sentiment keys: {list(result['sentiment'].keys()) if result['sentiment'] else 'None'}")
            if 'ohlcv' in result:
                logger.info(f"✅ OHLCV keys: {list(result['ohlcv'].keys()) if result['ohlcv'] else 'None'}")
            if 'metadata' in result:
                logger.info(f"✅ Metadata keys: {list(result['metadata'].keys()) if result['metadata'] else 'None'}")
                
        logger.info(f"✅ Market data fetch successful for {symbol}")
        
    except Exception as e:
        logger.error(f"❌ fetch_market_data failed for {symbol}: {str(e)}")
        import traceback
        logger.error(f"❌ fetch_market_data traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info(f"🚀 Starting KeyError investigation at {datetime.now()}")
    asyncio.run(main())
    logger.info(f"🏁 KeyError investigation completed at {datetime.now()}") 