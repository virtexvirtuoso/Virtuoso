#!/usr/bin/env python3
"""
Add direct symbols endpoint to dashboard routes
"""

patch = '''
@router.get("/symbols-direct")
async def get_symbols_direct() -> Dict[str, Any]:
    """Get symbols directly from cache without proxy."""
    try:
        from src.core.api_cache import api_cache
        
        # Get directly from cache
        symbols_data = api_cache.get("symbols")
        
        if symbols_data and "symbols" in symbols_data:
            logger.info(f"Returning {len(symbols_data['symbols'])} symbols directly")
            return symbols_data
        
        # Return empty if no data
        return {
            "status": "no_data", 
            "symbols": [],
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Cache is empty - waiting for data"
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols directly: {e}")
        return {"status": "error", "symbols": [], "error": str(e)}
'''

import sys
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

# Add to dashboard.py
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/dashboard.py', 'r') as f:
    content = f.read()

if '@router.get("/symbols-direct")' not in content:
    # Add after the existing symbols endpoint
    pos = content.find('@router.get("/symbols")')
    if pos > 0:
        # Find end of that function
        next_route = content.find('\n@router', pos + 1)
        if next_route > 0:
            content = content[:next_route] + '\n' + patch + content[next_route:]
        else:
            content = content + '\n' + patch
        
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/dashboard.py', 'w') as f:
            f.write(content)
        
        print("✅ Added direct symbols endpoint")
else:
    print("✅ Direct endpoint already exists")

print("\nNew endpoint available at:")
print("  http://${VPS_HOST}:8001/api/symbols-direct")
print("\nThis bypasses the proxy and gets data directly from cache.")