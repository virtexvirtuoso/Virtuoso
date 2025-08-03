#!/usr/bin/env python3
"""Test DI container MarketMonitor creation."""

import asyncio
import sys
sys.path.append('.')

from src.core.di.registration import bootstrap_container
from src.config.manager import ConfigManager
from src.monitoring.monitor import MarketMonitor

async def test_di_monitor():
    print('🚀 Testing DI container MarketMonitor creation...')
    config = ConfigManager()
    container = bootstrap_container(config.config)
    print('✅ Container bootstrapped')
    
    monitor = await container.get_service(MarketMonitor)
    print(f'✅ MarketMonitor created: {type(monitor).__name__}')
    print(f'Has exchange_manager: {hasattr(monitor, "exchange_manager") and monitor.exchange_manager is not None}')
    print(f'Has market_data_manager: {hasattr(monitor, "market_data_manager") and monitor.market_data_manager is not None}')
    print(f'Has top_symbols_manager: {hasattr(monitor, "top_symbols_manager") and monitor.top_symbols_manager is not None}')
    print(f'Has confluence_analyzer: {hasattr(monitor, "confluence_analyzer") and monitor.confluence_analyzer is not None}')
    
    # Test getting symbols
    if hasattr(monitor, 'top_symbols_manager') and monitor.top_symbols_manager:
        try:
            symbols = await monitor.top_symbols_manager.get_symbols()
            print(f'✅ Got {len(symbols)} symbols from top_symbols_manager')
        except Exception as e:
            print(f'❌ Error getting symbols: {e}')
    
    # Test start method
    try:
        print('🔄 Starting monitor...')
        await monitor.start()
        print('✅ Monitor started successfully!')
    except Exception as e:
        print(f'❌ Error starting monitor: {e}')

if __name__ == "__main__":
    asyncio.run(test_di_monitor())