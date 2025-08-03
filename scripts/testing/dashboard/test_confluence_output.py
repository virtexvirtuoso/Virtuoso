#!/usr/bin/env python3
"""Test confluence analysis output with proper formatting."""

import asyncio
import sys
import time
sys.path.append('.')

from src.core.di.registration import bootstrap_container
from src.config.manager import ConfigManager
from src.monitoring.monitor import MarketMonitor

async def wait_for_confluence_output():
    print('🚀 Testing confluence analysis formatted output...')
    config = ConfigManager()
    container = bootstrap_container(config.config)
    print('✅ Container bootstrapped')
    
    monitor = await container.get_service(MarketMonitor)
    print(f'✅ MarketMonitor created: {type(monitor).__name__}')
    
    # Start the monitor
    print('🔄 Starting monitor and waiting for confluence analysis...')
    monitor_task = asyncio.create_task(monitor.start())
    
    # Wait for the first monitoring cycle to complete (data loading + analysis)
    print('⏳ Waiting for data loading and first analysis cycle...')
    await asyncio.sleep(180)  # 3 minutes to complete initial data loading
    
    print('🔍 Looking for confluence analysis in logs...')
    print('💡 If confluence analysis has run, you should see:')
    print('   - "Successful indicators" message')
    print('   - Beautiful formatted table with borders and gauges')
    print('   - "Confluence analysis completed" message')
    
    # Let it run one monitoring cycle
    print('⏳ Waiting for monitoring cycle...')
    await asyncio.sleep(60)  # 1 minute for monitoring cycle
    
    print('🛑 Stopping monitor...')
    await monitor.stop()
    print('✅ Test completed')

if __name__ == "__main__":
    asyncio.run(wait_for_confluence_output())