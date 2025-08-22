#!/usr/bin/env python3
"""
Create a debug endpoint to test cache directly
"""

DEBUG_ROUTE = '''
@router.get("/debug-cache")
async def debug_cache() -> Dict[str, Any]:
    """Debug endpoint to check cache directly"""
    import aiomcache
    import json
    
    client = aiomcache.Client('localhost', 11211)
    
    # Check signals directly
    signals_data = await client.get(b'analysis:signals')
    signal_count = 0
    if signals_data:
        signals = json.loads(signals_data.decode())
        signal_count = len(signals.get('signals', []))
    
    await client.close()
    
    # Also check via adapter
    adapter_signals = await cache_adapter.get_signals()
    
    return {
        'direct_cache_signals': signal_count,
        'adapter_signals': len(adapter_signals.get('signals', [])),
        'adapter_type': type(cache_adapter).__name__,
        'adapter_module': cache_adapter.__module__ if hasattr(cache_adapter, '__module__') else 'unknown'
    }
'''

# Add to the routes file
import sys
file_path = sys.argv[1] if len(sys.argv) > 1 else '/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/dashboard_cached.py'

with open(file_path, 'r') as f:
    content = f.read()

# Add before the last line
content = content.rstrip() + '\n' + DEBUG_ROUTE + '\n'

with open(file_path, 'w') as f:
    f.write(content)

print("✅ Added debug endpoint")