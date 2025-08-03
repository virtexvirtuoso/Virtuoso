#!/usr/bin/env python3
"""Final test to see confluence analysis formatted output."""

import asyncio
import sys
import time
import logging
sys.path.append('.')

# Set up logging to capture everything
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_confluence_final():
    from src.core.di.registration import bootstrap_container
    from src.config.manager import ConfigManager
    from src.monitoring.monitor import MarketMonitor
    
    print('🚀 Final confluence analysis test...')
    config = ConfigManager()
    container = bootstrap_container(config.config)
    monitor = await container.get_service(MarketMonitor)
    
    print('🔄 Starting monitor...')
    # Start monitor in background
    monitor_task = asyncio.create_task(monitor.start())
    
    # Wait for data loading phase to complete
    print('⏳ Waiting for market data loading (4 minutes)...')
    await asyncio.sleep(240)
    
    print('🔍 Checking monitor status...')
    if hasattr(monitor, 'running') and monitor.running:
        print('✅ Monitor is running')
        if hasattr(monitor, 'symbols') and monitor.symbols:
            print(f'✅ Monitor has {len(monitor.symbols)} symbols')
        else:
            print('❌ Monitor has no symbols')
    else:
        print('❌ Monitor is not running')
    
    # Wait for confluence analysis cycles
    print('⏳ Waiting for confluence analysis cycles (2 minutes)...')
    await asyncio.sleep(120)
    
    print('🛑 Stopping monitor...')
    await monitor.stop()
    monitor_task.cancel()
    
    print('✅ Test completed - check logs above for:')
    print('  🎯 "Confluence analysis completed"')
    print('  🎨 Beautiful formatted tables with borders')
    print('  📊 Component breakdown with gauges and scores')

if __name__ == "__main__":
    asyncio.run(test_confluence_final())