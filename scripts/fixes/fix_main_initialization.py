#!/usr/bin/env python3
"""
Fix the main.py initialization to add better logging and timeout handling.
This will help identify where the system is hanging.
"""

import re
from pathlib import Path

# Read main.py
main_file = Path(__file__).parent.parent / "src/main.py"
with open(main_file, 'r') as f:
    content = f.read()

# Add more detailed logging around initialization
patches = []

# 1. Add logging before each major initialization step
logging_patch = """
    async def initialize_all(self, app, loop):
        \"\"\"Initialize all required components in the correct order.\"\"\"
        try:
            self.logger.info("=" * 80)
            self.logger.info("Starting system initialization sequence")
            self.logger.info("=" * 80)
            
            # Config Manager
            self.logger.info("Step 1/8: Initializing Config Manager...")
            start_time = datetime.now()
            self.config_manager = ConfigManager()
            self.config_manager.config = self.config
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ Config Manager initialized in {duration:.2f}s")
            
            # Database Client  
            self.logger.info("Step 2/8: Initializing Database Client...")
            start_time = datetime.now()
            self.database_client = DatabaseClient(
                config=self.config_manager.get_database_config()
            )
            async with asyncio.timeout(10.0):
                await self.database_client.initialize()
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ Database Client initialized in {duration:.2f}s")
            
            # Exchange Manager
            self.logger.info("Step 3/8: Initializing Exchange Manager...")
            start_time = datetime.now()
            self.exchange_manager = ExchangeManager(self.config_manager.config)
            async with asyncio.timeout(30.0):
                await self.exchange_manager.initialize()
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ Exchange Manager initialized in {duration:.2f}s")
"""

# 2. Add timeout wrapper around the entire initialization
timeout_wrapper = """
async def run(self):
    \"\"\"Main entry point for the bot with initialization timeout.\"\"\"
    try:
        # Set up signal handlers first
        self._setup_signal_handlers()
        
        self.logger.info("Starting Virtuoso Trading System...")
        self.logger.info(f"Python version: {sys.version}")
        self.logger.info(f"Event loop: {type(asyncio.get_event_loop())}")
        
        # Create aiohttp application
        app = aiohttp.web.Application()
        
        # Initialize all components with timeout
        self.logger.info("Initializing system components with 120s timeout...")
        try:
            async with asyncio.timeout(120.0):  # 2 minute timeout for entire init
                await self.initialize_all(app, asyncio.get_event_loop())
        except asyncio.TimeoutError:
            self.logger.error("System initialization timed out after 120 seconds!")
            self.logger.error("Check which component is hanging:")
            self.logger.error("- Config loading?")
            self.logger.error("- Database connection?") 
            self.logger.error("- Exchange API calls?")
            self.logger.error("- Market data fetching?")
            raise SystemExit("Initialization timeout - check logs for details")
"""

# 3. Add component status logging
status_logging = """
        # Log component status after initialization
        self.logger.info("\\n" + "=" * 80)
        self.logger.info("INITIALIZATION COMPLETE - Component Status:")
        self.logger.info("=" * 80)
        
        components = [
            ("Config Manager", self.config_manager is not None),
            ("Database Client", self.database_client is not None and self.database_client.initialized),
            ("Exchange Manager", self.exchange_manager is not None),
            ("Market Data Manager", self.market_data_manager is not None),
            ("Confluence Analyzer", self.confluence_analyzer is not None),
            ("Alert Manager", self.alert_manager is not None),
            ("Market Monitor", self.market_monitor is not None),
            ("Dashboard", self.dashboard_integration is not None),
        ]
        
        for name, status in components:
            status_icon = "✅" if status else "❌"
            self.logger.info(f"{status_icon} {name}: {'Ready' if status else 'Failed'}")
            
        self.logger.info("=" * 80 + "\\n")
"""

# Write the patches
print("Patches to apply to main.py:")
print("\n1. Add detailed initialization logging")
print("2. Add timeout wrapper around initialization")
print("3. Add component status logging after init")
print("\nThis will help identify exactly where the system is hanging.")

# Create a new monitoring script instead
monitor_script = '''#!/usr/bin/env python3
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
        logger.info("\\n" + "=" * 80)
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
        logger.info(f"\\nTotal initialization time: {total_time:.2f}s")
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
        logger.info("\\nCleaning up...")
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
        logger.info("\\n✅ All components initialized successfully!")
        logger.info("The system should be ready to start.")
    else:
        logger.error("\\n❌ Initialization failed!")
        logger.error("Check the logs above to identify the failing component.")
        

if __name__ == "__main__":
    asyncio.run(main())
'''

# Save the monitoring script
monitor_file = Path(__file__).parent / "monitor_initialization.py"
with open(monitor_file, 'w') as f:
    f.write(monitor_script)

print(f"\n✅ Created monitoring script: {monitor_file}")
print("\nRun this script to diagnose where initialization is hanging:")
print(f"  python {monitor_file}")