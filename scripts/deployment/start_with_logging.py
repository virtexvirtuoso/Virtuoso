#!/usr/bin/env python3
"""Simple startup wrapper with better logging."""

import asyncio
import sys
import os
import signal
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('startup.log')
    ]
)

logger = logging.getLogger(__name__)

# Track if we're shutting down
shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    shutdown_event.set()

async def main():
    """Main startup function."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Virtuoso Trading System...")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        # Import after setting up logging
        from src.main import run_application
        
        logger.info("Starting main application...")
        
        # Create a task for the main app
        app_task = asyncio.create_task(run_application())
        
        # Wait for either the app to finish or shutdown signal
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        done, pending = await asyncio.wait(
            [app_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        # Check if app task had an error
        if app_task in done:
            try:
                await app_task
            except Exception as e:
                logger.error(f"Application error: {e}", exc_info=True)
                return 1
                
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
        return 1
    
    logger.info("Shutdown complete")
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        sys.exit(0)