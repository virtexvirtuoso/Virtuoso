#!/usr/bin/env python3
"""Check top movers data flow"""

import asyncio
import aiomcache
import json

async def check():
    client = aiomcache.Client('localhost', 11211)
    
    print("=" * 60)
    print("TOP MOVERS DATA FLOW CHECK")
    print("=" * 60)
    
    # Check market:movers
    movers = await client.get(b'market:movers')
    if movers:
        data = json.loads(movers.decode())
        print('\n✅ market:movers in cache:')
        print(f'   Gainers: {len(data.get("gainers", []))}')
        print(f'   Losers: {len(data.get("losers", []))}')
        
        if data.get('gainers'):
            print('\n   Top 3 Gainers:')
            for i, g in enumerate(data['gainers'][:3], 1):
                print(f'   {i}. {g.get("symbol", "?")}:')
                print(f'      Price: ${g.get("price", 0):.2f}')
                print(f'      Change: {g.get("price_change_percent", 0):.2f}%')
                print(f'      Volume: ${g.get("volume_24h", 0):,.0f}')
        
        if data.get('losers'):
            print('\n   Top 3 Losers:')
            for i, l in enumerate(data['losers'][:3], 1):
                print(f'   {i}. {l.get("symbol", "?")}:')
                print(f'      Price: ${l.get("price", 0):.2f}')
                print(f'      Change: {l.get("price_change_percent", 0):.2f}%')
                print(f'      Volume: ${l.get("volume_24h", 0):,.0f}')
    else:
        print('\n❌ No market:movers in cache')
        
        # Try to generate from signals
        signals = await client.get(b'analysis:signals')
        if signals:
            data = json.loads(signals.decode())
            sigs = data.get('signals', [])
            
            # Sort by price change
            gainers = [s for s in sigs if s.get('price_change_percent', 0) > 0]
            losers = [s for s in sigs if s.get('price_change_percent', 0) < 0]
            
            gainers.sort(key=lambda x: x.get('price_change_percent', 0), reverse=True)
            losers.sort(key=lambda x: x.get('price_change_percent', 0))
            
            print('\n📊 Generated from signals:')
            print(f'   Potential gainers: {len(gainers)}')
            print(f'   Potential losers: {len(losers)}')
            
            if gainers:
                print('\n   Top gainers from signals:')
                for g in gainers[:3]:
                    print(f'   - {g.get("symbol")}: +{g.get("price_change_percent", 0):.2f}%')

asyncio.run(check())