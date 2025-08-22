#!/usr/bin/env python3
"""
Test if there's an import issue
"""
import sys
import os
import asyncio

# Add path
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

# Import the routes module
from src.api.routes import dashboard_cached

# Test the adapter
async def test():
    print(f"Adapter type: {type(dashboard_cached.cache_adapter)}")
    print(f"Adapter module: {dashboard_cached.cache_adapter.__module__}")
    
    # Test get_signals
    signals = await dashboard_cached.cache_adapter.get_signals()
    print(f"Signals returned: {len(signals.get('signals', []))}")
    
    # Test the endpoint function directly
    result = await dashboard_cached.get_signals()
    print(f"Endpoint returned: {len(result.get('signals', []))}")

if __name__ == "__main__":
    asyncio.run(test())