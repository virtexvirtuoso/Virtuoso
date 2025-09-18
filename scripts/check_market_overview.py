#!/usr/bin/env python3
"""Check market overview data in cache"""

import asyncio
import aiomcache
import json

async def check():
    client = aiomcache.Client('localhost', 11211)
    
    print("=" * 60)
    print("CHECKING MARKET OVERVIEW DATA FLOW")
    print("=" * 60)
    
    # Check market:overview
    overview = await client.get(b'market:overview')
    if overview:
        data = json.loads(overview.decode())
        print('\n1. market:overview in cache:')
        print(json.dumps(data, indent=2))
    else:
        print('\n1. ❌ No market:overview in cache')
    
    # Check analysis:signals for aggregated data
    signals = await client.get(b'analysis:signals')
    if signals:
        data = json.loads(signals.decode())
        sigs = data.get('signals', [])
        if sigs:
            total_vol = sum(s.get('volume_24h', 0) for s in sigs)
            avg_change = sum(s.get('price_change_percent', 0) for s in sigs) / len(sigs) if sigs else 0
            gainers = len([s for s in sigs if s.get('price_change_percent', 0) > 0])
            losers = len([s for s in sigs if s.get('price_change_percent', 0) < 0])
            
            print(f'\n2. Data calculated from signals:')
            print(f'   Total symbols: {len(sigs)}')
            print(f'   Total volume: ${total_vol:,.0f}')
            print(f'   Average change: {avg_change:.2f}%')
            print(f'   Gainers: {gainers}')
            print(f'   Losers: {losers}')
            
            # Show first signal as sample
            if sigs:
                s = sigs[0]
                print(f'\n   Sample signal ({s.get("symbol")}):')
                print(f'     Price: ${s.get("price", 0)}')
                print(f'     Volume: ${s.get("volume_24h", 0):,.0f}')
                print(f'     Change: {s.get("price_change_percent", 0):.2f}%')
    else:
        print('\n2. ❌ No analysis:signals in cache')
    
    # Check market:movers
    movers = await client.get(b'market:movers')
    if movers:
        data = json.loads(movers.decode())
        print('\n3. market:movers in cache:')
        print(f'   Gainers: {len(data.get("gainers", []))}')
        print(f'   Losers: {len(data.get("losers", []))}')
    else:
        print('\n3. ❌ No market:movers in cache')
    
    # Check market regime
    regime = await client.get(b'analysis:market_regime')
    if regime:
        print(f'\n4. Market regime: {regime.decode()}')
    else:
        print('\n4. ❌ No market regime in cache')

asyncio.run(check())