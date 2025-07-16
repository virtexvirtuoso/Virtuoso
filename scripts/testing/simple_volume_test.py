#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('src')

async def test():
    from core.exchanges.manager import ExchangeManager
    from core.config.config_manager import ConfigManager
    
    config = ConfigManager()
    await config.initialize()
    
    manager = ExchangeManager(config)
    await manager.initialize()
    
    try:
        market_data = await manager.get_market_data('BTCUSDT')
        print('Market data keys:', list(market_data.keys()))
        
        if 'price' in market_data:
            price = market_data['price']
            print('Price volume:', price.get('volume'))
            print('Price turnover:', price.get('turnover'))
        
        if 'ticker' in market_data:
            ticker = market_data['ticker']
            print('Ticker baseVolume:', ticker.get('baseVolume'))
            print('Ticker quoteVolume:', ticker.get('quoteVolume'))
    finally:
        await manager.cleanup()

asyncio.run(test()) 