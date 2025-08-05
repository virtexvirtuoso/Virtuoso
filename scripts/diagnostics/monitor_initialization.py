#!/usr/bin/env python3
"""
Monitor the initialization process with detailed timing and timeout protection.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
import signal

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


class InitializationMonitor:
    """Monitor and track initialization progress."""
    
    def __init__(self):
        self.start_times = {}
        self.durations = {}
        self.statuses = {}
        self.current_step = None
        self.timeout_handle = None
        
    def start_step(self, step_name: str, timeout: float = 30.0):
        """Start tracking a step."""
        self.current_step = step_name
        self.start_times[step_name] = time.time()
        self.statuses[step_name] = "in_progress"
        
        # Set timeout alarm
        def timeout_handler(signum, frame):
            logger.error(f"⏱️ TIMEOUT: {step_name} exceeded {timeout}s limit!")
            logger.error(f"System appears to be hanging at: {step_name}")
            self.statuses[step_name] = "timeout"
            raise TimeoutError(f"{step_name} initialization timeout")
            
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        logger.info(f"▶️  Starting: {step_name} (timeout: {timeout}s)")
        
    def complete_step(self, step_name: str, success: bool = True):
        """Mark a step as complete."""
        signal.alarm(0)  # Cancel timeout
        
        if step_name in self.start_times:
            duration = time.time() - self.start_times[step_name]
            self.durations[step_name] = duration
            self.statuses[step_name] = "success" if success else "failed"
            
            icon = "✅" if success else "❌"
            logger.info(f"{icon} Completed: {step_name} in {duration:.2f}s")
        
    def print_summary(self):
        """Print initialization summary."""
        logger.info("\n" + "=" * 80)
        logger.info("INITIALIZATION SUMMARY")
        logger.info("=" * 80)
        
        for step_name, status in self.statuses.items():
            duration = self.durations.get(step_name, 0)
            if status == "success":
                logger.info(f"✅ {step_name:30} {duration:6.2f}s")
            elif status == "failed":
                logger.error(f"❌ {step_name:30} {duration:6.2f}s")
            elif status == "timeout":
                logger.error(f"⏱️  {step_name:30} TIMEOUT")
            else:
                logger.warning(f"⚠️  {step_name:30} {status}")
                
        total_time = sum(self.durations.values())
        logger.info(f"\nTotal initialization time: {total_time:.2f}s")
        logger.info("=" * 80)


async def monitored_initialization():
    """Run initialization with monitoring."""
    monitor = InitializationMonitor()
    
    try:
        # Step 1: Config Manager
        monitor.start_step("Config Manager", timeout=10.0)
        from src.config.manager import ConfigManager
        config_manager = ConfigManager()
        monitor.complete_step("Config Manager")
        
        # Step 2: Database Client
        monitor.start_step("Database Client", timeout=15.0)
        from src.core.database.client import DatabaseClient
        db_client = DatabaseClient(config_manager.get_database_config())
        await db_client.initialize()
        monitor.complete_step("Database Client")
        
        # Step 3: Exchange Manager
        monitor.start_step("Exchange Manager", timeout=30.0)
        from src.core.exchanges.exchange_manager import ExchangeManager
        exchange_manager = ExchangeManager(config_manager.config)
        await exchange_manager.initialize()
        monitor.complete_step("Exchange Manager")
        
        # Step 4: Market Data Manager
        monitor.start_step("Market Data Manager", timeout=30.0)
        from src.core.market.market_data_manager import MarketDataManager
        market_data = MarketDataManager(
            exchange_manager=exchange_manager,
            config=config_manager.get_market_data_config()
        )
        await market_data.initialize()
        monitor.complete_step("Market Data Manager")
        
        # Print summary
        monitor.print_summary()
        
        # Clean up
        logger.info("\nCleaning up...")
        await market_data.close()
        await exchange_manager.close()
        await db_client.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Mark current step as failed
        if monitor.current_step:
            monitor.complete_step(monitor.current_step, success=False)
            
        monitor.print_summary()
        return False


async def main():
    """Main entry point."""
    logger.info("🚀 Virtuoso Trading System - Initialization Monitor")
    logger.info("=" * 80)
    
    success = await monitored_initialization()
    
    if success:
        logger.info("\n✅ All components initialized successfully!")
        logger.info("The system should be ready to start.")
    else:
        logger.error("\n❌ Initialization failed!")
        logger.error("Check the logs above to identify the failing component.")
        

if __name__ == "__main__":
    asyncio.run(main())
