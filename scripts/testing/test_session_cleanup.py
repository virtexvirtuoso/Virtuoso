#!/usr/bin/env python3
"""
Test script to verify aiohttp session cleanup during exchange initialization.

This script tests the exchange initialization and cleanup process to ensure
that all aiohttp sessions and connectors are properly closed.
"""

import asyncio
import logging
import sys
import gc
import aiohttp
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.utils.logging_config import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

async def count_aiohttp_objects():
    """Count unclosed aiohttp sessions and connectors."""
    gc.collect()  # Force garbage collection
    
    sessions = 0
    connectors = 0
    
    for obj in gc.get_objects():
        try:
            if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
                sessions += 1
            elif isinstance(obj, (aiohttp.TCPConnector, aiohttp.BaseConnector)) and not obj.closed:
                connectors += 1
        except Exception:
            continue
    
    return sessions, connectors

async def test_exchange_cleanup():
    """Test exchange initialization and cleanup."""
    logger.info("🧪 Starting exchange cleanup test...")
    
    # Count initial objects
    initial_sessions, initial_connectors = await count_aiohttp_objects()
    logger.info(f"Initial state: {initial_sessions} sessions, {initial_connectors} connectors")
    
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        logger.info("✅ Config manager initialized")
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        logger.info("✅ Exchange manager created")
        
        # Initialize exchanges
        success = await exchange_manager.initialize()
        if success:
            logger.info("✅ Exchanges initialized successfully")
        else:
            logger.warning("⚠️ Exchange initialization failed")
        
        # Count objects after initialization
        post_init_sessions, post_init_connectors = await count_aiohttp_objects()
        logger.info(f"After initialization: {post_init_sessions} sessions, {post_init_connectors} connectors")
        
        # Test basic functionality
        primary_exchange = await exchange_manager.get_primary_exchange()
        if primary_exchange:
            logger.info(f"✅ Primary exchange: {primary_exchange.exchange_id}")
            
            # Test health check
            is_healthy = await exchange_manager.is_healthy()
            logger.info(f"✅ Exchange health check: {is_healthy}")
        else:
            logger.warning("⚠️ No primary exchange available")
        
        # Cleanup exchanges
        logger.info("🧹 Starting exchange cleanup...")
        await exchange_manager.cleanup()
        logger.info("✅ Exchange cleanup completed")
        
        # Count objects after cleanup
        post_cleanup_sessions, post_cleanup_connectors = await count_aiohttp_objects()
        logger.info(f"After cleanup: {post_cleanup_sessions} sessions, {post_cleanup_connectors} connectors")
        
        # Final comprehensive cleanup
        logger.info("🧹 Starting comprehensive session cleanup...")
        from src.main import _cleanup_remaining_sessions
        await _cleanup_remaining_sessions()
        
        # Final count
        final_sessions, final_connectors = await count_aiohttp_objects()
        logger.info(f"Final state: {final_sessions} sessions, {final_connectors} connectors")
        
        # Report results
        session_leak = final_sessions - initial_sessions
        connector_leak = final_connectors - initial_connectors
        
        if session_leak <= 0 and connector_leak <= 0:
            logger.info("🎉 SUCCESS: No session or connector leaks detected!")
            return True
        else:
            logger.warning(f"⚠️ POTENTIAL LEAKS: {session_leak} sessions, {connector_leak} connectors")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting aiohttp session cleanup test")
    
    try:
        success = await test_exchange_cleanup()
        
        if success:
            logger.info("✅ All tests passed!")
            return 0
        else:
            logger.error("❌ Some tests failed!")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 