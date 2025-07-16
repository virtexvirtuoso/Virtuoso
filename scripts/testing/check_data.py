#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

async def check_data():
    from src.core.exchanges.bybit import BybitExchange
    
    exchange_config = {
        'exchanges': {
            'bybit': {
                'name': 'bybit',
                'enabled': True,
                'api_credentials': {'api_key': '', 'api_secret': ''},
                'sandbox': False,
                'testnet': False,
                'websocket': {
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                }
            }
        }
    }
    
    exchange = BybitExchange(exchange_config)
    await exchange.initialize()
    
    trades = await exchange.fetch_trades('BTCUSDT', limit=3)
    ticker = await exchange.fetch_ticker('BTCUSDT')
    
    print('📊 Sample trade data:')
    if trades:
        print(f'First trade: {trades[0]}')
        trades_df = pd.DataFrame(trades)
        print(f'Columns: {list(trades_df.columns)}')
    
    print(f'\n📊 Ticker data:')
    print(f'Price: {ticker["last"]:.2f}, Change: {ticker["percentage"]:+.2f}%')

if __name__ == "__main__":
    asyncio.run(check_data()) 