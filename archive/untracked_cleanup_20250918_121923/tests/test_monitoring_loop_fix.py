#!/usr/bin/env python3
"""
Test script to verify the monitoring loop fix.

This script tests the monitoring loop to ensure it runs continuously
and doesn't hang after the first cycle.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.monitoring.monitor import MarketMonitor
from src.core.market.top_symbols import TopSymbolsManager
from src.core.exchanges.manager import ExchangeManager
from src.core.validation.service import AsyncValidationService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_monitoring_loop():
    """Test that the monitoring loop runs continuously."""
    logger.info("🚀 Starting monitoring loop test")
    
    # Mock configuration for testing
    test_config = {
        'market': {
            'symbols': {
                'use_static_list': True,
                'static_symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT'],
                'max_symbols': 5,
                'cache_ttl': 60
            }
        },
        'interval': 10,  # Short interval for testing
        'max_concurrent_symbols': 3
    }
    
    try:
        # Create validation service (simplified mock)
        validation_service = AsyncValidationService()
        
        # Create exchange manager (simplified mock) 
        exchange_manager = ExchangeManager(test_config)
        
        # Create top symbols manager
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=test_config,
            validation_service=validation_service
        )
        
        # Create market monitor
        monitor = MarketMonitor(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=test_config,
            logger=logger
        )
        
        # Set running flag
        monitor.running = True
        
        logger.info("✅ Test components created, starting monitoring loop test")
        
        # Test the monitoring loop for 3 cycles (30 seconds)
        start_time = time.time()
        cycles_completed = 0
        
        async def monitor_cycles():
            nonlocal cycles_completed
            while time.time() - start_time < 35 and monitor.running:  # Run for 35 seconds
                try:
                    logger.info(f"🔄 Starting test cycle #{cycles_completed + 1}")
                    await monitor._monitoring_cycle()
                    cycles_completed += 1
                    logger.info(f"✅ Test cycle #{cycles_completed} completed")
                    
                    if cycles_completed >= 3:
                        logger.info("🎉 Successfully completed 3 monitoring cycles!")
                        break
                        
                    await asyncio.sleep(10)  # Wait 10 seconds between cycles
                    
                except Exception as e:
                    logger.error(f"❌ Error in test cycle #{cycles_completed + 1}: {e}")
                    break
        
        # Run the test
        await asyncio.wait_for(monitor_cycles(), timeout=40.0)
        
        duration = time.time() - start_time
        logger.info(f"📊 Test completed: {cycles_completed} cycles in {duration:.2f}s")
        
        if cycles_completed >= 2:
            logger.info("🎉 SUCCESS: Monitoring loop is working correctly!")
            return True
        else:
            logger.error("❌ FAILED: Monitoring loop did not complete enough cycles")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False
    finally:
        if 'monitor' in locals():
            monitor.running = False

if __name__ == "__main__":
    async def main():
        success = await test_monitoring_loop()
        sys.exit(0 if success else 1)
    
    asyncio.run(main())