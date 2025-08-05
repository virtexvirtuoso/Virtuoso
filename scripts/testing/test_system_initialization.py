#!/usr/bin/env python3
"""
Test the actual system initialization with our fixes.
This script simulates the real initialization flow.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_bybit_initialization():
    """Test Bybit initialization with our fixes."""
    logger.info("Testing Bybit initialization with BaseComponent...")
    
    try:
        from src.core.exchanges.bybit import BybitExchange
        from src.config.config_manager import ConfigManager
        
        # Load config
        config = ConfigManager().config
        
        # Create exchange instance
        exchange = BybitExchange(config.exchanges.bybit.model_dump())
        
        # Test initialization
        logger.info("First initialization attempt...")
        start_time = datetime.now()
        
        # First initialization
        result1 = await exchange.initialize(timeout=30.0)
        duration1 = (datetime.now() - start_time).total_seconds()
        
        if result1:
            logger.info(f"✅ First initialization successful in {duration1:.2f}s")
            logger.info(f"   State: {exchange.initialization_state.value}")
            logger.info(f"   Initialized: {exchange.initialized}")
        else:
            logger.error(f"❌ First initialization failed after {duration1:.2f}s")
            status = exchange.get_status()
            logger.error(f"   Error: {status['init_error']}")
            return False
        
        # Test duplicate initialization prevention
        logger.info("\nTesting duplicate initialization prevention...")
        start_time = datetime.now()
        
        result2 = await exchange.initialize(timeout=30.0)
        duration2 = (datetime.now() - start_time).total_seconds()
        
        if result2 and duration2 < 0.1:  # Should be instant
            logger.info(f"✅ Duplicate initialization properly prevented (took {duration2:.3f}s)")
        else:
            logger.error(f"❌ Duplicate initialization not prevented properly")
            return False
        
        # Clean up
        await exchange.close()
        logger.info("✅ Exchange closed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_startup_orchestrator():
    """Test the startup orchestrator with mock components."""
    logger.info("\nTesting Startup Orchestrator...")
    
    try:
        from src.core.startup_orchestrator import StartupOrchestrator
        from src.core.base_component import BaseComponent
        
        # Create mock components
        class MockExchange(BaseComponent):
            async def _do_initialize(self) -> bool:
                await asyncio.sleep(0.2)  # Simulate API calls
                return True
        
        class MockDatabase(BaseComponent):
            async def _do_initialize(self) -> bool:
                await asyncio.sleep(0.1)  # Simulate connection
                return True
        
        class MockMonitor(BaseComponent):
            async def _do_initialize(self) -> bool:
                await asyncio.sleep(0.15)  # Simulate setup
                return True
        
        # Create orchestrator
        orchestrator = StartupOrchestrator()
        
        # Register components
        orchestrator.register_component("database", MockDatabase({}, "Database"))
        orchestrator.register_component("exchange", MockExchange({}, "Exchange"))
        orchestrator.register_component("monitor", MockMonitor({}, "Monitor"))
        
        # Initialize all with proper order
        order = [
            ("database", 5.0),
            ("exchange", 5.0),
            ("monitor", 5.0),
        ]
        
        start_time = datetime.now()
        result = await orchestrator.initialize_all(order)
        total_duration = (datetime.now() - start_time).total_seconds()
        
        if result:
            logger.info(f"✅ All components initialized successfully in {total_duration:.2f}s")
            
            # Get report
            report = orchestrator.get_initialization_report()
            logger.info(f"   Successful: {report['successful_count']}/{report['total_components']}")
            
            # Check individual timings
            for comp, timing in report['initialization_times'].items():
                logger.info(f"   - {comp}: {timing:.3f}s")
        else:
            logger.error("❌ Some components failed to initialize")
            report = orchestrator.get_initialization_report()
            for comp, error in report['errors'].items():
                logger.error(f"   - {comp}: {error}")
            return False
        
        # Test shutdown
        await orchestrator.shutdown_all()
        logger.info("✅ All components shut down successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Orchestrator test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_timeout_behavior():
    """Test that timeouts work properly."""
    logger.info("\nTesting timeout behavior...")
    
    try:
        from src.core.base_component import BaseComponent
        
        class SlowComponent(BaseComponent):
            async def _do_initialize(self) -> bool:
                # This will take 5 seconds
                await asyncio.sleep(5.0)
                return True
        
        component = SlowComponent({}, "SlowComponent")
        
        # Test with short timeout
        logger.info("Testing with 1-second timeout on 5-second operation...")
        start_time = datetime.now()
        
        result = await component.initialize(timeout=1.0)
        duration = (datetime.now() - start_time).total_seconds()
        
        if not result and 0.9 < duration < 1.2:
            logger.info(f"✅ Timeout worked correctly (failed after {duration:.2f}s)")
            status = component.get_status()
            logger.info(f"   State: {status['state']}")
            logger.info(f"   Error: {status['init_error']}")
        else:
            logger.error(f"❌ Timeout did not work properly (took {duration:.2f}s)")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Timeout test failed: {str(e)}")
        return False


async def main():
    """Run all system initialization tests."""
    logger.info("🧪 Testing System Initialization with Critical Fixes")
    logger.info("=" * 60)
    
    results = []
    
    # Test 1: Bybit initialization
    logger.info("\n1. Bybit Exchange Initialization Test")
    logger.info("-" * 40)
    results.append(await test_bybit_initialization())
    
    # Test 2: Startup orchestrator
    logger.info("\n2. Startup Orchestrator Test")
    logger.info("-" * 40)
    results.append(await test_startup_orchestrator())
    
    # Test 3: Timeout behavior
    logger.info("\n3. Timeout Behavior Test")
    logger.info("-" * 40)
    results.append(await test_timeout_behavior())
    
    # Summary
    logger.info("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        logger.info(f"✅ All tests passed! ({passed}/{total})")
        logger.info("\nThe critical async fixes are working correctly:")
        logger.info("- Initialization state management prevents duplicates")
        logger.info("- Timeouts properly interrupt hanging operations")
        logger.info("- Orchestrator manages initialization order")
        logger.info("\n🚀 Ready to deploy to VPS!")
    else:
        logger.error(f"❌ Some tests failed: {passed}/{total} passed")
        logger.error("\nPlease review the errors above before deploying.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)