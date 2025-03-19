import asyncio
import aiohttp
import json

async def main():
    async with aiohttp.ClientSession() as session:
        # Test OHLCV endpoint
        params = {
            'category': 'linear',
            'symbol': 'BTCUSDT',
            'interval': '1',
            'limit': 200
        }
        
        async with session.get('https://api.bybit.com/v5/market/kline', params=params) as response:
            result = await response.json()
            print("=== OHLCV Response ===")
            print(json.dumps(result, indent=2))
            
            # Check if we have candles
            if 'result' in result and 'list' in result['result']:
                candles = result['result']['list']
                print(f"\nNumber of candles: {len(candles)}")
                if candles:
                    print(f"First candle: {candles[0]}")
            else:
                print("\nNo candles found in response")

if __name__ == "__main__":
    asyncio.run(main()) 