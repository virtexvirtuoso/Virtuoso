#!/usr/bin/env python3
"""
Debug script to test exchange manager and database client health
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.manager import ConfigManager
from core.exchanges.manager import ExchangeManager
from data_storage.database import DatabaseClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_exchange_manager():
    """Test exchange manager initialization and health"""
    logger.info("=== Testing Exchange Manager ===")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        logger.info("ConfigManager initialized")
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        logger.info("ExchangeManager created")
        
        # Test initialization
        success = await exchange_manager.initialize()
        logger.info(f"Exchange initialization result: {success}")
        
        if success:
            # Test primary exchange
            primary_exchange = await exchange_manager.get_primary_exchange()
            if primary_exchange:
                logger.info(f"Primary exchange: {primary_exchange.exchange_id}")
                
                # Test API credentials
                api_key = getattr(primary_exchange, 'api_key', None)
                api_secret = getattr(primary_exchange, 'api_secret', None)
                logger.info(f"API key configured: {bool(api_key)}")
                logger.info(f"API secret configured: {bool(api_secret)}")
                
                if api_key:
                    logger.info(f"API key length: {len(api_key)}")
                    logger.info(f"API key starts with: {api_key[:10]}...")
                
                # Test health check
                is_healthy = await exchange_manager.is_healthy()
                logger.info(f"Exchange manager health: {is_healthy}")
                
                # Test specific exchange health
                exchange_healthy = await primary_exchange.health_check()
                logger.info(f"Primary exchange health: {exchange_healthy}")
                
            else:
                logger.error("No primary exchange found")
        else:
            logger.error("Exchange manager initialization failed")
            
        # Cleanup
        await exchange_manager.cleanup()
        
    except Exception as e:
        logger.error(f"Exchange manager test failed: {str(e)}", exc_info=True)

async def test_database_client():
    """Test database client initialization and health"""
    logger.info("=== Testing Database Client ===")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Initialize database client
        database_client = DatabaseClient(config)
        logger.info("DatabaseClient created")
        
        # Test connection
        is_healthy = await database_client.is_healthy()
        logger.info(f"Database client health: {is_healthy}")
        
        # Test specific database operations
        try:
            # Test a simple query/operation
            await database_client.initialize()
            logger.info("Database initialization successful")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Database client test failed: {str(e)}", exc_info=True)

async def test_api_credentials():
    """Test API credentials directly"""
    logger.info("=== Testing API Credentials ===")
    
    # Check environment variables
    bybit_key = os.getenv('BYBIT_API_KEY')
    bybit_secret = os.getenv('BYBIT_API_SECRET')
    
    logger.info(f"BYBIT_API_KEY found: {bool(bybit_key)}")
    logger.info(f"BYBIT_API_SECRET found: {bool(bybit_secret)}")
    
    if bybit_key:
        logger.info(f"API key length: {len(bybit_key)}")
        logger.info(f"API key starts with: {bybit_key[:10]}...")
    
    if bybit_secret:
        logger.info(f"API secret length: {len(bybit_secret)}")
        logger.info(f"API secret starts with: {bybit_secret[:10]}...")

async def main():
    """Run all tests"""
    logger.info("Starting Health Check Diagnostics")
    
    await test_api_credentials()
    await test_exchange_manager()
    await test_database_client()
    
    logger.info("Health Check Diagnostics Complete")

if __name__ == "__main__":
    asyncio.run(main()) 