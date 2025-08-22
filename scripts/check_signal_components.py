#!/usr/bin/env python3
"""Check signal components structure in cache"""
import asyncio
import aiomcache
import json

async def check_signals():
    client = aiomcache.Client('localhost', 11211)
    
    try:
        # Get signals data
        data = await client.get(b'analysis:signals')
        if data:
            signals = json.loads(data.decode())
            print(f"Found {len(signals.get('signals', []))} signals")
            
            # Check first signal structure
            if signals.get('signals'):
                first_signal = signals['signals'][0]
                print(f"\nFirst signal ({first_signal.get('symbol')}):")
                print(f"  Score: {first_signal.get('score')}")
                print(f"  Action: {first_signal.get('action')}")
                print(f"  Components:")
                
                components = first_signal.get('components', {})
                for comp_name, comp_data in components.items():
                    if isinstance(comp_data, dict):
                        print(f"    {comp_name}: {comp_data.get('score', 'N/A')} (dict structure)")
                    else:
                        print(f"    {comp_name}: {comp_data} (simple value)")
        else:
            print("No signals data in cache")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check_signals())