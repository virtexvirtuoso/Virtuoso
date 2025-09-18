#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.exchanges.bybit import BybitExchange
from src.config.config_loader import load_config

async def test_lsr():
    config = load_config()
    exchange = BybitExchange(config)
    
    # Test LSR for BTC
    lsr_data = await exchange._fetch_long_short_ratio('BTCUSDT')
    print(f"Direct LSR fetch for BTCUSDT: {lsr_data}")
    
    # Test full market data
    market_data = await exchange.fetch_market_data('BTCUSDT')
    if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:
        print(f"LSR in market_data: {market_data['sentiment']['long_short_ratio']}")
    else:
        print("LSR not found in market_data!")

if __name__ == "__main__":
    asyncio.run(test_lsr())
