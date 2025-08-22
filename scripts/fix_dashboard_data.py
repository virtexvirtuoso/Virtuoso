#!/usr/bin/env python3
"""Fix dashboard data population by ensuring symbols are properly initialized."""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.exchanges.manager import ExchangeManager
from src.config.manager import ConfigManager
from src.core.market.top_symbols import TopSymbolsManager
from src.dashboard.dashboard_integration import DashboardIntegrationService
from src.monitoring.monitor import MarketMonitor
from src.core.validation.service import AsyncValidationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default symbols to ensure data is available
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT",
    "UNIUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT", "NEARUSDT"
]

async def initialize_monitor_with_symbols():
    """Initialize monitor with proper symbols."""
    try:
        # Initialize core components
        config = ConfigManager()
        exchange_manager = ExchangeManager(config)
        await exchange_manager.initialize()
        
        # Get available symbols from exchange
        try:
            # Try to get symbols from Bybit
            exchange = exchange_manager.exchanges.get('bybit')
            if exchange:
                await exchange.load_markets()
                available_symbols = list(exchange.markets.keys())[:50]  # Get top 50 symbols
                
                # Filter for USDT pairs
                usdt_symbols = [s for s in available_symbols if s.endswith('USDT')][:15]
                
                if usdt_symbols:
                    logger.info(f"Found {len(usdt_symbols)} USDT symbols from exchange")
                    symbols = usdt_symbols
                else:
                    symbols = DEFAULT_SYMBOLS
            else:
                symbols = DEFAULT_SYMBOLS
        except Exception as e:
            logger.warning(f"Failed to get symbols from exchange: {e}")
            symbols = DEFAULT_SYMBOLS
        
        logger.info(f"Using symbols: {symbols}")
        
        # Create validation service
        validation_service = AsyncValidationService(config)
        
        # Initialize top symbols manager with symbols
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config,
            validation_service=validation_service
        )
        
        # Set the symbols directly
        if hasattr(top_symbols_manager, '_symbols'):
            top_symbols_manager._symbols = symbols
        
        # Initialize market monitor with symbols
        monitor = MarketMonitor(
            exchange_manager=exchange_manager,
            config=config,
            top_symbols_manager=top_symbols_manager
        )
        
        # Set symbols on monitor
        monitor.symbols = symbols
        
        # Initialize dashboard integration
        dashboard_integration = DashboardIntegrationService(monitor=monitor)
        
        # Test getting symbol data
        await dashboard_integration._update_signals()
        symbol_data = dashboard_integration.get_symbol_data()
        
        logger.info(f"Dashboard integration initialized with {len(symbol_data)} symbols")
        
        # Get dashboard symbols to verify
        dashboard_symbols = await dashboard_integration.get_dashboard_symbols(limit=15)
        logger.info(f"Dashboard symbols: {dashboard_symbols}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize monitor with symbols: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    success = await initialize_monitor_with_symbols()
    if success:
        logger.info("✅ Successfully initialized monitor with symbols")
    else:
        logger.error("❌ Failed to initialize monitor with symbols")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())