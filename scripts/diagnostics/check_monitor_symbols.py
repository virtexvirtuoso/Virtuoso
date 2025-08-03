#!/usr/bin/env python3
"""Check if monitor has symbols populated."""

import asyncio
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_monitor_symbols():
    """Check if monitor has symbols."""
    try:
        # Import after setting path
        from src.main import initialize_components
        
        logger.info("Initializing components...")
        components = await initialize_components()
        
        monitor = components.get('market_monitor')
        if monitor:
            logger.info(f"Monitor initialized: {monitor}")
            
            # Check symbols
            if hasattr(monitor, 'symbols'):
                logger.info(f"Monitor symbols: {monitor.symbols}")
                logger.info(f"Number of symbols: {len(monitor.symbols) if monitor.symbols else 0}")
            else:
                logger.warning("Monitor has no symbols attribute")
                
            # Check top_symbols_manager
            if hasattr(monitor, 'top_symbols_manager'):
                logger.info(f"Top symbols manager: {monitor.top_symbols_manager}")
                if monitor.top_symbols_manager:
                    try:
                        symbols = await monitor.top_symbols_manager.get_top_symbols(limit=10)
                        logger.info(f"Top symbols from manager: {symbols}")
                    except Exception as e:
                        logger.error(f"Error getting top symbols: {e}")
            else:
                logger.warning("Monitor has no top_symbols_manager")
                
            # Check confluence analyzer
            if hasattr(monitor, 'confluence_analyzer'):
                logger.info(f"Confluence analyzer: {monitor.confluence_analyzer}")
            else:
                logger.warning("Monitor has no confluence_analyzer")
                
        else:
            logger.error("No monitor in components!")
            
    except Exception as e:
        logger.error(f"Error checking monitor: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_monitor_symbols())