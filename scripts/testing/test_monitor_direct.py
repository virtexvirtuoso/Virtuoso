#!/usr/bin/env python3
"""Direct test of MarketMonitor to bypass main.py initialization issues."""

import asyncio
import sys
import os
sys.path.insert(0, '.')

from src.core.exchanges.manager import ExchangeManager
from src.core.market.top_symbols import TopSymbolsManager
from src.core.validation.service import AsyncValidationService
from src.config.manager import ConfigManager
from src.monitoring.monitor import MarketMonitor

async def test_monitor_direct():
    print("🚀 DIRECT MONITOR TEST")
    
    try:
        # Initialize basic components
        config = ConfigManager()
        print("✅ Config loaded")
        
        exchange_manager = ExchangeManager(config)
        await exchange_manager.initialize()
        primary_exchange = await exchange_manager.get_primary_exchange()
        print(f"✅ Exchange: {primary_exchange.exchange_id}")
        
        validation_service = AsyncValidationService(config)
        
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config._config,
            validation_service=validation_service
        )
        top_symbols_manager.set_exchange(primary_exchange)
        print("✅ TopSymbolsManager initialized")
        
        # Test getting symbols
        symbols = await top_symbols_manager.get_symbols()
        print(f"✅ Got {len(symbols)} symbols: {symbols[:3]}")
        
        # Create minimal dependencies for MarketMonitor
        from src.monitoring.metrics_manager import MetricsManager
        from src.monitoring.alert_manager import AlertManager
        from src.core.market.market_data_manager import MarketDataManager
        
        alert_manager = AlertManager(config._config)
        metrics_manager = MetricsManager(config._config, alert_manager)
        market_data_manager = MarketDataManager(config._config, exchange_manager, alert_manager)
        
        # Create a minimal MarketMonitor with all dependencies
        monitor = MarketMonitor(
            logger=None,  # Will create its own
            exchange=primary_exchange,
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            market_data_manager=market_data_manager,  # Added this!
            config=config._config,
            metrics_manager=metrics_manager,
            alert_manager=alert_manager
        )
        
        print("🔄 Starting monitor...")
        await monitor.start()
        print("✅ Monitor started successfully!")
        
        # Let it run for a few cycles
        print("⏳ Waiting for monitoring cycles...")
        await asyncio.sleep(90)  # 3 cycles at 30-second intervals
        
        await monitor.stop()
        await exchange_manager.close()
        print("✅ Test completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_monitor_direct())