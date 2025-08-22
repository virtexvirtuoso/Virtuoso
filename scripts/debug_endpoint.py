#!/usr/bin/env python3
import asyncio
import aiohttp

async def test_endpoints():
    async with aiohttp.ClientSession() as session:
        # Test the cached signals endpoint
        async with session.get('http://45.77.40.77:8001/api/dashboard-cached/signals') as resp:
            data = await resp.json()
            print(f"Cached signals endpoint:")
            print(f"  Status: {resp.status}")
            print(f"  Signal count: {len(data.get('signals', []))}")
            print(f"  Response keys: {list(data.keys())}")
            
        # Test mobile data endpoint
        async with session.get('http://45.77.40.77:8001/api/dashboard-cached/mobile-data') as resp:
            data = await resp.json()
            print(f"\nMobile data endpoint:")
            print(f"  Status: {resp.status}")
            print(f"  Confluence scores: {len(data.get('confluence_scores', []))}")
            if data.get('confluence_scores'):
                print(f"  First score: {data['confluence_scores'][0]}")
                
        # Test fast signals (known to work)
        async with session.get('http://45.77.40.77:8001/api/fast/signals') as resp:
            data = await resp.json()
            print(f"\nFast signals endpoint (reference):")
            print(f"  Status: {resp.status}")
            print(f"  Signal count: {len(data.get('signals', []))}")
            if data.get('signals'):
                print(f"  First signal: {data['signals'][0]['symbol']} - Score: {data['signals'][0]['score']}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())