#!/usr/bin/env python3
"""Test aggregation with ticker fetching"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_aggregation():
    """Test the aggregation with ticker data"""
    try:
        # Import after path is set
        from src.main import aggregate_confluence_signals
        
        print("Running aggregation with ticker fetching...")
        await aggregate_confluence_signals()
        print("Aggregation complete!")
        
        # Check the result
        import aiomcache
        import json
        
        client = aiomcache.Client('localhost', 11211)
        data = await client.get(b'analysis:signals')
        
        if data:
            signals = json.loads(data.decode())
            if signals.get('signals'):
                first = signals['signals'][0]
                print(f"\nFirst signal: {first['symbol']}")
                print(f"  Price: ${first.get('price', 0)}")
                print(f"  Volume 24h: ${first.get('volume_24h', 0):,.0f}")
                print(f"  Change 24h: {first.get('price_change_percent', 0):.2f}%")
                print(f"  Turnover: ${first.get('turnover_24h', 0):,.0f}")
                print(f"  High 24h: ${first.get('high_24h', 0)}")
                print(f"  Low 24h: ${first.get('low_24h', 0)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_aggregation())