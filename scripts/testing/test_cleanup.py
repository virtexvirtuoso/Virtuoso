#!/usr/bin/env python3
"""
Test script to verify proper cleanup of aiohttp sessions and CCXT exchanges.
This script simulates the application startup and shutdown to test resource cleanup.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_cleanup():
    """Test the cleanup functionality."""
    logger.info("Starting cleanup test...")
    
    config_manager = None
    exchange_manager = None
    
    try:
        # Initialize components
        logger.info("Initializing config manager...")
        config_manager = ConfigManager()
        
        logger.info("Initializing exchange manager...")
        exchange_manager = ExchangeManager(config_manager)
        
        # Initialize exchanges
        if await exchange_manager.initialize():
            logger.info("Exchange manager initialized successfully")
        else:
            logger.warning("Exchange manager initialization failed")
        
        # Simulate some work
        logger.info("Simulating work for 2 seconds...")
        await asyncio.sleep(2)
        
        # Test cleanup
        logger.info("Testing cleanup...")
        if exchange_manager:
            await exchange_manager.cleanup()
            logger.info("Exchange manager cleanup completed")
        
        logger.info("Cleanup test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        raise
    finally:
        # Final cleanup
        if exchange_manager:
            try:
                await exchange_manager.cleanup()
            except Exception as e:
                logger.warning(f"Error in final cleanup: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(test_cleanup())
        logger.info("Test completed successfully")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        sys.exit(1) 