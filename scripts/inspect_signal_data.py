"""Inspect signal data in cache to see actual component values"""
import asyncio
import json
import sys

sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

import aiomcache

async def inspect_signals():
    """Check what's actually in the cache for signals"""
    print("\n" + "="*70)
    print("INSPECTING CACHE SIGNAL DATA")
    print("="*70)

    try:
        client = aiomcache.Client('localhost', 11211)

        # Get analysis:signals
        data = await client.get(b'analysis:signals')

        if not data:
            print("❌ No data found in analysis:signals")
            return

        decoded = json.loads(data.decode())
        signals = decoded.get('signals', decoded.get('recent_signals', []))

        print(f"\n✅ Found {len(signals)} signals in cache")
        print(f"Cache keys: {list(decoded.keys())}\n")

        # Look at first few signals
        for i, signal in enumerate(signals[:3]):
            symbol = signal.get('symbol', 'UNKNOWN')
            score = signal.get('confluence_score', signal.get('score', 0))

            print(f"\n{'='*70}")
            print(f"Signal {i+1}: {symbol}")
            print(f"{'='*70}")
            print(f"Confluence Score: {score}")
            print(f"Price: ${signal.get('price', 0)}")
            print(f"Price Change %: {signal.get('price_change_percent', signal.get('change_24h', 0))}%")
            print(f"Volume: ${signal.get('volume_24h', signal.get('volume', 0)):,.0f}")
            print(f"Sentiment: {signal.get('sentiment', 'N/A')}")

            # Check if components exist
            components = signal.get('components', {})
            print(f"\nComponents Available: {bool(components)}")

            if components:
                print("Component Breakdown:")
                for comp_name, comp_value in components.items():
                    print(f"  {comp_name}: {comp_value}")
            else:
                print("⚠️  WARNING: No components in signal data!")

            # Check for other useful fields
            print(f"\nOther Fields:")
            for key in ['high_24h', 'low_24h', 'range_24h', 'reliability', 'timestamp']:
                if key in signal:
                    print(f"  {key}: {signal[key]}")

        # Also check for confluence breakdown keys
        print(f"\n{'='*70}")
        print("CHECKING FOR DETAILED CONFLUENCE BREAKDOWNS")
        print(f"{'='*70}")

        for signal in signals[:3]:
            symbol = signal.get('symbol')
            if symbol:
                breakdown_key = f'confluence:breakdown:{symbol}'
                breakdown_data = await client.get(breakdown_key.encode())

                if breakdown_data:
                    breakdown = json.loads(breakdown_data.decode())
                    print(f"\n✅ Found breakdown for {symbol}")
                    print(f"   Overall Score: {breakdown.get('overall_score', 'N/A')}")
                    print(f"   Components: {list(breakdown.get('components', {}).keys())}")
                else:
                    print(f"\n⚠️  No breakdown found for {symbol} at key: {breakdown_key}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(inspect_signals())
