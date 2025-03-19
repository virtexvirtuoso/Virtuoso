import asyncio
import sys
import logging
import os
from src.core.exchanges.bybit import BybitExchange
from src.config.manager import ConfigManager

async def test_fetch_ohlcv():
    # Set up basic logging
    logging.basicConfig(level=logging.DEBUG, 
                      format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                      handlers=[logging.StreamHandler()])
    
    # Sample config
    config = {
        'exchanges': {
            'bybit': {
                'name': 'bybit',
                'enabled': True,
                'testnet': False,
                'rest_endpoint': 'https://api.bybit.com',
                'websocket': {
                    'enabled': False,
                    'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                    'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
                },
                'api_credentials': {
                    'api_key': 'dummy_key',
                    'api_secret': 'dummy_secret'
                }
            }
        }
    }
    
    # Create exchange directly since we're testing
    bybit = BybitExchange(config)
    
    # Initialize exchange (required)
    success = await bybit.initialize()
    if not success:
        print("Failed to initialize Bybit exchange")
        return
    
    # Test fetching order book
    try:
        print("\nTesting fetch_order_book:")
        orderbook = await bybit.fetch_order_book('BTCUSDT')
        print(f"Order book: {orderbook.keys()}")
        print(f"Bids count: {len(orderbook.get('bids', []))}")
        print(f"Asks count: {len(orderbook.get('asks', []))}")
    except Exception as e:
        print(f"Error fetching order book: {e}")
    
    # Test OHLCV fetching for BTCUSDT
    try:
        print("\nTesting _fetch_all_timeframes:")
        ohlcv_data = await bybit._fetch_all_timeframes('BTCUSDT')
        print('\nOHLCV Data:')
        for timeframe, df in ohlcv_data.items():
            print(f'\n{timeframe} Timeframe:')
            if not df.empty:
                print(f'Shape: {df.shape}')
                print(f'First few rows:')
                print(df.head(2))
            else:
                print('Empty DataFrame')
    except Exception as e:
        print(f'Error: {e}')
    
    # Cleanup
    await bybit.close()

# Run the test
if __name__ == "__main__":
    asyncio.run(test_fetch_ohlcv()) 