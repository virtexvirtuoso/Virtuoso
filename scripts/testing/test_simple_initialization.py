#!/usr/bin/env python3
"""
Simplified initialization test to identify hanging point.
Tests just the core components that are causing issues.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_exchange_manager_init():
    """Test just the Exchange Manager initialization."""
    logger.info("=" * 80)
    logger.info("Testing Exchange Manager Initialization")
    logger.info("=" * 80)
    
    try:
        # Step 1: Config
        logger.info("\n1. Loading configuration...")
        from src.config.manager import ConfigManager
        config_manager = ConfigManager()
        logger.info("✅ Config loaded successfully")
        
        # Step 2: Exchange Manager
        logger.info("\n2. Creating Exchange Manager...")
        from src.core.exchanges.exchange_manager import ExchangeManager
        exchange_manager = ExchangeManager(config_manager.config)
        logger.info("✅ Exchange Manager created")
        
        # Step 3: Initialize with detailed logging
        logger.info("\n3. Initializing Exchange Manager (this is where it might hang)...")
        logger.info("   Starting initialization with 30s timeout...")
        
        start_time = time.time()
        
        # Add timeout protection
        try:
            async with asyncio.timeout(30.0):
                await exchange_manager.initialize()
                
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"❌ TIMEOUT: Exchange initialization hung after {duration:.1f}s")
            logger.error("The system is hanging during exchange initialization!")
            return False
            
        duration = time.time() - start_time
        logger.info(f"✅ Exchange Manager initialized in {duration:.2f}s")
        
        # Step 4: Check exchange status
        logger.info("\n4. Checking exchange status...")
        if hasattr(exchange_manager, 'exchanges'):
            for name, exchange in exchange_manager.exchanges.items():
                if hasattr(exchange, 'initialized'):
                    status = "Initialized" if exchange.initialized else "Not initialized"
                    logger.info(f"   - {name}: {status}")
                    
        # Step 5: Clean up
        logger.info("\n5. Cleaning up...")
        await exchange_manager.close()
        logger.info("✅ Cleanup complete")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_bybit_direct():
    """Test Bybit initialization directly."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing Direct Bybit Initialization")
    logger.info("=" * 80)
    
    try:
        from src.config.manager import ConfigManager
        from src.core.exchanges.bybit import BybitExchange
        
        # Get config
        config = ConfigManager().config
        bybit_config = config['exchanges']['bybit']
        
        logger.info("Creating BybitExchange instance...")
        exchange = BybitExchange(bybit_config)
        
        logger.info("Starting initialization with 15s timeout...")
        start_time = time.time()
        
        try:
            # Check if exchange has the new initialize method
            if hasattr(exchange, 'initialize'):
                logger.info("Using initialize() method...")
                async with asyncio.timeout(15.0):
                    result = await exchange.initialize()
            else:
                logger.warning("No initialize() method found, exchange might already be initialized")
                result = True
                
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"❌ TIMEOUT: Bybit initialization hung after {duration:.1f}s")
            return False
            
        duration = time.time() - start_time
        
        if result:
            logger.info(f"✅ Bybit initialized in {duration:.2f}s")
        else:
            logger.error(f"❌ Bybit initialization failed after {duration:.2f}s")
            
        # Clean up
        if hasattr(exchange, 'close'):
            await exchange.close()
            
        return result
        
    except Exception as e:
        logger.error(f"Direct Bybit test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def check_api_connectivity():
    """Check if we can reach Bybit API."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing API Connectivity")
    logger.info("=" * 80)
    
    try:
        import aiohttp
        
        urls = [
            "https://api.bybit.com/v5/market/time",
            "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
        ]
        
        async with aiohttp.ClientSession() as session:
            for url in urls:
                logger.info(f"\nTesting: {url}")
                start_time = time.time()
                
                try:
                    async with asyncio.timeout(5.0):
                        async with session.get(url) as response:
                            duration = time.time() - start_time
                            
                            if response.status == 200:
                                data = await response.json()
                                logger.info(f"✅ Success (200) in {duration:.2f}s")
                                if 'retCode' in data:
                                    logger.info(f"   retCode: {data['retCode']}")
                            else:
                                logger.error(f"❌ Failed with status {response.status}")
                                
                except asyncio.TimeoutError:
                    logger.error(f"❌ Timeout after 5s")
                except Exception as e:
                    logger.error(f"❌ Error: {str(e)}")
                    
        return True
        
    except Exception as e:
        logger.error(f"Connectivity test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Virtuoso System - Initialization Diagnostics")
    logger.info("=" * 80)
    
    # Test 1: API connectivity
    await check_api_connectivity()
    
    # Test 2: Direct Bybit initialization
    bybit_ok = await test_bybit_direct()
    
    # Test 3: Exchange Manager initialization
    exchange_ok = await test_exchange_manager_init()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Direct Bybit Init: {'✅ PASS' if bybit_ok else '❌ FAIL'}")
    logger.info(f"Exchange Manager: {'✅ PASS' if exchange_ok else '❌ FAIL'}")
    
    if bybit_ok and exchange_ok:
        logger.info("\n✅ All tests passed!")
        logger.info("The initialization issues might be in the main.py flow.")
    else:
        logger.error("\n❌ Some tests failed!")
        logger.error("The system is hanging during exchange initialization.")


if __name__ == "__main__":
    asyncio.run(main())