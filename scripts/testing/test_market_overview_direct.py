#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('src')

async def test_market_overview():
    from monitoring.market_reporter import MarketReporter
    from core.exchanges.bybit import BybitExchange
    from core.config.config_manager import ConfigManager
    
    config = ConfigManager()
    await config.initialize()
    
    exchanges_config = config.get_value('exchanges', {})
    bybit_config = exchanges_config.get('bybit', {})
    
    exchange = BybitExchange(bybit_config)
    await exchange.initialize()
    
    try:
        # Create reporter with NO top_symbols_manager to force direct ticker fetch
        reporter = MarketReporter(exchange=exchange, top_symbols_manager=None)
        
        symbols = ['BTCUSDT', 'ETHUSDT']
        print("Testing market overview calculation with direct ticker fetch...")
        
        result = await reporter._calculate_market_overview(symbols)
        
        print(f'Total volume: {result.get("total_volume")}')
        print(f'Total turnover: {result.get("total_turnover")}')
        print(f'Volume by pair: {result.get("volume_by_pair")}')
        print(f'Failed symbols: {result.get("failed_symbols")}')
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_market_overview()) 