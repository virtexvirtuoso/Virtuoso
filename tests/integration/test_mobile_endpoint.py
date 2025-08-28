#!/usr/bin/env python3
"""Test script to debug mobile endpoint confluence integration."""

import asyncio
import aiohttp
import json

async def test_mobile_endpoint():
    async with aiohttp.ClientSession() as session:
        try:
            # Test mobile endpoint
            print("Testing mobile endpoint...")
            async with session.get('http://localhost:8001/api/dashboard/mobile-data') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Status: {data.get('status')}")
                    print(f"Confluence scores count: {len(data.get('confluence_scores', []))}")
                    if data.get('confluence_scores'):
                        print("First few scores:")
                        for score in data['confluence_scores'][:3]:
                            print(f"  {score.get('symbol')}: {score.get('score')}")
                    else:
                        print("No confluence scores found")
                        print(f"Response keys: {list(data.keys())}")
                else:
                    print(f"Error: {resp.status}")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mobile_endpoint())