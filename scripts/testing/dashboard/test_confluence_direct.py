#!/usr/bin/env python3
"""Test confluence analysis directly to see formatted output."""

import asyncio
import sys
sys.path.append('.')

async def test_confluence_directly():
    # Quick test to see if confluence analysis is running
    from src.core.di.registration import bootstrap_container
    from src.config.manager import ConfigManager
    from src.monitoring.monitor import MarketMonitor
    
    config = ConfigManager()
    container = bootstrap_container(config.config)
    monitor = await container.get_service(MarketMonitor)
    
    print('🚀 Starting monitor...')
    monitor_start = asyncio.create_task(monitor.start())
    
    # Wait longer for full initialization and data loading
    print('⏳ Waiting for initialization and data loading...')
    await asyncio.sleep(240)  # 4 minutes for full data loading
    
    # Check if we have symbols
    if hasattr(monitor, 'symbols') and monitor.symbols:
        print(f'✅ Monitor has {len(monitor.symbols)} symbols')
        
        # Try to run a single analysis cycle manually
        if hasattr(monitor, '_process_symbol'):
            print('🔄 Testing confluence analysis on first symbol...')
            test_symbol = monitor.symbols[0]
            try:
                await monitor._process_symbol(test_symbol)
                print('✅ Confluence analysis completed!')
            except Exception as e:
                print(f'❌ Error in confluence analysis: {e}')
        else:
            print('❌ No _process_symbol method found')
    else:
        print('❌ No symbols available for analysis')
    
    await monitor.stop()

if __name__ == "__main__":
    asyncio.run(test_confluence_directly())