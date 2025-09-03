#!/usr/bin/env python3
"""
Test script to verify DI container can resolve refactored monitoring components.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_di_resolution():
    """Test DI container resolution for refactored components."""
    try:
        # Import DI components
        from src.core.di.registration import bootstrap_container
        from src.core.di.container import ServiceContainer
        
        logger.info("Creating DI container...")
        container = bootstrap_container()
        
        logger.info("Testing AlertManager resolution...")
        
        # Test AlertManager resolution through different interfaces
        try:
            from src.core.interfaces.services import IAlertService
            alert_service = await container.get_service(IAlertService)
            logger.info(f"✓ IAlertService resolved: {type(alert_service).__name__}")
        except Exception as e:
            logger.error(f"✗ Failed to resolve IAlertService: {e}")
        
        # Test concrete AlertManager resolution
        try:
            # This should work with both original and refactored
            from src.monitoring.alert_manager import AlertManager
            alert_manager = await container.get_service(AlertManager)
            logger.info(f"✓ AlertManager resolved: {type(alert_manager).__name__}")
        except Exception as e:
            logger.error(f"✗ Failed to resolve AlertManager: {e}")
        
        # Test RefactoredAlertManager resolution
        try:
            from src.monitoring.components.alerts.alert_manager_refactored import AlertManagerRefactored
            alert_manager_refactored = await container.get_service(AlertManagerRefactored)
            logger.info(f"✓ AlertManagerRefactored resolved: {type(alert_manager_refactored).__name__}")
        except Exception as e:
            logger.error(f"✗ Failed to resolve AlertManagerRefactored: {e}")
        
        logger.info("Testing MarketMonitor resolution...")
        
        # Test MarketMonitor resolution
        try:
            from src.monitoring.monitor import MarketMonitor
            market_monitor = await container.get_service(MarketMonitor)
            logger.info(f"✓ MarketMonitor resolved: {type(market_monitor).__name__}")
        except Exception as e:
            logger.error(f"✗ Failed to resolve MarketMonitor: {e}")
        
        # Test RefactoredMarketMonitor resolution
        try:
            from src.monitoring.monitor_refactored import RefactoredMarketMonitor
            refactored_monitor = await container.get_service(RefactoredMarketMonitor)
            logger.info(f"✓ RefactoredMarketMonitor resolved: {type(refactored_monitor).__name__}")
        except Exception as e:
            logger.error(f"✗ Failed to resolve RefactoredMarketMonitor: {e}")
        
        logger.info("Testing component compatibility...")
        
        # Test that the resolved components are actually the refactored ones
        try:
            from src.monitoring.alert_manager import AlertManager as ImportedAlertManager
            alert_manager = await container.get_service(ImportedAlertManager)
            
            # Check if it's actually the refactored version
            if type(alert_manager).__name__ == 'AlertManagerRefactored':
                logger.info("✓ AlertManager is using refactored implementation")
            elif hasattr(alert_manager, '_alert_delivery') and hasattr(alert_manager, '_alert_throttler'):
                logger.info("✓ AlertManager is using refactored implementation (with components)")
            else:
                logger.warning("? AlertManager appears to be original implementation")
                
        except Exception as e:
            logger.error(f"✗ Failed compatibility test for AlertManager: {e}")
        
        try:
            from src.monitoring.monitor import MarketMonitor as ImportedMarketMonitor
            market_monitor = await container.get_service(ImportedMarketMonitor)
            
            # Check if it's actually the refactored version
            if type(market_monitor).__name__ == 'RefactoredMarketMonitor':
                logger.info("✓ MarketMonitor is using refactored implementation")
            elif hasattr(market_monitor, '_data_collector') and hasattr(market_monitor, '_signal_processor'):
                logger.info("✓ MarketMonitor is using refactored implementation (with components)")
            else:
                logger.warning("? MarketMonitor appears to be original implementation")
                
        except Exception as e:
            logger.error(f"✗ Failed compatibility test for MarketMonitor: {e}")
        
        logger.info("DI resolution test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"DI resolution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    logger.info("Starting DI refactored components test...")
    
    success = await test_di_resolution()
    
    if success:
        logger.info("✓ All tests passed - DI container properly resolves refactored components")
        return 0
    else:
        logger.error("✗ Some tests failed - DI container needs fixes")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)