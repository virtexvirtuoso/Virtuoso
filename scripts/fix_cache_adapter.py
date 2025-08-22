#\!/usr/bin/env python3
"""Fix the cache adapter to prevent hanging"""

import os

def fix_cache_adapter():
    # Fix the cache_adapter_direct.py file
    adapter_path = "src/api/cache_adapter_direct.py"
    
    with open(adapter_path, 'r') as f:
        content = f.read()
    
    # Add timeout to all cache operations
    old_client = "client = aiomcache.Client('localhost', 11211)"
    new_client = "client = aiomcache.Client('localhost', 11211, pool_size=2)"
    
    if old_client in content:
        content = content.replace(old_client, new_client)
        print("✅ Fixed cache client initialization")
    
    # Add timeout wrapper
    if "asyncio.wait_for" not in content:
        # Add import
        content = "import asyncio\n" + content
        
        # Wrap get operations with timeout
        content = content.replace(
            "data = await client.get(key)",
            "data = await asyncio.wait_for(client.get(key), timeout=1.0)"
        )
        print("✅ Added timeouts to cache operations")
    
    with open(adapter_path, 'w') as f:
        f.write(content)
    
    print("✅ cache_adapter_direct.py fixed")

if __name__ == "__main__":
    fix_cache_adapter()
