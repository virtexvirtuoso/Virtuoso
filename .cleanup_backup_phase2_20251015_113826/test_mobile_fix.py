#!/usr/bin/env python3
"""Test that the mobile dashboard fix works."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

async def test_mobile_endpoint():
    """Test the mobile-data endpoint directly."""
    from src.api.routes.dashboard import get_mobile_dashboard_data

    print("Testing mobile-data endpoint...")
    print("=" * 60)

    try:
        # Call the endpoint function directly
        response = await get_mobile_dashboard_data()

        print(f"Status: {response.get('status')}")
        print(f"Keys in response: {list(response.keys())}")

        # Check if status is now 'success'
        if response.get('status') == 'success':
            print("✅ SUCCESS! Status is now 'success'")

            # Check data
            if 'confluence_scores' in response:
                scores = response['confluence_scores']
                print(f"Confluence scores: {len(scores)} items")

            if 'top_movers' in response:
                movers = response['top_movers']
                print(f"Top gainers: {len(movers.get('gainers', []))} items")
                print(f"Top losers: {len(movers.get('losers', []))} items")

        elif response.get('status') == 'no_integration':
            print("❌ FAIL: Status is still 'no_integration' - fix didn't work")
        else:
            print(f"⚠️ Unexpected status: {response.get('status')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mobile_endpoint())