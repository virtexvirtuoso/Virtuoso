#!/usr/bin/env python3
"""Add background task to fetch ticker data periodically"""

import asyncio
from pathlib import Path

# Path to main.py
main_file = Path(__file__).parent.parent / "src" / "main.py"

# Read current content
with open(main_file, 'r') as f:
    content = f.read()

# Add ticker fetching function
ticker_function = '''
async def fetch_and_cache_tickers():
    """Fetch ticker data from Bybit and cache it"""
    try:
        import aiohttp
        import aiomcache
        import json
        
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        tickers = data.get('result', {}).get('list', [])
                        
                        # Convert to dict for easy lookup
                        ticker_dict = {}
                        for ticker in tickers:
                            symbol = ticker.get('symbol')
                            if symbol:
                                ticker_dict[symbol] = {
                                    'symbol': symbol,
                                    'price': float(ticker.get('lastPrice', 0)),
                                    'volume_24h_usd': float(ticker.get('turnover24h', 0)),
                                    'price_change_percent': float(ticker.get('price24hPcnt', 0)) * 100,
                                    'high_24h': float(ticker.get('highPrice24h', 0)),
                                    'low_24h': float(ticker.get('lowPrice24h', 0)),
                                    'volume': float(ticker.get('volume24h', 0))
                                }
                        
                        # Store in memcache
                        memcache_client = aiomcache.Client('localhost', 11211)
                        await memcache_client.set(
                            b'market:tickers',
                            json.dumps({'tickers': list(ticker_dict.values())}).encode(),
                            exptime=300  # 5 minutes
                        )
                        logger.info(f"✅ Cached {len(ticker_dict)} tickers from Bybit")
                        return ticker_dict
    except Exception as e:
        logger.error(f"Error fetching tickers: {e}")
    return {}


async def schedule_ticker_updates():
    """Schedule periodic ticker updates"""
    while True:
        await asyncio.sleep(120)  # Update every 2 minutes
        await fetch_and_cache_tickers()
'''

# Find where to insert the ticker functions
insert_pos = content.find("async def schedule_background_update():")
if insert_pos > 0:
    # Insert before schedule_background_update
    content = content[:insert_pos] + ticker_function + "\n\n" + content[insert_pos:]
    print("✅ Added ticker fetching functions")
else:
    print("❌ Could not find insertion point")
    exit(1)

# Add ticker scheduler to main function
# Find the line where background update is started
scheduler_line = "        asyncio.create_task(schedule_background_update())"
if scheduler_line in content:
    # Add ticker scheduler after it
    content = content.replace(
        scheduler_line,
        scheduler_line + "\n        asyncio.create_task(schedule_ticker_updates())"
    )
    print("✅ Added ticker scheduler to main()")

# Write back
with open(main_file, 'w') as f:
    f.write(content)

print("✅ Successfully added ticker background task to main.py")