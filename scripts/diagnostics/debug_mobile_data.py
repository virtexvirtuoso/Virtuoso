#!/usr/bin/env python3
"""Debug mobile dashboard data flow."""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_mobile_endpoints():
    """Test all mobile-related endpoints."""
    base_url = "http://localhost:8002"

    endpoints = [
        "/api/dashboard/mobile-data",
        "/api/dashboard/overview",
        "/api/dashboard/symbols",
        "/api/dashboard/market-overview",
        "/api/dashboard/signals"
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                print(f"\n{'='*60}")
                print(f"Testing: {url}")
                print(f"{'='*60}")

                async with session.get(url, timeout=10) as response:
                    status = response.status
                    data = await response.json()

                    print(f"Status: {status}")

                    if endpoint == "/api/dashboard/mobile-data":
                        # Detailed analysis for mobile-data
                        print(f"Response Status Field: {data.get('status')}")
                        print(f"Keys in response: {list(data.keys())}")

                        if 'confluence_scores' in data:
                            scores = data['confluence_scores']
                            print(f"Confluence scores: {len(scores)} items")
                            if scores:
                                print(f"Sample score: {json.dumps(scores[0], indent=2)}")

                        if 'top_movers' in data:
                            movers = data['top_movers']
                            print(f"Top movers structure: {list(movers.keys()) if isinstance(movers, dict) else type(movers)}")
                            if isinstance(movers, dict):
                                gainers = movers.get('gainers', [])
                                losers = movers.get('losers', [])
                                print(f"  Gainers: {len(gainers)} items")
                                print(f"  Losers: {len(losers)} items")
                                if gainers:
                                    print(f"  Sample gainer: {json.dumps(gainers[0], indent=2)}")

                        if 'market_overview' in data:
                            overview = data['market_overview']
                            print(f"Market overview keys: {list(overview.keys()) if isinstance(overview, dict) else type(overview)}")

                    elif endpoint == "/api/dashboard/signals":
                        print(f"Keys in response: {list(data.keys())}")
                        if 'signals' in data:
                            print(f"Signals: {len(data['signals'])} items")
                        elif 'recent_signals' in data:
                            print(f"Recent signals: {len(data['recent_signals'])} items")
                        elif isinstance(data, list):
                            print(f"Response is array with {len(data)} items")

                    elif endpoint == "/api/dashboard/overview":
                        print(f"Keys in response: {list(data.keys())}")
                        if 'opportunities' in data:
                            print(f"Opportunities: {len(data.get('opportunities', []))} items")

                    else:
                        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else f'Array with {len(data)} items'}")

            except Exception as e:
                print(f"ERROR testing {endpoint}: {e}")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print("\nKey findings:")
    print("1. Check if confluence_scores is empty or has data")
    print("2. Check if top_movers has gainers/losers arrays")
    print("3. Verify the 'status' field in mobile-data response")
    print("4. Look for any type mismatches or missing fields")

if __name__ == "__main__":
    asyncio.run(test_mobile_endpoints())